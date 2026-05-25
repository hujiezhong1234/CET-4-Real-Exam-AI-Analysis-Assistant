# 更新日志

## [1.1.0] - 2026-05-25

### 新增
- **Part I Writing 写作指导**：AI分析写作题目，提供文章结构、高分句型、范文框架
- **Part II Listening 听力分析**：针对听力部分给出备考建议和常见陷阱提示
- **Part IV Translation 翻译分析**：提供难点词汇、句型分析、参考译文、评分要点
- **结构化真题解析**：按 Part → Section → Passage 层级展示，更清晰

### 改进
- **PDF解析引擎重构**：修复答案页重复Part导致的解析错误
- **Part III Reading 全面展示**：
  - Section A：文章 + 选项分栏显示
  - Section B：每个段落可折叠展开，全部内容可见
  - Section C：文章摘要 + 题目列表，Passage One/Two 分别展示
- **过滤 KEYS 答案**：Translation 内容不再包含答案部分
- **多平台API支持**：DeepSeek、硅基流动、阿里云、OpenAI、自定义

### 修复
- Passage Two 文章解析失败（0词0题）的问题
- Section B 标题提取失败的问题
- 部分真题格式兼容性问题

## [1.0.0] - 2026-05-24

### 初始版本
- PDF真题自动解析（Reading部分）
- AI智能分析：高频词汇、长难句拆解、出题规律
- Streamlit Web界面
- 多平台API支持（5个平台）
- 一键下载分析报告