"""AI API 调用客户端"""

import requests


def call_ai_api(prompt, api_key, api_url, model):
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