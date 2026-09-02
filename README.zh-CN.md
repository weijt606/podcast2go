# podcast2go

![podcast2go：黑白四格漫画。通勤的人被一小时的视频和看不完的长文压住，贴上链接、选了 5 分钟，一台憨憨的机器把这堆东西压成一段短音频，最后他戴上耳机边走边听](./podcast2go-banner-cn.png)

[![简体中文](https://img.shields.io/badge/README-简体中文-15803d?style=flat-square)](README.zh-CN.md)
[![English](https://img.shields.io/badge/README-English-1f6feb?style=flat-square)](README.md)
[![Python](https://img.shields.io/badge/Python-3.10+-111111?style=flat-square)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-后端-111111?style=flat-square)](https://fastapi.tiangolo.com/)
![引擎](https://img.shields.io/badge/引擎-免费%20%2F%20免%20key-orange?style=flat-square)
![PWA](https://img.shields.io/badge/PWA-后台播放-1f6feb?style=flat-square)

一集一小时的播客，塞不进走去地铁站的这段路，四千字的长文也一样。podcast2go 的做法是：
你给一个链接，说你有几分钟，它还给你一段差不多那么长的音频，只讲重点，顺手用网络搜索
补上背景。戴上耳机走路，到地方也就听完了。

它是个自己部署的 FastAPI 小应用，配一个手机网页界面。自带的引擎全部免费、开源、不要 key，
你唯一得自备的是一个 LLM 端点，用本机跑的 Ollama 也行。

## 怎么跑的

```
链接 -> 解析 -> 提取重点 -> 网络检索 -> 定长脚本 -> 语音合成 -> 音频
```

1. **解析来源**：文章走 trafilatura，YouTube 取字幕，Apple Podcasts / RSS / 小宇宙 先解析出单集音频，音频直链交给 Whisper 转写。
2. **提取重点**：让 LLM 把长文本压成一份排好序的重点清单。
3. **网络检索**：对排在前面的几个点做搜索，把背景和出处补进来。
4. **撰写脚本**：按 `目标分钟 × 语速` 的字数预算写一份口播稿，用真人说话的口气写，可以是一个人讲，也可以是两个人对谈。
5. **语音合成**：合成 mp3，交给播放器。

## 它能做什么

- 时长是算出来的，不是猜的。选 3 / 5 / 10 / 15 分钟，写稿那一步按代码算好的预算写（英文 `分钟 × 150` 词，中文和日文 `分钟 × 240` 字，因为这两种语言实际就说这么快），不是模型写到哪算哪。单人模式实测落在目标的 10% 以内。双人对谈会偏短，常见少 20% 到 40%，因为模型每轮说得短，聊够了就收。对时长有要求就用单人模式。
- 两种形态：一个人讲，或者两个人一来一回对谈，两位说话人各用一个音色。
- 音色可选可试听，按输出语言挑好的几个；也可以接自己的 OpenAI 兼容 TTS 端点。
- 支持的来源：文章、YouTube、Apple Podcasts、RSS 订阅源、小宇宙、音频直链。链接旁边有个"检测"按钮，能先告诉你这条链接解不解得开，不用白跑一整轮。
- 可以引导：核心点、想听深一点的点、语气视角、输出语言。
- 写稿时套了一份去 AI 味的规则（中英都有），免得主播听起来像在念自己生成的要点。
- 多语言音频，中文在内，由 edge-tts 提供。
- LLM 和 TTS 端点都有测试按钮，key 填错一秒就知道，不用等到跑了四分钟才报错。
- 能装到手机桌面，锁屏也继续放（Media Session API）。
- 界面中英双语。
- BYOK：LLM 和 TTS 的端点、key、model 可以直接填在界面的设置面板里，不一定要写 `.env`。

## 截图

<table>
  <tr>
    <td align="center"><b>首页</b></td>
    <td align="center"><b>高级与设置</b></td>
  </tr>
  <tr>
    <td valign="top"><img src="./docs/screenshot-home.png" width="300" alt="podcast2go 首页：贴链接、选时长" /></td>
    <td valign="top"><img src="./docs/screenshot-advanced.png" width="300" alt="高级与设置：LLM/TTS 测试按钮、TTS 引擎选择、模式、音色选择与试听" /></td>
  </tr>
</table>

## 引擎

项目自带的这些全都免费、开源、不要 key。想换成别的，就在对应的 `providers/*.py` 里加个分支，
返回同样的结构。

| 能力 | 自带的 | 可以换成 |
|---|---|---|
| **LLM** | 任意 OpenAI 兼容端点 | OpenAI、Groq、OpenRouter、DeepSeek、智谱 GLM、通义千问、月之暗面 Kimi、本机 **Ollama** |
| **TTS** | edge-tts（多语言，含中文） | OpenAI TTS、ElevenLabs、Piper（离线）、[CosyVoice](https://github.com/FunAudioLLM/CosyVoice)（阿里，开源）、[VoxCPM](https://github.com/OpenBMB/VoxCPM)（本地，可克隆音色） |
| **网络搜索** | DuckDuckGo（`ddgs`） | Tavily、Brave、Serper、agent 自带的联网搜索 |
| **正文抽取** | trafilatura | Tavily Extract、Mercury、Readability |
| **STT**（音频来源） | faster-whisper | |

### 音色

自带的语音引擎是 [edge-tts](https://github.com/rany2/edge-tts)，也就是微软 Edge 背后那套神经
音色。免费、不要 key、出 mp3（`backend/providers/tts.py`）。

高级选项里可以从挑好的列表里选配音音色，按试听听一段样本，也可以在一个人讲和两人对谈之间
切换，对谈时两位说话人各用一个音色。音色留空就按输出语言自动选：英语、中文、日语、法语、
德语、西班牙语、葡萄牙语各有一个默认音色（`en-US-AriaNeural`、`zh-CN-XiaoxiaoNeural` 这些），
其余语言回退到英语。想锁死某个音色，在 `backend/.env` 里写 `EDGE_VOICE=`，或者在界面上按会话设。

edge-tts 是从微软的服务流式取音的，合成得联网，它不是本地音色。要离线出音就换 Piper（轻，
跑 CPU）或者 OpenBMB 的 [VoxCPM](https://github.com/OpenBMB/VoxCPM)（Apache-2.0，权重开放，
中英零样本克隆音色），能离线跑，但要一块 NVIDIA 显卡。

音频多长由脚本决定，跟音色无关。写稿那步按 `分钟 × WPM` 词的预算写（默认 `WPM=150`），输出中文或
日文时改按 `分钟 × 240` 字。成品 mp3 的真实时长再用 `mutagen` 量一遍显示在播放器上，所以你看到的
是实际拿到的长度，不是当初要的那个数。

## 快速开始

需要 Python 3.10 以上。

```bash
git clone https://github.com/weijt606/podcast2go.git
cd podcast2go

cp .env.example backend/.env          # 可选，也可以直接在界面里填 LLM

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# 打开 http://localhost:8000
```

### 指一个 LLM 给它

整个应用只需要这一份凭证。编辑 `backend/.env`，指向任意 OpenAI 兼容端点：

```bash
# 云端，任选其一
LLM_BASE_URL=https://api.deepseek.com/v1          LLM_API_KEY=sk-...  LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4 LLM_API_KEY=...     LLM_MODEL=glm-4-flash
LLM_BASE_URL=https://api.openai.com/v1            LLM_API_KEY=sk-...  LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.groq.com/openai/v1       LLM_API_KEY=gsk_... LLM_MODEL=llama-3.3-70b-versatile

# 完全本地，不要 key。装好 Ollama，跑 `ollama pull llama3.1`，然后：
LLM_BASE_URL=http://localhost:11434/v1            LLM_API_KEY=ollama  LLM_MODEL=llama3.1
```

`.env` 不是必须的，它装的只是服务端默认值。你在界面设置面板里填了 Base URL、key、model，
它们会跟着每次请求一起发过去，并且优先生效，所以完全不建 `.env` 也能跑；面板里留空的字段
才回退到 `.env`。想要一个换浏览器也还在的默认值就用文件，人在手机上就用面板。

要解析 Apple Podcasts、RSS、小宇宙、音频直链（这几种都要过 Whisper 转写），再装一下
`pip install faster-whisper`。Spotify 用不了，它不开放单集音频。

## 第一次用

从零到一段成品，全程不用付费 API。

先给它一个 LLM，写进 `backend/.env` 或者填在界面设置面板里，就是上面那段。不想给任何人付钱的话，
装个 [Ollama](https://ollama.com)，`ollama pull llama3.1`。

然后照[快速开始](#快速开始)走一遍：克隆、`.env`、`pip install`、`uvicorn`。终端打印出
`Uvicorn running on http://127.0.0.1:8000`，就在浏览器里打开这个地址。

接着做一段：

1. 贴链接。文章、YouTube、Apple Podcasts、RSS 订阅源、小宇宙都行，点"检测"确认能解开。
2. 选时长：3 / 5 / 10 / 15 分钟。
3. 想调就展开高级选项：核心点、想听深一点的点、语气视角、输出语言、一个人讲还是两个人对谈、以及配音音色（可试听）。
4. 点"生成播客"，看着五步跑完：解析、提取、检索、脚本、合成。
5. 播放器出来就能放。可以按章节跳、扫一眼核心点和来源、读完整脚本，也可以把 mp3 下载下来。锁屏了也继续放。

`.env` 里没填 key 也没关系，点顶部的设置面板，把 LLM 的 Base URL、key、model 贴进去就行，
只存在当前浏览器里，人在手机上的时候这样最省事。

要压播客和音频链接的话，开始之前先 `pip install faster-whisper`，装一次就够。

## 说明

生成的音频默认是英文，可以在界面里换输出语言，edge-tts 支持中文、日文和几种欧洲语言。

章节时间戳是按每段音频真实量出来的，不是估的。脚本没能干净分段时会退回均分，并在时间戳前加一个
`~`，你一眼能看出区别。

任务状态存在内存里，单进程，跑完的任务六小时后连 mp3 一起清掉。这是个自己部署自己用的工具，不是
多租户服务。

架构和构建细节见 [CLAUDE.md](./CLAUDE.md)。
