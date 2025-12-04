#!/usr/bin/env python3
"""
分析 0xFF 消息的具体含义
"""

import struct

# 从日志中提取的 0xFF 消息样本
samples = [
    bytes.fromhex("A5 01 FF 04 00 00 00 A5 00 00 00 B2"),
    bytes.fromhex("A5 01 FF 04 00 01 00 A5 00 00 00 B1"),
]

print("="*70)
print("分析 0xFF 消息")
print("="*70)

for i, msg in enumerate(samples):
    print(f"\n样本 {i+1}:")
    print(f"原始: {' '.join([f'{b:02X}' for b in msg])}")

    sync = msg[0]
    user_id = msg[1]
    msg_type = msg[2]
    msg_len = struct.unpack('<H', msg[3:5])[0]
    msg_id = struct.unpack('<H', msg[5:7])[0]

    print(f"\n解析:")
    print(f"  同步头: 0x{sync:02X}")
    print(f"  用户ID: {user_id}")
    print(f"  消息类型: 0x{msg_type:02X} (0xFF)")
    print(f"  数据长度: {msg_len} 字节")
    print(f"  消息ID: {msg_id}")

    if msg_len > 0:
        data = msg[7:7+msg_len]
        print(f"  数据: {' '.join([f'{b:02X}' for b in data])}")

        # 尝试不同的解释
        if len(data) == 4:
            val_le = struct.unpack('<I', data)[0]
            val_be = struct.unpack('>I', data)[0]
            print(f"\n  可能的解释:")
            print(f"    - 4个字节: {data[0]}, {data[1]}, {data[2]}, {data[3]}")
            print(f"    - 32位整数(小端): {val_le}")
            print(f"    - 32位整数(大端): {val_be}")
            print(f"    - 可能是版本号: {data[0]}.{data[1]}.{data[2]}.{data[3]}")

    checksum = msg[7+msg_len]
    calc_checksum = (~sum(msg[:7+msg_len]) + 1) & 0xFF

    print(f"\n  校验码: 0x{checksum:02X} {'✓' if checksum == calc_checksum else '✗'}")

print("\n" + "="*70)
print("结论:")
print("="*70)
print("""
0xFF 消息的特征:
1. 格式完全符合标准协议
2. 校验码正确
3. 数据长度为 4 字节，内容为 A5 00 00 00
4. 消息ID 递增 (0, 1, ...)

可能性:
1. 0xFF 是设备状态消息 (State/Status)
2. 0xFF 是错误消息 (Error)
3. 0xFF 是版本信息消息 (Version)
4. 0xFF 是心跳消息 (Heartbeat)

建议:
1. 尝试发送 0xFF 类型的确认消息
2. 查看设备是否有调试模式输出更多信息
3. 联系厂商获取完整协议文档
""")
