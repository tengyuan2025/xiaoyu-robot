#!/bin/bash
#
# RK3328语音交互系统快速启动脚本
#

echo "======================================================================"
echo "RK3328 环形麦克风阵列语音交互系统"
echo "======================================================================"
echo ""

# 检查串口设备
echo "查找串口设备..."
SERIAL_PORTS=$(ls /dev/tty.usbserial* 2>/dev/null)

if [ -z "$SERIAL_PORTS" ]; then
    echo "❌ 未找到串口设备"
    echo ""
    echo "请检查："
    echo "  1. USB转TTL是否已连接"
    echo "  2. RK3328是否已通电"
    echo "  3. macOS是否已安装CH340驱动"
    exit 1
fi

echo "✓ 找到串口设备："
echo "$SERIAL_PORTS"
echo ""

# 选择串口
SERIAL_PORT=$(echo "$SERIAL_PORTS" | head -1)
echo "使用串口: $SERIAL_PORT"
echo ""

# 检查Python依赖
echo "检查依赖..."
python3 -c "import pyaudio, websocket" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 缺少依赖，正在安装..."
    pip3 install pyaudio websocket-client
fi
echo "✓ 依赖完整"
echo ""

# 检查AIUI配置
if grep -q "your_appid_here" voice_interaction.py; then
    echo "⚠️  警告：检测到默认AIUI配置"
    echo ""
    echo "请先编辑 voice_interaction.py 文件，配置你的AIUI参数："
    echo "  AIUI_APPID"
    echo "  AIUI_API_KEY"
    echo "  AIUI_API_SECRET"
    echo ""
    echo "在 https://console.xfyun.cn/app/myapp 创建应用获取"
    echo ""
    read -p "是否继续（用于测试连接）？[y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 启动系统
echo "======================================================================"
echo "启动语音交互系统..."
echo "======================================================================"
echo ""

# 询问是否指定音频设备
read -p "是否要指定音频输入设备？[y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "可用的音频设备："
    python3 stream_recorder.py --list
    echo ""
    read -p "请输入音频设备索引: " AUDIO_INDEX
    python3 voice_interaction.py "$SERIAL_PORT" "$AUDIO_INDEX"
else
    python3 voice_interaction.py "$SERIAL_PORT"
fi
