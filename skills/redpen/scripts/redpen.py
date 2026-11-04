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
    text = target.read_text(encoding="utf-8")
    if is_html(target):
        return {"mode": "html", "name": target.name, "html": text}
    return {"mode": "md", "name": target.name, "blocks": parse_blocks(text)}


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
                cfg = {"server": True, "name": target.name, "mode": "html" if is_html(target) else "md"}
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
            self.send_json(200, {"comment": review.add(body["target"], label, body["text"])})

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
        "mode": "html" if is_html(target) else "md",
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
#notice { display:none; padding:8px 16px; background:var(--red-soft); color:var(--ink); font-size:13px; }
#notice.show { display:block; }
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
  var modeBtn = document.getElementById('mode');
  var copybox = document.getElementById('copybox');
  var state = { doc: null, comments: [], local: [], redOn: true, pending: null, frame: null, versions: {} };

  document.getElementById('name').textContent = CFG.name;
  function setStatus(t) { statusEl.textContent = t; }
  function notice(t) { noticeEl.textContent = t; noticeEl.classList.toggle('show', !!t); }

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function safeUrl(u) { return /^(https?:\/\/|mailto:|#|\.{0,2}\/|[A-Za-z0-9_\-][^:]*$)/i.test(u); }
  function inline(s) {
    var codes = [];
    s = s.replace(/`([^`]+)`/g, function (_, c) { codes.push(c); return '\u0000' + (codes.length - 1) + '\u0000'; });
    s = esc(s)
      .replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, function (m, alt, u) {
        u = u.replace(/&amp;/g, '&');
        return safeUrl(u) ? '<img alt="' + alt + '" src="' + esc(u) + '">' : m;
      })
      .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, function (m, t, u) {
        u = u.replace(/&amp;/g, '&');
        return safeUrl(u) ? '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + t + '</a>' : t + ' (' + esc(u) + ')';
      })
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>');
    return s.replace(/\u0000(\d+)\u0000/g, function (_, i) { return '<code>' + esc(codes[+i]) + '</code>'; });
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
      if (stack.length < depth + 1) { out += '<' + tag + '>'; stack.push(tag); }
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
    state.pending = { target: target, label: label.slice(0, 80) };
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

  function nowStamp() { return new Date().toISOString(); }
  function saveComment(target, label, text) {
    var body = { target: target, label: label, text: text };
    if (!CFG.server) { addLocal(body); return; }
    fetch('api/comments', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function () { closeComposer(); setStatus('朱を保存しました'); return loadComments(); })
      .catch(function (e) {
        addLocal(body);
        notice('サーバーに保存できませんでした（' + e.message + '）。この朱はこのページにだけあります。「朱をまとめてコピー」で会話に貼ってください。');
      });
  }
  function addLocal(body) {
    var used = {};
    allComments().forEach(function (c) { used[c.id] = 1; });
    /* サーバーなしで付けた朱は、会話に貼って .review.json に取り込んでも id が変わらないよう、
       ほかと重ならない id にする（書き出し直したページで、取り込み済みの控えを id で外すため） */
    var id;
    do { id = 'p' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); } while (used[id]);
    state.local.push({ id: id, target: body.target, label: body.label, text: body.text, status: 'open', createdAt: nowStamp() });
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
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return loadComments(); })
      .catch(function (e) { notice('状態を変えられませんでした（' + e.message + '）'); });
  }
  function renderAll() {
    renderList();
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
      if (!r.ok) return r.json().catch(function () { return {}; }).then(function (j) { throw new Error(j.error || 'HTTP ' + r.status); });
      return r.json();
    });
  }
  function loadDoc() { return getJson('api/doc').then(function (d) { state.doc = d; }); }
  function loadComments() { return getJson('api/comments').then(function (d) { state.comments = d.comments || []; renderAll(); }); }
  function poll() {
    getJson('api/version').then(function (v) {
      notice('');
      var docChanged = state.versions.doc && v.doc !== state.versions.doc;
      var cmChanged = state.versions.comments && v.comments !== state.versions.comments;
      state.versions = v;
      if (docChanged && !state.pending) {
        return loadDoc().then(function () { renderDoc(); return loadComments(); }).then(function () { setStatus('本文の更新を反映しました'); });
      }
      if (docChanged) state.versions.doc = 'stale';
      if (cmChanged) return loadComments();
    }).catch(function (e) {
      notice('サーバーに届きません（' + e.message + '）。付けた朱は「朱をまとめてコピー」で会話に貼れます。');
    }).then(function () { setTimeout(poll, 1500); });
  }

  if (CFG.server) {
    loadDoc().then(function () { renderDoc(); return loadComments(); })
      .then(function () { setStatus('朱はファイルの隣の .review.json に保存されます'); poll(); })
      .catch(function (e) { notice('読み込みに失敗しました: ' + e.message); });
  } else {
    state.doc = CFG.doc;
    state.comments = CFG.comments || [];
    try { state.local = JSON.parse(localStorage.getItem(CFG.storageKey) || '[]'); } catch (e) { state.local = []; }
    /* 会話に貼って .review.json に取り込まれ、書き出し直しで埋め込まれた朱（同じ id）は、このページの控えから外す */
    var known = Object.create(null);
    state.comments.forEach(function (c) { known[c.id] = 1; });
    state.local = (Array.isArray(state.local) ? state.local : []).filter(function (c) { return c && !known[c.id]; });
    persistLocal();
    renderDoc();
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
