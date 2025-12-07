import _thread as thread
import base64
import datetime
import hashlib
import hmac
import json
import traceback
from urllib.parse import urlparse
import time
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
import sys
import os

import websocket
import pyaudio

# 添加xfmic目录到路径以导入RK3328控制器
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'xfmic'))
from rk3328_controller import RK3328Controller

## 修改应用应用配置和文件地址后直接执行即可

# 请求地址
url = "wss://aiui.xf-yun.com/v3/aiint/sos"

# 应用配置
appid = "58b5befd"
api_key = "8499b910aee15c75718c936157cf085b"
api_secret = "OWE2OWY1ZWQ3NmEwMTNhOTEyNmZmODUz"

sn="rk3328-test"

# 场景
scene = "main_box"

vcn = "x2_xiaofeng"  # 通用发音人，更稳定
# vcn = "x5_lingxiaoyue_flow"  # 流式发音人（可能需要特殊配置）

# 请求类型用来设置文本请求还是音频请求，text/audio
data_type = 'audio'  # 使用音频模式

## 音频请求需要先设置audio_path
## 当前音频格式默认pcm 16k 16bit，修改音频格式需要修改audioReq中的payload中音频相关参数

# 音频请求上传的音频文件路径
audio_path = "/Users/yushuangyang/workspace/xiaoyu-robot/mic/test.pcm"  # 使用刚录制的音频

# 文本请求输入的文本
question = "明天天气怎么样"

# 下面两个参数配合音频采样率设置，16k 16bit的音频： 每 40毫秒 发送 1280字节
# 每帧音频数据大小，单位字节
frame_size = 1280
# 每帧音频发送间隔
sleep_inetrval = 0.04

