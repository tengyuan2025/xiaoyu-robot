#!/usr/bin/env python3
"""
纯监听模式 - 完全模拟 screen 命令的行为
只接收数据，不发送任何内容（包括握手确认）
"""

import serial
import time
import glob
import sys
import json
import struct


def find_serial_port():
    """查找串口"""
    ports = glob.glob('/dev/tty.usbserial*')
    if not ports:
        ports = glob.glob('/dev/cu.usbserial*')
    if not ports:
        ports = glob.glob('/dev/ttyUSB*')
    if not ports:
        print("❌ 未找到串口设备")
        sys.exit(1)
    return ports[0]


def parse_message(data):
    """尝试解析协议消息"""
    if len(data) < 7 or data[0] != 0xA5:
        return None

    msg_types = {
        0x01: "握手",
        0x02: "设备消息",
        0x03: "确认",
        0x04: "主控",
        0xFF: "未知0xFF"
    }

    try:
        msg_type = data[2]
        msg_len = struct.unpack('<H', data[3:5])[0]
        msg_id = struct.unpack('<H', data[5:7])[0]

        result = {
            'type': msg_types.get(msg_type, f"0x{msg_type:02X}"),
            'type_code': msg_type,
            'msg_len': msg_len,
            'msg_id': msg_id
        }

        # 解析 JSON
        if msg_len > 0 and len(data) >= 7 + msg_len:
            if msg_type in [0x02, 0x04]:  # 设备消息或主控消息
                try:
                    json_str = data[7:7+msg_len].decode('utf-8')
                    result['json'] = json.loads(json_str)
                except:
                    pass

        return result
    except:
        return None


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_serial_port()

    print("="*70)
    print("纯监听模式 - 模拟 screen 命令")
    print("="*70)
    print(f"串口: {port}")
    print(f"波特率: 115200")
    print()
    print("⚠️  重要：本程序不发送任何数据，只被动监听")
    print()
    print("现在请对着麦克风说：小飞小飞 或 小微小微")
    print("按 Ctrl+C 退出")
    print("="*70)
    print()

    try:
        # 打开串口 - 只读模式
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )

        print("✓ 串口已打开（纯监听模式）\n")

        # 清空输入缓冲
        ser.reset_input_buffer()

        buffer = bytearray()
        packet_count = 0
        wakeup_count = 0

        while True:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                buffer.extend(data)

                # 显示原始数据
                timestamp = time.strftime("%H:%M:%S")
                print(f"\n[{timestamp}] 接收 {len(data)} 字节:")
                print(f"  HEX: {' '.join([f'{b:02X}' for b in data[:50]])}{('...' if len(data) > 50 else '')}")

                # 尝试查找并解析完整消息
                while len(buffer) >= 7 and buffer[0] == 0xA5:
                    msg_type = buffer[2]
                    msg_len = struct.unpack('<H', buffer[3:5])[0]
                    total_len = 7 + msg_len + 1

                    if len(buffer) >= total_len:
                        packet_count += 1
                        msg_data = buffer[:total_len]

                        # 解析消息
                        parsed = parse_message(msg_data)

                        if parsed:
                            print(f"\n  📦 消息 #{packet_count}:")
                            print(f"     类型: {parsed['type']}")
                            print(f"     消息ID: {parsed['msg_id']}")
                            print(f"     数据长度: {parsed['msg_len']} 字节")

                            # 如果有 JSON
                            if 'json' in parsed:
                                json_str = json.dumps(parsed['json'], ensure_ascii=False, indent=6)
                                print(f"     JSON 数据:")
                                for line in json_str.split('\n'):
                                    print(f"     {line}")

                                # 检查是否是唤醒事件
                                if parsed['json'].get('type') == 'wakeup':
                                    wakeup_count += 1
                                    content = parsed['json'].get('content', {})

                                    print(f"\n     🎉 唤醒事件 #{wakeup_count}!")
                                    print(f"     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                                    print(f"     🎯 声源角度: {content.get('angle')}°")
                                    print(f"     📊 置信得分: {content.get('score')}")
                                    print(f"     📡 波束编号: {content.get('beam')}")
                                    if 'keyword' in content:
                                        print(f"     🎤 唤醒词: {content.get('keyword')}")
                                    print(f"     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

                        # 移除已处理的消息
                        buffer = buffer[total_len:]
                    else:
                        # 数据不完整，等待更多数据
                        break

                # 清空过大的缓冲区
                if len(buffer) > 1024:
                    print("  ⚠️  缓冲区过大，清空")
                    buffer.clear()

            time.sleep(0.01)

    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print("监听结束")
        print(f"{'='*70}")
        print(f"总消息数: {packet_count}")
        print(f"唤醒次数: {wakeup_count}")
        print(f"{'='*70}")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("\n串口已关闭")


if __name__ == "__main__":
    main()
