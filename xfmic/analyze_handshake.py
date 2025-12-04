#!/usr/bin/env python3
"""
分析握手消息格式
"""

import struct

# 从你的日志中提取的握手消息
handshake_hex = "A5 01 01 04 00 00 00 A5 00 00 00 B0"
handshake_bytes = bytes.fromhex(handshake_hex.replace(" ", ""))

print("="*60)
print("分析握手消息格式")
print("="*60)

print(f"\n原始数据: {handshake_hex}")
print(f"字节数组: {[f'0x{b:02X}' for b in handshake_bytes]}")

# 解析
sync = handshake_bytes[0]
user_id = handshake_bytes[1]
msg_type = handshake_bytes[2]
msg_len = struct.unpack('<H', handshake_bytes[3:5])[0]
msg_id = struct.unpack('<H', handshake_bytes[5:7])[0]
data = handshake_bytes[7:7+msg_len]
checksum = handshake_bytes[7+msg_len]

print(f"\n解析结果:")
print(f"  同步头: 0x{sync:02X}")
print(f"  用户ID: {user_id}")
print(f"  消息类型: 0x{msg_type:02X} ({'握手' if msg_type == 0x01 else '其他'})")
print(f"  数据长度: {msg_len} 字节")
print(f"  消息ID: {msg_id}")
print(f"  数据内容: {' '.join([f'{b:02X}' for b in data])}")
print(f"  校验码: 0x{checksum:02X}")

# 构造确认消息
print(f"\n{'='*60}")
print("构造确认消息")
print("="*60)

confirm_packet = bytearray()
confirm_packet.append(0xA5)  # 同步头
confirm_packet.append(0x01)  # 用户ID
confirm_packet.append(0x03)  # 消息类型：确认
confirm_packet.extend(struct.pack('<H', 0))  # 数据长度为0
confirm_packet.extend(handshake_bytes[5:7])  # 使用原消息ID

# 计算校验码
checksum_calc = (~sum(confirm_packet) + 1) & 0xFF
confirm_packet.append(checksum_calc)

print(f"\n确认消息:")
print(f"  HEX: {' '.join([f'{b:02X}' for b in confirm_packet])}")
print(f"  长度: {len(confirm_packet)} 字节")

# 验证校验码
print(f"\n{'='*60}")
print("验证握手消息校验码")
print("="*60)

checksum_data = handshake_bytes[:7+msg_len]
calculated_checksum = (~sum(checksum_data) + 1) & 0xFF
print(f"  计算得到: 0x{calculated_checksum:02X}")
print(f"  消息中的: 0x{checksum:02X}")
print(f"  验证结果: {'✓ 正确' if calculated_checksum == checksum else '✗ 错误'}")

# 如果握手数据不为空，分析数据内容
if msg_len > 0:
    print(f"\n{'='*60}")
    print("握手数据内容分析")
    print("="*60)
    print(f"  数据: {' '.join([f'{b:02X}' for b in data])}")

    # 尝试不同的解析方式
    if len(data) == 4:
        print(f"\n  可能的解释:")
        print(f"    - 4个字节: {data[0]}, {data[1]}, {data[2]}, {data[3]}")
        print(f"    - 1个32位整数(小端): {struct.unpack('<I', data)[0]}")
        print(f"    - 1个32位整数(大端): {struct.unpack('>I', data)[0]}")
        print(f"    - 2个16位整数(小端): {struct.unpack('<HH', data)}")
