# RK3328降噪板 Linux环境音频获取指南

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Linux主机                              │
│                                                               │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │ 串口控制程序  │────────│ 音频采集程序  │                  │
│  │ /dev/ttyUSB0 │         │ ALSA/Pulse   │                  │
│  └───────┬──────┘         └──────┬───────┘                  │
│          │                       │                           │
└──────────┼───────────────────────┼───────────────────────────┘
           │                       │
      USB转TTL                 3.5mm音频线
           │                       │
           ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   RK3328降噪板                                │
│                                                               │
│  TTL串口  ←→  麦克风音频输出  ←→  功放/回采输入              │
│                     ▲                      ▲                  │
│                     │                      │                  │
│              环形六麦阵列            扬声器/功放              │
└─────────────────────────────────────────────────────────────┘
```

## 一、硬件连接

### 1.1 必需硬件
- RK3328降噪板 + 环形六麦模拟硅麦
- USB转TTL模块（CH340或CP2102芯片）
- 3.5mm音频线 × 2
- Linux主机（需有音频输入接口或USB声卡）
- DC 12V电源适配器（≥1A，使用板载功放需≥3A）

### 1.2 接线方式

```bash
# 串口连接（控制通道）
RK3328 TTL接口 ─── USB转TTL ─── Linux /dev/ttyUSB0
  TX(发送)           RX
  RX(接收)           TX
  GND                GND

# 音频输出（音频数据获取）
RK3328 麦克风音频输出 ─── 3.5mm线 ─── Linux音频输入(Line-in/Mic)

# 回声消除（可选，如需播放音频）
RK3328 功放/回采输入 ─── 3.5mm线 ─── Linux音频输出
```

## 二、Linux环境配置

### 2.1 安装必要工具

```bash
# 串口工具和开发库
sudo apt-get update
sudo apt-get install -y \
    minicom \
    cu \
    screen \
    python3-serial \
    gcc \
    make

# 音频工具和库
sudo apt-get install -y \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils \
    libasound2-dev \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg \
    sox

# 检查USB转TTL驱动
lsmod | grep ch341    # CH340驱动
lsmod | grep cp210x   # CP2102驱动
```

### 2.2 查找设备

```bash
# 查找串口设备
ls -l /dev/ttyUSB*
# 或
dmesg | grep tty

# 查看音频设备
arecord -l    # 列出所有录音设备
aplay -l      # 列出所有播放设备

# 查看音频卡详细信息
cat /proc/asound/cards
```

### 2.3 配置串口权限

```bash
# 添加当前用户到dialout组（重启生效）
sudo usermod -a -G dialout $USER

# 或临时修改权限
sudo chmod 666 /dev/ttyUSB0
```

## 三、串口通信实现

### 3.1 Python串口控制脚本

```python
#!/usr/bin/env python3
"""
RK3328降噪板串口控制脚本
基于官方协议文档实现
"""

import serial
import json
import struct
import time
from typing import Dict, Any


