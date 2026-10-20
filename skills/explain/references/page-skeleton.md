# 二層ページの骨格と保存・公開

HTML 生成（`SKILL.md` 手順 5）と保存・公開（手順 7）で使う。上の階と下の階に何をどの順で置くか、
色と字をどう定義するか、絵をどう描くか、できたものをどこへ書き出すかを決める。

骨格を固定するのは、毎回の生成で読者が同じ場所に同じものを見つけられるようにするためである。上の階は
絵と一文（と、あるときは着地）だけで読み切れ、疑ったときは下の階の同じ番号を引けば根拠が出てくる —
この動線が毎回変わると、下の階は「あることは分かるが読まれない付録」になる。
配布先の既知の宣言があるときは、上の階から省いた内容を下の階の「前提とした知識」に置き、
上の階とその前提で読み切れるようにする。

本 reference は**置き場所**を決める。文の中身と比喩の選び方は `simplification.md`、事実リストの値と
裏取りは `fact-check.md` が決める。

## ファイルの形

出力は HTML 1 ファイルで、**`<body>` の中身だけを書く**（外部から読むのは Google Fonts だけ）。`<!DOCTYPE>` / `<html>` /
`<head>` / `<body>` の各タグは書かない。Artifact ツールは渡されたファイルを publish 時に
`<!doctype html>…<head>…</head><body>` で包むため、自前で書くと二重になる。この形のままブラウザで
直接開いても表示される（ブラウザは省略された骨格を補う）ので、ローカル保存と Artifact 公開で同じ
1 ファイルを使える。

先頭は次の順に置く。

1. `<meta charset="utf-8">` — 文字符号化の宣言。`file://` で開いたときの表示が閲覧環境に依存しない
   ようにする。Artifact がこのファイルを `<body>` で包むとこのタグも `<body>` 内に入るが、符号化の
   決定には使われず表示にも影響しない
2. `<title>` — explain はトピックの問いの形（例：`<title>DNS ってなに？</title>`）、文書系スキルは文書の
   題名をそのまま書く。Artifact はファイル先頭 8KB しか走査しないため、charset の直後（ファイル先頭付近）に置く
3. `<link>` — Google Fonts のスタイルシートを読むときだけ置く（下記「外部依存」で許した唯一の
   外部読み込み）。`<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=...&display=swap">`
   の形。**`display=swap` を必ず付ける** — 既定の `auto` はフォント取得中に本文を見えなくするため、
   応答が遅い環境で読者が白紙を見る
4. `<style>` — トークン定義から始める全 CSS
5. 本文 — explain は上の階 → 階段 → 下の階。文書系スキルは自分の文書の構成をそのまま写す。本文は
   `<main lang="ja">` で包む（英語の文書は `lang="en"`）。テーマの切り替えのボタンと tech-write の目次は
   `<main>` の前に置く。Artifact が足す骨格の `<html>` には `lang` が無いので、ここで言語を示さないと、
   見出しの `word-break: auto-phrase` が効かず、「認可コ」「ードフロー」のように語の途中で折れる

```html
<meta charset="utf-8">
<title>DNS ってなに？</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=...&display=swap">
<style>/* トークン定義から始める全 CSS */</style>
<div class="theme" role="group" aria-label="表示の明るさ">…</div>
<main lang="ja">
  <h1>DNS ってなに？</h1>
  …
</main>
```

## 上の階の骨格

順序を固定する。4 要素を上から次のとおり並べる。着地は任意なので、無いときは 3 要素になる。

| 順 | 要素 | 中身 |
|----|------|------|
| 1 | 見出し | `<h1>` にトピック（問いの形）。直下に一文の要約を 1 行。レベル名は出さない |
| 2 | パネル | 3〜7 枚。既知の宣言による省略で 3 枚未満になるときは、残る行だけで 1〜2 枚にしてよい。各パネルは `<figure>` で、inline SVG → 一文 → 添え書き（任意）→ 根拠ピンの順 |
| 3 | 着地 | 任意。1 ページに 1 つまで。主張 1 文 + 根拠ピン。無いときは要素ごと出さない |
| 4 | 階段 | 下の階へ降りることを示す短い区切り。`<hr>` 1 本と 1 行の案内文 |

パネル 1 枚の形は次に固定する。

```html
<figure class="panel" id="p2">
  <svg viewBox="0 0 320 180" width="320" role="img" aria-label="{絵の説明}"><!-- 図形 --></svg>
  <figcaption>
    <p class="claim">{一文}</p>
    <p class="note">{限定条件}</p>
    <p class="pin">くわしくは <a href="#f2">事実 2</a></p>
  </figcaption>
</figure>
```

複数の事実に基づくときは、「事実 n」の語ごとをリンクにし、中黒はリンクの外に置く。

```html
<p class="pin">くわしくは <a href="#f2">事実 2</a>・<a href="#f3">事実 3</a></p>
```

- 一直線のパネルは因果の順に並べる。前のパネルの結果が次のパネルの入力になる並びで、重要度順・話題別にしない。
  他の形の配置は下の「形ごとのパネルと図」に従う
- 添え書きは限定条件を置く行である。言い換えの置き場所ではない。同じものの別名はここに回してよい。
  無いパネルでは `<p class="note">` を出力しない（空要素を残さない）
- 根拠ピンの形式は `くわしくは <a href="#f{n}">事実 n</a>` に固定する。`{n}` は事実リストの No 列の値
- パネルの `id` は小文字 `p{n}`（n はパネルの通し番号）にする。事実リストの図列は `fact-check.md` が
  大文字 `P3` の形で持つので、対応は「図列 `P3` ↔ id `p3`」と大小だけが違う。HTML の id は大小を
  区別するため、図列の値をそのまま `href` に使わない
- パネルが 7 枚を超えたら、連鎖を保ったまま隣り合う環を統合して 7 枚以下にする。統合できない環は下の
  階の事実リストに残し、上の階からは外す。形に必要なつながりを外して欠落するなら、
  `simplification.md` の欠落の処置を取る。枚数だけを理由に条件・出来事・対を捨てない

### 形ごとのパネルと図

`fact-check.md` で選んだ形をページ全体で使う。見出し・各 figure の構造・着地・階段・下の階は保つ。
一直線では従来の一列の配置と因果の順を変えない。他の形でも 1 パネル 1 主張を守り、
同じ状態や送受信者の名前はパネル間でそろえる。接続は事実リストの「つながり」に合わせる。

| 形 | パネルの配置 | inline SVG で常時示すもの |
|----|--------------|---------------------------|
| 分岐 | 共通の分かれ目を先に置き、その後の道を条件ごとの組に分けて横に並べる。合流先は道の組の後に置く。狭い画面では条件名を残して道ごとに縦へ並べる | 分かれ目から各道へ向かう矢印と、その道へ進む条件。許可と拒否のように異なる結果を別の道として描く |
| 状態遷移 | 開始状態からたどれる順に遷移のパネルを置き、戻る遷移も描く。番号順を進むだけの図にしない | 各矢印の前後の状態と、矢印に添えた出来事。戻りの矢印は同じ名前の状態へ向ける |
| 往復 | 送受信者の位置を全パネルでそろえ、要求と対応する応答を隣接する組として置く。続きの要求はその組の後に置く | 要求は送信者から受信者へ、応答はその逆へ向かう矢印。何への応答かが分かる名前や文を添える |

