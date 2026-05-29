# 🎧 podcast2go

[![English](https://img.shields.io/badge/lang-English-gray?style=flat-square)](README.md)
[![简体中文](https://img.shields.io/badge/lang-简体中文-2563eb?style=flat-square)](README.zh-CN.md)

> 把一个很长的播客 / 视频 / 文章，压成一段**时长可控、重点突出、并经过深度搜索补充**的语音播客 —— 专为通勤、跑步、散步、开车时**后台收听**而设计。

## 它解决什么

长内容（一小时的播客、几千字的文章）很难在碎片时间消化。贴一个链接、选一个目标时长，就得到一段刚好那么长、只讲重点、还顺手补充了背景的语音播客，戴上耳机就能听完。

## 工作流程

1. **解析来源** — 文章（trafilatura）、YouTube（字幕）、或音频/播客直链（Whisper STT）
2. **提取重点** — LLM 把长文本提炼成排序后的核心点
3. **深度补充** — 对最重要的点做深度搜索，补上背景与出处
4. **撰写脚本** — 按 `目标分钟 × 语速` 的字数预算生成定长口语脚本
5. **语音合成** — TTS 合成音频，前端支持锁屏后台播放

## 可插拔引擎

每个引擎都可通过环境变量切换，默认全部为**免费 / 开源**实现，因此除了 LLM 之外**无需任何付费 key**，付费工具按需开启。

| 能力 | 免费默认 | 可选替换 |
|---|---|---|
| TTS | `edge-tts`（免费，多语言含中文） | Gradium（`TTS_PROVIDER=gradium`） |
| 网络搜索 | DuckDuckGo（`ddgs`） | Tavily（`SEARCH_PROVIDER=tavily`） |
| 正文抽取 | trafilatura | Tavily（`EXTRACT_PROVIDER=tavily`） |
| STT（音频来源） | faster-whisper | — |
| LLM | 任意 OpenAI 兼容（Nebius，或本地 Ollama） | — |

## BYOK（自带 key）

key 与引擎选择既可在前端 ⚙️ 设置面板里**按请求**填写（存于浏览器 localStorage，随请求发送），也可在 `backend/.env` 全局配置。请求值优先，留空则回退到 `.env`。

## 技术栈

- **后端 / 流水线**：Python + FastAPI（单体，无 DB）
- **前端**：移动端单页（Tailwind CDN + PWA），FastAPI 直接托管

## 快速开始

```bash
cp .env.example backend/.env        # 配置 LLM key（或指向本地 Ollama）
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
open http://localhost:8000
```

> 💡 使用默认引擎无需任何付费 key，只需一个 LLM 端点（Nebius，或本地 Ollama：`NEBIUS_BASE_URL=http://localhost:11434/v1`）。音频/播客来源需额外 `pip install faster-whisper`。

更多构建/运行/约定见 [CLAUDE.md](./CLAUDE.md)。
