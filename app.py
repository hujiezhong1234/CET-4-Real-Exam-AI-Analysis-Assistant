"""四级真题AI分析助手 - 主入口"""

import streamlit as st
from io import BytesIO

from config import PLATFORM_CONFIG, ANALYZE_OPTIONS
from pdf_parser import parse_cet4_pdf
from ai_client import call_ai_api
from ui_components import (
    render_pdf_overview,
    render_wrong_answer_checkboxes,
    render_vocabulary_buttons,
    render_sidebar_learning_records
)


def build_prompt(section_type, data, section_key=None):
    """构建 AI 分析 prompt"""
    if section_type == "Part_I Writing" and "Part_I" in data:
        return f"""你是一位大学英语四级写作专家。请分析以下四级写作题目，给出：

1. **题目解读**：这道题要求写什么类型的文章（议论文？说明文？）
2. **文章结构**：推荐的三段式结构（开头-主体-结尾）
3. **高分句型**：给出3-5个可以直接套用的万能句型
4. **常用词汇**：列出5个这个话题下的高频表达
5. **范文框架**：给出一个120-180词的范文大纲
6. **参考范文**：给出一篇 120-180 词的完整范文，并标注亮点句型

题目：
{data['Part_I']['content']}
"""

    elif section_type == "Part_II Listening" and "Part_II" in data:
        return f"""你是一位大学英语四级听力专家。请分析以下听力部分信息：

1. **题型说明**：这部分是什么题型
2. **备考建议**：针对这类听力的练习方法
3. **常见陷阱**：听力中容易出错的地方
4. **答案与原文定位**：根据现有文本，说明每道题答案可能出现的原文位置及判断依据

内容：
{data['Part_II']['content']}
"""

    elif section_type == "Part_III Section_A" and "Part_III" in data:
        sec_a = data["Part_III"]["sections"]["Section_A"]
        return f"""分析以下四级选词填空真题：
1. 列出文章中的5个高频词汇及释义
2. 分析每个空(26-35)应该填什么词性/词义
3. 给出解题技巧
4. **参考答案**：给出26-35每道题的正确选项字母，并说明选择理由（语法/词义/上下文）

文章：{sec_a['article']}

选项：{sec_a['wordbank']}"""

    elif section_type == "Part_III Section_B" and "Part_III" in data:
        sec_b = data["Part_III"]["sections"]["Section_B"]
        prompt = f"""你是一位大学英语四级阅读专家。请分析以下段落匹配真题：

1. **文章主旨**：用一句话概括这篇文章讲什么
2. **段落分析**：分析每个段落的核心内容
3. **匹配技巧**：做段落匹配题的解题策略
4. **高频词汇**：列出5个重要词汇
5. **参考答案**：给出36-45每道题对应的段落字母，并说明匹配依据（关键词对应）

标题：{sec_b['title']}

段落：
"""
        for letter, para in sec_b["paragraphs"].items():
            prompt += f"\n{letter}) {para[:200]}..."
        prompt += f"\n\n题目：\n"
        for num, q_text in sec_b["questions"].items():
            prompt += f"\n{num}. {q_text}"
        return prompt

    elif section_type == "Part_III Section_C Passage_One" and "Part_III" in data:
        p1 = data["Part_III"]["sections"]["Section_C"]["Passage_One"]
        prompt = f"""你是一位大学英语四级考试专家。请分析以下四级阅读理解真题，给出：

1. **高频词汇表**：列出5个高频/重要词汇，给出音标、词性、中文释义、例句
2. **长难句分析**：找出2个最难理解的句子，拆解语法结构
3. **出题规律**：分析每道题的出题角度（细节题/主旨题/推理题），指出做题技巧
4. **文章主旨**：用中文一句话总结核心观点
5. **参考答案与逐题解析**：
   - 给出每道题的正确答案（只写字母，如 46.B）
   - 对每道题详细解析：正确答案在原文哪里找到依据（引用原文关键句）
   - 分析每个错误选项的干扰点（为什么错）

文章：
{p1['article']}

题目：
"""
        for num, q_text in p1["questions"].items():
            prompt += f"\n{num}. {q_text}"
            for opt in ['A', 'B', 'C', 'D']:
                opt_key = f"{num}_{opt}"
                if opt_key in p1.get('options', {}):
                    prompt += f"\n{opt}) {p1['options'][opt_key]}"
        return prompt

    elif section_type == "Part_III Section_C Passage_Two" and "Part_III" in data:
        p2 = data["Part_III"]["sections"]["Section_C"]["Passage_Two"]
        prompt = f"""你是一位大学英语四级考试专家。请分析以下四级阅读理解真题，给出：

1. **高频词汇表**：列出5个高频/重要词汇，给出音标、词性、中文释义、例句
2. **长难句分析**：找出2个最难理解的句子，拆解语法结构
3. **出题规律**：分析每道题的出题角度（细节题/主旨题/推理题），指出做题技巧
4. **文章主旨**：用中文一句话总结核心观点
5. **参考答案与逐题解析**：
   - 给出每道题的正确答案（只写字母，如 51.C）
   - 对每道题详细解析：正确答案在原文哪里找到依据（引用原文关键句）
   - 分析每个错误选项的干扰点（为什么错）

文章：
{p2['article']}

题目：
"""
        for num, q_text in p2["questions"].items():
            prompt += f"\n{num}. {q_text}"
            for opt in ['A', 'B', 'C', 'D']:
                opt_key = f"{num}_{opt}"
                if opt_key in p2.get('options', {}):
                    prompt += f"\n{opt}) {p2['options'][opt_key]}"
        return prompt

    elif section_type == "Part_IV Translation" and "Part_IV" in data:
        return f"""你是一位大学英语四级翻译专家。请分析以下中译英题目，给出：

1. **难点词汇**：列出5个翻译难点词汇，给出英文对应和用法
2. **句型分析**：拆解中文句子的结构，给出英文语序建议
3. **常见错误**：指出中国学生容易犯的中式英语错误
4. **参考译文**：给出一段准确、自然的英文翻译
5. **评分要点**：四级翻译评分标准，哪些地方容易扣分
6. **学生练习版**：给出一段带有 3-5 个填空的中文原文，让学生先练习翻译关键短语

中文原文：
{data['Part_IV']['content']}
"""
    return None


