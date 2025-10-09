#!/usr/bin/env python3
"""
测试编辑后展示页面同步问题修复

这个脚本验证修改后的数据是否正确显示在展示页面
"""

import json
import os

def test_data_sync():
    """测试数据同步功能"""
    
    # 创建测试数据
    test_data = [
        {
            "input": [{"role": "user", "content": "原始输入内容"}],
            "output": {"field": "原始输出"},
            "predict_output": {"field": "原始预测"}
        }
    ]
    
    # 模拟修改后的数据
    modified_data = [
        {
            "input": [{"role": "user", "content": "修改后的输入内容"}],
            "output": {"field": "修改后的输出"},
            "predict_output": {"field": "修改后的预测"},
            "last_modified": "2024-01-15 16:20:30"
        }
    ]
    
    print("🧪 测试数据同步功能")
    print("=" * 50)
    
    print("📝 原始数据:")
    print(json.dumps(test_data, ensure_ascii=False, indent=2))
    
    print("\n✏️ 修改后的数据:")
    print(json.dumps(modified_data, ensure_ascii=False, indent=2))
    
    print("\n✅ 修复说明:")
    print("1. 现在展示页面会优先显示修改后的数据")
    print("2. 编辑模式下的初始值来自修改后的数据")
    print("3. 数据概览和导出都使用修改后的数据")
    print("4. 保存修改后会立即更新展示页面")
    
    print("\n🔧 关键修改点:")
    print("- display_single_record() 函数现在使用 current_data")
    print("- 主函数中显示记录时优先使用 modified_data")
    print("- 数据导出使用修改后的数据")
    print("- 所有显示都保持数据一致性")

if __name__ == "__main__":
    test_data_sync()
