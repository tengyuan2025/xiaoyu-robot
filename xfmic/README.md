# RK3328降噪板声源定位读取程序

这是一个用于在Linux系统下读取RK3328降噪板声源定位信息的C语言程序。

## 功能特性

- 🎯 **实时声源定位**: 监听并显示声源的方向角度信息
- 🔄 **环形六麦支持**: 支持0°-300°全方向声源检测
- 📡 **串口通信**: 通过TTL串口与RK3328降噪板通信
- ⚡ **多线程处理**: 使用多线程确保数据实时性
- 🎛️ **手动控制**: 支持手动唤醒指定波束方向
- 📊 **详细信息**: 显示波束号、角度、方向描述等信息

## 系统要求

- Linux操作系统 (Ubuntu/Debian/CentOS等)
- GCC编译器
- pthread库支持
- 串口设备权限

## 安装说明

### 1. 安装依赖

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install build-essential
```

**CentOS/RHEL:**
```bash
sudo yum groupinstall "Development Tools"
# 或者在新版本中
sudo dnf groupinstall "Development Tools"
```

### 2. 克隆或下载代码

```bash
# 如果您已经有源码文件，直接进入目录
cd /path/to/your/xfmic
```

### 3. 编译程序

```bash
# 使用Makefile编译
make

# 或者手动编译
gcc -o rk3328_doa_reader rk3328_doa_reader.c -lpthread -Wall -O2
```

### 4. 设置串口权限

```bash
# 将当前用户添加到dialout组
sudo usermod -a -G dialout $USER

# 重新登录或使用newgrp命令
newgrp dialout

# 或者直接使用sudo运行程序
```

## 使用方法

### 基本用法

```bash
# 连接到串口设备 (默认115200波特率)
./rk3328_doa_reader /dev/ttyUSB0

# 使用sudo权限运行
sudo ./rk3328_doa_reader /dev/ttyUSB0
```

### 高级选项

```bash
# 指定不同波特率
./rk3328_doa_reader /dev/ttyS0 -b 9600

# 手动唤醒指定波束 (0-5)
./rk3328_doa_reader /dev/ttyUSB0 -m 0    # 唤醒正前方波束

# 获取设备版本信息
./rk3328_doa_reader /dev/ttyUSB0 -v

# 显示帮助信息
./rk3328_doa_reader -h
```

### 常用串口设备

- `/dev/ttyUSB0` - USB转串口适配器
- `/dev/ttyS0` - 系统串口1
- `/dev/ttyAMA0` - 树莓派串口
- `/dev/ttyACM0` - Arduino等设备

## 波束方向对应关系

RK3328降噪板环形六麦的波束方向映射：

| 波束号 | 角度 | 方向描述 |
|--------|------|----------|
| 0      | 0°   | 正前方   |
| 1      | 60°  | 右前方   |
| 2      | 120° | 右后方   |
| 3      | 180° | 正后方   |
| 4      | 240° | 左后方   |
| 5      | 300° | 左前方   |

## 输出示例

程序运行时的典型输出：

```
RK3328降噪板声源定位读取程序
========================================
串口设备: /dev/ttyUSB0
波特率: 115200
========================================

串口已打开并配置成功
开始监听声源定位信息...
请对设备说出唤醒词或制造声音
按 Ctrl+C 退出

========================================
[2024-11-15 14:30:25] 检测到声源!
波束编号: 1
方向角度: 60°
方向描述: 右前方
唤醒词: xiao3 wei1 xiao3 wei1
========================================
```

## 硬件连接

确保正确连接RK3328降噪板：

1. **电源连接**: DC12V3A 或 DC5.5-2.1
2. **串口连接**: 
   - TTL 3.3V电平
   - 波特率: 115200
   - 数据位: 8
   - 停止位: 1
   - 无奇偶校验
3. **麦克风阵列**: 确保环形六麦正确连接

## 故障排除

### 常见问题

1. **权限被拒绝**
   ```bash
   # 解决方案1: 使用sudo
   sudo ./rk3328_doa_reader /dev/ttyUSB0
   
   # 解决方案2: 添加用户到dialout组
   sudo usermod -a -G dialout $USER
   # 然后重新登录
   ```

2. **找不到设备文件**
   ```bash
   # 查看可用串口设备
   ls -la /dev/tty*
   
   # 查看USB设备
   lsusb
   
   # 查看系统消息
   dmesg | grep tty
   ```

3. **编译错误**
   ```bash
   # 检查编译环境
   make check-deps
   
   # 安装缺失的依赖
   sudo apt install build-essential
   ```

4. **无数据返回**
   - 检查硬件连接
   - 确认波特率设置正确
   - 检查设备是否正常工作
   - 尝试手动唤醒: `./rk3328_doa_reader /dev/ttyUSB0 -m 0`

### 调试模式

编译调试版本获取更多信息：

```bash
make debug
./rk3328_doa_reader /dev/ttyUSB0
```

## Makefile命令

```bash
make           # 编译程序
make clean     # 清理编译文件
make install   # 安装到系统
make debug     # 编译调试版本
make release   # 编译发布版本
make help      # 显示所有可用命令
```

## 应用场景

- 🤖 **智能机器人**: 实现声源跟踪和转向
- 🏠 **智能家居**: 声控设备方向感知
- 🎙️ **语音助手**: 改善远场语音识别
- 📹 **会议系统**: 自动摄像头跟踪
- 🎮 **交互系统**: 声音定位游戏

## 技术支持

如果遇到问题，请检查：

1. 硬件连接是否正确
2. 串口设备路径是否正确
3. 用户权限是否足够
4. RK3328降噪板固件版本

## 许可证

本程序仅用于教学和研究目的，请遵循相关硬件厂商的使用协议。

## 更新日志

- v1.0.0: 初始版本，支持基本声源定位读取
- 支持环形六麦波束方向检测
- 支持手动唤醒和版本查询
- 多线程数据处理和实时显示

---

**注意**: 使用前请确保RK3328降噪板硬件正常工作，并参考官方文档进行正确的硬件配置。