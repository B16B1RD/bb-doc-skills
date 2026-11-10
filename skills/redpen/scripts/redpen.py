#!/usr/bin/env python3
"""redpen: 文書をブラウザで表示し、朱（コメント）を付けるための道具。

Python 3.9 以上の標準ライブラリだけで動く。本文は書き換えない。朱は対象ファイルの
隣の `<対象ファイル>.review.json` に保存する。

  python3 redpen.py <file> [--port N]   ローカルサーバーを起動する（127.0.0.1 のみ）
  python3 redpen.py <file> --static     サーバーなしで開ける HTML を、対象ファイルの隣の
                                        `<対象ファイル>.redpen.html` に書き出す（図などの
                                        隣のファイルは同じフォルダから読むので、動かさずに開く）

サーバーは対象ファイルのフォルダの中のファイルだけを、ページと同じ階層のパスで返す
（Markdown や HTML の中の `./fig-1.svg` のような相対パスをそのまま表示するため）。
Host と Origin を検証し、ほかのオリジンからの要求を拒否する。

終了コード: 0 = 正常（--static は書き出し完了）、2 = 対象を読めないなどの起動エラー。
"""

import argparse
import json
import mimetypes
import os
import re
import sys
import tempfile
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

LABEL_LIMIT = 80
# スクリプトを動かさずに表示する型。これ以外の隣のファイルは、最上位で開いても sandbox で動かす
# （スクリプトを動かせる型は HTML・SVG・XML 系と多く、数えきれないので、逆に安全な側を数える）
PLAIN_TYPES = {"application/pdf", "text/plain", "text/css", "text/markdown", "application/json"}
PLAIN_FAMILIES = ("image/", "audio/", "video/", "font/")


def needs_sandbox(ctype):
    if ctype == "image/svg+xml":
        return True
    ctype = ctype.split(";", 1)[0].strip()
    return not (ctype in PLAIN_TYPES or ctype.startswith(PLAIN_FAMILIES))


def atomic_write_text(path, text):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".redpen-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        try:
            os.chmod(tmp, os.stat(path).st_mode & 0o777)
        except FileNotFoundError:
            pass
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def is_html(path):
    return path.suffix.lower() in (".html", ".htm")


def storable(value):
    """UTF-8 で保存できる文字列か。単独のサロゲート（絵文字などの半分だけ）を含む文字列は保存できない。"""
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _front_matter_close(lines):
    if not lines or lines[0].rstrip() != "---":
        return None
    for j in range(1, len(lines)):
        if lines[j].rstrip() == "---":
            return j
    return None


def parse_blocks(text):
    """Markdown を空行で区切ったブロックに分ける。

    先頭の front matter（--- から次の --- まで）とコードの囲み（``` / ~~~）は、
    中に空行があっても 1 ブロックにする。戻り値は [{"id", "src"}]。
    """
    lines = text.split("\n")
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].strip() == "":
            i += 1
            continue
        start = i
        fm_close = _front_matter_close(lines) if i == 0 else None
        if fm_close is not None:
            i = fm_close + 1
        else:
            fence_char, fence_len = "", 0
            while i < n:
                stripped = lines[i].strip()
                if fence_len:
                    i += 1
                    m = re.match(r"^(`+|~+)\s*$", stripped)
                    if m and m.group(1)[0] == fence_char and len(m.group(1)) >= fence_len:
                        fence_len = 0
                    continue
                if stripped == "":
                    break
                m = re.match(r"^(`{3,}|~{3,})", stripped)
                if m:
                    fence_char, fence_len = m.group(1)[0], len(m.group(1))
                i += 1
        blocks.append({"id": len(blocks), "src": "\n".join(lines[start:i]).rstrip()})
    return blocks


def read_target(target):
    # 先頭の BOM（U+FEFF）は読み飛ばす。残すと、1 行目の見出し・front matter・フェンスがそれと読まれない
    text = target.read_text(encoding="utf-8-sig")
    if is_html(target):
        return {"mode": "html", "html": text}
    return {"mode": "md", "blocks": parse_blocks(text)}


