/**
 * RK3328降噪板声源定位读取程序
 * 用于Linux系统下通过串口读取声源定位信息
 * 
 * 编译: gcc -o rk3328_doa_reader rk3328_doa_reader.c -ljson-c -lpthread
 * 运行: sudo ./rk3328_doa_reader /dev/ttyUSB0
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <termios.h>
#include <time.h>
#include <signal.h>
#include <pthread.h>

// 如果没有json-c库，使用简单的字符串解析
#ifdef USE_JSON_C
#include <json-c/json.h>
#endif

#define BUFFER_SIZE 4096
#define SERIAL_TIMEOUT 100000  // 100ms in microseconds

// 全局变量
static int keep_running = 1;
static int serial_fd = -1;

// 波束角度映射表（环形六麦）
typedef struct {
    int beam_id;
    int angle;
    const char* direction;
} BeamInfo;

static BeamInfo beam_map[] = {
    {0, 0,   "正前方"},
    {1, 60,  "右前方"},
    {2, 120, "右后方"},
    {3, 180, "正后方"},
    {4, 240, "左后方"},
    {5, 300, "左前方"}
};

// 信号处理函数
void signal_handler(int sig) {
    if (sig == SIGINT || sig == SIGTERM) {
        printf("\n接收到退出信号，正在关闭...\n");
        keep_running = 0;
    }
}

// 配置串口
int configure_serial(int fd, int speed) {
    struct termios tty;
    
    if (tcgetattr(fd, &tty) != 0) {
        printf("错误: 获取串口属性失败 - %s\n", strerror(errno));
        return -1;
    }
    
    // 设置波特率
    speed_t baud_rate;
    switch(speed) {
        case 9600:   baud_rate = B9600; break;
        case 19200:  baud_rate = B19200; break;
        case 38400:  baud_rate = B38400; break;
        case 57600:  baud_rate = B57600; break;
        case 115200: baud_rate = B115200; break;
        default:
            printf("不支持的波特率: %d\n", speed);
            return -1;
    }
    
    cfsetospeed(&tty, baud_rate);
    cfsetispeed(&tty, baud_rate);
    
    // 8N1 配置
    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;  // 8位数据位
    tty.c_iflag &= ~IGNBRK;                       // 禁用break处理
    tty.c_lflag = 0;                              // 无信号字符，无回显，无规范处理
    tty.c_oflag = 0;                              // 无重映射，无延迟
    tty.c_cc[VMIN]  = 0;                          // 读取不阻塞
    tty.c_cc[VTIME] = 5;                          // 0.5秒读超时
    
    tty.c_iflag &= ~(IXON | IXOFF | IXANY);       // 关闭软件流控制
    tty.c_cflag |= (CLOCAL | CREAD);              // 忽略modem控制，启用接收
    tty.c_cflag &= ~(PARENB | PARODD);            // 关闭奇偶校验
    tty.c_cflag &= ~CSTOPB;                       // 1个停止位
    tty.c_cflag &= ~CRTSCTS;                      // 关闭硬件流控制
    
    if (tcsetattr(fd, TCSANOW, &tty) != 0) {
        printf("错误: 设置串口属性失败 - %s\n", strerror(errno));
        return -1;
    }
    
    return 0;
}

// 发送手动唤醒命令
int send_manual_wakeup(int fd, int beam) {
    char cmd[256];
    snprintf(cmd, sizeof(cmd), 
        "{\"type\":\"manual_wakeup\",\"content\":{\"beam\":%d}}\n", beam);
    
    int n = write(fd, cmd, strlen(cmd));
    if (n < 0) {
        printf("发送命令失败: %s\n", strerror(errno));
        return -1;
    }
    
    printf("已发送手动唤醒命令，波束: %d\n", beam);
    return 0;
}

// 获取版本信息
int send_get_version(int fd) {
    const char* cmd = "{\"type\":\"get_version\"}\n";
    
    int n = write(fd, cmd, strlen(cmd));
    if (n < 0) {
        printf("发送命令失败: %s\n", strerror(errno));
        return -1;
    }
    
    printf("已发送获取版本命令\n");
    return 0;
}

// 解析JSON消息（简单解析，不依赖json-c库）
void parse_message(const char* message) {
    char* type_pos = strstr(message, "\"type\"");
    if (!type_pos) return;
    
    // 检查是否是唤醒事件
    if (strstr(message, "\"aiui_event\"")) {
        char* event_type = strstr(message, "\"eventType\"");
        if (event_type) {
            int event_id = 0;
            sscanf(event_type, "\"eventType\":%d", &event_id);
            
            if (event_id == 4) {  // 唤醒事件
                // 获取波束信息
                char* beam_pos = strstr(message, "\"arg1\"");
                if (beam_pos) {
                    int beam = -1;
                    sscanf(beam_pos, "\"arg1\":%d", &beam);
                    
                    // 获取时间戳
                    time_t now;
                    time(&now);
                    char time_str[64];
                    strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", localtime(&now));
                    
                    // 查找对应的角度信息
                    if (beam >= 0 && beam < 6) {
                        printf("\n========================================\n");
                        printf("[%s] 检测到声源!\n", time_str);
                        printf("波束编号: %d\n", beam);
                        printf("方向角度: %d°\n", beam_map[beam].angle);
                        printf("方向描述: %s\n", beam_map[beam].direction);
                        
                        // 尝试获取唤醒词
                        char* keyword_pos = strstr(message, "\"keyword\"");
                        if (keyword_pos) {
                            char keyword[128] = {0};
                            sscanf(keyword_pos, "\"keyword\":\"%127[^\"]\"", keyword);
                            printf("唤醒词: %s\n", keyword);
                        }
                        printf("========================================\n");
                    }
                }
            }
        }
    } else if (strstr(message, "\"version\"")) {
        printf("\n设备版本信息: %s\n", message);
    }
}

// 读取串口数据线程
void* read_serial_thread(void* arg) {
    char buffer[BUFFER_SIZE];
    char message[BUFFER_SIZE * 2];
    int message_len = 0;
    
    while (keep_running) {
        int n = read(serial_fd, buffer, sizeof(buffer) - 1);
        
        if (n > 0) {
            buffer[n] = '\0';
            
            // 将数据追加到消息缓冲区
            if (message_len + n < sizeof(message) - 1) {
                memcpy(message + message_len, buffer, n);
                message_len += n;
                message[message_len] = '\0';
                
                // 查找完整的JSON消息（以}结尾）
                char* msg_end = strrchr(message, '}');
                if (msg_end) {
                    *(msg_end + 1) = '\0';
                    
                    // 处理每个完整的消息
                    char* msg_start = message;
                    char* brace_start;
                    
                    while ((brace_start = strchr(msg_start, '{')) != NULL) {
                        char* brace_end = strchr(brace_start, '}');
                        if (brace_end) {
                            char single_msg[BUFFER_SIZE];
                            int len = brace_end - brace_start + 1;
                            strncpy(single_msg, brace_start, len);
                            single_msg[len] = '\0';
                            
                            parse_message(single_msg);
                            msg_start = brace_end + 1;
                        } else {
                            break;
                        }
                    }
                    
                    // 保留未处理的部分
                    if (msg_end + 1 < message + message_len) {
                        int remaining = message + message_len - (msg_end + 1);
                        memmove(message, msg_end + 1, remaining);
                        message_len = remaining;
                    } else {
                        message_len = 0;
                    }
                }
                
                // 防止缓冲区溢出
                if (message_len > BUFFER_SIZE) {
                    message_len = 0;
                }
            }
        } else if (n < 0 && errno != EAGAIN) {
            printf("读取串口错误: %s\n", strerror(errno));
            break;
        }
        
        usleep(10000);  // 10ms延迟
    }
    
    return NULL;
}

// 显示帮助信息
void show_help(const char* program_name) {
    printf("使用方法: %s <串口设备> [选项]\n", program_name);
    printf("\n参数:\n");
    printf("  <串口设备>    串口设备路径 (例如: /dev/ttyUSB0, /dev/ttyS0)\n");
    printf("\n选项:\n");
    printf("  -b <波特率>   设置波特率 (默认: 115200)\n");
    printf("                支持: 9600, 19200, 38400, 57600, 115200\n");
    printf("  -m <波束号>   发送手动唤醒命令 (0-5)\n");
    printf("  -v            获取设备版本信息\n");
    printf("  -h            显示此帮助信息\n");
    printf("\n示例:\n");
    printf("  %s /dev/ttyUSB0              # 连接到ttyUSB0，默认115200波特率\n", program_name);
    printf("  %s /dev/ttyS0 -b 9600        # 使用9600波特率\n", program_name);
    printf("  %s /dev/ttyUSB0 -m 0         # 手动唤醒波束0(正前方)\n", program_name);
    printf("\n波束方向对应关系(环形六麦):\n");
    for (int i = 0; i < 6; i++) {
        printf("  波束%d: %3d° - %s\n", 
               beam_map[i].beam_id, 
               beam_map[i].angle, 
               beam_map[i].direction);
    }
    printf("\n按 Ctrl+C 退出程序\n");
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        show_help(argv[0]);
        return 1;
    }
    
    const char* serial_port = argv[1];
    int baud_rate = 115200;
    int manual_beam = -1;
    int get_version = 0;
    
    // 解析命令行参数
    for (int i = 2; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0) {
            show_help(argv[0]);
            return 0;
        } else if (strcmp(argv[i], "-b") == 0 && i + 1 < argc) {
            baud_rate = atoi(argv[++i]);
        } else if (strcmp(argv[i], "-m") == 0 && i + 1 < argc) {
            manual_beam = atoi(argv[++i]);
            if (manual_beam < 0 || manual_beam > 5) {
                printf("错误: 波束号必须在0-5之间\n");
                return 1;
            }
        } else if (strcmp(argv[i], "-v") == 0) {
            get_version = 1;
        }
    }
    
    printf("RK3328降噪板声源定位读取程序\n");
    printf("========================================\n");
    printf("串口设备: %s\n", serial_port);
    printf("波特率: %d\n", baud_rate);
    printf("========================================\n\n");
    
    // 打开串口
    serial_fd = open(serial_port, O_RDWR | O_NOCTTY | O_NDELAY);
    if (serial_fd < 0) {
        printf("错误: 无法打开串口 %s - %s\n", serial_port, strerror(errno));
        printf("\n提示:\n");
        printf("1. 检查设备是否连接\n");
        printf("2. 检查设备路径是否正确\n");
        printf("3. 可能需要sudo权限\n");
        printf("4. 检查用户是否在dialout组: groups $USER\n");
        printf("   如果不在，运行: sudo usermod -a -G dialout $USER\n");
        return 1;
    }
    
    // 配置串口
    if (configure_serial(serial_fd, baud_rate) < 0) {
        close(serial_fd);
        return 1;
    }
    
    // 设置非阻塞模式
    fcntl(serial_fd, F_SETFL, O_NONBLOCK);
    
    printf("串口已打开并配置成功\n");
    
    // 设置信号处理
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    // 发送初始命令
    if (get_version) {
        send_get_version(serial_fd);
        sleep(1);
    }
    
    if (manual_beam >= 0) {
        send_manual_wakeup(serial_fd, manual_beam);
        sleep(1);
    }
    
    // 创建读取线程
    pthread_t read_thread;
    if (pthread_create(&read_thread, NULL, read_serial_thread, NULL) != 0) {
        printf("创建读取线程失败\n");
        close(serial_fd);
        return 1;
    }
    
    printf("开始监听声源定位信息...\n");
    printf("请对设备说出唤醒词或制造声音\n");
    printf("按 Ctrl+C 退出\n\n");
    
    // 主循环
    while (keep_running) {
        sleep(1);
    }
    
    // 等待线程结束
    pthread_join(read_thread, NULL);
    
    // 关闭串口
    close(serial_fd);
    printf("\n程序已退出\n");
    
    return 0;
}