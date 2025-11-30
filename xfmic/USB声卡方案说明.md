# USB声卡方案完整说明

## 方案概述

USB声卡方案是将RK3328降噪板音频传输到上位机最简单、最经济的方案。

### 优势

- ✅ **即插即用** - 无需复杂配置
- ✅ **成本低** - 仅需20-50元
- ✅ **兼容性好** - 支持Windows/Linux/macOS
- ✅ **代码复用** - 与现有代码100%兼容
- ✅ **稳定可靠** - 标准USB Audio协议

---

## 一、硬件准备

### 必需硬件清单

| 硬件 | 数量 | 价格 | 说明 |
|------|------|------|------|
| RK3328降噪板 | 1 | 已有 | 6麦阵列降噪板 |
| USB声卡 | 1 | 20-50元 | 需支持Line-in输入 |
| USB转TTL模块 | 1 | 5-10元 | CH340或CP2102 |
| 3.5mm音频线 | 1 | 5元 | 公对公 |
| DC 12V电源 | 1 | 10-20元 | ≥1A |

**总成本：40-85元**（不含RK3328板）

### USB声卡推荐型号

#### 入门级（20-30元）

**绿联 CM129**
- 价格：25元
- 接口：3.5mm输入/输出
- 兼容：全平台免驱
- 购买：淘宝/京东搜索"绿联USB声卡"

**毕亚兹 USB声卡**
- 价格：20元
- 接口：Mic/Line-in
- 兼容：Windows/Linux/macOS
- 购买：淘宝/京东搜索"毕亚兹USB声卡"

#### 专业级（50-200元）

**创新 Sound Blaster Play! 3**
- 价格：150元
- 特点：专业音频芯片，低延迟
- 适用：对音质有要求的场景

### 选购要点

```bash
必须满足：
✅ 有3.5mm音频输入接口（Line-in或Mic）
✅ USB供电（不需要额外电源）
✅ 支持16kHz采样率（RK3328输出规格）

推荐选择：
✅ 带独立音量调节
✅ 金属外壳（抗干扰）
✅ USB-A接口（兼容性好）
```

---

## 二、硬件连接

### 接线图

```
┌──────────────────────────────────┐
│         RK3328降噪板              │
│                                   │
│  TTL串口 ──┬──> TX               │
│            │    RX                │
│            │    GND               │
│            │                      │
│  麦克风    │                      │
│  音频输出──┼──> 3.5mm座           │
│            │                      │
│  DC接口 ───┼──> 12V电源           │
│            │                      │
└────────────┼──────────────────────┘
             │
             ├─────> (杜邦线/PH2.0线)
             │         ↓
             │   ┌─────────────┐
             │   │ USB转TTL     │
             │   │  CH340/CP2102│
             │   └──────┬───────┘
             │          │ USB线
             │          ↓
             │   ┌─────────────┐
             │   │             │
             └─> (3.5mm线)    │
                      ↓        │
                ┌──────────┐  │
                │ USB声卡   │  │
                │          │  │
                │ Line-in  │  │
                │ 输入孔   │  │
                └────┬─────┘  │
                     │ USB线  │
                     ↓        ↓
              ┌──────────────────┐
              │     上位机        │
              │                  │
              │  USB口×2         │
              │  (串口+音频)      │
              └──────────────────┘
```

### 详细接线步骤

#### 步骤1: 串口连接（控制通道）

```bash
# RK3328 TTL接口 → USB转TTL模块
RK3328侧（PH2.0-3P）        USB转TTL侧
├─ TX（白色/红色）  ─────→  RX
├─ RX（黄色/绿色）  ─────→  TX
└─ GND（黑色）      ─────→  GND

# USB转TTL → 上位机
USB转TTL模块 ──(USB线)──→ 上位机USB口
```

**注意：TX和RX要交叉连接**

#### 步骤2: 音频连接（数据通道）

```bash
# RK3328 → USB声卡
RK3328 "麦克风音频输出" 3.5mm座
    ↓
3.5mm公对公音频线
    ↓
USB声卡 "Line-in"或"Mic"输入孔 (3.5mm)

# USB声卡 → 上位机
USB声卡 ──(USB线)──→ 上位机USB口
```

**注意事项：**
- 音频线两端都是插头（公对公）
- 插入USB声卡的**输入孔**（不是输出/耳机孔）
- 某些USB声卡输入/输出共用，需切换模式

#### 步骤3: 供电

```bash
RK3328 DC电源接口 ──→ 12V 3A电源适配器
```

---

## 三、软件配置

### Linux系统

#### 1. 检测USB声卡

