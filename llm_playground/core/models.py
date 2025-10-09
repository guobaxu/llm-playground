import os
from typing import Dict, Any, Tuple, Union
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAI
from langchain_openai import AzureChatOpenAI, AzureOpenAI

load_dotenv()


# =============================================================================================

LLAMA_STOP = ["<|eot_id|>"]
PHI_STOP = ["<|im_end|>"]
QWEN_STOP = ["<|im_end|>"]
DS_R1_STOP = ["<｜end▁of▁sentence｜>"]

GPT_4_LLM_NAME = "gpt-4"
GPT_4O_LLM_NAME = "gpt-4o"
GPT_4O_MINI_LLM_NAME = "gpt-4o-mini"

# 模型配置统一管理
MODEL_CONFIGS = {
    # QWEN 模型配置
    "QWEN25_14B": {
        "url": "http://101.126.41.66:12633/v1",
        "name": "Qwen2.5-14B-Instruct",
        "stop": QWEN_STOP,
    },
    "QWEN25_32B": {
        "url": "http://101.126.41.66:12633/v1",
        "name": "Qwen2.5-32B-Instruct",
        "stop": QWEN_STOP,
    },
    # CHATDD 模型配置
    "CHATDD_14B": {
        "url": "http://101.126.41.66:11633/v1",
        "name": "CHATDD_14B",
        "stop": QWEN_STOP,
    },
    "CHATDD_32B": {
        "url": "http://101.126.41.66:11633/v1",
        "name": "ChatDD_32B",
        "stop": QWEN_STOP,
    },
}

# 保持向后兼容的常量
QWEN25_7B_LLM_NAME = "QWEN25_7B"
QWEN25_14B_LLM_NAME = "QWEN25_14B"
QWEN25_32B_LLM_NAME = "QWEN25_32B"
CHATDD_7B_LLM_NAME = "CHATDD_7B"
CHATDD_14B_LLM_NAME = "CHATDD_14B"
CHATDD_32B_LLM_NAME = "CHATDD_32B"
JINGTAI_14B_LLM_NAME = "ChatDD-14B"

# =============================================================================================


def is_restricted_llm(llm_name: str) -> bool:
    """
    GPT 相关外部模型调用, 由于需要付费, 所以限制调用频率,
    DeepSeek-R1 由于是内部线上使用, 为了避免线上性能, 因此限制调用频率
    """
    if llm_name in [
        GPT_4O_MINI_LLM_NAME,
        GPT_4O_LLM_NAME,
        GPT_4_LLM_NAME,
        # QWEN25_14B_LLM_NAME,
        "DS_R1",
        "QWQ_32B",
    ]:
        return True
    return False

def is_reasoning_llm(llm_name:str) -> bool:
    if llm_name in [
        "DS_7B",
        "DS_14B",
        "DS_32B",
        "DS_R1",
        "QWQ_32B",
    ]:
        return True
    return False

def _get_azure_config(llm_name: str) -> Tuple[str, str]:
    """获取Azure OpenAI配置"""
    if llm_name == GPT_4_LLM_NAME:
        api_key = os.getenv("GPT_4_API_KEY")
        endpoint = os.getenv("GPT_4_ENDPOINT")
    elif llm_name == GPT_4O_LLM_NAME:
        api_key = os.getenv("GPT_4O_API_KEY")
        endpoint = os.getenv("GPT_4O_ENDPOINT")
    elif llm_name == GPT_4O_MINI_LLM_NAME:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    else:
        raise ValueError(f"不支持的Azure模型: {llm_name}")

    if not api_key or not endpoint:
        raise ValueError(f"缺少必要的环境变量: {llm_name} 的API密钥或端点")

    return api_key, endpoint


def _get_model_config(llm_name: str) -> Dict[str, Any]:
    """获取模型配置"""
    if llm_name not in MODEL_CONFIGS:
        raise ValueError(f"不支持的模型: {llm_name}")

    config = MODEL_CONFIGS[llm_name]
    if not config["url"]:
        raise ValueError(f"模型 {llm_name} 的URL未配置")

    return config


def get_chat_openai(
    llm_name: str = "",
    n: int = 1,
    presence_penalty: float = 0,
    temperature: float = 0.0,
    max_tokens: int = None,
    streaming: bool = False,
    stop: list = None,
) -> Union[ChatOpenAI, AzureChatOpenAI]:
    """
    创建ChatOpenAI客户端

    Args:
        llm_name: 模型名称
        n: 生成数量
        presence_penalty: 存在惩罚
        temperature: 温度
        max_tokens: 最大token数
        streaming: 是否流式输出
        stop: 停止词列表

    Returns:
        ChatOpenAI或AzureChatOpenAI客户端
    """
    if stop is None:
        stop = ["<|eot_id|>"]

    if not llm_name:
        raise ValueError("模型名称不能为空")

    # Azure OpenAI 模型
    if llm_name in [GPT_4_LLM_NAME, GPT_4O_LLM_NAME, GPT_4O_MINI_LLM_NAME]:
        api_key, endpoint = _get_azure_config(llm_name)
        # print(f"llm_name: {llm_name}, api_key: {api_key}, endpoint: {endpoint}")
        return AzureChatOpenAI(
            openai_api_key=api_key,
            azure_endpoint=endpoint,
            azure_deployment=llm_name,
            openai_api_version="2024-02-01",
        )

    # 其他模型
    config = _get_model_config(llm_name)
    return ChatOpenAI(
        openai_api_key="EMPTY",
        openai_api_base=config["url"],
        model_name=config["name"],
        n=n,
        presence_penalty=presence_penalty,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
        stop=config["stop"],
    )


def get_openai(
    llm_name: str = "",
    n: int = 1,
    presence_penalty: float = 0,
    temperature: float = 0.0,
    max_tokens: int = None,
    streaming: bool = False,
    stop: list = None,
) -> Union[OpenAI, AzureOpenAI]:
    """
    创建OpenAI客户端

    Args:
        llm_name: 模型名称
        n: 生成数量
        presence_penalty: 存在惩罚
        temperature: 温度
        max_tokens: 最大token数
        streaming: 是否流式输出
        stop: 停止词列表

    Returns:
        OpenAI或AzureOpenAI客户端
    """
    if stop is None:
        stop = ["<|eot_id|>"]

    if not llm_name:
        raise ValueError("模型名称不能为空")

    # Azure OpenAI 模型
    if llm_name in [GPT_4_LLM_NAME, GPT_4O_LLM_NAME, GPT_4O_MINI_LLM_NAME]:
        api_key, endpoint = _get_azure_config(llm_name)
        return AzureOpenAI(
            openai_api_key=api_key,
            azure_endpoint=endpoint,
            azure_deployment=llm_name,
            openai_api_version="2024-02-01",
        )

    # 其他模型
    config = _get_model_config(llm_name)
    return OpenAI(
        openai_api_key="EMPTY",
        openai_api_base=config["url"],
        model_name=config["name"],
        n=n,
        presence_penalty=presence_penalty,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
        stop=config["stop"],
    )