1 つの主張を描くための条件付きの複数矢印や要求への対応は、別の主張を増やすことではない。
事実が異なる主張ならパネルを分け、必要な根拠ピンを付ける。線や位置だけに頼らず、条件・出来事・
対応する要求を読める字で示す。ホバー・クリックによる強調や動的な図は使わない。
分岐の道を外したときは、その道の条件名と矢印も上の階から外し、共通の合流先への別の道は保つ。

着地の形は次に固定する。置く位置は最後のパネルの後、階段の前。

```html
<section class="landing">
  <p class="claim">だからサイトを移しても、しばらく古いほうが見える。</p>
  <p class="pin">くわしくは <a href="#f4">事実 4</a></p>
</section>
```

- 1 ページに 1 つまで。2 つ以上は 1 つに絞り、絞れないものはパネル側に戻す
- 主張は事実リストの行から引き、根拠ピンを持つ。ピンの形式はパネルと同じ
  `くわしくは <a href="#f{n}">事実 n</a>`。`{n}` は事実リストの No 列の値
- 主張は読者が経験しうる出来事の形で書く。最後のパネルの一文の言い直しは着地ではないので省く
- 根拠行が CONTRADICTED なら着地を出さない（`SKILL.md` の CONTRADICTED 規則）
- 根拠行が UNVERIFIED または「未検証（上限）」なら、言い切りの度合いを落とす
  （`fact-check.md` の結果の扱い）
- 添え書きはパネルと同じ。限定条件があるときだけ `<p class="note">` を置く。無いときは
  `<p class="note">` を出力しない
- ふさわしい行が無いとき、および省くと決めたときは `<section class="landing">` ごと出さない。
  空の見出しを残さない
- 着地は上の階の要素である。下の階の骨格には足さない

階段は次の 2 行に固定する。着地があるときはその直後に置く。

```html
<hr class="stairs">
<p class="stairs-note">ここまでが説明。ここから下は、その根拠です。</p>
```

## 下の階の骨格

順序を固定する。上から次のとおり並べる。既知の宣言があるときだけ、
「前提とした知識」を凡例とつまずき点の間に加える。実行根拠または文書との食い違いの記録があるときだけ、
「実行の検証記録」を事実リストの単純化欄の後に加える。記録が無ければ節を出さず、通常の構成を保つ。
比喩を 1 本以上使ったときだけ、順 5 の「このたとえ話が壊れるところ」を置く。比喩が 0 本のときは順 5 を
見出しごと出さず、事実リスト（実行の検証記録があればその後）の次に読了チェックを置く。

| 順 | 要素 | 中身 |
|----|------|------|
| 1 | 検証サマリ | `fact-check.md` の「検証サマリ」が定める 1 行をそのまま置く（`対象 N 件 / 一致 a / 単純化あり b / 確認できず c / 上限で裏取りせず u / 裏取り所要 s 秒`。未計測時の表示も同節に従う） |
| 2 | 凡例 | 下の階に出てくる 4 語の意味を 1 行ずつ。語は `fact-check.md` の検証サマリに揃えて「一致」「単純化あり」「確認できず」「上限で裏取りせず」を使う（下記） |
| 3 | つまずき点 | 入力か推定かを見出しで区別した問いの箇条書き（下記） |
| 4 | 事実リスト | 一直線は 6 列、他の形は「つながり」を足した 7 列の表 + その直下の「単純化」欄（下記） |
| 5 | このたとえ話が壊れるところ | 使った比喩ごとに、どこから成り立たなくなるかを 1 行ずつ（比喩を使ったときだけ置く） |
| 6 | 読了チェック | 3 問。答えは `<details>` に畳む |

凡例の 4 語は次に固定する。`fact-check.md` は「一致」を「VERIFIED の件数であって裏取りが済んだ件数
ではない」、「確認できず」を「状態列の『未検証（上限）』と字面で衝突させないための語」と定めており、
凡例が別の語を当てると下の階の中で同じものが 2 通りに呼ばれる。

| 語 | 意味 |
|----|------|
| 一致 | 一次ソース、または条件をそろえた最小の実行例で事実を確認した（状態列の `VERIFIED`） |
| 単純化あり | 説明のときに限定条件を落とした。落とした中身は下の「単純化」欄にある。裏取りしなかった行も含めて事実リストの全行から数えるので、検証サマリの「対象」より多くなることがある |
| 確認できず | 裏取りしたが、根拠を確認できなかった（状態列の `UNVERIFIED:<理由>`） |
| 上限で裏取りせず | 件数の上限で、裏取りに回さなかった（状態列の「未検証（上限）」）。検証サマリの「対象」に入らない。この行に由来する文は言い切らず、「（未確認）」などを付けている |

凡例は検証サマリに出る語で書く。`fact-check.md` が値に使う `N`・`a`・`b`・`c`・`u` の文字はページに
出ないので、凡例でも使わない。

一直線の事実リストの表頭は `fact-check.md` の 6 列をそのまま使い、列を足さない。
他の形だけは末尾に「つながり」を足し、各行に同 reference の No と条件・対応を表示する。
表の前には同 reference の始点を置く。一直線には始点の行や空の 7 列目を足さない。表の容器はキーボードでも
スクロールできるよう `tabindex="0"` と `role="region"` を付ける（マウスを使わない読者が横に長い表を
読めなくなるため）。

```html
<div class="scroll-x" tabindex="0" role="region" aria-label="事実リスト">
  <table class="facts">
    <thead><tr><th>No</th><th>事実</th><th>限定条件</th><th>状態</th><th>出典</th><th>図</th></tr></thead>
    <tbody>
      <tr id="f2"><td>2</td><td>…</td><td>…</td><td>VERIFIED</td><td>RFC 1035 §3.2.1</td><td><a href="#p2">P2</a></td></tr>
    </tbody>
  </table>
</div>
```

各行に `id="f{n}"` を付ける。`{n}` は同じ行の No 列の値。図列はパネルへのリンク
`<a href="#p{n}">P{n}</a>` にする。リンクの文字は列の値そのものにし、案内文を足さない。
対応するパネルが無い行は図列を空欄のままにする。空の `href="#"` を書かない。

読了チェックは `fact-check.md` の「つまずき点の記録」から起こし、3 問の少なくとも 1 問で
その問いへの答えを問う。残りも上の階の説明を確かめる問いにする。答えられる範囲と内部検査は
`SKILL.md` に従い、つまずき点の記録節や事実リストを読まないと答えられない問いにしない。
形は次のとおり。

```html
<details class="quiz">
  <summary>{問い}</summary>
  <p>{答え}</p>
</details>
```

### 実行の検証記録

実行を根拠にした行には、fact-check.md の実行記録を表示する。見出しは「実行の検証記録」とし、
対象の元の事実・限定条件、実行日時、コマンドと最小例、版・OS・入力・設定、終了コードと出力の抜粋を示す。
記録した版と OS を省かず、「実行：〈コマンド〉（〈版〉、〈OS〉）」を事実リストの出典列にも書く。
文書根拠があれば文書名・位置と併記する。引用・出力は HTML として解釈させず、文字としてエスケープする。
コードと出力には本 reference の <pre> のスクロール規則を使う。

