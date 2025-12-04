#!/usr/bin/env python3
"""
基于RK3328环形麦克风阵列的完整语音交互系统
集成AIUI V3极速超拟人链路实现语音识别、语义理解和语音合成
"""

import sys
import os
import time
import wave
import json
import base64
import hashlib
import hmac
from datetime import datetime
from time import mktime
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time
import _thread as thread
import traceback

import websocket
import pyaudio

# 添加xfmic目录到路径以导入RK3328控制器
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'xfmic'))
from rk3328_controller import RK3328Controller


# ============= AIUI 配置 =============
# 请在 https://console.xfyun.cn/app/myapp 创建应用获取以下参数
AIUI_APPID = "58b5befd"
AIUI_API_KEY = "8499b910aee15c75718c936157cf085b"
AIUI_API_SECRET = "OWE2OWY1ZWQ3NmEwMTNhOTEyNmZmODUz"

# AIUI WebSocket 接口地址
AIUI_URL = "wss://aiui.xf-yun.com/v3/aiint/sos"

# 设备序列号（可自定义）
DEVICE_SN = "rk3328-mic-array"

# 场景配置（极速超拟人链路）
SCENE = "main_box"

# TTS发音人（极速超拟人发音人）
# 可选：x5_lingxiaoyue_flow, x5_lingxiaoyue, x5_yefang 等
VCN = "x5_lingxiaoyue_flow"

# 音频参数（RK3328输出格式）
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
CHUNK_SIZE = 1280  # 每40ms发送1280字节（16000*2/1000*40）
FRAME_INTERVAL = 0.04  # 40ms


