#!/usr/bin/env python3
"""
Excel批量查询示例

演示如何使用批量Excel查询功能
"""

import pandas as pd
from batch_excel_query import BatchExcelQuery
import os


def create_sample_excel():
    """创建示例Excel文件"""
    sample_data = {
        "question": [
            "入选标准是什么？",
            "如何申请？",
            "需要准备哪些材料？",
            "申请流程是怎样的？",
            "审核时间需要多久？"
        ],
        "answer": [""] * 5  # 空的答案列
    }
    
    df = pd.DataFrame(sample_data)
    output_file = "sample_questions.xlsx"
    df.to_excel(output_file, index=False)
    print(f"已创建示例Excel文件: {output_file}")
    return output_file


def main():
    """主函数"""
    print("Excel批量查询示例")
    print("=" * 50)
    
    # 创建示例Excel文件
    sample_file = create_sample_excel()
    
    # 创建批量查询处理器
    processor = BatchExcelQuery(
        chat_session_id="1222121",
        kb_ids=["cde133cf85a543648c3947c35a556040"]
    )
    
    try:
        # 处理Excel文件
        output_file = processor.process_excel(
            input_file=sample_file,
            question_column="question",
            answer_column="answer",
            delay_seconds=0.5  # 减少延迟用于演示
        )
        
        print(f"\n处理完成! 结果文件: {output_file}")
        
        # 显示结果
        result_df = pd.read_excel(output_file)
        print("\n处理结果:")
        print("-" * 50)
        for i, row in result_df.iterrows():
            print(f"问题 {i+1}: {row['question']}")
            print(f"答案 {i+1}: {row['answer'][:100]}...")
            print("-" * 30)
            
    except Exception as e:
        print(f"处理失败: {e}")


if __name__ == "__main__":
    main()
