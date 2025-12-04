#!/usr/bin/env python3
"""
显示所有原始串口数据 - 完整的十六进制dump
"""

import serial
import struct
import time
import glob
import sys
import json


def find_serial_port():
    patterns = ['/dev/tty.usbserial*', '/dev/tty.wchusbserial*']
    ports = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))
    return ports[0] if ports else None


def hex_dump(data, prefix=""):
    """格式化显示十六进制数据"""
    hex_str = ' '.join([f'{b:02X}' for b in data])

    # 每16字节一行
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join([f'{b:02X}' for b in chunk])
        ascii_part = ''.join([chr(b) if 32 <= b < 127 else '.' for b in chunk])
        lines.append(f"{prefix}{i:04X}  {hex_part:<48}  {ascii_part}")

    return '\n'.join(lines)


def calculate_checksum(data):
    return (~sum(data) + 1) & 0xFF


def parse_message(data):
    """解析消息"""
    if len(data) < 7:
        return None

    if data[0] != 0xA5:
        return None

    msg_types = {
        0x01: "握手",
        0x02: "设备",
        0x03: "确认",
        0x04: "主控"
    }

    user_id = data[1]
    msg_type = data[2]
    msg_len = struct.unpack('<H', data[3:5])[0]
    msg_id = struct.unpack('<H', data[5:7])[0]

    result = {
        'type': msg_types.get(msg_type, f"未知(0x{msg_type:02X})"),
        'type_code': msg_type,
        'user_id': user_id,
        'msg_len': msg_len,
        'msg_id': msg_id
    }

    # 解析数据
    if len(data) >= 7 + msg_len:
        msg_data = data[7:7+msg_len]
        result['data'] = msg_data

        # 如果是JSON数据，尝试解析
        if msg_type in [0x02, 0x04]:  # 设备消息或主控消息
            try:
                json_str = msg_data.decode('utf-8')
                result['json'] = json.loads(json_str)
            except:
                pass

        # 校验码
        if len(data) >= 7 + msg_len + 1:
            result['checksum'] = data[7+msg_len]

            # 验证校验码
            calc_checksum = calculate_checksum(data[:7+msg_len])
            result['checksum_valid'] = (result['checksum'] == calc_checksum)

    return result


def send_confirm(ser, msg_id_bytes):
    """发送确认消息"""
    packet = bytearray()
    packet.append(0xA5)
    packet.append(0x01)
    packet.append(0x03)
    packet.extend(struct.pack('<H', 0))
    packet.extend(msg_id_bytes)

    checksum = calculate_checksum(packet)
    packet.append(checksum)

    ser.write(packet)
    return packet


def send_manual_wakeup(ser, beam=0):
    """发送手动唤醒命令"""
    message = {
        "type": "manual_wakeup",
        "content": {"beam": beam}
    }
    json_data = json.dumps(message, ensure_ascii=False).encode('utf-8')

    packet = bytearray()
    packet.append(0xA5)
    packet.append(0x01)
    packet.append(0x04)
    packet.extend(struct.pack('<H', len(json_data)))
    packet.extend(struct.pack('<H', 1))
    packet.extend(json_data)

    checksum = calculate_checksum(packet)
    packet.append(checksum)

    ser.write(packet)
    return packet


