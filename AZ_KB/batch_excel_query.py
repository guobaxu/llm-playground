#!/usr/bin/env python3
"""
批量Excel查询脚本

从Excel文件读取question列，批量调用RAG API，将完整答案写入Excel
"""

import pandas as pd
import sys
import os
from pathlib import Path
from typing import List, Optional
import time
from datetime import datetime

# 添加AZ_KB目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'AZ_KB'))
from rag_chat_client import RAGChatClient


class BatchExcelQuery:
    """批量Excel查询处理器"""
    
    def __init__(
        self, 
        chat_session_id: str = "1222121",
        kb_ids: List[str] = None,
        base_url: str = "http://39.106.153.140:8999"
    ):
        """
        初始化批量查询处理器
        
        Args:
            chat_session_id: 聊天会话ID
            kb_ids: 知识库ID列表
            base_url: API基础URL
        """
        if kb_ids is None:
            kb_ids = ["cde133cf85a543648c3947c35a556040"]
            
        self.chat_session_id = chat_session_id
        self.kb_ids = kb_ids
        self.client = RAGChatClient(base_url)
        
    def process_excel(
        self, 
        input_file: str, 
        output_file: Optional[str] = None,
        question_column: str = "question",
        answer_column: str = "answer",
        start_row: int = 0,
        max_rows: Optional[int] = None,
        delay_seconds: float = 1.0,
        overwrite_source: bool = False
    ) -> str:
        """
        处理Excel文件，批量查询并写入答案
        
        Args:
            input_file: 输入Excel文件路径
            output_file: 输出Excel文件路径，如果为None则生成新文件名
            question_column: 问题列名
            answer_column: 答案列名
            start_row: 开始处理的行号（0-based）
            max_rows: 最大处理行数，None表示处理所有行
            delay_seconds: 每次请求之间的延迟秒数
            overwrite_source: 是否直接覆盖源文件
            
        Returns:
            str: 输出文件路径
        """
        print(f"开始处理Excel文件: {input_file}")
        print(f"问题列: {question_column}")
        print(f"答案列: {answer_column}")
        print(f"开始行: {start_row}")
        print(f"最大行数: {max_rows if max_rows else '全部'}")
        print(f"请求延迟: {delay_seconds}秒")
        print("-" * 50)
        
        # 读取Excel文件
        try:
            df = pd.read_excel(input_file)
            print(f"成功读取Excel文件，共 {len(df)} 行数据")
        except Exception as e:
            print(f"读取Excel文件失败: {e}")
            raise
        
        # 检查列是否存在
        if question_column not in df.columns:
            print(f"错误: 找不到问题列 '{question_column}'")
            print(f"可用列: {list(df.columns)}")
            raise ValueError(f"找不到问题列 '{question_column}'")
        
        # 如果答案列不存在，创建它
        if answer_column not in df.columns:
            df[answer_column] = ""
            print(f"创建答案列: {answer_column}")
        
        # 确定处理范围
        end_row = len(df)
        if max_rows:
            end_row = min(start_row + max_rows, len(df))
        
        print(f"将处理第 {start_row + 1} 到第 {end_row} 行")
        print("-" * 50)
        
        # 统计信息
        success_count = 0
        error_count = 0
        start_time = time.time()
        
        # 批量处理
        for i in range(start_row, end_row):
            question = df.iloc[i][question_column]
            
            # 跳过空问题
            if pd.isna(question) or str(question).strip() == "":
                print(f"第 {i + 1} 行: 跳过空问题")
                continue
            
            print(f"第 {i + 1} 行: 处理问题 - {str(question)[:50]}...")
            
            try:
                # 调用RAG API
                answer = self.client.chat_with_kb_simple(
                    chat_session_id=self.chat_session_id,
                    query=str(question).strip(),
                    kb_ids=self.kb_ids
                )
                
                # 写入答案
                df.iloc[i, df.columns.get_loc(answer_column)] = answer
                success_count += 1
                print(f"第 {i + 1} 行: 成功获取答案 ({len(answer)} 字符)")
                
            except Exception as e:
                error_count += 1
                error_msg = f"错误: {str(e)}"
                df.iloc[i, df.columns.get_loc(answer_column)] = error_msg
                print(f"第 {i + 1} 行: {error_msg}")
            
            # 添加延迟避免请求过于频繁
            if delay_seconds > 0 and i < end_row - 1:
                time.sleep(delay_seconds)
        
        # 确定输出文件路径
        if overwrite_source:
            output_file = input_file
            print(f"将直接覆盖源文件: {output_file}")
        elif output_file is None:
            # 生成带时间戳的输出文件名
            input_path = Path(input_file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = input_path.parent / f"{input_path.stem}_processed_{timestamp}{input_path.suffix}"
        
        # 保存结果
        try:
            df.to_excel(output_file, index=False)
            print(f"结果已保存到: {output_file}")
        except Exception as e:
            print(f"保存Excel文件失败: {e}")
            raise
        
        # 输出统计信息
        end_time = time.time()
        duration = end_time - start_time
        
        print("-" * 50)
        print("处理完成!")
        print(f"总处理行数: {end_row - start_row}")
        print(f"成功: {success_count}")
        print(f"失败: {error_count}")
        print(f"耗时: {duration:.2f} 秒")
        print(f"平均每行: {duration / (end_row - start_row):.2f} 秒")
        
        return str(output_file)
    
    def process_excel_with_progress(
        self, 
        input_file: str, 
        output_file: Optional[str] = None,
        question_column: str = "question",
        answer_column: str = "answer",
        start_row: int = 0,
        max_rows: Optional[int] = None,
        delay_seconds: float = 1.0,
        save_interval: int = 10,
        overwrite_source: bool = False
    ) -> str:
        """
        带进度保存的Excel处理（每处理N行自动保存一次）
        
        Args:
            save_interval: 每处理多少行保存一次
            overwrite_source: 是否直接覆盖源文件
        """
        print(f"开始处理Excel文件（每 {save_interval} 行保存一次）: {input_file}")
        
        # 读取Excel文件
        df = pd.read_excel(input_file)
        
        # 检查列是否存在
        if question_column not in df.columns:
            raise ValueError(f"找不到问题列 '{question_column}'")
        
        if answer_column not in df.columns:
            df[answer_column] = ""
        
        # 确定处理范围
        end_row = len(df)
        if max_rows:
            end_row = min(start_row + max_rows, len(df))
        
        # 确定输出文件路径
        if overwrite_source:
            output_file = input_file
            print(f"将直接覆盖源文件: {output_file}")
        elif output_file is None:
            input_path = Path(input_file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = input_path.parent / f"{input_path.stem}_processed_{timestamp}{input_path.suffix}"
        
        success_count = 0
        error_count = 0
        start_time = time.time()
        
        for i in range(start_row, end_row):
            question = df.iloc[i][question_column]
            
            if pd.isna(question) or str(question).strip() == "":
                continue
            
            print(f"第 {i + 1} 行: 处理问题 - {str(question)[:50]}...")
            
            try:
                answer = self.client.chat_with_kb_simple(
                    chat_session_id=self.chat_session_id,
                    query=str(question).strip(),
                    kb_ids=self.kb_ids
                )
                
                df.iloc[i, df.columns.get_loc(answer_column)] = answer
                success_count += 1
                print(f"第 {i + 1} 行: 成功获取答案")
                
            except Exception as e:
                error_count += 1
                error_msg = f"错误: {str(e)}"
                df.iloc[i, df.columns.get_loc(answer_column)] = error_msg
                print(f"第 {i + 1} 行: {error_msg}")
            
            # 定期保存
            if (i + 1) % save_interval == 0:
                df.to_excel(output_file, index=False)
                print(f"已保存进度到: {output_file} (第 {i + 1} 行)")
            
            if delay_seconds > 0 and i < end_row - 1:
                time.sleep(delay_seconds)
        
        # 最终保存
        df.to_excel(output_file, index=False)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("-" * 50)
        print("处理完成!")
        print(f"总处理行数: {end_row - start_row}")
        print(f"成功: {success_count}")
        print(f"失败: {error_count}")
        print(f"耗时: {duration:.2f} 秒")
        print(f"结果已保存到: {output_file}")
        
        return str(output_file)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="批量Excel查询工具")
    parser.add_argument("input_file", help="输入Excel文件路径")
    parser.add_argument("-o", "--output", help="输出Excel文件路径")
    parser.add_argument("-q", "--question-column", default="question", help="问题列名")
    parser.add_argument("-a", "--answer-column", default="answer", help="答案列名")
    parser.add_argument("-s", "--start-row", type=int, default=0, help="开始行号（0-based）")
    parser.add_argument("-m", "--max-rows", type=int, help="最大处理行数")
    parser.add_argument("-d", "--delay", type=float, default=1.0, help="请求延迟秒数")
    parser.add_argument("--session-id", default="1222121", help="聊天会话ID")
    parser.add_argument("--kb-ids", nargs="+", default=["cde133cf85a543648c3947c35a556040"], help="知识库ID列表")
    parser.add_argument("--progress-save", type=int, help="每N行保存一次进度")
    parser.add_argument("--overwrite", action="store_true", help="直接覆盖源文件")
    
    args = parser.parse_args()
    
    # 创建处理器
    processor = BatchExcelQuery(
        chat_session_id=args.session_id,
        kb_ids=args.kb_ids
    )
    
    try:
        if args.progress_save:
            # 使用进度保存模式
            output_file = processor.process_excel_with_progress(
                input_file=args.input_file,
                output_file=args.output,
                question_column=args.question_column,
                answer_column=args.answer_column,
                start_row=args.start_row,
                max_rows=args.max_rows,
                delay_seconds=args.delay,
                save_interval=args.progress_save,
                overwrite_source=args.overwrite
            )
        else:
            # 使用普通模式
            output_file = processor.process_excel(
                input_file=args.input_file,
                output_file=args.output,
                question_column=args.question_column,
                answer_column=args.answer_column,
                start_row=args.start_row,
                max_rows=args.max_rows,
                delay_seconds=args.delay,
                overwrite_source=args.overwrite
            )
        
        print(f"\n处理完成! 结果文件: {output_file}")
        
    except Exception as e:
        print(f"处理失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