```bash
# 运行自动配置脚本
chmod +x usb_soundcard_setup.sh
./usb_soundcard_setup.sh

# 或手动检查
# 查看USB设备
lsusb | grep -i audio

# 查看音频设备
arecord -l

# 使用Python查看
python3 -c "
import pyaudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f'[{i}] {info[\"name\"]}')
"
```

#### 2. 测试录音

```bash
# 使用ALSA录音（设备号从上面获取）
arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav

# 播放测试
aplay test.wav
```

#### 3. 设置默认设备（可选）

```bash
# 编辑ALSA配置
sudo nano ~/.asoundrc

# 添加内容（设备号替换为实际值）
pcm.!default {
    type hw
    card 1
    device 0
}
```

### macOS系统

#### 1. 连接USB声卡

```bash
# 插入USB声卡后，macOS会自动识别

# 查看设备
system_profiler SPAudioDataType

# 或使用Python
python3 -c "
import pyaudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f'[{i}] {info[\"name\"]}')
"
```

#### 2. 系统设置

```bash
1. 打开"系统偏好设置"
2. 选择"声音"
3. 点击"输入"标签
4. 选择USB声卡设备
5. 调整输入音量到合适位置
```

#### 3. 授权麦克风权限

```bash
系统偏好设置 → 安全性与隐私 → 隐私 → 麦克风
勾选 "终端" 或 "Python"
```

### Windows系统

```bash
1. 插入USB声卡，Windows自动安装驱动
2. 右键任务栏音量图标 → "声音设置"
3. 输入设备选择USB声卡
4. 调整输入音量
```

---

## 四、代码使用

### 快速开始

```bash
# 运行完整示例
python3 usb_soundcard_demo.py

# 或手动指定设备
python3 usb_soundcard_demo.py /dev/ttyUSB0 1
#                             串口设备     音频设备号
```

### 示例1: 基本唤醒+录音

```python
from rk3328_controller import RK3328Controller
from audio_recorder import AudioRecorder

# 连接设备
controller = RK3328Controller('/dev/ttyUSB0')
recorder = AudioRecorder(device_index=1)  # USB声卡设备号

if controller.connect():
    print("等待唤醒...")

    # 等待唤醒事件
    msg = controller.read_device_message(timeout=60)

    if msg and msg.get('type') == 'wakeup':
        print("检测到唤醒，开始录音...")

        # 录音5秒
        recorder.record(duration=5, output_file='voice.wav')

        print("录音完成")

    controller.close()
    recorder.close()
```

### 示例2: 完整语音交互

```python
from rk3328_controller import RK3328Controller
from audio_recorder import AudioRecorder
import requests

controller = RK3328Controller('/dev/ttyUSB0')
recorder = AudioRecorder(device_index=1)

if controller.connect():
    while True:
        # 1. 等待唤醒
        msg = controller.read_device_message(timeout=1)

        if msg and msg.get('type') == 'wakeup':
            angle = msg['content']['angle']
            print(f"唤醒检测 (方向: {angle}°)")

            # 2. 录音
            recorder.record(duration=5, output_file='cmd.wav')

            # 3. 发送到ASR识别
            with open('cmd.wav', 'rb') as f:
                # 这里调用你的ASR API
                # result = asr_api.recognize(f)
                pass

            # 4. 处理识别结果
            # process_result(result)
```

### 自动检测USB声卡

```python
import pyaudio

def find_usb_soundcard():
    """自动查找USB声卡设备"""
    p = pyaudio.PyAudio()

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        name = info['name'].lower()

        # 检测是否为USB设备
        if 'usb' in name and info['maxInputChannels'] > 0:
            print(f"找到USB声卡: [{i}] {info['name']}")
            p.terminate()
            return i

    p.terminate()
    return None

# 使用
device_index = find_usb_soundcard()
recorder = AudioRecorder(device_index=device_index)
```

---

## 五、常见问题

### 1. USB声卡无法识别

**问题：** 插入USB声卡后系统无反应

**解决：**
```bash
# Linux
sudo dmesg | tail -20  # 查看系统日志
lsusb                  # 检查USB设备

# 可能需要重新插拔USB
# 或尝试其他USB口

# macOS
system_profiler SPUSBDataType  # 查看USB设备
```

### 2. 录音无声音

**问题：** 录音文件没有声音或音量很小

**解决：**
```bash
# 检查1: RK3328是否唤醒
# RK3328首次唤醒后才持续输出音频
python3 rk3328_controller.py /dev/ttyUSB0
# 发送手动唤醒: controller.manual_wakeup(beam=0)

# 检查2: 音频线是否正确连接
# 确认接在USB声卡的"输入"口

# 检查3: 调整输入音量
# Linux: alsamixer
# macOS: 系统偏好设置 → 声音 → 输入
# Windows: 声音设置 → 输入音量

# 检查4: 测试音频线
# 用手机或其他设备测试3.5mm线是否正常
```

