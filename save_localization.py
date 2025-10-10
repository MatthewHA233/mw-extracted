# save_localization.py
# mitmproxy addon: Save localization / bundle / json responses automatically
# 用法: mitmproxy -s save_localization.py -p 8888
# or: mitmweb -s save_localization.py

from mitmproxy import http, ctx
from pathlib import Path
import re
import json
import time
import urllib.parse
import os

# 输出目录（默认：脚本所在目录下的 MW资源/captured_network）
BASE_OUT = Path(__file__).parent / "MW资源" / "captured_network"
BASE_OUT.mkdir(parents=True, exist_ok=True)

# 匹配 URL 或响应体的关键词（小写匹配）
URL_KEYWORDS = ["local", "localization", "bundle", "string", "strings", "catalog", "lang", ".json"]
BODY_KEYWORDS = [b"ship_", b"weapon_", b"localiz", b"lang", b"\"ship_", b"\"weapon_"]

# 最长保存文件名长度
MAX_FILENAME_LEN = 180

def safe_filename(s: str) -> str:
    # 基本清理，保留常用字符
    s = re.sub(r"[\\/:*?\"<>|]+", "_", s)
    if len(s) > MAX_FILENAME_LEN:
        s = s[:MAX_FILENAME_LEN]
    return s

def guess_extension_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    ext = Path(path).suffix
    if ext:
        return ext
    return ""

def save_binary(path: Path, data: bytes):
    with open(path, "wb") as f:
        f.write(data)

def save_text_json(path: Path, data: bytes):
    try:
        obj = json.loads(data.decode("utf-8"))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        # 不是合法 json
        return False

class Saver:
    def __init__(self):
        self.num_saved = 0

    def response(self, flow: http.HTTPFlow) -> None:
        # 只处理有响应的流量
        if not flow.response:
            return

        url = flow.request.pretty_url or ""
        url_l = url.lower()

        # 先基于 URL 关键字检查
        url_hit = any(k in url_l for k in URL_KEYWORDS)

        # 再基于 body 检查字节关键词（避免大量误判，先检查 small size）
        body = flow.response.content or b""
        body_hit = False
        if body:
            # 如果 body 包含关键词，标记为命中
            for token in BODY_KEYWORDS:
                if token in body:
                    body_hit = True
                    break

        # 如果 URL 或 body 命中，则保存
        if url_hit or body_hit:
            ts = time.strftime("%Y%m%d_%H%M%S")
            host = flow.request.host or "host"
            safe_url = safe_filename(url.replace("http://", "").replace("https://", ""))
            ext = guess_extension_from_url(url)
            # 如果响应 Content-Type 指示 JSON，优先 .json
            ctype = flow.response.headers.get("Content-Type", "")
            if "application/json" in ctype.lower() or ext.lower() == ".json":
                ext = ".json"
            elif ext == "":
                # 如果不确定扩展名，尝试解析 JSON 成功则用 .json，否则用 .bin 或 .bundle
                ext = ""
            # 构造文件名
            base_name = f"{ts}__{host}__{safe_url}"
            base_name = base_name.replace("/", "_")
            if ext:
                file_path = BASE_OUT / (base_name + ext)
            else:
                # 尝试先保存为 json (pretty) — 若失败则保存二进制 .bin
                tentative_json = BASE_OUT / (base_name + ".json")
                if save_text_json(tentative_json, body):
                    ctx.log.info(f"[saved-json] {tentative_json}")
                    self.num_saved += 1
                    return
                file_path = BASE_OUT / (base_name + ".bin")

            # 防重名：若已存在，追加编号
            i = 1
            orig_file_path = file_path
            while file_path.exists():
                file_path = orig_file_path.with_name(orig_file_path.stem + f"_{i}" + orig_file_path.suffix)
                i += 1

            # 如果 content-type 是 json but decoding failed, still save raw bytes with .json or .bin
            if file_path.suffix.lower() == ".json":
                if not save_text_json(file_path, body):
                    # fallback to binary
                    file_path = file_path.with_suffix(".bin")
                    save_binary(file_path, body)
                    ctx.log.info(f"[saved-bin-fallback] {file_path}")
                else:
                    ctx.log.info(f"[saved-json] {file_path}")
            else:
                save_binary(file_path, body)
                ctx.log.info(f"[saved-bin] {file_path}")

            self.num_saved += 1

addons = [
    Saver()
]
