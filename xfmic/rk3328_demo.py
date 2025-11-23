#!/usr/bin/env python3
"""
RK3328降噪板完整示例
演示串口控制 + 音频采集的集成使用
"""

import threading
import queue
import time
import wave
import numpy as np
from datetime import datetime
from rk3328_controller import RK3328Controller
from audio_recorder import AudioRecorder


class RK3328Demo:
    """RK3328完整示例程序"""

    def __init__(self, serial_port='/dev/ttyUSB0', audio_device=None):
        """初始化

        Args:
            serial_port: 串口设备路径
            audio_device: 音频设备索引
        """
        self.controller = RK3328Controller(serial_port)
        self.recorder = AudioRecorder(
            device_index=audio_device,
            rate=16000,
            channels=1,
            chunk=1024
        )

        self.audio_queue = queue.Queue(maxsize=100)
        self.running = False
        self.wakeup_detected = False

    def start(self):
        """启动系统"""
        print("="*60)
        print("RK3328降噪板示例程序")
        print("="*60)

        # 连接串口
        print("\n[1/3] 连接串口...")
        if not self.controller.connect():
            print("✗ 串口连接失败，请检查设备")
            return False

        # 设置初始波束方向
        print("\n[2/3] 配置设备...")
        self.controller.manual_wakeup(beam=0)  # 设置为0°方向
        print("✓ 已设置波束方向: 0°")

        # 启动线程
        print("\n[3/3] 启动音频采集...")
        self.running = True

        # 音频采集线程
        self.audio_thread = threading.Thread(
            target=self._audio_thread,
            daemon=True
        )
        self.audio_thread.start()

        # 串口监听线程
        self.serial_thread = threading.Thread(
            target=self._serial_thread,
            daemon=True
        )
        self.serial_thread.start()

        print("\n✓ 系统已启动")
        print("="*60)
        return True

    def _audio_thread(self):
        """音频采集线程"""
        def audio_callback(data, frame_count):
            # 将音频数据放入队列
            try:
                self.audio_queue.put_nowait({
                    'data': data,
                    'timestamp': time.time()
                })
            except queue.Full:
                pass  # 队列满时丢弃

        # 开始流式录音
        try:
            self.recorder.record_stream(audio_callback)
        except Exception as e:
            print(f"音频采集错误: {e}")
            self.running = False

    def _serial_thread(self):
        """串口监听线程"""
        while self.running:
            msg = self.controller.read_device_message(timeout=0.5)
            if msg:
                self._handle_device_message(msg)

    def _handle_device_message(self, msg):
        """处理设备消息"""
        msg_type = msg.get('type')

        if msg_type == 'wakeup':
            self.wakeup_detected = True
            content = msg.get('content', {})

            print("\n" + "="*60)
            print("🎤 检测到唤醒事件")
            print("="*60)
            print(f"  唤醒角度: {content.get('angle')}°")
            print(f"  唤醒得分: {content.get('score')}")
            print(f"  所属波束: {content.get('beam')}")
            print(f"  唤醒词: {content.get('keyword', 'N/A')}")
            print("="*60)

    def demo_basic(self):
        """示例1: 基本功能演示"""
        print("\n【示例1: 基本功能】")
        print("监听唤醒事件和音频数据...")
        print("按 Ctrl+C 停止\n")

        try:
            frame_count = 0
            while True:
                # 获取音频数据
                try:
                    audio_item = self.audio_queue.get(timeout=0.1)
                    audio_data = audio_item['data']

                    # 计算音量
                    volume = np.abs(audio_data).mean()

                    frame_count += 1
                    if frame_count % 10 == 0:  # 每10帧显示一次
                        print(f'\r音频: 音量={int(volume):4d} 队列={self.audio_queue.qsize():2d}', end='')

                except queue.Empty:
                    pass

                time.sleep(0.01)

        except KeyboardInterrupt:
            print("\n停止监听")

    def demo_save_on_wakeup(self, save_duration=5):
        """示例2: 唤醒后保存音频

        Args:
            save_duration: 唤醒后保存多少秒的音频
        """
        print(f"\n【示例2: 唤醒后保存音频】")
        print(f"唤醒后将保存 {save_duration} 秒音频")
        print("按 Ctrl+C 停止\n")

        try:
            while True:
                # 检查是否唤醒
                if self.wakeup_detected:
                    self.wakeup_detected = False

                    # 开始保存音频
                    print("\n开始保存音频...")
                    frames = []
                    save_frames = int(16000 / 1024 * save_duration)

                    for i in range(save_frames):
                        try:
                            audio_item = self.audio_queue.get(timeout=1)
                            frames.append(audio_item['data'].tobytes())

                            progress = (i + 1) / save_frames * 100
                            print(f'\r保存进度: {progress:.1f}%', end='')
                        except queue.Empty:
                            break

                    # 保存为WAV文件
                    filename = f"wakeup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                    self._save_audio(filename, frames)
                    print(f"\n✓ 已保存: {filename}\n")

                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n停止监听")

    def demo_beam_following(self):
        """示例3: 波束跟随
        根据唤醒角度自动调整波束方向
        """
        print("\n【示例3: 波束跟随】")
        print("系统将根据唤醒角度自动调整波束方向")
        print("按 Ctrl+C 停止\n")

        # 角度到波束的映射（环形六麦）
        def angle_to_beam(angle):
            """将角度转换为最近的波束编号"""
            beams = [0, 60, 120, 180, 240, 300]
            distances = [abs(angle - b) for b in beams]
            return distances.index(min(distances))

        try:
            while True:
                msg = self.controller.read_device_message(timeout=1)
                if msg and msg.get('type') == 'wakeup':
                    content = msg.get('content', {})
                    angle = content.get('angle', 0)

                    # 计算最佳波束
                    beam = angle_to_beam(angle)

                    print(f"\n唤醒角度: {angle}° → 切换到波束 {beam}")
                    self.controller.manual_wakeup(beam=beam)

        except KeyboardInterrupt:
            print("\n停止监听")

    def _save_audio(self, filename, frames):
        """保存音频文件"""
        wf = wave.open(filename, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16bit = 2 bytes
        wf.setframerate(16000)
        wf.writeframes(b''.join(frames))
        wf.close()

    def stop(self):
        """停止系统"""
        print("\n正在停止...")
        self.running = False

        # 等待线程结束
        if hasattr(self, 'audio_thread'):
            self.audio_thread.join(timeout=2)
        if hasattr(self, 'serial_thread'):
            self.serial_thread.join(timeout=2)

        self.controller.close()
        self.recorder.close()
        print("✓ 已停止")


def main():
    """主程序"""
    import sys

    # 解析命令行参数
    serial_port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'
    audio_device = int(sys.argv[2]) if len(sys.argv) > 2 else None

    # 创建示例程序
    demo = RK3328Demo(serial_port, audio_device)

    # 如果没有指定音频设备，先列出设备
    if audio_device is None:
        print("未指定音频设备，列出可用设备：")
        demo.recorder.list_devices()
        device_input = input("\n请输入音频设备编号（留空使用默认）: ").strip()
        if device_input:
            demo.recorder.device_index = int(device_input)

    # 启动系统
    if not demo.start():
        return

    # 选择示例
    print("\n请选择示例：")
    print("1. 基本功能（监听唤醒和音频）")
    print("2. 唤醒后保存音频")
    print("3. 波束跟随")
    print("4. 退出")

    choice = input("\n请选择 [1-4]: ").strip()

    try:
        if choice == '1':
            demo.demo_basic()
        elif choice == '2':
            duration = input("唤醒后保存多少秒音频？（默认5）: ").strip()
            duration = int(duration) if duration else 5
            demo.demo_save_on_wakeup(duration)
        elif choice == '3':
            demo.demo_beam_following()
        elif choice == '4':
            pass
        else:
            print("无效选择")

    finally:
        demo.stop()


if __name__ == "__main__":
    main()
