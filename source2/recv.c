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
	if(buf[2] == 0xff){
		//对确认消息先不处理
		return;
	}

	int index;
	ack_buf[0] = 0xA5;
	ack_buf[1] = 0x01;
	ack_buf[2] = 0xff; //0xff是确认消息类型
	ack_buf[3] = 0x04;
	ack_buf[4] = 0x00;
	ack_buf[5] = buf[5]; // 消息ID同要收到消息ID相同
	ack_buf[6] = buf[6];
	ack_buf[7] = 0xA5;
	ack_buf[8] = 0x00;
	ack_buf[9] = 0x00;
	ack_buf[10] = 0x00;

	//计算校检码
	char check_code = 0;
	for(index = 0; index <= 10; index++){
		check_code += ack_buf[index];
	}
	check_code = ~check_code + 1;
	ack_buf[11] = check_code;

	//发送确认消息
	uart_send(uart_hd, ack_buf, 12);

	printf("recv ");
	for(index = 0; index < len; index++){
		printf("%02X ", buf[index]);
	}

	printf("\n");
	if (buf[2] == 4) {
		int outLength = 0;
		char* outData = NULL;
		gzipDecompress(buf + 7, len-8, &outData, &outLength);
		if (outData) {
			printf("%s", outData);
			free(outData);
		}
		printf("\n");
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
				memset(big_buf, big_buf_len, 0);
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