文書と実行が食い違った記録は、元の事実を事実表から外したり訂正したりしても残す。
文書の URL と引用、実行出力、比較した条件と判定理由を並べ、読者が両方を確認できるようにする。
文書が得られなければその旨を記す。元の No と事実の全文で対象を示し、現在の表の同じ No の行と混同させない。
記録の id は execution-1 などとして、事実表の f{n} と分ける。上の階の根拠ピンは現在の事実表だけを
指し、除外した元の行や検証記録へ付け替えない。空の節・架空の出力・省略した実行の成功記録は出さない。

### つまずき点の表示

`fact-check.md` の「つまずき点の記録」を箇条書きで示す。入力を使ったときの見出しは
「入力されたつまずき点」、推定したときは「推定したつまずき点」とする。各項目は問いと対応する
事実行へのリンクを持ち、対応行なしの項目はその旨を記す。推定した項目には事実の状態・出典・
検証済みを表すバッジを付けない。事実表へ問いの行を混ぜない。

### 「前提とした知識」節

配布先の既知の宣言があるときだけ出す。宣言の文と、`simplification.md` の「配布先の既知による省略」で
省いた行の事実 No・事実・限定条件を因果順に列挙する。リンク先を見ることを前提にせず、この節の本文だけで
省いた内容を理解できるようにする。裏取りの状態に応じた言い切りは同 reference に従う。

```html
<section class="known" aria-labelledby="known-h">
  <h2 id="known-h">前提とした知識</h2>
  <p>配布先の宣言：HTTP は知っている</p>
  <ul>
    <li><a href="#f1">事実 1</a>：ブラウザが HTTP の要求を送り、サーバが応答を返す。限定条件：HTTP の要求と応答による通信の場合。</li>
  </ul>
</section>
```

宣言があっても省いた行が無いときは、宣言の文に続けて「省いた行はない」と書き、空のリストは置かない。
宣言が空なら節ごと出さず、空の見出しも残さない。省いた行は事実リストにも状態・出典つきで残し、
対応するパネルが無いので図列は空欄にする。全行に当たる宣言でも、上の階に残す末尾行は省いた行に含めない。

読了チェック 3 問は、宣言があれば上の階とこの節だけ、宣言が空なら上の階だけで答えられる内容にする。
事実リストや出典を開かないと答えられない問いは、`SKILL.md` の内部検査で直す。

### 「単純化」欄

`simplification.md` が「下の階の『単純化』欄に記録する」と書くときの記録先は、**事実リストの表の直下に
置く「単純化」欄**である。事実リスト要素の一部であって、下の階に独立した要素として足さない。

```html
<section class="simplification" aria-labelledby="simplification-h">
  <h3 id="simplification-h">単純化</h3>
  <ul>
    <li>事実 3: この 3 回はキャッシュが空のときの話である</li>
  </ul>
  <p class="level-note">もっとやさしく書くなら「期限」とだけ書くところを、ここでは TTL という名前で呼んでいる。</p>
</section>
```

この 1 箇所に次の 2 種類を書く。記録先を 2 箇所に割らない。

| 書くもの | 出所 | 形 |
|---------|------|-----|
| 上の階から落とした限定条件 | `simplification.md` の「省略の 2 分類」判定手順 2 段目、「過度一般化の検査」3 段目 | `<ul>` の項目。`事実 n: ` に続けて `simplification.md` が定める記録文をそのまま書く（同 reference の「この文は〈限定条件〉のときの話である」の形。限定条件だけを裸で置かない） |
| もっとやさしく書くなら | `simplification.md` のレベル表の同名の列 | `<p class="level-note">` の 1 行。5 歳の段では出力しない |

検証サマリの `b`（単純化ありの件数）の数え方は `fact-check.md` の `b` に従う。

落とした限定条件を**事実リストの状態列に書かない**。状態列は裏取りの 3 分類（と「未検証（上限）」）
専用で、`fact-check.md` が「単純化は裏取りの状態と別の軸であり、混ぜて 1 つの状態列にしない」と
定めている。VERIFIED かつ単純化ありの行は普通に存在する。

落とした限定条件が 1 つもなく、かつレベルの明示も無いときだけ、`<section class="simplification">`
ごと出力しない。空の見出しを残さないための規則で、**段だけを見て判断しない** — レベルの明示が無いのは
5 歳の段だけだが、その段は限定条件を落とす（骨格 claim に紐づくものも含む）ので `<ul>` は最も長くなる。

## 表示しないもの

次の 5 つはページに出さない。

| 出さないもの | 理由 |
|------------|------|
| つながりチェックの結果 | 納品前の自己点検であり、読者向けの情報ではない（`SKILL.md` の内部検査） |
| 内部検査の結果 | 同上。不合格だった事実は納品報告で会話に伝える |
| 読みやすさ点検の結果 | 同上。実施状況と残った指摘は納品報告で会話に伝える（`SKILL.md` の読みやすさ点検） |
| レベル切替 UI | 1 回の実行で作るのは指定された 1 段だけである。切替は再実行で行う |
| レビューモード | 探索のプロトタイプ専用の仕掛けで、成果物には含めない |

## 色と字

トークンを `:root` に定義し、本文とパネルは必ずトークン経由で色を引く。生の色値を要素に直書きしない。

文書の種類ごとに、書体とアクセント色を次の 1 組に固定する。explain・retention-write・tech-write のどれが
作ったページかで行を選び、下の雛形の `--font-body` / `--font-head` / `--font-mono` と、明るい側 2 箇所（1 段目と
4 段目）と暗い側 2 箇所（2 段目と 3 段目）の `--accent` / `--hi` / `--mark` / `--panel` / `--c1` / `--c1-soft` をその行の値に差し替える。ほかのトークンと規則は 3 スキルで
共通に使う。行に無い書体や色を足さない。

| スキル | 本文の書体 | 見出しの書体 | コードの書体 | アクセント（ライト / ダーク） | `--hi`・`--mark`（ライト / ダーク） | `--panel`（ライト / ダーク） | `--c1`・`--c1-soft`（ライト / ダーク） |
|--------|-----------|-------------|-------------|------------------------------|-----------------------------------|-----------------------------|--------------------------------------|
| explain | Noto Sans JP | Noto Sans JP | Source Code Pro | 青 `#1f5fbf` / `#6fa3ef` | `#dde8f8` / `#1d3150` | `#f3f6fb` / `#161c26` | 緑 `#1a7f37`・`#dcf0e1` / `#3fb950`・`#1c3524` |
| retention-write | 本文 Noto Serif JP | Noto Serif JP | Source Code Pro | 藍 `#2c4a7a` / `#8fb0e6` | `#e1e7f1` / `#24324a` | `#f3f5f9` / `#191e28` | 緑 `#1a7f37`・`#dcf0e1` / `#3fb950`・`#1c3524` |
| tech-write | IBM Plex Sans JP | IBM Plex Sans JP | IBM Plex Mono | 緑 `#1a7f37` / `#3fb950` | `#dcf0e1` / `#1c3524` | `#f4f8f5` / `#17211a` | 青 `#1f5fbf`・`#e2ecfa` / `#79aef0`・`#1b2c44` |

