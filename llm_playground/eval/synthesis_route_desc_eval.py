import os
import re
import json
from pydantic import BaseModel
from typing import List, Dict, Any
from collections import defaultdict
import pandas as pd

from llm_playground.datamodel.synthesis_route import (
    ReactionStepDescriptionRecord,
    ReactionStepDescription
)


# ---------- 数据模型 ----------
class CompoundTextIdItem(BaseModel):
    structure: str
    compound_id: str | None = None
    example_id: str | None = None
    iupac_name: str | None = None

def empty_item(detail_id_key: str) -> ReactionStepDescription:
    detail_ids = detail_id_key.split('|')
    return ReactionStepDescription(
        compound_id="",           # 必填：给空串
        iupac_name="",            # 必填：给空串
        structure_id="",          # 允许空
        detail_ids=detail_ids,    # 必填：用key还原
        detail="",                # 必填：给空串
        refs=None,                # 必填但可为None：显式给None
    )
class ErrorAnalysis(BaseModel):
    """错误分析数据结构"""
    detail_id: str
    error_type: int
    ground_truth: ReactionStepDescription
    prediction: ReactionStepDescription

class ComparisonResult(BaseModel):
    """比较结果数据结构"""
    record_id: str
    is_correct: bool
    errors: List[ErrorAnalysis]
    item_recall: int
    item_correct: int
    total_ground_truth_items: int
    total_predicted_items: int

# ---------- 规范化 ----------
def make_detail_key(detail_ids: List[str], compound_id: str, structure_id: str) -> str:
    # 1) 规范化：detail_ids 排序 + 去重
    norm_ids = sorted(dict.fromkeys(detail_ids))
    base = "|".join(norm_ids)
    # 2) 安全拼接（避免分隔符冲突可再做转义，这里简化处理）
    return f"{base}||{compound_id}||{structure_id}"


def conv_output_to_dict(results: List[Dict[str, Any]]) -> Dict[str, "ReactionStepDescription"]:
    """
    主键 = sorted(detail_ids) + compound_id + structure_id 的组合
    - 缺 detail_ids 直接跳过
    - 允许 refs 为 None 或 list
    - 如遇到重复 key（理论不应发生），保留首个并记录一次告警
    """
    out: Dict[str, ReactionStepDescription] = {}
    for obj in results:
        detail_ids = obj.get("detail_ids") or []
        if not detail_ids:
            continue
        key = make_detail_key(detail_ids, obj.get("compound_id",""), obj.get("structure_id","") or "")
        try:
            rsd = ReactionStepDescription(
                compound_id=obj.get("compound_id",""),
                iupac_name=obj.get("iupac_name",""),
                structure_id=obj.get("structure_id","") or "",
                detail_ids=sorted(dict.fromkeys(detail_ids)),
                detail=obj.get("detail",""),
                refs=obj.get("refs") or None,
            )
        except Exception:
            continue

        if key in out:
            # 理论不该出现；保留首个，打印一次以便排查
            print(f"[WARN] Duplicate composite key detected (kept first): {key}")
            continue
        out[key] = rsd
    return out


def norm_example_id(x: str | None) -> str | None:
    if not x:
        return None
    s = re.sub(r'[\s\u00A0]+', ' ', x.strip()).strip().lower()
    s = re.sub(r'^(example|实施例|例|样例|实例)\s*', '', s)
    m = re.search(r'(\d+)\s*$', s)
    if m:
        return m.group(1)
    m = re.search(r'([a-z0-9]+)\s*$', s)
    return m.group(1) if m else None

def norm_compound_id(x: str | None) -> str | None:
    if not x:
        return None
    s = re.sub(r'[\s\u00A0]+', ' ', x).strip()
    if re.search(r'[\u4e00-\u9fa5]', s):
        for i, ch in enumerate(s):
            if not re.match(r'[\u4e00-\u9fa5]', ch):
                return s[i:].strip()
        return None
    else:
        return s.split()[-1]

# ---------- IUPAC 归一 + 编辑距离 ----------
def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0: return lb
    if lb == 0: return la
    prev = list(range(lb + 1))
    curr = [0] * (lb + 1)
    for i in range(1, la + 1):
        curr[0] = i
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cb = b[j - 1]
            cost = 0 if ca == cb else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev, curr = curr, prev
    return prev[lb]

