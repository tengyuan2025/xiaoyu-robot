#!/usr/bin/env python3
"""
修改唤醒词为 "小飞小飞"
"""

import glob
import sys
from rk3328_controller import RK3328Controller


def find_serial_port():
    """查找串口设备"""
    patterns = ['/dev/tty.usbserial*', '/dev/tty.wchusbserial*']
    ports = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))
    return ports[0] if ports else None


def main():
    print("="*60)
    print("修改 RK3328 唤醒词为 '小飞小飞'")
    print("="*60)

    # 查找串口
    port = find_serial_port()
    if not port:
        print("❌ 未找到串口设备")
        sys.exit(1)

    print(f"\n✓ 找到设备: {port}")

    # 连接
    controller = RK3328Controller(port)
    if not controller.connect():
        print("❌ 连接失败")
        sys.exit(1)

    print("✓ 设备连接成功\n")

    # 修改唤醒词
    print("正在修改唤醒词...")
    print("  原唤醒词: 小微小微 (xiao3 wei1 xiao3 wei1)")
    print("  新唤醒词: 小飞小飞 (xiao3 fei1 xiao3 fei1)")
    print("  唤醒阈值: 900")

    # 发送修改命令
    success = controller.switch_wakeup_word(
        keyword="xiao3 fei1 xiao3 fei1",
        threshold=900
    )

    if success:
        print("\n✓ 唤醒词修改成功！")
        print("\n现在可以说 '小飞小飞' 来唤醒设备了")
    else:
        print("\n❌ 唤醒词修改失败")
        print("请检查设备是否支持浅定制功能")

    controller.close()


if __name__ == "__main__":
    main()