地・字・罫は無彩色にする。色には次の 2 つの役だけを持たせ、飾りのためには塗らない。

- **アクセント**（`--accent` と、そこから作った淡い `--hi` / `--mark` / `--panel`）：リンク、見出しの左の帯、
  冒頭の帯と主役図の台紙、強調する 1 か所
- **区別の色**（`--c1` / `--c2` / `--c3` と、淡い `--c1-soft` / `--c2-soft` / `--c3-soft`）：文書の中で
  繰り返し出てくる対象（型・段階・立場・比べる候補など）を見分ける。対象ごとに 1 色を決め、図の箱・節の見出しの
  帯・表・本文の札（`.tag`）のどこでも同じ色を当てる。読者は色だけで、いまどの対象の話かが分かる。3 色まで
  使う。`--c2`（紫）と `--c3`（ローズ）は 3 スキル共通で、`--c1` だけを上の表の行の値にする。区別の色が
  アクセントと同じ色相だと、対象の色と強調の色が見分けられなくなるので、`--c1` はアクセントと違う色相にしてある。
  見分ける対象が 4 つ以上あるときは、本文で節や小節を立てて説明している対象を優先して 3 つに色を当て、
  残りは無彩色（`--muted` と `--fill`）にする。見分ける対象がない文書では使わない

クリーム色の地とテラコッタのアクセントの組は、生成 AI の画面の配色そのもので、ひと目で AI が作ったページに
見えるので使わない。地を黄みに寄せたり、アクセントや区別の色を橙・赤茶に寄せたりもしない。

テーマを決める手がかりは 3 つあり、優先する順に次のとおり。

1. ページの切り替えのボタン（下の「テーマの切り替え」）：根要素の `data-page-theme` に `light` か `dark` を付ける
2. 閲覧環境の選択：claude.ai の Artifact では、閲覧者が明示的に選ぶと根要素に `data-theme="dark"` か
   `data-theme="light"` が付く。既定（システム任せ）では何も付かない
3. OS の設定：`prefers-color-scheme`

この順を CSS の並び順だけで成り立たせるため、次の 4 段で書く。雛形の書体と色は explain の行の値である。

```html
<style>
  /* 1. 明るい側の完全な定義。ここだけで全トークンが揃う。
     color-scheme はスクロールバーやボタンなど、ブラウザが描く部品の明暗をテーマに合わせる */
  :root {
    color-scheme: light;
    --bg: #ffffff;
    --fg: #222222;
    --muted: #5c5c5c;
    --line: #222222;        /* SVG の線 */
    --fill: #f2f2f2;        /* SVG の面。地に近い無彩色 */
    --accent: #1f5fbf;
    --hi: #dde8f8;          /* SVG の強調する 1 か所の面。アクセントを薄めた色 */
    --rule: #dadada;        /* 罫線・区切り */
    --mark: #dde8f8;        /* 着地した事実行の目印 */
    --panel: #f3f6fb;       /* 冒頭の帯と主役図の台紙。アクセントをごく薄く混ぜた地 */
    --c1: #1a7f37; --c1-soft: #dcf0e1;  /* 区別の色。--c1 はスキルの行の値、--c2・--c3 は 3 スキル共通 */
    --c2: #7c3aad; --c2-soft: #efe4f8;
    --c3: #be185d; --c3-soft: #fbe4ef;
    --font-body: "Noto Sans JP", "Hiragino Sans", "Yu Gothic", system-ui, sans-serif;
    --font-head: "Noto Sans JP", "Hiragino Sans", "Yu Gothic", system-ui, sans-serif;
    --font-mono: "Source Code Pro", ui-monospace, SFMono-Regular, Menlo, monospace;
  }

  /* 2. システムが暗いとき。ただし閲覧者が light を選んでいたら適用しない */
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --bg: #171717;
      --fg: #e6e6e6;
      --muted: #9e9e9e;
      --line: #e6e6e6;
      --fill: #262626;
      --accent: #6fa3ef;
      --hi: #1d3150;
      --rule: #363636;
      --mark: #1d3150;
      --panel: #161c26;
      --c1: #3fb950; --c1-soft: #1c3524;
      --c2: #c39be6; --c2-soft: #2e2240;
      --c3: #f07aae; --c3-soft: #3d1a2b;
    }
  }

  /* 3. 閲覧環境かページのボタンで dark を選んだとき。明るいシステムでも適用される */
  :root[data-theme="dark"],
  :root[data-page-theme="dark"] {
    color-scheme: dark;
    --bg: #171717;
    --fg: #e6e6e6;
    --muted: #9e9e9e;
    --line: #e6e6e6;
    --fill: #262626;
    --accent: #6fa3ef;
    --hi: #1d3150;
    --rule: #363636;
    --mark: #1d3150;
    --panel: #161c26;
    --c1: #3fb950; --c1-soft: #1c3524;
    --c2: #c39be6; --c2-soft: #2e2240;
    --c3: #f07aae; --c3-soft: #3d1a2b;
  }

  /* 4. ページのボタンで light を選んだとき。閲覧環境や OS が暗くても明るい側に戻す。
     2・3 段と詳細度が同じなので、最後に置いて並び順で勝たせる */
  :root[data-page-theme="light"] {
    color-scheme: light;
    --bg: #ffffff;
    --fg: #222222;
    --muted: #5c5c5c;
    --line: #222222;
    --fill: #f2f2f2;
    --accent: #1f5fbf;
    --hi: #dde8f8;
    --rule: #dadada;
    --mark: #dde8f8;
    --panel: #f3f6fb;
    --c1: #1a7f37; --c1-soft: #dcf0e1;
    --c2: #7c3aad; --c2-soft: #efe4f8;
    --c3: #be185d; --c3-soft: #fbe4ef;
  }

  /* 台紙の内側の余白を幅に含める。含めないと、台紙だけが本文の列から右へはみ出す */
  *, *::before, *::after { box-sizing: border-box; }

  /* body の背景は必ず明示する。透明のままだと閲覧環境の地の色が透ける。
     字の既定もここで決める（毎回の生成で同じ系統にするため散文ではなく雛形に置く） */
  body {
    background: var(--bg);
    color: var(--fg);
    font-family: var(--font-body);
    font-size: 1.0625rem;  /* 既定 16px 環境で 17px。px 直書きは読者の文字サイズ設定を上書きする */
    line-height: 1.8;
    max-width: 40em;       /* 1 行を全角 40 字前後に収める */
    line-break: strict;    /* 小書きの仮名や長音符を行頭に送らない */
    text-autospace: normal; /* 和文と欧文・数字の間に四分の空きを入れる */
    font-synthesis: none;  /* 読み込んでいない太さを偽の太字で作らせない */
  }

  /* 詰め組・行の釣り合い・文節での改行は見出しにだけ掛ける。本文に掛けると字間と行末がそろわない */
  h1, h2, h3 {
    font-family: var(--font-head);
    font-weight: 700;
    line-height: 1.45;
    font-feature-settings: "palt";
    text-wrap: balance;
    word-break: auto-phrase;
    margin: 2.2em 0 .6em;
  }
  h1 { font-size: 1.75rem; margin-top: 0; }
  /* h2 の左に太い帯を引く。節に区別の色（--sec）が決まっていればその色、なければアクセント */
  h2 {
    font-size: 1.35rem;
    margin-top: 3em;
    padding: .1em 0 .1em .7em;
    border-left: .3rem solid var(--sec, var(--accent));
  }
  h3 { font-size: 1.1rem; }

  /* 区別の色。節の要素（<section>）や図に付けると、中の見出しの帯・表の見出し行・箇条の記号がその色になる。
     見分ける対象がない文書では使わない */
  .is-c1 { --sec: var(--c1); --sec-soft: var(--c1-soft); }
  .is-c2 { --sec: var(--c2); --sec-soft: var(--c2-soft); }
  .is-c3 { --sec: var(--c3); --sec-soft: var(--c3-soft); }
  /* 区別の色を決めた小節の h3 にも、同じ色の細い帯を引く */
  :is(.is-c1, .is-c2, .is-c3) > h3 { padding-left: .6em; border-left: .2rem solid var(--sec); }
  /* 本文や表の中で対象の名前に付ける札 */
  .tag {
    display: inline-block; padding: 0 .5em; border-radius: 3px;
    font-size: .85em; font-weight: 700; line-height: 1.7; white-space: nowrap;
    color: var(--sec, var(--muted)); background: var(--sec-soft, var(--fill));
  }
  /* 表の中の札は折り返す。折り返さないと狭い幅で 1 列目だけが広がり、右の列が押し出される */
  td .tag { white-space: normal; }

  /* 定義したトークンは、区別の色（--c1〜--c3）と、文書系スキルの --mark を除いて必ずどこかで使う。使わないトークンは次の生成で値がずれる。
     --hi は inline SVG の強調する 1 か所の fill で使う */
  a { color: inherit; text-decoration-color: var(--muted); text-underline-offset: .2em; }
  a:hover { color: var(--accent); }
  .panel .claim { font-size: 1.15em; }
  .panel { scroll-margin-top: 5rem; background: var(--panel); border-radius: 6px; padding: 1.4rem 1.25rem 1rem; }
  .panel:target { outline: 2px solid var(--accent); outline-offset: .5rem; }
  .note { color: var(--muted); font-size: .95em; margin: 0 0 .2em; }
  .pin { color: var(--muted); font-size: .9em; }
  .pin a { color: var(--accent); }
  /* <!DOCTYPE> の無いファイルをブラウザで直接開くと互換モードで描かれ、表が本文の字の色と大きさを受け継がない。
     受け継ぎを明示しないと、表の字が本文より小さくなり、テーマを切り替えたときに字の色だけが前のテーマに残る */
  table { border-collapse: collapse; color: inherit; font-size: inherit; }
  th, td {
    border-bottom: 1px solid var(--rule);
    padding: .5em .7em;
    text-align: left;
    vertical-align: top;
    overflow-wrap: normal;  /* 語の途中で折らない */
    line-break: strict;
    word-break: normal;     /* 日本語は字の間で折る。文節で折ると狭い画面で列の幅が足りなくなる */
  }
  th { font-weight: 700; }
  thead th { background: var(--sec-soft, var(--fill)); border-bottom: 2px solid var(--sec, var(--accent)); }
  li::marker { color: var(--sec, var(--accent)); }
  td code, th code { white-space: nowrap; }
  /* 日付・版番号のようにハイフンや点でつないだ語を、ハイフンの後ろで折らない */
  .nobr { white-space: nowrap; }
  /* 狭い画面の 1 行に収まらない長い値（例の値・ハッシュ・トークン・長い URL）は、どの字の後ろでも折る */
  code.break { white-space: normal; overflow-wrap: anywhere; }
  .facts tbody tr { scroll-margin-top: 5rem; }
  .facts tbody tr:target { background: var(--mark); }
  @media (prefers-reduced-motion: no-preference) {
    html { scroll-behavior: smooth; }
  }
  hr.stairs { border: 0; border-top: 1px solid var(--rule); margin: 3rem 0 1rem; }
  .stairs-note { color: var(--muted); }
  .quiz summary { color: var(--accent); cursor: pointer; }
  .level-note { color: var(--muted); }
  pre, code { font-family: var(--font-mono); }
</style>
```

