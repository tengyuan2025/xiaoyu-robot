# RK3328 环形麦克风阵列语音交互系统

基于RK3328环形六麦阵列和讯飞AIUI V3极速超拟人链路实现的完整语音交互系统。

## 功能特点

✅ **环形麦克风阵列唤醒** - 支持360°全方位拾音和声源定位
✅ **语音识别** - 实时语音转文字
✅ **语义理解** - 基于AIUI大模型的自然语言理解
✅ **语音合成** - 极速超拟人TTS流式合成
✅ **完整交互流程** - 唤醒 → 录音 → 识别 → 理解 → 合成 → 播放

## 系统架构

```
┌─────────────────┐
│  RK3328环形麦   │ ──唤醒检测──┐
│   6麦克风阵列   │             │
└─────────────────┘             │
                                ▼
┌─────────────────┐      ┌──────────────┐
│  音频录制模块   │ ───► │ 语音交互系统 │
│   PyAudio       │      │              │
└─────────────────┘      └──────────────┘
                                │
                                ▼
                    ┌────────────────────┐
                    │  AIUI V3 云端服务  │
                    │  (WebSocket API)   │
                    └────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
            ┌──────────────┐        ┌──────────────┐
            │  语音识别    │        │  语义理解    │
            │  (IAT)       │        │  (NLP)       │
            └──────────────┘        └──────────────┘
                    │                       │
                    └───────────┬───────────┘
                                ▼
                        ┌──────────────┐
                        │  语音合成    │
                        │  (TTS)       │
                        └──────────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │  音频播放    │
                        └──────────────┘
```

## 快速开始

### 1. 硬件准备

- RK3328 环形六麦降噪板
- USB转TTL串口线
- 3.5mm音频线
- USB声卡（Mac M系列需要）或电脑音频输入

**连接方式：**
```
RK3328 串口 → USB转TTL → 电脑USB口
RK3328 3.5mm音频输出 → 电脑音频输入/USB声卡
RK3328 DC 12V供电
```

### 2. 软件依赖

```bash
# 安装Python依赖
pip3 install pyaudio websocket-client

# macOS安装音频支持
brew install portaudio

# Linux安装音频支持
sudo apt-get install portaudio19-dev python3-pyaudio
```

### 3. AIUI应用配置

