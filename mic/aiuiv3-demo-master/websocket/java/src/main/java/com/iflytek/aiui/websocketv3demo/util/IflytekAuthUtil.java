package com.iflytek.aiui.websocketv3demo.util;

import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Base64;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * 
 * 授权参数签名工具
 *
 */
public class IflytekAuthUtil {

    /**
     * 
     * @param url           接口请求地址
     * @param method        请求方法，websocket 接口为 GET
     * @param apiKey        api key，通过AIUI平台获取
     * @param apiSecret     api secret，通过AIUI平台获取
     * @return              带签名查询参数的url
     * @throws Exception
     */
    public static String getAuthUrl(String url, String method, String apiKey, String apiSecret) throws Exception {
        URI uri = URI.create(url);
        String host = uri.getHost();
        String path = uri.getPath();
        // 获取当前GMT时间
        SimpleDateFormat format = new SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss z", Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("GMT"));
        String date = format.format(new Date());
        // 拼接 host date request-line
        String headerLine = "host: " + host + "\n" + "date: " + date + "\n" + method + " " + path + " HTTP/1.1";
        // SHA256加密
        Mac mac = Mac.getInstance("hmacsha256");
        SecretKeySpec spec = new SecretKeySpec(apiSecret.getBytes(StandardCharsets.UTF_8), "hmacsha256");
        mac.init(spec);

        byte[] hexDigits = mac.doFinal(headerLine.getBytes(StandardCharsets.UTF_8));
        // Base64加密
        String sha = Base64.getEncoder().encodeToString(hexDigits);
        // 生成authorization
        String authorization = String.format("api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"",
                apiKey, "hmac-sha256", "host date request-line", sha);
        String authorizationBase64 = Base64.getEncoder().encodeToString(authorization.getBytes(StandardCharsets.UTF_8));

        // 生成鉴权URL
        return String.format("%s?authorization=%s&date=%s&host=%s",
                url,
                URLEncoder.encode(authorizationBase64, "UTF-8"),
                URLEncoder.encode(date, "UTF-8"),
                URLEncoder.encode(host, "UTF-8"));
    }
}