def _norm_iupac_for_compare(s: str | None) -> str | None:
    if not s:
        return None
    t = s.lower()
    t = re.sub(r'[\s\u00A0]+', ' ', t.replace("\n", " ").replace("\t", " ")).strip()
    t = re.sub(r'\s*-\s*', '-', t)
    t = re.sub(r'\s*,\s*', ',', t)
    t = re.sub(r'\s*\(\s*', '(', t)
    t = re.sub(r'\s*\)\s*', ')', t)
    t = t.replace(' ', '')
    t = re.sub(r'(^|,|-|\()l(?=(?:,|\d|-|\)))', lambda m: m.group(1) + '1', t)
    t = re.sub(r'(^|,|-|\()o(?=(?:,|\d|-|\)))', lambda m: m.group(1) + '0', t)
    t = t.replace('yljacetamide', 'yl)acetamide')
    return t

def _similar_enough(a: str | None, b: str | None, threshold: float = 0.85) -> bool:
    if a is None or b is None:
        return a == b
    if a == b:
        return True
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return False
    dist = _levenshtein(a, b)
    sim = 1.0 - dist / max(la, lb)
    return sim >= threshold

def cmp_compound_item_editdistance(a: CompoundTextIdItem, b: CompoundTextIdItem, iupac_sim_threshold: float = 0.9):
    raw_iupac_a = a.iupac_name if getattr(a, 'iupac_name', None) else None
    raw_iupac_b = b.iupac_name if getattr(b, 'iupac_name', None) else None
    iupac_name_a = raw_iupac_a.replace(" ", "").replace("\n", "").lower() if raw_iupac_a else None
    iupac_name_b = raw_iupac_b.replace(" ", "").replace("\n", "").lower() if raw_iupac_b else None

    example_id_a = norm_example_id(getattr(a, 'example_id', None))
    example_id_b = norm_example_id(getattr(b, 'example_id', None))
    compound_id_a = norm_compound_id(getattr(a, 'compound_id', None))
    compound_id_b = norm_compound_id(getattr(b, 'compound_id', None))

    if getattr(a, 'structure', None) != getattr(b, 'structure', None):
        return 1
    elif compound_id_a != compound_id_b:
        return 2
    elif example_id_a != example_id_b:
        return 3

    if iupac_name_a == iupac_name_b:
        return 0

    can_iupac_a = _norm_iupac_for_compare(raw_iupac_a)
    can_iupac_b = _norm_iupac_for_compare(raw_iupac_b)
    if _similar_enough(can_iupac_a, can_iupac_b, threshold=iupac_sim_threshold):
        return 0
    return 4

# ---------- 比较description ----------
def cmp_description_item(a: ReactionStepDescription, b: ReactionStepDescription):
    # iupac name norm
    a_iupac_name_clean = a.iupac_name.replace(" ", "").replace("\n", "") if a.iupac_name else None
    b_iupac_name_clean = b.iupac_name.replace(" ", "").replace("\n", "") if b.iupac_name else None

    # detail norm
    a_detail_clean = a.detail.replace(" ", "").replace("\n", "") if a.detail else None
    b_detail_clean = b.detail.replace(" ", "").replace("\n", "") if b.detail else None

    if a.detail_ids != b.detail_ids: # list vs list
        return 1
    elif a.compound_id != b.compound_id:
        return 2
    elif a.structure_id != b.structure_id:
        return 3
    elif a.refs != b.refs:
        return 4
    elif a_iupac_name_clean != b_iupac_name_clean:
        return 5
    elif a_detail_clean != b_detail_clean:
        return 6
    return 0