def perform_analysis(data, analyze_options, api_key, api_url, model):
    """执行 AI 分析"""
    results = {}
    section_config = {
        "Part_I Writing": ("✍️ Part I Writing 写作指导", True),
        "Part_II Listening": ("🎧 Part II Listening 听力分析", False),
        "Part_III Section_A": ("📝 Part III Section A 选词填空分析", False),
        "Part_III Section_B": ("📄 Part III Section B 段落匹配分析", False),
        "Part_III Section_C Passage_One": ("📖 Part III Passage One 分析结果", True),
        "Part_III Section_C Passage_Two": ("📖 Part III Passage Two 分析结果", False),
        "Part_IV Translation": ("🌐 Part IV Translation 翻译分析", False),
    }

    for option in analyze_options:
        if option not in section_config:
            continue

        title, expanded = section_config[option]
        prompt = build_prompt(option, data)
        if not prompt:
            continue

        with st.spinner(f"正在用 [{model}] 分析 {option}..."):
            result = call_ai_api(prompt, api_key, api_url, model)
            results[option] = result

        with st.expander(title, expanded=expanded):
            st.markdown(result)

            # 错题标注
            if "Section_A" in option:
                render_wrong_answer_checkboxes(26, 35, "sec_a")
            elif "Section_B" in option:
                render_wrong_answer_checkboxes(36, 45, "sec_b")
            elif "Passage_One" in option:
                render_wrong_answer_checkboxes(46, 50, "p1")
            elif "Passage_Two" in option:
                render_wrong_answer_checkboxes(51, 55, "p2")

            # 词汇收藏
            if "Section_A" in option:
                render_vocabulary_buttons(result, "sec_a")
            elif "Section_B" in option:
                render_vocabulary_buttons(result, "sec_b")
            elif "Passage_One" in option:
                render_vocabulary_buttons(result, "p1")
            elif "Passage_Two" in option:
                render_vocabulary_buttons(result, "p2")
            elif "Translation" in option:
                render_vocabulary_buttons(result, "trans")

    # 下载报告
    if results:
        report = "# 四级真题AI分析报告\n\n"
        for section, content in results.items():
            report += f"## {section}\n\n{content}\n\n---\n\n"

        st.download_button(
            label="📥 下载完整报告",
            data=report,
            file_name="cet4_analysis_report.md",
            mime="text/markdown"
        )

    return results


