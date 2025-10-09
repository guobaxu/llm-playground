import os
import time
import json
from typing import List

from llm_playground.inference import InferenceRunner
from llm_playground.core.models import (
    QWEN25_14B_LLM_NAME,
    GPT_4_LLM_NAME,
    GPT_4O_LLM_NAME
)
# task4
from llm_playground.agents.synthesis_route_desc_agents import PatentSynthesisRouteAgent
from llm_playground.datamodel.synthesis_route import ReactionStepDescriptionRecord
from llm_playground.eval.synthesis_route_desc_eval import run_error_eval_like_test_eval



def load_json_data(json_file_path: str):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def convert_to_records(data) -> List[ReactionStepDescriptionRecord]:
    """
    将JSON数据转换为ReactionStepDescriptionRecord格式
    Args:
        data: JSON数据列表
    Returns:
        ReactionStepDescriptionRecord列表
    """
    records = []
    for item in data:
        # 创建记录对象
        record = ReactionStepDescriptionRecord(
            id=item.get('id'),
            input=item.get('input'),
            output=item.get('output'),
            predict_output={},
            llm_response='',
            model='',
            status='',
            name='',
            header_name=''
        )
        records.append(record)
    return records

def infer_and_eval(sft_param_key:str,
                   infer_output_dirpath:str,
                   eval_output_dirpath:str,
                   llm_name:str,
                   only_eval=False):
    if not only_eval:
        # agents
        agents = [PatentSynthesisRouteAgent(llm_name)]

        # data
        data = load_json_data('data/synthesis_route_desc/qa_reaction_desc_inout_total41.json')
        print(f"\n>>>>>>>加载 {len(data)} 条数据")
        print("\n>>>>>>>转换数据格式...")
        records = convert_to_records(data)

        # check dirpath
        if not os.path.exists(infer_output_dirpath):
            os.makedirs(infer_output_dirpath)
        
        # infer
        ir = InferenceRunner(
            agents=agents, output_dirpath=infer_output_dirpath,
            records=records, is_appending=False)
        ir.run_in_multithread(max_batch_size=20)
        time.sleep(15)
    
    # eval
    if not os.path.exists(eval_output_dirpath):
            os.makedirs(eval_output_dirpath)
    run_error_eval_like_test_eval(input_infer_res_dirpath=infer_output_dirpath,
                                output_dirpath=eval_output_dirpath,
                                llm_names=[
                                    llm_name
                                ],
                                sft_param_key=sft_param_key)


if __name__ == "__main__":
    # sft_param_key = '64_128_0_5.0e-5_all'
    # infer_and_eval(sft_param_key=sft_param_key, 
    #                 infer_output_dirpath = 'infer_res_delivery/text_compound/',
    #                 eval_output_dirpath = 'eval_res_delivery/text_compound/',
    #                 llm_name=QWEN25_14B_LLM_NAME)
    
    infer_and_eval(sft_param_key='', 
                    infer_output_dirpath = 'infer_res_delivery/synthesis_route_desc/',
                    eval_output_dirpath = 'eval_res_delivery/synthesis_route_desc/',
                    llm_name=GPT_4O_LLM_NAME,
                    only_eval=False)
    