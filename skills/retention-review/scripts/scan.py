#!/usr/bin/env python3
"""定着レビュー用の機械スキャン。

日本語文書（Markdown / プレーンテキスト）から、「記憶に残る文書設計の原則」の
違反シグナルを行番号つきで列挙する。出力はシグナルであって判定ではない——
引用された悪例の中のヒットは違反ではないので、利用側が文脈を確認すること。

使い方:
    python3 scan.py <file> [--json] [--baseline <前回の --json 出力>] [--preserve <原文>]
    python3 scan.py <file> --profile reference [--json] [--baseline <前回の --json 出力>]

--profile reference は、README・Issue・手順書などの参照系技術文書向けの設定。検出するのは
tech-write/references/style.md の S1（前置きフィラー）・S2（万能語）・S3（太字）・
S4（ヘッジ）・S6（空虚な結び）と、弱シグナルの S9（記号。下の記号表記）で、語表は style.md の日本語の語に合わせてある。
これに、既定と共通の LLM っぽい言い回し・翻訳調の比喩の弱シグナルを加える。
手順の「〜してください」を指示レジスタとして数えないなど、判断文書向けの原則 2・4・5・8 と
文体レジスタは出力に含めない。太字は箇条書き先頭のラベル（`- **名前**: 説明`）を除いて数える。
既存カテゴリの語彙・太字・統計欄の集計と exit code は変えない。

記号表記（symbol_notation）は、style.md の S9 の字形からはずれた記号を拾う弱シグナルで、
既定と --profile reference の両方に出す。日本語の文字を含む地の文の行にある、日本語を含む
半角の括弧・日本語の直後の半角コロン・日本語に隣接する半角スラッシュ・`~` と「～」（U+FF5E）・
単体の「…」と日本語に隣接する `...`・日本語を囲む半角の二重引用符と、箇条書き先頭の太字の
ラベルを句点で区切った形（`- **名前**。説明`。S3）、ラベルを含めた行に日本語があるときの
ラベル直後の半角コロン（`- **名前**: 説明`・`- **名前:** 説明`。S3）が対象。コードスパン・
コードフェンス・表・見出し・URL・Markdown のリンク先・引用行は対象外。強シグナルではないので、強シグナルの基準
（納品前セルフチェックの「強シグナルは 0」）と exit code は変わらない。

--baseline を渡すと、前回スキャンとの差分を resolved（前回あり今回なし）/
new（今回のみ）/ persisting（両方）に仕分けて出力に加える。finding の同一性は
「カテゴリ + NFC 正規化した該当語」で判定するため、行番号のずれだけでは new に
ならない。--baseline なしの出力・exit code は従来と完全に同一。

--preserve を渡すと、<file>（書き直し後）を原文と突き合わせ、原文にあった数字と
インラインコード（バッククォートで囲んだ部分）が書き直し後に 1 つも残っていないものを、
原文の行番号つきで出力の末尾に加える。数字は NFKC で全角を半角に直し、桁区切りの
カンマを除いて比べる（「32,000」と「32000」は同じ）。出現回数は比べず、英字の製品名など
バッククォートで囲まれていない語は対象にしない。消えた要素があっても exit code は変えない。
--preserve なしの出力・exit code は従来と完全に同一。

語彙系の各ヒットには severity（strong/weak）が付く。weak には、コーパス実測で
正当用法が確認された語と、正当用法を削らせないため予防的に暫定指定した語がある。
同梱の references/scan-guidance.md が文脈判断の基準を示す。出力ではともに [弱] と表示する。
違反の断定ではなく文脈判断に回すこと。

principle_6_style_register は詠嘆・指示レジスタの検出結果で、敬体・常体のどちらの
文体で書かれているかは問わない（既定は です・ます調だが、である調で書かれた文書を
文体だけを理由に違反にはしない）。規定の本体は retention-write の
references/skeleton.md「文体レジスタ」節の 2 軸表。
"""

import argparse
import json
import re
import sys
import unicodedata

# --- 検出パターン ------------------------------------------------------------
# 各リストは「素の AI 文体の癖」対照表（memorable-doc-principles.md 付録)を
# 機械可読に落としたもの。網羅ではなく高頻度パターンに絞る。

FILLERS = [  # 原則 1 賭け金の宣言 に反する前置きフィラー
    "本ドキュメントでは", "本書では", "本稿では", "本資料では",
    "について説明します", "についてまとめます", "について解説します",
    "を紹介します", "一助となれば", "参考になれば",
    # 日本語ビジネス定型の社交フィラー（連絡メモで賭け金を遅らせる）
    "お疲れさまです", "お疲れ様です", "共有させていただきます",
    "よろしくお願いいたします", "よろしくお願いします",
]

STRUCTURE_DECL = re.compile(  # 原則 2 因果の物語 に反する構造宣言
    r"(以下|次)の?\s*[0-9０-９一二三四五六七八九十]+\s*つの(観点|ポイント|側面|項目|柱|軸|カテゴリ)"
)

BUZZWORDS = [  # 原則 3 具体で書く に反する万能語
    "最適化", "効率化", "簡素化", "高度化", "抜本的",
    "適切な", "適切に", "柔軟な", "柔軟に", "様々な", "さまざまな",
    "総合的に", "積極的に", "シナジー", "ソリューション",
]

