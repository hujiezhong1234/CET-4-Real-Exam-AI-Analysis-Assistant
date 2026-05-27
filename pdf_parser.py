"""PDF 解析模块"""

import re
import PyPDF2


def parse_cet4_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    full_text = full_text.replace('\r\n', '\n').replace('\r', '\n')
    full_text = re.sub(r'<[^>]+>', '', full_text)

    parts = {}

    # Part I: Writing
    writing_match = re.search(r'Part\s+I.*?(?=Part\s+II|$)', full_text, re.DOTALL)
    if writing_match:
        writing_text = writing_match.group(0)
        lines = writing_text.split('\n')
        content_lines = []
        for line in lines[1:]:
            if line.strip() and not line.strip().startswith('('):
                content_lines.append(line)
        parts["Part_I"] = {
            "name": "Writing",
            "content": '\n'.join(content_lines).strip()
        }

    # Part II: Listening
    listening_match = re.search(r'Part\s+II.*?(?=Part\s+III|Part\s+IV|$)', full_text, re.DOTALL)
    if listening_match:
        listening_text = listening_match.group(0)
        has_full_listening = 'you will hear' in listening_text or 'Questions 1' in listening_text
        keys_pos = listening_text.find("KEYS")
        if keys_pos != -1:
            listening_text = listening_text[:keys_pos].strip()

        lines = listening_text.split('\n')
        content_lines = []
        for line in lines[1:]:
            line_stripped = line.strip()
            if re.match(r'^[\d\s]+$', line_stripped):
                continue
            if re.match(r'^[A-D\s]+$', line_stripped):
                continue
            if line_stripped.startswith('KEYS'):
                continue
            if line_stripped == 'Listening Comprehension':
                continue
            content_lines.append(line)

        parts["Part_II"] = {
            "name": "Listening Comprehension",
            "content": '\n'.join(content_lines).strip(),
            "has_full_audio": has_full_listening
        }

    # Part III: Reading
    reading_start = None
    part3_match = re.search(r'Part\s+III.*?(Section\s+A)', full_text, re.DOTALL)
    if part3_match:
        section_a_start = part3_match.start(1)
        section_a_text = full_text[section_a_start:section_a_start + 2000]
        if 'word bank' in section_a_text or re.search(r'A\)\s+\w+.*B\)\s+\w+', section_a_text):
            reading_start = section_a_start

    if reading_start is None:
        for match in re.finditer(r'Section\s+A', full_text):
            check_text = full_text[match.start():match.start() + 2000]
            if 'word bank' in check_text or re.search(r'A\)\s+\w+.*B\)\s+\w+', check_text):
                reading_start = match.start()
                break

    if reading_start:
        part4_match = re.search(r'Part\s+IV', full_text[reading_start:])
        if part4_match:
            reading_end = reading_start + part4_match.start()
        else:
            reading_end = len(full_text)

        reading_text = full_text[reading_start:reading_end].strip()
        keys_pos = reading_text.find("KEYS")
        if keys_pos != -1:
            reading_text = reading_text[:keys_pos].strip()

        sections = {}

        sec_a_text = _extract_section(reading_text, 'A', 'B')
        if sec_a_text:
            article_match = re.search(r'Directions:.*?\n(.*?)(?=A\)\s+\w+)', sec_a_text, re.DOTALL)
            article = article_match.group(1).strip() if article_match else ""
            wordbank_lines = re.findall(r'[A-O]\)\s+\w+', sec_a_text)
            sections["Section_A"] = {
                "article": article,
                "wordbank": '\n'.join(wordbank_lines)
            }

        sec_b_text = _extract_section(reading_text, 'B', 'C')
        if sec_b_text:
            title_match = re.search(r'"([^"]+)"', sec_b_text)
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

        sec_c_text = _extract_section(reading_text, 'C', None)
        if sec_c_text:
            passages = {}
            p1_match = re.search(r'Passage\s+One.*?(?=Passage\s+Two|$)', sec_c_text, re.DOTALL)
            if p1_match:
                passages["Passage_One"] = _parse_passage(p1_match.group(0), 46)

            p2_match = re.search(r'Passage\s+Two.*?(?=$)', sec_c_text, re.DOTALL)
            if p2_match:
                passages["Passage_Two"] = _parse_passage(p2_match.group(0), 51)

            sections["Section_C"] = passages

        parts["Part_III"] = {
            "name": "Reading Comprehension",
            "sections": sections
        }

    # Part IV: Translation
    translation_match = re.search(r'Part\s+IV.*?(?=KEYS|$)', full_text, re.DOTALL)
    if translation_match:
        trans_text = translation_match.group(0)
        keys_pos = trans_text.find("KEYS")
        if keys_pos != -1:
            trans_text = trans_text[:keys_pos].strip()

        lines = trans_text.split('\n')
        content_lines = []
        for line in lines[1:]:
            content_lines.append(line)

        content = '\n'.join(content_lines).strip()
        chinese_match = re.search(r'[\u4e00-\u9fff].*?(?=$)', content, re.DOTALL)
        if chinese_match:
            content = chinese_match.group(0).strip()

        parts["Part_IV"] = {
            "name": "Translation",
            "content": content
        }

    return parts