# ---------- 错误分析 ----------
def analyze_errors(
        ground_truth_records: List[ReactionStepDescriptionRecord],
        prediction_records: List[ReactionStepDescriptionRecord]
        ) -> List[ComparisonResult]:
    prediction_dict = {record.id: record for record in prediction_records}
    detailed_results: List[ComparisonResult] = []
    error_type_counts = defaultdict(int)

    # ---- 全局累计 ----
    total_tp = 0          # 真正预测正确（cmp==0）的总数
    total_gt = 0          # 全部 GT 的条数
    total_pred = 0        # 全部 PRED 的条数

    print(f"开始错误分析，真实标签记录数: {len(ground_truth_records)}")

    for gt_record in ground_truth_records:
        if gt_record.id not in prediction_dict:
            print(f"警告: 记录ID {gt_record.id} 在预测结果中未找到")
            continue

        pred_record = prediction_dict[gt_record.id]
        gt_descriptions   = conv_output_to_dict(gt_record.output.get("results", []))
        pred_descriptions = conv_output_to_dict(pred_record.predict_output.get("results", []))

        # 可选：确保预测 detail_id 唯一（若上游已保证可省略）
        # pred_descriptions = {k: v for k, v in pred_descriptions.items()}  # 去重占位

        keys_gt = set(gt_descriptions.keys())
        keys_pred = set(pred_descriptions.keys())

        common = keys_gt & keys_pred   # 候选 TP（key 对齐）
        miss   = keys_gt - keys_pred   # FN
        extra  = keys_pred - keys_gt   # FP
        errors: List[ErrorAnalysis] = []

        # ---- 本条样本的局部统计 ----
        tp_strict = 0

        for k in common:
            gt_desc = gt_descriptions[k]
            pred_desc = pred_descriptions[k]
            err = cmp_description_item(gt_desc, pred_desc)
            if err == 0:
                tp_strict += 1
            else:
                errors.append(ErrorAnalysis(detail_id=k, error_type=err,
                                            ground_truth=gt_desc, prediction=pred_desc))
                error_type_counts[err] += 1

        for k in miss:
            errors.append(ErrorAnalysis(detail_id=k, error_type=7,  # 7: 漏检
                                        ground_truth=gt_descriptions[k],
                                        prediction=empty_item(k)))
            error_type_counts[7] += 1

        for k in extra:
            errors.append(ErrorAnalysis(detail_id=k, error_type=8,  # 8: 多检
                                        ground_truth=empty_item(k),
                                        prediction=pred_descriptions[k]))
            error_type_counts[8] += 1

        # ---- 累加到全局（micro 统计）----
        total_tp  += tp_strict
        total_gt  += len(keys_gt)
        total_pred += len(keys_pred)

        # ---- 写入当前样本的对比结果（用“局部”数字）----
        detailed_results.append(ComparisonResult(
            record_id=gt_record.id,
            is_correct=(len(keys_gt) == len(keys_pred) and tp_strict == len(keys_gt)),
            errors=errors,
            item_recall=tp_strict,                 # 本样本真正匹配条数
            item_correct=tp_strict,                # 分子同上
            total_ground_truth_items=len(keys_gt), # 本样本 GT 数
            total_predicted_items=len(keys_pred)   # 本样本 Pred 数
        ))

    print_error_statistics(detailed_results, error_type_counts)
    return detailed_results


def print_error_statistics(
    detailed_results: List[ComparisonResult],
    error_type_counts: Dict[int, int]
):
    total_recall = sum(r.item_recall for r in detailed_results)                 # = 全局 TP
    total_correct = sum(r.item_correct for r in detailed_results)               # = 全局 TP
    total_ground_truth = sum(r.total_ground_truth_items for r in detailed_results)
    total_predicted = sum(r.total_predicted_items for r in detailed_results)
    fully_correct_records = sum(1 for r in detailed_results if r.is_correct)

    # 安全除法
    def safe_ratio(a, b): 
        return (a / b) if b else 0.0

    # micro-averaged Precision / Recall / F1
    precision = safe_ratio(total_correct, total_predicted)  # TP / (TP+FP)
    recall    = safe_ratio(total_recall, total_ground_truth) # TP / (TP+FN)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    print(f"\n=== 错误分析统计 ===")
    print(f"总记录数: {len(detailed_results)}")
    print(f"完全正确记录数: {fully_correct_records}, 比例: {safe_ratio(fully_correct_records, len(detailed_results)):.4f}")
    print(f"召回率 = {total_recall} / {total_ground_truth} => {recall:.4f}")
    print(f"精确率 = {total_correct} / {total_predicted} => {precision:.4f}")
    print(f"F1 = 2 * P * R / (P + R) = {f1:.4f}")
    print(f"正确预测项目数(TP) = {total_correct}")
    print(f"总ground truth项目数 = {total_ground_truth}")
    print(f"总预测项目数 = {total_predicted}")

    print("\n错误类型统计:")
    error_type_names = {
        1: "detail_ids错误",
        2: "compound_id错误",
        3: "structure_id错误",
        4: "refs错误",
        5: "iupac_name错误",
        6: "detail错误",
        7: "detail_ids漏检(FN)",
        8: "detail_ids多检(FP)"
    }
    for et, count in error_type_counts.items():
        print(f"{error_type_names.get(et, f'未知类型({et})')}: {count}次")