DEAD_METAPHORS = [  # 原則 4 スキーマフック に反する死んだ比喩
    "車の両輪", "銀の弾丸", "諸刃の剣", "両刃の剣", "一石二鳥",
    "追い風", "向かい風", "一丁目一番地",
]

# 既存の万能語・死んだ比喩と分け、両プロファイルで検出する。全語を暫定の弱シグナルにする。
# 文脈判断の基準は同梱の references/scan-guidance.md を参照する。
LLM_PHRASES = [
    "正面から", "多角的", "掘り下げる",
]

TRANSLATED_METAPHORS = [
    "開かれた問い", "議論を運ぶ",
]

INSTRUCTION_MARKERS = [  # 読者へ指示して予測させる形。原則 5 のシグナルであり、同時に
    # 文体レジスタ違反でもある（STYLE_REGISTER_MARKERS と併せて principle_6_style_register に
    # 直接合流させる。語尾側だけに任せると「手を止めて数える。」のように語尾がレジスタ語で
    # ない指示形が原則 5 にしか出ず、二段計上が語尾に依存して崩れる）
    "予想して", "予測して", "考えてみて", "思い浮かべて", "数えてほしい",
    "手を止めて", "自問して",
]

NEUTRAL_QUESTION_MARKERS = [  # 中立レジスタの問い形（文体レジスタ規則が推奨する形）
    "ここで一問", "だろうか。", "でしょうか。",
]
# 既知の限界: 「でしょうか。」「だろうか。」は敬体・常体の疑問文全般に当たるため、修辞疑問や
# 社交疑問も拾う。原則 5 の「有」は問いの存在を保証しない。summarize は該当行を明細に出すので、
# 利用側はその行を読んで生成の問いかどうかを判断すること。

GENERATION_MARKERS = INSTRUCTION_MARKERS + NEUTRAL_QUESTION_MARKERS  # 原則 5 の存在シグナル

# 「でしょうか。」「だろうか。」はヘッジ「（の）ではないでしょうか / ではないだろうか」と
# 語形が衝突する。照合前に行から除去し、ヘッジは原則 6 だけに計上する（生成の問いに数えない）。
# 敬体・常体を対で入れる。長い語形が短い語形を包含するため、どちらを先に除去しても
# 「でしょうか。」「だろうか。」は残らない。ヘッジの検出辞書が敬体・常体の両形を持つので、
# マスクも同じ両形を置く。
GENERATION_HEDGE_MASKS = [
    "のではないでしょうか", "ではないでしょうか",
    "のではないだろうか", "ではないだろうか",
]

HEDGES = [  # 原則 6 断定 に反するヘッジ・両論併記・事なかれ表現
    "可能性があります", "可能性がある", "傾向があります", "傾向がある",
    "場合があります", "と考えられます", "と思われます", "一概に",
    "期待できます", "が望ましい", "検討していく", "検討を進め",
    "判断することが重要", "ことが重要です", "メリットとデメリット", "一長一短",
    "ればと思います", "ではないかと考え", "ではないでしょうか", "ではないだろうか",
]

STYLE_REGISTER_MARKERS = [  # 原則 6 補足 詠嘆・指示レジスタ（敬体・常体の両方を検出する）
    # 敬体（です・ます調）の詠嘆・指示形
    "ましょう", "てください", "ですよね", "ますよね", "それだけです。",
    # 常体（である調）の詠嘆・指示形
    "からだ。", "それだけだ。", "てほしい",
]
# 敬体の「〜からです。」は入れない。常体の「〜からだ。」が詠嘆になるのは である調の中立形が
# 「〜ためである。」だからで、敬体では「理由は X だからです。」が中立の標準形にあたる。
# 2 軸表の敬体行も同じ理由で当該語形を挙げていない。

RECALL_MARKERS = [  # 原則 8 想起テスト の存在シグナル
    "読了チェック", "想起テスト", "1 週間後", "一週間後", "1週間後",
    "確認問題", "クイズ", "答えられるか",
]

# --- 弱シグナル ---------------------------------------------------------------
# 正当用法が確認された語と、予防的に暫定指定した語を弱シグナルとして扱う。
# 同梱の references/scan-guidance.md が正当用法を残す判断基準を示す。
# 検出はするが違反の断定ではなく文脈判断に回す。
# 各集合は対応する上のリストの部分集合であること（外れた語は検出されなくなる）。

FILLERS_WEAK_SIGNAL = [
    "について解説します", "を紹介します", "本ドキュメントでは",
]

BUZZWORDS_WEAK_SIGNAL = [
    # 「様々な」「適切に」はヒット 0 だが、実測した「さまざまな」「適切な」の
    # 異表記・活用形のため同一分類（片方だけ強のままでは基準が矛盾する）
    "さまざまな", "様々な", "適切な", "適切に",
]

DEAD_METAPHORS_WEAK_SIGNAL = []  # 基準集合でヒット 0 のため格下げなし（全語保持）

HEDGES_WEAK_SIGNAL = [
    "可能性があります", "可能性がある", "場合があります",
]

# 文体レジスタの弱シグナルは持たない。文脈の例外は references/skeleton.md の規則で判断する。
# 「からだ。」の名詞終止への誤検出は、本ファイル冒頭が全体の前提として掲げる
# 「シグナルであって判定ではない」に委ねる。

