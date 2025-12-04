#!/usr/bin/env python3
"""
探测 RK3328 设备需要的初始化命令
尝试不同的命令序列来激活设备
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


def calculate_checksum(data):
    return (~sum(data) + 1) & 0xFF


def send_raw_command(ser, msg_type, data_bytes=b''):
    """发送原始命令"""
    packet = bytearray()
    packet.append(0xA5)  # 同步头
    packet.append(0x01)  # 用户ID
    packet.append(msg_type)  # 消息类型
    packet.extend(struct.pack('<H', len(data_bytes)))  # 数据长度
    packet.extend(struct.pack('<H', 1))  # 消息ID
    packet.extend(data_bytes)  # 数据

    checksum = calculate_checksum(packet)
    packet.append(checksum)

    ser.write(packet)
    return packet


def send_json_command(ser, cmd_type, content, msg_id=1):
    """发送 JSON 格式的命令"""
    message = {
        "type": cmd_type,
        "content": content
    }
    json_data = json.dumps(message, ensure_ascii=False).encode('utf-8')

    packet = bytearray()
    packet.append(0xA5)
    packet.append(0x01)
    packet.append(0x04)  # 主控消息
    packet.extend(struct.pack('<H', len(json_data)))
    packet.extend(struct.pack('<H', msg_id))
    packet.extend(json_data)

    checksum = calculate_checksum(packet)
    packet.append(checksum)

    ser.write(packet)
    return packet


def wait_for_response(ser, timeout=2):
    """等待设备响应"""
    start = time.time()
    buffer = bytearray()
    messages = []

    while time.time() - start < timeout:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            buffer.extend(data)

            # 解析消息
            while len(buffer) >= 7 and buffer[0] == 0xA5:
                msg_type = buffer[2]
                msg_len = struct.unpack('<H', buffer[3:5])[0]
                total_len = 7 + msg_len + 1

                if len(buffer) >= total_len:
                    msg_data = buffer[:total_len]
                    messages.append({
                        'type': msg_type,
                        'data': msg_data,
                        'len': msg_len
                    })
                    buffer = buffer[total_len:]
                else:
                    break

        time.sleep(0.01)

    return messages


def main():
    print("="*70)
    print("RK3328 设备探测工具 - 尝试激活唤醒功能")
    print("="*70)

    port = find_serial_port()
    if not port:
        print("❌ 未找到串口")
        sys.exit(1)

    print(f"\n✓ 串口: {port}\n")

    ser = serial.Serial(
        port=port,
        baudrate=115200,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1
    )

    # 清空接收缓冲
    ser.reset_input_buffer()
    time.sleep(0.5)

    print("开始探测...\n")
    print("="*70)

    # 测试不同的命令
    tests = [
        {
            'name': '1. 发送空主控消息',
            'func': lambda: send_raw_command(ser, 0x04, b''),
        },
        {
            'name': '2. 发送手动唤醒 (beam=0)',
            'func': lambda: send_json_command(ser, "manual_wakeup", {"beam": 0}),
        },
        {
            'name': '3. 发送手动唤醒 (beam=1)',
            'func': lambda: send_json_command(ser, "manual_wakeup", {"beam": 1}),
        },
        {
            'name': '4. 发送麦克风阵列配置 (环形6麦)',
            'func': lambda: send_json_command(ser, "switch_mic", {"mic_type": 0}),
        },
        {
            'name': '5. 发送获取版本信息命令',
            'func': lambda: send_json_command(ser, "get_version", {}),
        },
        {
            'name': '6. 发送获取状态命令',
            'func': lambda: send_json_command(ser, "get_status", {}),
        },
        {
            'name': '7. 发送启用唤醒命令',
            'func': lambda: send_json_command(ser, "enable_wakeup", {"enable": 1}),
        },
        {
            'name': '8. 发送启动命令',
            'func': lambda: send_json_command(ser, "start", {}),
        },
        {
            'name': '9. 发送初始化命令',
            'func': lambda: send_json_command(ser, "init", {}),
        },
        {
            'name': '10. 发送设置参数命令',
            'func': lambda: send_json_command(ser, "set_params", {"sample_rate": 16000}),
        },
    ]

    for test in tests:
        print(f"\n{test['name']}")
        print("-"*70)

        # 清空之前的数据
        ser.reset_input_buffer()
        time.sleep(0.1)

        # 发送命令
        packet = test['func']()
        print(f"发送: {' '.join([f'{b:02X}' for b in packet[:20]])}{'...' if len(packet) > 20 else ''}")

        # 等待响应
        responses = wait_for_response(ser, timeout=1)

        if responses:
            print(f"\n收到 {len(responses)} 条响应:")
            for i, msg in enumerate(responses):
                msg_types = {0x01: "握手", 0x02: "设备", 0x03: "确认", 0x04: "主控", 0xFF: "未知"}
                type_name = msg_types.get(msg['type'], f"0x{msg['type']:02X}")
                print(f"  [{i+1}] 类型: {type_name}, 长度: {msg['len']} 字节")

                # 如果有 JSON 数据，尝试解析
                if msg['type'] in [0x02, 0x04] and msg['len'] > 0:
                    try:
                        json_str = msg['data'][7:7+msg['len']].decode('utf-8')
                        print(f"      JSON: {json_str}")
                    except:
                        pass
        else:
            print("无响应")

        time.sleep(0.5)

    # 持续监听模式
    print("\n" + "="*70)
    print("测试完成！现在持续监听 30 秒...")
    print("请对着麦克风说话或制造声音")
    print("="*70)

    start = time.time()
    device_msg_count = 0

    try:
        while time.time() - start < 30:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)

                # 简单解析
                i = 0
                while i < len(data):
                    if data[i] == 0xA5 and i + 2 < len(data):
                        msg_type = data[i+2]

                        if msg_type == 0x02:  # 设备消息
                            device_msg_count += 1
                            print(f"\n🎉 收到设备消息 #{device_msg_count}！")
                            print(f"原始数据: {' '.join([f'{b:02X}' for b in data[i:min(i+50, len(data))]])}")

                        i += 1
                    else:
                        i += 1

            time.sleep(0.01)

    except KeyboardInterrupt:
        pass

    print(f"\n\n监听结束，共收到 {device_msg_count} 条设备消息")

    if device_msg_count == 0:
        print("\n" + "="*70)
        print("⚠️  建议：")
        print("="*70)
        print("1. 设备可能需要通过官方 Windows 工具先配置一次")
        print("2. 或者固件版本不兼容，需要更新固件")
        print("3. 检查板子上是否有物理按键需要按下")
        print("4. 尝试联系厂商获取最新的协议文档")

    ser.close()


if __name__ == "__main__":
    main()
