import streamlit as st
import json
import pandas as pd
from typing import List, Dict, Any
import io
import os
from datetime import datetime

# 设置页面配置
st.set_page_config(
    page_title="化合物反应条件提取",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .stats-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    
    .column-header {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px 8px 0 0;
        text-align: center;
        font-weight: bold;
        margin-bottom: 0;
    }
    
    .column-header-2 {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }
    
    .column-header-3 {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    }
    
    .item-container {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        margin-bottom: 1rem;
        overflow: hidden;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    .item-header {
        background: #f8f9fa;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid #e9ecef;
        font-weight: 600;
        color: #495057;
    }
    
    .json-content {
        background: #f8f9fa;
        padding: 1rem;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        line-height: 1.4;
        white-space: pre-wrap;
        word-wrap: break-word;
        max-height: 400px;
        overflow-y: auto;
    }
    
    .empty-content {
        text-align: center;
        color: #6c757d;
        font-style: italic;
        padding: 2rem;
    }
</style>
""", unsafe_allow_html=True)

def extract_user_content(input_array: List[Dict]) -> str:
    """从输入数组中提取用户内容"""
    if not isinstance(input_array, list):
        return '无输入数据'
    
    user_message = next((msg for msg in input_array if msg.get('role') in ['user', 'human']), None)
    if user_message and user_message.get('content'):
        try:
            content = user_message['content']
            if '{' in content and '}' in content:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, ensure_ascii=False, indent=2)
            return content
        except Exception:
            return user_message['content']
    return '无用户输入'

def extract_record_id(record: Dict, record_index: int) -> str:
    """从记录中提取ID，如果没有则使用索引"""
    # 尝试从不同字段提取ID
    possible_id_fields = ['id', 'ID', 'record_id', 'recordId', 'index', '序号']
    
    for field in possible_id_fields:
        if field in record and record[field]:
            return str(record[field])
    
    # 尝试从input内容中提取ID
    if 'input' in record and isinstance(record['input'], list):
        for msg in record['input']:
            if isinstance(msg, dict) and 'content' in msg:
                content = msg['content']
                # 查找可能的ID模式
                import re
                id_patterns = [
                    r'ID[:\s]*(\w+)',
                    r'id[:\s]*(\w+)',
                    r'序号[:\s]*(\w+)',
                    r'编号[:\s]*(\w+)'
                ]
                for pattern in id_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        return match.group(1)
    
    # 如果没有找到ID，使用索引
    return f"记录_{record_index + 1}"

def display_item_content(content: str) -> None:
    """显示单个项目的内容"""
    st.markdown(f"""
    <div class="item-container">
        <div class="json-content">{content}</div>
    </div>
    """, unsafe_allow_html=True)

def load_comments_data():
    """加载评论数据"""
    if 'comments_data' not in st.session_state:
        st.session_state.comments_data = {}
    return st.session_state.comments_data

def save_comments_data():
    """保存评论数据到文件"""
    comments_file = "comments_data.json"
    try:
        with open(comments_file, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.comments_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"保存评论数据失败: {str(e)}")
        return False

def load_modified_data():
    """加载修改后的数据"""
    if 'modified_data' not in st.session_state:
        st.session_state.modified_data = None
    return st.session_state.modified_data

def save_modified_data(data):
    """保存修改后的数据"""
    st.session_state.modified_data = data
    # 同时保存到文件
    try:
        with open("modified_data.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"保存修改数据失败: {str(e)}")
        return False

def save_to_original_file(data, original_filename):
    """保存到原JSON文件（带已校对后缀）"""
    try:
        # 生成带"已校对"后缀的文件名
        if original_filename.endswith('.json'):
            base_name = original_filename[:-5]  # 去掉.json
            new_filename = f"{base_name}_已校对.json"
        else:
            new_filename = f"{original_filename}_已校对.json"
        
        # 保存文件
        with open(new_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return new_filename, True
    except Exception as e:
        st.error(f"保存到原文件失败: {str(e)}")
        return None, False

def display_single_record(record, record_index):
    """显示单条记录"""
    comments_data = load_comments_data()
    record_key = f"record_{record_index}"
    
    # 获取该记录的评论
    record_comments = comments_data.get(record_key, [])
    
    # 检查是否处于编辑模式
    edit_mode_key = f"edit_mode_{record_index}"
    if edit_mode_key not in st.session_state:
        st.session_state[edit_mode_key] = False
    
    # 获取当前显示的数据（优先使用修改后的数据）
    current_data = record
    modified_data = load_modified_data()
    if modified_data and record_index < len(modified_data):
        current_data = modified_data[record_index]
    
    # 创建三栏布局
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="column-header">📥 输入内容 (Input)</div>', unsafe_allow_html=True)
        
        if st.session_state[edit_mode_key]:
            # 编辑模式
            input_edit = st.text_area(
                "编辑输入内容", 
                value=extract_user_content(current_data.get('input', [])), 
                key=f"edit_input_{record_index}",
                height=200,
                help="修改输入内容"
            )
        else:
            # 显示模式
            input_content = extract_user_content(current_data.get('input', []))
            display_item_content(input_content)
    
    with col2:
        st.markdown('<div class="column-header column-header-2">📤 标准输出 (Output)</div>', unsafe_allow_html=True)
        
        if st.session_state[edit_mode_key]:
            # 编辑模式
            output_edit = st.text_area(
                "编辑标准输出 (JSON格式)", 
                value=json.dumps(current_data.get('output', {}), ensure_ascii=False, indent=2), 
                key=f"edit_output_{record_index}",
                height=200,
                help="修改标准输出，必须是有效的JSON格式"
            )
        else:
            # 显示模式
            output_content = json.dumps(current_data.get('output', {}), ensure_ascii=False, indent=2) if current_data.get('output') else '无输出数据'
            display_item_content(output_content)
    
    with col3:
        st.markdown('<div class="column-header column-header-3">🤖 模型预测 (Predict Output)</div>', unsafe_allow_html=True)
        
        if st.session_state[edit_mode_key]:
            # 编辑模式
            predict_edit = st.text_area(
                "编辑模型预测 (JSON格式)", 
                value=json.dumps(current_data.get('predict_output', {}), ensure_ascii=False, indent=2), 
                key=f"edit_predict_{record_index}",
                height=200,
                help="修改模型预测，必须是有效的JSON格式"
            )
        else:
            # 显示模式
            predict_content = json.dumps(current_data.get('predict_output', {}), ensure_ascii=False, indent=2) if current_data.get('predict_output') else '无预测数据'
            display_item_content(predict_content)
    
    # 编辑控制按钮
    # st.markdown("---")
    
    if st.session_state[edit_mode_key]:
        # 编辑模式下的按钮
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        
        with col1:
            if st.button("💾 保存修改", key=f"save_edit_{record_index}", type="primary"):
                try:
                    # 获取编辑的内容
                    input_edit = st.session_state.get(f"edit_input_{record_index}", "")
                    output_edit = st.session_state.get(f"edit_output_{record_index}", "")
                    predict_edit = st.session_state.get(f"edit_predict_{record_index}", "")
                    
                    # 验证JSON格式
                    if output_edit.strip():
                        json.loads(output_edit)
                    if predict_edit.strip():
                        json.loads(predict_edit)
                    
                    # 更新数据
                    modified_data = load_modified_data()
                    if modified_data is None:
                        modified_data = st.session_state.original_data.copy()
                    
                    # 更新当前记录
                    modified_data[record_index] = {
                        **modified_data[record_index],
                        'input': [{"role": "user", "content": input_edit}] if input_edit.strip() else modified_data[record_index].get('input', []),
                        'output': json.loads(output_edit) if output_edit.strip() else modified_data[record_index].get('output', {}),
                        'predict_output': json.loads(predict_edit) if predict_edit.strip() else modified_data[record_index].get('predict_output', {}),
                        'last_modified': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    save_modified_data(modified_data)
                    st.success("修改已保存！")
                    st.session_state[edit_mode_key] = False
                    st.rerun()
                    
                except json.JSONDecodeError as e:
                    st.error(f"JSON格式错误: {str(e)}")
                except Exception as e:
                    st.error(f"保存失败: {str(e)}")
        
        with col2:
            if st.button("❌ 取消", key=f"cancel_edit_{record_index}"):
                st.session_state[edit_mode_key] = False
                st.rerun()
        
        with col3:
            if st.button("🔄 重置", key=f"reset_edit_{record_index}"):
                st.rerun()
    else:
        # 显示模式下的按钮
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("✏️ 编辑", key=f"start_edit_{record_index}"):
                st.session_state[edit_mode_key] = True
                st.rerun()
    
    # 评论功能
    # with st.expander("💬 评论功能", expanded=True):
    #     # 显示已有评论
    #     if record_comments:
    #         st.subheader("📝 已有评论")
    #         for i, comment in enumerate(record_comments):
    #             with st.container():
    #                 st.markdown(f"**评论 {i+1}** (时间: {comment.get('timestamp', '未知')})")
    #                 st.text_area(f"评论内容 {i+1}", value=comment.get('content', ''), key=f"comment_display_{record_index}_{i}", disabled=True)
        
    #     # 添加新评论
    #     st.subheader("✍️ 添加新评论")
    #     new_comment = st.text_area("请输入评论内容:", key=f"new_comment_{record_index}", height=100)
        
    #     col1, col2 = st.columns([1, 4])
    #     with col1:
    #         if st.button("💾 保存评论", key=f"save_comment_{record_index}"):
    #             if new_comment.strip():
    #                 comment_data = {
    #                     'content': new_comment,
    #                     'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #                 }
    #                 if record_key not in st.session_state.comments_data:
    #                     st.session_state.comments_data[record_key] = []
    #                 st.session_state.comments_data[record_key].append(comment_data)
    #                 save_comments_data()
    #                 st.success("评论已保存！")
    #                 st.rerun()
    #             else:
    #                 st.warning("请输入评论内容")

def main():
    # 页面标题
    st.markdown("""
    <div class="main-header">
        <h1>🧪 反应场数据展示</h1>
        <p>三栏对比展示：输入内容 | 标准输出 | 模型预测</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 初始化session state
    if 'original_data' not in st.session_state:
        st.session_state.original_data = None
    if 'current_record_index' not in st.session_state:
        st.session_state.current_record_index = 0
    
    # 文件上传
    uploaded_file = st.file_uploader(
        "选择JSON文件",
        type=['json'],
        help="请上传包含反应场数据的JSON文件"
    )
    
    if uploaded_file is not None:
        try:
            # 读取JSON数据
            data = json.load(uploaded_file)
            
            if not isinstance(data, list):
                st.error("JSON文件应该包含一个数组")
                return
            
            # 保存原始数据
            st.session_state.original_data = data
            
            # 显示统计信息
            total_items = len(data)
            completed_items = sum(1 for item in data if item.get('predict_output') and len(item.get('predict_output', {})) > 0)
            
            st.markdown(f"""
            <div class="stats-container">
                <h3>📊 数据统计</h3>
                <p><strong>总记录数:</strong> {total_items}</p>
                <p><strong>已完成记录数:</strong> {completed_items}</p>
                <p><strong>完成率:</strong> {(completed_items/total_items*100):.1f}%</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 记录选择
            st.markdown("---")
            st.subheader("📋 记录选择")
            
            # 生成记录选项（包含ID信息）
            record_options = []
            for i, record in enumerate(data):
                record_id = extract_record_id(record, i)
                record_options.append(f"记录 {i + 1} (ID: {record_id})")
            
            # 记录选择下拉菜单
            selected_index = st.selectbox(
                "选择要查看的记录:",
                range(len(data)),
                format_func=lambda x: record_options[x],
                index=st.session_state.current_record_index
            )
            st.session_state.current_record_index = selected_index
            
            # 导航按钮（放在下拉菜单下方）
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("⬅️ 上一个"):
                    if st.session_state.current_record_index > 0:
                        st.session_state.current_record_index -= 1
                        st.rerun()
            
            with col2:
                if st.button("➡️ 下一个"):
                    if st.session_state.current_record_index < len(data) - 1:
                        st.session_state.current_record_index += 1
                        st.rerun()
            
            # 显示选中的记录（优先使用修改后的数据）
            current_record = data[st.session_state.current_record_index]
            modified_data = load_modified_data()
            if modified_data and st.session_state.current_record_index < len(modified_data):
                current_record = modified_data[st.session_state.current_record_index]
            
            display_single_record(current_record, st.session_state.current_record_index)
            
            # 数据导出功能
            st.markdown("---")
            st.subheader("📥 数据导出")
            
            # 创建DataFrame用于导出（使用修改后的数据）
            export_data = []
            modified_data = load_modified_data()
            current_data = modified_data if modified_data else data
            
            for i, item in enumerate(current_data):
                record_id = extract_record_id(item, i)
                export_data.append({
                    '项目编号': i + 1,
                    '记录ID': record_id,
                    '输入内容': extract_user_content(item.get('input', [])),
                    '标准输出': json.dumps(item.get('output', {}), ensure_ascii=False) if item.get('output') else '',
                    '模型预测': json.dumps(item.get('predict_output', {}), ensure_ascii=False) if item.get('predict_output') else '',
                    '最后修改时间': item.get('last_modified', '未修改')
                })
            
            df = pd.DataFrame(export_data)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                # CSV导出
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📊 下载CSV文件",
                    data=csv,
                    file_name="reaction_field_data.csv",
                    mime="text/csv"
                )
            
            with col2:
                # JSON导出（使用修改后的数据）
                export_json = current_data
                json_str = json.dumps(export_json, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📄 下载JSON文件",
                    data=json_str,
                    file_name="reaction_field_data.json",
                    mime="application/json"
                )
            
            with col3:
                # 保存到原文件（带已校对后缀）
                if st.button("💾 保存到原文件", type="primary"):
                    if uploaded_file:
                        original_filename = uploaded_file.name
                        new_filename, success = save_to_original_file(current_data, original_filename)
                        if success:
                            st.success(f"已保存到: {new_filename}")
                        else:
                            st.error("保存失败")
                    else:
                        st.warning("请先上传文件")
            
            with col4:
                # 评论数据导出
                comments_data = load_comments_data()
                if comments_data:
                    comments_json = json.dumps(comments_data, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="💬 下载评论数据",
                        data=comments_json,
                        file_name="comments_data.json",
                        mime="application/json"
                    )
            
            # 显示数据概览
            st.subheader("📋 数据概览")
            st.dataframe(df, use_container_width=True)
            
        except json.JSONDecodeError as e:
            st.error(f"JSON文件格式错误: {str(e)}")
        except Exception as e:
            st.error(f"处理文件时发生错误: {str(e)}")
    
    else:
        # 显示示例数据
        st.info("👆 请上传JSON文件开始使用")
        
        # 显示示例JSON格式
        st.subheader("📝 示例JSON格式")
        example_data = [
            {
                "input": [
                    {
                        "role": "user",
                        "content": "请分析以下反应场数据: {\"reaction_type\": \"oxidation\", \"conditions\": \"室温\"}"
                    }
                ],
                "output": {
                    "reaction_field": "氧化反应",
                    "conditions": "室温条件"
                },
                "predict_output": {
                    "reaction_field": "氧化反应",
                    "conditions": "室温条件"
                }
            }
        ]
        
        st.json(example_data)

if __name__ == "__main__":
    main()
