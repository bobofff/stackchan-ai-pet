# Stack-chan AI Pet

真实物理桌面陪伴机器人框架：Stack-chan 风格外壳，ESP32/M5Stack 控制表情和舵机，树莓派或远程服务器运行 AI 大脑和长期记忆。

## 架构

```text
麦克风/触摸/摄像头/按钮
          |
          v
M5Stack / ESP32  <----HTTP/JSON---->  brain 服务(FastAPI)
  表情屏幕 + 舵机                         LLM + 记忆(SQLite/mem0/Letta)
          |
          v
扬声器 / TTS 播放 / 小动作
```

第一版先把通信、记忆和行为协议跑通。你可以先不用真实硬件，直接启动 `brain` 再用 `simulator/chat.py` 测试。

## 目录

```text
brain/                  AI 大脑服务，跑在树莓派、Mac mini、NAS 或云服务器
device/m5stack-stackchan/ ESP32/M5Stack 固件骨架
shared/                 设备和后端共用的 JSON 协议
docs/                   硬件、协议、记忆设计说明
simulator/              无硬件调试工具
```

## 快速开始：先跑 AI 大脑

```bash
cd stackchan-ai-pet
cp .env.example .env
make setup-brain
make migrate-brain-db
make run-brain
```

另开一个终端测试：

```bash
make simulate
```

在 macOS 上，命令行模拟器会默认调用系统自带的 `say` 把宠物回复读出来。可以用下面的环境变量调整或关闭：

```bash
STACKCHAN_TTS_VOICE=Tingting STACKCHAN_TTS_RATE=180 make simulate
STACKCHAN_TTS=0 make simulate
```

Web 虚拟设备模拟器会跟随 brain 服务一起启动。打开浏览器访问：

```text
http://127.0.0.1:8787/simulator/
```

页面会展示虚拟屏幕表情、动作状态、语音输出、记忆召回/保存、LLM 返回 JSON 和最近交互日志。你也可以运行 `make simulate-web` 查看入口地址。

如果希望 Web 虚拟设备提前走接近真实硬件的“后端生成音频 + 设备播放”链路，在 `.env` 里打开：

```bash
TTS_ENABLED=1
TTS_PROVIDER=macos_say
TTS_VOICE=Meijia
TTS_RATE=180
```

`TTS_VOICE` 留空会使用 macOS 默认音色，可能和浏览器默认音色很像。可以用 `say -v '?'` 查看本机可用音色，例如 `Tingting`、`Meijia`、`Sinji`。重启 `make run-brain` 后，`/api/v1/turn` 会在响应里带上 `audio_url`。Web 虚拟设备会优先播放这个音频；如果后端没有返回音频，仍会回退到浏览器自带语音。

如果 `.env` 里没有填 `LLM_API_KEY`，后端会用本地 fallback 行为，方便先调硬件闭环。填入 OpenAI-compatible API 后，会让模型返回结构化的说话内容、表情、动作和可保存记忆。

## 设计问答总结

### 这是屏幕桌宠还是实体机器人？

目标是真实物理桌面上的陪伴机器人，不是电脑桌面里的虚拟 Live2D 挂件。因此项目采用硬件身体和 AI 大脑分层的方案：

- Stack-chan 风格 3D 打印外壳，适合小型桌面陪伴机器人。
- ESP32/M5Stack 负责屏幕表情、舵机动作、按钮、基础传感器和网络通信。
- 树莓派、本地小主机或远程服务器负责 LLM、语音、视觉和长期记忆。

### LLM 可以用哪家？DeepSeek 可以吗？

可以。只要供应商支持 API，最好支持 OpenAI-compatible 调用、JSON 输出或工具调用，就能接入当前 `brain` 服务。DeepSeek 可以作为第一版文本大脑，适合中文陪伴、动作 JSON 生成、记忆提取和低成本长期运行。

推荐阶段性选择：

- 第一版：DeepSeek 或其他 OpenAI-compatible 文本模型，先跑通对话、记忆、表情和动作。
- 体验升级：接入更强的实时语音模型，例如 OpenAI Realtime 或 Gemini Live，改善低延迟语音、打断和自然对话。
- 本地隐私版：后续可以接 Ollama、LM Studio、vLLM 等本地或局域网模型服务。

