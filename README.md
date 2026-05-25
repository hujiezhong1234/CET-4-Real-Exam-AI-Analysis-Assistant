# 四级真题AI分析助手

上传大学英语四级真题PDF，自动提取Reading部分，调用大语言模型分析高频词汇、长难句和出题规律。

## 功能

- 📄 PDF真题自动解析（Section A / Passage One / Passage Two）
- 🤖 AI智能分析（高频词汇、长难句拆解、出题规律、文章主旨）
- 🌐 多平台支持（DeepSeek、硅基流动、阿里云、OpenAI、自定义）
- 📥 一键下载分析报告

## 技术栈

- Python + Streamlit
- PyPDF2（PDF文本提取）
- 正则表达式（结构化解析）
- 大语言模型 API（OpenAI兼容格式）

## 更新日志

**最新版本 [v1.1.0]** - 新增 Writing/Listening/Translation 分析，重构 PDF 解析引擎

查看完整更新日志 👉 [CHANGELOG.md](./CHANGELOG.md)

## 运行

```bash
pip install -r requirements.txt
streamlit run app.py