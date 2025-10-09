"""
测试模型相关功能
"""

import pytest
from llm_playground.core.models import is_restricted_llm


def test_is_restricted_llm():
    """测试受限模型判断"""
    # 测试受限模型
    assert is_restricted_llm("gpt-4") == True
    assert is_restricted_llm("gpt-4o") == True
    assert is_restricted_llm("gpt-4o-mini") == True
    assert is_restricted_llm("QWEN25_14B") == True
    
    # 测试非受限模型
    assert is_restricted_llm("QWEN25_32B") == False
    assert is_restricted_llm("CHATDD_14B") == False
