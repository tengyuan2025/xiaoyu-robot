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

    cfsetispeed(&options, B115200);
    cfsetospeed(&options, B115200);

    options.c_cflag &= ~PARENB;
    options.c_cflag &= ~CSTOPB;
    options.c_cflag &= ~CSIZE;
    options.c_cflag |= CS8;
    options.c_cflag &= ~CRTSCTS;
    options.c_cflag |= CREAD | CLOCAL;

    options.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);
    options.c_oflag &= ~OPOST;
    options.c_iflag &= ~(IXON | IXOFF | IXANY);

    if (tcsetattr(fd, TCSANOW, &options) != 0) {
        perror("tcsetattr");
        return -1;
    }

    return 0;
}

// 发送JSON命令
int send_json_command(int fd, const char* json_cmd)
{
    int json_len = strlen(json_cmd);
    int packet_len = 7 + json_len + 1;

    unsigned char* packet = (unsigned char*)malloc(packet_len);
    if (!packet) {
        printf("内存分配失败\n");
        return -1;
    }

    packet[0] = 0xA5;
    packet[1] = 0x01;
    packet[2] = 0x04;
    packet[3] = json_len & 0xFF;
    packet[4] = (json_len >> 8) & 0xFF;
    packet[5] = 0x01;
    packet[6] = 0x00;

    memcpy(packet + 7, json_cmd, json_len);
    packet[7 + json_len] = calculate_checksum(packet, 7 + json_len);

    printf("发送: %s\n", json_cmd);

    ssize_t written = write(fd, packet, packet_len);
    if (written < 0) {
        perror("写入失败");
        free(packet);
        return -1;
    }

    free(packet);
    return 0;
}

// 发送确认消息
void send_confirm(int fd, unsigned char msg_id_low, unsigned char msg_id_high)
{
    unsigned char packet[8];
    packet[0] = 0xA5;
    packet[1] = 0x01;
    packet[2] = 0x03;
    packet[3] = 0x00;
    packet[4] = 0x00;
    packet[5] = msg_id_low;
    packet[6] = msg_id_high;
    packet[7] = calculate_checksum(packet, 7);

    write(fd, packet, 8);
}

// 等待并处理握手
int wait_for_handshake(int fd, int timeout_sec)
{
    unsigned char buffer[256];
    fd_set readfds;
    struct timeval tv;
    int handshake_received = 0;

    printf("等待设备握手...\n");

    for(int i = 0; i < timeout_sec * 2; i++) {
        FD_ZERO(&readfds);
        FD_SET(fd, &readfds);
        tv.tv_sec = 0;
        tv.tv_usec = 500000; // 0.5秒

        int ret = select(fd + 1, &readfds, NULL, NULL, &tv);
        if (ret > 0) {
            ssize_t n = read(fd, buffer, sizeof(buffer));
            if (n >= 12) {
                // 检查是否是握手消息 (A5 01 01...)
                if (buffer[0] == 0xA5 && buffer[1] == 0x01 && buffer[2] == 0x01) {
                    printf("✓ 收到握手消息\n");
                    // 发送确认
                    send_confirm(fd, buffer[5], buffer[6]);
                    printf("✓ 已发送握手确认\n");
                    handshake_received = 1;
                    break;
                }
            }
        } else {
            printf(".");
            fflush(stdout);
        }
    }

    printf("\n");
    return handshake_received;
}

int main(int argc, char* argv[])
{
    printf("=== RK3328 设备初始化与唤醒词设置 ===\n\n");

    // 打开串口
    printf("打开串口: %s\n", UART_DEVICE);
    int fd = open(UART_DEVICE, O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (fd < 0) {
        perror("打开串口失败");
        return -1;
    }

    if (setup_serial(fd) < 0) {
        close(fd);
        return -1;
    }

    // 改回阻塞模式
    int flags = fcntl(fd, F_GETFL, 0);
    fcntl(fd, F_SETFL, flags & ~O_NONBLOCK);

    printf("✓ 串口已打开并配置 (115200 8N1)\n\n");

    // 步骤1：等待握手
    if (!wait_for_handshake(fd, 5)) {
        printf("✗ 握手超时\n");
        close(fd);
        return -1;
    }

    sleep(1);

    // 步骤2：发送 manual_wakeup 初始化设备
    printf("\n步骤1: 发送初始化命令 (manual_wakeup)\n");
    send_json_command(fd, "{\"type\":\"manual_wakeup\",\"content\":{\"beam\":0}}");
    printf("✓ 初始化命令已发送\n");

    sleep(2);

    // 步骤3：发送唤醒词设置
    printf("\n步骤2: 发送唤醒词设置命令\n");
    const char* wakeup_cmd = "{\"type\":\"wakeup_keywords\",\"content\":{\"keyword\":\"xiao3 fei1 xiao3 fei1;xiao3 bu4 xiao3 bu4\",\"threshold\":\"900;900\"}}";
    send_json_command(fd, wakeup_cmd);
    printf("✓ 唤醒词设置已发送\n");

    // 等待响应
    printf("\n等待设备响应...\n");
    unsigned char response[256];
    fd_set readfds;
    struct timeval tv;

    for(int i = 0; i < 5; i++) {
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

    printf("\n\n完成！现在可以运行 ./recv_program 监听唤醒事件\n");
    printf("尝试说: '小飞小飞' 或 '小布小布'\n\n");

    close(fd);
    return 0;
}
