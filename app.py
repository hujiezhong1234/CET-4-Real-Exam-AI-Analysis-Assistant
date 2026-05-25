import streamlit as st
import PyPDF2
import re
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


# ========== PDF解析函数 ==========
def parse_cet4_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    full_text = full_text.replace('\r\n', '\n').replace('\r', '\n')

    # 找到所有 Part 的位置，但过滤掉答案页的重复 Part
    part_pattern = r'Part\s+(I{1,3}|IV)\b'
    all_matches = list(re.finditer(part_pattern, full_text))

    # 过滤：保留第一次出现的每个 Part，跳过答案页的重复
    seen_parts = set()
    part_matches = []
    for match in all_matches:
        part_num = match.group(1)
        if part_num not in seen_parts:
            seen_parts.add(part_num)
            part_matches.append(match)

    parts = {}

    for i, match in enumerate(part_matches):
        part_num = match.group(1)
        start_pos = match.start()

        if i + 1 < len(part_matches):
            end_pos = part_matches[i + 1].start()
        else:
            end_pos = len(full_text)

        part_text = full_text[start_pos:end_pos].strip()

        # 提取 Part 名称：找 "Part X Name" 格式
        # 第一行应该是 "Part I Writing (30 minutes)" 这种
        first_line = part_text.split('\n')[0].strip()
        part_name = ""

        # 从第一行提取名称
        name_match = re.search(r'Part\s+' + part_num + r'\s+(.+?)(?:\s*\(|$)', first_line)
        if name_match:
            part_name = name_match.group(1).strip()

        part_key = f"Part_{part_num}"

        # 检查是否有 Section
        section_a_match = re.search(r'Section\s+A', part_text)

        if not section_a_match:
            # 无 Section：Writing, Listening, Translation
            content_lines = part_text.split('\n')[1:]
            content = '\n'.join(content_lines).strip()

            # 过滤掉 KEYS 及之后的内容
            keys_pos = content.find("KEYS")
            if keys_pos != -1:
                content = content[:keys_pos].strip()

            parts[part_key] = {
                "name": part_name,
                "content": content
            }
        else:
            # 有 Section：Reading
            # 只提取到 KEYS 之前（如果 KEYS 在当前 Part 内）
            reading_end = part_text.find("KEYS")
            if reading_end != -1:
                reading_text = part_text[:reading_end].strip()
            else:
                reading_text = part_text

            sections = {}

            # Section A
            sec_a_text = extract_section(reading_text, 'A', 'B')
            if sec_a_text:
                article_match = re.search(r'Directions:.*?\n(.*?)(?=A\)\s+adapt)', sec_a_text, re.DOTALL)
                article = article_match.group(1).strip() if article_match else ""
                wordbank_lines = re.findall(r'[A-O]\)\s+\w+', sec_a_text)
                sections["Section_A"] = {
                    "article": article,
                    "wordbank": '\n'.join(wordbank_lines)
                }

            # Section B
            sec_b_text = extract_section(reading_text, 'B', 'C')
            if sec_b_text:
                title_match = re.search(r'Section\s+B.*?Directions:.*?\n\s*"?([^"\n]{20,100})"?', sec_b_text, re.DOTALL)
                if not title_match:
                    # 备选：找第一个大写的长句子作为标题
                    lines = sec_b_text.split('\n')
                    for line in lines[2:]:  # 跳过 Section B 和 Directions
                        line = line.strip()
                        if len(line) > 20 and line[0].isupper():
                            title = line
                            break
                    else:
                        title = ""
                else:
                    title = title_match.group(1).strip()
                title = title_match.group(1) if title_match else ""

                paragraphs = {}
                for letter in 'ABCDEFGHIJKLMN':
                    para_pattern = rf'{letter}\)(.*?)(?=[A-N]\)|\n\s*3[6-9]\.|\n\s*4[0-5]\.|$)'
                    para_match = re.search(para_pattern, sec_b_text, re.DOTALL)
                    if para_match:
                        para_content = para_match.group(1).strip()
                        q_start = re.search(r'\n\s*3[6-9]\.|\n\s*4[0-5]\.', para_content)
                        if q_start:
                            para_content = para_content[:q_start.start()].strip()
                        paragraphs[letter] = para_content

                questions = {}
                for num in range(36, 46):
                    q_pattern = rf'{num}\.?(.*?)(?={num + 1}\.|$)' if num < 45 else rf'{num}\.?(.*?)(?=$)'
                    q_match = re.search(q_pattern, sec_b_text, re.DOTALL)
                    if q_match:
                        questions[str(num)] = q_match.group(1).strip()

                sections["Section_B"] = {
                    "title": title,
                    "paragraphs": paragraphs,
                    "questions": questions
                }

            # Section C
            sec_c_text = extract_section(reading_text, 'C', None)
            if sec_c_text:
                passages = {}

                p1_match = re.search(r'Passage\s+One.*?(?=Passage\s+Two|$)', sec_c_text, re.DOTALL)
                if p1_match:
                    passages["Passage_One"] = parse_passage(p1_match.group(0), 46)

                p2_match = re.search(r'Passage\s+Two.*?(?=$)', sec_c_text, re.DOTALL)
                if p2_match:
                    passages["Passage_Two"] = parse_passage(p2_match.group(0), 51)

                sections["Section_C"] = passages

            parts[part_key] = {
                "name": part_name,
                "sections": sections
            }

    return parts


