"""平台配置和常量"""

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

# 分析选项列表
ANALYZE_OPTIONS = [
    "Part_I Writing",
    "Part_II Listening",
    "Part_III Section_A",
    "Part_III Section_B",
    "Part_III Section_C Passage_One",
    "Part_III Section_C Passage_Two",
    "Part_IV Translation"
]