2 段目の `:not([data-theme="light"])` を落とすと、暗いシステムで明るいテーマを選んだ閲覧者に暗い色が
出る。トークンが並んでいても優先の順にならないので、この guard は省略しない。4 段目は 1 段目と同じ明るい側の
値を写したもので、1 段目の値を変えたら 4 段目も同じ値に変える。4 段目を 2・3 段目より前に置くと、暗いシステムや
閲覧環境のダークが勝ち、ボタンの「ライト」が効かない。

### テーマの切り替え

ページの右上に、閲覧者がテーマを選ぶボタンを置く。OS がダークの閲覧者でも、白地で読みたいときに切り替え
られるようにするためである。選べるのは「自動」（閲覧環境の選択、無ければ OS の設定に従う）・「ライト」・「ダーク」の
3 つで、押すと根要素の `data-page-theme` を書き換える。上の 4 段の CSS がこの印で色を切り替えるので、色の定義は
足さない。

ボタンは `data-theme` に書き込まない。`data-theme` は claude.ai の Artifact などの閲覧環境が付ける印で、ボタンが
同じ印を書き換えると、閲覧環境で選んだテーマを「自動」が消してしまう。閲覧環境が後から印を書き換えたときも、
ボタンの押された表示が実際の表示と食い違う。印を分ければ、優先の順は CSS の並び順だけで決まり、ボタンの表示は
いつもページ自身の選択と一致する。

ボタンは `<body>` の中身の先頭（`<style>` の直後）に置く。

```html
<div class="theme" role="group" aria-label="表示の明るさ">
  <button type="button" data-set="auto" aria-pressed="true">自動</button>
  <button type="button" data-set="light" aria-pressed="false">ライト</button>
  <button type="button" data-set="dark" aria-pressed="false">ダーク</button>
</div>
<script>
  (() => {
    const root = document.documentElement;
    const buttons = document.querySelectorAll('.theme button');
    const apply = (mode) => {
      if (mode === 'auto') root.removeAttribute('data-page-theme');
      else root.setAttribute('data-page-theme', mode);
      buttons.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.set === mode)));
    };
    // 選んだテーマはこの閲覧者のブラウザにだけ残す。保存できない環境でも表示は切り替わる
    let saved = null;
    try { saved = localStorage.getItem('theme'); } catch (e) {}
    if (saved === 'light' || saved === 'dark') apply(saved);
    buttons.forEach((b) => b.addEventListener('click', () => {
      apply(b.dataset.set);
      try { localStorage.setItem('theme', b.dataset.set); } catch (e) {}
    }));
  })();
</script>
<style>
  /* 右上に固定し、本文の列の幅には入れない */
  .theme {
    position: fixed; top: .75rem; right: .75rem; z-index: 10;
    display: flex; border: 1px solid var(--rule); border-radius: 6px; overflow: hidden;
    background: var(--bg); font-size: .8rem;
  }
  .theme button { font: inherit; color: var(--muted); background: none; border: 0; padding: .35em .8em; cursor: pointer; }
  .theme button + button { border-left: 1px solid var(--rule); }
  .theme button[aria-pressed="true"] { color: var(--fg); background: var(--fill); font-weight: 700; }
  .theme button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  @media print { .theme { display: none; } }
  /* 狭い画面では、ボタンをページの先頭の空きに置き、スクロールしても本文の字に重ならないようにする */
  @media (max-width: 600px) {
    body { padding-top: 3.5rem; }
    .theme { position: absolute; }
  }
</style>
```