def main():
    print("="*70)
    print("原始串口数据监控 - 完整十六进制dump")
    print("="*70)

    port = find_serial_port()
    if not port:
        print("❌ 未找到串口")
        sys.exit(1)

    print(f"\n✓ 串口: {port}")
    print(f"✓ 波特率: 115200")

    # 打开串口
    ser = serial.Serial(
        port=port,
        baudrate=115200,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1
    )

    print(f"✓ 串口已打开\n")
    print("="*70)
    print("开始监控（按 Ctrl+C 退出）")
    print("="*70)
    print()

    buffer = bytearray()
    packet_count = 0
    handshake_done = False
    init_sent = False

    try:
        while True:
            # 接收数据
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                buffer.extend(data)

                # 显示接收的原始数据
                print(f"\n{'━'*70}")
                print(f"⬇️  接收 [{time.strftime('%H:%M:%S.%f')[:-3]}] ({len(data)} 字节)")
                print(f"{'━'*70}")
                print(hex_dump(data, "  "))

                # 尝试解析消息
                if len(buffer) >= 7 and buffer[0] == 0xA5:
                    msg_len = struct.unpack('<H', buffer[3:5])[0]
                    total_len = 7 + msg_len + 1

                    if len(buffer) >= total_len:
                        packet_count += 1
                        msg_data = buffer[:total_len]

                        # 解析消息
                        parsed = parse_message(msg_data)

                        if parsed:
                            print(f"\n📦 消息 #{packet_count} 解析:")
                            print(f"  - 类型: {parsed['type']}")
                            print(f"  - 用户ID: {parsed['user_id']}")
                            print(f"  - 消息ID: {parsed['msg_id']}")
                            print(f"  - 数据长度: {parsed['msg_len']} 字节")

                            if parsed['msg_len'] > 0 and 'data' in parsed:
                                print(f"  - 数据: {' '.join([f'{b:02X}' for b in parsed['data']])}")

                            if 'json' in parsed:
                                print(f"  - JSON: {json.dumps(parsed['json'], ensure_ascii=False)}")

                            if 'checksum' in parsed:
                                status = "✓" if parsed['checksum_valid'] else "✗"
                                print(f"  - 校验码: 0x{parsed['checksum']:02X} {status}")

                            # 自动响应
                            if parsed['type_code'] == 0x01:  # 握手
                                print(f"\n  → 自动发送确认消息")
                                msg_id_bytes = buffer[5:7]
                                confirm_packet = send_confirm(ser, msg_id_bytes)

                                print(f"\n{'━'*70}")
                                print(f"⬆️  发送 [{time.strftime('%H:%M:%S.%f')[:-3]}] ({len(confirm_packet)} 字节)")
                                print(f"{'━'*70}")
                                print(hex_dump(confirm_packet, "  "))

                                handshake_done = True

                            elif parsed['type_code'] == 0x02:  # 设备消息
                                print(f"\n  🎉 收到设备消息！")
                                print(f"\n  → 自动发送确认消息")
                                msg_id_bytes = buffer[5:7]
                                confirm_packet = send_confirm(ser, msg_id_bytes)

                                print(f"\n{'━'*70}")
                                print(f"⬆️  发送 [{time.strftime('%H:%M:%S.%f')[:-3]}] ({len(confirm_packet)} 字节)")
                                print(f"{'━'*70}")
                                print(hex_dump(confirm_packet, "  "))

                            elif parsed['type_code'] == 0x03:  # 确认消息
                                print(f"\n  ✓ 收到对我们命令的确认")

                        # 清空已处理数据
                        buffer = buffer[total_len:]

                # 握手成功后发送初始化
                if handshake_done and not init_sent:
                    time.sleep(1)
                    print(f"\n{'='*70}")
                    print(f"握手完成！发送初始化命令...")
                    print(f"{'='*70}")

                    init_packet = send_manual_wakeup(ser, beam=0)

                    print(f"\n{'━'*70}")
                    print(f"⬆️  发送 [{time.strftime('%H:%M:%S.%f')[:-3]}] ({len(init_packet)} 字节)")
                    print(f"{'━'*70}")
                    print(hex_dump(init_packet, "  "))

                    # 解析发送的命令
                    parsed = parse_message(init_packet)
                    if parsed and 'json' in parsed:
                        print(f"\n📤 发送命令: {json.dumps(parsed['json'], ensure_ascii=False)}")

                    init_sent = True
                    print(f"\n{'='*70}")
                    print(f"🎤 现在请对着麦克风说话或制造声音")
                    print(f"{'='*70}\n")

            time.sleep(0.01)

    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print(f"监控结束，共接收 {packet_count} 条消息")
        print(f"{'='*70}")

    finally:
        ser.close()


if __name__ == "__main__":
    main()
