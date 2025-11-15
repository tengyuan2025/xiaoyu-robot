# Makefile for RK3328 DOA Reader
# RK3328降噪板声源定位读取程序编译脚本

CC = gcc
CFLAGS = -Wall -O2 -std=c99
LIBS = -lpthread
TARGET = rk3328_doa_reader
SOURCE = rk3328_doa_reader.c

# 默认目标
all: $(TARGET)

# 编译主程序
$(TARGET): $(SOURCE)
	@echo "正在编译 $(TARGET)..."
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCE) $(LIBS)
	@echo "编译完成: $(TARGET)"
	@echo "使用方法: ./$(TARGET) /dev/ttyUSB0"

# 安装到系统
install: $(TARGET)
	@echo "安装到 /usr/local/bin/..."
	sudo cp $(TARGET) /usr/local/bin/
	sudo chmod +x /usr/local/bin/$(TARGET)
	@echo "安装完成，现在可以在任何位置使用 $(TARGET) 命令"

# 创建软链接到/usr/local/bin
link: $(TARGET)
	@echo "创建软链接到 /usr/local/bin/..."
	sudo ln -sf $(PWD)/$(TARGET) /usr/local/bin/$(TARGET)
	@echo "软链接创建完成"

# 清理编译文件
clean:
	@echo "清理编译文件..."
	rm -f $(TARGET)
	@echo "清理完成"

# 卸载
uninstall:
	@echo "从系统中卸载..."
	sudo rm -f /usr/local/bin/$(TARGET)
	@echo "卸载完成"

# 检查依赖
check-deps:
	@echo "检查编译环境..."
	@which $(CC) > /dev/null || (echo "错误: 未找到 gcc 编译器" && false)
	@echo "gcc 版本:"
	@$(CC) --version | head -1
	@echo "依赖检查完成"

# 测试编译
test: $(TARGET)
	@echo "测试程序编译..."
	@./$(TARGET) -h > /dev/null && echo "程序正常" || echo "程序异常"

# 快速编译和测试
quick: clean $(TARGET) test

# 调试版本
debug: CFLAGS += -g -DDEBUG
debug: $(TARGET)
	@echo "调试版本编译完成"

# 发布版本
release: CFLAGS += -DNDEBUG -s
release: $(TARGET)
	@echo "发布版本编译完成"
	@strip $(TARGET)
	@echo "已去除调试信息"

# 显示帮助
help:
	@echo "可用的编译目标:"
	@echo "  all      - 编译程序 (默认)"
	@echo "  clean    - 清理编译文件"
	@echo "  install  - 安装到系统"
	@echo "  link     - 创建软链接"
	@echo "  uninstall- 从系统卸载"
	@echo "  debug    - 编译调试版本"
	@echo "  release  - 编译发布版本"
	@echo "  test     - 测试编译"
	@echo "  quick    - 快速重新编译"
	@echo "  check-deps - 检查编译环境"
	@echo "  help     - 显示此帮助"
	@echo ""
	@echo "使用示例:"
	@echo "  make              # 编译程序"
	@echo "  make clean        # 清理"
	@echo "  make install      # 编译并安装"
	@echo "  make debug        # 编译调试版本"

# 确保这些目标总是被执行
.PHONY: all clean install uninstall check-deps test quick debug release help link