上の例は読みやすさのために CSS を並べて書いている。実際のページでは、CSS は先頭の `<style>` へ統合する。

- `localStorage` の読み書きは `try` で包む。プライベートウィンドウなど保存を許さない環境では例外が出るが、
  切り替え自体は動かす
- テーマを切り替えたら、表の字が本文と同じ濃さで出ることを確かめる。雛形の `table` の `color: inherit` を
  落とすと、手元のファイルで開いたとき表の字だけが前のテーマの色に残る

### 書体の読み込みと太さ

`font-synthesis: none` と、Google Fonts の読み込み URL のウェイト指定 `wght@400;700` は対で使う。
`font-synthesis: none` はブラウザが太字を合成するのを止めるので、700 を読み込まずに書くと見出しと
`<strong>` が太字にならない。逆に 400 と 700 を読み込んでも `font-synthesis: none` を書かないと、
読み込みが遅れたときや代替フォントで、ブラウザが字を太らせて潰れた太字を出す。片方だけでは使わない。
CSS の `font-weight` も 400 と 700 の 2 つだけにする（600 などは読み込んでいないので、近い太さへ丸められる）。

`<link>` の URL は、表の行の書体を 400 と 700 で読む次の形にする。

| スキル | `<link>` の `href` |
|--------|-------------------|
| explain | `https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&family=Source+Code+Pro:wght@400;700&display=swap` |
| retention-write | `https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700&family=Source+Code+Pro:wght@400;700&display=swap` |
| tech-write | `https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+JP:wght@400;700&family=IBM+Plex+Mono:wght@400;700&display=swap` |

代替フォントの並びは、retention-write の明朝では `"Noto Serif JP", "Hiragino Mincho ProN", "Yu Mincho", serif`、
tech-write では `"IBM Plex Sans JP", "Hiragino Sans", "Yu Gothic", system-ui, sans-serif` と
`"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace` にする。

### 組版の既定

本文と見出しで、日本語の組版の規則を分ける。

- 本文（`body`）：行の幅は `max-width: 40em`、`line-break: strict`、`text-autospace: normal`。
  1 行を 40 字前後に保ち、行頭の禁則を厳しくし、和文と欧文の間を空ける
- 見出し（`h1`〜`h3`）だけ：`font-feature-settings: "palt"`（詰め組）、`text-wrap: balance`（行の長さの釣り合い）、
  `word-break: auto-phrase`（文節での改行）。本文の `body`・`p`・`li` には掛けない。本文で詰めると字間が
  不ぞろいになり、`balance` は長い段落の行末をがたつかせる
- 日付（`1873-01-01`）・版番号（`0.7.0`）・識別子・コマンドのオプション名（`--no-ff`）・ハイフンでつないだ
  用語（fast-forward）のように、ハイフンや点でつないだ一続きの語は、見出しでも
  本文でも `<span class="nobr">` で包む。ブラウザはハイフンの後ろを改行してよい位置として扱い、見出しの
  `text-wrap: balance` が行の長さをそろえようとして「1873-」と「01-01」に割ることがある。`line-break: strict`
  ではこの改行を止められない。文字を改行しないハイフン（U+2011）に置き換えて防がない。コピーした語が元の字と
  別の文字になり、検索に掛からなくなる
- `nobr` で包むのは、狭い画面（390px）の 1 行に収まる短い語だけにする。`<code>` に入れて書く値（例として出す
  値・ハッシュ・トークン・パラメータの組）が半角 20 字を超えるときは、`nobr` で包まず `<code class="break">` に
  してどの字の後ろでも折る。長い値を包むと 1 行に収まらず、ページ本体が横にスクロールする（「レイアウト」）。
  地の文の語を、折るためだけに `<code>` へ入れない。出典一覧の URL は、出典一覧の CSS が折る
- 見出しはブラウザ既定のまま置かない。大きさ・行間・上下の空きは雛形の `h1` / `h2` / `h3` の規則を使う
- 表のセル：`overflow-wrap: normal` で英単語の途中で折らず、日本語は `word-break: normal` で字の間で折る。
  `auto-phrase`（文節で折る）は見出しにだけ掛け、セルには掛けない。390px の 2 列の表で試すと、「アプリケーション。」の
  ような文節を割れないため 2 列目の最小の幅が 186px になり、表が列から 16px はみ出した。`keep-all` も使わない。
  日本語の文を句読点まで折らないので、文の入ったセルが列の幅を超え、表の右側が横スクロールの中に隠れる。表の中の `code` は
  `white-space: nowrap` にして、コマンドやパスを途中で折らない（長い値は上の `code.break`）。表の中の札
  （`.tag`）は折り返す。幅に収まらない表は `.scroll-x` の中で横にスクロールさせる（「レイアウト」）

見た目の既定は技術図解調にする。SVG の輪郭は細め、角は控えめに丸め、面は地に近い無彩色か区別の色の淡い側、
強調は 1 か所だけアクセント系の `--hi`。字と罫の既定は上の雛形が持つので、散文で言い直さずそのまま使う。
トークン名も上の例の `--bg` / `--fg` / `--muted` / `--line` / `--fill` / `--accent` / `--hi` / `--rule` /
`--mark` / `--panel` / `--c1`〜`--c3` / `--c1-soft`〜`--c3-soft` / `--font-body` / `--font-head` /
`--font-mono` を使い回し、毎回の生成で同じ系統の見た目にする。
台紙（`--panel` の面）を持つのは、冒頭の帯・主役図・explain のパネルだけにする。段落や箇条まで枠・影・背景色で
囲むと、どこが要かが分からなくなる。
線幅・角丸・図内の字の大きさは「inline SVG の規則」が、表示幅は「レイアウト」が決める。

## 外部依存

外部ホストへの通信は Artifact の CSP で遮断される。許すのは Google Fonts だけにする。

- **許可**：`https://fonts.googleapis.com` のスタイルシートと、そこが読む
  `https://fonts.gstatic.com` のフォント本体
- **必須**：どの `font-family` にも代替フォントを並べる。Google Fonts が読めない環境でも崩れない
  ことを優先する（上の `--font-body` / `--font-head` / `--font-mono` の形）
- **禁止**：外部画像（`<img src="https://…">`）、外部スクリプト、`fetch` / `XHR` / WebSocket、
  および **Google Fonts 以外の**外部スタイルシート。図はすべて inline SVG で描く

自前の CSS と JS はインラインに書く（外に置かない）。外部から読むのは上で許した Google Fonts の
スタイルシート 1 本だけで、その `<link>` は「ファイルの形」の順序 3 に置く。ページの JS は「テーマの切り替え」の
ボタンだけで足りる。`<details>` の開閉はブラウザの機能で足りる。

