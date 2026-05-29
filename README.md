# 🎧 podcast2go

> 把一个很长的播客 / 视频 / 文章，压成一段**时长可控、重点突出、并经过深度搜索补充**的语音播客 —— 专为通勤、跑步、散步、开车时**后台收听**而设计。

一个由 [@weijt606](https://github.com/weijt606) 开发的个人项目。

## 它解决什么

长内容（一小时的播客、几千字的文章）很难在碎片时间消化。podcast2go 让你贴一个链接、选一个目标时长，就得到一段刚好那么长、只讲重点、还顺手补充了背景的语音播客，戴上耳机就能听完。

## 工作流程

1. **解析来源** — 文章用 Tavily Extract 抓正文；YouTube 取字幕
2. **提取重点** — Nebius 上的 LLM 把长文本提炼成排序后的核心点
3. **深度补充** — 对最重要的点用 Tavily 深度搜索，补上背景与出处
4. **撰写脚本** — 按 `目标分钟 × 语速` 的字数预算生成定长口语脚本
5. **语音合成** — Gradium TTS 合成音频，前端支持锁屏后台播放

## 技术栈

- **后端 / 流水线**：Python + FastAPI（单体，无 DB）
- **LLM**：Nebius AI Studio（OpenAI 兼容）
- **搜索 / 抓取**：Tavily（Search + Extract）
- **语音合成**：Gradium TTS
- **前端**：移动端单页（Tailwind CDN + PWA），FastAPI 直接托管

## 快速开始

```bash
cp .env.example backend/.env        # 填入 NEBIUS / TAVILY / GRADIUM 三个 key
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
open http://localhost:8000
```

> ⚠️ Gradium TTS 目前支持英 / 法 / 德 / 西 / 葡，**不支持中文**。源内容可以是任意语言，但生成的语音默认英文。

更多构建/运行/约定见 [CLAUDE.md](./CLAUDE.md)。