def _extract_section(text, current, next_section):
    if current == 'C':
        pattern = rf'Section\s+{current}.*?(?=KEYS|Part\s+IV|$)'
    else:
        pattern = rf'Section\s+{current}.*?(?=Section\s+{next_section}|KEYS|Part\s+IV|$)'
    match = re.search(pattern, text, re.DOTALL)
    return match.group(0) if match else None


def _parse_passage(passage_text, start_q_num):
    if not passage_text or len(passage_text) < 50:
        return {"article": "", "questions": {}, "options": {}}

    article_start = passage_text.find("following passage.")
    if article_start == -1:
        article_start = passage_text.lower().find("passage.")

    if article_start == -1:
        lines = passage_text.split('\n')
        if len(lines) > 2:
            for i, line in enumerate(lines[2:], 2):
                if line.strip() and not line.strip().startswith('Questions'):
                    article_start = passage_text.find(line)
                    break
            else:
                return {"article": "", "questions": {}, "options": {}}
        else:
            return {"article": "", "questions": {}, "options": {}}

    nl_pos = passage_text.find('\n', article_start)
    if nl_pos != -1:
        article_start = nl_pos + 1
    else:
        article_start = article_start + len("following passage.")

    search_text = passage_text[article_start:]
    first_q = re.search(rf'\n?\s*{start_q_num}\s*\.', search_text)
    if first_q:
        article = search_text[:first_q.start()].strip()
    else:
        article = search_text.strip()

    questions = {}
    options = {}
    for num in range(start_q_num, start_q_num + 5):
        pattern = rf'{num}\s*\.(.*?)(?={num + 1}\s*\.|$)' if num < start_q_num + 4 else rf'{num}\s*\.(.*?)(?=$)'
        match = re.search(pattern, passage_text, re.DOTALL)
        if match:
            q_content = match.group(1).strip()
            opts = re.findall(r'([A-D])\)(.*?)(?=[A-D]\)|$)', q_content, re.DOTALL)
            if not opts:
                opts = re.findall(r'([A-D])\.(.*?)(?=[A-D]\.|$)', q_content, re.DOTALL)
            if not opts:
                opts = re.findall(r'([A-D])\s+(.*?)(?=[A-D]\s+|$)', q_content, re.DOTALL)

            for letter, opt_content in opts:
                options[f"{num}_{letter}"] = opt_content.strip()

            opt_start = re.search(r'\s*[A-D][\)\.\s]', q_content)
            if opt_start:
                stem = q_content[:opt_start.start()].strip()
            else:
                stem = q_content
            questions[str(num)] = stem

    return {"article": article, "questions": questions, "options": options}