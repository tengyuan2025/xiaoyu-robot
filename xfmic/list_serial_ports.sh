#!/bin/bash
# 串口设备查看工具

echo "======================================================================"
echo "macOS 串口设备列表"
echo "======================================================================"
echo ""

echo "📱 USB 串口设备:"
echo "----------------------------------------------------------------------"
USB_DEVICES=$(ls /dev/tty.usbserial* /dev/tty.wchusbserial* 2>/dev/null)
if [ -n "$USB_DEVICES" ]; then
    for device in $USB_DEVICES; do
        echo "  ✓ $device"
        ls -l $device | awk '{print "    权限: " $1 "  修改时间: " $6 " " $7 " " $8}'

        # 检查是否被占用
        if lsof $device 2>/dev/null | grep -q "$device"; then
            echo "    状态: 🔴 使用中"
            lsof $device 2>/dev/null | tail -n +2 | awk '{print "    进程: " $1 " (PID: " $2 ")"}'
        else
            echo "    状态: 🟢 空闲"
        fi
        echo ""
    done
else
    echo "  ❌ 未找到 USB 串口设备"
    echo ""
fi

echo "🔌 其他串口设备:"
echo "----------------------------------------------------------------------"
OTHER_DEVICES=$(ls /dev/tty.* 2>/dev/null | grep -v "ttyp" | grep -v "usbserial" | grep -v "wchusbserial")
if [ -n "$OTHER_DEVICES" ]; then
    for device in $OTHER_DEVICES; do
        basename $device | sed 's/^/  - /'
    done
else
    echo "  无"
fi
echo ""

echo "======================================================================"
echo "USB 设备信息:"
echo "======================================================================"
system_profiler SPUSBDataType 2>/dev/null | grep -B 2 -A 8 -i "serial" | head -30
echo ""

echo "======================================================================"
echo "💡 使用提示:"
echo "======================================================================"
echo "  查看实时数据:"
echo "    screen /dev/tty.usbserial-XXXX 115200"
echo ""
echo "  使用 Python 脚本:"
echo "    python3 passive_listen_only.py /dev/tty.usbserial-XXXX"
echo ""
echo "  退出 screen: Ctrl+A 然后按 K，再按 Y"
echo "======================================================================"
