#include <stdio.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "uart.h"
#include <zlib.h>

#define GZIP_WINDOWS_BIT (15 + 16)
#define GZIP_CHUNK_SIZE (32 * 1024)
#undef MAX
#define MAX(a,b)        ((a) > (b) ? (a) : (b))
#undef MIN
#define MIN(a,b)        ((a) < (b) ? (a) : (b))
#define RECV_BUF_LEN 12
#define MSG_NORMAL_LEN 4
#define MSG_EXTRA_LEN 8
#define PACKET_LEN_BIT 4
#define SYNC_HEAD 0xa5
#define SYNC_HEAD_SECOND 0x01

static int recv_index = 0;
static unsigned char recv_buf[RECV_BUF_LEN];
static unsigned int big_buf_len = 0;
static unsigned int big_buf_index = 0;
static void* big_buf = NULL;
static UART_HANDLE uart_hd;
static char ack_buf[RECV_BUF_LEN];
int gzipDecompress(const char* input_data, int inputLength, char** dst, int* outLength)
{

	z_stream strm;
	strm.zalloc = Z_NULL;
	strm.zfree = Z_NULL;
	strm.opaque = Z_NULL;
	strm.avail_in = 0;
	strm.next_in = Z_NULL;
	*outLength = 0;
	int ret = inflateInit2(&strm, GZIP_WINDOWS_BIT);

	if (ret != Z_OK)
		return 0;

	int input_data_left = inputLength;

	do {
		int chunk_size = MIN(GZIP_CHUNK_SIZE, input_data_left);

		if (chunk_size <= 0)
			break;

		strm.next_in = (unsigned char *) input_data;
		strm.avail_in = chunk_size;

		input_data += chunk_size;
		input_data_left -= chunk_size;

		do {
			char out[GZIP_CHUNK_SIZE + 1] = {0};

			strm.next_out = (unsigned char *) out;
			strm.avail_out = GZIP_CHUNK_SIZE;

			ret = inflate(&strm, Z_NO_FLUSH);

			switch (ret) {
				case Z_NEED_DICT:
					ret = Z_DATA_ERROR;
				case Z_DATA_ERROR:
				case Z_MEM_ERROR:
				case Z_STREAM_ERROR:

					inflateEnd(&strm);
					printf("gzip error");
					return 0;
			}

			int have = (GZIP_CHUNK_SIZE - strm.avail_out);

			if (have > 0) {
				char* outTmp = malloc(have + (*outLength) + 1);
				if (*dst && *outLength) {
					memcpy(outTmp, *dst, *outLength);
					free(*dst);
				}
				memcpy(outTmp + (*outLength), out, have);
				*outLength = have + (*outLength);
				*dst = outTmp;
				printf("%s", outTmp);
			}
		} while (strm.avail_out == 0);
	} while (ret != Z_STREAM_END);

	inflateEnd(&strm);
	if (*outLength > 0) {
		(*dst)[*outLength-1] = (char)'\0';
	}
	return (ret == Z_STREAM_END);
}
void process_recv(unsigned char* buf, int len)
{
	//过滤确认消息，避免无限应答循环
	if(buf[2] == 0x03 || buf[2] == 0xFF){
		//0x03是我们发送的确认，0xFF是设备发送的确认
		return;
	}

	int index;
	//构造确认消息（7字节）
	ack_buf[0] = 0xA5;      // 同步头
	ack_buf[1] = 0x01;      // 用户ID
	ack_buf[2] = 0x03;      // 消息类型：确认
	ack_buf[3] = 0x00;      // 数据长度低字节
	ack_buf[4] = 0x00;      // 数据长度高字节
	ack_buf[5] = buf[5];    // 消息ID低字节
	ack_buf[6] = buf[6];    // 消息ID高字节

	//计算校检码
	char check_code = 0;
	for(index = 0; index <= 6; index++){
		check_code += ack_buf[index];
	}
	check_code = ~check_code + 1;
	ack_buf[7] = check_code;

	//发送确认消息（8字节：7字节数据+1字节校验）
	uart_send(uart_hd, ack_buf, 8);

	printf("recv ");
	for(index = 0; index < len; index++){
		printf("%02X ", buf[index]);
	}

	printf("\n");

	//解析不同类型的消息
	if (buf[2] == 0x02) {
		//设备消息（唤醒、DOA等）
		if (len > 7) {
			int data_len = buf[3] | (buf[4] << 8);
			if (data_len > 0) {
				//尝试解析JSON数据
				char json_buf[1024] = {0};
				int copy_len = (data_len < 1023) ? data_len : 1023;
				memcpy(json_buf, buf + 7, copy_len);
				printf("设备消息: %s\n", json_buf);
			}
		}
	} else if (buf[2] == 0x04) {
		//主控消息/设备事件
		if (len > 7) {
			int data_len = buf[3] | (buf[4] << 8);
			if (data_len > 0 && data_len < 4096) {
				// 提取 JSON 数据（跳过前7字节头部，最后1字节是校验码）
				char* json_buf = (char*)malloc(data_len + 1);
				if (json_buf) {
					memset(json_buf, 0, data_len + 1);
					memcpy(json_buf, buf + 7, data_len);

					// 检查是否是 JSON 格式（以 { 开头）
					if (json_buf[0] == '{') {
						printf("\n=== 设备事件 (JSON) ===\n");
						printf("%s\n", json_buf);
						printf("======================\n");
					} else {
						// 尝试 gzip 解压
						int outLength = 0;
						char* outData = NULL;
						if (gzipDecompress(json_buf, data_len, &outData, &outLength)) {
							printf("\n=== Gzip 解压数据 ===\n");
							printf("%s\n", outData);
							printf("====================\n");
							free(outData);
						}
					}
					free(json_buf);
				}
			}
		}
	}

}


