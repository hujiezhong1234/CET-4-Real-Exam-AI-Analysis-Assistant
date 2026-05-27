# 更新日志

## [1.2.0] - 2026-05-27

### 新增
- **错题标注功能**：每道题目后增加复选框，可标记错题，侧边栏实时统计
- **词汇收藏功能**：AI 分析的高频词汇支持一键收藏，生成个人词汇本
- **词汇导出**：支持将收藏词汇导出为 JSON 格式
- **学习记录面板**：侧边栏新增"我的学习记录"，显示收藏词汇数和错题数

### 改进
- **代码重构**：将臃肿的 `app.py` 拆分为 5 个模块：
  - `config.py` — 平台配置与常量
  - `pdf_parser.py` — PDF 解析引擎
  - `ai_client.py` — AI API 调用客户端
  - `ui_components.py` — UI 组件（错题、收藏、概览等）
  - `app.py` — 主入口（从 500+ 行精简至 150 行）
- **AI Prompt 增强**：所有题型均要求给出参考答案与逐题解析
- **选项提取兼容**：支持 `A)` / `A.` / `A ` 等多种选项格式

---

## [1.1.0] - 2026-05-25

### 新增
- Part I Writing 写作指导
- Part II Listening 听力分析  
- Part IV Translation 翻译分析
- 结构化真题解析（Part → Section → Passage）

### 改进
- PDF 解析引擎重构，过滤答案页重复 Part
- Reading 部分全面展示（Section A/B/C 完整内容）
- Translation 过滤 KEYS 答案

### 修复
- Passage Two 解析失败（0 词 0 题）
- Section B 标题提取失败

---

## [1.0.0] - 2026-05-24

### 初始版本
- PDF 真题自动解析
- AI 智能分析（高频词汇、长难句、出题规律）
- Streamlit Web 界面
- 多平台 API 支持（DeepSeek、硅基流动、阿里云、OpenAI、自定义）
- 一键下载分析报告