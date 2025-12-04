#!/bin/bash
# RK3328声源定位测试方案
# 基于11月23日成功经验：使用纯监听模式，不发送任何数据

echo "======================================================================"
echo "RK3328 声源定位测试方案"
echo "======================================================================"
echo ""
echo "📋 测试说明："
echo "  - 本方案完全模拟 screen 命令的行为"
echo "  - 只监听串口数据，不发送任何内容（包括握手确认）"
echo "  - 基于你在 11月23日 成功获取DOA信息的方法"
echo ""
echo "======================================================================"
echo ""

# 查找串口
echo "🔍 正在查找串口设备..."
PORT=$(ls /dev/tty.usbserial* 2>/dev/null | head -1)

if [ -z "$PORT" ]; then
    PORT=$(ls /dev/cu.usbserial* 2>/dev/null | head -1)
fi

if [ -z "$PORT" ]; then
    echo "❌ 未找到串口设备"
    echo ""
    echo "请检查："
    echo "  1. RK3328降噪板是否已连接到Mac"
    echo "  2. USB转串口驱动是否已安装"
    echo ""
    exit 1
fi

echo "✓ 找到串口: $PORT"
echo ""

# 提供三个测试选项
echo "======================================================================"
echo "请选择测试方式："
echo "======================================================================"
echo ""
echo "方案 1: 使用 passive_listen_only.py (推荐)"
echo "        完整的协议解析 + 唤醒事件检测"
echo "        命令: python3 passive_listen_only.py"
echo ""
echo "方案 2: 使用 raw_serial_monitor.py"
echo "        最原始的数据监听，显示所有字节"
echo "        命令: python3 raw_serial_monitor.py"
echo ""
echo "方案 3: 使用 screen 命令 (你11月23日成功的方法)"
echo "        系统自带工具，最简单"
echo "        命令: screen $PORT 115200"
echo "        退出: 按 Ctrl+A 然后按 K，再按 Y 确认"
echo ""
echo "======================================================================"
echo ""
echo "💡 测试步骤："
echo "  1. 运行上述任一命令"
echo "  2. 等待设备初始化（可能看到握手消息和0xFF消息）"
echo "  3. 对着麦克风说：'小飞小飞' 或 '小微小微'"
echo "  4. 观察是否打印出包含 angle、beam、score 的JSON数据"
echo ""
echo "======================================================================"
echo ""

read -p "按回车键开始运行方案1 (passive_listen_only.py)，或按 Ctrl+C 取消... "

echo ""
echo "🚀 启动纯监听模式..."
echo ""

python3 passive_listen_only.py "$PORT"