class VoiceInteractionSystem:
    """语音交互系统主类"""

    def __init__(self, serial_port, audio_device_index=None):
        """初始化语音交互系统

        Args:
            serial_port: RK3328串口设备路径
            audio_device_index: 音频输入设备索引
        """
        self.serial_port = serial_port
        self.audio_device_index = audio_device_index

        # RK3328控制器
        self.rk3328 = None

        # PyAudio
        self.audio = pyaudio.PyAudio()
        self.audio_stream = None

        # WebSocket连接
        self.ws = None
        self.ws_connected = False

        # 状态控制
        self.is_recording = False
        self.is_listening = False
        self.session_id = None

        # TTS音频缓冲
        self.tts_audio_buffer = []

        print("=" * 70)
        print("RK3328 环形麦克风阵列语音交互系统")
        print("基于AIUI V3 极速超拟人链路")
        print("=" * 70)

    def init_rk3328(self):
        """初始化RK3328环形麦克风阵列"""
        print("\n[1/3] 初始化RK3328环形麦克风阵列...")

        self.rk3328 = RK3328Controller(self.serial_port)

        if not self.rk3328.connect():
            print("✗ RK3328连接失败")
            return False

        print("✓ RK3328已连接")

        # 激活麦克风阵列
        print("  激活麦克风阵列...")
        self.rk3328.manual_wakeup(beam=0)
        time.sleep(0.5)

        print("✓ 麦克风阵列已就绪")
        return True

    def init_aiui_websocket(self):
        """初始化AIUI WebSocket连接"""
        print("\n[2/3] 连接AIUI云端服务...")

        # 生成鉴权URL
        handshake_url = self._generate_auth_url()

        # 创建WebSocket连接
        self.ws = websocket.WebSocketApp(
            handshake_url,
            on_open=self._on_ws_open,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close
        )

        # 在后台线程运行WebSocket
        thread.start_new_thread(self.ws.run_forever, ())

        # 等待连接建立
        timeout = 10
        start_time = time.time()
        while not self.ws_connected and time.time() - start_time < timeout:
            time.sleep(0.1)

        if self.ws_connected:
            print("✓ AIUI服务已连接")
            return True
        else:
            print("✗ AIUI连接超时")
            return False

    def _generate_auth_url(self):
        """生成AIUI鉴权URL"""
        host = urlparse(AIUI_URL).netloc
        path = urlparse(AIUI_URL).path

        # 生成RFC1123格式时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接签名原文
        signature_origin = f"host: {host}\n"
        signature_origin += f"date: {date}\n"
        signature_origin += f"GET {path} HTTP/1.1"

        # HMAC-SHA256加密
        signature_sha = hmac.new(
            AIUI_API_SECRET.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode('utf-8')

        # 生成authorization
        authorization_origin = f'api_key="{AIUI_API_KEY}", algorithm="hmac-sha256", ' \
                                f'headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')

        # 拼接URL参数
        params = {
            "host": host,
            "date": date,
            "authorization": authorization
        }

        return AIUI_URL + '?' + urlencode(params)

    def _on_ws_open(self, ws):
        """WebSocket连接建立"""
        self.ws_connected = True
        print("  WebSocket连接已建立")

    def _on_ws_message(self, ws, message):
        """接收AIUI返回消息"""
        try:
            data = json.loads(message)
            header = data.get('header', {})
            payload = data.get('payload', {})

            # 检查错误
            code = header.get('code', 0)
            if code != 0:
                print(f"\n✗ AIUI错误: {code}, {json.dumps(data, ensure_ascii=False)}")
                return

            # 保存session ID
            if 'sid' in header:
                self.session_id = header['sid']

            # 调试：显示收到的消息类型
            msg_types = list(payload.keys())
            if msg_types:
                print(f"[AIUI响应] 包含: {', '.join(msg_types)}")

            # 解析各类结果
            self._parse_event(payload)
            self._parse_iat(payload)
            self._parse_nlp(payload)
            self._parse_tts(payload)

            # 结束标志
            if header.get('status') == 2:
                print("\n✓ 交互完成")
                self._play_tts_audio()

        except Exception as e:
            print(f"\n✗ 解析消息失败: {e}")
            traceback.print_exc()

    def _parse_event(self, payload):
        """解析事件结果"""
        if 'event' in payload:
            event_text_b64 = payload['event']['text']
            event_text = base64.b64decode(event_text_b64).decode('utf-8')
            print(f"\n[事件] {event_text}")

    def _parse_iat(self, payload):
        """解析语音识别结果"""
        if 'iat' in payload:
            iat_json = payload['iat']
            iat_text_b64 = iat_json['text']
            iat_text = base64.b64decode(iat_text_b64).decode('utf-8')

            # 提取识别文本
            result_text = self._extract_iat_text(iat_text)
            status = iat_json.get('status', 0)

            if status == 2:
                print(f"\n[识别完成] {result_text}")
            else:
                print(f"[识别中] {result_text}", end='\r')

    def _extract_iat_text(self, iat_json_str):
        """从IAT结果中提取文本"""
        try:
            iat_data = json.loads(iat_json_str)
            text = ""
            for ws in iat_data.get('text', {}).get('ws', []):
                for cw in ws.get('cw', []):
                    text += cw.get('w', '')
            return text
        except:
            return iat_json_str

    def _parse_nlp(self, payload):
        """解析语义理解结果"""
        if 'nlp' in payload:
            nlp_json = payload['nlp']
            nlp_text_b64 = nlp_json['text']
            nlp_text = base64.b64decode(nlp_text_b64).decode('utf-8')
            print(f"\n[语义结果]\n{nlp_text}")

        # 技能结果
        if 'cbm_semantic' in payload:
            semantic_json = payload['cbm_semantic']
            semantic_text_b64 = semantic_json['text']
            semantic_text = base64.b64decode(semantic_text_b64).decode('utf-8')
            semantic_data = json.loads(semantic_text)

            if semantic_data.get('rc') == 0:
                answer = semantic_data.get('answer', {}).get('text', '')
                category = semantic_data.get('category', '')
                print(f"[技能] {category}")
                print(f"[回复] {answer}")

    def _parse_tts(self, payload):
        """解析TTS合成音频"""
        if 'tts' in payload:
            audio_b64 = payload['tts'].get('audio')
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                self.tts_audio_buffer.append(audio_bytes)
                print(f"[TTS] 收到 {len(audio_bytes)} 字节音频")

    def _on_ws_error(self, ws, error):
        """WebSocket错误"""
        print(f"\n✗ WebSocket错误: {error}")

    def _on_ws_close(self, ws, close_status_code, close_msg):
        """WebSocket关闭"""
        self.ws_connected = False
        print(f"\n  WebSocket连接已关闭 (code: {close_status_code})")

    def start_listening(self):
        """开始监听唤醒事件"""
        print("\n[3/3] 系统就绪")
        print("\n" + "=" * 70)
        print("请说唤醒词：小飞小飞")
        print("=" * 70)

        self.is_listening = True

        try:
            while self.is_listening:
                # 读取RK3328唤醒消息
                msg = self.rk3328.read_device_message(timeout=1)

                # 调试：显示收到的所有消息
                if msg:
                    print(f"\n[调试] 收到消息: {json.dumps(msg, ensure_ascii=False)}")

                # 检查是否是唤醒事件
                # RK3328发送的唤醒事件类型是 "aiui_event"
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

                        # 开始录音并发送到AIUI
                        self.process_voice_interaction()

                        print(f"\n{'='*70}")
                        print("继续等待唤醒...")
                        print(f"{'='*70}")

        except KeyboardInterrupt:
            print("\n\n用户中断，退出系统")

    def process_voice_interaction(self):
        """处理一次完整的语音交互"""
        print("\n开始录音 (3秒)...")

        # 录制音频
        audio_data = self._record_audio(duration=3)

        if not audio_data:
            print("✗ 录音失败")
            return

        print(f"✓ 录音完成，共 {len(audio_data)} 字节")
        print("\n发送到AIUI进行识别...")

        # 清空TTS缓冲
        self.tts_audio_buffer.clear()

        # 分帧发送音频到AIUI
        self._send_audio_to_aiui(audio_data)

        # 等待结果
        print("等待识别和语义分析结果...")
        time.sleep(2)

    def _record_audio(self, duration=3):
        """录制音频

        Args:
            duration: 录音时长（秒）

        Returns:
            bytes: 音频数据
        """
        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=self.audio_device_index,
                frames_per_buffer=CHUNK_SIZE
            )

            frames = []
            num_chunks = int(SAMPLE_RATE / CHUNK_SIZE * duration)

            for i in range(num_chunks):
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                frames.append(data)
                # 显示进度
                progress = int((i + 1) / num_chunks * 20)
                print(f"\r录音中: [{'='*progress}{' '*(20-progress)}] {i+1}/{num_chunks}", end='')

            print()  # 换行
            stream.stop_stream()
            stream.close()

            return b''.join(frames)

        except Exception as e:
            print(f"\n录音失败: {e}")
            return None

    def _send_audio_to_aiui(self, audio_data):
        """分帧发送音频到AIUI

        Args:
            audio_data: 完整音频数据
        """
        if not self.ws_connected:
            print("✗ WebSocket未连接")
            return

        total_frames = len(audio_data) // CHUNK_SIZE
        offset = 0

        print(f"\n开始向AIUI发送音频...")
        print(f"总帧数: {total_frames}, 每帧: {CHUNK_SIZE} 字节")

        for i in range(total_frames):
            # 提取音频帧
            chunk = audio_data[offset:offset + CHUNK_SIZE]
            offset += CHUNK_SIZE

            # 确定状态：0=首帧，1=中间帧，2=尾帧
            if i == 0:
                status = 0
                status_name = "首帧"
            elif i == total_frames - 1:
                status = 2
                status_name = "尾帧"
            else:
                status = 1
                status_name = "中间帧"

            # 构造AIUI请求
            request = self._build_audio_request(chunk, status)

            # 发送
            self.ws.send(json.dumps(request))

            # 显示发送进度
            if i == 0 or i == total_frames - 1 or i % 20 == 0:
                print(f"[WebSocket] 发送 {status_name} ({i+1}/{total_frames})")

            # 控制发送速率
            time.sleep(FRAME_INTERVAL)

        print(f"✓ 已发送 {total_frames} 帧音频到AIUI云端")

    def _build_audio_request(self, audio_chunk, status):
        """构造AIUI音频请求

        Args:
            audio_chunk: 音频数据块
            status: 帧状态 (0=首帧, 1=中间帧, 2=尾帧)

        Returns:
            dict: AIUI请求结构
        """
        return {
            "header": {
                "appid": AIUI_APPID,
                "sn": DEVICE_SN,
                "stmid": f"rk3328-{int(time.time())}",
                "status": status,
                "scene": SCENE,
                "interact_mode": "continuous"  # 连续交互模式
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
                "tts": {
                    "vcn": VCN,  # 极速超拟人发音人
                    "tts": {
                        "channels": 1,
                        "bit_depth": 16,
                        "sample_rate": 16000,
                        "encoding": "raw"  # PCM格式
                    }
                }
            },
            "payload": {
                "audio": {
                    "encoding": "raw",
                    "sample_rate": SAMPLE_RATE,
                    "channels": CHANNELS,
                    "bit_depth": 16,
                    "status": status,
                    "audio": base64.b64encode(audio_chunk).decode()
                }
            }
        }

    def _play_tts_audio(self):
        """播放TTS合成的音频"""
        if not self.tts_audio_buffer:
            return

        print(f"\n播放TTS音频...")

        try:
            # 合并所有音频数据
            audio_data = b''.join(self.tts_audio_buffer)

            # 播放
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

    def cleanup(self):
        """清理资源"""
        print("\n正在清理资源...")

        if self.rk3328:
            self.rk3328.close()

        if self.ws:
            self.ws.close()

        if self.audio:
            self.audio.terminate()

        print("✓ 资源已释放")


