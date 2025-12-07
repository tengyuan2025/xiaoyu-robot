#!/bin/bash
#
# RK3328 + AIUI 完整语音助手启动脚本
#

# 清屏并重置终端状态
clear
printf '\033c'  # 重置终端

echo "======================================================================"
echo "RK3328 + AIUI V3 语音交互系统"
echo "======================================================================"
echo ""

# 查找串口设备
echo "查找串口设备..."
SERIAL_PORT=$(ls /dev/tty.usbserial* 2>/dev/null | head -1)

if [ -z "$SERIAL_PORT" ]; then
    echo "❌ 未找到串口设备"
    echo ""
    echo "请检查："
    echo "  1. USB转TTL是否已连接"
    echo "  2. RK3328是否已通电"
    exit 1
fi

echo "✓ 找到串口: $SERIAL_PORT"
echo ""

# 询问是否指定音频设备
read -p "是否指定音频输入设备？[y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "可用的音频设备："
    python3 -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'  [{i}] {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count()) if p.get_device_info_by_index(i)['maxInputChannels'] > 0]"
    echo ""
    read -p "请输入设备索引: " AUDIO_INDEX

    cd aiuiv3-demo-master/websocket/python
    python3 aiui_v3_demo.py "$SERIAL_PORT" "$AUDIO_INDEX"
else
    cd aiuiv3-demo-master/websocket/python
    python3 aiui_v3_demo.py "$SERIAL_PORT"
fi