void uart_rec(const void *msg, unsigned int msglen, void *user_data)
{
	printf("uart recv %d\n", msglen);

	//过滤不以A5 01开头的无效数据
	if(big_buf == NULL && recv_index + msglen >= 2){
		if(recv_index == 0){
			if(((unsigned char*)msg)[0] != SYNC_HEAD | ((unsigned char*)msg)[1] != SYNC_HEAD_SECOND){
				printf("recv data not SYNC HEAD, drop\n");
				return;
			}
		}else if(recv_index == 1){
			if(recv_buf[0] != SYNC_HEAD | ((unsigned char*)msg)[0] != SYNC_HEAD_SECOND){
				printf("recv data not SYNC HEAD, drop\n");
				recv_index = 0;
				return;
			}
		}
	}

	//不断接收串口字节，构造完成消息
	int copy_len;
	if(big_buf != NULL)
	{
		copy_len = big_buf_len - big_buf_index < msglen? big_buf_len - big_buf_index : msglen;
		memcpy(big_buf + big_buf_index, msg, copy_len);
		big_buf_index += copy_len;
		if(big_buf_index < big_buf_len) return;
	}else {
		copy_len = RECV_BUF_LEN - recv_index < msglen? RECV_BUF_LEN - recv_index : msglen;
		memcpy(recv_buf + recv_index, msg, copy_len);
		if((recv_index + copy_len) > PACKET_LEN_BIT) {
			unsigned int content_len = recv_buf[PACKET_LEN_BIT] << 8 | recv_buf[PACKET_LEN_BIT - 1];
			if(content_len != MSG_NORMAL_LEN){
				big_buf_index = 0;
				big_buf_len = content_len + MSG_EXTRA_LEN;
				big_buf = malloc(big_buf_len);
				printf("uart malloc buf %x len %d\n", (unsigned int)big_buf, big_buf_len);
				memset(big_buf, 0, big_buf_len);
				memcpy(big_buf, recv_buf, recv_index);
				big_buf_index += recv_index;
				recv_index = 0;
				return uart_rec(msg, msglen, user_data);
			}
		}
		recv_index += copy_len;
		if(recv_index < RECV_BUF_LEN) return;
	}

	//已接收完一条完整消息
	if(big_buf != NULL){
		process_recv(big_buf, big_buf_len);   //接受消息处理
		big_buf_len = 0;
		big_buf_index = 0;
		printf("uart free buf %x\n", (unsigned int)big_buf);
		free(big_buf);
		big_buf = NULL;
	}else{
		process_recv(recv_buf, RECV_BUF_LEN);  //接受消息处理
		recv_index = 0;
	}

	//读取的数据中包含下一条消息的开头部分
	if(copy_len < msglen){
		printf("multi msg in one stream left %d byte\n", msglen - copy_len);
		uart_rec(msg + copy_len, msglen - copy_len, user_data);
	}
}

#define UART_DEVICE "/dev/tty.usbserial-140"

int main(int argc, char* argv[])
{
	int ret = 0;
	printf("uart test\n");
	ret = uart_init(&uart_hd, UART_DEVICE,115200, uart_rec, NULL);
	if (0 != ret)
	{
		printf("uart_init error ret = %d\n", ret);
	}
	while(1)
	{
		sleep(3);
	}

}