# キーは原則番号ではなくカテゴリ名。原則 6 に hedges と style_register の 2 カテゴリが
# 同居するため、番号キーでは片方の弱シグナルをもう片方へ漏らさずに持てない。
_WEAK_BY_CATEGORY = {
    "principle_1_fillers": frozenset(FILLERS_WEAK_SIGNAL),
    "principle_3_buzzwords": frozenset(BUZZWORDS_WEAK_SIGNAL),
    "principle_4_dead_metaphors": frozenset(DEAD_METAPHORS_WEAK_SIGNAL),
    "principle_6_hedges": frozenset(HEDGES_WEAK_SIGNAL),
    # 新しい 2 カテゴリは全語を暫定指定する。0 ヒットは正当用法の実証ではない。
    "llm_phrasing": frozenset(LLM_PHRASES),
    "translated_metaphors": frozenset(TRANSLATED_METAPHORS),
}

# --- 参照文書用プロファイル（--profile reference）-----------------------------
# tech-write/references/style.md の日本語の語をそのまま表にしたもの。既定の語表とは
# 別に持つ（既定の BUZZWORDS などへ足すと、判断文書向けの既定の出力が変わる）。
# style.md の語は文脈で正当にもなる（「以下に」「ここでは」「を示します」など）。
# 出力はシグナルであり、該当行を読んで判断すること。

REFERENCE_FILLERS = [  # S1 前置きフィラー
    "本ドキュメントでは", "について説明します", "以下に", "を示します",
    "ここでは", "を紹介します",
    # style.md の語ではない追加語。実測校正で弱シグナルにした語（FILLERS_WEAK_SIGNAL）を
    # 参照文書でも同じ弱シグナルとして扱うために置く。
    "について解説します",
]

REFERENCE_BUZZWORDS = [  # S2 万能語
    "強力な", "柔軟な", "シームレスな", "包括的な",
    "効率的に", "簡単に", "迅速に", "洗練された",
]

REFERENCE_HEDGES = [  # S4 両論併記・過剰ヘッジ
    "場合によっては", "かもしれません", "一般的には",
]

REFERENCE_CLOSINGS = [  # S6 空虚な結び
    "ぜひご活用ください", "お役に立てれば幸いです",
]

# 既存語の新たな格下げはしない。実測校正を通した FILLERS_WEAK_SIGNAL と、
# 新しい 2 カテゴリの暫定指定を既定プロファイルと共用する。
_REFERENCE_WEAK_BY_CATEGORY = {
    "principle_1_fillers": frozenset(FILLERS_WEAK_SIGNAL),
    "llm_phrasing": frozenset(LLM_PHRASES),
    "translated_metaphors": frozenset(TRANSLATED_METAPHORS),
}

BOLD = re.compile(r"\*\*[^*\n]+?\*\*|__[^_\n]+?__|<(?:b|strong)>.*?</(?:b|strong)>")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
FENCE = re.compile(r"^\s{0,3}(```|~~~)")
# ダッシュは違反のカテゴリではなく統計欄の数値だけに使う。連続する「——」は 1 個と数える
DASH_RUN = re.compile(r"[—―]+")
PROSE_INLINE_CODE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
TABLE_ROW = re.compile(r"^\s*\|")


def prose_lines(lines):
    """地の文の (行番号, 行) を順に返す。表の行・コードフェンス・見出しを除き、
    インラインコードを空白 1 文字に置き換えた行。"""
    fence = False
    for i, line in enumerate(lines, 1):
        if FENCE.match(line):
            fence = not fence
            continue
        if fence or HEADING.match(line) or TABLE_ROW.match(line):
            continue
        # 空白 1 文字に置き換える。空文字だと前後のダッシュがつながって 1 個に縮む
        yield i, PROSE_INLINE_CODE.sub(" ", line)


def prose_text(lines) -> str:
    """地の文。表の行・コードフェンス・見出しを除き、インラインコードを取り除いた本文。"""
    return "\n".join(line for _, line in prose_lines(lines))


# --- 記号表記（S9）-------------------------------------------------------------
# tech-write/references/style.md の S9 の字形からはずれた記号を、日本語の文字を含む
# 地の文の行から拾う。半角の記号は正当な用法が多いので、すべて弱シグナルとして出す。
# 数字と英字は対象にしない。

JA = "぀-ヿ㐀-鿿"  # ひらがな・カタカナ・漢字（文字クラスの中身）
SYMBOL_URL = re.compile(r"https?://\S+|<[^<>\n]+>")  # URL と HTML タグ（属性の引用符を拾わない）
SYMBOL_LINK_TARGET = re.compile(r"\]\([^()\n]*\)")  # Markdown のリンク・画像の宛先。リンクテキストは本文なので残す
SYMBOL_JA_LINE = re.compile(f"[{JA}]")
SYMBOL_PATTERNS = [  # (表示する記号, パターン)
    # 先読みで日本語の有無を見てから本体を取る。日本語を挟む 2 つの `[^()\n]*` を並べると、
    # 閉じ記号のない長い 1 行で試行ごとに行末まで走り、2 乗時間になる
    ("( )", re.compile(rf"\((?=[^()\n]*[{JA}])[^()\n]*\)")),
    (":", re.compile(rf"(?<=[{JA}]):")),
    # 片側が日本語で、もう片側が英数字・パスの文字でないスラッシュ（A/B やパスは除く）
    ("/", re.compile(rf"(?<=[{JA}])/(?![A-Za-z0-9._~-])|(?<![A-Za-z0-9._~-])/(?=[{JA}])")),
    ("~", re.compile(r"(?<!~)~(?![~/])")),
    ("～", re.compile("～")),
    ("…", re.compile("(?<!…)…(?!…)")),
    ("...", re.compile(rf"(?<=[{JA}])\.{{3}}(?!\.)|(?<!\.)\.{{3}}(?=[{JA}])")),
    ('" "', re.compile(rf'"(?=[^"\n]*[{JA}])[^"\n]*"')),
]


