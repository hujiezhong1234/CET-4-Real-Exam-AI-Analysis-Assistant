import streamlit as st
import PyPDF2
import re
import json
import requests
from io import BytesIO

# ========== 全平台配置 ==========
PLATFORM_CONFIG = {
    "DeepSeek 官方": {
        "url": "https://api.deepseek.com/chat/completions",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "key_hint": "sk-... (platform.deepseek.com)",
        "note": "新用户送5000万Token"
    },
    "硅基流动": {
        "url": "https://api.siliconflow.cn/v1/chat/completions",
        "models": [
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1",
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2.5-14B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "Pro/ByteDance-Seed/豆包",
            "THUDM/glm-4-9b-chat",
        ],
        "key_hint": "sk-... (siliconflow.cn)",
        "note": "新用户送2000万Token，有永久免费模型"
    },
    "阿里云百炼": {
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "models": ["qwen-max", "qwen-plus", "qwen-turbo"],
        "key_hint": "sk-... (dashscope.aliyun.com)",
        "note": "需开通服务，按量付费"
    },
    "OpenAI": {
        "url": "https://api.openai.com/v1/chat/completions",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        "key_hint": "sk-... (platform.openai.com)",
        "note": "需海外支付，较贵"
    },
    "自定义": {
        "url": "",
        "models": [],
        "key_hint": "你的API Key",
        "note": "支持任何OpenAI兼容API"
    }
}

# ========== 页面配置 ==========
st.set_page_config(page_title="四级真题AI分析助手", layout="wide")
st.title("📚 四级真题AI分析助手")
st.caption("上传真题PDF，AI自动分析高频词汇、长难句、出题规律")


# ========== PDF解析函数 ==========
def parse_cet4_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    reading_start = full_text.find("Section A")
    reading_end = full_text.find("KEYS")
    if reading_end == -1:
        reading_end = full_text.find("Part IV")
    reading_text = full_text[reading_start:reading_end].strip()

    # Section A
    sec_a_match = re.search(r'Section\s+A.*?(?=Section\s+B|$)', reading_text, re.DOTALL)
    sec_a = {"article": "", "wordbank": ""}
    if sec_a_match:
        text = sec_a_match.group(0)
        article_match = re.search(r'Directions:.*?\n(.*?)(?=A\)\s+adapt)', text, re.DOTALL)
        article = article_match.group(1).strip() if article_match else ""
        wordbank_lines = re.findall(r'[A-O]\)\s+\w+', text)
        sec_a = {"article": article, "wordbank": '\n'.join(wordbank_lines)}

    # Passage One
    p1_match = re.search(r'Passage\s+One.*?(?=Passage\s+Two|$)', reading_text, re.DOTALL)
    passage_one = {"article": "", "questions": {}}
    if p1_match:
        text = p1_match.group(0)
        article_start = text.find("following passage.")
        if article_start != -1:
            article_start = text.find('\n', article_start) + 1
            first_q = re.search(r'\n\s*46\.', text[article_start:])
            if first_q:
                article = text[article_start:article_start + first_q.start()].strip()
            else:
                article = text[article_start:].strip()
        else:
            article = ""

        questions = {}
        for num in range(46, 51):
            pattern = rf'{num}\.(.*?)(?={num + 1}\.|$)' if num < 50 else rf'{num}\.(.*?)(?=$)'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                questions[str(num)] = match.group(1).strip()

        passage_one = {"article": article, "questions": questions}

    # Passage Two
    p2_match = re.search(r'Passage\s+Two.*?(?=$)', reading_text, re.DOTALL)
    passage_two = {"article": "", "questions": {}}
    if p2_match:
        text = p2_match.group(0)
        article_start = text.find("following passage.")
        if article_start != -1:
            article_start = text.find('\n', article_start) + 1
            first_q = re.search(r'\n\s*51\.', text[article_start:])
            if first_q:
                article = text[article_start:article_start + first_q.start()].strip()
            else:
                article = text[article_start:].strip()
        else:
            article = ""

        questions = {}
        for num in range(51, 56):
            pattern = rf'{num}\.(.*?)(?={num + 1}\.|$)' if num < 55 else rf'{num}\.(.*?)(?=$)'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                questions[str(num)] = match.group(1).strip()

        passage_two = {"article": article, "questions": questions}

    return {
        "Section_A": sec_a,
        "Passage_One": passage_one,
        "Passage_Two": passage_two
    }


