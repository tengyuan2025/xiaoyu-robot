#!/usr/bin/env python3
"""
最简单的串口监听器 - 100% 模拟 screen 命令
不做任何解析，不发送任何数据，只显示接收到的原始内容
"""

import serial
import sys

# 串口配置
port = sys.argv[1] if len(sys.argv) > 1 else '/dev/tty.usbserial-2130'
baudrate = 115200

print(f"监听串口: {port}")
print(f"波特率: {baudrate}")
print("-" * 60)
print("开始监听... (按 Ctrl+C 退出)")
print("-" * 60)
print()

# 打开串口 - 完全只读
ser = serial.Serial(
    port=port,
    baudrate=baudrate,
    timeout=1
)

# 清空缓冲区
ser.reset_input_buffer()

try:
    while True:
        # 只要有数据就读取并立即显示
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)

            # 显示HEX
            hex_str = ' '.join(f'{b:02X}' for b in data)
            print(f"HEX: {hex_str}")

            # 尝试显示文本（如果是JSON）
            try:
                text = data.decode('utf-8', errors='ignore')
                if '{' in text:
                    print(f"TXT: {text.strip()}")
            except:
                pass

            print()

except KeyboardInterrupt:
    print("\n监听结束")
    ser.close()
