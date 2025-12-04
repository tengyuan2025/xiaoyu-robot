#!/bin/bash

echo "=== 测试 recv_program_original ==="
echo ""

# 启动程序
echo "启动程序..."
./recv_program_original &
PID=$!

# 等待2秒
sleep 2

# 检查进程状态
if ps -p $PID > /dev/null 2>&1; then
    echo "✓ 程序已成功启动 (PID: $PID)"
    echo ""

    # 检查线程数
    echo "线程信息:"
    ps -M -p $PID 2>/dev/null | head -5

    # 检查串口是否打开
    echo ""
    echo "打开的文件描述符:"
    lsof -p $PID 2>/dev/null | grep -E "tty|serial"

    echo ""
    echo "程序正在运行，按 Ctrl+C 停止"
    echo "或等待5秒后自动停止..."
    sleep 5

    # 停止程序
    kill -2 $PID 2>/dev/null
    sleep 1
    if ps -p $PID > /dev/null 2>&1; then
        kill -9 $PID 2>/dev/null
        echo "程序已强制停止"
    else
        echo "程序已正常停止"
    fi
else
    echo "✗ 程序启动失败或立即退出"
    exit 1
fi
