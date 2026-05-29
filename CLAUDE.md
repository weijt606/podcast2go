# podcast2go

把一个很长的播客 / 视频 / 文章，压成一段**时长可控、重点突出、并由深度搜索补充过**的语音播客，专为通勤、跑步、开车等场景下**后台收听**而设计。

## 架构

单体 FastAPI 后端承载整条 AI 流水线，并直接托管移动端单页前端（无独立前端构建、无 DB、无登录）。

```
前端 (static/index.html, Tailwind CDN, PWA)
  │  POST /api/generate          → 创建任务，返回 job_id（可携带 BYOK 覆盖）
  │  GET  /api/events/{job_id}    → SSE 实时进度
  │  GET  /api/result/{job_id}    → 完成后取结果
  ▼
FastAPI (main.py) → settings.resolve(req) → pipeline/orchestrator.py 串联 5 阶段：
  1. ingest    文章=trafilatura / YouTube=字幕 / 音频=whisper STT
  2. extract   LLM map-reduce → 排序后的核心重点
  3. research  网络检索补充 top 重点（并发）
  4. script    LLM 按字数预算写定长口语脚本
  5. tts       edge-tts 合成 mp3
音频写入 static/audio/{job_id}.{ext}，由 /audio 提供。
```

## 引擎（providers/）

每个能力一个模块。随附的都是免费/开源、无需 key 的实现；要接付费 API（见下）只需在对应模块加分支。

| 能力 | 随附实现 | 可自行接入 |
|---|---|---|
| LLM | 任意 OpenAI 兼容端点（`LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`） | OpenAI / Groq / Together / OpenRouter / Nebius / 本地 Ollama |
| TTS | edge-tts（免费，多语言含中文） | OpenAI TTS / ElevenLabs / Azure / Piper(离线) |
| 搜索 | DuckDuckGo (ddgs) | Tavily / Brave / Serper |
| 抽取 | trafilatura | Tavily / Mercury / Readability |
| STT | faster-whisper（可选安装，音频源用） | — |

## BYOK / 关键约束

- **BYOK**：`settings.resolve(req)` 把请求里的 LLM 端点/key/model 叠在 `.env` 默认值之上；
  请求值优先，留空回退 `.env`。所有 pipeline / provider 函数第一个参数都是 `Settings s`。
- 时长控制是确定性的：`目标词数 = 分钟 × WPM`（`settings.wpm`），由代码算好写进 prompt，不靠模型猜。
- **语言**：edge-tts 支持中文及多语言，源内容可任意语言。
- 任务状态存在内存（`state.JOBS`），单进程单机运行。

## 运行命令

```bash
# 1. 配置（默认免费引擎下，只需一个 LLM key，或指向本地 Ollama）
cp .env.example backend/.env

# 2. 安装依赖（需要 Python ≥ 3.10；本机用 python3.12）
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 音频/播客来源额外需要： pip install faster-whisper

# 3. 启动（从 backend/ 目录运行，使其能加载 .env 并定位 static/）
uvicorn main:app --reload --port 8000

# 4. 打开
open http://localhost:8000
```

## 验证

```bash
# 健康：返回 HTML 首页
curl -s http://localhost:8000/ | head -1
# 端到端：贴一篇文章 URL → 选时长 → 生成 → 播放
```

## Project rules

These rules apply to every task in this project unless explicitly overridden.
Bias: caution over speed on non-trivial work. Use judgment on trivial tasks.

### Rule 1 — Think Before Coding
State assumptions explicitly. If uncertain, ask rather than guess.
Present multiple interpretations when ambiguity exists.
Push back when a simpler approach exists.
Stop when confused. Name what's unclear.

### Rule 2 — Simplicity First
Minimum code that solves the problem. Nothing speculative.
No features beyond what was asked. No abstractions for single-use code.
Test: would a senior engineer say this is overcomplicated? If yes, simplify.

### Rule 3 — Surgical Changes
Touch only what you must. Clean up only your own mess.
Don't "improve" adjacent code, comments, or formatting.
Don't refactor what isn't broken. Match existing style.

### Rule 4 — Goal-Driven Execution
Define success criteria. Loop until verified.
Don't follow steps. Define success and iterate.
Strong success criteria let you loop independently.

### Rule 5 — Use the model only for judgment calls
Use the model for: classification, drafting, summarization, extraction.
Do NOT use it for: routing, retries, deterministic transforms.
If code can answer, code answers.

### Rule 6 — Token budgets are not advisory
Per-task: 4,000 tokens. Per-session: 30,000 tokens.
If approaching budget, summarize and start fresh.
Surface the breach. Do not silently overrun.

### Rule 7 — Surface conflicts, don't average them
If two patterns contradict, pick one (more recent / more tested).
Explain why. Flag the other for cleanup.
Don't blend conflicting patterns.

### Rule 8 — Read before you write
Before adding code, read exports, immediate callers, shared utilities.
"Looks orthogonal" is dangerous. If unsure why code is structured a way, ask.

### Rule 9 — Tests verify intent, not just behavior
Tests must encode WHY behavior matters, not just WHAT it does.
A test that can't fail when business logic changes is wrong.

### Rule 10 — Checkpoint after every significant step
Summarize what was done, what's verified, what's left.
Don't continue from a state you can't describe back.
If you lose track, stop and restate.

### Rule 11 — Match the codebase's conventions, even if you disagree
Conformance > taste inside the codebase.
If you genuinely think a convention is harmful, surface it. Don't fork silently.

### Rule 12 — Fail loud
"Completed" is wrong if anything was skipped silently.
"Tests pass" is wrong if any were skipped.
Default to surfacing uncertainty, not hiding it.
