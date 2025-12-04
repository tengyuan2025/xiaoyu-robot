#!/usr/bin/env python3
"""
串口原始数据调试工具
显示所有从 RK3328 接收到的原始数据
"""

import serial
import time
import glob
import sys
import struct


def find_serial_port():
    """查找串口设备"""
    patterns = [
        '/dev/tty.usbserial*',
        '/dev/tty.wchusbserial*',
    ]

    ports = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))

    return ports[0] if ports else None


def parse_message(data):
    """尝试解析消息"""
    if len(data) < 7:
        return None

    if data[0] != 0xA5:
        return None

    user_id = data[1]
    msg_type = data[2]
    msg_len = struct.unpack('<H', data[3:5])[0]
    msg_id = struct.unpack('<H', data[5:7])[0]

    msg_types = {
        0x01: "握手消息",
        0x02: "设备消息",
        0x03: "确认消息",
        0x04: "主控消息"
    }

    result = {
        'sync': f"0x{data[0]:02X}",
        'user_id': user_id,
        'msg_type': f"{msg_types.get(msg_type, '未知')} (0x{msg_type:02X})",
        'msg_len': msg_len,
        'msg_id': msg_id
    }

    # 如果是设备消息，尝试解析 JSON
    if msg_type == 0x02 and len(data) >= 7 + msg_len:
        try:
            json_data = data[7:7+msg_len].decode('utf-8')
            result['json'] = json_data
        except:
            result['json'] = "解析失败"

    return result


def main():
    print("="*70)
    print("RK3328 串口原始数据调试工具")
    print("="*70)

    # 查找串口
    port = find_serial_port()
    if not port:
        print("❌ 未找到串口设备")
        sys.exit(1)

    print(f"\n✓ 找到设备: {port}")
    print(f"✓ 波特率: 115200")

    # 打开串口
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        print("✓ 串口已打开\n")
    except Exception as e:
        print(f"❌ 无法打开串口: {e}")
        sys.exit(1)

    print("="*70)
    print("开始监听串口数据...")
    print("请尝试以下操作：")
    print("  1. 对着麦克风说话（任何词）")
    print("  2. 尝试不同的唤醒词：")
    print("     - '小飞小飞'")
    print("     - '你好小飞'")
    print("     - '讯飞讯飞'")
    print("     - '你好问问'")
    print("  3. 观察下方是否有数据输出")
    print("\n按 Ctrl+C 退出")
    print("="*70)
    print()

    buffer = bytearray()
    msg_count = 0

    try:
        while True:
            # 读取数据
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                buffer.extend(data)

                # 显示原始十六进制数据
                hex_str = ' '.join([f'{b:02X}' for b in data])
                print(f"\n[{time.strftime('%H:%M:%S')}] 接收到 {len(data)} 字节:")
                print(f"  HEX: {hex_str}")

                # 尝试解析
                if len(buffer) >= 7 and buffer[0] == 0xA5:
                    msg_len = struct.unpack('<H', buffer[3:5])[0]
                    total_len = 7 + msg_len + 1  # 头部 + 数据 + 校验

                    if len(buffer) >= total_len:
                        msg_count += 1
                        parsed = parse_message(buffer[:total_len])

                        if parsed:
                            print(f"\n  ✓ 解析消息 #{msg_count}:")
                            print(f"    - 同步头: {parsed['sync']}")
                            print(f"    - 用户ID: {parsed['user_id']}")
                            print(f"    - 消息类型: {parsed['msg_type']}")
                            print(f"    - 数据长度: {parsed['msg_len']}")
                            print(f"    - 消息ID: {parsed['msg_id']}")

                            if 'json' in parsed:
                                print(f"    - JSON数据: {parsed['json']}")

                        # 清空已处理的数据
                        buffer = buffer[total_len:]

                # 清空过大的缓冲区
                if len(buffer) > 1024:
                    buffer.clear()

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print(f"调试结束，共接收到 {msg_count} 条消息")
        print("="*70)

    finally:
        ser.close()
        print("串口已关闭")


if __name__ == "__main__":
    main()
