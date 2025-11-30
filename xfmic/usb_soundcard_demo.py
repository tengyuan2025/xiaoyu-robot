#!/usr/bin/env python3
"""
USB声卡方案完整示例
演示如何使用RK3328 + USB声卡进行语音交互
"""

import sys
import time
from rk3328_controller import RK3328Controller
from audio_recorder import AudioRecorder


def find_usb_soundcard():
    """自动查找USB声卡设备

    Returns:
        int: USB声卡设备索引，未找到返回None
    """
    import pyaudio

    p = pyaudio.PyAudio()
    usb_devices = []

    print("\n正在扫描USB声卡...")
    print("="*60)

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        device_name = info['name'].lower()

        # USB声卡常见关键词
        usb_keywords = ['usb', 'external', 'sound card', 'audio adapter']

        if info['maxInputChannels'] > 0:
            is_usb = any(keyword in device_name for keyword in usb_keywords)

            print(f"[{i}] {info['name']}")
            print(f"    类型: {'USB声卡 ✓' if is_usb else '内置设备'}")
            print(f"    采样率: {int(info['defaultSampleRate'])} Hz")
            print(f"    通道数: {info['maxInputChannels']}")
            print()

            if is_usb:
                usb_devices.append(i)

    p.terminate()

    if usb_devices:
        print(f"找到 {len(usb_devices)} 个USB声卡设备")
        return usb_devices[0]  # 返回第一个USB声卡
    else:
        print("⚠️  未找到USB声卡，将使用默认设备")
        return None


def demo_basic_wakeup_and_record(serial_port, audio_device):
    """示例1: 基本唤醒+录音

    Args:
        serial_port: 串口设备路径
        audio_device: 音频设备索引
    """
    print("\n" + "="*60)
    print("示例1: 唤醒后录音")
    print("="*60)

    controller = RK3328Controller(serial_port)
    recorder = AudioRecorder(device_index=audio_device, rate=16000)

    if not controller.connect():
        print("❌ 串口连接失败")
        return

    try:
        print("\n✓ 系统就绪")
        print("请说唤醒词（如：小飞小飞）...")
        print("按 Ctrl+C 退出\n")

        while True:
            # 等待唤醒事件
            msg = controller.read_device_message(timeout=1)

            if msg and msg.get('type') == 'wakeup':
                content = msg.get('content', {})
                angle = content.get('angle', 0)
                beam = content.get('beam', 0)

                print(f"\n🎙️  检测到唤醒！")
                print(f"   声源方向: {angle}°")
                print(f"   波束编号: {beam}")
                print(f"   开始录音5秒...")

                # 录音5秒
                filename = f"voice_{int(time.time())}.wav"
                recorder.record(duration=5, output_file=filename)

                print(f"   ✓ 录音已保存: {filename}")
                print(f"\n等待下一次唤醒...")

    except KeyboardInterrupt:
        print("\n\n程序退出")
    finally:
        controller.close()
        recorder.close()


def demo_stream_processing(serial_port, audio_device):
    """示例2: 流式音频处理

    Args:
        serial_port: 串口设备路径
        audio_device: 音频设备索引
    """
    print("\n" + "="*60)
    print("示例2: 实时音频流处理")
    print("="*60)

    import numpy as np
    import queue
    import threading

    controller = RK3328Controller(serial_port)
    recorder = AudioRecorder(device_index=audio_device, rate=16000)

    if not controller.connect():
        print("❌ 串口连接失败")
        return

    audio_queue = queue.Queue()
    is_recording = False

    def audio_callback(data, frame_count):
        """音频流回调"""
        if is_recording:
            audio_queue.put(data)

    def process_audio_thread():
        """音频处理线程"""
        nonlocal is_recording

        while True:
            if not audio_queue.empty():
                audio_data = audio_queue.get()

                # 计算音量（示例）
                volume = np.abs(audio_data).mean()

                # 这里可以：
                # 1. 发送到ASR进行实时识别
                # 2. 进行VAD检测
                # 3. 保存到缓冲区
                print(f"\r音频音量: {volume:.2f}  ", end='', flush=True)

    try:
        print("\n✓ 系统就绪")
        print("请说唤醒词...")

        # 启动音频处理线程
        threading.Thread(target=process_audio_thread, daemon=True).start()

        # 启动音频流
        threading.Thread(
            target=recorder.record_stream,
            args=(audio_callback,),
            daemon=True
        ).start()

        while True:
            msg = controller.read_device_message(timeout=1)

            if msg and msg.get('type') == 'wakeup':
                print(f"\n🎙️  唤醒检测！开始录音...")
                is_recording = True

                # 录音5秒
                time.sleep(5)

                is_recording = False
                print(f"\n   录音结束\n")

    except KeyboardInterrupt:
        print("\n\n程序退出")
    finally:
        controller.close()
        recorder.close()


