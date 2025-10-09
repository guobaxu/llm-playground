import re
import json
import hashlib


def md5_text(text):
    """
    计算输入文本字符串的MD5哈希值。

    参数:
        text (str): 需要计算MD5的文本字符串。

    返回:
        str: 32位的十六进制MD5哈希字符串。
    """
    # 将文本编码为UTF-8字节流后计算MD5，并返回十六进制表示
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def get_json_text_from_response(response:str):
    """
    用于从 LLM 返回的结果 ResponseText 大段文本中提取出完整的 JSON-Text 部分
    因为模型的输出不一定严格遵循JSON语法格式，该操作只是简单的对Response内容截取
    首尾 "{", "}" 得到一个完整的JSON串。

    如果找不到首尾匹配的括号，则直接返回原始输出
    """
    start_json_pos = response.find('```json')
    content = response
    if start_json_pos >= 0:
        content = response[start_json_pos:]
    l_pos = content.find('{')
    r_pos = content.rfind('}')
    if l_pos >= 0 and l_pos < r_pos:
        return content[l_pos:r_pos+1]
    return content 


def get_json_text_of_compound_from_response(response: str) -> str:
    """
    提取首个完整 JSON（对象或数组）：
    - 去掉 ```json/``` 围栏
    - 去掉常见前缀（如 'Output json results:'、'Results:' 等）
    - 从首个 '[' 或 '{' 起，做配对扫描，截到匹配的 ']' 或 '}'
    - 清理少量非法控制字符与尾随逗号
    """
    start_json_pos = response.find('```json')
    content = response
    if start_json_pos >= 0:
        content = response[start_json_pos:]
    l_pos = content.find('[')
    r_pos = content.rfind(']')
    if l_pos >= 0 and l_pos < r_pos:
        return content[l_pos:r_pos+1]
    return content 


def split_llm_thinking_content_from_response(response:str):
    """
    当LLM返回结果按 DeepSeek-R1 样式在 ResponseText 中先返回 <think>xxxxxx</think> 部分，
    再返回 real content 部分时，用于从 response 中按<think-tag> 切分出这两个部分
    """
    thinking_content = ''
    response_content = response

    pos_thinking_start = response.find('<think>')
    pos_thinking_end = response.rfind('</think>')
    if pos_thinking_end >= 0:
        response_content = response[pos_thinking_end + 8:]
        if pos_thinking_start >= 0 and \
            pos_thinking_start < pos_thinking_end:
            thinking_content = response[pos_thinking_start+7:pos_thinking_end]
    return thinking_content, response_content


def trim_text_whitespace(text:str) -> str:
    return re.sub(r'\s', '', text)


def is_text_exact_match(text1: str, text2: str, ignore_case: bool=False,
                        ignore_whitespace: bool=False) -> bool:
    
    a = text1
    b = text2
    if ignore_case:
        a = a.lower()
        b = b.lower()
    if ignore_whitespace:
        a = trim_text_whitespace(a)
        b = trim_text_whitespace(b)
    if a == b:
        return True
    else:
        return False


def write_base_model_items_to_jsonl_file(
    jsonl_filepath:str, records):

    with open(jsonl_filepath, mode='w', encoding='utf-8') as fp:
        for record in records:
            fp.write(record.model_dump_json())
            fp.write('\n')


def write_base_model_items_to_json_array_file(
    json_array_filepath:str, records, uid_filtering:bool=True):

    fp = open(json_array_filepath, mode='w', encoding='utf-8')
    fp.write('[\n')

    JSON_INDENT = 2

    # 对 records 按 uid 去重
    if uid_filtering:
        uids = set()
        unique_records = list()
        for record in records:
            if record.uid not in uids:
                uids.add(record.uid)
                unique_records.append(record)
    else:
        unique_records = records

    if len(unique_records) <= 1:
        for record in unique_records:
            fp.write(record.model_dump_json(indent=JSON_INDENT, ))
            fp.write('\n')
    else:
        for record in unique_records[:-1]:
            fp.write(record.model_dump_json(indent=JSON_INDENT))
            fp.write(',\n')
        fp.write(unique_records[-1].model_dump_json(indent=JSON_INDENT))
        fp.write('\n')
    fp.write(']\n')
    fp.close()



def load_json_array_from_file(json_filepath:str):
    jarray = None
    with open(json_filepath, mode='r', encoding='utf-8') as fp:
        jarray = json.loads(fp.read())
    return jarray
    

def load_uids_from_file(uids_filepath:str) -> set[str]:
    uids = set()
    with open(uids_filepath, mode='r', encoding='utf-8') as fp:
        for line in fp.readlines():
            uid = line.rstrip('\r\n')
            if len(uid) > 0:
                uids.add(uid)
    return uids
