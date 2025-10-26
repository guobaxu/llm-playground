#!/usr/bin/env python3
"""
RAG聊天客户端 - 实现多知识库聊天API调用

这个脚本实现了对RAG聊天API的调用，支持流式响应处理
"""

import requests
import json
import time
from typing import Dict, List, Optional, Generator
from dataclasses import dataclass


@dataclass
class RAGMessage:
    """RAG消息数据类"""
    role: str
    type: str
    content: str


@dataclass
class RAGResponse:
    """RAG响应数据类"""
    sse_type: str
    chat_session_id: str
    message: RAGMessage


class RAGChatClient:
    """RAG聊天客户端"""
    
    def __init__(self, base_url: str = "http://39.106.153.140:8999"):
        """
        初始化RAG聊天客户端
        
        Args:
            base_url: API基础URL
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def chat_with_kb(
        self, 
        chat_session_id: str,
        query: str,
        kb_ids: List[str],
        history: Optional[List[Dict]] = None
    ) -> Generator[RAGResponse, None, None]:
        """
        与知识库进行聊天对话
        
        Args:
            chat_session_id: 聊天会话ID
            query: 用户查询
            kb_ids: 知识库ID列表
            history: 历史对话记录，默认为空列表
            
        Yields:
            RAGResponse: 流式响应数据
        """
        if history is None:
            history = []
            
        url = f"{self.base_url}/api/v1/rag/chat/multiple_kb/{chat_session_id}"
        
        payload = {
            "history": history,
            "kb_ids": kb_ids,
            "query": query
        }
        
        try:
            # 发送POST请求，启用流式响应
            response = self.session.post(
                url, 
                json=payload, 
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            # 处理流式响应
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    # 处理SSE格式的数据
                    if line.startswith('data: '):
                        data_str = line[6:]  # 移除 'data: ' 前缀
                        try:
                            data = json.loads(data_str)
                            yield self._parse_response(data)
                        except json.JSONDecodeError as e:
                            print(f"JSON解析错误: {e}, 原始数据: {data_str}")
                    else:
                        # 直接处理JSON数据
                        try:
                            data = json.loads(line)
                            yield self._parse_response(data)
                        except json.JSONDecodeError as e:
                            print(f"JSON解析错误: {e}, 原始数据: {line}")
                            
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            raise
    
    def _parse_response(self, data: Dict) -> RAGResponse:
        """
        解析响应数据
        
        Args:
            data: 原始响应数据
            
        Returns:
            RAGResponse: 解析后的响应对象
        """
        message_data = data.get('message', {})
        message = RAGMessage(
            role=message_data.get('role', ''),
            type=message_data.get('type', ''),
            content=message_data.get('content', '')
        )
        
        return RAGResponse(
            sse_type=data.get('sse_type', ''),
            chat_session_id=data.get('chatSessionId', ''),
            message=message
        )
    
    def chat_with_kb_simple(
        self, 
        chat_session_id: str,
        query: str,
        kb_ids: List[str],
        history: Optional[List[Dict]] = None
    ) -> str:
        """
        简化版聊天方法，返回完整响应文本
        
        Args:
            chat_session_id: 聊天会话ID
            query: 用户查询
            kb_ids: 知识库ID列表
            history: 历史对话记录，默认为空列表
            
        Returns:
            str: 完整的响应文本
        """
        full_response = ""
        
        for response in self.chat_with_kb(chat_session_id, query, kb_ids, history):
            if response.sse_type == "stage1_message":
                full_response += response.message.content
            elif response.sse_type == "retrival_end":
                # 检索完成，继续收集后续的消息片段
                continue
        
        return full_response
    
    def chat_with_kb_complete(
        self, 
        chat_session_id: str,
        query: str,
        kb_ids: List[str],
        history: Optional[List[Dict]] = None
    ) -> tuple[str, List[RAGResponse]]:
        """
        完整版聊天方法，返回完整响应文本和所有响应对象
        
        Args:
            chat_session_id: 聊天会话ID
            query: 用户查询
            kb_ids: 知识库ID列表
            history: 历史对话记录，默认为空列表
            
        Returns:
            tuple: (完整响应文本, 所有响应对象列表)
        """
        full_response = ""
        all_responses = []
        
        for response in self.chat_with_kb(chat_session_id, query, kb_ids, history):
            all_responses.append(response)
            
            if response.sse_type == "stage1_message":
                full_response += response.message.content
        
        return full_response, all_responses


def main():
    """主函数 - 演示如何使用RAG聊天客户端"""
    
    # 创建客户端实例
    client = RAGChatClient()
    
    # 配置参数
    chat_session_id = "1222121"
    query = "入选标准"
    kb_ids = ["cde133cf85a543648c3947c35a556040"]
    
    print("=" * 50)
    print("RAG聊天客户端演示")
    print("=" * 50)
    print(f"查询: {query}")
    print(f"知识库ID: {kb_ids}")
    print(f"会话ID: {chat_session_id}")
    print("=" * 50)
    
    try:
        # 方法1: 流式处理响应
        print("\n方法1: 流式处理响应")
        print("-" * 30)
        
        for response in client.chat_with_kb(chat_session_id, query, kb_ids):
            print(f"SSE类型: {response.sse_type}")
            print(f"会话ID: {response.chat_session_id}")
            print(f"消息角色: {response.message.role}")
            print(f"消息类型: {response.message.type}")
            print(f"消息内容: {response.message.content}")
            print("-" * 30)
            
            # 如果收到retrival_end，表示检索完成
            if response.sse_type == "retrival_end":
                print("知识库检索完成，开始正式回答...")
                break
        
        print("\n方法2: 简化版调用（自动拼接）")
        print("-" * 30)
        
        # 方法2: 简化版调用，自动拼接所有消息片段
        full_response = client.chat_with_kb_simple(chat_session_id, query, kb_ids)
        print(f"完整响应: {full_response}")
        
        print("\n方法3: 完整版调用（返回拼接结果和所有响应）")
        print("-" * 30)
        
        # 方法3: 完整版调用
        complete_response, all_responses = client.chat_with_kb_complete(chat_session_id, query, kb_ids)
        print(f"拼接后的完整响应: {complete_response}")
        print(f"总共收到 {len(all_responses)} 个响应片段")
        
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()