def create_error_dataframe(detailed_results: List[ComparisonResult]) -> pd.DataFrame:
    data: List[Dict[str, Any]] = []

    # 与前面统计一致的错误类型含义
    error_type_names = {
        1: "detail_ids错误",
        2: "compound_id错误",
        3: "structure_id错误",
        4: "refs错误",
        5: "iupac_name错误",
        6: "detail错误",
        7: "detail_ids漏检(FN)",
        8: "detail_ids多检(FP)",
    }

    def _join_refs(v):
        if v is None:
            return None
        if isinstance(v, (list, tuple)):
            return "|".join(str(x) for x in v)
        return str(v)

    def _join_detail_ids(v):
        if not v:
            return ""
        return "|".join(str(x) for x in v)

    for result in detailed_results:
        for error in result.errors:
            gt = error.ground_truth
            pr = error.prediction

            # 兼容 empty_item 返回的占位对象：用 getattr 安全取字段
            gt_detail_ids = getattr(gt, "detail_ids", []) or []
            pr_detail_ids = getattr(pr, "detail_ids", []) or []

            row = {
                "record_id": result.record_id,
                "detail_id_key": error.detail_id,  # 你的 ErrorAnalysis 中已存了 key（如 "DETAIL_IDS:..." 或直接 "|"-拼接）
                "error_type": error_type_names.get(error.error_type, f"未知类型({error.error_type})"),

                "ground_truth_structure_id": getattr(gt, "structure_id", "") or "",
                "prediction_structure_id": getattr(pr, "structure_id", "") or "",

                "ground_truth_compound_id": getattr(gt, "compound_id", "") or "",
                "prediction_compound_id": getattr(pr, "compound_id", "") or "",

                "ground_truth_iupac_name": getattr(gt, "iupac_name", "") or "",
                "prediction_iupac_name": getattr(pr, "iupac_name", "") or "",

                "ground_truth_refs": _join_refs(getattr(gt, "refs", None)),
                "prediction_refs": _join_refs(getattr(pr, "refs", None)),

                "ground_truth_detail_ids": _join_detail_ids(gt_detail_ids),
                "prediction_detail_ids": _join_detail_ids(pr_detail_ids),

                # 可辅助定位差异：detail 文本长度
                "ground_truth_detail_len": len(getattr(gt, "detail", "") or ""),
                "prediction_detail_len": len(getattr(pr, "detail", "") or ""),

                # 每条 record 的局部统计（便于透视）
                "item_recall": result.item_recall,
                "item_correct": result.item_correct,
                "total_ground_truth_items": result.total_ground_truth_items,
                "total_predicted_items": result.total_predicted_items,
            }
            data.append(row)

    return pd.DataFrame(data)


# ---------- I/O ----------
def load_records_from_json_file(json_file_path: str) -> List[ReactionStepDescriptionRecord]:
    """
    读取 JSON（数组） -> List[ReactionStepDescriptionRecord]
    """
    records: List[ReactionStepDescriptionRecord] = []
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        records.append(ReactionStepDescriptionRecord(
            id=item.get('id'),
            input=item.get('input'),
            output=item.get('output'),
            predict_output=item.get('predict_output', []),
            llm_response=item.get('llm_response', ''),
            model=item.get('model', ''),
            status=item.get('status', ''),
            name=item.get('name', ''),
            header_name=item.get('header_name', '')
        ))
    return records

def _compute_stats_from_detailed(detailed_results: List[ComparisonResult]) -> Dict[str, Any]:
    total_recall = sum(r.item_recall for r in detailed_results)
    total_correct = sum(r.item_correct for r in detailed_results)
    total_ground_truth = sum(r.total_ground_truth_items for r in detailed_results)
    total_predicted = sum(r.total_predicted_items for r in detailed_results)
    fully_correct_records = sum(1 for r in detailed_results if r.is_correct)

    recall_rate = (total_recall / total_ground_truth) if total_ground_truth else 0.0
    precision_rate = (total_correct / total_predicted) if total_predicted else 0.0
    fully_correct_ratio = (fully_correct_records / len(detailed_results)) if detailed_results else 0.0

    return {
        "num_records": len(detailed_results),
        "fully_correct_records": fully_correct_records,
        "fully_correct_ratio": round(fully_correct_ratio, 6),
        "total_recall": total_recall,
        "total_ground_truth": total_ground_truth,
        "recall_rate": round(recall_rate, 6),
        "total_correct": total_correct,
        "total_predicted": total_predicted,
        "precision_rate": round(precision_rate, 6),
    }

