# 设备通信协议

设备请求：

```json
{
  "device_id": "stackchan-devkit",
  "user_text": "我回来了",
  "context": {
    "battery_percent": 88,
    "touch": "button_a",
    "face_detected": true,
    "wake_reason": "button",
    "extra": {}
  }
}
```

后端响应：

```json
{
  "say": "欢迎回来，我刚刚在等你。",
  "expression": "happy",
  "motion": "bounce",
  "duration_ms": 3000,
  "audio_url": "/audio/0f6d1a2b3c4d.wav",
  "thought": "用户回来了，使用欢迎动作",
  "saved_memories": [],
  "recalled_memories": []
}
```

## 表情枚举

- `neutral`
- `happy`
- `curious`
- `sleepy`
- `surprised`
- `sad`
- `thinking`

## 动作枚举

- `idle`
- `nod`
- `shake`
- `look_left`
- `look_right`
- `look_up`
- `bounce`
- `sleep`

## 音频

`audio_url` 是可选字段。后端启用 TTS 时会返回音频文件 URL，Web 虚拟设备和真实硬件都应该优先播放它；没有该字段时，设备可以退回本地 TTS 或只显示文字。

当前本机开发版支持 `macos_say`，用 macOS 自带 `say` 生成语音，再转换为 WAV 文件挂在 `/audio/...` 下。

后续可以扩展为动作队列，例如眨眼、转头、灯光颜色等。