def extract_section(text, current, next_section):
    """提取指定Section的文本"""
    if current == 'C':
        pattern = rf'Section\s+{current}.*?(?=KEYS|Part\s+IV|$)'
    else:
        pattern = rf'Section\s+{current}.*?(?=Section\s+{next_section}|KEYS|Part\s+IV|$)'

    match = re.search(pattern, text, re.DOTALL)
    return match.group(0) if match else None


def parse_passage(passage_text, start_q_num):
    """解析Passage"""
    # 调试：看看传进来的是什么
    if not passage_text or len(passage_text) < 50:
        return {"article": "", "questions": {}}

    # 尝试多种方式找文章开始
    article_start = passage_text.find("following passage.")
    if article_start == -1:
        # 备选：找 "passage." 或第一个换行后的大写句子
        article_start = passage_text.lower().find("passage.")

    if article_start == -1:
        # 再备选：跳过前两行（Passage Two + Questions...），后面就是文章
        lines = passage_text.split('\n')
        if len(lines) > 2:
            # 从第三行开始找，第一个非空且不是题目的行
            for i, line in enumerate(lines[2:], 2):
                if line.strip() and not line.strip().startswith('Questions'):
                    article_start = passage_text.find(line)
                    break
            else:
                return {"article": "", "questions": {}}
        else:
            return {"article": "", "questions": {}}

    # 找到文章开始位置（换行后）
    nl_pos = passage_text.find('\n', article_start)
    if nl_pos != -1:
        article_start = nl_pos + 1
    else:
        article_start = article_start + len("following passage.")

    search_text = passage_text[article_start:]

    # 找第一个题号
    first_q = re.search(rf'\n?\s*{start_q_num}\s*\.', search_text)
    if first_q:
        article = search_text[:first_q.start()].strip()
    else:
        # 没题号？全部当文章
        article = search_text.strip()

    # 提取题目
    questions = {}
    for num in range(start_q_num, start_q_num + 5):
        pattern = rf'{num}\s*\.(.*?)(?={num + 1}\s*\.|$)' if num < start_q_num + 4 else rf'{num}\s*\.(.*?)(?=$)'
        match = re.search(pattern, passage_text, re.DOTALL)
        if match:
            questions[str(num)] = match.group(1).strip()

    return {"article": article, "questions": questions}


