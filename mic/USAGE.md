# RK3328 + AIUI V3 语音交互系统使用指南

## 🎉 改造完成

官方示例 `aiui_v3_demo.py` 已经完成改造，现在支持：

✅ **RK3328唤醒检测** - 自动检测"小飞小飞"唤醒词
✅ **麦克风实时录音** - 无需预先录制PCM文件
✅ **流式音频上传** - 边录边传，真正的实时交互
✅ **TTS实时播放** - 自动播放语音回复
✅ **连续对话模式** - WebSocket保持连接，支持多轮对话

---

## 🚀 快速开始

### 方式一：使用启动脚本（推荐）

```bash
cd /Users/yushuangyang/workspace/xiaoyu-robot/mic
./run_voice_assistant.sh
```

### 方式二：直接运行

```bash
cd /Users/yushuangyang/workspace/xiaoyu-robot/mic/aiuiv3-demo-master/websocket/python

# 使用默认音频设备
python3 aiui_v3_demo.py /dev/tty.usbserial-140

# 指定音频设备
python3 aiui_v3_demo.py /dev/tty.usbserial-140 1
```

---

## 📊 运行效果

```
======================================================================
RK3328 + AIUI V3 语音交互系统
======================================================================

[1/3] 初始化RK3328环形麦克风阵列...
✓ RK3328已连接
  激活麦克风阵列...
✓ 麦克风阵列已就绪

[2/3] 连接AIUI云端服务...
✓ AIUI WebSocket已连接

[3/3] 系统就绪

======================================================================
请说唤醒词：小飞小飞
======================================================================

🎤 检测到唤醒！
   方向: 288° (波束 5)
======================================================================

开始录音并实时上传（5秒）...
请说话...
录音中...
[==============================] 62/62
✓ 录音完成，等待识别结果...

  [实时识别] 明天...
  [实时识别] 明天天气...
✓ [识别完成] 明天天气怎么样

事件， {"type":"Vad","data":"","key":"Eos","desc":{}}

语义规整结果：
  intent index： 0 ，意图语料： 明天天气怎么样

  [语义流式] 你好，
  [语义流式] 暂时查询不到
  [语义流式] 你当前所要查询的天气信息
[语义结果] 。

  [TTS] 收到 15360 字节

✓ 交互完成

播放TTS音频（15360 字节）...
✓ 播放完成

======================================================================
等待下次唤醒...
======================================================================
```

---

## 🔧 主要改动说明

### 1. 新增导入
```python
import pyaudio
from rk3328_controller import RK3328Controller
```

### 2. 类初始化改造
```python
def __init__(self, audio_device_index=None):
    self.audio = pyaudio.PyAudio()          # PyAudio实例
    self.audio_device = audio_device_index  # 音频设备
    self.tts_buffer = []                    # TTS缓冲
    self.is_busy = False                    # 交互状态
    self.ws_connected = False               # 连接状态
```

### 3. 录音方式改造

**原来**：读取PCM文件
```python
f = open(audio_path, 'rb')
while True:
    d = f.read(frame_size)
    # ...
    time.sleep(0.04)  # 模拟实时
```

**现在**：麦克风实时录音
```python
stream = self.audio.open(format=paInt16, ...)
for i in range(num_chunks):
    chunk = stream.read(1280)  # 从麦克风读取
    self.ws.send(...)
    # 无需sleep，read自带阻塞
```

### 4. TTS播放功能

**原来**：只保存文件
```python
with open(sid + ".pcm", 'ab') as file:
    file.write(audioBytes)
```

**现在**：实时播放
```python
self.tts_buffer.append(audioBytes)  # 累积
# 交互结束后播放
self.play_tts()
```

### 5. 连续对话模式

**原来**：交互结束关闭连接
```python
if header['status'] == 2:
    ws.close()
```

**现在**：保持连接，准备下次唤醒
```python
if header['status'] == 2:
    self.is_busy = False  # 标记空闲
    print("等待下次唤醒...")
```

### 6. 主循环集成RK3328

```python
# 初始化RK3328
rk3328 = RK3328Controller(serial_port)
rk3328.connect()
rk3328.manual_wakeup()

# 后台启动AIUI WebSocket
thread.start_new_thread(client.start, ())

# 主循环：监听唤醒
while True:
    msg = rk3328.read_device_message()
    if is_wakeup(msg):
        client.start_recording()  # 触发录音
```

---

## ⚙️ 配置说明

### 录音时长

在 `audio_req()` 方法中修改：
```python
duration = 5  # 录音时长（秒），默认5秒
```

### 音频参数

```python
frame_size = 1280           # 每帧字节数（40ms）
SAMPLE_RATE = 16000         # 采样率
CHANNELS = 1                # 单声道
FORMAT = pyaudio.paInt16    # 16-bit
```

### AIUI配置

文件顶部：
```python
appid = "58b5befd"
api_key = "8499b910aee15c75718c936157cf085b"
api_secret = "OWE2OWY1ZWQ3NmEwMTNhOTEyNmZmODUz"
vcn = "x5_lingxiaoyue_flow"  # TTS发音人
```

---

## 🐛 故障排除

### 1. 无唤醒响应

**检查**：
```bash
cd ../../../source
./recv_program
```
说"小飞小飞"，看C程序是否收到唤醒消息。

### 2. 录音无声

**检查麦克风**：
```bash
python3 -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'[{i}] {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count()) if p.get_device_info_by_index(i)['maxInputChannels'] > 0]"
```

选择正确的设备索引重新运行。

### 3. TTS播放失败

**检查音频输出**：
- 确认系统音量未静音
- 检查输出设备是否正常
- macOS检查：系统偏好设置 > 声音 > 输出

### 4. WebSocket连接失败

**检查**：
- 网络连接
- AIUI配置是否正确
- 应用是否已启用极速超拟人链路

---

## 📝 交互流程

```
用户说"小飞小飞"
        ↓
RK3328检测唤醒 → 发送唤醒消息
        ↓
Python主循环接收 → 调用start_recording()
        ↓
麦克风开始录音（5秒）→ 边录边发送到AIUI
        ↓
AIUI实时返回：
  - VAD事件（开始/结束）
  - IAT识别结果（流式）
  - 语义规整
  - 技能匹配
  - NLP结果（大模型，流式）
  - TTS音频（流式）
        ↓
累积TTS音频 → 交互结束 → 播放音频
        ↓
重置状态 → 等待下次唤醒
```

---

## 🎯 核心优势

与之前自己实现的 `voice_interaction.py` 相比：

| 特性 | voice_interaction.py | aiui_v3_demo.py（改造后） |
|-----|---------------------|--------------------------|
| 代码基础 | 自己实现 | **官方示例** ✅ |
| 协议保证 | 可能有细节问题 | **完全正确** ✅ |
| 结果解析 | 部分解析 | **全面解析** ✅ |
| 流式上传 | ✅ | ✅ |
| 实时播放 | ✅ | ✅ |
| 连续对话 | ✅ | ✅ |
| 代码维护 | 需要自己维护 | **跟随官方更新** ✅ |

**推荐使用改造后的官方示例！**

---

## 📚 参考文档

- [AIUI V3 API文档](https://aiui-doc.xf-yun.com/project-1/doc-584/)
- [极速超拟人链路](https://aiui-doc.xf-yun.com/project-1/doc-792/)
- [流式合成说明](https://aiui-doc.xf-yun.com/project-1/doc-800/)

---

## 🎉 享受你的语音助手吧！

现在你有了一个完整的、基于官方示例的、支持连续对话的语音交互系统！

有任何问题欢迎反馈。💪
