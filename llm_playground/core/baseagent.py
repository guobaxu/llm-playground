import asyncio
from abc import ABC, abstractmethod
from .models import (
    is_restricted_llm,
    get_chat_openai,
)


class TaskAgent(ABC):
    def __init__(self, llm_name: str, llm=None, max_tokens: int = 8 * 1024):
        self.llm_name = llm_name
        if llm is not None:
            self.llm = llm
        else:
            self.llm = get_chat_openai(llm_name=llm_name, max_tokens=max_tokens)

    def get_unique_label(self):
        return self.__class__.__name__ + "_" + self.llm_name

    @abstractmethod
    def init_process_chain(self):
        """
        初始化 LangChain 调用链
        """
        pass

    @abstractmethod
    def post_process_response(self, record, response: str):
        """
        LLM 返回 response 后进行后处理
        """
        pass

    @abstractmethod
    def process(self, record):
        """
        调用 LLM 处理 record 同步Inference过程
        """
        pass

    @abstractmethod
    async def async_process(self, record):
        """
        调用 LLM 处理 record 异步Inference过程
        """
        pass

    async def async_process_multiple(self, records, max_batch_size: int = 64):
        """
        调用 LLM 处理 record 一个Batch并发异步Inference过程
        """

        batch_records = []
        new_records = []

        if not is_restricted_llm(self.llm_name):
            for record in records:
                if len(batch_records) >= max_batch_size:
                    tasks = [self.async_process(record) for record in batch_records]
                    delta_new_records = await asyncio.gather(*tasks)
                    new_records.extend(delta_new_records)
                    batch_records.clear()
                batch_records.append(record)
            if len(batch_records) > 0:
                tasks = [self.async_process(record) for record in batch_records]
                delta_new_records = await asyncio.gather(*tasks)
                new_records.extend(delta_new_records)
                batch_records.clear()
        else:
            # 如果是被限制频率调用的LLM, 严格按照一次一个请求进行调用
            print(
                f"{self.llm_name} is a restricted llm, so we can only run request one by one..."
            )
            for record in records:
                new_record = await self.async_process(record)
                new_records.append(new_record)

        return new_records