def run_error_eval_like_test_eval(
    input_infer_res_dirpath: str,            # 放 AssayInfoChatAgent_{llm_name}.json 的目录
    output_dirpath: str,              # 输出目录
    llm_names: List[str],             # 模型名列表
    sft_param_key: str | None = None, # 任务后缀（可选）
    loader_fn = load_records_from_json_file
):
    """
    test_eval 风格的一站式错误评测：
      - 读 GT 与各模型预测
      - analyze_errors / create_error_dataframe
      - 输出每模型 report/CSV/Excel + 跨模型 all_stats.xlsx
    """
    assert callable(loader_fn), "loader_fn 必须是可调用的加载函数"

    os.makedirs(output_dirpath, exist_ok=True)

    all_stats: List[Dict[str, Any]] = []

    for llm_name in llm_names:
        # 支持eval多个llm
        pred_filepath = os.path.join(input_infer_res_dirpath, f"PatentSynthesisRouteAgent_{llm_name}.json")
        if not os.path.exists(pred_filepath):
            print(f"[WARN] 预测文件不存在：{pred_filepath}，跳过该模型")
            continue

        print(f">>>>> [LOAD] prediction FROM {pred_filepath}")
        gt_records = pred_records = loader_fn(pred_filepath)  # ✅ 返回 List[LabelTextCompoundIdRecord]

        detailed_results = analyze_errors(gt_records, pred_records)
        error_df = create_error_dataframe(detailed_results)

        # 下面的部分都是直接可用
        stats = _compute_stats_from_detailed(detailed_results)
        stats["model_name"] = llm_name
        stats["task_name"] = f"ErrorEval_{llm_name}" + (f"_{sft_param_key}" if sft_param_key else "")
        if sft_param_key:
            stats["sft_param_key"] = sft_param_key

        # 文本报告
        report_txt = os.path.join(output_dirpath, f"report_ErrorEval_{llm_name}.txt")
        with open(report_txt, "w", encoding="utf-8") as f:
            f.write(json.dumps(stats, ensure_ascii=False, indent=2))
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        print("-" * 180)

        # 错误明细 CSV
        error_csv = os.path.join(output_dirpath, f"ErrorDetails_{llm_name}.csv")
        error_df.to_csv(error_csv, index=False, encoding="utf-8")

        # Excel（两个 sheet）
        excel_path = os.path.join(output_dirpath, f"ErrorEval_{llm_name}.xlsx")
        df_stats = pd.DataFrame([stats])
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            error_df.to_excel(writer, sheet_name="错误明细", index=False)
            df_stats.to_excel(writer, sheet_name="总体统计", index=False)

        all_stats.append(stats)

    # 跨模型汇总
    if all_stats:
        all_stats_xlsx = os.path.join(output_dirpath, "all_stats.xlsx")
        df_all = pd.DataFrame(all_stats)
        with pd.ExcelWriter(all_stats_xlsx, engine="openpyxl") as writer:
            df_all.to_excel(writer, sheet_name="综合评估", index=False)
    else:
        print("[WARN] 没有任何模型完成评测，未生成 all_stats.xlsx")


if __name__ == "__main__":

    # json_filepathes = [
    #     # 'infer_res/text_compound_id/TextCompoundIdChatAgent_DS_14B.jsonl',
    #     # 'infer_res/text_compound_id/TextCompoundIdChatAgent_DS_32B.jsonl',
    #     # 'infer_res/text_compound_id/TextCompoundIdChatAgent_PHI4_14B.jsonl',
    #     # 'infer_res/text_compound_id/TextCompoundIdChatAgent_PHI4_MINI.jsonl',
    #     # 'infer_res/text_compound_id/TextCompoundIdChatAgent_QWEN25_7B.jsonl',
    #     # 'infer_res/text_compound_id/TextCompoundIdChatAgent_QWEN25_14B.jsonl',
    #     # 'infer_res/text_compound_id/TextCompoundIdChatAgent_QWEN25_32B.jsonl',
    #     # 'infer_res/text_compound_id/TextCompoundIdChatAgent_gpt-4o.jsonl',
    #     'infer_res/text_compound_id/TextCompoundIdChatAgent_QWQ_32B.jsonl',
    #     'infer_res/text_compound_id/TextCompoundIdChatAgent_DS_R1.jsonl',
    # ]

    # for json_filepath in json_filepathes:
    #     text_compound_eval(json_filepath)
    #     print('-' * 160)
    pass