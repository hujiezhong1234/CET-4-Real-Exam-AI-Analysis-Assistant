"""UI 组件模块：错题标注、词汇收藏、学习记录面板"""

import time
import json
import re
import streamlit as st


def render_wrong_answer_checkboxes(start_num, end_num, section_key):
    """渲染错题标注复选框"""
    st.markdown("---")
    st.markdown("**📝 错题标注**")
    cols = st.columns(5)
    for idx, num in enumerate(range(start_num, end_num + 1)):
        wrong_key = f"wrong_{section_key}_{num}"
        if wrong_key not in st.session_state:
            st.session_state[wrong_key] = False
        with cols[idx % 5]:
            st.checkbox(f"❌ {num}", key=wrong_key)


def render_vocabulary_buttons(analysis_text, section_key):
    """渲染词汇收藏按钮"""
    st.markdown("---")
    st.markdown("**⭐ 高频词汇收藏**")
    st.caption("点击按钮收藏你觉得重要的词汇（最多显示10个候选词）")

    candidate_words = []

    # 方法1：匹配 markdown 表格中的第一列单词
    table_words = re.findall(r'^\s*\|\s*([a-zA-Z]{3,})\s*\|', analysis_text, re.MULTILINE)
    candidate_words.extend(table_words)

    # 方法2：匹配 **单词** 格式
    bold_words = re.findall(r'\*\*([a-zA-Z]{3,})\*\*', analysis_text)
    candidate_words.extend(bold_words)

    # 方法3：匹配独立行的大写单词
    line_words = re.findall(r'^\s*[-•]\s*([a-zA-Z]{3,})', analysis_text, re.MULTILINE)
    candidate_words.extend(line_words)

    # 去重并限制数量
    seen = set()
    unique_words = []
    for w in candidate_words:
        w_lower = w.lower()
        if w_lower not in seen and len(w_lower) > 2:
            seen.add(w_lower)
            unique_words.append(w)

    display_words = unique_words[:10]

    if display_words:
        cols_per_row = 3
        for i in range(0, len(display_words), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = i + j
                if idx < len(display_words):
                    word = display_words[idx]
                    with cols[j]:
                        btn_key = f"fav_{section_key}_{word}"
                        if st.button(f"⭐ {word}", key=btn_key, use_container_width=True):
                            _save_vocabulary(word, analysis_text, section_key)
    else:
        st.info("未自动识别到词汇，你可以手动输入收藏")
        manual_col1, manual_col2 = st.columns([2, 1])
        with manual_col1:
            manual_word = st.text_input("输入单词", key=f"manual_word_{section_key}")
        with manual_col2:
            if st.button("⭐ 收藏", key=f"manual_fav_{section_key}"):
                if manual_word:
                    _save_vocabulary(manual_word, "", section_key)


def _save_vocabulary(word, context_text, section):
    """保存词汇到收藏夹"""
    if 'saved_vocabulary' not in st.session_state:
        st.session_state.saved_vocabulary = []

    existing = [v for v in st.session_state.saved_vocabulary if v['word'].lower() == word.lower()]
    if not existing:
        # 从分析文本中提取该词的上下文
        context = ""
        if context_text:
            lines = context_text.split('\n')
            for line in lines:
                if word.lower() in line.lower():
                    context = line.strip()
                    break

        st.session_state.saved_vocabulary.append({
            "word": word,
            "context": context,
            "section": section,
            "timestamp": time.strftime("%Y-%m-%d %H:%M")
        })
        st.success(f"已收藏 {word}！")
        st.rerun()
    else:
        st.info(f"{word} 已收藏过")


def render_sidebar_learning_records():
    """渲染侧边栏学习记录面板"""
    st.markdown("---")
    st.markdown("**📚 我的学习记录**")

    # 显示已收藏的词汇
    if 'saved_vocabulary' in st.session_state and st.session_state.saved_vocabulary:
        st.markdown(f"已收藏词汇：**{len(st.session_state.saved_vocabulary)}** 个")
        with st.expander("查看收藏词汇"):
            for vocab in st.session_state.saved_vocabulary:
                st.write(f"• **{vocab['word']}** — {vocab.get('context', '')[:60]}...")
        # 导出词汇
        vocab_export = json.dumps(st.session_state.saved_vocabulary, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 导出词汇本 (JSON)",
            data=vocab_export,
            file_name="my_vocabulary.json",
            mime="application/json"
        )
    else:
        st.markdown("已收藏词汇：**0** 个")

    # 显示错题统计
    wrong_count = 0
    wrong_details = []
    for key in st.session_state:
        if key.startswith("wrong_") and st.session_state[key]:
            wrong_count += 1
            match = re.search(r'wrong_(\w+)_(\d+)', key)
            if match:
                section, num = match.groups()
                wrong_details.append(f"{section} - 第{num}题")

    st.markdown(f"已标记错题：**{wrong_count}** 道")
    if wrong_details:
        with st.expander("查看错题"):
            for detail in wrong_details:
                st.write(f"• {detail}")


def render_pdf_overview(data):
    """渲染 PDF 解析结果概览"""
    st.markdown("---")
    st.subheader("📋 真题结构概览")

    for part_key in ["Part_I", "Part_II", "Part_III", "Part_IV"]:
        if part_key not in data:
            continue

        part_data = data[part_key]
        part_name = part_data.get("name", "")
        part_display = part_key.replace("_", " ")

        with st.expander(f"{part_display} - {part_name}", expanded=(part_key == "Part_III")):

            if "content" in part_data:
                content = part_data["content"]
                st.text_area("内容", content[:800] + ("..." if len(content) > 800 else ""),
                             height=150, disabled=True, label_visibility="collapsed")

            elif "sections" in part_data:
                sections = part_data["sections"]

                if "Section_A" in sections:
                    with st.container():
                        st.markdown("**📝 Section A - 选词填空**")
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            article = sections["Section_A"]["article"]
                            st.text_area("文章", article[:500] + "...", height=100, disabled=True)
                        with col2:
                            st.text_area("选项", sections["Section_A"]["wordbank"], height=100, disabled=True)

                if "Section_B" in sections:
                    with st.container():
                        st.markdown("**📄 Section B - 段落匹配**")
                        st.write(f"**标题**: {sections['Section_B']['title']}")
                        st.write("**段落列表**：")
                        for letter, para in sections['Section_B']['paragraphs'].items():
                            with st.expander(f"段落 {letter}"):
                                st.write(para)
                        st.write(f"**题目数**: {len(sections['Section_B']['questions'])}")

                if "Section_C" in sections:
                    with st.container():
                        st.markdown("**📖 Section C - 阅读理解**")
                        for passage_name, passage_data in sections["Section_C"].items():
                            passage_display = passage_name.replace("_", " ")
                            article = passage_data['article']
                            summary = article[:150] + "..." if len(article) > 150 else article

                            with st.expander(
                                    f"📄 {passage_display} ({len(article.split())} 词, {len(passage_data['questions'])} 题)"):
                                st.write("**文章摘要：**")
                                st.write(summary)
                                st.write("---")
                                st.write("**题目：**")
                                for num, q_text in passage_data['questions'].items():
                                    st.write(f"{num}. {q_text[:200]}...")