using Newtonsoft.Json.Linq;
using System.Text;
using System.Web;
using System.Security.Cryptography;
using System.Net.WebSockets;

// 运行方式：
// 设置应用信息: APPID, APIKEY, APISECRET
// 设置音频文件地址: FILE_PATH
// 直接执行: dotnet run
class AIUIV3Demo {

    // 服务地址
    private readonly static String BASE_URL = "wss://aiui.xf-yun.com/v3/aiint/sos";

    private readonly static String APPID = "";
    private readonly static String APIKEY = "";
    private readonly static String APISECRET = "";

    private readonly static String SN = "test-sn";
    // 场景
    private readonly static String SCENE = "main_box";

    private readonly static String VCN = "x5_lingxiaoyue_flow";

    /**
     * 用于设置发送文本请求还是音频请求 请求类型: text/audio
     * 
     * 音频请求需要先设置FILE_PATH 当前音频格式默认pcm，修改音频格式需要修改audioReq中的payload中音频相关参数
     */
    private readonly static String REQ_TYPE = "audio";

    // 请求文本
    private readonly static String question = "你是谁";

    // 每帧音频数据大小，单位字节
    private readonly static int CHUNCKED_SIZE = 1280;
    // 音频发送间隔，模拟录音结果，16k 16bit 音频 每40毫秒发送 1280字节
    private readonly static int SLEEP_INTERVAL = 40;
    // 音频文件位置
    private readonly static String FILE_PATH = "D:/workspace/AIUIV3Demo/resource/weather.pcm";

    static void Main(string[] args) {
        string handShakeUri = AssembleAuthUrl(BASE_URL);
        Uri serverUri = new(handShakeUri);

        using ClientWebSocket client = new();
        client.ConnectAsync(serverUri, CancellationToken.None).Wait();
        if (client.State != WebSocketState.Open) {
            Console.WriteLine("握手失败");
            return;
        }

        // 发送消息
        Task sendTread = SendMessageAsync(client);
        // 接收返回值
        Task recieveTread = ReceiveMessageAsync(client);

        sendTread.Wait();
        Console.WriteLine("sendTread end");
        recieveTread.Wait();
        Console.WriteLine("recieveTread end");
    }

    private static Task SendMessageAsync(ClientWebSocket client) {
        Task task = Task.Run(() => {
            if (REQ_TYPE == "text") {
                // 文本请求
                ArraySegment<byte> bytesToSend = new(Encoding.UTF8.GetBytes(GenTextReq()));
                client.SendAsync(bytesToSend, WebSocketMessageType.Text, true, CancellationToken.None);
            }
            if (REQ_TYPE == "audio") {
                // 音频请求
                using FileStream fs = new(FILE_PATH, FileMode.Open, FileAccess.Read);
                byte[] buffer = new byte[CHUNCKED_SIZE];
                long fileSize = fs.Length;
                long lastIndex = fileSize / CHUNCKED_SIZE + (fileSize % CHUNCKED_SIZE == 0 ? 0 : 1);
                for (int i = 1; i <= lastIndex; i++) {
                    int rlen = fs.Read(buffer);
                    if (rlen < CHUNCKED_SIZE) {
                        buffer = buffer.Take(rlen).ToArray();
                    }

                    int status = 0;
                     if (i == lastIndex) {
                        // 结束帧
                        status = 2;
                    } else if (i != 1) {
                        // 中间帧
                        status = 1;
                    }
                    string audioReq = GenAudioReq(buffer, status);
                    // Console.WriteLine(audioReq);
                    ArraySegment<byte> bytesToSend = new(Encoding.UTF8.GetBytes(audioReq));
                    if (client.State != WebSocketState.Open) {
                        Console.WriteLine("websocket closed");
                        return;
                    }
        
                    client.SendAsync(bytesToSend, WebSocketMessageType.Binary, true, CancellationToken.None);
                    Thread.Sleep(SLEEP_INTERVAL);
                }
            }
        });
        return task;
    }

    private static Task ReceiveMessageAsync(ClientWebSocket client) {
        Task task = Task.Run(() => {
            while (true) {
                // 如果接收到json不完整可能是buffer大小不足
                ArraySegment<byte> buffer = new(new byte[102400]);
                if (client.State != WebSocketState.Open) {
                    Console.WriteLine("websocket closed");
                    return;
                }
                WebSocketReceiveResult result = client.ReceiveAsync(buffer, CancellationToken.None).Result;
                byte[] a = buffer.Array ?? Array.Empty<byte>();
                string response = Encoding.UTF8.GetString(a, 0, result.Count);
                // Console.WriteLine($"收到返回值：{response}");
                JObject resObj = JObject.Parse(response);
                if (resObj == null) {
                    Console.WriteLine("invalid response");
                    return;
                }
                JToken? h = resObj.GetValue("header");
                if (h == null) {
                    Console.WriteLine("invalid response, no header");
                    return;
                }
                JObject? header = h.ToObject<JObject>();
                int? code = header.Value<int>("code");
                if (code != 0) {
                    Console.WriteLine($"server error: {response}");
                    return;
                }

                // 解析返回值
                JToken? p = resObj.GetValue("payload");
                if (p != null) {
                    JObject? payload = p.ToObject<JObject>();
                    if (payload == null) {
                        Console.WriteLine("invalid payload");
                        return;
                    }

                    JObject? eventj = payload.Value<JObject>("event");
                    if (eventj != null) {
                        string? text = eventj.Value<string>("text");
                        if (text != null) {
                            Console.WriteLine($"event text：{DecodeBase64(text)}");
                        }
                    }

                    JObject? iat = payload.Value<JObject>("iat");
                    if (iat != null) {
                        string? text = iat.Value<string>("text");
                        if (text != null) {
                            Console.WriteLine($"iat text：{DecodeBase64(text)}");
                        }
                    }

                    JObject? nlp = payload.Value<JObject>("nlp");
                    if (nlp != null) {
                        string? text = nlp.Value<string>("text");
                        if (text != null) {
                            Console.WriteLine($"nlp text：{DecodeBase64(text)}");
                        }
                    }
                    // TODO 其他结果处理逻辑可以参考python demo
                }

                int status = header.Value<int>("status");
                if (status == 2) {
                    // 最后一帧结果
                    client.CloseAsync(WebSocketCloseStatus.NormalClosure, "end", CancellationToken.None);
                    break;
                }
            }
        });
        return task;
    }

