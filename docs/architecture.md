# 架构说明

这个项目分成三层：

1. **Device 层**：M5Stack/ESP32，负责屏幕表情、舵机、按钮、基础传感器和播放声音。
2. **Brain 层**：树莓派、本地电脑、NAS 或云服务器，负责 LLM、记忆、TTS/STT 编排。
3. **Memory 层**：第一版 SQLite，本地可控；后续可接 mem0 或 Letta。

## 为什么不把 AI 放进 ESP32

ESP32 很适合实时控制硬件，但不适合跑 LLM、长期记忆和复杂语音链路。把 AI 放在树莓派或远程服务器上，硬件端就能保持简单稳定。

## 一次互动流程

```text
用户说话/触摸/按键
  -> device 收集上下文
  -> POST /api/v1/turn
  -> brain 检索记忆
  -> LLM 生成 say/expression/motion
  -> brain 可选生成 audio_url
  -> brain 保存显式记忆和对话片段
  -> device 显示表情、执行动作、播放 audio_url 或本地 TTS
```

## 后续扩展点

- `speech-to-text`: Whisper、FunASR、语音云服务
- `text-to-speech`: Edge TTS、GPT-SoVITS、CosyVoice、OpenAI TTS
- `vision`: 摄像头截图发给多模态模型
- `memory`: SQLite -> mem0/Letta
- `motion`: 从简单枚举升级到动作队列
