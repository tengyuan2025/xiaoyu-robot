#!/usr/bin/env python3
"""
实时音频流获取示例
演示如何从USB声卡实时获取音频流并处理
"""

import sys
import numpy as np
import pyaudio
import queue
import threading
import time
from collections import deque


class RealtimeAudioStream:
    """实时音频流处理器"""

    def __init__(self, device_index=None, rate=16000, chunk=1024):
        """
        初始化

        Args:
            device_index: 音频设备索引（USB声卡）
            rate: 采样率 (Hz)
            chunk: 缓冲区大小（采样点数）
        """
        self.device_index = device_index
        self.rate = rate
        self.chunk = chunk
        self.format = pyaudio.paInt16
        self.channels = 1

        self.p = pyaudio.PyAudio()
        self.stream = None
        self.is_running = False

        # 音频数据队列
        self.audio_queue = queue.Queue()

        # 音频缓冲区（用于VAD等需要历史数据的场景）
        self.buffer = deque(maxlen=int(rate * 2))  # 保留2秒历史数据

    def start(self):
        """启动音频流"""
        if self.is_running:
            print("音频流已在运行")
            return

        try:
            self.stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk,
                stream_callback=self._audio_callback
            )

            self.is_running = True
            self.stream.start_stream()
            print(f"✓ 音频流已启动 (设备:{self.device_index}, 采样率:{self.rate}Hz)")

        except Exception as e:
            print(f"✗ 启动音频流失败: {e}")
            raise

    def stop(self):
        """停止音频流"""
        if not self.is_running:
            return

        self.is_running = False

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        print("✓ 音频流已停止")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        PyAudio音频回调函数（内部使用）
        在独立线程中被调用
        """
        # 将原始字节数据转为numpy数组
        audio_data = np.frombuffer(in_data, dtype=np.int16)

        # 放入队列供主线程处理
        self.audio_queue.put(audio_data)

        # 添加到缓冲区
        self.buffer.extend(audio_data)

        return (in_data, pyaudio.paContinue)

    def get_audio_chunk(self, timeout=1):
        """
        获取一个音频数据块

        Args:
            timeout: 超时时间（秒）

        Returns:
            numpy数组，如果超时返回None
        """
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_buffer_data(self):
        """
        获取缓冲区的所有历史数据

        Returns:
            numpy数组
        """
        return np.array(list(self.buffer))

    def close(self):
        """关闭音频流"""
        self.stop()
        self.p.terminate()


# ==================== 应用示例 ====================

def example_1_basic_streaming():
    """示例1: 基本音频流监听"""
    print("\n" + "="*60)
    print("示例1: 基本音频流监听")
    print("="*60)

    # 创建音频流
    stream = RealtimeAudioStream(device_index=1, rate=16000)

    try:
        stream.start()
        print("\n开始监听音频流...")
        print("按 Ctrl+C 停止\n")

        while True:
            # 获取音频数据
            audio_chunk = stream.get_audio_chunk(timeout=1)

            if audio_chunk is not None:
                # 计算音量
                volume = np.abs(audio_chunk).mean()
                max_value = np.max(np.abs(audio_chunk))

                # 显示音量条
                bar_length = int(volume / 100)
                bar = '█' * bar_length + '░' * (50 - bar_length)

                print(f"\r音量: [{bar}] {volume:.0f} (峰值:{max_value})",
                      end='', flush=True)

    except KeyboardInterrupt:
        print("\n\n停止监听")
    finally:
        stream.close()


def example_2_vad_detection():
    """示例2: 语音活动检测（VAD）"""
    print("\n" + "="*60)
    print("示例2: 语音活动检测（VAD）")
    print("="*60)

    stream = RealtimeAudioStream(device_index=1, rate=16000)

    # VAD参数
    SPEECH_THRESHOLD = 500  # 语音音量阈值
    SILENCE_DURATION = 1.0  # 静音持续时间（秒）

    is_speaking = False
    silence_start = None
    speech_buffer = []

    try:
        stream.start()
        print("\n开始检测语音活动...")
        print("请说话测试...\n")

        while True:
            audio_chunk = stream.get_audio_chunk(timeout=1)

            if audio_chunk is not None:
                volume = np.abs(audio_chunk).mean()

                # 检测语音开始
                if not is_speaking and volume > SPEECH_THRESHOLD:
                    is_speaking = True
                    silence_start = None
                    speech_buffer = [audio_chunk]
                    print("\n🎤 检测到语音开始...")

                # 语音进行中
                elif is_speaking and volume > SPEECH_THRESHOLD:
                    silence_start = None
                    speech_buffer.append(audio_chunk)

                # 检测静音
                elif is_speaking and volume <= SPEECH_THRESHOLD:
                    if silence_start is None:
                        silence_start = time.time()

                    speech_buffer.append(audio_chunk)

                    # 静音超过阈值，判定语音结束
                    if time.time() - silence_start > SILENCE_DURATION:
                        print(f"✓ 语音结束 (时长: {len(speech_buffer) * 0.064:.1f}秒)")

                        # 合并所有音频数据
                        full_audio = np.concatenate(speech_buffer)

                        # 这里可以：
                        # 1. 保存为文件
                        # 2. 发送到ASR
                        # 3. 进行其他处理
                        print(f"   共采集 {len(full_audio)} 个采样点")

                        # 重置
                        is_speaking = False
                        silence_start = None
                        speech_buffer = []
                        print("\n等待下一次语音...\n")

                # 显示状态
                status = "🔴 语音中" if is_speaking else "⚪ 静音"
                print(f"\r{status}  音量: {volume:.0f}  ", end='', flush=True)

    except KeyboardInterrupt:
        print("\n\n停止检测")
    finally:
        stream.close()


def example_3_realtime_asr():
    """示例3: 实时ASR集成（模拟）"""
    print("\n" + "="*60)
    print("示例3: 实时ASR集成")
    print("="*60)

    from rk3328_controller import RK3328Controller

    stream = RealtimeAudioStream(device_index=1, rate=16000)
    controller = RK3328Controller('/dev/ttyUSB0')

    if not controller.connect():
        print("串口连接失败")
        return

    is_recording = False
    recording_buffer = []

    try:
        stream.start()
        print("\n✓ 系统就绪")
        print("流程: 等待唤醒 → 实时录音 → 发送ASR\n")

        # 启动音频处理线程
        def audio_processor():
            while stream.is_running:
                audio_chunk = stream.get_audio_chunk(timeout=0.1)

                if audio_chunk is not None and is_recording:
                    recording_buffer.append(audio_chunk)

                    # 每隔0.5秒可以发送一次到实时ASR
                    if len(recording_buffer) % 8 == 0:  # 约0.5秒
                        # 模拟发送到实时ASR
                        audio_segment = np.concatenate(recording_buffer[-8:])
                        print(f"\r→ 发送音频到ASR ({len(audio_segment)}采样点)",
                              end='', flush=True)

                        # 这里调用实时ASR API
                        # result = realtime_asr_api.send(audio_segment)

        threading.Thread(target=audio_processor, daemon=True).start()

        while True:
            # 监听唤醒事件
            msg = controller.read_device_message(timeout=1)

            if msg and msg.get('type') == 'wakeup':
                angle = msg['content']['angle']
                print(f"\n🎤 唤醒检测 (方向: {angle}°)")
                print("开始实时录音，请说话...")

                is_recording = True
                recording_buffer = []

                # 录音5秒
                time.sleep(5)

                is_recording = False

                # 处理完整录音
                if recording_buffer:
                    full_audio = np.concatenate(recording_buffer)
                    print(f"\n✓ 录音完成 (时长: {len(full_audio)/16000:.1f}秒)")
                    print("→ 发送完整音频到ASR...")

                    # 这里调用ASR API
                    # result = asr_api.recognize(full_audio)
                    # print(f"识别结果: {result}")

                    print("\n等待下一次唤醒...\n")

    except KeyboardInterrupt:
        print("\n\n程序退出")
    finally:
        stream.close()
        controller.close()


def example_4_audio_analysis():
    """示例4: 实时音频分析"""
    print("\n" + "="*60)
    print("示例4: 实时音频分析")
    print("="*60)

    stream = RealtimeAudioStream(device_index=1, rate=16000, chunk=2048)

    try:
        stream.start()
        print("\n开始音频分析...")
        print("显示: 音量 | 过零率 | 频谱能量\n")

        while True:
            audio_chunk = stream.get_audio_chunk(timeout=1)

            if audio_chunk is not None:
                # 1. 音量
                volume = np.abs(audio_chunk).mean()

                # 2. 过零率（Zero Crossing Rate）
                # 用于区分语音和噪音
                zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_chunk))))
                zcr = zero_crossings / len(audio_chunk)

                # 3. 频谱能量
                fft = np.fft.fft(audio_chunk)
                spectrum_energy = np.abs(fft[:len(fft)//2]).mean()

                # 显示
                print(f"\r音量:{volume:6.0f} | 过零率:{zcr:.3f} | "
                      f"频谱:{spectrum_energy:6.0f}  ",
                      end='', flush=True)

    except KeyboardInterrupt:
        print("\n\n停止分析")
    finally:
        stream.close()


def main():
    """主函数"""
    print("="*60)
    print("实时音频流获取示例")
    print("="*60)

    print("\n请选择示例:")
    print("  1. 基本音频流监听")
    print("  2. 语音活动检测（VAD）")
    print("  3. 实时ASR集成")
    print("  4. 实时音频分析")

    choice = input("\n请选择 (1-4): ").strip()

    if choice == '1':
        example_1_basic_streaming()
    elif choice == '2':
        example_2_vad_detection()
    elif choice == '3':
        example_3_realtime_asr()
    elif choice == '4':
        example_4_audio_analysis()
    else:
        print("无效选择")


if __name__ == '__main__':
    main()
