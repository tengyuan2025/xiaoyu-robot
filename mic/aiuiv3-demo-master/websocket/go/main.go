package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// 设置应用配置后直接执行
var (
	baseUrl = "wss://aiui.xf-yun.com/v3/aiint/sos"
	// 应用配置
	appid     = ""
	apikey    = ""
	apisecret = ""

	sn = "test-sn"

	// 场景
	scene = "main_box"

	vcn = "x5_lingxiaoyue_flow"

	// 用于设置发送文本请求还是音频请求
	// 请求数据类型：text/audio
	// 音频请求需要先设置filePath
	// 当前音频格式默认pcm，修改音频格式需要修改audioReq中的payload中音频相关参数
	dataType = "text"
	// 请求文本呢
	payLoadText = "你是谁"

	// 下面两个参数配合音频采样率设置，16k 16bit的音频： 每 40毫秒 发送 1280字节
	// 每帧音频数据大小，单位字节
	frameSize     int64 = 1024
	sleepInterval int64 = 40
	// 音频文件位置
	filePath = "D:/workspace/AIUIV3Demo/resource/weather.pcm"
)

func main() {
	// 设置握手超时
	d := websocket.Dialer{
		HandshakeTimeout: 5 * time.Second,
	}
	// 建立websocket连接
	handshakeUrl := assembleAuthUrl(baseUrl, apikey, apisecret)
	conn, resp, err := d.Dial(handshakeUrl, nil)
	if err != nil || resp.StatusCode != 101 {
		// 握手失败
		log.Panicf("handshake error：%v, %v", readResp(resp), err.Error())
	}

	wg := new(sync.WaitGroup)
	wg.Add(2)
	go sendReq(conn, wg)
	go receiveRes(conn, wg)
	// 等待交互完成
	wg.Wait()
}

// 发送请求数据
func sendReq(conn *websocket.Conn, wg *sync.WaitGroup) {
	defer wg.Done()
	var err error
	if dataType == "text" {
		req := genTextParam()
		log.Printf("send req: %v\n", marshalToString(req))
		err = conn.WriteJSON(req)
	}
	if dataType == "audio" {
		f, err := os.OpenFile(filePath, os.O_RDONLY, os.ModePerm)
		if err != nil {
			log.Printf("open file error: %v", err.Error())
			conn.Close()
			return
		}

		buf := make([]byte, frameSize)
		fileInfo, err := f.Stat()
		if err != nil {
			log.Printf("get file info error: %v", err.Error())
			conn.Close()
			return
		}
		fileSize := fileInfo.Size()
		frameMax := fileSize / frameSize
		if fileSize%frameSize != 0 {
			frameMax += 1
		}

		status := 0
		for i := int64(1); i <= frameMax; i++ {
			n, err := f.Read(buf)
			if err != nil && err != io.EOF {
				conn.Close()
				break
			}
			if i == frameMax {
				// 尾帧
				status = 2
			} else if i != 1 {
				// 中间帧
				status = 1
			}

			req := genAudioParam(buf[:n], status)
			err = conn.WriteJSON(req)
			if err != nil {
				break
			}
			time.Sleep(time.Duration(sleepInterval) * time.Millisecond)
		}
	}

	if err != nil {
		log.Printf("sendReq error: %v", err.Error())
	}
}

// 接收返回值
func receiveRes(conn *websocket.Conn, wg *sync.WaitGroup) {
	defer wg.Done()
	var audioFile *os.File
	for {
		_, d, err := conn.ReadMessage()
		if err != nil {
			log.Println("read message error: ", err.Error())
			return
		}
		// log.Println("response: ", string(d))

		aiuiRes := new(AIUIV3Res)
		err = json.Unmarshal(d, aiuiRes)
		if err != nil {
			fmt.Println("Unmarshal response error: ", err.Error())
			return
		}

		if aiuiRes.Header.Code != 0 {
			log.Println("response error: ", string(d))
			return
		}
		sid := aiuiRes.Header.Sid
		if aiuiRes.Payload.Event != nil {
			// 事件：vad开始，vad结束，silence 静音（结束）
			log.Println("event result: " + string(aiuiRes.Payload.Event.Text))
		}
		if aiuiRes.Payload.Iat != nil {
			// 识别结果
			log.Println("iat result: " + string(aiuiRes.Payload.Iat.Text))
		}
		if aiuiRes.Payload.CbmSemantic != nil {
			// 技能结果
			skillRes := map[string]any{}
			if err := json.Unmarshal(aiuiRes.Payload.CbmSemantic.Text, &skillRes); err == nil {
				if rc, ok := skillRes["rc"].(float64); ok {
					if rc == 0 {
						// 命中技能
						log.Printf("text : %v,  hit skill: %v, answer: %v\n", skillRes["text"], skillRes["category"], skillRes["answer"].(map[string]any)["text"])
					} else {
						log.Printf("semantic result: %v \n", string(aiuiRes.Payload.CbmSemantic.Text))
					}
				}
			}
		}
		if aiuiRes.Payload.Nlp != nil {
			// 语义结果
			log.Println("nlp result: " + string(aiuiRes.Payload.Nlp.Text))
		}
		if aiuiRes.Payload.Tts != nil {
			// 将音频保存到当前目录下
			tts := aiuiRes.Payload.Tts
			audioName := sid + "." + getSuffix(tts.Encoding)
			// log.Printf("tts result seq: %v, len: %v\n", tts.Seq, len(tts.Audio))
			if tts.Seq == 1 {
				audioFile, err = os.Create(audioName)
				if err != nil {
					log.Println("create audio file error: ", err.Error())
					continue
				}
			}
			if audioFile != nil {
				_, err := audioFile.Write(tts.Audio)
				if err != nil {
					log.Println("write audio file error: ", err.Error())
				}
			}
		}
		if aiuiRes.Header.Status == 2 {
			if audioFile != nil {
				err = audioFile.Close()
				if err != nil {
					log.Println("close audio file error: ", err.Error())
				}
			}
			// 最后一帧结果
			return
		}
	}
}

