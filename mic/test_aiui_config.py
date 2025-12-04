#!/usr/bin/env python3
"""
测试AIUI配置是否正确
"""

import sys
import hashlib
import hmac
import base64
from datetime import datetime
from time import mktime
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

# 从voice_interaction.py导入配置
sys.path.insert(0, '.')

try:
    # 尝试从config.py导入
    from config import AIUI_APPID, AIUI_API_KEY, AIUI_API_SECRET, AIUI_URL
except ImportError:
    # 从voice_interaction.py导入
    import voice_interaction
    AIUI_APPID = voice_interaction.AIUI_APPID
    AIUI_API_KEY = voice_interaction.AIUI_API_KEY
    AIUI_API_SECRET = voice_interaction.AIUI_API_SECRET
    AIUI_URL = voice_interaction.AIUI_URL


def test_config():
    """测试AIUI配置"""
    print("=" * 70)
    print("AIUI 配置测试")
    print("=" * 70)
    print()

    # 检查配置
    print("检查配置参数...")

    if AIUI_APPID == "your_appid_here":
        print("✗ APPID 未配置")
        print("  请修改 voice_interaction.py 或创建 config.py")
        return False

    print(f"✓ APPID: {AIUI_APPID}")
    print(f"✓ API_KEY: {AIUI_API_KEY[:10]}...")
    print(f"✓ API_SECRET: {AIUI_API_SECRET[:10]}...")
    print()

    # 生成鉴权URL
    print("生成鉴权URL...")
    try:
        auth_url = generate_auth_url(AIUI_URL)
        print("✓ 鉴权URL生成成功")
        print()
        print("URL长度:", len(auth_url))
        print("URL前100字符:", auth_url[:100] + "...")
        print()

        # 测试WebSocket连接
        print("测试WebSocket连接...")
        print("提示：需要安装 websocket-client 库")
        print("  pip3 install websocket-client")
        print()

        try:
            import websocket

            connected = [False]
            error_msg = [None]

            def on_open(ws):
                print("✓ WebSocket连接成功！")
                connected[0] = True
                ws.close()

            def on_error(ws, error):
                error_msg[0] = str(error)

            def on_close(ws, code, msg):
                if not connected[0] and error_msg[0]:
                    print(f"✗ 连接失败: {error_msg[0]}")

            ws = websocket.WebSocketApp(
                auth_url,
                on_open=on_open,
                on_error=on_error,
                on_close=on_close
            )

            ws.run_forever(timeout=5)

            if connected[0]:
                print()
                print("=" * 70)
                print("✓ AIUI配置正确，可以正常使用！")
                print("=" * 70)
                return True
            else:
                print()
                print("=" * 70)
                print("✗ WebSocket连接失败")
                print("=" * 70)
                print()
                print("可能的原因：")
                print("  1. APPID/API_KEY/API_SECRET 不正确")
                print("  2. 网络连接问题")
                print("  3. AIUI应用未启用或已过期")
                print()
                print("请访问 https://console.xfyun.cn/app/myapp 检查应用状态")
                return False

        except ImportError:
            print("⚠️  未安装 websocket-client，跳过连接测试")
            print("  安装方法: pip3 install websocket-client")
            print()
            print("=" * 70)
            print("✓ 配置格式正确（未测试连接）")
            print("=" * 70)
            return True

    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_auth_url(base_url):
    """生成AIUI鉴权URL"""
    host = urlparse(base_url).netloc
    path = urlparse(base_url).path

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

    return base_url + '?' + urlencode(params)


if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)