class RK3328Controller:
    # 消息类型
    MSG_TYPE_HANDSHAKE = 0x01      # 握手消息
    MSG_TYPE_DEVICE = 0x02         # 设备消息
    MSG_TYPE_CONFIRM = 0x03        # 确认消息
    MSG_TYPE_MASTER = 0x04         # 主控消息

    # 串口参数
    BAUDRATE = 115200
    SYNC_HEAD = 0xA5
    USER_ID = 0x01

    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        """初始化串口连接"""
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.msg_id = 0

    def connect(self):
        """建立串口连接"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            print(f"串口已连接: {self.port}")

            # 等待握手
            self.wait_handshake()
            return True
        except Exception as e:
            print(f"串口连接失败: {e}")
            return False

    def wait_handshake(self, timeout=10):
        """等待设备握手"""
        print("等待设备握手...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            data = self.ser.read(100)
            if len(data) > 0:
                # 检查是否是握手消息
                if data[0] == self.SYNC_HEAD and data[2] == self.MSG_TYPE_HANDSHAKE:
                    print("收到握手消息，发送确认...")
                    # 发送确认消息
                    self.send_confirm(data[5:7])  # 使用原消息ID
                    print("握手成功！")
                    return True

        print("握手超时")
        return False

    def calculate_checksum(self, data: bytearray) -> int:
        """计算校验码"""
        return (~sum(data) + 1) & 0xFF

    def send_confirm(self, msg_id_bytes: bytes):
        """发送确认消息"""
        packet = bytearray()
        packet.append(self.SYNC_HEAD)
        packet.append(self.USER_ID)
        packet.append(self.MSG_TYPE_CONFIRM)
        packet.extend(struct.pack('<H', 0))  # 数据长度为0
        packet.extend(msg_id_bytes)          # 使用原消息ID

        checksum = self.calculate_checksum(packet)
        packet.append(checksum)

        self.ser.write(packet)

    def send_command(self, cmd_type: str, content: Dict[str, Any]):
        """发送主控命令"""
        # 构造JSON消息
        message = {
            "type": cmd_type,
            "content": content
        }
        json_data = json.dumps(message, ensure_ascii=False).encode('utf-8')

        # 构造协议包
        packet = bytearray()
        packet.append(self.SYNC_HEAD)
        packet.append(self.USER_ID)
        packet.append(self.MSG_TYPE_MASTER)

        # 消息长度（小端序）
        msg_len = len(json_data)
        packet.extend(struct.pack('<H', msg_len))

        # 消息ID（小端序）
        self.msg_id = (self.msg_id + 1) % 65536
        packet.extend(struct.pack('<H', self.msg_id))

        # JSON数据
        packet.extend(json_data)

        # 校验码
        checksum = self.calculate_checksum(packet)
        packet.append(checksum)

        # 发送
        self.ser.write(packet)
        print(f"已发送命令: {cmd_type}")

        # 等待确认
        time.sleep(0.1)
        return self.wait_confirm()

    def wait_confirm(self, timeout=1):
        """等待确认消息"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                if len(data) > 0 and data[2] == self.MSG_TYPE_CONFIRM:
                    print("收到确认")
                    return True
        return False

    def manual_wakeup(self, beam: int = 1):
        """手动唤醒，指定波束方向

        Args:
            beam: 波束序号
                环形六麦: 0-5 (0°, 60°, 120°, 180°, 240°, 300°)
                线性四麦: 0-2 (0°, 90°, 180°)
                线性六麦: 0-5
        """
        return self.send_command("manual_wakeup", {"beam": beam})

    def switch_wakeup_word(self, keyword: str, threshold: int = 900):
        """更换唤醒词（浅定制）

        Args:
            keyword: 唤醒词拼音，如 "xiao3 fei1 xiao3 fei1"
            threshold: 唤醒阈值，默认900
        """
        return self.send_command("wakeup_keywords", {
            "keyword": keyword,
            "threshold": str(threshold)
        })

    def switch_mic_array(self, mic_type: int):
        """切换麦克风阵列类型

        Args:
            mic_type: 0=环形6麦, 1=线性4麦, 2=线性6麦
        """
        return self.send_command("switch_mic", {"mic_type": mic_type})

    def read_device_message(self, timeout=1):
        """读取设备上报消息（如唤醒事件）"""
        start_time = time.time()
        buffer = bytearray()

        while time.time() - start_time < timeout:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                buffer.extend(data)

                # 查找完整的消息包
                if len(buffer) >= 7:
                    if buffer[0] == self.SYNC_HEAD and buffer[2] == self.MSG_TYPE_DEVICE:
                        msg_len = struct.unpack('<H', buffer[3:5])[0]
                        total_len = 7 + msg_len + 1  # 头+数据+校验

                        if len(buffer) >= total_len:
                            # 提取JSON数据
                            json_data = buffer[7:7+msg_len].decode('utf-8')
                            msg = json.loads(json_data)

                            # 发送确认
                            msg_id = buffer[5:7]
                            self.send_confirm(msg_id)

                            return msg

        return None

    def close(self):
        """关闭串口"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("串口已关闭")


# 使用示例
if __name__ == "__main__":
    controller = RK3328Controller('/dev/ttyUSB0')

    if controller.connect():
        # 手动唤醒，设置波束为0°方向
        controller.manual_wakeup(beam=0)

        # 等待并读取唤醒事件
        while True:
            msg = controller.read_device_message(timeout=5)
            if msg:
                print(f"收到设备消息: {msg}")
                if msg.get('type') == 'wakeup':
                    print(f"唤醒角度: {msg['content'].get('angle')}°")
                    print(f"唤醒得分: {msg['content'].get('score')}")
                    break

        controller.close()
```

### 3.2 C语言实现（参考官方）

官方提供了C语言参考代码，下载地址见文档：
- 串口实现参考_C语言.zip

## 四、音频采集实现

### 4.1 使用ALSA直接录音

```bash
# 查看音频设备
arecord -l

# 录音测试（16kHz, 单声道, 16bit）
arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 -d 10 test.wav

# 参数说明：
# -D hw:1,0  : 设备号（根据实际调整）
# -f S16_LE  : 格式 16bit 小端序
# -r 16000   : 采样率 16kHz
# -c 1       : 单声道
# -d 10      : 录制10秒
```

### 4.2 Python + PyAudio录音

```python
#!/usr/bin/env python3
"""
Linux环境下使用PyAudio录音
"""

import pyaudio
import wave
import numpy as np

class AudioRecorder:
    def __init__(self,
                 device_index=None,
                 rate=16000,
                 channels=1,
                 chunk=1024,
                 format=pyaudio.paInt16):
        self.rate = rate
        self.channels = channels
        self.chunk = chunk
        self.format = format
        self.device_index = device_index

        self.p = pyaudio.PyAudio()

    def list_devices(self):
        """列出所有音频设备"""
        print("\n可用音频输入设备：")
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"[{i}] {info['name']}")
                print(f"    采样率: {int(info['defaultSampleRate'])} Hz")
                print(f"    输入通道: {info['maxInputChannels']}")

    def record(self, duration=5, output_file='output.wav'):
        """录音

        Args:
            duration: 录音时长（秒）
            output_file: 输出文件名
        """
        stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk
        )

        print(f"开始录音 {duration} 秒...")
        frames = []

        for i in range(0, int(self.rate / self.chunk * duration)):
            data = stream.read(self.chunk, exception_on_overflow=False)
            frames.append(data)

            # 显示进度
            if i % 10 == 0:
                progress = (i * self.chunk) / (self.rate * duration) * 100
                print(f"\r进度: {progress:.1f}%", end='')

        print("\n录音完成")

        stream.stop_stream()
        stream.close()

        # 保存为WAV
        wf = wave.open(output_file, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()

        print(f"已保存到: {output_file}")

    def record_stream(self, callback, duration=None):
        """流式录音，实时回调

        Args:
            callback: 回调函数 callback(audio_data, frame_count)
            duration: 录音时长，None表示无限
        """
        stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk,
            stream_callback=self._stream_callback_wrapper(callback)
        )

        stream.start_stream()
        print("开始流式录音...")

        try:
            if duration:
                import time
                time.sleep(duration)
            else:
                while stream.is_active():
                    import time
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n停止录音")

        stream.stop_stream()
        stream.close()

    def _stream_callback_wrapper(self, callback):
        """包装流回调"""
        def stream_callback(in_data, frame_count, time_info, status):
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            callback(audio_data, frame_count)
            return (in_data, pyaudio.paContinue)
        return stream_callback

    def close(self):
        """关闭"""
        self.p.terminate()


# 使用示例
if __name__ == "__main__":
    recorder = AudioRecorder()

    # 列出设备
    recorder.list_devices()

    # 选择设备（根据实际情况修改）
    device_index = int(input("\n请输入设备编号: "))
    recorder.device_index = device_index

    # 录音5秒
    recorder.record(duration=5, output_file='rk3328_audio.wav')

    recorder.close()
```

### 4.3 使用ALSA C API

```c
// alsa_record.c
#include <alsa/asoundlib.h>
#include <stdio.h>

#define SAMPLE_RATE 16000
#define CHANNELS 1
#define FRAMES_PER_BUFFER 1024

int main() {
    snd_pcm_t *capture_handle;
    snd_pcm_hw_params_t *hw_params;
    short buffer[FRAMES_PER_BUFFER];

    // 打开PCM设备
    snd_pcm_open(&capture_handle, "default", SND_PCM_STREAM_CAPTURE, 0);

    // 配置参数
    snd_pcm_hw_params_alloc(&hw_params);
    snd_pcm_hw_params_any(capture_handle, hw_params);
    snd_pcm_hw_params_set_access(capture_handle, hw_params, SND_PCM_ACCESS_RW_INTERLEAVED);
    snd_pcm_hw_params_set_format(capture_handle, hw_params, SND_PCM_FORMAT_S16_LE);
    snd_pcm_hw_params_set_rate(capture_handle, hw_params, SAMPLE_RATE, 0);
    snd_pcm_hw_params_set_channels(capture_handle, hw_params, CHANNELS);
    snd_pcm_hw_params(capture_handle, hw_params);
    snd_pcm_hw_params_free(hw_params);

    // 准备录音
    snd_pcm_prepare(capture_handle);

    printf("开始录音...\n");

    // 录音循环
    for (int i = 0; i < 100; i++) {
        snd_pcm_readi(capture_handle, buffer, FRAMES_PER_BUFFER);
        // 处理音频数据
        // ...
    }

    snd_pcm_close(capture_handle);
    return 0;
}

// 编译: gcc alsa_record.c -o alsa_record -lasound
```

## 五、完整集成方案

### 5.1 串口控制 + 音频采集联动

```python
#!/usr/bin/env python3
"""
RK3328完整控制方案
同时控制串口和采集音频
"""

import threading
import queue
import time
from rk3328_controller import RK3328Controller
from audio_recorder import AudioRecorder

class RK3328System:
    def __init__(self, serial_port='/dev/ttyUSB0', audio_device=None):
        self.controller = RK3328Controller(serial_port)
        self.recorder = AudioRecorder(device_index=audio_device)
        self.audio_queue = queue.Queue()

    def start(self):
        """启动系统"""
        # 连接串口
        if not self.controller.connect():
            print("串口连接失败")
            return False

        # 手动唤醒，设置波束方向
        self.controller.manual_wakeup(beam=0)

        # 启动音频采集线程
        audio_thread = threading.Thread(
            target=self._audio_thread,
            daemon=True
        )
        audio_thread.start()

        # 启动串口监听线程
        serial_thread = threading.Thread(
            target=self._serial_thread,
            daemon=True
        )
        serial_thread.start()

        print("系统已启动")
        return True

    def _audio_thread(self):
        """音频采集线程"""
        def audio_callback(data, frame_count):
            # 将音频数据放入队列
            self.audio_queue.put(data)

            # 可以在这里做实时处理
            # 例如：VAD检测、发送到ASR等

        self.recorder.record_stream(audio_callback)

    def _serial_thread(self):
        """串口监听线程"""
        while True:
            msg = self.controller.read_device_message(timeout=1)
            if msg:
                self.on_device_message(msg)

    def on_device_message(self, msg):
        """处理设备消息"""
        msg_type = msg.get('type')

        if msg_type == 'wakeup':
            content = msg.get('content', {})
            angle = content.get('angle')
            score = content.get('score')
            beam = content.get('beam')

            print(f"\n[唤醒事件]")
            print(f"  角度: {angle}°")
            print(f"  得分: {score}")
            print(f"  波束: {beam}")

            # 可以根据唤醒角度切换波束
            # self.controller.manual_wakeup(beam=beam)

    def get_audio_data(self, timeout=1):
        """获取音频数据"""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        """停止系统"""
        self.controller.close()
        self.recorder.close()


# 使用
if __name__ == "__main__":
    system = RK3328System(
        serial_port='/dev/ttyUSB0',
        audio_device=1  # 根据实际修改
    )

    if system.start():
        try:
            while True:
                # 获取音频数据
                audio_data = system.get_audio_data(timeout=0.1)
                if audio_data is not None:
                    # 处理音频：发送到ASR、保存等
                    pass

                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\n停止中...")
            system.stop()
```

## 六、音频参数配置

根据AIUI平台的标准，推荐配置：

```python
AUDIO_CONFIG = {
    'sample_rate': 16000,     # 16kHz采样率（语音识别标准）
    'channels': 1,            # 单声道（已经过波束成形）
    'sample_width': 2,        # 16bit = 2字节
    'format': 'pcm',          # PCM格式
    'encoding': 'signed',     # 有符号整数
    'endian': 'little'        # 小端序
}
```

## 七、故障排查

### 7.1 串口问题

```bash
# 检查串口是否存在
ls -l /dev/ttyUSB*

# 检查权限
sudo chmod 666 /dev/ttyUSB0

# 测试串口通信
minicom -D /dev/ttyUSB0 -b 115200

# 查看串口通信日志
dmesg | grep ttyUSB
```

### 7.2 音频问题

```bash
# 检查ALSA设备
arecord -l
aplay -l

# 测试录音
arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav
aplay test.wav

# 查看PulseAudio状态
pactl list sources

# 重启音频服务
pulseaudio -k
pulseaudio --start
```

### 7.3 常见错误

| 错误 | 原因 | 解决方法 |
|------|------|----------|
| Permission denied | 串口权限不足 | sudo usermod -a -G dialout $USER |
| Device busy | 串口被占用 | 关闭其他串口程序 |
| No such device | 音频设备未识别 | 检查音频线连接，arecord -l |
| Underrun | 音频缓冲区溢出 | 增大chunk大小 |

## 八、后续应用

获取到音频后，可以：

1. **发送到AIUI API进行识别**
   ```python
   # 使用AIUI WebSocket API
   # 参考文档: 4.1.1 交互API
   ```

2. **本地VAD检测**
   ```python
   import webrtcvad
   vad = webrtcvad.Vad(3)  # 灵敏度 0-3
   ```

3. **保存音频文件**
   ```python
   wave.open('recording.wav', 'wb')
   ```

4. **实时流式识别**
   ```python
   # WebSocket流式发送到ASR服务
   ```

## 参考资料

- RK3328降噪板使用手册: `docs/06.html`
- RK3328降噪板协议手册: `docs/08.html`
- 官方C语言参考代码: 串口实现参考_C语言.zip
- AIUI API文档: 第4章