### 长期记忆会不会占很多存储？

存储通常不是最大问题。文字对话、摘要、显式记忆和元数据即使用多年，也更可能是几百 MB 到数 GB 级别，适合放在本地 SQLite、NAS 或远程数据库里。

真正需要控制的是每次请求远程 AI 时发送的 token 数量。

### 长期使用后 token 会不会指数级增长？

不会必然增长，也不应该增长。错误做法是把全部历史聊天记录都塞进 prompt；正确做法是把“存储”和“喂给模型的上下文”分开。

每次请求只带这些内容：

- 最近几轮短期对话。
- 用户长期画像和机器人当前状态。
- 当前问题相关的 Top-K 记忆。
- 最近一天或一周的摘要。
- 当前传感器上下文，例如触摸、按钮、电量、是否看到人。

这样即使项目运行五年或十年，每次请求的上下文也可以保持在一个稳定范围内，不会随着全部历史线性塞入 prompt，更不会指数级增长。

### 记忆应该怎么分层？

推荐从第一版就按下面的结构设计：

- 短期记忆：最近几轮对话，直接进上下文。
- 显式记忆：用户说“记住……”，高优先级保存。
- 长期事实：偏好、习惯、重要日期、长期项目、人际关系。
- 情节记忆：完整原始对话日志，冷存储，平时不全部进入 prompt。
- 周期摘要：每天、每周、每月生成摘要，用来压缩长期历史。
- 关系和情绪状态：亲密度、最近压力、常聊主题、共同经历。

控制成本的核心机制：

- Top-K 检索，只召回最相关的几条记忆。
- 时间衰减，旧记忆默认权重降低。
- 重要性评分，生日、偏好、承诺、长期项目权重大。
- 去重合并，重复事实只保留更稳定的一条。
- 周期总结，用摘要替代大段历史。
- 小模型整理记忆，贵模型只负责关键对话体验。

## 硬件建议

第一版建议不要做四足，先做“会看、会说、会转头”的桌面宠物：

- M5Stack Core2/CoreS3 或 ESP32-S3 开发板
- 2 个 SG90/MG90S 舵机：左右转头、点头
- 小喇叭或 I2S 功放
- 麦克风模块，或先由树莓派/手机/电脑收音
- 可选摄像头，视觉先放后端做
- 3D 打印 Stack-chan 风格外壳

更多见 [docs/hardware-bom.md](docs/hardware-bom.md)。

## 下一步路线

1. 打印 Stack-chan 风格外壳，确认板子、舵机、喇叭、电池空间。
2. 让 `device` 固件连上 Wi-Fi，并能请求 `brain` 的 `/api/v1/turn`。
3. 把 `say` 接到 TTS，先用服务器 TTS 或 M5Stack 本地播放都可以。
4. 把记忆从 SQLite 升级到 mem0 或 Letta，当对话数据开始变多再做。

## 没有硬件时的本机开发路线

如果暂时还没有购买硬件，可以先把 Mac mini M4 当成完整的无硬件实验台，把“性格、记忆、交互节奏、协议稳定性”先打磨出来。等硬件到手时，M5Stack 只需要替换虚拟设备，负责真实屏幕、舵机和传感器。

建议优先做：

1. 补自动化测试，覆盖 `/api/v1/turn`、显式记忆、记忆召回、设备密钥、LLM fallback 等核心路径。
2. 做一个 Web 虚拟设备模拟器，在浏览器里展示表情、动作、记忆、LLM 返回 JSON 和交互日志。
3. 加 Mac 本机语音输出，先用 macOS 自带 TTS 或简单播放链路把 `say` 真的读出来。
4. 再加语音输入，第一版可以保留文字输入，后续接 Whisper、本地 STT 或云 STT。
5. 最后再买硬件并做实机联调，确认 M5Stack 能连 Wi-Fi、POST 到 `brain`、解析 response、驱动屏幕和舵机。