def demo_voice_interaction(serial_port, audio_device):
    """示例3: 完整语音交互流程

    Args:
        serial_port: 串口设备路径
        audio_device: 音频设备索引
    """
    print("\n" + "="*60)
    print("示例3: 完整语音交互")
    print("="*60)

    controller = RK3328Controller(serial_port)
    recorder = AudioRecorder(device_index=audio_device, rate=16000)

    if not controller.connect():
        print("❌ 串口连接失败")
        return

    try:
        print("\n✓ 语音交互系统就绪")
        print("流程: 唤醒 → 录音 → 识别 → 响应")
        print("请说唤醒词...\n")

        while True:
            # 1. 等待唤醒
            msg = controller.read_device_message(timeout=1)

            if msg and msg.get('type') == 'wakeup':
                content = msg.get('content', {})
                angle = content.get('angle', 0)

                print(f"[1/4] 唤醒检测 ✓ (方向: {angle}°)")

                # 2. 录音
                print(f"[2/4] 录音中...")
                filename = f"temp_voice.wav"
                recorder.record(duration=5, output_file=filename)
                print(f"[2/4] 录音完成 ✓")

                # 3. 发送到ASR识别（这里用模拟）
                print(f"[3/4] 语音识别中...")
                time.sleep(1)  # 模拟ASR处理

                # TODO: 实际应用中，这里调用ASR API
                # result = call_asr_api(filename)
                result = "模拟识别结果: 今天天气怎么样"
                print(f"[3/4] 识别完成 ✓")
                print(f"      识别结果: {result}")

                # 4. 响应处理
                print(f"[4/4] 生成响应...")
                # TODO: 调用NLU/TTS等
                print(f"[4/4] 响应完成 ✓")

                print(f"\n等待下一次唤醒...\n")

    except KeyboardInterrupt:
        print("\n\n程序退出")
    finally:
        controller.close()
        recorder.close()


def main():
    """主函数"""
    print("="*60)
    print("USB声卡方案 - RK3328语音交互演示")
    print("="*60)

    # 检查参数
    if len(sys.argv) < 2:
        print("\n自动检测设备...")
        serial_port = '/dev/ttyUSB0'  # 默认串口
        audio_device = find_usb_soundcard()
    elif len(sys.argv) == 3:
        serial_port = sys.argv[1]
        audio_device = int(sys.argv[2])
        print(f"\n使用指定设备:")
        print(f"  串口: {serial_port}")
        print(f"  音频: 设备{audio_device}")
    else:
        print("\n使用方法:")
        print(f"  {sys.argv[0]} [串口设备] [音频设备号]")
        print(f"\n示例:")
        print(f"  {sys.argv[0]}                          # 自动检测")
        print(f"  {sys.argv[0]} /dev/ttyUSB0 1          # 手动指定")
        return

    # 选择示例
    print("\n请选择运行示例:")
    print("  1. 基本唤醒+录音")
    print("  2. 实时音频流处理")
    print("  3. 完整语音交互")

    choice = input("\n请选择 (1-3): ").strip()

    if choice == '1':
        demo_basic_wakeup_and_record(serial_port, audio_device)
    elif choice == '2':
        demo_stream_processing(serial_port, audio_device)
    elif choice == '3':
        demo_voice_interaction(serial_port, audio_device)
    else:
        print("无效选择")


if __name__ == '__main__':
    main()
