#!/usr/bin/env python3
"""
最底层的串口原始数据监听器
不做任何处理，只显示接收到的每一个字节
"""

import serial
import glob
import sys
import time

def find_serial_port():
    """自动查找串口"""
    ports = glob.glob('/dev/tty.usbserial*')
    if not ports:
        ports = glob.glob('/dev/cu.usbserial*')
    if not ports:
        ports = glob.glob('/dev/ttyUSB*')
    if not ports:
        print("❌ 未找到串口设备")
        sys.exit(1)
    return ports[0]

# 配置
port = sys.argv[1] if len(sys.argv) > 1 else find_serial_port()
baudrate = 115200

print("="*70)
print("原始串口数据监听器")
print("="*70)
print(f"串口: {port}")
print(f"波特率: {baudrate}")
print("="*70)
print()

try:
    # 打开串口
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1
    )

    print(f"✓ 串口已打开")
    print()
    print("开始接收数据...")
    print("按 Ctrl+C 退出")
    print("="*70)
    print()

    # 清空缓冲区
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    packet_count = 0
    total_bytes = 0

    while True:
        if ser.in_waiting > 0:
            # 读取所有可用数据
            data = ser.read(ser.in_waiting)
            packet_count += 1
            total_bytes += len(data)

            timestamp = time.strftime("%H:%M:%S")

            print(f"\n[数据包 #{packet_count}] {timestamp} - {len(data)} 字节")
            print("-"*70)

            # HEX格式 - 每行16字节
            hex_str = data.hex()
            print("HEX:")
            for i in range(0, len(hex_str), 32):  # 32个字符 = 16字节
                line = hex_str[i:i+32]
                # 每2个字符加一个空格
                formatted = ' '.join(line[j:j+2] for j in range(0, len(line), 2))
                print(f"  {formatted}")

            # 尝试解码为文本
            print("\n文本 (UTF-8, 忽略错误):")
            try:
                text = data.decode('utf-8', errors='replace')
                # 显示可打印字符
                printable_text = ''.join(c if c.isprintable() or c in '\n\r\t' else '·' for c in text)
                print(f"  {printable_text[:200]}")
            except:
                print("  [无法解码]")

            # 检测特征
            print("\n特征:")
            features = []

            # 检查同步头
            if data[0] == 0xA5:
                features.append("✓ 同步头 0xA5")

            # 检查是否包含JSON
            if b'{' in data and b'}' in data:
                features.append("✓ 包含JSON数据")

            # 检查是否包含特定关键字
            if b'wakeup' in data:
                features.append("🎤 包含 'wakeup' 关键字")
            if b'keyword' in data:
                features.append("🎤 包含 'keyword' 关键字")
            if b'aiui' in data:
                features.append("✓ 包含 'aiui' 关键字")
            if b'angle' in data:
                features.append("📐 包含 'angle' 关键字")

            if features:
                for f in features:
                    print(f"  {f}")
            else:
                print("  [普通数据包]")

            print("-"*70)
            print(f"累计: {packet_count} 个包, {total_bytes} 字节")

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\n\n" + "="*70)
    print("监听已停止")
    print(f"总共接收: {packet_count} 个数据包, {total_bytes} 字节")
    print("="*70)

except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("串口已关闭")