// 生成文本请求参数
func genTextParam() map[string]any {
	// 文本请求status固定为3，interact_mode固定为oneshot
	return map[string]any{
		"header": map[string]any{
			"appid":         appid,
			"sn":            sn,
			"stmid":         "text-1",
			"status":        3,
			"scene":         scene,
			"interact_mode": "oneshot",
		},
		"parameter": map[string]any{
			"nlp": map[string]any{
				"nlp": map[string]any{
					"compress": "raw",
					"format":   "json",
					"encoding": "utf8",
				},
				"new_session": true,
			},
			"tts": map[string]any{
				"vcn": vcn,
				"tts": map[string]any{
					"channels":    1,
					"bit_depth":   16,
					"sample_rate": 16000,
					"encoding":    "raw",
				},
			},
		},
		"payload": map[string]any{
			"text": map[string]any{
				"compress": "raw",
				"format":   "plain",
				"text":     base64.StdEncoding.EncodeToString([]byte(payLoadText)),
				"encoding": "utf8",
				"status":   3,
			},
		},
	}
}

// 生成音频请求参数
func genAudioParam(data []byte, status int) map[string]any {
	return map[string]any{
		"header": map[string]any{
			"appid":         appid,
			"sn":            sn,
			"stmid":         "audio-1",
			"status":        status,
			"scene":         scene,
			"interact_mode": "continuous",
		},
		"parameter": map[string]any{
			"nlp": map[string]any{
				"nlp": map[string]any{
					"compress": "raw",
					"format":   "json",
					"encoding": "utf8",
				},
				"new_session": true,
			},
			"tts": map[string]any{
				"vcn": vcn,
				"tts": map[string]any{
					"channels":    1,
					"bit_depth":   16,
					"sample_rate": 16000,
					"encoding":    "raw",
				},
			},
		},
		"payload": map[string]any{
			"audio": map[string]any{
				"encoding":    "raw",
				"sample_rate": 16000,
				"channels":    1,
				"bit_depth":   16,
				"status":      status,
				"audio":       base64.StdEncoding.EncodeToString(data),
			},
		},
	}
}

// 创建鉴权url
func assembleAuthUrl(hosturl string, apikey, apisecret string) string {
	ul, err := url.Parse(hosturl)
	if err != nil {
		log.Panic("parse url error: ", err.Error())
	}
	// 签名时间 Sun, 03 Sep 2023 16:47:59 GMT
	date := time.Now().UTC().Format(time.RFC1123)
	date = strings.Replace(date, "UTC", "GMT", -1)
	// 参与签名的字段 host ,date, request-line
	signString := []string{"host: " + ul.Host, "date: " + date, "GET " + ul.Path + " HTTP/1.1"}
	// 拼接签名字符串
	sgin := strings.Join(signString, "\n")
	// fmt.Println(sgin)
	// 签名结果
	sha := HmacWithShaTobase64("hmac-sha256", sgin, apisecret)
	// 构建请求参数 此时不需要urlencoding
	authUrl := fmt.Sprintf("api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"", apikey,
		"hmac-sha256", "host date request-line", sha)
	// 将请求参数使用base64编码
	authorization := base64.StdEncoding.EncodeToString([]byte(authUrl))

	v := url.Values{}
	v.Add("host", ul.Host)
	v.Add("date", date)
	v.Add("authorization", authorization)
	// 将编码后的字符串url encode后添加到url后面
	return hosturl + "?" + v.Encode()
}

func HmacWithShaTobase64(algorithm, data, key string) string {
	mac := hmac.New(sha256.New, []byte(key))
	mac.Write([]byte(data))
	encodeData := mac.Sum(nil)
	return base64.StdEncoding.EncodeToString(encodeData)
}

func getSuffix(encoding string) string {
	switch encoding {
	case "raw":
		return "pcm"
	case "lame":
		return "mp3"
	default:
		return "unknow"
	}
}

func readResp(resp *http.Response) string {
	if resp == nil {
		return ""
	}
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		panic(err)
	}
	return fmt.Sprintf("code=%d,body=%s", resp.StatusCode, string(b))
}

func marshalToString(r any) string {
	b, _ := json.Marshal(r)
	return string(b)
}

type AIUIV3Res struct {
	Header  AIUIV3ResHeader  `json:"header"`
	Payload AIUIV3ResPayload `json:"payload"`
}

type AIUIV3ResHeader struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Sid     string `json:"sid"`
	Stmid   string `json:"stmid"`
	Status  int    `json:"status"`
}

type AIUIV3ResPayload struct {
	Event       *AIUIV3ResPayloadTextData  `json:"event"`
	Iat         *AIUIV3ResPayloadTextData  `json:"iat"`
	CbmSemantic *AIUIV3ResPayloadTextData  `json:"cbm_semantic"`
	Nlp         *AIUIV3ResPayloadTextData  `json:"nlp"`
	Tts         *AIUIV3ResPayloadAudioData `json:"tts"`
}

type AIUIV3ResPayloadTextData struct {
	Compress string `json:"compress"`
	Encoding string `json:"encoding"`
	Format   string `json:"format"`
	Seq      int    `json:"seq"`
	Status   int    `json:"status"`
	Text     []byte `json:"Text"`
}

type AIUIV3ResPayloadAudioData struct {
	Compress string `json:"compress"`
	Encoding string `json:"encoding"`
	Format   string `json:"format"`
	Seq      int    `json:"seq"`
	Status   int    `json:"status"`
	Audio    []byte `json:"audio"`
}
