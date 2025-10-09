#!/usr/bin/env python3
"""
化合物反应条件提取工具 - 使用演示

这个脚本演示了如何使用Streamlit应用的各种功能
"""

import streamlit as st
import json
import os

def create_demo_data():
    """创建演示数据"""
    demo_data = [
        {
            "input": [
                {
                    "role": "user",
                    "content": "请分析以下反应条件: {\"reaction_type\": \"oxidation\", \"temperature\": \"25°C\", \"catalyst\": \"MnO2\", \"solvent\": \"water\"}"
                }
            ],
            "output": {
                "reaction_field": "氧化反应",
                "temperature": "25°C",
                "catalyst": "MnO2催化剂",
                "solvent": "水溶剂"
            },
            "predict_output": {
                "reaction_field": "氧化反应",
                "temperature": "25°C",
                "catalyst": "MnO2催化剂",
                "solvent": "水溶剂"
            }
        },
        {
            "input": [
                {
                    "role": "user",
                    "content": "分析这个还原反应: {\"reaction_type\": \"reduction\", \"temperature\": \"80°C\", \"reducing_agent\": \"H2\", \"pressure\": \"1 atm\"}"
                }
            ],
            "output": {
                "reaction_field": "还原反应",
                "temperature": "80°C",
                "reducing_agent": "H2还原剂",
                "pressure": "1 atm"
            },
            "predict_output": {
                "reaction_field": "还原反应",
                "temperature": "80°C",
                "reducing_agent": "H2还原剂",
                "pressure": "1 atm"
            }
        }
    ]
    return demo_data

def main():
    st.title("🧪 化合物反应条件提取工具 - 功能演示")
    
    st.markdown("""
    ## 主要功能演示
    
    这个工具支持以下功能：
    
    ### 1. 📋 记录选择
    - 支持从下拉菜单选择特定记录
    - 提供"上一个"/"下一个"导航按钮
    - 单条记录展示，提高查看效率
    
    ### 2. ✏️ 内联编辑
    - 点击"编辑"按钮进入编辑模式
    - 直接在展示页面中修改内容
    - 支持修改输入内容、标准输出和模型预测
    - 实时JSON格式验证
    
    ### 3. 💬 评论功能
    - 为每条记录添加评论和备注
    - 自动记录评论时间戳
    - 支持查看历史评论
    
    ### 4. 💾 数据持久化
    - 自动保存修改到 `modified_data.json`
    - 自动保存评论到 `comments_data.json`
    - 支持导出各种格式的数据
    """)
    
    # 创建演示数据
    demo_data = create_demo_data()
    
    st.subheader("📝 演示数据")
    st.json(demo_data)
    
    # 保存演示数据到文件
    if st.button("💾 保存演示数据到文件"):
        with open("demo_data.json", "w", encoding="utf-8") as f:
            json.dump(demo_data, f, ensure_ascii=False, indent=2)
        st.success("演示数据已保存到 demo_data.json")
    
    st.subheader("🚀 启动应用")
    st.markdown("""
    要启动完整的应用，请运行：
    
    ```bash
    streamlit run reaction_field_viewer.py
    ```
    
    然后上传 `demo_data.json` 文件开始体验所有功能！
    """)
    
    # 显示文件结构
    st.subheader("📁 文件结构")
    st.code("""
    llm-playground/
    ├── reaction_field_viewer.py      # 主应用文件
    ├── streamlit_requirements.txt   # 依赖文件
    ├── test_data.json               # 测试数据
    ├── demo_data.json               # 演示数据
    ├── comments_data.json           # 评论数据（自动生成）
    ├── modified_data.json           # 修改数据（自动生成）
    └── STREAMLIT_README.md          # 使用说明
    """, language="text")

if __name__ == "__main__":
    main()
