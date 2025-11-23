# RK3328降噪板 Linux使用指南

本项目提供RK3328降噪板（环形六麦）在Linux环境下的完整控制和音频采集方案。

## 📋 目录

- [硬件准备](#硬件准备)
- [快速开始](#快速开始)
- [详细文档](#详细文档)
- [脚本说明](#脚本说明)
- [常见问题](#常见问题)

## 🔧 硬件准备

### 必需硬件

1. **RK3328降噪板** + 环形六麦模拟硅麦
2. **USB转TTL模块**（CH340或CP2102芯片）
3. **3.5mm音频线** × 2
4. **DC 12V电源适配器**（≥1A）
5. **Linux主机**（需有音频输入接口）

### 接线方式

```
┌─────────────── Linux主机 ───────────────┐
│                                          │
│  /dev/ttyUSB0 ←→ USB转TTL                │
│  音频输入 ←→ 3.5mm线                     │
│  音频输出 ←→ 3.5mm线（可选，用于回声消除）│
│                                          │
└──────────────────┬───────────────────────┘
                   │
              ┌────▼────────────────┐
              │   RK3328降噪板      │
              │                     │
              │  TTL串口            │
              │  麦克风音频输出     │
              │  功放/回采输入      │
              │                     │
              └─────────────────────┘
```

**详细接线：**

```bash
# 串口连接（控制通道）
RK3328 TTL接口          USB转TTL          Linux
  TX (发送)      ───→     RX        ───→  /dev/ttyUSB0
  RX (接收)      ←───     TX
  GND            ───      GND

# 音频连接
RK3328 麦克风音频输出  ───  3.5mm线  ───→  Linux音频输入(Line-in/Mic)
RK3328 功放/回采输入   ←──  3.5mm线  ───  Linux音频输出（可选）
```

## 🚀 快速开始

### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    portaudio19-dev \
    alsa-utils \
    libasound2-dev

# Fedora/CentOS
sudo dnf install python3-pip python3-devel portaudio-devel alsa-lib-devel
```

### 2. 安装Python依赖

```bash
pip3 install -r requirements.txt
```

如果PyAudio安装失败，尝试：

```bash
# Ubuntu/Debian
sudo apt-get install python3-pyaudio

# 或从源码编译
pip3 install --global-option='build_ext' \
  --global-option='-I/usr/include' \
  --global-option='-L/usr/lib' \
  pyaudio
```

### 3. 配置串口权限

```bash
# 添加用户到dialout组
sudo usermod -a -G dialout $USER

# 重新登录使权限生效，或临时修改：
sudo chmod 666 /dev/ttyUSB0
```

### 4. 查找设备

```bash
# 查找串口设备
ls -l /dev/ttyUSB*

# 查看音频设备
python3 audio_recorder.py
# 选择菜单 1 列出音频设备
```

### 5. 运行示例程序

```bash
# 基本示例（自动检测设备）
python3 rk3328_demo.py

# 指定设备
python3 rk3328_demo.py /dev/ttyUSB0 1
#                      ^^^^^^^^^^^  ^
#                      串口设备     音频设备编号
```

## 📚 详细文档

- **[linux_audio_guide.md](linux_audio_guide.md)** - Linux环境完整使用指南
  - 系统架构说明
  - 硬件连接详解
  - 串口通信协议
  - 音频采集方法（ALSA/PyAudio/C语言）
  - 完整集成方案
  - 故障排查

## 📄 脚本说明

### rk3328_controller.py

串口控制脚本，实现设备通信和控制。

**功能：**
- 串口握手和通信
- 手动唤醒和波束控制
- 唤醒词更换
- 麦克风阵列切换
- 读取设备消息（唤醒事件等）

**命令行使用：**

```bash
# 交互式控制
python3 rk3328_controller.py /dev/ttyUSB0

# Python代码使用
from rk3328_controller import RK3328Controller

controller = RK3328Controller('/dev/ttyUSB0')
if controller.connect():
    # 手动唤醒，波束方向0°
    controller.manual_wakeup(beam=0)

    # 等待唤醒事件
    msg = controller.read_device_message()
    print(msg)

    controller.close()
```

**API说明：**

```python
# 手动唤醒，指定波束方向
controller.manual_wakeup(beam=0)  # 0-5，对应0°,60°,120°,180°,240°,300°

# 更换唤醒词（浅定制）
controller.switch_wakeup_word("xiao3 fei1 xiao3 fei1", threshold=900)

# 切换麦克风阵列
controller.switch_mic_array(mic_type=0)  # 0=环形6麦, 1=线性4麦, 2=线性6麦

# 读取设备消息
msg = controller.read_device_message(timeout=1)
# 返回: {'type': 'wakeup', 'content': {'angle': 30, 'score': 950, ...}}
```

### audio_recorder.py

音频录制工具，支持多种录音模式。

**功能：**
- 列出音频设备
- 定时录音
- 流式录音（实时处理）
- VAD录音（自动检测静音）

**命令行使用：**

```bash
# 交互式菜单
python3 audio_recorder.py

# Python代码使用
from audio_recorder import AudioRecorder

recorder = AudioRecorder(device_index=1, rate=16000)

# 录音5秒
recorder.record(duration=5, output_file='test.wav')

# 流式录音
def callback(audio_data, frame_count):
    print(f"音量: {audio_data.mean()}")

recorder.record_stream(callback, duration=10)

recorder.close()
```

### rk3328_demo.py

完整集成示例，演示串口控制和音频采集的联动使用。

**功能：**
- 示例1: 基本功能（监听唤醒和音频）
- 示例2: 唤醒后保存音频
- 示例3: 波束跟随（根据唤醒角度自动调整波束）

**使用：**

```bash
# 运行示例
python3 rk3328_demo.py /dev/ttyUSB0 1

# 选择示例
# 1. 基本功能 - 实时显示音频音量和唤醒事件
# 2. 唤醒后保存 - 检测到唤醒后自动保存音频文件
# 3. 波束跟随 - 根据唤醒角度自动切换波束方向
```

## 🎯 使用场景

### 场景1: 语音唤醒 + ASR识别

```python
from rk3328_controller import RK3328Controller
from audio_recorder import AudioRecorder
import requests

controller = RK3328Controller('/dev/ttyUSB0')
recorder = AudioRecorder(device_index=1)

if controller.connect():
    print("等待唤醒...")

    # 等待唤醒事件
    msg = controller.read_device_message(timeout=60)
    if msg and msg.get('type') == 'wakeup':
        print("已唤醒，开始录音...")

        # 录音5秒
        recorder.record(duration=5, output_file='command.wav')

        # 发送到ASR服务
        with open('command.wav', 'rb') as f:
            # 调用AIUI API或其他ASR服务
            response = requests.post('ASR_API_URL', files={'audio': f})
            print(f"识别结果: {response.json()}")

    controller.close()
    recorder.close()
```

### 场景2: 实时流式处理

```python
import queue
import threading

audio_queue = queue.Queue()

def audio_callback(data, frame_count):
    """音频回调，实时处理音频数据"""
    audio_queue.put(data)

def process_audio():
    """音频处理线程"""
    while True:
        data = audio_queue.get()
        # 进行VAD检测、发送到ASR等
        # ...

# 启动音频处理线程
threading.Thread(target=process_audio, daemon=True).start()

# 开始流式录音
recorder.record_stream(audio_callback)
```

### 场景3: 波束跟随

```python
def angle_to_beam(angle):
    """将角度转换为波束编号"""
    beams = [0, 60, 120, 180, 240, 300]
    distances = [abs(angle - b) for b in beams]
    return distances.index(min(distances))

while True:
    msg = controller.read_device_message()
    if msg and msg.get('type') == 'wakeup':
        angle = msg['content']['angle']
        beam = angle_to_beam(angle)

        print(f"声源方向: {angle}° → 切换波束: {beam}")
        controller.manual_wakeup(beam=beam)
```

## ❓ 常见问题

### Q1: 串口连接失败

```bash
# 检查设备是否存在
ls -l /dev/ttyUSB*

# 检查权限
sudo chmod 666 /dev/ttyUSB0

# 检查驱动
lsmod | grep ch341    # CH340驱动
lsmod | grep cp210x   # CP2102驱动

# 安装驱动（如需要）
sudo modprobe ch341
```

### Q2: 找不到音频设备

```bash
# 列出ALSA设备
arecord -l

# 测试音频输入
arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav
aplay test.wav

# 检查PulseAudio
pactl list sources
```

### Q3: PyAudio安装失败

```bash
# 安装依赖
sudo apt-get install portaudio19-dev python3-dev

# 重新安装
pip3 install --upgrade pyaudio

# 或使用系统包
sudo apt-get install python3-pyaudio
```

### Q4: 握手超时

**可能原因：**
- 串口未连接或连接错误（TX/RX接反）
- 波特率不匹配
- 设备未通电

**解决方法：**
```bash
# 使用minicom测试串口
minicom -D /dev/ttyUSB0 -b 115200

# 检查TX/RX是否接反
# RK3328 TX → USB转TTL RX
# RK3328 RX → USB转TTL TX
```

### Q5: 没有音频输出

**检查：**
1. 3.5mm音频线是否正确连接
2. Linux音频输入设备是否选择正确
3. RK3328是否已唤醒（唤醒前无音频输出）

```bash
# 实时监听音频输入
arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 | aplay
```

## 📊 音频参数

RK3328降噪板输出的音频参数：

| 参数 | 值 |
|------|------|
| 采样率 | 16000 Hz |
| 声道数 | 1（单声道） |
| 位深 | 16 bit |
| 格式 | PCM |
| 字节序 | 小端序 |

## 🔗 相关资源

- [RK3328降噪板白皮书](docs/04.html)
- [RK3328降噪板使用手册](docs/06.html)
- [RK3328降噪板协议手册](docs/08.html)
- [AIUI平台文档](https://aiui-doc.xf-yun.com/project-1/doc-1/)

## 📝 许可证

本项目代码基于MIT许可证开源。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📧 联系方式

如有问题，请查看：
- [常见问题文档](docs/project-1/doc-80.html)
- [官方联系方式](docs/project-1/doc-83.html)