    private static string EncodeBase64(string source) {
        byte[] bytes = Encoding.UTF8.GetBytes(source);
        return EncodeBase64(bytes);
    }

    private static string EncodeBase64(byte[] bytes) {
        return Convert.ToBase64String(bytes);
    }

    private static string DecodeBase64(string encodedData) {
        byte[] decodedBytes = Convert.FromBase64String(encodedData);
        string decodedData = Encoding.UTF8.GetString(decodedBytes);
        return decodedData;
    }

    private static string GenAudioReq(byte[] data, int status) {
        JObject audioReq = new (){
            {
                "header", new JObject {
                    {"appid", APPID},
                    {"sn", SN},
                    {"stmid", "audio-1"},
                    {"status", status},
                    {"scene", SCENE},
                    {"interact_mode", "continuous"}
                }
            },
            {
                "parameter", new JObject {
                    {
                        "nlp", new JObject {
                            {
                                "nlp", new JObject {
                                    {"compress", "raw"},
                                    {"format", "json"},
                                    {"encoding", "utf8"}
                                }
                            },
                            {"new_session", true}
                        }
                    },
                    {
                        "tts", new JObject {
                            {
                                "tts", new JObject {
                                    {"channels", 1},
                                    {"bit_depth", 16},
                                    {"sample_rate", 16000},
                                    {"encoding", "raw"}
                                }
                            },
                            {"vcn", VCN}
                        }
                    }
                }
            },
            {
                "payload", new JObject {
                    {
                        "audio", new JObject {
                            {"encoding", "raw"},
                            {"sample_rate", 16000},
                            {"channels", 1},
                            {"bit_depth", 16},
                            {"status", status},
                            {"audio", EncodeBase64(data)}
                        }
                    }
                }
            }
        };

        return audioReq.ToString().ReplaceLineEndings();
    }

    private static string GenTextReq() {
        JObject textReq = new (){
            {
                "header", new JObject {
                    {"appid", APPID},
                    {"sn", SN},
                    {"stmid", "text-1"},
                    {"status", 3},
                    {"scene", SCENE},
                    {"interact_mode", "oneshot"}
                }
            },
            {
                "parameter", new JObject {
                    {
                        "nlp", new JObject {
                            {
                                "nlp", new JObject {
                                    {"compress", "raw"},
                                    {"format", "json"},
                                    {"encoding", "utf8"}
                                }
                            },
                            {"new_session", true}
                        }
                    },
                    {
                        "tts", new JObject {
                            {
                                "tts", new JObject {
                                    {"channels", 1},
                                    {"bit_depth", 16},
                                    {"sample_rate", 16000},
                                    {"encoding", "raw"}
                                }
                            },
                            {"vcn", VCN}
                        }
                    }
                }
            },
            {
                "payload", new JObject {
                    {
                        "text", new JObject {
                            {"compress", "raw"},
                            {"format", "plain"},
                            {"encoding", "utf8"},
                            {"status", 3},
                            {"text", EncodeBase64(question)}
                        }
                    }
                }
            }
        };

        return textReq.ToString().ReplaceLineEndings();
    }

    private static string AssembleAuthUrl(string url) {
        Uri uri = new(BASE_URL);

        string host = uri.Host;
        string path = uri.AbsolutePath;

        string date = DateTimeOffset.UtcNow.ToString("r");
        string preStr = $"host: {host}\ndate: {date}\nGET {path} HTTP/1.1";

        using var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(APISECRET));
        byte[] hashBytes = hmac.ComputeHash(Encoding.UTF8.GetBytes(preStr));
        String sha = EncodeBase64(hashBytes);
        String authorization = $"api_key=\"{APIKEY}\", algorithm=\"hmac-sha256\", headers=\"host date request-line\", signature=\"{sha}\"";
        return $"{url}?authorization={HttpUtility.UrlEncode(EncodeBase64(authorization))}&date={HttpUtility.UrlEncode(date)}&host={HttpUtility.UrlEncode(host)}";
    }
}