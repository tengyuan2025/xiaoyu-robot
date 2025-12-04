"""
AIUI配置示例文件
复制此文件为 config.py 并填入你的AIUI应用信息
"""

# AIUI 应用配置
# 在 https://console.xfyun.cn/app/myapp 创建应用获取
AIUI_APPID = "your_appid_here"
AIUI_API_KEY = "your_api_key_here"
AIUI_API_SECRET = "your_api_secret_here"

# 设备序列号（可自定义）
DEVICE_SN = "rk3328-mic-array"

# 场景配置
SCENE = "main_box"

# TTS发音人（极速超拟人发音人）
# 可选发音人列表：
# - x5_lingxiaoyue_flow: 灵小悦流式（推荐）
# - x5_lingxiaoyue: 灵小悦
# - x5_yefang: 夜芳
# - x5_xiaowen: 小雯
# 更多发音人请查看文档
VCN = "x5_lingxiaoyue_flow"

# 音频参数（RK3328默认配置，通常不需要修改）
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2
CHUNK_SIZE = 1280
FRAME_INTERVAL = 0.04
