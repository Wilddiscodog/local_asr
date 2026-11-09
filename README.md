# local_asr — 本机离线整段语音转写

局域网 HTTP 服务：设备/脚本上传 **完整段** 16 kHz mono WAV/PCM → 本机 sherpa-onnx 中文 Paraformer 识别 → 返回 JSON 文本。

不做边说边出字。适合手表等嵌入式设备把算力放到 PC。

## 打包成可执行文件（推荐部署）

在一台已装 Python 3.11 的 Windows x64 上构建一次，拷到任意电脑即可（目标机**无需装 Python**）。

```bat
build_exe.bat
pack_release.bat
```

产物：

- `dist\pc_stt_server\` — 可直接复制的目录（`pc_stt_server.exe` + `_internal\`）
- `dist\pc_stt_server_win64.zip` — 约 40MB（**不含**识别模型）

部署：

1. 解压/复制 `pc_stt_server` 文件夹
2. 双击 `pc_stt_server.exe`  
   - **首次运行**自动下载约 200MB 模型到同目录 `models\`（需联网一次）  
   - 或事先拷贝已有 `models\`，可完全离线启动
3. 防火墙放行 TCP **8765**
4. `POST http://<PC局域网IP>:8765/transcribe`

## 源码运行

- Windows + **Python 3.9+**（推荐 3.11）
- CPU 即可

```bat
py -3.11 -m pip install -r requirements.txt
py -3.11 download_model.py
py -3.11 server.py --host 0.0.0.0 --port 8765
```

或：`run_server.bat`

### 接口

| 接口 | 说明 |
|------|------|
| `GET /health` | 探活 |
| `POST /transcribe` | body = `audio/wav`，或 raw **16 kHz mono s16le**；也可 multipart `file`/`audio` |

```json
{"ok": true, "text": "识别出的中文", "bytes": 12345, "ms": 280}
```

### 冒烟 / 客户端测试

```bat
py -3.11 smoke_test.py
py -3.11 test_transcribe.py models\sherpa-onnx-paraformer-zh-2023-09-14\test_wavs\0.wav
```

```bat
curl -s -X POST --data-binary @models\sherpa-onnx-paraformer-zh-2023-09-14\test_wavs\0.wav -H "Content-Type: audio/wav" http://127.0.0.1:8765/transcribe
```

## 与嵌入式设备对接

- 音频：`16000 Hz / mono / s16le`
- 建议 PTT 录完再上传；单段建议 ≤ 5–15 s
- 设备作 HTTP 客户端：`POST http://<PC局域网IP>:8765/transcribe`

## 文件

| 文件 | 作用 |
|------|------|
| `build_exe.bat` / `pc_stt_server.spec` | 打成 Windows 可执行目录 |
| `pack_release.bat` | 打 zip |
| `run_server.bat` | 源码一键启动 |
| `download_model.py` | 下载 Paraformer 中文模型 |
| `asr_engine.py` | 离线识别封装 |
| `server.py` | HTTP 服务 |
| `smoke_test.py` / `test_transcribe.py` | 本地 / HTTP 测试 |
| `requirements.txt` | Python 依赖 |

模型与 `build/`、`dist/` 已在 `.gitignore` 中忽略。
