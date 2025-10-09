import os, requests, json
from dotenv import load_dotenv

load_dotenv()
LLM_MODEL_URL = os.getenv("QWEN_14B_API_URL")
LLM_MODEL_NAME = os.getenv("QWEN_14B_MODEL_NAME")


# prompt and template
SYSTEM_PROMPT = """
你是一个中文助手
"""

USER_TEMPLATE = """
Input Text For You:
{input_text}

"""


def llm_request(input_text="你好", max_tokens=8192, temperature=0.1):

    user_input = USER_TEMPLATE.format(
        input_text=json.dumps(input_text, ensure_ascii=False)
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]
    url = f"{LLM_MODEL_URL}/chat/completions"
    payload = {
        "model": LLM_MODEL_NAME,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code != 200:
        print("请求失败:", resp.status_code, resp.text)
        return None
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        print("响应结构异常：", data)
        return None


if __name__ == "__main__":
    print(llm_request())
