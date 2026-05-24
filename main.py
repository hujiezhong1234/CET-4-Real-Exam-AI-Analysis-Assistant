import PyPDF2
import re
import json

pdf_path = "cet4_2025_06_3.pdf"

# 读取PDF
with open(pdf_path, 'rb') as file:
    reader = PyPDF2.PdfReader(file)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

# 找到Reading部分
reading_start = full_text.find("Section A")
reading_end = full_text.find("KEYS")
if reading_end == -1:
    reading_end = full_text.find("Part IV")
reading_text = full_text[reading_start:reading_end].strip()

# 按Section分割
section_a_match = re.search(r'Section\s+A.*?(?=Section\s+B|$)', reading_text, re.DOTALL)
section_b_match = re.search(r'Section\s+B.*?(?=Section\s+C|$)', reading_text, re.DOTALL)
section_c_match = re.search(r'Section\s+C.*?(?=KEYS|Part\s+IV|$)', reading_text, re.DOTALL)

sections = {}

# ========== Section A ==========
if section_a_match:
    text = section_a_match.group(0)
    # 提取文章：Directions之后到word bank之前
    # word bank以 "A) adapt" 开头
    article_match = re.search(r'Directions:.*?\n(.*?)(?=A\)\s+adapt)', text, re.DOTALL)
    article = article_match.group(1).strip() if article_match else ""

    # 提取word bank：A) 到 O)
    wordbank_lines = re.findall(r'[A-O]\)\s+\w+', text)
    wordbank = '\n'.join(wordbank_lines)

    sections["Section_A"] = {
        "type": "选词填空",
        "article": article,
        "wordbank": wordbank
    }

# ========== Section B ==========
if section_b_match:
    text = section_b_match.group(0)

    # 提取标题
    title_match = re.search(r'"([^"]+)"', text)
    title = title_match.group(1) if title_match else ""

    # 提取段落 A-N)：格式是 "A)" 或换行后跟"A)"
    # 先清理文本，统一换行
    clean_text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 提取段落：找 "A)" 到 "B)" 之间的内容
    paragraphs = {}
    for letter in 'ABCDEFGHIJKLMN':
        pattern = rf'{letter}\)(.*?)(?=[A-N]\)|$)'
        match = re.search(pattern, clean_text, re.DOTALL)
        if match:
            # 找到下一个段落标记的位置，截断
            content = match.group(1).strip()
            paragraphs[letter] = content

    # 提取题目 36-45：格式是 "36.内容" 或 "36 内容"
    questions = {}
    for num in range(36, 46):
        pattern = rf'{num}\.?(.*?)(?={num + 1}\.|$)' if num < 45 else rf'{num}\.?(.*?)(?=$)'
        match = re.search(pattern, clean_text, re.DOTALL)
        if match:
            questions[str(num)] = match.group(1).strip()

    sections["Section_B"] = {
        "type": "段落匹配",
        "title": title,
        "paragraphs": paragraphs,
        "questions": questions
    }

# ========== Section C ==========
if section_c_match:
    text = section_c_match.group(0)
    clean_text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 分割Passage One和Passage Two
    p1_split = clean_text.split("Passage One")
    p2_split = clean_text.split("Passage Two")

    p1_text = ""
    p2_text = ""

    if len(p1_split) > 1:
        # Passage One内容：从"Passage One"到"Passage Two"
        p1_content = p1_split[1]
        if "Passage Two" in p1_content:
            p1_text = p1_content[:p1_content.find("Passage Two")].strip()
        else:
            p1_text = p1_content.strip()

    if len(p2_split) > 1:
        # Passage Two内容：从"Passage Two"到结尾
        p2_text = p2_split[1].strip()


    def parse_passage(passage_text, name):
        if not passage_text:
            return {"article": "", "questions": {}, "options": {}}

        # 找到文章正文：在"following passage."之后，第一个题号之前
        article_start = passage_text.find("following passage.")
        if article_start == -1:
            article_start = passage_text.find("Questions")

        if article_start != -1:
            article_start = passage_text.find('\n', article_start) + 1
            # 找到第一个题号位置
            first_question = re.search(r'\n\s*46\.|\n\s*51\.', passage_text[article_start:])
            if first_question:
                article_end = article_start + first_question.start()
                article = passage_text[article_start:article_end].strip()
            else:
                article = passage_text[article_start:].strip()
        else:
            article = ""

        # 提取题目和选项
        # 格式：46.What do we learn... A)... B)... C)... D)... 47.
        questions = {}
        options = {}

        # 匹配 "46." 到 "47." 之间的所有内容
        q_matches = list(re.finditer(r'(\d{2})\.(.*?)(?=\d{2}\.|$)', passage_text, re.DOTALL))

        for match in q_matches:
            num = match.group(1)
            q_content = match.group(2).strip()
            questions[num] = q_content

            # 在这个题目内容里提取选项 A) B) C) D)
            opts = re.findall(r'([A-D])\)(.*?)(?=[A-D]\)|$)', q_content, re.DOTALL)
            for letter, opt_content in opts:
                options[f"{num}_{letter}"] = opt_content.strip()

        return {
            "article": article,
            "questions": questions,
            "options": options
        }


    sections["Section_C"] = {
        "type": "阅读理解",
        "passage_one": parse_passage(p1_text, "Passage One"),
        "passage_two": parse_passage(p2_text, "Passage Two")
    }

# ========== 显示结果 ==========
for sec_name, sec_data in sections.items():
    print(f"\n{'=' * 60}")
    print(f"【{sec_name}】 {sec_data['type']}")
    print(f"{'=' * 60}")

    if sec_name == "Section_A":
        print(f"文章长度: {len(sec_data['article'])} 字")
        print(f"文章前200字: {sec_data['article'][:200]}...")
        print(f"Word bank选项数: {len(sec_data['wordbank'].split(chr(10)))}")

    elif sec_name == "Section_B":
        print(f"标题: {sec_data['title']}")
        print(f"段落数: {len(sec_data['paragraphs'])}")
        if sec_data['paragraphs']:
            print(f"段落A前100字: {sec_data['paragraphs'].get('A', '')[:100]}...")
        print(f"题目数: {len(sec_data['questions'])}")
        if sec_data['questions']:
            print(f"题目36: {sec_data['questions'].get('36', '')[:100]}...")

    elif sec_name == "Section_C":
        p1 = sec_data['passage_one']
        p2 = sec_data['passage_two']
        print(f"Passage One 文章: {len(p1['article'])} 字")
        print(f"Passage One 文章前200字: {p1['article'][:200]}...")
        print(f"Passage One 题目: {list(p1['questions'].keys())}")
        print(f"Passage One 选项数: {len(p1['options'])}")
        print(f"Passage Two 文章: {len(p2['article'])} 字")
        print(f"Passage Two 文章前200字: {p2['article'][:200]}...")
        print(f"Passage Two 题目: {list(p2['questions'].keys())}")
        print(f"Passage Two 选项数: {len(p2['options'])}")

# 保存
with open("reading_questions.json", "w", encoding="utf-8") as f:
    json.dump(sections, f, ensure_ascii=False, indent=2)

print(f"\n✅ 已保存到 reading_questions.json")