def symbol_hits(lines):
    """記号表記のヒット。コードスパン・フェンス・表・見出し・URL・Markdown のリンク先・引用行は対象外で、
    日本語の文字を含まない行は記号が半角でも拾わない。ラベル直後の半角コロンだけは、ラベルを含めた
    行に日本語があれば拾い、そのほかの記号はラベルを除いた残りに日本語があるときだけ拾う。"""
    found = []
    for i, line in prose_lines(lines):
        if is_quotish(line):
            continue
        probe = SYMBOL_URL.sub(" ", SYMBOL_LINK_TARGET.sub("]", line))
        # 箇条書き先頭のラベルを句点で区切った形（`- **名前**。説明`）。ラベルの区切りは全角コロン
        if label_period(probe):
            found.append({
                "line": i, "match": "**ラベル**。",
                "text": line.strip()[:120],
                "in_quote_context": False,
                "severity": "weak",
            })
        # 日本語の有無はラベルを含めた行全体で決める（S9: 日本語を含まない行だけが半角のまま残せる）
        line_has_ja = bool(SYMBOL_JA_LINE.search(probe))
        # 箇条書き先頭のラベル（`- **名前:** 説明`）の太字は、末尾のコロンごと対象から外す。
        # ただしラベルと説明を区切る半角コロンそのものは、日本語を含む行なら S3 の字形違反として拾う
        label_start = label_bold_start(probe)
        if label_start is not None:
            if line_has_ja and label_half_colon(probe, label_start):
                found.append({
                    "line": i, "match": "**ラベル**:",
                    "text": line.strip()[:120],
                    "in_quote_context": False,
                    "severity": "weak",
                })
            bold = BOLD.match(probe, label_start)
            probe = probe[:label_start] + " " + probe[bold.end():]
        if not SYMBOL_JA_LINE.search(probe):
            continue
        for label, pattern in SYMBOL_PATTERNS:
            for _ in pattern.finditer(probe):
                found.append({
                    "line": i, "match": label,
                    "text": line.strip()[:120],
                    "in_quote_context": False,
                    "severity": "weak",
                })
    return found


LIST_ITEM = re.compile(r"^\s*(?:[-*+]|[0-9]+[.)])\s+")
LABEL_TAIL = re.compile(r"\s*(?:[:：]|$)")
LABEL_PERIOD_INSIDE = re.compile(r"。(?:\*\*|__)$")
LABEL_COLON_INSIDE = re.compile(r"[:：](?:\*\*|__|</(?:b|strong)>)$")
LABEL_HALF_COLON_INSIDE = re.compile(r":(?:\*\*|__|</(?:b|strong)>)$")
LABEL_HALF_COLON_AFTER = re.compile(r"\s*:")


def label_half_colon(line: str, start: int) -> bool:
    """ラベル太字（`label_bold_start` が返した位置）が、半角コロンで説明と区切られているか
    （`**名前**:` / `**名前** :` / `**名前:**`）。全角コロンは含めない。"""
    bold = BOLD.match(line, start)
    return bool(LABEL_HALF_COLON_INSIDE.search(bold.group(0))) or bool(LABEL_HALF_COLON_AFTER.match(line, bold.end()))


def label_bold_start(line: str):
    """箇条書き先頭のラベル太字の開始位置。ラベルでなければ None。

    ラベルは、項目の先頭にある太字で、中身がコロンで終わるか、直後にコロンまたは行末が
    続くもの（`- **名前**: 説明` / `- **名前:** 説明` / `1. **手順**`）。
    先頭にあっても直後に文が続く太字（`- **注意** この操作は…`）は強調なのでラベルにしない。
    """
    item = LIST_ITEM.match(line)
    if not item:
        return None
    bold = BOLD.match(line, item.end())
    if not bold:
        return None
    if LABEL_COLON_INSIDE.search(bold.group(0)) or LABEL_TAIL.match(line, bold.end()):
        return bold.start()
    return None


def label_period(line: str) -> bool:
    """箇条書き先頭の太字の直後が句点か（`- **名前**。説明` / `1. **名前。**説明`）。"""
    item = LIST_ITEM.match(line)
    if not item:
        return False
    bold = BOLD.match(line, item.end())
    if not bold:
        return False
    return bool(LABEL_PERIOD_INSIDE.search(bold.group(0))) or line.startswith("。", bold.end())


def is_quotish(line: str) -> bool:
    """引用・例示らしい行か。ヒットを弱シグナル扱いにするためのヒント。"""
    stripped = line.lstrip()
    if stripped.startswith(">"):
        return True
    # 「素の文体:」「Before:」「例:」等のラベル行は悪例引用であることが多い
    return bool(re.match(r"[-*+]?\s*(素の文体|Before|悪い例|例|適用後|After)\s*[:：]", stripped))


