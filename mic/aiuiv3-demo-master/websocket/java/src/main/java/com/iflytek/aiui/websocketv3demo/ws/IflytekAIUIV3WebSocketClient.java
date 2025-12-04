package com.iflytek.aiui.websocketv3demo.ws;

import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.net.URI;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.Base64;
import java.util.Objects;
import java.util.concurrent.CountDownLatch;

import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.iflytek.aiui.websocketv3demo.util.CommonUtil;

/**
 * 急速交互结果处理ws客户端
 * 
 */
public class IflytekAIUIV3WebSocketClient extends WebSocketClient {

    private CountDownLatch countDownLatch;
    // 当前这轮交互的id
    private String curRoundId;
    // 记录此次交互合音频长度
    private int audioLen;
    private String ttsDir;

    public IflytekAIUIV3WebSocketClient(URI serverUri, CountDownLatch countDownLatch, String ttsDir) {
        super(serverUri, new DraftWithOrigin(getWebsocketUrlOrigin(serverUri)));
        this.countDownLatch = countDownLatch;
        this.ttsDir = ttsDir;
    }

    private static String getWebsocketUrlOrigin(URI serverUri) {
        return (serverUri.getScheme().equals("ws") ? "http://" : "https://") + serverUri.getHost();
    }

    @Override
    public void onOpen(ServerHandshake handshake) {
        // 会阻塞onMesage, 如果要在这里发送数据需要另起线程
        System.out.println("连接建立成功, code:" + handshake.getHttpStatusMessage());
    }

    @Override
    public void onMessage(ByteBuffer bytes) {
        try {
            // 急速交互websocket返回数据为二进制数据
            // 二进制数据转换成文本统一处理
            String responseText = new String(bytes.array(), "utf-8");
//            System.out.println("接收到服务端返回的二进制数据：" + responseText);
            onMessage(responseText);
        } catch (UnsupportedEncodingException e) {
            e.printStackTrace();
        }
    }

    @Override
    public void onMessage(String msg) {
        JSONObject response = JSONObject.parseObject(msg);
        // 结果解析
        JSONObject header = response.getJSONObject("header");
        String sid = header.getString("sid");
        int status = header.getIntValue("status");
        String stmid = header.getString("stmid");
//        System.out.println("sid: " + sid + ", stmid: " + stmid);

        int code = header.getIntValue("code");
        if (code != 0) {
            this.close(1001, "服务端返回错误：" + msg);
            return;
        }

        JSONObject payload = response.getJSONObject("payload");
        if (payload == null) {
            if (status == 0) {
                System.out.println("第一帧结果：" + response);
            }
            return;
        }
//        System.out.println("payload key:" + JSON.toJSONString(payload.keySet()));

        // event 识别的vad事件
        JSONObject event = payload.getJSONObject("event");
        if (event != null) {
            String eventDataStr = new String(Base64.getDecoder().decode(event.getString("text")));

            JSONObject eventJson = JSONObject.parseObject(eventDataStr);
            String eventKey = eventJson.getString("key");
            switch (eventKey) {
            case "Bos":
                System.out.println("检测到前端点");
                // 检测到用户说话，将当前这帧结果的stmid作为当前交互的标志
                this.curRoundId = stmid;
                this.audioLen = 0;
                break;
            case "Eos":
                System.out.println("检测到尾端点");
                // vad尾端点
                break;
            case "Silence":
                // 静音事件，客户端的音频长时间无人说话会触发。或者客户端发送了最后一帧音频，服务端结果下发完成之后触发silence
                // 此时客户端可以重新开启一轮交互，可以复用当前连接用一个新的stmid重新开始请求
                break;
            default:
                System.out.println("event:" + eventDataStr);
            }
        }

        if (!Objects.equals(stmid, this.curRoundId)) {
            // 全双工交互会存在上一次交互的结果还没有完全下发完，用户又问了一个问题，这时服务端开启了新的一次交互
            // 端上如果需要打断上次交互，需要丢弃上次交互返回的结果
            // stmid不是最新的表示不是当前这次交互的结果, 端上播报和展示结果应该直接忽略
            System.out.println("---skip this result---");
            return;
        }


        // 识别结果
        JSONObject iat = payload.getJSONObject("iat");
        if (iat != null) {
            String iatStr = new String(Base64.getDecoder().decode(iat.getString("text")));
            System.out.println("识别结果：" + printIat(iatStr));
        }

        // 意图规整结果（历史改写）
        JSONObject cbmTidy = payload.getJSONObject("cbm_tidy");
        if (cbmTidy != null) {
            String cbmTidyStr = new String(Base64.getDecoder().decode(cbmTidy.getString("text")));
            System.out.println("意图规整结果：" + cbmTidyStr);
        }

        // 技能结果
        JSONObject semantic = payload.getJSONObject("cbm_semantic");
        if (semantic != null) {
            String text = new String(Base64.getDecoder().decode(semantic.getString("text")));
            System.out.println("技能结果：" + text);
        }

        // 语义结果
        JSONObject nlp = payload.getJSONObject("nlp");
        if (nlp != null) {
            String text = new String(Base64.getDecoder().decode(nlp.getString("text")));
            System.out.println("语义结果：" + text);
        }

        // 保存合成音频
        JSONObject tts = payload.getJSONObject("tts");
        if (tts != null) {
            String fileName = String.format("%s.%s", sid, getSuffix(tts.getString("encoding")));
            Path path = Paths.get(ttsDir, fileName);

            String aData = tts.getString("audio");
            if (!CommonUtil.isEmptyStr(aData)) {
                byte[] audioData = Base64.getDecoder().decode(aData);
                try {
//                    System.out.println("sid:" + sid +" 合成结果, seq:" + tts.getIntValue("seq") + ", status: " +tts.getString("status") + ", audioLen：" + audioData.length);
                    Files.write(path, audioData, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
                    this.audioLen += audioData.length;
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
            if (tts.getIntValue("status") == 2) {
                System.out.println("接收到最后一帧合成结果，音频保存到: "+ path.toFile().getAbsolutePath() + "， 音频总长度：" + this.audioLen);
            }
        }

        if (status == 2) {
            countDownLatch.countDown();
        }
    }

    private String printIat(String iatStr) {
//        System.out.println(iatStr);
        StringBuffer sb = new StringBuffer();
        JSONObject iat = JSON.parseObject(iatStr);
        JSONArray ws = iat.getJSONObject("text").getJSONArray("ws");
        if (ws == null) {
            return "";
        }
        for (int i = 0; i < ws.size(); i++) {
            JSONObject j = ws.getJSONObject(i);
            JSONArray cws = j.getJSONArray("cw");
            for (int k = 0; k < cws.size(); k++) {
                JSONObject cw = cws.getJSONObject(k);
                sb.append(cw.getString("w"));
            }
        }
        return sb.toString();
    }

    private Object getSuffix(String encoding) {
        switch (encoding) {
        case "raw":
            return "pcm";
        case "lame":
            return "mp3";
        default:
            return "unknow";
        }
    }

    @Override
    public void onError(Exception e) {
        System.out.println("连接异常：" + e.getMessage());
        e.printStackTrace();
    }

    @Override
    public void onClose(int code, String message, boolean b) {
        System.out.println("连接关闭" + "," + message);
        countDownLatch.countDown();
    }
}