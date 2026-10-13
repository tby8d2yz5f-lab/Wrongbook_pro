from __future__ import annotations

import json
import ipaddress
import mimetypes
import os
import threading
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
LAN_MODE = os.environ.get("ZHI_CUO_LAN") == "1"
HOST = "0.0.0.0" if LAN_MODE else "127.0.0.1"
PORT = 8765
BASE_URL = f"http://{HOST}:{PORT}"
OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = os.environ.get("OLLAMA_MODEL", "qwen3-vl:8b")
MAX_BODY = 60_000_000


class LocalHandler(BaseHTTPRequestHandler):
    server_version = "ZhiCuoLocal/1.0"

    def log_message(self, fmt: str, *args) -> None:
        # Do not print question contents or request bodies to the console.
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")

    def send_json(self, data: dict, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def check_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if LAN_MODE:
            try:
                client_ip = ipaddress.ip_address(self.client_address[0].split("%", 1)[0])
            except ValueError:
                self.send_json({"ok": False, "error": "无法确认访问设备的局域网地址。"}, 403)
                return False
            if not (client_ip.is_private or client_ip.is_loopback):
                self.send_json({"ok": False, "error": "手机访问仅允许来自本地局域网。"}, 403)
                return False
            if origin:
                try:
                    parsed_origin = urlsplit(origin)
                    request_host = urlsplit("//" + self.headers.get("Host", ""))
                    origin_ip = ipaddress.ip_address((parsed_origin.hostname or "").split("%", 1)[0])
                    valid_origin = (
                        parsed_origin.scheme == "http"
                        and parsed_origin.port == PORT
                        and request_host.port == PORT
                        and parsed_origin.hostname == request_host.hostname
                        and (origin_ip.is_private or origin_ip.is_loopback)
                    )
                except ValueError:
                    valid_origin = False
                if not valid_origin:
                    self.send_json({"ok": False, "error": "仅允许从本机或同一局域网的错题本页面访问。"}, 403)
                    return False
        elif origin and origin != BASE_URL:
            self.send_json({"ok": False, "error": "仅允许从本机错题本页面访问。"}, 403)
            return False
        return True

    def read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("请求格式不正确。") from exc
        if length <= 0 or length > MAX_BODY:
            raise ValueError("请求内容为空或图片太大，请压缩后重试。")
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("请求内容不是有效 JSON。") from exc
        if not isinstance(value, dict):
            raise ValueError("请求内容格式不正确。")
        return value

    def ollama_chat(self, messages: list[dict], json_mode: bool = False) -> str:
        body = {
            "model": MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        if json_mode:
            body["format"] = "json"
        request = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=900) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"Ollama 请求失败：{detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("无法连接本机 Ollama。请确认 Ollama 已安装并正在运行。") from exc
        content = result.get("message", {}).get("content", "")
        if not content:
            raise RuntimeError("本机模型没有返回内容。")
        return content.strip()

    @staticmethod
    def image_base64(value: object) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError("没有收到图片，请重新上传。")
        if value.startswith("data:image/") and "," in value:
            return value.split(",", 1)[1]
        if all(char.isalnum() or char in "+/=" for char in value):
            return value
        raise ValueError("图片格式无法识别，请重新上传。")

    def do_GET(self) -> None:
        if not self.check_origin():
            return
        path = unquote(urlsplit(self.path).path)
        if path == "/api/health":
            try:
                request = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
                with urllib.request.urlopen(request, timeout=5) as response:
                    tags = json.loads(response.read().decode("utf-8"))
                models = [item.get("name", "") for item in tags.get("models", [])]
                self.send_json({"ok": True, "ollama": True, "model": MODEL,
                                "modelAvailable": MODEL in models, "installedModels": models})
            except Exception:
                self.send_json({"ok": True, "ollama": False, "model": MODEL,
                                "modelAvailable": False, "installedModels": []})
            return

        relative = "index.html" if path == "/" else path.lstrip("/")
        target = (ROOT / relative).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError:
            self.send_json({"ok": False, "error": "找不到请求的文件。"}, 404)
            return
        if not target.is_file():
            self.send_json({"ok": False, "error": "找不到请求的文件。"}, 404)
            return
        content = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix.lower() in (".html", ".js", ".css", ".webmanifest"):
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if not self.check_origin():
            return
        path = urlsplit(self.path).path
        try:
            data = self.read_json()
            if path == "/api/analyze":
                question = str(data.get("question", "")).strip()
                if not question:
                    raise ValueError("请先填写题目内容。")
                system = (
                    "你是一位严谨的中国高中学科辅导老师。请根据用户提供的错题，讲清正确解法、关键推理、常见误区，并归纳可迁移的知识点。"
                    "不得虚构题目条件；若题目缺条件或存在歧义，要在解析中明确说明。若用户没有提供错误过程，不得臆测其实际错因。"
                    "请在 analysis 中按“题意与已知条件、核心思路、逐步推导、结论检查、错因提醒”的顺序讲解；knowledgePoints 每项说明定义/公式、适用条件和本题用法。必须只返回符合 JSON 格式的对象，字段为：analysis（字符串，中文分步详解与错因分析）、knowledgePoints（字符串数组，每项说明知识点及适用条件/本题用法）、"
                    "exercises（恰好 3 个对象组成的数组，每个对象有 level、question、answer 三个字符串字段）。"
                    "三道练习的 level 必须依次为“基础巩固”“方法应用”“综合提升”；围绕本题核心知识点，由易到难，题干清楚，答案必须给出关键步骤和结果；出题后先检查题目条件是否完整、答案推导是否正确、三题是否逐级加深；"
                    "不要照抄原题，只改变数字造成的无效练习。不要加 Markdown 代码围栏。"
                )
                user = (
                    f"学科：{data.get('schoolSubject', '')}\n知识模块：{data.get('module', '')}\n用户自述错因：{data.get('reason', '')}\n\n"
                    f"题目：\n{question}\n\n原错误过程：\n{data.get('wrongWork', '')}\n\n已知参考答案或解析：\n{data.get('solution', '')}"
                )
                raw = self.ollama_chat(
                    [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    json_mode=True,
                )
                if raw.startswith("```"):
                    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                result = json.loads(raw)
                exercises = result.get("exercises")
                points = result.get("knowledgePoints")
                analysis = result.get("analysis")
                if not isinstance(analysis, str) or not analysis.strip() or not isinstance(points, list) or not points:
                    raise RuntimeError("模型返回的详解或知识点不完整，请重试。")
                if not isinstance(exercises, list) or len(exercises) != 3:
                    raise RuntimeError("模型没有返回恰好三道练习，请重试。")
                expected = ["基础巩固", "方法应用", "综合提升"]
                normalized = []
                for index, level in enumerate(expected):
                    matches = [item for item in exercises if isinstance(item, dict) and item.get("level") == level]
                    item = matches[0] if matches else exercises[index]
                    if not isinstance(item, dict) or not str(item.get("question", "")).strip() or not str(item.get("answer", "")).strip():
                        raise RuntimeError("模型返回的练习题目不完整，请重试。")
                    normalized.append({"level": level, "question": str(item["question"]),
                                       "answer": str(item.get("answer", ""))})
                self.send_json({"ok": True, "analysis": analysis,
                                "knowledgePoints": [str(item) for item in points], "exercises": normalized})
                return

            if path in ("/api/math-ocr", "/api/vision-correct"):
                if path == "/api/math-ocr":
                    images = [self.image_base64(data.get("image"))]
                    prompt = (
                        "请准确转写图片中的数学题文字、数字、公式、上下标、分数、根号、单位和选项。数学表达式尽量使用 LaTeX 标记。"
                        "不确定处用【不确定】标明。只输出转写结果，不要解题。"
                    )
                else:
                    raw_images = data.get("images")
                    if not isinstance(raw_images, list) or not raw_images:
                        raise ValueError("请先上传题目图片。")
                    images = [self.image_base64(item) for item in raw_images]
                    prompt = (
                        f"你是高中题目图片校对助手。学科：{data.get('subject', '数学')}\n"
                        f"已有 OCR 文本（可能有错误）：\n{data.get('ocrText', '')}\n\n"
                        "请逐行核对图片原文，尽量还原完整题干、公式、单位、选项和图表标注。保留原题结构；不要擅自解题或补全图片中看不清的内容。"
                        "不确定的文字、数字、符号请用【不确定】标记，并简短说明需要人工核对的位置。只输出校对后的题目文本。"
                    )
                text = self.ollama_chat([{"role": "user", "content": prompt, "images": images}])
                if path == "/api/math-ocr":
                    self.send_json({"ok": True, "text": text, "latex": ""})
                else:
                    self.send_json({"ok": True, "text": text})
                return
            self.send_json({"ok": False, "error": "不支持的本机 AI 接口。"}, 404)
        except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
            self.send_json({"ok": False, "error": str(exc)}, 400)
        except Exception as exc:
            self.send_json({"ok": False, "error": f"本机 AI 处理失败：{exc}"}, 500)


def main() -> None:
    try:
        server = ThreadingHTTPServer((HOST, PORT), LocalHandler)
    except OSError as exc:
        print("本机服务启动失败。请关闭占用 8765 端口的程序后重试。")
        print(exc)
        input("按回车退出")
        return
    server.daemon_threads = True
    print("知错智能错题本本机版已启动。")
    print(f"网页地址：{BASE_URL}/")
    print("AI 请求仅发送到本机 Ollama。关闭此窗口即可停止服务。")
    if LAN_MODE:
        print("手机访问模式已开启：请确认手机与电脑连接同一 Wi-Fi。")
        print("在电脑命令提示符运行 ipconfig，找到当前 Wi-Fi/WLAN 的 IPv4 地址。")
        print(f"然后在手机浏览器打开：http://电脑的IPv4地址:{PORT}/")
        print("若 Windows 防火墙询问，请只允许“专用网络”。不要在公共 Wi-Fi 使用此模式。")
    threading.Timer(0.8, lambda: webbrowser.open(f"{BASE_URL}/")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