## inline SVG の規則

規則は 3 つ。

1. **ラベルも一文と同じ主従にする**。平易語を大きく、用語を括弧で小さく併記する。図の中だけの略語や
   言い換えを作らない。括弧内の用語が事実リストの語と字面一致していれば、「同じものが同じ名前で出てくる」
   を満たす
2. **矢印の向きは因果の向きと一致させる**。原因から結果へ向ける。図の見栄えのために逆向きに描かない。
   状態が戻るときや応答が返るときの逆向きの矢印は、その出来事・送受信の向きを表す
3. **1 パネル 1 主張**：1 枚の絵で 2 つのことを言わない。2 つ言いたくなったらパネルを分ける

描き方の制約も置く。

- 矩形・円・直線・短いパスで構成する。長いパスデータを手で書き起こさない
- `viewBox` を必ず付ける。付けない SVG は拡大率が計算できないので許さない。explain のパネルと補助図の幅は
  雛形どおり 320 を使う。retention-write と tech-write の主役図は、列いっぱいに置くので 640 まで広げてよい
- 幅属性は `viewBox` の幅と同じにする（`width="320"`）。CSS の `max-width` はこれを上限として切り詰め、広げない
- `role="img"` と `aria-label` を付ける。`aria-label` にはそのパネルの一文の要旨を書く
- 色は `var(--line)` / `var(--fill)` / `var(--accent)` / `var(--hi)` / `var(--muted)` / `var(--bg)` と、区別の色
  `var(--c1)`〜`var(--c3)` / `var(--c1-soft)`〜`var(--c3-soft)` で引く。生の色値を書かない（テーマが
  切り替わったとき線と面だけ取り残される）。トークン名 `--line`・`--fill`・`--accent` は変えずに使う
- 輪郭は細めにする。拡大率は「表示幅 ÷ `viewBox` 幅」である。幅属性を `viewBox` 幅と同じにすると
  デスクトップでは拡大率 1.0 になり、指定した `stroke-width` がそのまま実効の線幅になる。実効の線幅が
  1.2〜1.8px に収まる指定にする。既定は `stroke-width="1.5"`。幅属性を付け忘れたときでも、
  「レイアウト」の `max-width: min(22rem, 100%)` が天井になる。根要素の字が 16px のとき 22rem は 352px で、
  `viewBox` 幅 320 に対する拡大率は 352 ÷ 320 = 1.1 倍である
- 角は控えめに丸める。矩形の `rx` は 4 を既定にする
- 面は `var(--fill)` で塗る。`--fill` の値は地（`--bg`）に近い無彩色にし、色みを持たせない。区別の色を
  決めた対象の箱だけは、面を `var(--cN-soft)`、輪郭と主ラベルを `var(--cN)` にする（N は対象に決めた番号）。
  本文・表・見出しの帯と同じ番号を使い、図の中だけで色を変えない。面に濃い色（`--cN` そのもの）を使うのは
  1 枚に 1 か所までにし、その上の字は `var(--bg)` で抜く。濃い面が多いと、図が色の塊になって線とラベルが沈む
- 強調は新しいトークン `--hi` で引く。そのパネルの一文が指す 1 か所だけを `fill="var(--hi)"` で塗り、
  輪郭を `stroke="var(--accent)"` にしてよい。1 パネルに強調は 1 か所までで、`--hi` を地の代わりに使わない
- 図に具体値（実際の値の例）を置いてよい。置く量は 1 パネルに 1 組までとする
- 図内の主ラベルの `font-size` は 16 を既定にする。拡大率 1.0 のとき実効 16px で、本文 17px に対して
  0.94 倍に収まる。従ラベル（括弧内の用語）は主より小さくする。主ラベルの既定 16 は動かさない。
  はみ出した字を小さくして箱に収めない
- 箱と札の座標は、字の幅を見積もってから決める。全角 1 字は `font-size` と同じ幅、半角 1 字（数字・
  英字・記号・空白）は `font-size` の 0.55 倍で見積もる。Chrome で測った半角は 0.45 倍前後なので、
  見積もりは実際より少し広くなる。`text-anchor="middle"` の字は、`x` から左右へ幅の半分ずつ伸びる
- 箱の中の字は、見積もりの幅に左右 4 ずつの余白を足しても箱の幅に収める。たとえば `font-size="16"` の
  「サイトのサーバ」は 7 × 16 = 112 で、幅 110 の箱から左右に 1 ずつはみ出す。箱を広げて収める
- 矢印に付けた札（矢印のそばに置く字）は、どの箱とも重ねない。札の範囲は、横が見積もりの幅、縦が
  `y` から上へ `font-size` の高さである。この範囲が箱と交わるなら、札を箱の無い段（箱の上か下の空いた
  `y`）へ移すか、箱と箱の間を広げるか、札の文を短くする。たとえば `font-size="13"` の「192.0.2.1 を返す
  （未確認）」は 8 × 13 + 10 × 13 × 0.55 = 175.5 の幅で、間が 80 の 2 つの箱の間には置けない。
  「（未確認）」は裏取りの留保なので、札を短くするときも削らない

## レイアウト

ページの幅は 1 本だけにする。本文の行の幅は `max-width: 40em`（全角 40 字前後）で、冒頭の帯・図の台紙・
explain のパネル・表も、この列の中に置いて本文と同じ左端と右端にそろえる。本文の外へ張り出す要素も、
本文の横に並べる要素も作らない。画面に固定する操作部品（テーマの切り替えのボタンと、tech-write の左の目次）は
本文の列の外の余白に置く部品で、この規則の対象ではない。帯や図だけが広い・狭いと、右端が要素ごとに出入りし、読者の視線が左右に
振られる。台紙の内側の字は、台紙の余白の分だけ内側から始まってよい。そろえるのは台紙の縁と本文の端である。

ページ本体は横スクロールさせない。横に長くなりうるもの — 事実リストの表とコードブロック — は
`overflow-x: auto` の容器に入れ、容器の中だけがスクロールするようにする。図は容器に入れず、
`viewBox` を持つ SVG は比率を保って縮むので、横スクロールさせる必要がない。パネルの SVG は
`figure.panel svg` の `max-width: min(22rem, 100%)` で表示幅の上限を持つ。根要素の字が 16px のとき
22rem は 352px である。これは上限であって固定幅ではない。幅属性を `viewBox` 幅と同じにした絵は
原寸で出る。`viewBox` 幅が上限より小さい絵も拡大せず原寸で出る。本文幅が 22rem より狭い画面では
`100%` が上限になり、横スクロールは出ない。