def main():
    """主程序"""
    # 检查AIUI配置
    if AIUI_APPID == "your_appid_here":
        print("=" * 70)
        print("错误：请先配置AIUI参数")
        print("=" * 70)
        print("\n请修改以下配置：")
        print("  AIUI_APPID")
        print("  AIUI_API_KEY")
        print("  AIUI_API_SECRET")
        print("\n在 https://console.xfyun.cn/app/myapp 创建应用获取")
        return

    # 从命令行参数获取配置
    if len(sys.argv) < 2:
        print("用法:")
        print(f"  {sys.argv[0]} <串口设备> [音频设备索引]")
        print("\n示例:")
        print(f"  {sys.argv[0]} /dev/tty.usbserial-140")
        print(f"  {sys.argv[0]} /dev/tty.usbserial-140 1")
        return

    serial_port = sys.argv[1]
    audio_device = int(sys.argv[2]) if len(sys.argv) > 2 else None

    # 创建语音交互系统
    system = VoiceInteractionSystem(serial_port, audio_device)

    try:
        # 初始化各个组件
        if not system.init_rk3328():
            return

        if not system.init_aiui_websocket():
            return

        # 开始监听
        system.start_listening()

    except Exception as e:
        print(f"\n系统错误: {e}")
        traceback.print_exc()

    finally:
        system.cleanup()
        print("\n再见！")


if __name__ == "__main__":
    main()