# ========== AI分析函数 ==========
def analyze_with_ai(article, questions, api_key, api_url, model):
    prompt = f"""你是一位大学英语四级考试专家。请分析以下四级阅读理解真题，给出：

1. **高频词汇表**：列出5个高频/重要词汇，给出音标、词性、中文释义、例句
2. **长难句分析**：找出2个最难理解的句子，拆解语法结构
3. **出题规律**：分析每道题的出题角度（细节题/主旨题/推理题），指出做题技巧
4. **文章主旨**：用中文一句话总结核心观点

文章：
{article}

题目：
"""
    for num, q_text in questions.items():
        prompt += f"\n{num}. {q_text}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ 分析失败 (状态码: {response.status_code})\n\n```\n{response.text[:500]}\n```"
    except Exception as e:
        return f"❌ 请求异常: {str(e)}"


# ========== 侧边栏 ==========
with st.sidebar:
    st.header("⚙️ 配置")

    # 选择平台
    platform = st.selectbox(
        "选择API平台",
        list(PLATFORM_CONFIG.keys()),
        index=1,  # 默认硅基流动
        help="不同平台价格、速度、模型不同"
    )

    config = PLATFORM_CONFIG[platform]

    # API Key
    api_key = st.text_input(
        "API Key",
        type="password",
        placeholder=config["key_hint"],
        help=f"{config['note']}"
    )

    # API URL
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

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("选词填空文章", f"{len(data['Section_A']['article'])} 字")
    with col2:
        st.metric("Passage One", f"{len(data['Passage_One']['article'])} 词")
    with col3:
        st.metric("Passage Two", f"{len(data['Passage_Two']['article'])} 词")

    st.markdown("---")
    st.subheader("🎯 选择分析内容")

    analyze_options = st.multiselect(
        "勾选要分析的部分",
        ["Passage One (46-50题)", "Passage Two (51-55题)", "Section A 选词填空"],
        default=["Passage One (46-50题)"]
    )

    if st.button("🚀 开始AI分析", type="primary"):
        results = {}

        if "Passage One (46-50题)" in analyze_options:
            with st.spinner(f"正在用 [{model}] 分析 Passage One..."):
                result = analyze_with_ai(
                    data["Passage_One"]["article"],
                    data["Passage_One"]["questions"],
                    api_key,
                    api_url,
                    model
                )
                results["Passage One"] = result
                with st.expander("📖 Passage One 分析结果", expanded=True):
                    st.markdown(result)

        if "Passage Two (51-55题)" in analyze_options:
            with st.spinner(f"正在用 [{model}] 分析 Passage Two..."):
                result = analyze_with_ai(
                    data["Passage_Two"]["article"],
                    data["Passage_Two"]["questions"],
                    api_key,
                    api_url,
                    model
                )
                results["Passage Two"] = result
                with st.expander("📖 Passage Two 分析结果"):
                    st.markdown(result)

        if "Section A 选词填空" in analyze_options:
            with st.spinner(f"正在用 [{model}] 分析 Section A..."):
                prompt = f"""分析以下四级选词填空真题：
1. 列出文章中的5个高频词汇及释义
2. 分析每个空(26-35)应该填什么词性/词义
3. 给出解题技巧

文章：{data['Section_A']['article']}

选项：{data['Section_A']['wordbank']}"""

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }

                try:
                    response = requests.post(api_url, headers=headers, json=payload, timeout=60)
                    if response.status_code == 200:
                        result = response.json()["choices"][0]["message"]["content"]
                    else:
                        result = f"❌ 失败: {response.status_code}\n```\n{response.text[:500]}\n```"
                except Exception as e:
                    result = f"❌ 异常: {str(e)}"

                results["Section A"] = result
                with st.expander("📝 Section A 分析结果"):
                    st.markdown(result)

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

elif not api_key:
    st.info("👈 请在左侧边栏输入API Key")
elif not uploaded_file:
    st.info("👆 请上传四级真题PDF文件")

st.markdown("---")
st.caption("Made with ❤️ by 四级备考AI助手")