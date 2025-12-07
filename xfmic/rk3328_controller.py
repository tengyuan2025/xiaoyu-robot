#!/usr/bin/env python3
"""
RK3328降噪板串口控制脚本
基于官方协议文档实现
支持Linux环境
"""

import serial
import json
import struct
import time
from typing import Dict, Any, Optional


class RK3328Controller:
    """RK3328降噪板串口控制器"""

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
        """初始化串口控制器

        Args:
            port: 串口设备路径，Linux下通常是/dev/ttyUSB0
            baudrate: 波特率，默认115200
        """
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.msg_id = 0

    def connect(self) -> bool:
        """建立串口连接并完成握手

        Returns:
            bool: 连接成功返回True
        """
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            print(f"✓ 串口已连接: {self.port}")

            # 等待握手
            if self.wait_handshake():
                print("✓ 握手成功，设备已就绪")
                return True
            else:
                print("✗ 握手失败")
                return False

        except Exception as e:
            print(f"✗ 串口连接失败: {e}")
            return False

    def wait_handshake(self, timeout=10) -> bool:
        """等待设备握手

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 握手成功返回True
        """
        print("等待设备握手...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)

                # 检查是否是握手消息
                if len(data) >= 7:
                    if data[0] == self.SYNC_HEAD and data[2] == self.MSG_TYPE_HANDSHAKE:
                        # 发送确认消息
                        msg_id_bytes = data[5:7]
                        self.send_confirm(msg_id_bytes)
                        return True

            time.sleep(0.1)

        return False

    def calculate_checksum(self, data: bytearray) -> int:
        """计算校验码

        校验码 = ~sum(所有字节) + 1

        Args:
            data: 待校验的数据

        Returns:
            int: 校验码
        """
        return (~sum(data) + 1) & 0xFF

    def send_confirm(self, msg_id_bytes: bytes):
        """发送确认消息

        Args:
            msg_id_bytes: 原消息的ID（2字节）
        """
        packet = bytearray()
        packet.append(self.SYNC_HEAD)           # 同步头
        packet.append(self.USER_ID)             # 用户ID
        packet.append(self.MSG_TYPE_CONFIRM)    # 消息类型：确认
        packet.extend(struct.pack('<H', 0))     # 数据长度为0
        packet.extend(msg_id_bytes)             # 使用原消息ID

        checksum = self.calculate_checksum(packet)
        packet.append(checksum)

        self.ser.write(packet)

    def send_command(self, cmd_type: str, content: Dict[str, Any]) -> bool:
        """发送主控命令

        Args:
            cmd_type: 命令类型
            content: 命令内容

        Returns:
            bool: 命令发送成功且收到确认返回True
        """
        # 构造JSON消息
        message = {
            "type": cmd_type,
            "content": content
        }
        json_data = json.dumps(message, ensure_ascii=False).encode('utf-8')

        # 构造协议包
        packet = bytearray()
        packet.append(self.SYNC_HEAD)           # 同步头
        packet.append(self.USER_ID)             # 用户ID
        packet.append(self.MSG_TYPE_MASTER)     # 消息类型：主控消息

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
        print(f"→ 已发送命令: {cmd_type}")

        # 等待确认
        time.sleep(0.1)
        return self.wait_confirm()

    def wait_confirm(self, timeout=1) -> bool:
        """等待确认消息

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 收到确认返回True
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                if len(data) >= 7 and data[2] == self.MSG_TYPE_CONFIRM:
                    print("← 收到确认")
                    return True
            time.sleep(0.01)
        return False

    def manual_wakeup(self, beam: int = 1) -> bool:
        """手动唤醒，指定波束方向

        Args:
            beam: 波束序号
                环形六麦: 0-5 (0°, 60°, 120°, 180°, 240°, 300°)
                线性四麦: 0-2 (0°, 90°, 180°)
                线性六麦: 0-5

        Returns:
            bool: 命令发送成功返回True
        """
        return self.send_command("manual_wakeup", {"beam": beam})

    def switch_wakeup_word(self, keyword: str, threshold: int = 900) -> bool:
        """更换唤醒词（浅定制）

        Args:
            keyword: 唤醒词拼音，如 "xiao3 fei1 xiao3 fei1"
            threshold: 唤醒阈值，默认900

        Returns:
            bool: 命令发送成功返回True
        """
        return self.send_command("wakeup_keywords", {
            "keyword": keyword,
            "threshold": str(threshold)
        })

    def switch_mic_array(self, mic_type: int) -> bool:
        """切换麦克风阵列类型

        Args:
            mic_type: 0=环形6麦, 1=线性4麦, 2=线性6麦

        Returns:
            bool: 命令发送成功返回True
        """
        return self.send_command("switch_mic", {"mic_type": mic_type})

    def read_device_message(self, timeout=1) -> Optional[Dict]:
        """读取设备上报消息（如唤醒事件）

        Args:
            timeout: 超时时间（秒）

        Returns:
            dict: 设备消息，超时返回None
        """
        start_time = time.time()
        buffer = bytearray()

        while time.time() - start_time < timeout:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                buffer.extend(data)

                # 调试：显示原始数据（已禁用）
                # if len(data) > 0:
                #     hex_str = ' '.join([f'{b:02X}' for b in data[:20]])
                #     print(f"[串口] 收到 {len(data)} 字节: {hex_str}...")

                # 查找完整的消息包
                if len(buffer) >= 7:
                    # 调试：显示buffer状态（已禁用）
                    # print(f"[Buffer] 长度:{len(buffer)}, 头:{buffer[0]:02X}, 类型:{buffer[2]:02X}")

                    # 检查消息头是否正确
                    if buffer[0] != self.SYNC_HEAD:
                        # 尝试查找正确的同步头
                        sync_pos = buffer.find(self.SYNC_HEAD)
                        if sync_pos > 0:
                            # print(f"[警告] 丢弃 {sync_pos} 字节垃圾数据，重新同步")
                            buffer = buffer[sync_pos:]
                        else:
                            # print(f"[警告] 未找到同步头，清空buffer")
                            buffer.clear()
                        continue

                    # 唤醒事件是0x04类型，也接受0x02类型的设备消息
                    if buffer[2] in [self.MSG_TYPE_DEVICE, self.MSG_TYPE_MASTER]:
                        msg_len = struct.unpack('<H', buffer[3:5])[0]
                        total_len = 7 + msg_len + 1  # 头+数据+校验

                        if len(buffer) >= total_len:
                            try:
                                # 提取JSON数据
                                json_data = buffer[7:7+msg_len].decode('utf-8')
                                msg = json.loads(json_data)

                                # 发送确认（跳过0x03和0xFF避免ACK循环）
                                if buffer[2] not in [self.MSG_TYPE_CONFIRM, 0xFF]:
                                    msg_id = buffer[5:7]
                                    self.send_confirm(msg_id)

                                # 清空已处理的消息
                                buffer = buffer[total_len:]

                                return msg
                            except Exception as e:
                                print(f"解析设备消息失败: {e}")
                                buffer.clear()
                    else:
                        # 不是我们需要的消息类型，跳过这条消息
                        if buffer[2] == self.MSG_TYPE_CONFIRM or buffer[2] == 0xFF:
                            # 确认消息，跳过
                            msg_len = struct.unpack('<H', buffer[3:5])[0]
                            total_len = 7 + msg_len + 1
                            if len(buffer) >= total_len:
                                # print(f"[跳过] 确认消息 (类型:{buffer[2]:02X})")
                                buffer = buffer[total_len:]
                        else:
                            # print(f"[跳过] 未知消息类型: {buffer[2]:02X}")
                            buffer = buffer[1:]  # 跳过一个字节，继续搜索

            time.sleep(0.01)

        return None

    def close(self):
        """关闭串口"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("串口已关闭")


# 命令行测试
if __name__ == "__main__":
    import sys

    # 从命令行参数获取串口
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'

    controller = RK3328Controller(port)

    if controller.connect():
        print("\n=== 设备控制菜单 ===")
        print("1. 手动唤醒（0°方向）")
        print("2. 切换波束方向")
        print("3. 监听唤醒事件")
        print("4. 退出")

        while True:
            choice = input("\n请选择操作 [1-4]: ").strip()

            if choice == '1':
                controller.manual_wakeup(beam=0)
                print("已发送手动唤醒命令")

            elif choice == '2':
                beam = int(input("请输入波束编号 (0-5): "))
                controller.manual_wakeup(beam=beam)

            elif choice == '3':
                print("等待唤醒事件（Ctrl+C退出）...")
                try:
                    while True:
                        msg = controller.read_device_message(timeout=2)
                        if msg:
                            print(f"\n← 收到设备消息: {json.dumps(msg, ensure_ascii=False, indent=2)}")
                            if msg.get('type') == 'wakeup':
                                content = msg.get('content', {})
                                print(f"\n[唤醒事件]")
                                print(f"  角度: {content.get('angle')}°")
                                print(f"  得分: {content.get('score')}")
                                print(f"  波束: {content.get('beam')}")
                except KeyboardInterrupt:
                    print("\n停止监听")

            elif choice == '4':
                break

            else:
                print("无效选择")

        controller.close()
