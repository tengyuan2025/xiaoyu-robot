package com.iflytek.aiui.websocketv3demo;

import java.io.File;
import java.io.RandomAccessFile;
import java.net.URI;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.concurrent.CountDownLatch;

import org.java_websocket.client.WebSocketClient;

import com.alibaba.fastjson.JSONObject;
import com.iflytek.aiui.websocketv3demo.util.CommonUtil;
import com.iflytek.aiui.websocketv3demo.util.IflytekAuthUtil;
import com.iflytek.aiui.websocketv3demo.ws.IflytekAIUIV3WebSocketClient;

/**
 * 急速交互API音频请求demo
 * 
 * 配置好应用信息和音频文件地址直接执行
 * 
 */
@SuppressWarnings("unused")
public class AIUIV3APIAudioReqDemo {

    // 接口地址
    private static final String BASE_URL = "wss://aiui.xf-yun.com/v3/aiint/sos";

    // 应用配置，通过AIUI开放平台获取
    private static final String APPID = "";
    private static final String APIKEY = "";
    private static final String APISECRET = "";

    // 音频请求上传的音频文件路径
    private static final String FILE_PATH = "";
    // 合成结果音频保存目录
    private static final String TTS_AUDIO_DIR = "";

    // 文本请求输入的文本
    private static final String TEXT_REQ = "你叫什么名字";

    // 用户、设备 标识
    private static String sn = "test-sn";

    // 场景
    private static final String SCENE = "main_box";

    // 发音人聆小玥
    private static final String VCN = "x5_lingxiaoyue_flow";

    // 每帧音频数据大小，单位字节
    private static final int FRAME_SIZE = 1280;
    // 每帧音频发送间隔
    private static final int SEND_INTERVAL = 40;

    public static void main(String[] args) throws Exception {
        if (!checkConfig()) {
            return;
        }

        URI url = new URI(IflytekAuthUtil.getAuthUrl(BASE_URL, "GET", APIKEY, APISECRET));
        CountDownLatch countDownLatch = new CountDownLatch(1);
        IflytekAIUIV3WebSocketClient client = new IflytekAIUIV3WebSocketClient(url, countDownLatch, TTS_AUDIO_DIR);

        if (!client.connectBlocking()) {
            System.out.println("连接建立失败");
            return;
        }

        // 建立连接成功后开始发送音频数据
        sendAudioData(client);

        // 发送文本数据
//        sendTextData(client);

        // 等待交互完成
        countDownLatch.await();
        if (!client.isClosed()) {
            // 主动断开连接，如果不主动断开60秒无交互之后服务端会主动断开连接
            client.close(1000);
        }
    }

