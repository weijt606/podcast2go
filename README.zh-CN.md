# 🎧 podcast2go

[![English](https://img.shields.io/badge/lang-English-gray?style=flat-square)](README.md)
[![简体中文](https://img.shields.io/badge/lang-简体中文-2563eb?style=flat-square)](README.zh-CN.md)

> 把一个很长的播客 / 视频 / 文章，压成一段**时长可控、重点突出、并经过网络检索补充**的语音播客 —— 专为通勤、跑步、散步、开车时**后台收听**而设计。

## 这是什么

长内容（一小时的播客、几千字的文章）很难在碎片时间消化。用 podcast2go，你贴一个链接、选一个目标时长，就得到一段**刚好那么长**、只讲重点、还顺手从网络补充了背景的语音播客，戴上耳机就能听完。

它是一个小巧的自托管 FastAPI 应用，带移动端网页界面，**不绑定任何厂商**，**开箱即用免费/开源引擎**——你唯一需要自备的是一个 LLM 端点（也可以是本地的）。

### 工作流程

```
链接 ─▶ 解析 ─▶ 提取重点 ─▶ 网络检索 ─▶ 定长脚本 ─▶ 语音合成 ─▶ 🎧
```

1. **解析来源** — 文章（trafilatura）、YouTube（字幕）、或音频/播客直链（Whisper STT）
2. **提取重点** — LLM 把长文本提炼成排序后的核心点
3. **网络检索** — 对最重要的点做网络搜索，补上背景与出处
4. **撰写脚本** — 按 `目标分钟 × 语速` 的字数预算生成定长口语脚本
5. **语音合成** — TTS 合成音频，前端支持锁屏后台播放

### 特性

- ⏱️ **时长可控**（3 / 5 / 10 / 15 分钟），基于确定性的字数预算
- 🎛️ **可引导**：核心点、深度了解的点、语气/视角、输出语言
- 🌍 **多语言**音频（含中文），由 edge-tts 提供
- 📱 移动端 PWA，**后台播放**（Media Session API）
- 🌐 **中英双语界面**一键切换
- 🔑 **BYOK** — 在界面或 `.env` 里自带 LLM 端点/key

## 引擎（均可替换）

随附引擎全部免费/开源、**无需 key**。架构可插拔——想用付费 API，只需在对应 `providers/*.py` 加分支。

| 能力 | 随附（免费） | 可自行接入的推荐项 |
|---|---|---|
| **LLM** | 任意 OpenAI 兼容端点 | OpenAI · Groq · Together · OpenRouter · Nebius · 本地 **Ollama** |
| **TTS** | edge-tts（多语言含中文） | OpenAI TTS · ElevenLabs · Azure · Piper（离线） |
| **网络搜索** | DuckDuckGo（`ddgs`） | Tavily · Brave · Serper |
| **正文抽取** | trafilatura | Tavily Extract · Mercury · Readability |
| **STT**（音频源） | faster-whisper | — |

## 快速开始

需要 **Python ≥ 3.10**。

```bash
git clone https://github.com/weijt606/podcast2go.git
cd podcast2go

cp .env.example backend/.env          # 配置一个 LLM 端点（见下）

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# 打开 http://localhost:8000
```

### 配置 LLM（唯一必填）

编辑 `backend/.env`，指向任意 OpenAI 兼容端点，例如：

```bash
# 云端（任选其一）
LLM_BASE_URL=https://api.openai.com/v1      LLM_API_KEY=sk-...   LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.groq.com/openai/v1 LLM_API_KEY=gsk_...  LLM_MODEL=llama-3.3-70b-versatile

# 完全本地、免费（无 key）——装好 Ollama，`ollama pull llama3.1`，然后：
LLM_BASE_URL=http://localhost:11434/v1      LLM_API_KEY=ollama   LLM_MODEL=llama3.1
```

也可在界面 ⚙️ 面板里按会话设置 LLM 端点（存于浏览器本地）。
要转写音频/播客直链，再 `pip install faster-whisper`。

## 说明

- 生成音频默认英文；可在界面切换输出语言（edge-tts 支持中文、日文及多种欧洲语言）。
- 任务状态在内存、单进程——这是个人/自托管工具，非多租户服务。

架构与构建细节见 [CLAUDE.md](./CLAUDE.md)。