```css
/* overflow-x だけを指定すると overflow-y は visible のままでいられず auto に計算されるため、
   縦は明示的に閉じる（意図しない縦スクロールバーを出さない） */
.scroll-x { overflow-x: auto; overflow-y: hidden; }
.scroll-x table { width: 100%; }
/* 3 列以上の表が狭い画面で潰れて縦に伸びないよう、最小の幅を持たせ、はみ出た分は容器の中で横に送る。
   2 列の表には付けない。付けると狭い画面で右の列が横スクロールの中に隠れる。2 列なら折り返して読める */
.scroll-x table:has(tr > :nth-child(3)) { min-width: 32rem; }
pre { overflow-x: auto; }
img, svg { max-width: 100%; height: auto; }
figure.panel svg { max-width: min(22rem, 100%); }
/* ページの幅は 1 本。図も帯も表もこの列の中に置き、張り出させない */
body { max-width: 40em; margin: 0 auto; padding: 2rem 1rem; }
figure { margin: 2.5rem 0; }
figure > svg { display: block; margin-inline: auto; }
figcaption { margin-top: 1em; color: var(--muted); font-size: .9em; }
```

幅を確かめるときは、描画したページで本文の列の各要素（帯・見出し・段落・図・表）の左端と右端を測り、
すべて同じ値になっていることを見る。目で見るだけだと、数 px の出入りを見落とす。

`overflow-x: auto` の容器はマウス以外でも操作できるようにする。`tabindex="0"` と `role="region"` と
アクセシブル名（`aria-label`）を付けないと、キーボードだけの読者は容器の中身を最後まで読めない。
対象は事実リストの `.scroll-x` と、横に長いコードブロックの `<pre>` の 2 つ。ただし付ける属性は
違う。

```html
<div class="scroll-x" tabindex="0" role="region" aria-label="事実リスト">…</div>
<pre tabindex="0">…</pre>
```

`<pre>` には `tabindex="0"` だけを付け、`role="region"` は付けない。ページに横長のコードが 2 つ以上
あると同じ名前のランドマークが並び、支援技術の一覧で見分けが付かなくなる。事実リストの表はページに
1 つだけなので、そちらは `role="region"` と名前を持たせる。

幅は相対単位で指定する。固定 px の幅を本文や表に与えない。

## 保存と公開

既定は**ローカル保存だけ**行う。「Artifact で」の指定があったときだけ、保存に加えて公開する。

### 保存

- 書き出し先はカレントディレクトリ直下の `explain-<slug>.html`。`<slug>` はトピックを kebab-case に
  したもの（`DNS` → `dns`、「電気回路」→ `denki-kairo`）
- ユーザーがパスを指定していればそちらに従う（`SKILL.md` の引数表）
- **同名のファイルがあれば上書きしない**。`explain-<slug>-2.html`、`explain-<slug>-3.html` と連番を
  付け、納品報告でそのファイル名を伝える。ユーザー指定パスにも同じ規則を当て、拡張子の直前に連番を
  入れる（`~/notes/dns.html` が既にあれば `~/notes/dns-2.html`）
- **例外**：「Artifact で」の指定があり、かつ同名のファイルが既にあるときは**再公開の候補とみなす**
  （実行のたびにセッションが変わり前回公開の記憶は残らないので、手元にある手がかりはこれだけである）。
  保存は通常どおり連番を付ける。更新先の Artifact を決めるのは `url` であってファイルパスではないため、
  連番のパスでも `url` を渡せば同じページが更新される見込みが高い（但し書きは下記「公開」）
- **候補どまりのことがある**：同名ファイルがあっても、前回はローカル保存だけで公開していない場合が
  ある（既定が保存のみなので普通に起きる）。公開段で `url` が見つからなければ再公開ではないので、
  通常の新規公開として扱う

### 公開

「Artifact で」の指定があるときだけ、保存したファイルをそのまま Artifact ツールに渡す。

| 項目 | 値 |
|------|-----|
| 渡すもの | 保存した `explain-<slug>.html` のパス |
| `url` | **既存の Artifact を更新するときだけ**渡す。前回の URL を持っていないなら Artifact ツールの一覧機能（`action: "list"`）で探すか、ユーザーに URL を尋ねる。渡さずに公開すると、同じパスを渡しても別の Artifact が新しく作られる |
| `<title>` | トピックの問い（例「DNS ってなに？」）。`<meta charset="utf-8">` の直後に置く。ツールの引数ではなく HTML 内のタグで持つ |
| `favicon` | 📖 に固定する。再公開でも変えない |
| `description` | 何を説明したページかを 1 文で。「DNS が名前を IP アドレスに変える道筋を、絵 5 枚と裏取り済みの事実 5 件で説明する」の形 |

公開したら URL を納品報告に添える。Artifact ツールが無い・公開に失敗したときはローカル保存だけで
納品し、報告に理由を 1 行添える（`SKILL.md` のエラー時の表）。

再公開（同じトピックを直したとき）は **`url` に前回の Artifact の URL** を渡す。同じセッションの中なら
同じパスを渡すだけで同じ URL へ deploy されるが、`/explain` を後日また実行したときは別のセッションに
なるため、`url` を渡さないと別のページが新しく作られて前の URL が取り残される。更新先を決めるのは
`url`、中身の出所が `file_path` と役割が分かれているので、連番で保存したファイルを渡しても前の URL が
更新される見込みが高い（ツールの説明は `url` と異なるパスを同時に渡したときの優先関係までは書いて
いないので、別ページが作られたらその旨を報告に添える）。

別ページが作られたかどうかは、**公開して返ってきた URL を渡した `url` と突き合わせて**確かめる。
一致しなければ新しいページができているので、その URL と前の URL の両方を報告に添える（照合しないと、
前の URL が取り残されたことに読者も気づけない）。

URL が分からないときは Artifact ツールの一覧機能で探し、それでも見つからなければユーザーに尋ねる。
一覧にもユーザーにも無ければ、そのトピックはまだ公開されていない。**再公開ではないので `url` を
付けずに新規公開する**（保存の例外は「候補」の判定にすぎず、ここで確定する）。

## エラー時

| 状況 | 挙動 |
|------|------|
| Google Fonts が読み込めない | 代替フォントで表示される。生成時に、各 `font-family` の最後が `sans-serif` / `monospace` などの総称ファミリで終わっているかを見る（終わっていなければ書き足す） |
| Artifact ツールが無い／公開に失敗 | ローカル保存だけで納品し、報告に理由を 1 行添える |
| 保存先に同名ファイルがある | 上書きせず連番を付け、報告でファイル名を伝える |
| 前回の Artifact の URL が分からない | 一覧機能で探し、見つからなければユーザーに尋ねる。**両方とも空振りしたら未公開のトピックなので、`url` 無しで新規公開する**。公開済みかもしれないと思いながら当てずっぽうで `url` 無しの公開をしない、という規則であって、新規公開を止める規則ではない |
| パネルが 7 枚を超える | 連鎖を保ったまま統合して 7 枚以下にする。統合できない環は下の階に残し上の階から外す |
| 落とした限定条件もレベルの明示も無い | 「単純化」欄ごと出力しない。空の見出しを残さない |
| 図のラベルが箱からはみ出す、または矢印の札が箱に重なる | 箱を広げる、箱と箱の間を広げる、札を箱の無い段へ移す、平易語を短くする、のどれかで直す。文字を小さくして収めない |
| 着地にふさわしい行が無い | 着地の要素ごと出さない。空の見出しを残さない |
| 着地を 2 つ以上作りたくなった | 1 つに絞る。絞れないものはパネル側に戻す |
| 着地の主張が最後のパネルの言い直し | 着地ではないので省く |
