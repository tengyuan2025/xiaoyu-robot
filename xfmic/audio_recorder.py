#!/usr/bin/env python3
"""
Linux环境下音频录制工具
使用PyAudio从RK3328降噪板采集音频
"""

import pyaudio
import wave
import numpy as np
from typing import Callable, Optional
import sys


class AudioRecorder:
    """音频录制器"""

    def __init__(self,
                 device_index: Optional[int] = None,
                 rate: int = 16000,
                 channels: int = 1,
                 chunk: int = 1024,
                 format: int = pyaudio.paInt16):
        """初始化音频录制器

        Args:
            device_index: 音频设备索引，None表示使用默认设备
            rate: 采样率，默认16000 Hz
            channels: 声道数，默认1（单声道）
            chunk: 缓冲区大小，默认1024帧
            format: 音频格式，默认16bit PCM
        """
        self.rate = rate
        self.channels = channels
        self.chunk = chunk
        self.format = format
        self.device_index = device_index

        self.p = pyaudio.PyAudio()

    def list_devices(self):
        """列出所有可用的音频输入设备"""
        print("\n" + "="*60)
        print("可用音频输入设备：")
        print("="*60)

        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"\n[设备 {i}]")
                print(f"  名称: {info['name']}")
                print(f"  采样率: {int(info['defaultSampleRate'])} Hz")
                print(f"  输入通道: {info['maxInputChannels']}")
                print(f"  输出通道: {info['maxOutputChannels']}")

        print("\n" + "="*60)

    def record(self, duration: int = 5, output_file: str = 'output.wav'):
        """录音到文件

        Args:
            duration: 录音时长（秒）
            output_file: 输出WAV文件路径
        """
        try:
            stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk
            )

            print(f"\n开始录音 {duration} 秒...")
            print(f"采样率: {self.rate} Hz")
            print(f"声道: {self.channels}")
            print(f"格式: 16bit PCM")

            frames = []
            total_frames = int(self.rate / self.chunk * duration)

            for i in range(total_frames):
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    frames.append(data)

                    # 显示进度条
                    progress = (i + 1) / total_frames * 100
                    bar_length = 40
                    filled = int(bar_length * (i + 1) / total_frames)
                    bar = '█' * filled + '-' * (bar_length - filled)
                    print(f'\r录音进度: |{bar}| {progress:.1f}%', end='')

                except IOError as e:
                    print(f"\n警告: 音频溢出 {e}")
                    continue

            print("\n录音完成！")

            stream.stop_stream()
            stream.close()

            # 保存为WAV文件
            self._save_wav(output_file, frames)

        except Exception as e:
            print(f"录音错误: {e}")

    def _save_wav(self, filename: str, frames: list):
        """保存音频数据为WAV文件

        Args:
            filename: 文件名
            frames: 音频帧列表
        """
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()

        print(f"✓ 已保存到: {filename}")

        # 显示文件信息
        import os
        file_size = os.path.getsize(filename)
        duration = len(frames) * self.chunk / self.rate
        print(f"  文件大小: {file_size / 1024:.1f} KB")
        print(f"  时长: {duration:.1f} 秒")

    def record_stream(self,
                      callback: Callable[[np.ndarray, int], None],
                      duration: Optional[int] = None):
        """流式录音，实时回调处理音频数据

        Args:
            callback: 回调函数 callback(audio_data, frame_count)
                audio_data: numpy数组，int16类型
                frame_count: 帧数
            duration: 录音时长（秒），None表示无限
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
        print("按 Ctrl+C 停止")

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

    def _stream_callback_wrapper(self, callback: Callable):
        """包装流回调函数"""
        def stream_callback(in_data, frame_count, time_info, status):
            # 转换为numpy数组
            audio_data = np.frombuffer(in_data, dtype=np.int16)

            # 调用用户回调
            callback(audio_data, frame_count)

            return (in_data, pyaudio.paContinue)

        return stream_callback

    def record_with_vad(self,
                        output_file: str = 'output.wav',
                        silence_threshold: int = 500,
                        silence_duration: float = 2.0):
        """带VAD（语音活动检测）的录音
        自动检测静音并停止录音

        Args:
            output_file: 输出文件
            silence_threshold: 静音阈值（音量低于此值视为静音）
            silence_duration: 连续静音多久后停止录音（秒）
        """
        stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk
        )

        print("\n开始录音（自动检测静音）...")
        print(f"静音阈值: {silence_threshold}")
        print(f"静音时长: {silence_duration}s")

        frames = []
        silent_chunks = 0
        max_silent_chunks = int(self.rate / self.chunk * silence_duration)

        try:
            while True:
                data = stream.read(self.chunk, exception_on_overflow=False)
                frames.append(data)

                # 计算音量
                audio_data = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_data).mean()

                # VAD检测
                if volume < silence_threshold:
                    silent_chunks += 1
                    print(f'\r静音检测: {silent_chunks}/{max_silent_chunks} 音量: {int(volume):4d}', end='')

                    if silent_chunks > max_silent_chunks:
                        print("\n检测到持续静音，停止录音")
                        break
                else:
                    if silent_chunks > 0:
                        print()  # 换行
                    silent_chunks = 0
                    print(f'\r录音中... 音量: {int(volume):4d}', end='')

        except KeyboardInterrupt:
            print("\n手动停止录音")

        stream.stop_stream()
        stream.close()

        # 保存
        self._save_wav(output_file, frames)

    def close(self):
        """关闭音频设备"""
        self.p.terminate()


def main():
    """命令行主程序"""
    recorder = AudioRecorder()

    print("="*60)
    print("RK3328降噪板音频录制工具")
    print("="*60)

    while True:
        print("\n菜单：")
        print("1. 列出音频设备")
        print("2. 录音（指定时长）")
        print("3. 流式录音（实时处理）")
        print("4. VAD录音（自动检测静音）")
        print("5. 退出")

        choice = input("\n请选择 [1-5]: ").strip()

        if choice == '1':
            recorder.list_devices()
            device = input("\n请输入要使用的设备编号（留空使用默认）: ").strip()
            if device:
                recorder.device_index = int(device)
                print(f"已选择设备: {device}")

        elif choice == '2':
            duration = input("录音时长（秒，默认5）: ").strip()
            duration = int(duration) if duration else 5

            filename = input("输出文件名（默认output.wav）: ").strip()
            filename = filename if filename else 'output.wav'

            recorder.record(duration=duration, output_file=filename)

        elif choice == '3':
            print("\n流式录音示例（显示实时音量）")

            # 定义回调函数
            def audio_callback(data, frame_count):
                volume = np.abs(data).mean()
                print(f'\r实时音量: {int(volume):4d}', end='')

            duration = input("录音时长（秒，留空表示无限）: ").strip()
            duration = int(duration) if duration else None

            try:
                recorder.record_stream(audio_callback, duration=duration)
            except KeyboardInterrupt:
                print("\n停止录音")

        elif choice == '4':
            filename = input("输出文件名（默认output.wav）: ").strip()
            filename = filename if filename else 'output.wav'

            recorder.record_with_vad(output_file=filename)

        elif choice == '5':
            break

        else:
            print("无效选择")

    recorder.close()
    print("\n再见！")


if __name__ == "__main__":
    main()
