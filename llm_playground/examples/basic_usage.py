"""
基本使用示例
展示如何使用llm_playground包
"""

from llm_playground.core import TaskAgent, get_chat_openai
from llm_playground.utils import write_base_model_items_to_json_array_file


class SimpleAgent(TaskAgent):
    """简单的任务代理示例"""

    def init_process_chain(self):
        """初始化处理链"""
        pass

    def post_process_response(self, record, response: str):
        """后处理响应"""
        return response

    def process(self, record):
        """同步处理"""
        # 这里实现具体的处理逻辑
        response = self.llm.invoke(record)
        return self.post_process_response(record, response)

    async def async_process(self, record):
        """异步处理"""
        # 这里实现具体的异步处理逻辑
        response = await self.llm.ainvoke(record)
        return self.post_process_response(record, response)


def main():
    """主函数示例"""
    # 创建LLM客户端
    llm = get_chat_openai("gpt-4o-mini")

    # 创建代理
    agent = SimpleAgent("gpt-4o-mini", llm=llm)

    # 处理单个记录
    record = "你好，请介绍一下自己"
    result = agent.process(record)
    print(f"处理结果: {result}")


if __name__ == "__main__":
    main()
