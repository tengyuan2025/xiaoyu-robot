#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <termios.h>

#define UART_DEVICE "/dev/tty.usbserial-140"

// 计算校验码
unsigned char calculate_checksum(unsigned char* data, int len)
{
    unsigned char sum = 0;
    for(int i = 0; i < len; i++){
        sum += data[i];
    }
    return (~sum + 1) & 0xFF;
}

// 配置串口
int setup_serial(int fd)
{
    struct termios options;

    if (tcgetattr(fd, &options) != 0) {
        perror("tcgetattr");
        return -1;
    }

    // 设置波特率
    cfsetispeed(&options, B115200);
    cfsetospeed(&options, B115200);

    // 8N1
    options.c_cflag &= ~PARENB;
    options.c_cflag &= ~CSTOPB;
    options.c_cflag &= ~CSIZE;
    options.c_cflag |= CS8;

    // 不使用流控
    options.c_cflag &= ~CRTSCTS;
    options.c_cflag |= CREAD | CLOCAL;

    // 原始模式
    options.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);
    options.c_oflag &= ~OPOST;
    options.c_iflag &= ~(IXON | IXOFF | IXANY);

    // 应用配置
    if (tcsetattr(fd, TCSANOW, &options) != 0) {
        perror("tcsetattr");
        return -1;
    }

    return 0;
}

int main(int argc, char* argv[])
{
    const char* json_cmd = "{ \"type\": \"wakeup_keywords\", \"content\": { \"keyword\": \"xiao3 fei1 xiao3 fei1;xiao3 bu4 xiao3 bu4\", \"threshold\": \"900;900\" } }";

    printf("=== 发送唤醒词设置命令 ===\n\n");

    // 打开串口
    printf("打开串口: %s\n", UART_DEVICE);
    int fd = open(UART_DEVICE, O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (fd < 0) {
        perror("打开串口失败");
        return -1;
    }

    // 配置串口
    if (setup_serial(fd) < 0) {
        close(fd);
        return -1;
    }

    // 改回阻塞模式
    int flags = fcntl(fd, F_GETFL, 0);
    fcntl(fd, F_SETFL, flags & ~O_NONBLOCK);

    printf("✓ 串口已打开并配置 (115200 8N1)\n\n");

    // 构造消息包
    int json_len = strlen(json_cmd);
    int packet_len = 7 + json_len + 1;

    unsigned char* packet = (unsigned char*)malloc(packet_len);
    if (!packet) {
        printf("内存分配失败\n");
        close(fd);
        return -1;
    }

    packet[0] = 0xA5;                           // 同步头
    packet[1] = 0x01;                           // 用户ID
    packet[2] = 0x04;                           // 消息类型：主控消息
    packet[3] = json_len & 0xFF;                // 数据长度低字节
    packet[4] = (json_len >> 8) & 0xFF;         // 数据长度高字节
    packet[5] = 0x01;                           // 消息ID低字节
    packet[6] = 0x00;                           // 消息ID高字节

    memcpy(packet + 7, json_cmd, json_len);     // JSON数据

    packet[7 + json_len] = calculate_checksum(packet, 7 + json_len); // 校验码

    // 打印发送的数据
    printf("JSON命令:\n%s\n\n", json_cmd);

    printf("发送数据包 (%d 字节):\n", packet_len);
    printf("HEX: ");
    for(int i = 0; i < packet_len; i++){
        printf("%02X ", packet[i]);
        if ((i + 1) % 16 == 0) printf("\n     ");
    }
    printf("\n\n");

    // 发送数据
    ssize_t written = write(fd, packet, packet_len);
    if (written < 0) {
        perror("写入串口失败");
        free(packet);
        close(fd);
        return -1;
    }

    printf("✓ 发送完成，已写入 %zd 字节\n\n", written);

    // 等待一下，看看有没有响应
    printf("等待设备响应 (3秒)...\n");
    sleep(1);

    // 尝试读取响应
    unsigned char response[256];
    fd_set readfds;
    struct timeval tv;

    for(int i = 0; i < 3; i++) {
        FD_ZERO(&readfds);
        FD_SET(fd, &readfds);
        tv.tv_sec = 1;
        tv.tv_usec = 0;

        int ret = select(fd + 1, &readfds, NULL, NULL, &tv);
        if (ret > 0) {
            ssize_t n = read(fd, response, sizeof(response));
            if (n > 0) {
                printf("\n收到响应 (%zd 字节): ", n);
                for(int j = 0; j < n; j++) {
                    printf("%02X ", response[j]);
                }
                printf("\n");
            }
        } else {
            printf(".");
            fflush(stdout);
        }
    }

    printf("\n\n提示：如果没有看到响应，请运行 ./recv_program 持续监听\n");

    free(packet);
    close(fd);

    return 0;
}