1. 访问 [讯飞开放平台控制台](https://console.xfyun.cn/app/myapp)
2. 创建新应用，选择 **AIUI** 服务
3. 获取 `APPID`、`API Key`、`API Secret`
4. 配置应用：
   - 选择 **极速超拟人链路**
   - 启用 **语音识别**、**语义理解**、**语音合成** 能力

### 4. 配置系统

编辑 `voice_interaction.py` 文件，修改以下配置：

```python
# AIUI 配置
AIUI_APPID = "你的appid"
AIUI_API_KEY = "你的api_key"
AIUI_API_SECRET = "你的api_secret"

# TTS发音人（可选）
VCN = "x5_lingxiaoyue_flow"  # 灵小悦流式（默认）
```

或者创建 `config.py` 文件：

```bash
cp config.example.py config.py
# 然后编辑 config.py
```

### 5. 运行系统

```bash
# 基本用法
python3 voice_interaction.py /dev/tty.usbserial-140

# 指定音频设备
python3 voice_interaction.py /dev/tty.usbserial-140 1

# 查看可用音频设备
python3 stream_recorder.py --list
```

## 使用流程

1. **启动系统**
   ```
   python3 voice_interaction.py /dev/tty.usbserial-140
   ```

2. **等待系统初始化**
   ```
   [1/3] 初始化RK3328环形麦克风阵列...
   ✓ RK3328已连接
   ✓ 麦克风阵列已就绪

   [2/3] 连接AIUI云端服务...
   ✓ AIUI服务已连接

   [3/3] 系统就绪

   ======================================================================
   请说唤醒词：小飞小飞
   ======================================================================
   ```

3. **语音交互**
   - 说："**小飞小飞**"（唤醒词）
   - 系统检测到唤醒后自动开始录音（3秒）
   - 说出你的问题，例如："明天天气怎么样"
   - 系统自动识别、理解并语音回复

4. **查看交互结果**
   ```
   🎤 检测到唤醒！
      方向: 120° (波束 2)

   开始录音 (3秒)...
   录音中: [====================] 188/188
   ✓ 录音完成，共 240640 字节

   [识别完成] 明天天气怎么样
   [语义结果] {"intent":"QUERY.weather",...}
   [技能] QUERY.weather
   [回复] 明天多云转晴，温度15-25度
   [TTS] 收到 12800 字节音频

   播放TTS音频...
   ✓ 播放完成
   ```

## 配置说明

### TTS发音人列表

| 发音人代码 | 名称 | 特点 |
|----------|------|------|
| `x5_lingxiaoyue_flow` | 灵小悦流式 | 推荐，极速超拟人 |
| `x5_lingxiaoyue` | 灵小悦 | 标准版 |
| `x5_yefang` | 夜芳 | 温柔女声 |
| `x5_xiaowen` | 小雯 | 活泼女声 |

更多发音人请查看 [AIUI发音人列表文档](https://aiui-doc.xf-yun.com/project-1/doc-93/)

### 唤醒词配置

默认唤醒词：**小飞小飞**

修改唤醒词需要在RK3328设备上配置，参考 `xfmic/change_wakeup_word.py`

### 录音时长调整

在 `voice_interaction.py` 的 `process_voice_interaction()` 方法中修改：

```python
# 录制音频（默认3秒）
audio_data = self._record_audio(duration=3)  # 修改这里
```

## 文件说明

```
mic/
├── voice_interaction.py      # 主程序：完整语音交互系统
├── stream_recorder.py         # 工具：实时音频流录制
├── config.example.py          # 配置示例文件
├── README.md                  # 本文件
└── aiuiv3-demo-master/        # AIUI官方示例代码
    └── websocket/python/
        └── aiui_v3_demo.py    # AIUI WebSocket示例
```

## 故障排除

### 1. 串口连接失败

**问题**：`✗ RK3328连接失败`

**解决**：
- 检查串口路径：`ls /dev/tty.usbserial*`
- 确认TX/RX接线正确
- 检查RK3328是否已通电（DC 12V）
- macOS需要安装CH340驱动

### 2. 音频录制失败

**问题**：`✗ 录音失败`

**解决**：
```bash
# 列出音频设备
python3 stream_recorder.py --list

# 测试音频输入
python3 stream_recorder.py 1
```

- 确认3.5mm音频线已连接
- Mac M系列需要USB声卡
- 检查系统音频输入设置

### 3. AIUI连接失败

**问题**：`✗ AIUI连接超时`

**解决**：
- 检查网络连接
- 确认AIUI配置正确（APPID/API_KEY/API_SECRET）
- 检查应用是否已启用极速超拟人链路
- 查看AIUI控制台应用状态

### 4. 无唤醒响应

**问题**：说"小飞小飞"没有反应

**解决**：
- 检查RK3328是否已激活（日志中应有 `manual_wakeup` 调用）
- 调整说话音量和距离（建议1米内）
- 检查环境噪音
- 查看RK3328串口输出是否有唤醒消息

### 5. TTS无声音

**问题**：识别成功但没有语音回复

**解决**：
- 检查音频输出设备
- 确认系统音量未静音
- 查看日志是否收到TTS数据
- 尝试其他发音人

## 技术文档

- [AIUI V3 API文档](https://aiui-doc.xf-yun.com/project-1/doc-584/)
- [极速超拟人链路](https://aiui-doc.xf-yun.com/project-1/doc-792/)
- [流式合成说明](https://aiui-doc.xf-yun.com/project-1/doc-800/)
- [RK3328硬件协议](../xfmic/README_RK3328.md)

## 开发说明

### 自定义处理逻辑

修改 `_on_ws_message` 方法可以自定义结果处理：

```python
def _on_ws_message(self, ws, message):
    data = json.loads(message)
    payload = data.get('payload', {})

    # 自定义：识别结果处理
    if 'iat' in payload:
        # 你的代码
        pass

    # 自定义：语义结果处理
    if 'nlp' in payload:
        # 你的代码
        pass
```

### 集成到自己的项目

```python
from voice_interaction import VoiceInteractionSystem

# 创建系统
system = VoiceInteractionSystem(
    serial_port='/dev/tty.usbserial-140',
    audio_device_index=1
)

# 初始化
system.init_rk3328()
system.init_aiui_websocket()

# 开始监听
system.start_listening()
```

## 许可证

本项目使用 MIT 许可证。

## 参考资源

- [AIUI开放平台](https://aiui.xfyun.com/)
- [讯飞开放平台](https://www.xfyun.cn/)
- [RK3328降噪板资料](https://www.iflytek.com/)

## 更新日志

### v1.0.0 (2024-12-04)
- ✅ 完整的语音交互流程实现
- ✅ RK3328环形麦克风阵列集成
- ✅ AIUI V3极速超拟人链路接入
- ✅ 实时语音识别和语义理解
- ✅ 流式TTS合成和播放
- ✅ 唤醒词检测和声源定位
