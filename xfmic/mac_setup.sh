#!/bin/bash
# RK3328降噪板 Mac环境快速配置脚本

echo "=================================="
echo "RK3328降噪板 Mac环境配置向导"
echo "=================================="
echo ""

# 检查Homebrew
echo "[1/5] 检查Homebrew..."
if ! command -v brew &> /dev/null; then
    echo "❌ 未安装Homebrew"
    echo "正在安装Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✓ Homebrew已安装"
fi

# 检查Python3
echo ""
echo "[2/5] 检查Python3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未安装Python3"
    echo "正在安装Python3..."
    brew install python3
else
    PYTHON_VERSION=$(python3 --version)
    echo "✓ $PYTHON_VERSION"
fi

# 安装PortAudio
echo ""
echo "[3/5] 安装PortAudio（PyAudio依赖）..."
if brew list portaudio &> /dev/null; then
    echo "✓ PortAudio已安装"
else
    echo "正在安装PortAudio..."
    brew install portaudio
fi

# 安装Python依赖
echo ""
echo "[4/5] 安装Python依赖..."
pip3 install --upgrade pip
pip3 install pyserial pyaudio numpy

echo ""
echo "[5/5] 检查串口设备..."
echo "请确保USB转TTL已连接到Mac"
echo ""

# 查找串口设备
SERIAL_PORTS=$(ls /dev/tty.{usbserial,wchusbserial}* 2>/dev/null)

if [ -z "$SERIAL_PORTS" ]; then
    echo "⚠️  未找到串口设备"
    echo ""
    echo "可能原因："
    echo "1. USB转TTL未连接"
    echo "2. CH340驱动未安装"
    echo ""
    echo "请按照以下步骤操作："
    echo "1. 下载CH340 Mac驱动: http://www.wch.cn/downloads/CH341SER_MAC_ZIP.html"
    echo "2. 安装驱动并重启Mac"
    echo "3. 连接USB转TTL到Mac"
    echo "4. 重新运行此脚本"
else
    echo "✓ 找到串口设备:"
    echo "$SERIAL_PORTS"
    echo ""
    echo "=================================="
    echo "✓ 配置完成！"
    echo "=================================="
    echo ""
    echo "下一步："
    echo "1. 连接硬件:"
    echo "   - RK3328 TTL串口 ← USB转TTL ← Mac"
    echo "   - RK3328 麦克风音频输出 ← 3.5mm线 ← Mac音频输入"
    echo ""
    echo "2. 运行示例:"
    for PORT in $SERIAL_PORTS; do
        echo "   python3 rk3328_demo.py $PORT"
        break
    done
    echo ""
    echo "3. 查看完整文档:"
    echo "   cat README_MAC.md"
fi

echo ""