# ========== 页面配置 ==========
st.set_page_config(page_title="四级真题AI分析助手", layout="wide")
st.title("📚 四级真题AI分析助手")
st.caption("上传真题PDF，AI自动分析高频词汇、长难句、出题规律")

# ========== 侧边栏 ==========
with st.sidebar:
    st.header("⚙️ 配置")

    platform = st.selectbox(
        "选择API平台",
        list(PLATFORM_CONFIG.keys()),
        index=1,
        help="不同平台价格、速度、模型不同"
    )

    config = PLATFORM_CONFIG[platform]

    api_key = st.text_input(
        "API Key",
        type="password",
        placeholder=config["key_hint"],
        help=f"{config['note']}"
    )

    if platform == "自定义":
        api_url = st.text_input(
            "API URL",
            value="https://api.xxx.com/v1/chat/completions",
            help="输入你的OpenAI兼容API地址"
        )
        model = st.text_input(
            "模型名称",
            value="",
            placeholder="如: gpt-4o, claude-3-sonnet",
            help="输入该平台支持的模型名"
        )
    else:
        api_url = config["url"]
        model = st.selectbox(
            "选择模型",
            config["models"],
            help=f"当前平台: {platform}"
        )
        st.caption(f"URL: `{api_url}`")

    st.markdown("---")
    st.markdown("**支持格式**: CET-4真题PDF")
    st.markdown("**功能**: 自动提取Reading → AI分析 → 生成报告")

    # 学习记录面板
    render_sidebar_learning_records()

# ========== 主界面 ==========
uploaded_file = st.file_uploader("📄 上传四级真题PDF", type=["pdf"])

if uploaded_file:
    if not api_key:
        st.info("👈 请先在左侧边栏输入 API Key")
        st.stop()

    if platform == "自定义" and (not api_url or not model):
        st.warning("👈 自定义模式需要填写 API URL 和模型名称")
        st.stop()

    with st.spinner("正在解析PDF...请稍等"):
        try:
            data = parse_cet4_pdf(BytesIO(uploaded_file.read()))
            st.success("✅ PDF解析成功！")
        except Exception as e:
            st.error(f"解析失败: {e}")
            st.stop()

    # 显示解析概览
    render_pdf_overview(data)

    # 选择分析内容
    st.markdown("---")
    st.subheader("🎯 选择分析内容")

    analyze_options = st.multiselect(
        "勾选要分析的部分",
        ANALYZE_OPTIONS,
        default=["Part_III Section_C Passage_One"]
    )

    # 开始分析
    if st.button("🚀 开始AI分析", type="primary", key="btn_start_analysis"):
        perform_analysis(data, analyze_options, api_key, api_url, model)

elif not api_key:
    st.info("👈 请先在左侧边栏输入API Key")
elif not uploaded_file:
    st.info("👆 请上传四级真题PDF文件")

st.markdown("---")
st.caption("Made with ❤️ by 四级备考AI助手")