#!/usr/bin/env python3
"""
手动唤醒测试 - 发送手动唤醒命令
"""

import sys
import glob

# 导入控制器
sys.path.insert(0, '/Users/yushuangyang/workspace/xiaoyu-robot/xfmic')
from rk3328_controller import RK3328Controller

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

port = sys.argv[1] if len(sys.argv) > 1 else find_serial_port()

print("="*60)
print("手动唤醒测试")
print("="*60)
print(f"串口: {port}")
print()

controller = RK3328Controller(port)

if controller.connect():
    print()
    print("="*60)
    print("正在发送手动唤醒命令...")
    print("波束方向: 0° (正前方)")
    print("="*60)

    # 发送手动唤醒命令
    if controller.manual_wakeup(beam=0):
        print("✓ 手动唤醒命令已发送")
        print()
        print("现在设备应该进入唤醒状态")
        print("请尝试说话，或者运行 raw_serial_monitor.py 查看数据")
    else:
        print("✗ 手动唤醒命令发送失败")

    print()
    print("="*60)
    print("等待5秒，监听设备响应...")
    print("="*60)

    import time
    for i in range(5):
        msg = controller.read_device_message(timeout=1)
        if msg:
            import json
            print(f"\n收到设备消息:")
            print(json.dumps(msg, ensure_ascii=False, indent=2))

    controller.close()
else:
    print("✗ 连接失败")