class ReviewFile:
    """`<対象>.review.json` の読み書き。読めないファイルは .bak に退避して空から始める。

    前の退避が残っていれば .bak.1、.bak.2 … と空いている名前に退避し、前の退避を上書きしない。
    """

    def __init__(self, target):
        self.path = Path(str(target) + ".review.json")
        self.lock = threading.Lock()

    def load(self):
        try:
            raw = self.path.read_bytes()
        except FileNotFoundError:
            return {"comments": []}
        try:
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("comments"), list):
                raise ValueError("comments の配列がありません")
            if not all(isinstance(c, dict) and isinstance(c.get("id"), str) for c in data["comments"]):
                raise ValueError("comments の要素が、id を持つ朱の形ではありません")
            # 単独のサロゲート（\ud800 など）は読めても UTF-8 で保存し直せず、保存が失敗し続ける
            json.dumps(data, ensure_ascii=False).encode("utf-8")
            return data
        except (ValueError, RecursionError) as e:
            bak = self.move_aside(raw)
            print(f"redpen: WARNING: {self.path.name} を読めないため {bak.name} へ退避しました（{e}）",
                  file=sys.stderr)
            return {"comments": []}

    def move_aside(self, raw):
        """読めなかった中身を、空いている名前に排他的に書いてから、元のファイルを消す。

        名前は open の "x" で取るので、別のプロセス（同じ文書の別の redpen）と同時でも、既にある退避を
        上書きしない。元のファイルは、中身がまだ読めなかったものと同じときだけ消す（別のプロセスが
        退避の後に書いた正しい朱を消さない）。

        守らない範囲: 2 つのプロセスが同時に退避すると、同じ中身の退避が 2 つできることがある。中身を
        比べてから消すまでの間に、別のプロセスが正しい朱を書くと、それを消す（単一ユーザーの開発機で、
        同じ文書に redpen を 2 つ起動し、その瞬間に保存が重なったときだけ）。
        """
        k = 0
        while True:
            bak = Path(str(self.path) + (".bak" if k == 0 else f".bak.{k}"))
            try:
                with open(bak, "xb") as f:
                    f.write(raw)
                break
            except FileExistsError:
                k += 1
        try:
            if self.path.read_bytes() == raw:
                self.path.unlink()
        except FileNotFoundError:
            pass
        return bak

    def save(self, data):
        atomic_write_text(self.path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    def add(self, target, label, text):
        with self.lock:
            data = self.load()
            used = {c.get("id") for c in data["comments"]}
            k = 1
            while f"c{k}" in used:
                k += 1
            comment = {
                "id": f"c{k}",
                "target": target,
                "label": label[:LABEL_LIMIT],
                "text": text,
                "status": "open",
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
            data["comments"].append(comment)
            self.save(data)
            return comment

    def set_status(self, cid, status):
        with self.lock:
            data = self.load()
            for c in data["comments"]:
                if c.get("id") == cid:
                    c["status"] = status
                    self.save(data)
                    return c
            return None

    def mtime(self):
        try:
            return self.path.stat().st_mtime_ns
        except OSError:
            return 0


def valid_target(value):
    return isinstance(value, str) and re.fullmatch(r"block:\d+|selector:.+", value, re.S) is not None


def make_handler(target, review, port_box):
    root = target.parent

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            pass

        def send_bytes(self, status, body, ctype, extra=()):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            for key, value in extra:
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status, obj):
            self.send_bytes(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                            "application/json; charset=utf-8")

        def read_json(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0:
                    return None
                raw = self.rfile.read(length) if length else b""
                return json.loads(raw.decode("utf-8")) if raw else {}
            except (ValueError, UnicodeDecodeError):
                return None

        def do_GET(self):
            self.handle_with(self.route_get)

        def do_POST(self):
            self.handle_with(self.route_post)

        def do_PATCH(self):
            self.handle_with(self.route_patch)

        def handle_with(self, route):
            try:
                if not self.origin_ok():
                    self.close_connection = True
                    self.send_json(403, {"error": "ほかのオリジンからの要求を拒否しました"})
                    return
                route()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                self.close_connection = True
                try:
                    self.send_json(500, {"error": f"{e.__class__.__name__}: {e}"})
                except OSError:
                    pass

        def origin_ok(self):
            # 127.0.0.1 で待ち受けても、ブラウザの中のほかのページからは要求が届く。
            # Host で DNS rebinding を、Origin でほかのオリジンからの書き込みを止める。
            port = port_box[0]
            allowed = (f"127.0.0.1:{port}", f"localhost:{port}")
            if self.headers.get("Host", "") not in allowed:
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin not in tuple("http://" + a for a in allowed):
                return False
            return True

        def route_get(self):
            path = urlsplit(self.path).path
            if path == "/":
                cfg = {"server": True, "name": target.name}
                self.send_bytes(200, render_app(cfg).encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/doc":
                try:
                    doc = read_target(target)
                except (OSError, UnicodeDecodeError) as e:
                    self.send_json(500, {"error": f"{target.name} を読めません: {e}"})
                    return
                self.send_json(200, doc)
            elif path == "/api/comments":
                with review.lock:
                    comments = review.load()
                self.send_json(200, comments)
            elif path == "/api/version":
                try:
                    doc_m = target.stat().st_mtime_ns
                except OSError:
                    doc_m = 0
                self.send_json(200, {"doc": str(doc_m), "comments": str(review.mtime())})
            elif path.startswith("/api/"):
                self.send_json(404, {"error": "not found"})
            else:
                self.serve_sibling(path)

        def serve_sibling(self, path):
            # 対象ファイルのフォルダの中の通常ファイルだけを返す。.. や symlink で外へ出る
            # パスは、実体のパスがフォルダの外になるので返さない。
            rel = unquote(path).lstrip("/")
            try:
                real = (root / rel).resolve(strict=True)
                real.relative_to(root)
            except (OSError, ValueError, RuntimeError):
                self.send_json(404, {"error": "not found"})
                return
            if not real.is_file():
                self.send_json(404, {"error": "not found"})
                return
            ctype = mimetypes.guess_type(real.name)[0] or "application/octet-stream"
            if real.suffix.lower() == ".svg":
                ctype = "image/svg+xml"
            if ctype in ("text/plain", "text/markdown"):
                # 文書スキルの書く文書は UTF-8。HTML・CSS は文書の中の charset の指定に任せる
                ctype += "; charset=utf-8"
            # 最上位で開いても、中のスクリプトを動かさない（allow-scripts を付けない sandbox）。朱の API を
            # 呼ばせないため。PDF などには付けない（ブラウザが表示を止める）
            extra = (("Content-Security-Policy", "sandbox"),) if needs_sandbox(ctype) else ()
            self.send_bytes(200, real.read_bytes(), ctype, extra=extra)

        def route_post(self):
            if urlsplit(self.path).path != "/api/comments":
                self.send_json(404, {"error": "not found"})
                return
            body = self.read_json()
            if (not isinstance(body, dict) or not valid_target(body.get("target"))
                    or not isinstance(body.get("text"), str) or not body["text"].strip()):
                self.send_json(400, {"error": "target（block:<n> か selector:<css>）と text が要ります"})
                return
            label = body.get("label") if isinstance(body.get("label"), str) else ""
            if storable(body["target"]) and storable(label) and storable(body["text"]):
                self.send_json(200, {"comment": review.add(body["target"], label, body["text"])})
            else:
                # そのまま保存すると UnicodeEncodeError で 500 になり、朱のファイルは書かれない
                self.send_json(400, {"error": "保存できない文字（半分だけの絵文字など）が、朱の場所・抜粋・本文のどれかにあります"})

        def route_patch(self):
            m = re.fullmatch(r"/api/comments/([A-Za-z0-9_-]+)", urlsplit(self.path).path)
            if not m:
                self.send_json(404, {"error": "not found"})
                return
            body = self.read_json()
            if not isinstance(body, dict) or body.get("status") not in ("open", "resolved"):
                self.send_json(400, {"error": "status は open か resolved です"})
                return
            comment = review.set_status(m.group(1), body["status"])
            if comment is None:
                self.send_json(404, {"error": "その朱はありません"})
                return
            self.send_json(200, {"comment": comment})

    return Handler


class Server(ThreadingHTTPServer):
    daemon_threads = True


def create_server(target, port=0):
    """(httpd, review) を返す。試験からも使う。"""
    review = ReviewFile(target)
    review.load()
    port_box = [port]
    httpd = Server(("127.0.0.1", port), make_handler(target, review, port_box))
    port_box[0] = httpd.server_address[1]
    return httpd, review


def write_static(target):
    """サーバーなしで開ける HTML を書き出し、そのパスを返す。"""
    review = ReviewFile(target)
    cfg = {
        "server": False,
        "name": target.name,
        "doc": read_target(target),
        "comments": review.load()["comments"],
        "storageKey": "redpen:" + str(target),
    }
    out = Path(str(target) + ".redpen.html")
    atomic_write_text(out, render_app(cfg))
    return out


def render_app(cfg):
    # json.dumps は < > & を逃がさないので、本文の </script> でスクリプトが閉じないよう \u で書く
    data = json.dumps(cfg, ensure_ascii=False)
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    data = data.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return APP_HTML.replace("__CFG__", data)


def main(argv=None):
    parser = argparse.ArgumentParser(description="文書をブラウザで表示し、朱を付ける")
    parser.add_argument("file", help="対象の Markdown か HTML のファイル")
    parser.add_argument("--port", type=int, default=0, help="待ち受けるポート（省略時は空きを自動で選ぶ）")
    parser.add_argument("--static", action="store_true", help="サーバーを起動せず、対象ファイルの隣に HTML を書き出す")
    args = parser.parse_args(argv)

    target = Path(args.file).expanduser().resolve()
    if not target.is_file():
        print(f"redpen: ERROR: ファイルがありません: {target}", file=sys.stderr)
        return 2
    try:
        target.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        print(f"redpen: ERROR: UTF-8 のテキストとして読めません: {target} ({e})", file=sys.stderr)
        return 2

    try:
        ReviewFile(target).load()
    except OSError as e:
        print(f"redpen: ERROR: 朱のファイルを扱えません: {e}", file=sys.stderr)
        return 2

    if args.static:
        try:
            out = write_static(target)
        except OSError as e:
            print(f"redpen: ERROR: 書き出せません: {e}", file=sys.stderr)
            return 2
        print(f"redpen: static {out}", flush=True)
        return 0

    try:
        httpd, _ = create_server(target, port=args.port)
    except OSError as e:
        print(f"redpen: ERROR: ポート {args.port} で待ち受けられません: {e}", file=sys.stderr)
        return 2
    print(f"redpen: http://127.0.0.1:{httpd.server_address[1]}/ ({target})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


APP_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>朱入れ</title>
<style>
:root { --bg:#faf8f4; --panel:#ffffff; --ink:#1f1d1a; --muted:#6b665e; --line:#e2ddd3;
  --red:#c03a22; --red-soft:#fbe9e4; --ok:#2f6b3a; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#1b1a18; --panel:#24221f; --ink:#ece8e1; --muted:#a39d93; --line:#3a3732;
    --red:#ef7a62; --red-soft:#3a2420; --ok:#8cc596; }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.75 system-ui, -apple-system, "Hiragino Sans", "Noto Sans JP", sans-serif; }
header { position:sticky; top:0; z-index:5; display:flex; flex-wrap:wrap; gap:8px; align-items:center;
  padding:8px 16px; background:var(--panel); border-bottom:1px solid var(--line); }
header h1 { font-size:15px; margin:0 8px 0 0; }
button { font:inherit; font-size:13px; padding:4px 10px; border:1px solid var(--line); border-radius:6px;
  background:var(--panel); color:var(--ink); cursor:pointer; }
button.primary { background:var(--red); border-color:var(--red); color:#fff; }
button[aria-pressed="true"] { background:var(--red-soft); border-color:var(--red); color:var(--red); }
#status { font-size:12px; color:var(--muted); margin-left:auto; }
#notice, #unsaved { display:none; padding:8px 16px; background:var(--red-soft); color:var(--ink); font-size:13px; }
#notice.show, #unsaved.show { display:block; }
.wrap { display:grid; grid-template-columns:minmax(0,1fr) 320px; gap:16px; padding:16px; }
@media (max-width: 860px) { .wrap { grid-template-columns:minmax(0,1fr); } }
#doc { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:8px 24px; min-width:0; }
#doc.html { padding:0; }
#doc iframe { display:block; width:100%; height:calc(100vh - 110px); border:0; border-radius:8px; background:#fff; }
.block { position:relative; padding:2px 6px; margin:0 -6px; border-radius:6px; border-left:3px solid transparent; }
.on .block:hover { background:var(--red-soft); cursor:pointer; }
.block.has { border-left-color:var(--red); }
.block table { border-collapse:collapse; margin:8px 0; display:block; overflow-x:auto; }
.block th, .block td { border:1px solid var(--line); padding:4px 8px; }
.block img { max-width:100%; height:auto; }
.block pre { background:var(--bg); padding:8px 12px; border-radius:6px; overflow-x:auto; }
.block code { font-family:ui-monospace, Menlo, Consolas, monospace; font-size:13px; }
.block blockquote { margin:0; padding-left:12px; border-left:3px solid var(--line); color:var(--muted); }
aside { min-width:0; }
.composer, .item { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px 12px; margin-bottom:10px; }
.composer { border-color:var(--red); }
.composer textarea { width:100%; min-height:90px; font:inherit; padding:6px; border:1px solid var(--line);
  border-radius:6px; background:var(--bg); color:var(--ink); }
.where { font-size:12px; color:var(--muted); overflow-wrap:anywhere; }
.chip { display:inline-block; font-size:11px; padding:0 6px; border-radius:10px; background:var(--red-soft); color:var(--red); margin-right:6px; }
.item.resolved { opacity:.6; }
.item.resolved .chip { background:transparent; color:var(--ok); border:1px solid var(--ok); }
.item .text { white-space:pre-wrap; margin:4px 0; }
.row { display:flex; gap:6px; margin-top:6px; }
#copybox { display:none; width:100%; min-height:140px; font:12px ui-monospace, monospace; margin-bottom:10px; }
#copybox.show { display:block; }
.empty { color:var(--muted); font-size:13px; }
</style>
</head>
<body>
<header>
  <h1 id="name"></h1>
  <button id="mode" aria-pressed="true" title="入のとき、本文のクリックで朱を付けます。切にすると本文のボタンやリンクが動きます">朱を付ける: 入</button>
  <button id="copy">朱をまとめてコピー</button>
  <span id="status"></span>
</header>
<div id="notice"></div>
<div id="unsaved"></div>
<div class="wrap">
  <main id="doc"></main>
  <aside>
    <textarea id="copybox" readonly aria-label="コピーする朱"></textarea>
    <div id="composer"></div>
    <div id="list"></div>
  </aside>
</div>
<script>
(function () {
  'use strict';
  var CFG = __CFG__;
  var docEl = document.getElementById('doc');
  var listEl = document.getElementById('list');
  var composerEl = document.getElementById('composer');
  var statusEl = document.getElementById('status');
  var noticeEl = document.getElementById('notice');
  var unsavedEl = document.getElementById('unsaved');
  var modeBtn = document.getElementById('mode');
  var copybox = document.getElementById('copybox');
  var state = { doc: null, comments: [], local: [], redOn: true, pending: null, frame: null, versions: {}, saveError: '' };

  document.getElementById('name').textContent = CFG.name;
  /* 操作の結果（保存した・コピーした・状態を変えられなかった）は setStatus に出す。次の操作の結果が出るまで残る */
  function setStatus(t) { statusEl.textContent = t; }
  /* 知らせの欄は、続いている状態（サーバーに届かない・サーバーが失敗を返す・最初の読み込みに失敗した）だけに使う。
     定期確認（poll）が、版の確認とその回の読み直しまで通り、本文の読み直しの失敗も残っていないときに消す。
     最初の読み込みに失敗したときは、定期確認を始めないので、ページを読み込み直すまで消えない。
     保存できなかった朱の知らせは、別の欄（renderUnsaved）に状態から出す */
  function notice(t) {
    noticeEl.textContent = t;
    noticeEl.classList.toggle('show', !!t);
  }

  /* ---- ここから「ここまで」の印までは、ページの要素に触れない関数。dev/tests/test_redpen.py が node で動かす ---- */
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  /* esc の逆。URL は、逃がす前の字に戻してから判定し、属性に入れるときに 1 回だけ逃がす */
  function unesc(s) {
    return String(s).replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
      .replace(/&amp;/g, '&');
  }
  /* スキーム（javascript: など）のある URL を通さないための判定。通すのは、http(s)・mailto、ページ内の #、
     / か ./ か ../ で始まるパス、コロンを 1 つも含まない相対パス（日本語や % で始まる名前を含む）だけ */
  function safeUrl(u) { return /^(https?:\/\/|mailto:|#|\.{0,2}\/|[^:]*$)/i.test(u); }
  /* 朱の抜粋を 80 字までにする。UTF-16 の単位でなく文字（コードポイント）で数え、半分だけの文字（単独の
     サロゲート）は落とす。単位で切ると絵文字などの半分が末尾に残り、UTF-8 で保存できない。HTML の文書の枠
     （FRAME_SCRIPT）は単位で切って送ってくるので、その末尾の半分もここで落ちる。数えるのは見た目の 1 文字では
     ないので、いくつかの文字をつないだ絵文字（家族・国旗など）は途中で切れることがある（保存はできる） */
  function clip(s) {
    return Array.from(String(s)).filter(function (ch) { return !/^[\uD800-\uDFFF]$/.test(ch); }).slice(0, 80).join('');
  }
  /* 書きかけの朱。抜粋はここで切る */
  function draftOf(target, label) { return { target: target, label: clip(label) }; }
  /* サーバーが付ける時刻と同じ形（その場所の時刻と UTC との差。例 2026-11-10T12:34:56+0900） */
  function nowStamp(d) {
    d = d || new Date();
    var p = function (n) { return String(n).padStart(2, '0'); };
    var off = -d.getTimezoneOffset(), a = Math.abs(off);
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + 'T' + p(d.getHours()) + ':' +
      p(d.getMinutes()) + ':' + p(d.getSeconds()) + (off < 0 ? '-' : '+') + p(Math.floor(a / 60)) + p(a % 60);
  }
  /* このページにだけ置く朱（サーバーなしで付けた朱と、サーバーに保存できなかった朱）。サーバーが保存する朱と同じ形 */
  function localComment(id, body, d) {
    return { id: id, target: body.target, label: body.label, text: body.text, status: 'open', createdAt: nowStamp(d) };
  }
  /* 1 行の中の記法を HTML にする。組み立てたタグ（コード、画像、リンクの開始タグ）は控えに入れて印（\u0000 番号
     \u0000）に替え、最後に戻す。後ろの置き換えが、前の置き換えの作ったタグを本文として読み直さないようにするため
     （読み直すと、画像の URL の中にリンクを書いた行から、タグの属性を作れてしまう）。印の字は本文から先に除き、
     URL には許さない */
  function inline(s) {
    var kept = [];
    function keep(html) { kept.push(html); return '\u0000' + (kept.length - 1) + '\u0000'; }
    function back(x) { return x.replace(/\u0000(\d+)\u0000/g, function (_, i) { return back(kept[+i]); }); }
    s = s.replace(/\u0000/g, '').replace(/`([^`]+)`/g, function (_, c) { return keep('<code>' + esc(c) + '</code>'); });
    s = esc(s)
      .replace(/!\[([^\]]*)\]\(([^)\s\u0000]+)\)/g, function (m, alt, u) {
        u = unesc(u);
        return safeUrl(u) ? keep('<img alt="' + alt + '" src="' + esc(u) + '">') : m;
      })
      .replace(/\[([^\]]+)\]\(([^)\s\u0000]+)\)/g, function (m, t, u) {
        u = unesc(u);
        return safeUrl(u) ? keep('<a href="' + esc(u) + '" target="_blank" rel="noopener">') + t + '</a>' : t + ' (' + esc(u) + ')';
      })
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>');
    return back(s);
  }
  function cells(line) {
    return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(function (c) { return c.trim(); });
  }
  function renderMdList(lines) {
    var out = '', stack = [];
    lines.forEach(function (l) {
      var m = l.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
      if (!m) { out += ' ' + inline(l.trim()); return; }
      var depth = Math.floor(m[1].replace(/\t/g, '    ').length / 2);
      var tag = /\d/.test(m[2]) ? 'ol' : 'ul';
      while (stack.length > depth + 1) out += '</li></' + stack.pop() + '>';
      if (stack.length < depth + 1) {
        /* 空行で区切った番号付きリストは項目ごとに別のブロックになるので、書いてある番号から始める。
           桁の多い番号（CommonMark が番号と認めるのは 9 桁まで）の扱いは決めていない */
        var first = tag === 'ol' ? parseInt(m[2], 10) : 1;
        out += first === 1 ? '<' + tag + '>' : '<ol start="' + first + '">';
        stack.push(tag);
      }
      else out += '</li>';
      out += '<li>' + inline(m[3]);
    });
    while (stack.length) out += '</li></' + stack.pop() + '>';
    return out;
  }
  function renderMd(src) {
    var lines = src.split('\n');
    if (/^(```|~~~)/.test(lines[0].trim())) {
      return '<pre><code>' + esc(lines.slice(1, /^(```|~~~)/.test(lines[lines.length - 1].trim()) ? -1 : undefined).join('\n')) + '</code></pre>';
    }
    if (lines[0].trim() === '---' && lines.length > 1 && lines[lines.length - 1].trim() === '---') {
      return '<pre><code>' + esc(src) + '</code></pre>';
    }
    if (lines.length >= 2 && /\|/.test(lines[0]) && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/.test(lines[1])) {
      var head = cells(lines[0]).map(function (c) { return '<th>' + inline(c) + '</th>'; }).join('');
      var body = lines.slice(2).map(function (l) {
        return '<tr>' + cells(l).map(function (c) { return '<td>' + inline(c) + '</td>'; }).join('') + '</tr>';
      }).join('');
      return '<table><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table>';
    }
    var h = lines[0].match(/^(#{1,6})\s+(.*)$/);
    if (h && lines.length === 1) return '<h' + h[1].length + '>' + inline(h[2]) + '</h' + h[1].length + '>';
    if (lines.length === 1 && /^(\*{3,}|-{3,}|_{3,})$/.test(lines[0].trim())) return '<hr>';
    if (/^\s*([-*+]|\d+[.)])\s/.test(lines[0])) return renderMdList(lines);
    if (lines.every(function (l) { return /^\s*>/.test(l); })) {
      return '<blockquote>' + renderMd(lines.map(function (l) { return l.replace(/^\s*>\s?/, ''); }).join('\n')) + '</blockquote>';
    }
    var html = '';
    if (h) { html += '<h' + h[1].length + '>' + inline(h[2]) + '</h' + h[1].length + '>'; lines = lines.slice(1); }
    return html + '<p>' + lines.map(inline).join('<br>') + '</p>';
  }
  function plain(src) { return src.replace(/[#>*`|\[\]!_-]/g, ' ').replace(/\([^)]*\)/g, ' ').replace(/\s+/g, ' ').trim(); }
  /* ---- ここまで ---- */

  /* ---- 朱の場所 ---- */
  function blockFor(c) {
    var blocks = state.doc && state.doc.blocks || [];
    var m = /^block:(\d+)$/.exec(c.target);
    var label = (c.label || '').trim();
    if (m && blocks[+m[1]] && (!label || plain(blocks[+m[1]].src).indexOf(label.slice(0, 20)) === 0)) return +m[1];
    if (label) {
      for (var i = 0; i < blocks.length; i++) if (plain(blocks[i].src).indexOf(label.slice(0, 20)) !== -1) return i;
    }
    return -1;
  }

  /* ---- Markdown 表示 ---- */
  function renderDoc() {
    docEl.innerHTML = '';
    docEl.className = state.redOn ? 'on' : '';
    if (state.doc.mode === 'html') { renderHtml(); return; }
    var openAt = {};
    allComments().forEach(function (c) { if (c.status !== 'resolved') { var b = blockFor(c); if (b >= 0) openAt[b] = 1; } });
    state.doc.blocks.forEach(function (b) {
      var d = document.createElement('div');
      d.className = 'block' + (openAt[b.id] ? ' has' : '');
      d.innerHTML = renderMd(b.src);
      d.addEventListener('click', function (e) {
        if (!state.redOn) return;
        e.preventDefault();
        openComposer('block:' + b.id, plain(b.src));
      });
      docEl.appendChild(d);
    });
  }

  /* ---- HTML 表示 ---- */
  var FRAME_SCRIPT = '<scr' + 'ipt>(function(){var on=true,marks=[];' +
    'function css(el){if(!el||el===document.documentElement)return "html";var p=css(el.parentElement);' +
    'var t=el.tagName.toLowerCase(),i=1,s=el;while((s=s.previousElementSibling)){if(s.tagName===el.tagName)i++;}' +
    'return p+" > "+t+":nth-of-type("+i+")";}' +
    'function find(sel,label){var el=null;try{el=document.querySelector(sel);}catch(e){}' +
    'var k=(label||"").slice(0,20);if(el&&(!k||(el.textContent||"").replace(/\\s+/g," ").indexOf(k)!==-1))return el;' +
    'if(!k)return null;var all=document.body?document.body.getElementsByTagName("*"):[],best=null;' +
    'for(var j=0;j<all.length;j++){if((all[j].textContent||"").replace(/\\s+/g," ").indexOf(k)!==-1)best=all[j];}return best;}' +
    'addEventListener("message",function(e){var d=e.data||{};if(d.type==="redpen-mode")on=!!d.on;' +
    'if(d.type==="redpen-marks"){marks.forEach(function(m){m.style.outline="";});marks=[];' +
    '(d.items||[]).forEach(function(it){var el=find(it.selector,it.label);if(el){el.style.outline="2px solid #c03a22";marks.push(el);}});}});' +
    'document.addEventListener("mouseover",function(e){if(!on)return;e.target.__o=e.target.style.outline;e.target.style.outline="2px dashed #c03a22";},true);' +
    'document.addEventListener("mouseout",function(e){if(e.target.__o!==undefined){e.target.style.outline=e.target.__o;delete e.target.__o;}},true);' +
    'document.addEventListener("click",function(e){' +
    'if(on){e.preventDefault();e.stopPropagation();var el=e.target;if(el.__o!==undefined){el.style.outline=el.__o;delete el.__o;}' +
    'parent.postMessage({type:"redpen-pick",selector:css(el),label:(el.textContent||"").replace(/\\s+/g," ").trim().slice(0,80)},"*");return;}' +
    'var a=e.target.closest&&e.target.closest("a[href^=\\"#\\"]");if(a){var id=decodeURIComponent(a.getAttribute("href").slice(1));' +
    'var t=document.getElementById(id)||document.getElementsByName(id)[0];e.preventDefault();if(t)t.scrollIntoView({behavior:"smooth",block:"start"});}' +
    '},true);parent.postMessage({type:"redpen-ready"},"*");})();</scr' + 'ipt>';

  function renderHtml() {
    docEl.className = 'html';
    var f = document.createElement('iframe');
    /* サーバー方式では本文のスクリプトに API を呼ばせないため、別のオリジンに置く。
       サーバーなしの方式は書き込み先が無く、同じオリジンにしないと隣の画像を file:// から読めない */
    f.setAttribute('sandbox', 'allow-scripts allow-popups' + (CFG.server ? '' : ' allow-same-origin'));
    f.setAttribute('title', CFG.name);
    var html = state.doc.html;
    /* 末尾に足す。</body> や </html> の後ろのスクリプトも、ブラウザは本文に戻して実行するので、
       本文の中の </body> の文字列を探さない */
    f.srcdoc = html + FRAME_SCRIPT;
    state.frame = f;
    docEl.appendChild(f);
  }
  function syncFrame() {
    if (!state.frame || !state.frame.contentWindow) return;
    state.frame.contentWindow.postMessage({ type: 'redpen-mode', on: state.redOn }, '*');
    var items = allComments().filter(function (c) { return c.status !== 'resolved' && /^selector:/.test(c.target); })
      .map(function (c) { return { selector: c.target.slice(9), label: c.label }; });
    state.frame.contentWindow.postMessage({ type: 'redpen-marks', items: items }, '*');
  }
  window.addEventListener('message', function (e) {
    if (!state.frame || e.source !== state.frame.contentWindow) return;
    var d = e.data || {};
    if (d.type === 'redpen-ready') syncFrame();
    if (d.type === 'redpen-pick' && typeof d.selector === 'string') openComposer('selector:' + d.selector, String(d.label || ''));
  });

  /* ---- 朱を書く ---- */
  function openComposer(target, label) {
    state.pending = draftOf(target, label);
    composerEl.innerHTML = '<div class="composer"><div class="where">' + esc(state.pending.label || target) + '</div>' +
      '<textarea id="ctext" placeholder="ここをどう直してほしいか"></textarea>' +
      '<div class="row"><button class="primary" id="csave">朱を保存</button><button id="ccancel">取消</button></div></div>';
    var ta = document.getElementById('ctext');
    ta.focus();
    document.getElementById('ccancel').onclick = closeComposer;
    document.getElementById('csave').onclick = function () {
      var text = ta.value.trim();
      if (!text) { ta.focus(); return; }
      saveComment(state.pending.target, state.pending.label, text);
    };
  }
  function closeComposer() { state.pending = null; composerEl.innerHTML = ''; }

  /* 失敗した応答の理由。サーバーが返した文（error）があればそれを、無ければ状態の番号を使う */
  function refused(r) {
    return r.json().catch(function () { return {}; }).then(function (j) {
      var e = new Error(j.error || 'HTTP ' + r.status);
      e.refused = true;
      throw e;
    });
  }
  /* fetch そのものの失敗（サーバーに届かなかった）に印を付ける */
  function offline(e) { e.offline = true; throw e; }
  /* 読み込みの失敗の知らせ。届かなかったのか、サーバーが失敗を返したのか、届いた内容を扱えなかったのかを言い分ける */
  function loadFailed(e) {
    var what = e.offline ? 'サーバーに届きません' : e.refused ? 'サーバーが失敗を返しました' : '読み込んだ内容を扱えませんでした';
    notice(what + '（' + e.message + '）。付けた朱は「朱をまとめてコピー」で会話に貼れます。');
  }
  /* 朱の読み直しの失敗。版を古いままの印（stale）にして、次の定期確認で読み直す（版を確かめている途中の
     定期確認が、前の版のまま「変わっていない」と見て知らせを消さないように。すでに朱を読みに行っている
     定期確認が、保存より前の中身で通ったときは、知らせが次の定期確認まで消える） */
  function markStale(e) { state.versions.comments = 'stale'; throw e; }
  function saveComment(target, label, text) {
    var body = { target: target, label: label, text: text };
    if (!CFG.server) { addLocal(body); return; }
    /* 保存の失敗として扱うのは、POST が届かなかったときと断られたときだけ。保存できた後の読み直しの失敗は、
       読み込みの失敗の知らせ（loadFailed）に出す（保存できた朱を、このページにもう 1 件足さない） */
    fetch('api/comments', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) return refused(r); })
      .then(function () { closeComposer(); setStatus('朱を保存しました'); loadComments().catch(markStale).catch(loadFailed); },
        function (e) { state.saveError = e.message; addLocal(body); });
  }
  function addLocal(body) {
    var used = {};
    allComments().forEach(function (c) { used[c.id] = 1; });
    /* サーバーなしで付けた朱は、会話に貼って .review.json に取り込んでも id が変わらないよう、
       ほかと重ならない id にする（書き出し直したページで、取り込み済みの控えを id で外すため） */
    var id;
    do { id = 'p' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); } while (used[id]);
    state.local.push(localComment(id, body));
    persistLocal();
    closeComposer();
    setStatus('朱をこのページに保存しました');
    renderAll();
  }
  function persistLocal() {
    if (CFG.server || !CFG.storageKey) return;
    try { localStorage.setItem(CFG.storageKey, JSON.stringify(state.local)); } catch (e) { /* 保存できない環境でも表示は続ける */ }
  }
  function allComments() { return state.comments.concat(state.local); }

  /* ---- 朱の一覧 ---- */
  function renderList() {
    var cs = allComments();
    if (!cs.length) { listEl.innerHTML = '<p class="empty">まだ朱はありません。「朱を付ける: 入」で本文をクリックすると付けられます。</p>'; return; }
    listEl.innerHTML = '';
    cs.forEach(function (c) {
      var d = document.createElement('div');
      var lost = state.doc.mode === 'md' && c.status !== 'resolved' && blockFor(c) < 0;
      d.className = 'item' + (c.status === 'resolved' ? ' resolved' : '');
      d.innerHTML = '<span class="chip">' + (c.status === 'resolved' ? '対応済み' : '朱') + '</span>' +
        '<span class="where">' + esc(c.label || c.target) + (lost ? '（本文が変わり、場所が見つかりません）' : '') + '</span>' +
        '<div class="text">' + esc(c.text) + '</div>';
      if (CFG.server && state.comments.indexOf(c) !== -1) {
        var b = document.createElement('button');
        b.textContent = c.status === 'resolved' ? '開き直す' : '対応済みにする';
        b.onclick = function () { setCommentStatus(c.id, c.status === 'resolved' ? 'open' : 'resolved'); };
        var row = document.createElement('div'); row.className = 'row'; row.appendChild(b); d.appendChild(row);
      }
      listEl.appendChild(d);
    });
  }
  function setCommentStatus(id, status) {
    fetch('api/comments/' + encodeURIComponent(id), { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: status }) })
      .then(function (r) { if (!r.ok) return refused(r); })
      .then(function () { setStatus('朱の状態を変えました'); loadComments().catch(markStale).catch(loadFailed); },
        function (e) { setStatus('朱の状態を変えられませんでした（' + e.message + '）'); });
  }
  /* サーバーに保存できずにこのページにだけある朱の知らせ。朱が残っている間は出し続ける */
  function renderUnsaved() {
    var n = CFG.server ? state.local.length : 0;
    unsavedEl.textContent = n ? 'サーバーに保存できなかった朱が ' + n + ' 件あります（最後の理由: ' + state.saveError +
      '）。この朱はこのページにだけあり、ページを読み込み直すと消えます。「朱をまとめてコピー」で会話に貼ってください。' : '';
    unsavedEl.classList.toggle('show', !!n);
  }
  function renderAll() {
    renderList();
    renderUnsaved();
    if (state.doc.mode === 'md') renderDoc(); else syncFrame();
  }

  /* ---- まとめてコピー ---- */
  document.getElementById('copy').onclick = function () {
    var text = JSON.stringify({ file: CFG.name, comments: allComments() }, null, 2);
    copybox.value = text;
    copybox.classList.add('show');
    copybox.focus();
    copybox.select();
    var done = function () { setStatus('朱をコピーしました。会話に貼ってください'); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { setStatus('下の枠の中身をコピーしてください'); });
    } else { setStatus('下の枠の中身をコピーしてください'); }
  };

  modeBtn.onclick = function () {
    state.redOn = !state.redOn;
    modeBtn.setAttribute('aria-pressed', String(state.redOn));
    modeBtn.textContent = '朱を付ける: ' + (state.redOn ? '入' : '切');
    if (state.doc.mode === 'md') docEl.className = state.redOn ? 'on' : ''; else syncFrame();
  };

  /* ---- 読み込みと更新の監視 ---- */
  function getJson(u) {
    return fetch(u, { cache: 'no-store' }).then(function (r) {
      return r.ok ? r.json() : refused(r);
    }, offline);
  }
  function loadDoc() { return getJson('api/doc').then(function (d) { state.doc = d; }); }
  function loadComments() { return getJson('api/comments').then(function (d) { state.comments = d.comments || []; renderAll(); }); }
  function poll() {
    getJson('api/version').then(function (v) {
      var docChanged = state.versions.doc && v.doc !== state.versions.doc;
      var cmChanged = state.versions.comments && v.comments !== state.versions.comments;
      var docFailed = state.versions.doc === 'failed';
      state.versions = v;
      /* 本文の読み直しに失敗したら、版を失敗の印（failed）にして理由を取っておき、次の定期確認で読み直す。
         本文は読み直せて、続く朱の読み直しだけが失敗したときは、朱の版だけを古いままの印にする
         （朱の読み直しは、朱を書いている間も、次の定期確認でやり直す） */
      if (docChanged && !state.pending) {
        return loadDoc().then(function () { renderDoc(); })
          .catch(function (e) { state.versions.doc = 'failed'; state.docError = e; throw e; })
          .then(function () { return loadComments().catch(markStale); })
          .then(function () { setStatus('本文の更新を反映しました'); });
      }
      /* 朱を書いている間は、本文を読み直さずに待つ（stale）。前の読み直しが失敗していたら、失敗の印を残す */
      if (docChanged) state.versions.doc = docFailed ? 'failed' : 'stale';
      if (cmChanged) return loadComments().catch(markStale);
      /* 知らせを消すのは、この回が最後まで通り、本文の読み直しの失敗も残っていないときだけ。読み直しが失敗し続ける間と、
         失敗した後に朱を書いていて読み直しを待っている間は、知らせを出したままにする
         （先に消してから出し直すと、1.5 秒ごとに点滅する） */
    }).then(function () { if (state.versions.doc === 'failed') loadFailed(state.docError); else notice(''); }, loadFailed)
      .then(function () { setTimeout(poll, 1500); });
  }

  if (CFG.server) {
    /* 版を先に取ってから読む。読んでいる間に本文や朱が変わっても、最初の定期確認が版の違いに気づいて読み直す */
    getJson('api/version').then(function (v) { state.versions = v; return loadDoc(); })
      .then(function () { renderDoc(); return loadComments(); })
      .then(function () { setStatus('朱はファイルの隣の .review.json に保存されます'); poll(); })
      .catch(function (e) { notice('読み込みに失敗しました（' + e.message + '）。ページを読み込み直してください。'); });
  } else {
    state.doc = CFG.doc;
    state.comments = CFG.comments || [];
    try { state.local = JSON.parse(localStorage.getItem(CFG.storageKey) || '[]'); } catch (e) { state.local = []; }
    /* 会話に貼って .review.json に取り込まれ、書き出し直しで埋め込まれた朱（同じ id）は、このページの控えから外す */
    var known = Object.create(null);
    state.comments.forEach(function (c) { known[c.id] = 1; });
    state.local = (Array.isArray(state.local) ? state.local : []).filter(function (c) { return c && !known[c.id]; });
    persistLocal();
    /* Markdown の本文は renderAll が組み立てる。HTML の本文（枠）だけ先に作る */
    if (state.doc.mode === 'html') renderDoc();
    renderAll();
    setStatus('サーバーなしで開いています。付けた朱は「朱をまとめてコピー」で会話に貼ってください');
  }
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
