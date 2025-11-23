#!/usr/bin/env python3
"""
RK3328降噪板 Mac专用示例
自动检测串口设备，简化Mac用户使用
"""

import glob
import sys
from rk3328_controller import RK3328Controller
from audio_recorder import AudioRecorder


def find_serial_port():
    """自动查找Mac上的串口设备"""
    print("正在查找串口设备...")

    # Mac上的串口设备模式
    patterns = [
        '/dev/tty.usbserial*',
        '/dev/tty.wchusbserial*',
        '/dev/tty.SLAB_USBtoUART*',
        '/dev/tty.usbmodem*'
    ]

    ports = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))

    if not ports:
        print("\n❌ 未找到串口设备\n")
        print("请检查：")
        print("1. USB转TTL是否已连接到Mac")
        print("2. CH340驱动是否已安装")
        print("   下载地址: http://www.wch.cn/downloads/CH341SER_MAC_ZIP.html")
        print("3. 驱动安装后是否已重启Mac")
        print("\n安装驱动后，在'系统偏好设置 > 安全性与隐私'中可能需要允许驱动")
        return None

    print(f"\n✓ 找到 {len(ports)} 个串口设备：")
    for i, port in enumerate(ports):
        print(f"  [{i}] {port}")

    if len(ports) == 1:
        print(f"\n使用设备: {ports[0]}")
        return ports[0]
    else:
        while True:
            choice = input(f"\n请选择设备 [0-{len(ports)-1}]: ").strip()
            try:
                idx = int(choice)
                if 0 <= idx < len(ports):
                    return ports[idx]
            except ValueError:
                pass
            print("无效选择，请重试")


def check_audio_input():
    """检查Mac音频输入"""
    print("\n正在检查音频设备...")

    try:
        import pyaudio
        p = pyaudio.PyAudio()

        input_devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append((i, info))

        p.terminate()

        if not input_devices:
            print("\n⚠️  未找到音频输入设备")
            print("\n可能的原因：")
            print("1. Mac没有音频输入接口（部分新款Mac仅有输出）")
            print("2. 需要使用USB声卡")
            print("3. 需要在'系统偏好设置 > 安全性与隐私 > 隐私 > 麦克风'中授权")
            return None

        print(f"\n✓ 找到 {len(input_devices)} 个音频输入设备：")
        for i, (idx, info) in enumerate(input_devices):
            print(f"  [{i}] {info['name']}")
            print(f"      采样率: {int(info['defaultSampleRate'])} Hz")

        if len(input_devices) == 1:
            device_idx = input_devices[0][0]
            print(f"\n使用设备: {input_devices[0][1]['name']}")
            return device_idx
        else:
            while True:
                choice = input(f"\n请选择音频设备 [0-{len(input_devices)-1}]: ").strip()
                try:
                    idx = int(choice)
                    if 0 <= idx < len(input_devices):
                        return input_devices[idx][0]
                except ValueError:
                    pass
                print("无效选择，请重试")

    except Exception as e:
        print(f"\n⚠️  音频检查出错: {e}")
        return None


def demo_basic(controller):
    """基本功能演示"""
    print("\n" + "="*60)
    print("基本功能演示")
    print("="*60)
    print("\n等待唤醒事件（按 Ctrl+C 退出）...")

    try:
        while True:
            msg = controller.read_device_message(timeout=2)
            if msg:
                import json
                print(f"\n收到消息:\n{json.dumps(msg, ensure_ascii=False, indent=2)}")

                if msg.get('type') == 'wakeup':
                    content = msg.get('content', {})
                    print(f"\n🎤 唤醒事件")
                    print(f"  角度: {content.get('angle')}°")
                    print(f"  得分: {content.get('score')}")
                    print(f"  波束: {content.get('beam')}")

    except KeyboardInterrupt:
        print("\n\n停止监听")


def demo_with_audio(controller, audio_device):
    """带音频录制的演示"""
    print("\n" + "="*60)
    print("唤醒后录音演示")
    print("="*60)
    print("\n等待唤醒事件...")

    recorder = AudioRecorder(device_index=audio_device)

    try:
        while True:
            msg = controller.read_device_message(timeout=2)
            if msg and msg.get('type') == 'wakeup':
                print("\n✓ 检测到唤醒！开始录音5秒...")

                from datetime import datetime
                filename = f"wakeup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"

                recorder.record(duration=5, output_file=filename)
                print(f"✓ 已保存: {filename}\n")
                print("继续等待唤醒事件...")

    except KeyboardInterrupt:
        print("\n\n停止监听")

    recorder.close()


def main():
    """主程序"""
    print("="*60)
    print("RK3328降噪板 - Mac专用示例")
    print("="*60)

    # 1. 查找串口设备
    serial_port = find_serial_port()
    if not serial_port:
        sys.exit(1)

    # 2. 连接设备
    print(f"\n正在连接到 {serial_port}...")
    controller = RK3328Controller(serial_port)

    if not controller.connect():
        print("\n❌ 连接失败")
        print("\n请检查：")
        print("1. RK3328是否已通电（DC 12V）")
        print("2. TTL串口接线是否正确:")
        print("   RK3328 TX → USB转TTL RX")
        print("   RK3328 RX → USB转TTL TX")
        print("   RK3328 GND → USB转TTL GND")
        sys.exit(1)

    print("\n✓ 设备已连接")

    # 3. 配置初始波束
    print("\n设置波束方向为 0°...")
    controller.manual_wakeup(beam=0)

    # 4. 选择示例
    print("\n" + "="*60)
    print("请选择示例：")
    print("="*60)
    print("1. 基本功能（监听唤醒事件）")
    print("2. 唤醒后录音（需要音频输入）")
    print("3. 退出")

    choice = input("\n请选择 [1-3]: ").strip()

    try:
        if choice == '1':
            demo_basic(controller)

        elif choice == '2':
            audio_device = check_audio_input()
            if audio_device is not None:
                demo_with_audio(controller, audio_device)
            else:
                print("\n⚠️  无法使用音频功能")
                print("\n备选方案：")
                print("1. 使用USB声卡（推荐）")
                print("2. 只使用串口功能（不录音）")

        elif choice == '3':
            pass

        else:
            print("无效选择")

    finally:
        controller.close()
        print("\n再见！")


if __name__ == "__main__":
    main()