    private static void sendAudioData(WebSocketClient client) {
        byte[] bytes = new byte[FRAME_SIZE];
        try (RandomAccessFile raf = new RandomAccessFile(FILE_PATH, "r")) {
            int len = -1;
            int readIndex = 0;
            int fileLength = (int) raf.length();
            int lastIndex = fileLength / FRAME_SIZE + (fileLength % FRAME_SIZE == 0 ? 0 : 1);
            while ((len = raf.read(bytes)) != -1) {
                readIndex += 1;
                if (len < FRAME_SIZE) {
                    bytes = Arrays.copyOfRange(bytes, 0, len);
                }

                // 首帧
                int status = 0;
                if (readIndex == lastIndex) {
                    // 结束帧
                    status = 2;
                } else if (readIndex != 1) {
                    // 中间帧
                    status = 1;
                }
                JSONObject req = buildAudioReq(status, bytes);

                if (client.isClosed()) {
                    System.out.println("连接异常关闭");
                    return;
                }
                client.send(req.toJSONString());
                Thread.sleep(SEND_INTERVAL);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    /**
     * 构造音频请求
     * @param status        数据帧状态：0 开始、1 中间、2 结束
     * @param audioData     音频二进制数据
     * @return
     */
    private static JSONObject buildAudioReq(int status, byte[] audioData) {
        JSONObject req = new JSONObject(new LinkedHashMap<>());
        JSONObject header = new JSONObject(new LinkedHashMap<>());
        req.put("header", header);

        header.put("appid", APPID);
        header.put("sn", sn);
        header.put("status", status);
        header.put("stmid", "1");
        header.put("scene", SCENE);

        // 单工，一次交互(一问一答)一个stmid，一个连接可以多次交互
//        header.put("interact_mode", "continuous_vad");

        // 全双工，一个stmid对应一轮交互（多次问答），一个连接可以多轮交互
        // 客户端可以一直送音频到服务端，服务端会对进行端点检测。多次交互需要打断上次交互回复，客户端需要通过vad前端点返回的sid来过滤获取最新最新一次交互下发的结果
        header.put("interact_mode", "continuous");

        JSONObject parameter = new JSONObject(new LinkedHashMap<>());
        req.put("parameter", parameter);
        // 识别参数配置
        JSONObject iat = new JSONObject(new LinkedHashMap<>());
        parameter.put("iat", iat);
        JSONObject iatFormat = new JSONObject(new LinkedHashMap<>());
        iat.put("iat", iatFormat);
        iatFormat.put("encoding", "utf8");
        iatFormat.put("compress", "raw");
        iatFormat.put("format", "json");
        // 云端vad断句设置
//        iat.put("vgap", 40);
//        iat.put("eos", 400);

        // 语义参数配置
        JSONObject nlp = new JSONObject(new LinkedHashMap<>());
        parameter.put("nlp", nlp);
        JSONObject nlpFormat = new JSONObject(new LinkedHashMap<>());
        nlp.put("nlp", nlpFormat);
        nlpFormat.put("encoding", "utf8");
        nlpFormat.put("compress", "raw");
        nlpFormat.put("format", "json");
        // 清除历史
//        nlp.put("new_session", "true");
        // 自定义prompt，用于修改系统默认的人设
//        nlp.put("prompt", "你是小飞飞，一个小学生，热爱画画");

        // 合成参数配置
        JSONObject tts = new JSONObject(new LinkedHashMap<>());
        parameter.put("tts", tts);
        // 发音人
        tts.put("vcn", VCN);
        JSONObject ttsFmt  = new JSONObject(new LinkedHashMap<>());
        tts.put("tts", ttsFmt);
        // 音频格式：raw（pcm）、lame（mp3）
        ttsFmt.put("encoding", "raw");
        ttsFmt.put("sample_rate", 16000);
        ttsFmt.put("channels", 1);
        ttsFmt.put("bit_depth", 16);

        JSONObject payload = new JSONObject(new LinkedHashMap<>());
        req.put("payload", payload);
        JSONObject audio = new JSONObject(new LinkedHashMap<>());
        payload.put("audio", audio);
        audio.put("status", status);
        audio.put("audio", Base64.getEncoder().encodeToString(audioData));
        // 上传的音频格式：pcm 16k 16bit 单通道
        audio.put("encoding", "raw");
        audio.put("sample_rate", 16000);
        audio.put("channels", 1);
        audio.put("bit_depth", 16);

        return req;
    }

    private static void sendTextData(WebSocketClient client) {
        JSONObject req = new JSONObject(new LinkedHashMap<>());
        JSONObject header = new JSONObject(new LinkedHashMap<>());
        req.put("header", header);

        header.put("appid", APPID);
        header.put("sn", sn);
        // 文本请求status固定为3
        header.put("status", 3);
        header.put("stmid", "1");
        header.put("scene", SCENE);

        // 文本请求interact_mode只能是oneshot
        header.put("interact_mode", "oneshot");

        JSONObject parameter = new JSONObject(new LinkedHashMap<>());
        req.put("parameter", parameter);
        // 识别参数配置
        JSONObject iat = new JSONObject(new LinkedHashMap<>());
        parameter.put("iat", iat);
        JSONObject iatFormat = new JSONObject(new LinkedHashMap<>());
        iat.put("iat", iatFormat);
        iatFormat.put("encoding", "utf8");
        iatFormat.put("compress", "raw");
        iatFormat.put("format", "json");

        // 语义参数配置
        JSONObject nlp = new JSONObject(new LinkedHashMap<>());
        parameter.put("nlp", nlp);
        JSONObject nlpFormat = new JSONObject(new LinkedHashMap<>());
        nlp.put("nlp", nlpFormat);
        nlpFormat.put("encoding", "utf8");
        nlpFormat.put("compress", "raw");
        nlpFormat.put("format", "json");

        JSONObject tts = new JSONObject(new LinkedHashMap<>());
        parameter.put("tts", tts);
        tts.put("vcn", VCN);
        JSONObject ttsFmt  = new JSONObject(new LinkedHashMap<>());
        tts.put("tts", ttsFmt);
        ttsFmt.put("encoding", "raw");
        ttsFmt.put("sample_rate", 16000);
        ttsFmt.put("channels", 1);
        ttsFmt.put("bit_depth", 16);

        JSONObject payload = new JSONObject(new LinkedHashMap<>());
        req.put("payload", payload);
        JSONObject text = new JSONObject(new LinkedHashMap<>());
        payload.put("text", text);
        text.put("encoding", "utf8");
        text.put("compress", "raw");
        text.put("format", "plain");
        // 文本请求status固定为3
        text.put("status", 3);
        text.put("text", Base64.getEncoder().encodeToString(TEXT_REQ.getBytes()));
        System.out.println(req.toJSONString());

        client.send(req.toJSONString());
    }

    private static boolean checkConfig() {
        if (CommonUtil.isEmptyStr(APPID) || CommonUtil.isEmptyStr(APIKEY) || CommonUtil.isEmptyStr(APISECRET)) {
            System.out.println("请填写应用信息：APPID、APIKEY、APISECRET");
            return false;
        }
        if (CommonUtil.isEmptyStr(FILE_PATH) || CommonUtil.isEmptyStr(TTS_AUDIO_DIR)) {
            System.out.println("请填写音频文件地址：FILE_PATH、TTS_AUDIO_DIR");
            return false;
        }
        if (!new File(FILE_PATH).exists()) {
            System.out.println("音频文件：" + FILE_PATH + "不存在");
            return false;
        }
        if (!new File(TTS_AUDIO_DIR).exists()) {
            System.out.println("合成结果音频目录：" + TTS_AUDIO_DIR + "不存在");
            return false;
        }

        return true;
    }
}