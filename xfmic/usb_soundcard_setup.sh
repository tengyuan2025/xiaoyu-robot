#!/bin/bash
# USB声卡配置脚本 - Linux

echo "================================"
echo "USB声卡设备检测和配置"
echo "================================"

# 1. 检测USB声卡是否连接
echo -e "\n1. 检测USB设备："
lsusb | grep -i "audio\|sound"

# 2. 列出所有音频录音设备
echo -e "\n2. ALSA音频设备列表："
arecord -l

# 3. 列出PyAudio可用设备
echo -e "\n3. PyAudio设备列表："
python3 << 'EOF'
import pyaudio
p = pyaudio.PyAudio()
print("\n可用的音频输入设备：")
print("="*60)
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f"[{i}] {info['name']}")
        print(f"    采样率: {int(info['defaultSampleRate'])} Hz")
        print(f"    输入通道: {info['maxInputChannels']}")
        print()
p.terminate()
EOF

# 4. 测试音频录制
echo -e "\n4. 测试录音（请输入设备编号，或按Ctrl+C跳过）："
read -p "请输入设备编号: " device_num

if [ ! -z "$device_num" ]; then
    echo "录音5秒，请对RK3328说话..."
    arecord -D hw:$device_num,0 -f S16_LE -r 16000 -c 1 -d 5 test_usb_soundcard.wav
    echo "录音完成，播放录音内容..."
    aplay test_usb_soundcard.wav
    echo "录音文件保存为: test_usb_soundcard.wav"
fi

echo -e "\n配置完成！"
