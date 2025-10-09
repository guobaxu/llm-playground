from typing import Any, Optional
import json
from pydantic import ValidationError
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm_playground.datamodel.synthesis_route import (
    ReactionStepDescription,
    ReactionStepDescriptionRecord,
    ReactionInfo
)
from llm_playground.core.baseagent import TaskAgent
from llm_playground.core.models import is_reasoning_llm
from llm_playground.core.prompts import (
    PATENT_SYNTHESIS_SYSTEM_PROMPT,
    PATENT_SYNTHESIS_USER_TEMPLATE,
    PATENT_SYNTHESIS_reaction_field_SYSTEM_PROMPT,
    PATENT_SYNTHESIS_reaction_field_USER_TEMPLATE
)
from llm_playground.utils.helpers import (
    get_json_text_from_response,
    split_llm_thinking_content_from_response,
)


class PatentSynthesisRouteAgent(TaskAgent):
    """LLM agent that mines synthesis routes from patent fragments."""

    def __init__(
        self,
        llm_name: str,
        llm: Optional[Any] = None,
        max_tokens: int = 10*1024,
        system_prompt: str = PATENT_SYNTHESIS_SYSTEM_PROMPT,
    ) -> None:
        super().__init__(llm_name=llm_name, llm=llm, max_tokens=max_tokens)
        self.system_prompt = system_prompt
        self._chain = None

    def init_process_chain(self):
        if self._chain is None:
            self._prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("user", PATENT_SYNTHESIS_USER_TEMPLATE),
            ])
            self._chain = self._prompt | self.llm | StrOutputParser()
        return self._chain
    
    def post_process_response(self, record: ReactionStepDescriptionRecord, response: str):
        record.llm_response = response

        if is_reasoning_llm(self.llm_name):
            thinking_content, response = split_llm_thinking_content_from_response(response)

        record.model = self.get_unique_label()

        json_text = get_json_text_from_response(response)
        try:
            jobj = json.loads(json_text)
            # 关键：统一为 dict
            results = jobj.get('results', [])
            if not isinstance(results, list):
                results = []
            record.predict_output = {"results": results}
        except Exception:
            print("解析Json结构失败，模型response如下\n", response)
            record.predict_output = {}
        return record

    def process(self, record: ReactionStepDescriptionRecord):
        chain = self.init_process_chain()
        user_messages = [m for m in record.input if m.get("role") == "user"]
        user_content = user_messages[0]["content"] if user_messages else ""

        try:
            # 渲染完整 prompt 保存到record.input
            msgs = self._prompt.format_messages(input_text=user_content)
            record.input = [{"role": m.type, "content": m.content} for m in msgs]

            # 真正调用
            response = chain.invoke({"input_text": user_content})
        except Exception as exc:
            print(exc)
            record.llm_response = None
            record.predict_output = {}
            return record
        return self.post_process_response(record, response)

    async def async_process(self, record: ReactionStepDescriptionRecord):
        chain = self.init_process_chain()
        user_messages = [m for m in record.input if m.get("role") == "user"]
        user_content = user_messages[0]["content"] if user_messages else ""

        try:
            # 渲染完整 prompt 保存到record.input
            msgs = self._prompt.format_messages(input_text=user_content)
            record.input = [{"role": m.type, "content": m.content} for m in msgs]

            # 真正调用
            response = await chain.ainvoke({"input_text": user_content})
        except Exception as exc:
            print(exc)
            record.llm_response = None
            record.predict_output = {}
            return record
        return self.post_process_response(record, response)


class PatentReactionFieldAgent(TaskAgent):
    """LLM agent that extracts reaction field information from chemical synthesis descriptions."""

    def __init__(
        self,
        llm_name: str,
        llm: Optional[Any] = None,
        max_tokens: int = 15*1024,
        system_prompt: str = PATENT_SYNTHESIS_reaction_field_SYSTEM_PROMPT,
    ) -> None:
        super().__init__(llm_name=llm_name, llm=llm, max_tokens=max_tokens)
        self.system_prompt = system_prompt
        self._chain = None

    def init_process_chain(self):
        if self._chain is None:
            self._prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("user", PATENT_SYNTHESIS_reaction_field_USER_TEMPLATE),
            ])
            self._chain = self._prompt | self.llm | StrOutputParser()
        return self._chain
    
    def post_process_response(self, record: ReactionStepDescriptionRecord, response: str):
        record.llm_response = response

        if is_reasoning_llm(self.llm_name):
            thinking_content, response = split_llm_thinking_content_from_response(response)

        record.model = self.get_unique_label()

        json_text = get_json_text_from_response(response)
        try:
            jobj = json.loads(json_text)
            # 直接使用整个JSON对象作为预测输出
            record.predict_output = jobj
        except Exception:
            print("解析Json结构失败，模型response如下\n", response)
            record.predict_output = {}
        return record

    def process(self, record: ReactionStepDescriptionRecord):
        chain = self.init_process_chain()
        user_messages = [m for m in record.input if m.get("role") == "user"]
        user_content = user_messages[0]["content"] if user_messages else ""

        try:
            # 渲染完整 prompt 保存到record.input
            msgs = self._prompt.format_messages(input_text=user_content)
            record.input = [{"role": m.type, "content": m.content} for m in msgs]

            # 真正调用
            response = chain.invoke({"input_text": user_content})
        except Exception as exc:
            print(exc)
            record.llm_response = None
            record.predict_output = {}
            return record
        return self.post_process_response(record, response)

    async def async_process(self, record: ReactionStepDescriptionRecord):
        chain = self.init_process_chain()
        user_messages = [m for m in record.input if m.get("role") == "user"]
        user_content = user_messages[0]["content"] if user_messages else ""
        try:
            # 渲染完整 prompt 保存到record.input
            msgs = self._prompt.format_messages(input_text=user_content)
            record.input = [{"role": m.type, "content": m.content} for m in msgs]

            # 真正调用
            response = await chain.ainvoke({"input_text": user_content})
        except Exception as exc:
            print(exc)
            record.llm_response = None
            record.predict_output = {}
            return record
        return self.post_process_response(record, response)