def scan(text: str, profile=None):
    reference = profile == "reference"
    weak_by_category = _REFERENCE_WEAK_BY_CATEGORY if reference else _WEAK_BY_CATEGORY
    lines = text.splitlines()
    in_fence = False

    def hits_of(patterns, category, masks=()):
        """category はカテゴリキー（principle_N_*）で弱シグナル集合の引き当てに使う。"""
        weak = weak_by_category.get(category, frozenset())
        found = []
        fence = False
        for i, line in enumerate(lines, 1):
            if FENCE.match(line):
                fence = not fence
                continue
            if fence:
                continue
            probe = line
            for m in masks:
                probe = probe.replace(m, "")
            for p in patterns:
                if p in probe:
                    found.append({
                        "line": i, "match": p,
                        "text": line.strip()[:120],
                        "in_quote_context": is_quotish(line),
                        "severity": "weak" if p in weak else "strong",
                    })
        return found

    bold_hits = []
    for i, line in enumerate(lines, 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or HEADING.match(line):
            continue
        label_start = label_bold_start(line) if reference else None
        for m in BOLD.finditer(line):
            if m.start() == label_start:
                continue
            bold_hits.append({
                "line": i, "match": m.group(0)[:80],
                "text": line.strip()[:120],
                "in_quote_context": is_quotish(line),
            })

    struct_hits = []
    fence = False
    for i, line in enumerate(lines, 1):
        if FENCE.match(line):
            fence = not fence
            continue
        if fence:
            continue
        m = STRUCTURE_DECL.search(line)
        if m:
            struct_hits.append({
                "line": i, "match": m.group(0),
                "text": line.strip()[:120],
                "in_quote_context": is_quotish(line),
            })

    # 具体性の粗い指標: 本文 1000 文字あたりの数字トークン数
    body = "\n".join(l for l in lines if not HEADING.match(l))
    digits = len(re.findall(r"[0-9０-９][0-9０-９,.]*", body))
    chars = max(1, len(re.sub(r"\s", "", body)))
    prose = prose_text(lines)
    dashes = len(DASH_RUN.findall(prose))
    prose_chars = max(1, len(re.sub(r"\s", "", prose)))
    stats = {
        "lines": len(lines),
        "chars_no_ws": chars,
        "numeric_tokens": digits,
        "numeric_per_1000_chars": round(digits * 1000 / chars, 1),
        "dash_count": dashes,
        "dash_per_1000_chars": round(dashes * 1000 / prose_chars, 1),
    }

    if reference:
        return {
            "profile": "reference",
            "principle_1_fillers": hits_of(REFERENCE_FILLERS, "principle_1_fillers"),
            "principle_3_buzzwords": hits_of(REFERENCE_BUZZWORDS, "principle_3_buzzwords"),
            "principle_6_hedges": hits_of(REFERENCE_HEDGES, "principle_6_hedges"),
            "reference_closings": hits_of(REFERENCE_CLOSINGS, "reference_closings"),
            "principle_7_bold_emphasis": bold_hits,
            "symbol_notation": symbol_hits(lines),
            "llm_phrasing": hits_of(LLM_PHRASES, "llm_phrasing"),
            "translated_metaphors": hits_of(TRANSLATED_METAPHORS, "translated_metaphors"),
            "stats": stats,
        }

    return {
        "principle_1_fillers": hits_of(FILLERS, "principle_1_fillers"),
        "principle_2_structure_decl": struct_hits,
        "principle_3_buzzwords": hits_of(BUZZWORDS, "principle_3_buzzwords"),
        "principle_4_dead_metaphors": hits_of(
            DEAD_METAPHORS, "principle_4_dead_metaphors"
        ),
        "principle_5_generation_markers": hits_of(
            GENERATION_MARKERS, "principle_5_generation_markers",
            masks=GENERATION_HEDGE_MASKS,
        ),
        "principle_6_hedges": hits_of(HEDGES, "principle_6_hedges"),
        # 指示形は原則 5 と本カテゴリの両方に計上する（二段計上）。計数は他カテゴリと同じく
        # 語単位で、同一行に語幹と語尾の両方が当たれば 2 件になる。
        "principle_6_style_register": hits_of(
            INSTRUCTION_MARKERS + STYLE_REGISTER_MARKERS,
            "principle_6_style_register",
        ),
        "principle_7_bold_emphasis": bold_hits,
        "principle_8_recall_markers": hits_of(
            RECALL_MARKERS, "principle_8_recall_markers"
        ),
        "symbol_notation": symbol_hits(lines),
        "llm_phrasing": hits_of(LLM_PHRASES, "llm_phrasing"),
        "translated_metaphors": hits_of(TRANSLATED_METAPHORS, "translated_metaphors"),
        "stats": stats,
    }


# --- baseline 差分 ------------------------------------------------------------

FINDING_KEYS = [
    "principle_1_fillers",
    "principle_2_structure_decl",
    "principle_3_buzzwords",
    "principle_4_dead_metaphors",
    "principle_5_generation_markers",
    "principle_6_hedges",
    "principle_6_style_register",
    "principle_7_bold_emphasis",
    "principle_8_recall_markers",
    "symbol_notation",
    "llm_phrasing",
    "translated_metaphors",
]

REFERENCE_FINDING_KEYS = [
    "principle_1_fillers",
    "principle_3_buzzwords",
    "principle_6_hedges",
    "reference_closings",
    "principle_7_bold_emphasis",
    "symbol_notation",
    "llm_phrasing",
    "translated_metaphors",
]

PROFILE_FINDING_KEYS = {None: FINDING_KEYS, "reference": REFERENCE_FINDING_KEYS}


# 本版で新設したカテゴリ。baseline の欠落がこれだけなら、利用者が渡した JSON 自体は正しく、
# 旧版の scan.py で作ったことだけが原因だと断定できる。
BASELINE_ADDED_KEYS = frozenset({
    "principle_6_style_register", "symbol_notation", "llm_phrasing", "translated_metaphors",
})


def _profile_label(profile):
    return profile if profile else "既定（--profile なし）"


def load_baseline(path, profile=None):
    """前回の --json 出力を読み、スキーマを検証する。

    入力エラー（不在・非 JSON・キー欠落・形の不一致・profile の不一致）は検出結果と
    区別するため、黙って比較をスキップせず理由を表示して exit 1 する。
    """
    keys = PROFILE_FINDING_KEYS[profile]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as e:
        sys.exit(f"エラー: baseline を読めません: {e}")
    except json.JSONDecodeError as e:
        sys.exit(f"エラー: baseline が JSON として解釈できません ({path}): {e}")
    if not isinstance(data, dict):
        sys.exit(f"エラー: baseline のトップレベルがオブジェクトではありません ({path})")
    # profile の照合はキー欠落の判定より前に行う。別 profile の出力はキー集合が違うため、
    # 先に欠落判定へ進むと「必要なキーがありません」という原因違いの診断になる。
    # profile を持たない JSON は既定（--profile なし）の出力として扱う。
    if data.get("profile") != profile:
        sys.exit(
            f"エラー: baseline の profile が今回の実行と違います ({path}): "
            f"baseline={_profile_label(data.get('profile'))} / 今回={_profile_label(profile)}\n"
            "同じ --profile で出した --json 出力を渡してください"
        )
    missing = [k for k in keys if k not in data]
    if missing:
        if set(missing) <= BASELINE_ADDED_KEYS:
            sys.exit(
                f"エラー: baseline が旧バージョンの scan.py の出力です ({path}): "
                f"{', '.join(missing)} がありません\n"
                "比較したい前回時点の原稿（git 管理下なら "
                "git show HEAD~1:<file> > /tmp/prev.md、そうでなければ編集前の控え）に"
                "現行の scan.py で --json をかけ直してください。対象文書そのものから"
                "作り直すと、以後の比較は今回時点を起点にします"
            )
        sys.exit(
            f"エラー: baseline に必要なキーがありません ({path}): {', '.join(missing)}\n"
            "scan.py の --json 出力をそのまま渡してください"
        )
    for key in keys:
        if not isinstance(data[key], list) or not all(
            isinstance(h, dict) and isinstance(h.get("match"), str) for h in data[key]
        ):
            sys.exit(
                f"エラー: baseline の {key} が期待する形（match を持つオブジェクトの配列）ではありません ({path})"
            )
    return data


def finding_counts(result, keys=FINDING_KEYS):
    """(カテゴリ, NFC 正規化した該当語) → 出現回数。行番号は同一性に使わない。"""
    counts = {}
    for key in keys:
        for h in result.get(key, []):
            k = (key, unicodedata.normalize("NFC", h["match"]).strip())
            counts[k] = counts.get(k, 0) + 1
    return counts


def baseline_diff(baseline, current, keys=FINDING_KEYS):
    b, c = finding_counts(baseline, keys), finding_counts(current, keys)
    diff = {"resolved": [], "new": [], "persisting": []}
    for key in sorted(set(b) | set(c)):
        entry = {
            "category": key[0],
            "match": key[1],
            "baseline_count": b.get(key, 0),
            "current_count": c.get(key, 0),
        }
        if entry["current_count"] == 0:
            diff["resolved"].append(entry)
        elif entry["baseline_count"] == 0:
            diff["new"].append(entry)
        else:
            diff["persisting"].append(entry)
    return diff


def summarize_diff(diff):
    out = []
    out.append("=== ベースライン比較 ===")
    out.append(
        f"resolved: {len(diff['resolved'])} / new: {len(diff['new'])} / persisting: {len(diff['persisting'])}"
    )
    for label, note in [
        ("resolved", "前回あり今回なし"),
        ("new", "今回のみ"),
        ("persisting", "両方"),
    ]:
        entries = diff[label]
        if not entries:
            continue
        out.append(f"--- {label} ({note}, {len(entries)} 件) ---")
        for e in entries:
            out.append(
                f"  {e['category']}: {e['match']}  (前回 {e['baseline_count']} → 今回 {e['current_count']})"
            )
    return "\n".join(out)


# --- 原文からの保持 -----------------------------------------------------------

INLINE_CODE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
# 桁区切りは 3 桁ごとのカンマだけを数字の一部とみなす（「1, 2, 3」の列挙を 1 つに繋げない）
NUMBER = re.compile(r"[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?")


def preserve_targets(text: str):
    """突き合わせの対象を {数字: 最初の行番号}, {インラインコード: 最初の行番号} で返す。

    コードフェンスの中は対象外。数字はインラインコードを除いた残りから拾い、
    NFKC で全角を半角に直して桁区切りのカンマを除く。
    """
    numbers, codes = {}, {}
    fence = False
    for i, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            fence = not fence
            continue
        if fence:
            continue
        for m in INLINE_CODE.finditer(line):
            code = m.group(2).strip()
            if code:
                codes.setdefault(code, i)
        rest = unicodedata.normalize("NFKC", INLINE_CODE.sub(" ", line))
        for m in NUMBER.finditer(rest):
            numbers.setdefault(m.group(0).replace(",", ""), i)
    return numbers, codes


def load_preserve(path):
    """原文を読む。読めなければ、検出結果と区別するため理由を表示して exit 1 する。"""
    try:
        with open(path, encoding="utf-8") as f:
            return unicodedata.normalize("NFC", f.read())
    except (OSError, UnicodeDecodeError) as e:
        sys.exit(f"エラー: --preserve の原文を読めません ({path}): {e}")


def preserve_diff(original: str, rewritten: str):
    """原文の数字・インラインコードのうち書き直し後に無いものと、原文の対象件数を返す。"""
    o_numbers, o_codes = preserve_targets(original)
    r_numbers, r_codes = preserve_targets(rewritten)
    diff = {
        "missing_numbers": [
            {"match": k, "line": v} for k, v in o_numbers.items() if k not in r_numbers
        ],
        "missing_code": [
            {"match": k, "line": v} for k, v in o_codes.items() if k not in r_codes
        ],
    }
    return diff, (len(o_numbers), len(o_codes))


def summarize_preserve(diff, totals):
    n_numbers, n_codes = totals
    out = ["=== 原文からの保持 ==="]
    if n_numbers == 0 and n_codes == 0:
        out.append("対象 0 件（原文に数字もインラインコードもありません）")
        return "\n".join(out)
    out.append(f"原文の対象: 数字 {n_numbers} 種 / インラインコード {n_codes} 種")
    out.append(f"消えた数字: {len(diff['missing_numbers'])} 件")
    for e in diff["missing_numbers"]:
        out.append(f"  L{e['line']}: {e['match']}")
    out.append(f"消えたインラインコード: {len(diff['missing_code'])} 件")
    for e in diff["missing_code"]:
        out.append(f"  L{e['line']}: `{e['match']}`")
    return "\n".join(out)


def _count_label(hits):
    """「N 件」に弱シグナル内訳を添える（弱 0 なら従来表示のまま）。"""
    weak = sum(1 for h in hits if h.get("severity") == "weak")
    if weak:
        return f"{len(hits)} 件 (うち弱 {weak})"
    return f"{len(hits)} 件"


def _symbol_lines(hits):
    """記号表記のヒットを行ごとに 1 行へまとめる。(行番号, 該当の記号の列, 本文) の列。"""
    by_line = {}
    for h in hits:
        entry = by_line.setdefault(h["line"], ([], h["text"]))
        if h["match"] not in entry[0]:
            entry[0].append(h["match"])
    return [(line, " ".join(marks), text) for line, (marks, text) in sorted(by_line.items())]


def _append_symbol_detail(out, hits):
    if not hits:
        return
    out.append(f"--- 記号表記 ({_count_label(hits)}) ---")
    for line, marks, text in _symbol_lines(hits):
        out.append(f"  L{line}: [弱] {marks}  |  {text}")
    out.append("")


WEAK_PHRASE_LABELS = [
    ("llm_phrasing", "LLM っぽい言い回し"),
    ("translated_metaphors", "翻訳調の比喩"),
]


def _append_weak_phrase_detail(out, result):
    for key, label in WEAK_PHRASE_LABELS:
        hits = result[key]
        if not hits:
            continue
        out.append(f"--- {label} ({_count_label(hits)}) ---")
        for h in hits:
            q = "  [引用文脈?]" if h["in_quote_context"] else ""
            w = "[弱] " if h.get("severity") == "weak" else ""
            out.append(f"  L{h['line']}: {w}{h['match']}  |  {h['text']}{q}")
        out.append("")


def summarize(result):
    r = result
    has_recall = bool(r["principle_8_recall_markers"])
    has_generation = bool(r["principle_5_generation_markers"])
    out = []
    out.append("=== 定着レビュー 機械スキャン ===")
    out.append("(注意: 以下はシグナルであって判定ではない。引用悪例の中のヒットは違反ではない。")
    out.append(" [弱] は実測で正当用法を確認した語・予防的に暫定指定した語・記号表記。違反断定でなく文脈判断)")
    out.append("")
    out.append(f"太字などの強調      : {len(r['principle_7_bold_emphasis'])} 箇所  (原則 7: 2 箇所以上で違反疑い)")
    out.append(f"前置きフィラー      : {_count_label(r['principle_1_fillers'])}    (原則 1)")
    out.append(f"構造宣言            : {len(r['principle_2_structure_decl'])} 件    (原則 2)")
    out.append(f"万能語              : {_count_label(r['principle_3_buzzwords'])}    (原則 3)")
    out.append(f"死んだ比喩          : {_count_label(r['principle_4_dead_metaphors'])}    (原則 4)")
    out.append(f"ヘッジ・両論併記    : {_count_label(r['principle_6_hedges'])}    (原則 6)")
    out.append(f"文体レジスタ        : {_count_label(r['principle_6_style_register'])}    (原則 6 補足: 詠嘆・指示)")
    out.append(f"生成の問いシグナル  : {'有' if has_generation else '無'}     (原則 5)")
    out.append(f"想起テストシグナル  : {'有' if has_recall else '無'}     (原則 8)")
    out.append(f"記号表記            : {_count_label(r['symbol_notation'])}    (記号の字形。S9)")
    for key, label in WEAK_PHRASE_LABELS:
        out.append(f"{label}：{_count_label(r[key])}（暫定の弱シグナル）")
    s = r["stats"]
    out.append(f"数字の密度          : {s['numeric_per_1000_chars']} 個/1000字 (数字トークン {s['numeric_tokens']})")
    out.append(f"ダッシュの密度      : {s['dash_per_1000_chars']} 個/1000字 (ダッシュ {s['dash_count']}。地の文のみで、表・コード・見出しは数えない)")
    out.append("")
    for key, label in [
        ("principle_1_fillers", "前置きフィラー"),
        ("principle_2_structure_decl", "構造宣言"),
        ("principle_3_buzzwords", "万能語"),
        ("principle_4_dead_metaphors", "死んだ比喩"),
        ("principle_5_generation_markers", "生成の問い"),
        ("principle_6_hedges", "ヘッジ・両論併記"),
        ("principle_6_style_register", "文体レジスタ（詠嘆・指示）"),
        ("principle_7_bold_emphasis", "強調"),
    ]:
        hits = r[key]
        if not hits:
            continue
        out.append(f"--- {label} ({_count_label(hits)}) ---")
        for h in hits:
            q = "  [引用文脈?]" if h["in_quote_context"] else ""
            w = "[弱] " if h.get("severity") == "weak" else ""
            out.append(f"  L{h['line']}: {w}{h['match']}  |  {h['text']}{q}")
        out.append("")
    _append_symbol_detail(out, r["symbol_notation"])
    _append_weak_phrase_detail(out, r)
    return "\n".join(out)


def summarize_reference(result):
    r = result
    out = []
    out.append("=== 参照文書 機械スキャン（--profile reference）===")
    out.append("(注意: 以下はシグナルであって判定ではない。引用例の中のヒットは違反ではない。")
    out.append(" [弱] は実測で正当用法を確認した語・予防的に暫定指定した語・記号表記。違反断定でなく文脈判断。")
    out.append(" 手順の「〜してください」と箇条書き先頭のラベルの太字は数えない)")
    out.append("")
    sections = [
        ("principle_1_fillers", "前置きフィラー", "S1"),
        ("principle_3_buzzwords", "万能語", "S2"),
        ("principle_7_bold_emphasis", "太字（ラベルを除く）", "S3"),
        ("principle_6_hedges", "ヘッジ・両論併記", "S4"),
        ("reference_closings", "空虚な結び", "S6"),
    ]
    for key, label, rule in sections:
        out.append(f"{label}: {_count_label(r[key])}    ({rule})")
    s = r["stats"]
    out.append(f"数字の密度: {s['numeric_per_1000_chars']} 個/1000字 (数字トークン {s['numeric_tokens']})")
    out.append(f"記号表記: {_count_label(r['symbol_notation'])}    (S9)")
    for key, label in WEAK_PHRASE_LABELS:
        out.append(f"{label}：{_count_label(r[key])}（暫定の弱シグナル）")
    out.append(f"ダッシュの密度: {s['dash_per_1000_chars']} 個/1000字 (ダッシュ {s['dash_count']}。地の文のみ)")
    out.append("")
    for key, label, rule in sections:
        hits = r[key]
        if not hits:
            continue
        out.append(f"--- {label} ({_count_label(hits)}) ---")
        for h in hits:
            q = "  [引用文脈?]" if h["in_quote_context"] else ""
            w = "[弱] " if h.get("severity") == "weak" else ""
            out.append(f"  L{h['line']}: {w}{h['match']}  |  {h['text']}{q}")
        out.append("")
    _append_symbol_detail(out, r["symbol_notation"])
    _append_weak_phrase_detail(out, r)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="定着レビュー用 機械スキャン")
    ap.add_argument("file", help="対象ファイル (Markdown / テキスト)")
    ap.add_argument("--json", action="store_true", help="JSON で出力")
    ap.add_argument("--baseline", metavar="PREV_JSON",
                    help="前回の --json 出力と比較し resolved/new/persisting を出力")
    ap.add_argument("--preserve", metavar="ORIGINAL",
                    help="原文と比較し、書き直しで消えた数字とインラインコードを出力")
    ap.add_argument("--profile", choices=["reference"],
                    help="参照系技術文書向けの設定（README・Issue・手順書など。日本語文書のみ）")
    args = ap.parse_args()

    with open(args.file, encoding="utf-8") as f:
        text = unicodedata.normalize("NFC", f.read())

    result = scan(text, args.profile)
    diff = None
    if args.baseline:
        diff = baseline_diff(
            load_baseline(args.baseline, args.profile), result,
            PROFILE_FINDING_KEYS[args.profile],
        )
    kept = None
    if args.preserve:
        kept = preserve_diff(load_preserve(args.preserve), text)

    if args.json:
        if diff is not None or kept is not None:
            result = dict(result)
        if diff is not None:
            result["baseline_diff"] = diff
        if kept is not None:
            result["preserve_diff"] = kept[0]
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print(summarize_reference(result) if args.profile == "reference" else summarize(result))
        if diff is not None:
            print(summarize_diff(diff))
        if kept is not None:
            if diff is not None:
                print()
            print(summarize_preserve(*kept))


if __name__ == "__main__":
    main()
