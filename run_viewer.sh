#!/bin/bash
echo "启动反应场数据展示工具..."
echo ""
echo "正在安装依赖..."
pip install -r streamlit_requirements.txt
echo ""
echo "启动Streamlit应用..."
streamlit run reaction_field_viewer.py
