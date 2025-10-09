"""
LLM Playground - 一个用于测试和实验大语言模型的Python包
"""

__version__ = "0.1.0"
__author__ = "Your Name"

# 导入主要模块
from .core import TaskAgent, models
from .utils import helpers

__all__ = ["TaskAgent", "models", "helpers"]
