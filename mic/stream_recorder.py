#!/usr/bin/env python3
"""
实时音频流录制工具
持续录制来自RK3328的音频数据并保存到文件
按 Ctrl+C 停止录制
"""

import pyaudio
import wave
import sys
import os
from datetime import datetime
import time


class StreamRecorder:
    """实时音频流录制器"""

    def __init__(self, device_index=None):
        """初始化录制器

        Args:
            device_index: 音频输入设备索引，None表示使用默认设备
        """
        self.device_index = device_index
        self.audio = pyaudio.PyAudio()

        # RK3328音频参数
        self.sample_rate = 16000    # 16kHz
        self.channels = 1           # 单声道
        self.format = pyaudio.paInt16  # 16位PCM
        self.chunk_size = 1024      # 每次读取的帧数

        self.stream = None
        self.wf = None
        self.is_recording = False

    def list_devices(self):
        """列出所有可用的音频输入设备"""
        print("\n可用的音频输入设备：")
        print("-" * 70)

        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"[{i}] {info['name']}")
                print(f"    采样率: {int(info['defaultSampleRate'])} Hz")
                print(f"    输入通道: {info['maxInputChannels']}")
                print()

        print("-" * 70)

    def start_recording(self, output_file=None):
        """开始录制音频流

        Args:
            output_file: 输出文件路径，None则自动生成文件名
        """
        # 生成输出文件名
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"audio_stream_{timestamp}.wav"

        # 确保文件路径在xfmic目录下
        if not os.path.isabs(output_file):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_file = os.path.join(script_dir, output_file)

        print(f"\n开始录制音频流...")
        print(f"输出文件: {output_file}")
        print(f"采样率: {self.sample_rate} Hz")
        print(f"声道数: {self.channels}")
        print(f"格式: 16-bit PCM")

        if self.device_index is not None:
            device_info = self.audio.get_device_info_by_index(self.device_index)
            print(f"输入设备: [{self.device_index}] {device_info['name']}")

        print("\n按 Ctrl+C 停止录制\n")

        # 打开WAV文件
        self.wf = wave.open(output_file, 'wb')
        self.wf.setnchannels(self.channels)
        self.wf.setsampwidth(self.audio.get_sample_size(self.format))
        self.wf.setframerate(self.sample_rate)

        # 打开音频流
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._audio_callback
        )

        self.is_recording = True
        self.frame_count = 0
        self.start_time = time.time()

        # 开始录制
        self.stream.start_stream()

        try:
            # 持续显示录制状态
            while self.is_recording and self.stream.is_active():
                elapsed = time.time() - self.start_time
                size_mb = (self.frame_count * self.channels * 2) / (1024 * 1024)

                print(f"\r录制中... 时长: {int(elapsed)}秒 | 数据量: {size_mb:.2f} MB | 帧数: {self.frame_count}", end='', flush=True)
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n\n收到停止信号，正在保存文件...")

        self.stop_recording()

        # 显示录制统计
        total_time = time.time() - self.start_time
        file_size = os.path.getsize(output_file) / (1024 * 1024)

        print(f"\n录制完成！")
        print(f"  总时长: {int(total_time)} 秒")
        print(f"  文件大小: {file_size:.2f} MB")
        print(f"  保存位置: {output_file}")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """音频流回调函数"""
        if status:
            print(f"\n警告: {status}")

        # 写入数据到文件
        if self.wf:
            self.wf.writeframes(in_data)
            self.frame_count += frame_count

        return (in_data, pyaudio.paContinue)

    def stop_recording(self):
        """停止录制"""
        self.is_recording = False

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        if self.wf:
            self.wf.close()
            self.wf = None

    def close(self):
        """关闭录制器，释放资源"""
        self.stop_recording()
        self.audio.terminate()


def main():
    """主程序"""
    print("=" * 70)
    print("RK3328 实时音频流录制工具")
    print("=" * 70)

    recorder = StreamRecorder()

    # 显示帮助信息
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("\n用法:")
        print(f"  {sys.argv[0]} [设备索引] [输出文件名]")
        print("\n示例:")
        print(f"  {sys.argv[0]}                    # 使用默认设备")
        print(f"  {sys.argv[0]} 1                  # 使用设备1")
        print(f"  {sys.argv[0]} 1 my_audio.wav    # 使用设备1并指定文件名")
        print(f"  {sys.argv[0]} --list             # 列出所有设备")
        print()
        recorder.close()
        return

    # 列出设备
    if len(sys.argv) > 1 and sys.argv[1] == '--list':
        recorder.list_devices()
        recorder.close()
        return

    # 解析命令行参数
    device_index = None
    output_file = None

    if len(sys.argv) > 1:
        try:
            device_index = int(sys.argv[1])
            recorder.device_index = device_index
        except ValueError:
            print(f"错误: 设备索引必须是数字，得到: {sys.argv[1]}")
            print(f"使用 '{sys.argv[0]} --list' 查看可用设备")
            recorder.close()
            return

    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    # 如果没有指定设备，列出可用设备供选择
    if device_index is None:
        recorder.list_devices()

        choice = input("请选择音频输入设备索引（留空使用默认设备）: ").strip()

        if choice:
            try:
                device_index = int(choice)
                recorder.device_index = device_index
            except ValueError:
                print("无效的设备索引，使用默认设备")

    try:
        # 开始录制
        recorder.start_recording(output_file)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        recorder.close()
        print("\n再见！")


if __name__ == "__main__":
    main()