# ========== AI分析函数 ==========
def call_ai_api(prompt, api_key, api_url, model):
    """通用AI调用"""
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
            return f"❌ 失败: {response.status_code}\n```\n{response.text[:500]}\n```"
    except Exception as e:
        return f"❌ 异常: {str(e)}"


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

    # 显示解析结果概览
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
                # 无Section的Part
                content = part_data["content"]
                st.text_area("内容", content[:800] + ("..." if len(content) > 800 else ""),
                             height=150, disabled=True, label_visibility="collapsed")

            elif "sections" in part_data:
                # 有Section的Part（Reading）
                sections = part_data["sections"]

                # Section A
                if "Section_A" in sections:
                    with st.container():
                        st.markdown("**📝 Section A - 选词填空**")
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            article = sections["Section_A"]["article"]
                            st.text_area("文章", article[:500] + "...", height=100, disabled=True)
                        with col2:
                            st.text_area("选项", sections["Section_A"]["wordbank"], height=100, disabled=True)

                # Section B
                if "Section_B" in sections:
                    with st.container():
                        st.markdown("**📄 Section B - 段落匹配**")
                        st.write(f"**标题**: {sections['Section_B']['title']}")

                        # 显示每个段落（可折叠）
                        st.write("**段落列表**：")
                        for letter, para in sections['Section_B']['paragraphs'].items():
                            with st.expander(f"段落 {letter}"):
                                st.write(para)

                        # 显示题目
                        st.write(f"**题目数**: {len(sections['Section_B']['questions'])}")

                # Section C
                if "Section_C" in sections:
                    with st.container():
                        st.markdown("**📖 Section C - 阅读理解**")
                        for passage_name, passage_data in sections["Section_C"].items():
                            passage_display = passage_name.replace("_", " ")

                            # 文章摘要（前100字）
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

    # 选择分析内容
    st.markdown("---")
    st.subheader("🎯 选择分析内容")

    analyze_options = st.multiselect(
        "勾选要分析的部分",
        [
            "Part_I Writing",
            "Part_II Listening",
            "Part_III Section_A",
            "Part_III Section_B",
            "Part_III Section_C Passage_One",
            "Part_III Section_C Passage_Two",
            "Part_IV Translation"
        ],
        default=["Part_III Section_C Passage_One"]
    )

    if st.button("🚀 开始AI分析", type="primary"):
        results = {}

        # Part I Writing
        if "Part_I Writing" in analyze_options and "Part_I" in data:
            with st.spinner(f"正在用 [{model}] 分析 Writing..."):
                prompt = f"""你是一位大学英语四级写作专家。请分析以下四级写作题目，给出：

1. **题目解读**：这道题要求写什么类型的文章（议论文？说明文？）
2. **文章结构**：推荐的三段式结构（开头-主体-结尾）
3. **高分句型**：给出3-5个可以直接套用的万能句型
4. **常用词汇**：列出5个这个话题下的高频表达
5. **范文框架**：给出一个120-180词的范文大纲

题目：
{data['Part_I']['content']}
"""
                result = call_ai_api(prompt, api_key, api_url, model)
                results["Part_I Writing"] = result
                with st.expander("✍️ Part I Writing 写作指导", expanded=True):
                    st.markdown(result)

        # Part II Listening
        if "Part_II Listening" in analyze_options and "Part_II" in data:
            with st.spinner(f"正在用 [{model}] 分析 Listening..."):
                prompt = f"""你是一位大学英语四级听力专家。请分析以下听力部分信息：

1. **题型说明**：这部分是什么题型
2. **备考建议**：针对这类听力的练习方法
3. **常见陷阱**：听力中容易出错的地方

内容：
{data['Part_II']['content']}
"""
                result = call_ai_api(prompt, api_key, api_url, model)
                results["Part_II Listening"] = result
                with st.expander("🎧 Part II Listening 听力分析"):
                    st.markdown(result)

        # Part III Section A
        if "Part_III Section_A" in analyze_options and "Part_III" in data:
            with st.spinner(f"正在用 [{model}] 分析 Section A..."):
                sec_a = data["Part_III"]["sections"]["Section_A"]
                prompt = f"""分析以下四级选词填空真题：
1. 列出文章中的5个高频词汇及释义
2. 分析每个空(26-35)应该填什么词性/词义
3. 给出解题技巧

文章：{sec_a['article']}

选项：{sec_a['wordbank']}"""

                result = call_ai_api(prompt, api_key, api_url, model)
                results["Part_III Section_A"] = result
                with st.expander("📝 Part III Section A 选词填空分析"):
                    st.markdown(result)

        # Part III Section B
        if "Part_III Section_B" in analyze_options and "Part_III" in data:
            with st.spinner(f"正在用 [{model}] 分析 Section B..."):
                sec_b = data["Part_III"]["sections"]["Section_B"]
                prompt = f"""你是一位大学英语四级阅读专家。请分析以下段落匹配真题：

1. **文章主旨**：用一句话概括这篇文章讲什么
2. **段落分析**：分析每个段落的核心内容
3. **匹配技巧**：做段落匹配题的解题策略
4. **高频词汇**：列出5个重要词汇

标题：{sec_b['title']}

段落：
"""
                for letter, para in sec_b["paragraphs"].items():
                    prompt += f"\n{letter}) {para[:200]}..."

                prompt += f"\n\n题目：\n"
                for num, q_text in sec_b["questions"].items():
                    prompt += f"\n{num}. {q_text}"

                result = call_ai_api(prompt, api_key, api_url, model)
                results["Part_III Section_B"] = result
                with st.expander("📄 Part III Section B 段落匹配分析"):
                    st.markdown(result)

        # Part III Section C Passage One
        if "Part_III Section_C Passage_One" in analyze_options and "Part_III" in data:
            with st.spinner(f"正在用 [{model}] 分析 Passage One..."):
                p1 = data["Part_III"]["sections"]["Section_C"]["Passage_One"]
                prompt = f"""你是一位大学英语四级考试专家。请分析以下四级阅读理解真题，给出：

1. **高频词汇表**：列出5个高频/重要词汇，给出音标、词性、中文释义、例句
2. **长难句分析**：找出2个最难理解的句子，拆解语法结构
3. **出题规律**：分析每道题的出题角度（细节题/主旨题/推理题），指出做题技巧
4. **文章主旨**：用中文一句话总结核心观点

文章：
{p1['article']}

题目：
"""
                for num, q_text in p1["questions"].items():
                    prompt += f"\n{num}. {q_text}"

                result = call_ai_api(prompt, api_key, api_url, model)
                results["Part_III Passage_One"] = result
                with st.expander("📖 Part III Passage One 分析结果", expanded=True):
                    st.markdown(result)

        # Part III Section C Passage Two
        if "Part_III Section_C Passage_Two" in analyze_options and "Part_III" in data:
            with st.spinner(f"正在用 [{model}] 分析 Passage Two..."):
                p2 = data["Part_III"]["sections"]["Section_C"]["Passage_Two"]
                prompt = f"""你是一位大学英语四级考试专家。请分析以下四级阅读理解真题，给出：

1. **高频词汇表**：列出5个高频/重要词汇，给出音标、词性、中文释义、例句
2. **长难句分析**：找出2个最难理解的句子，拆解语法结构
3. **出题规律**：分析每道题的出题角度（细节题/主旨题/推理题），指出做题技巧
4. **文章主旨**：用中文一句话总结核心观点

文章：
{p2['article']}

题目：
"""
                for num, q_text in p2["questions"].items():
                    prompt += f"\n{num}. {q_text}"

                result = call_ai_api(prompt, api_key, api_url, model)
                results["Part_III Passage_Two"] = result
                with st.expander("📖 Part III Passage Two 分析结果"):
                    st.markdown(result)

        # Part IV Translation
        if "Part_IV Translation" in analyze_options and "Part_IV" in data:
            with st.spinner(f"正在用 [{model}] 分析 Translation..."):
                prompt = f"""你是一位大学英语四级翻译专家。请分析以下中译英题目，给出：

1. **难点词汇**：列出5个翻译难点词汇，给出英文对应和用法
2. **句型分析**：拆解中文句子的结构，给出英文语序建议
3. **常见错误**：指出中国学生容易犯的中式英语错误
4. **参考译文**：给出一段准确、自然的英文翻译
5. **评分要点**：四级翻译评分标准，哪些地方容易扣分

中文原文：
{data['Part_IV']['content']}
"""
                result = call_ai_api(prompt, api_key, api_url, model)
                results["Part_IV Translation"] = result
                with st.expander("🌐 Part IV Translation 翻译分析"):
                    st.markdown(result)

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

elif not api_key:
    st.info("👈 请先在左侧边栏输入API Key")
elif not uploaded_file:
    st.info("👆 请上传四级真题PDF文件")

st.markdown("---")
st.caption("Made with ❤️ by 四级备考AI助手")