class AIUIV3WsClient(object):
    # 初始化
    def __init__(self, audio_device_index=None):
        self.handshake = self.assemble_auth_url(url)

        # PyAudio实例
        self.audio = pyaudio.PyAudio()
        self.audio_device = audio_device_index

        # TTS音频缓冲
        self.tts_buffer = []

        # 交互状态
        self.is_busy = False
        self.ws_connected = False

    # 生成握手url
    def assemble_auth_url(self, base_url):
        host = urlparse(base_url).netloc
        path = urlparse(base_url).path
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + path + " HTTP/1.1"

        # 进行hmac-sha256进行加密
        print(signature_origin)
        signature_sha = hmac.new(api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'

        print('get authorization_origin:', authorization_origin)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        # 将请求的鉴权参数组合为字典
        v = {
            "host": host,
            "date": date,
            "authorization": authorization,
        }
        # 拼接鉴权参数，生成url
        url = base_url + '?' + urlencode(v)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        return url

    def on_open(self, ws):
        # 连接建立成功
        print("✓ AIUI WebSocket已连接")
        self.ws_connected = True

    def start_recording(self):
        """开始一次录音交互"""
        if self.is_busy:
            print("⚠️  正在交互中，跳过本次唤醒")
            return

        if not self.ws_connected:
            print("✗ WebSocket未连接")
            return

        self.is_busy = True
        self.tts_buffer.clear()

        print("\n开始录音并实时上传（5秒）...")
        print("请说话...")

        # 启动录音线程
        thread.start_new_thread(self.audio_req, ())

    def text_req(self):
        # 文本请求status固定为3，interact_mode固定为oneshot
        aiui_data = {
            "header": {
                "appid": appid,
                "sn": sn,
                "stmid": "text-1",
                "status": 3,
                "scene": scene,
                "interact_mode": "oneshot"
            },
            "parameter": {
                "nlp": {
                    "nlp": {
                        "compress": "raw",
                        "format": "json",
                        "encoding": "utf8"
                    },
                    "new_session": True
                },
                # 合成参数
                "tts": {
                    # 发音人
                    "vcn": vcn,
                    "tts": {
                        "channels": 1,
                        "bit_depth": 16,
                        "sample_rate": 16000,
                        "encoding": "raw"
                    }
                }
            },
            "payload": {
                "text": {
                    "compress": "raw",
                    "format": "plain",
                    "text": base64.b64encode(question.encode('utf-8')).decode('utf-8'),
                    "encoding": "utf8",
                    "status": 3
                }
            }
        }
        data = json.dumps(aiui_data)
        print('text request data:', data)
        self.ws.send(data)

    def audio_req(self):
        """从麦克风实时录音并流式上传"""
        try:
            # 打开音频流
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=self.audio_device,
                frames_per_buffer=frame_size
            )

            # 录音时长（秒）
            duration = 5
            num_chunks = int(16000 / frame_size * duration)

            print(f"录音中...")

            for i in range(num_chunks):
                # 从麦克风读取一帧音频
                audio_chunk = stream.read(frame_size, exception_on_overflow=False)

                # 确定状态：0=首帧，1=中间帧，2=尾帧
                if i == 0:
                    status = 0
                elif i == num_chunks - 1:
                    status = 2
                else:
                    status = 1

                # 构造请求并发送
                req = self.genAudioReq(audio_chunk, status)
                self.ws.send(req)

                # 显示进度
                progress = int((i + 1) / num_chunks * 30)
                print(f"\r[{'='*progress}{' '*(30-progress)}] {i+1}/{num_chunks}", end='', flush=True)

                # 注意：不需要sleep，stream.read()本身会阻塞约40ms

            print()
            print("✓ 录音完成，等待识别结果...")

            stream.stop_stream()
            stream.close()

        except Exception as e:
            print(f"\n✗ 录音失败: {e}")
            traceback.print_exc()
            self.is_busy = False

    def genAudioReq(self, data, status):
        # 构造pcm音频请求参数
        aiui_data = {
            "header": {
                "appid": appid,
                "sn": sn,
                "stmid": "audio-1",
                "status": status,
                "scene": scene,
                "interact_mode": "continuous"
            },
            "parameter": {
                "nlp": {
                    "nlp": {
                        "compress": "raw",
                        "format": "json",
                        "encoding": "utf8"
                    },
                    "new_session": True
                },
                # 合成参数
                "tts": {
                    # 发音人
                    "vcn": vcn,
                    "tts": {
                        "channels": 1,
                        "bit_depth": 16,
                        "sample_rate": 16000,
                        "encoding": "raw"
                    }
                }
            },
            "payload": {
                "audio": {
                    "encoding": "raw",
                    "sample_rate": 16000,
                    "channels": 1,
                    "bit_depth": 16,
                    "status": status,
                    "audio": base64.b64encode(data).decode(),
                }
            }
        }
        return json.dumps(aiui_data)

    # 收到websocket消息的处理
    def on_message(self, ws, message):
        try:
            data = json.loads(message)

            # print('原始结果:', message)  # 调试用，已禁用
            header = data['header']
            code = header['code']
            # 结果解析
            if code != 0:
                print('请求错误：', code, json.dumps(data, ensure_ascii=False))
                ws.close()
            sid = header.get('sid', "sid")
            payload = data.get('payload', {})
            parameter = data.get('parameter', {})
            if 'event' in payload:
                # 事件结果
                event_json = payload['event']
                event_text_bs64 = event_json['text']
                event_text = base64.b64decode(event_text_bs64).decode('utf-8')
                print("事件，", event_text)
            if 'iat' in payload:
                # 识别结果
                iat_json = payload['iat']
                iat_text_bs64 = iat_json['text']
                iat_text = base64.b64decode(iat_text_bs64).decode('utf-8')
                result_text = self.parse_iat_result(iat_text)
                status_val = iat_json['status']

                if status_val == 2:
                    print(f"\n✓ [识别完成] {result_text}")
                else:
                    print(f"  [实时识别] {result_text}...", end='\r')
            if 'cbm_tidy' in payload:
                # 语义规整结果（历史改写），意图拆分
                cbm_tidy_json = payload['cbm_tidy']
                cbm_tidy_text_bs64 = cbm_tidy_json['text']
                cbm_tidy_text = base64.b64decode(cbm_tidy_text_bs64).decode('utf-8')
                cbm_tidy_json = json.loads(cbm_tidy_text)
                print("语义规整结果：")
                intents = cbm_tidy_json['intent']
                for intent in intents:
                    print("  intent index：", intent['index'], "，意图语料：", intent['value'])
            if 'cbm_intent_domain' in payload:
                # 意图拆分后的落域结果
                cbm_intent_domain_json = payload['cbm_intent_domain']
                cbm_intent_domain_text_bs64 = cbm_intent_domain_json['text']
                cbm_intent_domain_text = base64.b64decode(cbm_intent_domain_text_bs64).decode('utf-8')
                index = self.get_intent_index(parameter, "cbm_intent_domain")
                print("intent index：", index, "，落域结果：", cbm_intent_domain_text)
            if 'cbm_semantic' in payload:
                # 技能结果
                cbm_semantic_json = payload['cbm_semantic']
                cbm_semantic_text_bs64 = cbm_semantic_json['text']
                cbm_semantic_text = base64.b64decode(cbm_semantic_text_bs64).decode('utf-8')
                cbm_semantic_json = json.loads(cbm_semantic_text)
                index = self.get_intent_index(parameter, "cbm_semantic")
                if cbm_semantic_json['rc'] != 0:
                    print("intent index：", index, "，技能结果：说法：", cbm_semantic_json['text'], "，", cbm_semantic_text)
                else:
                    print("intent index：", index, "，技能结果：说法：", cbm_semantic_json['text'], "，命中技能：", cbm_semantic_json['category'], "，回复：", cbm_semantic_json['answer']['text'])
            if 'nlp' in payload:
                # 语义结果，经过大模型润色的最终结果
                nlp_json = payload['nlp']
                nlp_text_bs64 = nlp_json['text']
                nlp_text = base64.b64decode(nlp_text_bs64).decode('utf-8')
                nlp_status = nlp_json['status']

                if nlp_status == 2:
                    print(f"\n[语义结果] {nlp_text}")
                else:
                    print(f"  [语义流式] {nlp_text}", end='')

            if 'tts' in payload:
                # TTS音频数据
                audioData = payload['tts']['audio']
                if audioData != None:
                    audioBytes = base64.b64decode(audioData)
                    self.tts_buffer.append(audioBytes)
                    print(f"  [TTS] 收到 {len(audioBytes)} 字节")

            if 'status' in header and header['status'] == 2:
                # 本轮交互结束
                print("\n✓ 交互完成")

                # 播放TTS音频
                if self.tts_buffer:
                    self.play_tts()
                else:
                    print("\n⚠️  警告：未收到TTS音频数据")
                    print("   可能原因：")
                    print("   1. AIUI应用未启用TTS合成")
                    print("   2. 极速超拟人链路未配置语音输出")
                    print("   3. TTS服务未开通或次数不足")
                    print("   请登录 https://aiui.xfyun.cn/ 检查配置")

                # 重置状态，准备下次唤醒
                self.is_busy = False
                print("\n" + "="*70)
                print("等待下次唤醒...")
                print("="*70)
        except Exception as e:
            traceback.print_exc()
            pass

    def parse_iat_result(self, iat_res):
        iat_text = ""
        iat_res_json = json.loads(iat_res)
        for cw in iat_res_json['text']['ws']:
            for cw_item in cw["cw"]:
                iat_text += cw_item['w']

        return iat_text

    def get_intent_index(self, parameter, key):
        if key in parameter:
            return parameter[key]['loc']['intent']

        return "-"

    def get_suffix(self, encoding):
        if encoding == 'raw':
            return 'pcm'
        if encoding == 'lame':
            return 'mp3'

        return 'unknow'

    def play_tts(self):
        """播放TTS音频"""
        try:
            audio_data = b''.join(self.tts_buffer)

            if len(audio_data) == 0:
                return

            print(f"\n播放TTS音频（{len(audio_data)} 字节）...")

            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                output=True
            )

            stream.write(audio_data)
            stream.stop_stream()
            stream.close()

            print("✓ 播放完成")

        except Exception as e:
            print(f"✗ 播放失败: {e}")

    def on_error(self, ws, error):
        print("### connection error: ", str(error))
        ws.close()

    def on_close(self, ws, close_status_code, close_msg):
        print("### connection is closed ###, cloce code:", close_status_code)

    def start(self):
        self.ws = websocket.WebSocketApp(
            self.handshake,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()

if __name__ == "__main__":
    print("=" * 70)
    print("RK3328 + AIUI V3 语音交互系统")
    print("=" * 70)

    # 从命令行参数获取配置
    if len(sys.argv) < 2:
        print("\n用法:")
        print(f"  {sys.argv[0]} <串口设备> [音频设备索引]")
        print("\n示例:")
        print(f"  {sys.argv[0]} /dev/tty.usbserial-140")
        print(f"  {sys.argv[0]} /dev/tty.usbserial-140 1")
        sys.exit(1)

    serial_port = sys.argv[1]
    audio_device = int(sys.argv[2]) if len(sys.argv) > 2 else None

    # 1. 初始化RK3328环形麦克风阵列
    print("\n[1/3] 初始化RK3328环形麦克风阵列...")
    rk3328 = RK3328Controller(serial_port)

    if not rk3328.connect():
        print("✗ RK3328连接失败")
        sys.exit(1)

    print("✓ RK3328已连接")

    # 激活麦克风阵列
    print("  激活麦克风阵列...")
    rk3328.manual_wakeup(beam=0)
    time.sleep(0.5)
    print("✓ 麦克风阵列已就绪")

    # 2. 初始化AIUI客户端
    print("\n[2/3] 连接AIUI云端服务...")
    client = AIUIV3WsClient(audio_device_index=audio_device)

    # 在后台线程启动WebSocket连接
    thread.start_new_thread(client.start, ())

    # 等待WebSocket连接建立
    timeout = 10
    start_time = time.time()
    while not client.ws_connected and time.time() - start_time < timeout:
        time.sleep(0.1)

    if not client.ws_connected:
        print("✗ AIUI连接超时")
        sys.exit(1)

    # 3. 主循环：监听唤醒事件
    print("\n[3/3] 系统就绪")
    print("\n" + "=" * 70)
    print("请说唤醒词：小飞小飞")
    print("=" * 70)

    try:
        while True:
            # 读取RK3328唤醒消息
            msg = rk3328.read_device_message(timeout=1)

            if msg and msg.get('type') == 'aiui_event':
                content = msg.get('content', {})

                # 检查是否是唤醒事件（eventType == 4）
                if content.get('eventType') == 4:
                    # 从info字段解析详细信息
                    try:
                        info_str = content.get('info', '{}')
                        info = json.loads(info_str)
                        ivw = info.get('ivw', {})

                        angle = ivw.get('angle', 0)
                        beam = ivw.get('beam', 0)
                    except:
                        angle = 0
                        beam = 0

                    print(f"\n{'='*70}")
                    print(f"🎤 检测到唤醒！")
                    print(f"   方向: {angle}° (波束 {beam})")
                    print(f"{'='*70}")

                    # 触发录音
                    client.start_recording()

    except KeyboardInterrupt:
        print("\n\n用户中断，退出系统")

    finally:
        rk3328.close()
        client.audio.terminate()
        print("\n再见！")