### 3. 音质差/有杂音

**问题：** 录音有电流声或杂音

**解决：**
```bash
# 1. 使用金属外壳USB声卡（更好的屏蔽）
# 2. USB声卡插到主板后置USB口（前置容易有干扰）
# 3. 音频线远离电源线
# 4. 检查RK3328供电是否稳定（需12V 1A以上）
# 5. 更换质量好的音频线
```

### 4. 延迟问题

**问题：** 唤醒到录音开始有延迟

**解决：**
```python
# 使用流式录音代替文件录音
def audio_callback(data, frame_count):
    # 实时处理音频
    pass

recorder.record_stream(audio_callback)
```

### 5. 设备号变化

**问题：** 每次重启设备号会变

**解决：**
```python
# 方法1: 使用自动检测
device = find_usb_soundcard()

# 方法2: 使用设备名称
import pyaudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if 'USB' in info['name']:
        device_index = i
        break
```

---

## 六、性能参数

### 音频规格

```
RK3328输出:
  采样率: 16000 Hz
  位深: 16 bit
  声道: 1 (单声道)
  格式: PCM
  接口: 模拟音频 (3.5mm)

USB声卡:
  输入: 模拟音频 (3.5mm)
  ADC: 16-24 bit
  采样率: 8k-96kHz (可配置为16kHz)
  输出: USB数字音频
  延迟: 10-50ms (取决于型号)
```

### 带宽计算

```
音频数据量:
16000 Hz × 16 bit × 1 channel = 256 kbps = 32 KB/s

USB 2.0带宽:
480 Mbps = 60 MB/s

结论: USB带宽充足，单个USB声卡占用<0.1%
```

---

## 七、进阶应用

### 多路音频采集

如果需要同时录制多路音频：

```python
# 使用多个USB声卡
recorder1 = AudioRecorder(device_index=1)  # USB声卡1
recorder2 = AudioRecorder(device_index=2)  # USB声卡2

# 同时录音
import threading
threading.Thread(target=recorder1.record, args=(5, 'audio1.wav')).start()
threading.Thread(target=recorder2.record, args=(5, 'audio2.wav')).start()
```

### 与AIUI集成

```python
# 发送到讯飞AIUI平台
import requests

def send_to_aiui(audio_file):
    """发送音频到AIUI进行识别"""
    url = "https://openapi.xfyun.cn/v2/aiui"

    with open(audio_file, 'rb') as f:
        files = {'audio': f}
        # 添加你的AIUI认证信息
        response = requests.post(url, files=files, headers=headers)

    return response.json()

# 使用
recorder.record(duration=5, output_file='voice.wav')
result = send_to_aiui('voice.wav')
print(result)
```

---

## 八、总结

### 方案优势

| 项目 | USB声卡方案 | I2S方案 | 串口方案 |
|------|------------|---------|---------|
| 成本 | ⭐⭐⭐⭐⭐ 低 | ⭐⭐⭐ 中 | ❌ 不支持 |
| 复杂度 | ⭐⭐⭐⭐⭐ 简单 | ⭐⭐⭐ 中等 | ❌ 不支持 |
| 兼容性 | ⭐⭐⭐⭐⭐ 好 | ⭐⭐⭐⭐ 较好 | ❌ 不支持 |
| 音质 | ⭐⭐⭐⭐ 好 | ⭐⭐⭐⭐⭐ 极好 | ❌ 不支持 |
| 延迟 | ⭐⭐⭐⭐ 低 | ⭐⭐⭐⭐⭐ 极低 | ❌ 不支持 |

### 适用场景

**✅ 推荐使用USB声卡方案的场景：**
- 开发测试阶段
- 预算有限
- 需要快速部署
- 上位机无3.5mm接口
- 需要跨平台兼容

**⚠️ 考虑其他方案的场景：**
- 对音质要求极高 → 考虑I2S方案
- 需要多路音频输入 → 使用多个USB声卡
- 工业级应用 → 考虑专业USB声卡

### 下一步

1. 购买USB声卡和音频线
2. 按照接线图连接硬件
3. 运行 `usb_soundcard_setup.sh` 检测设备
4. 运行 `usb_soundcard_demo.py` 测试功能
5. 集成到你的语音交互项目

---

## 参考资料

- RK3328降噪板白皮书: `docs/04.html`
- Python代码示例: `usb_soundcard_demo.py`
- 配置脚本: `usb_soundcard_setup.sh`
- 音频录制工具: `audio_recorder.py`
- 串口控制: `rk3328_controller.py`
