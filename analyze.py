import json
import requests

API_KEY = "sk-67d617aa7ba34f99be145bc609ba8285"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"  # 补全后缀

with open("reading_questions.json", "r", encoding="utf-8") as f:
    data = json.load(f)

passage_one = data["Section_C"]["passage_one"]
article = passage_one["article"]
questions = passage_one["questions"]

prompt = f"""你是一位大学英语四级考试专家。请分析以下四级阅读理解真题，给出：

1. **高频词汇表**：列出文章中出现的5个高频/重要词汇，给出音标、词性、中文释义、例句
2. **长难句分析**：找出2个最难理解的句子，拆解语法结构
3. **出题规律**：分析这5道题的出题角度（细节题？主旨题？推理题？），并指出做题技巧
4. **文章主旨**：用中文一句话总结文章核心观点

文章：
{article}

题目：
"""
for num, q_text in questions.items():
    prompt += f"\n{num}. {q_text}"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "qwen-max",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.7
}

print("正在调用AI分析...")
response = requests.post(API_URL, headers=headers, json=payload)

if response.status_code != 200:
    print(f"❌ 失败，状态码: {response.status_code}")
    print(response.text[:300])
    exit()

result = response.json()
analysis = result["choices"][0]["message"]["content"]

print("\n" + "="*60)
print("【AI分析结果】")
print("="*60)
print(analysis)

with open("passage_one_analysis.txt", "w", encoding="utf-8") as f:
    f.write(analysis)

print("\n✅ 已保存到 passage_one_analysis.txt")