#!/usr/bin/env python3
"""
异步批量Excel查询脚本 - 高性能版本

支持并发处理、智能延迟控制、批量优化等功能
"""

import pandas as pd
import sys
import os
import asyncio
import aiohttp
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import time
from datetime import datetime
from dataclasses import dataclass
import logging
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor
import threading

# 添加AZ_KB目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'AZ_KB'))
from rag_chat_client import RAGChatClient


@dataclass
class QueryResult:
    """查询结果数据类"""
    row_index: int
    question: str
    answer: str
    success: bool
    error_msg: Optional[str] = None
    response_time: float = 0.0


class AsyncBatchExcelQuery:
    """异步批量Excel查询处理器"""
    
    def __init__(
        self, 
        chat_session_id: str = "1222121",
        kb_ids: List[str] = None,
        base_url: str = "http://39.106.153.140:8999",
        max_concurrent: int = 10,
        adaptive_delay: bool = True,
        log_level: str = "INFO",
        log_file: Optional[str] = None
    ):
        """
        初始化异步批量查询处理器
        
        Args:
            chat_session_id: 聊天会话ID
            kb_ids: 知识库ID列表
            base_url: API基础URL
            max_concurrent: 最大并发数
            adaptive_delay: 是否启用自适应延迟
            log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
            log_file: 日志文件路径，如果为None则自动生成
        """
        if kb_ids is None:
            kb_ids = ["cde133cf85a543648c3947c35a556040"]
            
        self.chat_session_id = chat_session_id
        self.kb_ids = kb_ids
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.adaptive_delay = adaptive_delay
        
        # 性能统计
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_time': 0.0,
            'avg_response_time': 0.0
        }
        
        # 延迟控制
        self.base_delay = 0.1  # 基础延迟（秒）
        self.max_delay = 2.0   # 最大延迟（秒）
        self.current_delay = self.base_delay
        
        # 设置日志
        if log_file is None:
            log_filename = f"async_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        else:
            log_filename = log_file
        
        # 创建logger
        self.logger = logging.getLogger(__name__)
        log_level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR
        }
        self.logger.setLevel(log_level_map.get(log_level.upper(), logging.INFO))
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # 文件处理器（带轮转）
        file_handler = RotatingFileHandler(
            log_filename, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
        # 防止日志重复
        self.logger.propagate = False
        
        self.logger.info(f"日志系统初始化完成，日志文件: {log_filename}")
        print(f"日志文件: {log_filename}")  # 在控制台显示日志文件路径
    
    async def _query_single_async(
        self, 
        session: aiohttp.ClientSession,
        question: str,
        row_index: int,
        semaphore: asyncio.Semaphore
    ) -> QueryResult:
        """
        异步查询单个问题
        
        Args:
            session: aiohttp会话
            question: 问题文本
            row_index: 行索引
            semaphore: 并发控制信号量
            
        Returns:
            QueryResult: 查询结果
        """
        async with semaphore:
            start_time = time.time()
            
            try:
                # 构建请求URL和载荷
                url = f"{self.base_url}/api/v1/rag/chat/multiple_kb/{self.chat_session_id}"
                payload = {
                    "history": [],
                    "kb_ids": self.kb_ids,
                    "query": question
                }
                
                # 发送异步请求
                async with session.post(
                    url, 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)  # 增加超时时间
                ) as response:
                    response.raise_for_status()
                    
                    # 处理流式响应
                    full_response = ""
                    line_count = 0
                    async for line in response.content:
                        line_count += 1
                        try:
                            line_str = line.decode('utf-8').strip()
                            if line_str:
                                if line_str.startswith('data: '):
                                    data_str = line_str[6:]
                                    try:
                                        data = json.loads(data_str)
                                        if data.get('sse_type') == 'stage1_message':
                                            content = data.get('message', {}).get('content', '')
                                            if content:
                                                full_response += content
                                    except json.JSONDecodeError as e:
                                        self.logger.debug(f"JSON解析错误 (data:): {e}, 数据: {data_str[:100]}")
                                        continue
                                else:
                                    try:
                                        data = json.loads(line_str)
                                        if data.get('sse_type') == 'stage1_message':
                                            content = data.get('message', {}).get('content', '')
                                            if content:
                                                full_response += content
                                    except json.JSONDecodeError as e:
                                        self.logger.debug(f"JSON解析错误: {e}, 数据: {line_str[:100]}")
                                        continue
                        except UnicodeDecodeError as e:
                            self.logger.debug(f"Unicode解码错误: {e}")
                            continue
                    
                    # 检查是否收到任何有效响应
                    if not full_response and line_count > 0:
                        self.logger.warning(f"收到 {line_count} 行响应但内容为空")
                
                response_time = time.time() - start_time
                
                # 更新统计信息
                self.stats['total_requests'] += 1
                self.stats['successful_requests'] += 1
                
                # 自适应延迟调整
                if self.adaptive_delay:
                    self._adjust_delay(response_time)
                
                return QueryResult(
                    row_index=row_index,
                    question=question,
                    answer=full_response,
                    success=True,
                    response_time=response_time
                )
                
            except Exception as e:
                response_time = time.time() - start_time
                self.stats['total_requests'] += 1
                self.stats['failed_requests'] += 1
                
                # 更详细的错误信息
                error_type = type(e).__name__
                error_msg = str(e) if str(e) else f"{error_type}: 未知错误"
                detailed_error = f"{error_type}: {error_msg}"
                
                self.logger.error(f"第 {row_index + 1} 行查询失败: {detailed_error}")
                self.logger.debug(f"问题内容: {question[:100]}...")
                
                return QueryResult(
                    row_index=row_index,
                    question=question,
                    answer="",
                    success=False,
                    error_msg=detailed_error,
                    response_time=response_time
                )
    
    def _adjust_delay(self, response_time: float):
        """自适应调整延迟时间"""
        if response_time > 5.0:  # 响应时间过长，增加延迟
            self.current_delay = min(self.current_delay * 1.2, self.max_delay)
        elif response_time < 1.0:  # 响应时间较短，减少延迟
            self.current_delay = max(self.current_delay * 0.9, self.base_delay)
    
    async def test_single_query(self, question: str) -> QueryResult:
        """
        测试单个查询，用于调试
        
        Args:
            question: 测试问题
            
        Returns:
            QueryResult: 查询结果
        """
        self.logger.info(f"测试查询: {question}")
        self.logger.info(f"API URL: {self.base_url}/api/v1/rag/chat/multiple_kb/{self.chat_session_id}")
        self.logger.info(f"知识库ID: {self.kb_ids}")
        self.logger.info("-" * 50)
        
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(1)
            result = await self._query_single_async(session, question, 0, semaphore)
            
            self.logger.info(f"查询结果: {result.success}")
            self.logger.info(f"响应时间: {result.response_time:.2f}s")
            if result.success:
                self.logger.info(f"答案长度: {len(result.answer)} 字符")
                self.logger.info(f"答案预览: {result.answer[:200]}...")
            else:
                self.logger.error(f"错误信息: {result.error_msg}")
            
            return result
    
    async def process_excel_async(
        self, 
        input_file: str, 
        output_file: Optional[str] = None,
        question_column: str = "question",
        answer_column: str = "answer",
        start_row: int = 0,
        max_rows: Optional[int] = None,
        save_interval: int = 50,
        overwrite_source: bool = False
    ) -> str:
        """
        异步处理Excel文件
        
        Args:
            input_file: 输入Excel文件路径
            output_file: 输出Excel文件路径
            question_column: 问题列名
            answer_column: 答案列名
            start_row: 开始处理的行号
            max_rows: 最大处理行数
            save_interval: 保存间隔
            overwrite_source: 是否覆盖源文件
            
        Returns:
            str: 输出文件路径
        """
        self.logger.info(f"开始异步处理Excel文件: {input_file}")
        self.logger.info(f"最大并发数: {self.max_concurrent}")
        self.logger.info(f"自适应延迟: {'启用' if self.adaptive_delay else '禁用'}")
        self.logger.info("-" * 50)
        
        # 读取Excel文件
        try:
            df = pd.read_excel(input_file)
            self.logger.info(f"成功读取Excel文件，共 {len(df)} 行数据")
        except Exception as e:
            self.logger.error(f"读取Excel文件失败: {e}")
            raise
        
        # 检查列是否存在
        if question_column not in df.columns:
            raise ValueError(f"找不到问题列 '{question_column}'")
        
        if answer_column not in df.columns:
            df[answer_column] = ""
            self.logger.info(f"创建答案列: {answer_column}")
        
        # 确定处理范围
        end_row = len(df)
        if max_rows:
            end_row = min(start_row + max_rows, len(df))
        
        self.logger.info(f"将处理第 {start_row + 1} 到第 {end_row} 行")
        self.logger.info("-" * 50)
        
        # 准备查询任务
        tasks = []
        questions = []
        
        for i in range(start_row, end_row):
            question = df.iloc[i][question_column]
            
            # 跳过空问题
            if pd.isna(question) or str(question).strip() == "":
                continue
            
            questions.append((i, str(question).strip()))
        
        self.logger.info(f"准备处理 {len(questions)} 个有效问题")
        
        # 确定输出文件路径
        if overwrite_source:
            output_file = input_file
        elif output_file is None:
            input_path = Path(input_file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = input_path.parent / f"{input_path.stem}_async_processed_{timestamp}{input_path.suffix}"
        
        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # 开始处理
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            # 分批处理，避免内存占用过大
            batch_size = 100
            processed_count = 0
            
            for batch_start in range(0, len(questions), batch_size):
                batch_end = min(batch_start + batch_size, len(questions))
                batch_questions = questions[batch_start:batch_end]
                
                self.logger.info(f"处理批次 {batch_start//batch_size + 1}: 第 {batch_start + 1} 到第 {batch_end} 个问题")
                
                # 创建当前批次的任务
                batch_tasks = []
                for row_index, question in batch_questions:
                    task = self._query_single_async(session, question, row_index, semaphore)
                    batch_tasks.append(task)
                
                # 并发执行当前批次
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # 处理结果
                for result in batch_results:
                    if isinstance(result, Exception):
                        self.logger.error(f"任务执行异常: {result}")
                        continue
                    
                    # 更新DataFrame
                    if result.success:
                        df.iloc[result.row_index, df.columns.get_loc(answer_column)] = result.answer
                        self.logger.info(f"第 {result.row_index + 1} 行: 成功 ({result.response_time:.2f}s)")
                    else:
                        error_msg = f"错误: {result.error_msg}"
                        df.iloc[result.row_index, df.columns.get_loc(answer_column)] = error_msg
                        self.logger.error(f"第 {result.row_index + 1} 行: {error_msg}")
                
                processed_count += len(batch_questions)
                
                # 定期保存
                if processed_count % save_interval == 0:
                    df.to_excel(output_file, index=False)
                    self.logger.info(f"已保存进度到: {output_file} (已处理 {processed_count} 个问题)")
                
                # 批次间短暂延迟
                if batch_end < len(questions):
                    await asyncio.sleep(0.1)
        
        # 最终保存
        df.to_excel(output_file, index=False)
        
        # 计算统计信息
        end_time = time.time()
        self.stats['total_time'] = end_time - start_time
        
        if self.stats['successful_requests'] > 0:
            self.stats['avg_response_time'] = sum(
                r.response_time for r in batch_results 
                if hasattr(r, 'response_time') and r.success
            ) / self.stats['successful_requests']
        
        # 输出统计信息
        self.logger.info("-" * 50)
        self.logger.info("异步处理完成!")
        self.logger.info(f"总处理问题数: {len(questions)}")
        self.logger.info(f"成功: {self.stats['successful_requests']}")
        self.logger.info(f"失败: {self.stats['failed_requests']}")
        self.logger.info(f"总耗时: {self.stats['total_time']:.2f} 秒")
        self.logger.info(f"平均响应时间: {self.stats['avg_response_time']:.2f} 秒")
        self.logger.info(f"平均每问题: {self.stats['total_time'] / len(questions):.2f} 秒")
        self.logger.info(f"并发效率: {len(questions) / self.stats['total_time']:.2f} 问题/秒")
        self.logger.info(f"结果已保存到: {output_file}")
        
        return str(output_file)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="异步批量Excel查询工具")
    parser.add_argument("input_file", help="输入Excel文件路径")
    parser.add_argument("-o", "--output", help="输出Excel文件路径")
    parser.add_argument("-q", "--question-column", default="Question", help="问题列名")
    parser.add_argument("-a", "--answer-column", default="AI_Response（加入了父子chunk，summary等trick）", help="答案列名")
    parser.add_argument("-s", "--start-row", type=int, default=0, help="开始行号（0-based）")
    parser.add_argument("-m", "--max-rows", type=int, help="最大处理行数")
    parser.add_argument("-c", "--concurrent", type=int, default=10, help="最大并发数")
    parser.add_argument("--session-id", default="1222121", help="聊天会话ID")
    parser.add_argument("--kb-ids", nargs="+", default=["cde133cf85a543648c3947c35a556040"], help="知识库ID列表")
    parser.add_argument("--save-interval", type=int, default=50, help="每N个问题保存一次进度")
    parser.add_argument("--overwrite", action="store_true", help="直接覆盖源文件")
    parser.add_argument("--no-adaptive-delay", action="store_true", help="禁用自适应延迟")
    parser.add_argument("--test-query", help="测试单个查询（不处理Excel文件）")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help="日志级别")
    parser.add_argument("--log-file", help="日志文件路径（默认为自动生成）")
    
    args = parser.parse_args()
    
    # 创建异步处理器
    processor = AsyncBatchExcelQuery(
        chat_session_id=args.session_id,
        kb_ids=args.kb_ids,
        max_concurrent=args.concurrent,
        adaptive_delay=not args.no_adaptive_delay,
        log_level=args.log_level,
        log_file=args.log_file
    )
    
    try:
        # 如果指定了测试查询，则只测试单个查询
        if args.test_query:
            result = asyncio.run(processor.test_single_query(args.test_query))
            if result.success:
                processor.logger.info(f"测试成功! 答案: {result.answer}")
            else:
                processor.logger.error(f"测试失败: {result.error_msg}")
                sys.exit(1)
        else:
            # 运行异步处理
            output_file = asyncio.run(processor.process_excel_async(
                input_file=args.input_file,
                output_file=args.output,
                question_column=args.question_column,
                answer_column=args.answer_column,
                start_row=args.start_row,
                max_rows=args.max_rows,
                save_interval=args.save_interval,
                overwrite_source=args.overwrite
            ))
            
            processor.logger.info(f"处理完成! 结果文件: {output_file}")
        
    except Exception as e:
        # 创建临时logger用于错误记录
        temp_logger = logging.getLogger(__name__)
        temp_logger.error(f"处理失败: {e}")
        import traceback
        temp_logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
