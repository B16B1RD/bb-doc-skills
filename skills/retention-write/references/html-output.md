# HTML 出力の共有 reference

文書系スキルが「HTML で」と頼まれて納品するときに使う。骨格、図の決め方、再生できるフロー図、アクセシビリティ、スクリーンショット確認、目視チェックリストを 1 か所で引けるようにして、スキルごとに書き方がずれないようにする。

各スキルは `<このスキルのディレクトリ>/../retention-write/references/html-output.md` で読む。
このディレクトリは呼出し元が解決したスキルの実体を指す。兄弟の参照も、呼出し元から受け取った
実体のパスを使う。規範は同じルートの全文 1 部を使い、参照内で置換変数を再解決しない。
成果物は利用者の作業領域へ保存し、参照元やプラグインキャッシュへ保存しない。

本 reference が決めるのは HTML にするときの共通部分だけである。文書の中身（結論の置き方、見出しの順、文体）は各スキルの規定のままで、HTML にしても変えない。

## 骨格

`<body>` の中身だけを書く形、`<title>` の置き場所、`<meta charset>` と Google Fonts の扱い、色と字のトークン、テーマの切り替え、外部依存の禁止、幅と横スクロールの扱いは、`<このスキルのディレクトリ>/../explain/references/page-skeleton.md` の「ファイルの形」「色と字」（「テーマの切り替え」を含む）「外部依存」「レイアウト」に従う。ここでは写さない。二重に持つと、片方だけが更新されて食い違う。

書体とアクセント色は、page-skeleton.md の「色と字」の表から、作ったスキルの行（retention-write か tech-write）を選んで使う。ほかのスキルの行の値を借りない。組版の既定（本文の 40em・見出しだけの詰め組・表のセルの改行）も同じ節の雛形のまま使う。

page-skeleton.md が上の階・下の階として決める本文の構成（パネル・着地・事実リスト）は explain 専用である。文書系スキルは、自分の文書の構成を `<h1>`・`<h2>`・段落・表・リストへそのまま写す。雛形の CSS のうち explain 専用の規則（`.panel`・`.note`・`.pin`・`.facts`・`.stairs`・`.quiz`・`.level-note`）は落とす。`--mark` も事実リストの目印なので、文書系スキルでは使わなくてよい。

ページに表が 2 つ以上あるときは、`.scroll-x` の `aria-label` を表ごとに違う名前にする（例：「ブランチの表」「補助ブランチの表」）。同じ名前のランドマークが並ぶと、支援技術の一覧で見分けが付かない。

page-skeleton.md の読取に失敗した場合、次の最小骨格で縮退出力できるが、参照確認は失敗として報告する。

```html
<meta charset="utf-8">
<title>{文書のタイトル}</title>
<style>/* :root にトークンを定義し、body の背景を明示する */</style>
<main lang="ja">
  <h1>{文書のタイトル}</h1>
</main>
```

- 自前の CSS と JS はインラインに書く。外部スクリプトと外部画像は使わない
- 色は `:root` のトークン経由で引き、生の色値を要素に直書きしない
- ページ本体は横スクロールさせない。横に長い表とコードは `overflow-x: auto` の容器に入れ、容器の中だけがスクロールする形にする。SVG は `max-width: 100%` で縮める

## 出典の上付き番号

HTML では、本文の出典を上付きの番号にする。本文の中に「（出典 3）」が並ぶと、括弧とリンクの色が文の
あちこちに散って本文が読みにくくなる。形は次に固定する。`n` は出典一覧の番号で、`href` の `src-n`・
`aria-label` の「出典 n」・リンクの文字の 3 か所で同じ値にする。

```html
<p>本文の文<sup class="cite"><a href="#src-n" aria-label="出典 n">n</a></sup>。</p>
<ol class="sources">
  <li id="src-n">{出典の書誌と URL}</li>
</ol>
<style>
  sup.cite { font-size: .7em; line-height: 0; margin-left: .1em; }
  sup.cite a { color: var(--accent); text-decoration: none; }
  .sources li { scroll-margin-top: 5rem; overflow-wrap: anywhere; }  /* 長い URL を狭い幅で折る */
</style>
```

- 1 つの文が 2 つ以上の出典に拠るときは、1 つの `<sup>` の中に番号ごとのリンクを半角のカンマで区切って並べる（`<sup class="cite"><a href="#src-1" aria-label="出典 1">1</a>,<a href="#src-2" aria-label="出典 2">2</a></sup>`）。`<sup>` を 2 つ続けると、番号が「12」と 1 つの数に読める
- 句点の前の上付き番号が、行頭に 1 つだけ送られることがある。番号の直前の 1 字と `<sup>` を `<span class="nobr">` で包む（`…の状態<span class="nobr">す<sup class="cite">…</sup></span>。`）。改行しない文字（U+2060 など）を挟んで防がない。コピーした文が元の字と別の文字になる
- 出典一覧はページの本文の一部である。出典の URL と確認日を本文に残す決まりのある文書（tech-write の技術トピックの解説など）は、出典一覧の項目に URL と確認日を書けば、その決まりを満たす
- 出典一覧の各項目に `id="src-n"` を付け、番号は本文に現れる順に 1 から振る。同じ出典を 2 度目に引くときは、最初の番号をそのまま使う
- `aria-label` を省かない。上付きの数字だけでは、読み上げで出典への参照だと分からない
- Markdown の原稿は「（出典 n）」のまま変えない。上付き番号にするのは HTML へ写すときだけで、原稿の書き方や scan.py のセルフチェックの対象は変わらない。原稿を上付きの形に書き換えると、原稿と HTML のどちらが元かが分からなくなる

## 図の置き場所と強弱

文字だけが続くページでは、読者は文字の量の多さに読み始める気を失う。図は、文を読み比べなくても構造が見える箇所に置き、大きさで強弱を付けて、読者の目がどこから入ればよいかを示す。結論は文で書き、図は文を補う。図にしか書かれていない結論を作らない。

### 図を置く箇所

節ごとに、文が次のどれかを説明しているかを見る。説明していれば、その節に図を置く。

| 文が説明していること | 図の例 |
|------|---------|
| 構造・分類（いくつかの型や部品と、その関係） | 中心と周りの型を並べた地図、入れ子の円 |
| 流れ・手順・因果 | 矢印でつないだ箱、再生できるフロー図 |
| 段階・水準の上がり方 | 階段、目盛りの上の点 |
| 比較・対比（前と後、悪い例と良い例） | 左右に並べた 2 つの箱と、間の矢印 |
| 前提と、その上に乗るもの | 土台の上に載る箱 |
| 時間の経過・期間 | 時間の軸と、その上の出来事 |

どれも説明していない節（単独の事実、数値 1 つ、引用、注意書きだけの節）には、無理に図を置かない。隣り合う 2 つの節が同じ構造を説明しているときは、詳しく説明している方の節に 1 枚だけ置く。同じ構造の図を 2 枚描かない。図の枚数に上限は設けない。上の表に当たる箇所がある限り、何枚あってもよい。逆に、当たる箇所がない文書に図を足して枚数を増やさない。

図に書くのは、本文に書いてある事実と語だけにする。図のために事実を足さない。キャプションには、図が何を見せるかと、図の読み方（矢印の向き、色が何を表すか）を書いてよい。特定の論文・記事を紹介する文書（tech-write の原典の紹介）で、原典に無い図を描いたときは、キャプションに「図は原典にはありません」と書く。技術トピックの解説のように複数の資料から書く文書では、この一文は要らない。原典の図表は転載しない。

### 主役図と補助図

大きさと台紙で、図に強弱を付ける。全部の図を同じ大きさで並べると、どれが要かが分からない。

| | 主役図 | 補助図 |
|---|---|---|
| 担うもの | 文書全体、またはその節の要（読者に持ち帰らせたいこと）を描いた図 | 1〜2 段落の中身を補う図 |
| 枚数 | 文書の結論に 1 枚。加えて、`<h2>` か `<h3>` の節ごとに 1 枚まで | 制限しない |
| 置き方 | `<figure class="main">`。本文の列いっぱいの台紙（`--panel`）に載せる。SVG の `viewBox` の幅は 640 まで | `<figure class="aside">`。台紙なしで、列の中央に小さく置く。SVG の `viewBox` の幅は 320 |
| 置く位置 | 説明する文の直後か直前 | 補う段落の直後 |

```html
<figure class="main">
  <svg viewBox="0 0 640 300" width="640" role="img" aria-label="{図の要旨}">…</svg>
  <figcaption>図 1：{何を見せる図か}</figcaption>
</figure>
<figure class="aside">
  <svg viewBox="0 0 320 240" width="320" role="img" aria-label="{図の要旨}">…</svg>
  <figcaption>図 2：{何を見せる図か}</figcaption>
</figure>
<style>
  figure.main { background: var(--panel); border-radius: 6px; padding: 1.6rem 1.5rem 1.2rem; }
  figure.main > svg { max-width: min(40rem, 100%); }
  figure.aside > svg { max-width: min(19rem, 100%); }
  figure.aside > figcaption { text-align: center; font-size: .85em; }
  /* 狭い画面で広い主役図が縮みすぎて字が読めなくならないよう、台紙の中だけ横にスクロールさせる */
  @media (max-width: 600px) {
    figure.main { overflow-x: auto; }
    figure.main > svg { min-width: 32rem; }
    figure.main > figcaption { position: sticky; left: 0; max-width: calc(100vw - 4.4rem); }
  }
</style>
```

主役図も補助図も、本文の列の中に置く。本文の外へ張り出させず、本文の横にも並べない（page-skeleton.md の「レイアウト」）。

補助図は、置く前に担う役を「この図は〇〇を見せる」と一文で言えることを確かめる。言えない図は、何のためにあるかが決まっていないので置かない。主役図と同じことを言い直す補助図も置かない。判定は目視のセルフチェックで行う。`scan.py` では判定できない。

### 色の当て方

文書の中で繰り返し出てくる対象（型・段階・立場・比べる候補など）があるときは、page-skeleton.md の「色と字」の区別の色を対象ごとに 1 色ずつ決める。決めた色は、図の箱・その対象を扱う節の見出しの帯・表・本文の札（`.tag`）のすべてで同じものを使う。

```html
<section class="is-c1">
  <h2 id="h2-2">Altitude：作業ではなく成果を任せる</h2>
  …
</section>
<p><span class="tag is-c1">Altitude</span> は…</p>
<style>
  section { display: contents; }
</style>
```

- 対象ごとの節を `<section class="is-cN">` で包むと、中の `<h2>` の帯・表の見出し行・箇条の記号がその色になる。`section { display: contents; }` で、包んでも幅とレイアウトは変わらない
- 図の中では、対象の箱の面を `var(--cN-soft)`、輪郭と主ラベルを `var(--cN)` にする
- 対象ごとの節が無い文書（対象を 1 つの表や 1 枚の図で並べるだけの文書）では、図の箱と札（`.tag`）にだけ色を当て、見出しの帯には当てない。節を色で包まない
- 色だけで区別しない。札や図のラベルには、対象の名前を必ず字で書く

### 冒頭の帯

タイトル（`<h1>`）・要約の段落・出典や日付の行を、`<header class="hero">` にまとめて淡い台紙に載せる。どこからが本文かが一目で分かり、読者は帯の中だけで文書の要点をつかめる。

```html
<header class="hero">
  <h1>{文書のタイトル}</h1>
  <p class="lead">{要約の段落}</p>
  <p class="source">{出典・日付の行}</p>
</header>
<style>
  .hero { background: var(--panel); border-top: .3rem solid var(--accent); border-radius: 0 0 6px 6px; padding: 2.2rem 1.5rem 1.6rem; margin-bottom: 2.5rem; }
  .hero .lead { font-size: 1.15em; }
  .hero .source { color: var(--muted); font-size: .9em; margin: 0; }
</style>
```

帯の上に分類語の小ラベルを置かない。帯に入れるのは、Markdown 原稿の冒頭にある文だけにする。原稿の冒頭の段落が、要約の文と出典・日付の文を 1 段落に含むときは、出典・日付の文を `.source` に分けてよい。文言は変えない。

図は inline SVG で描く。`viewBox`・`role="img"`・`aria-label`・色の引き方は、page-skeleton.md の「inline SVG の規則」に従う。

## 再生できるフロー図

流れを説明する図（手順・処理の順序・時間の経過）は、ステップ送りか再生ボタンで 1 ステップずつ見られる形にする。静止した 1 枚だと、読者は矢印をたどって順序を自分で組み立てることになる。

作り方は次の 3 点である。

- 図のステップ（SVG の `<g>`）と、同じステップの説明文（`<li>`）に、同じ番号の `data-step` を付ける
- 操作ボタン（前へ・次へ・再生）は JS が `<figcaption>` の前に挿入する。JS が動かない環境に、押せないボタンを出さない
- 既定は全ステップを表示した状態にする。JS が動いたときだけ、ステップ送りの状態に切り替わる

```html
<figure class="flow" data-flow>
  <svg viewBox="0 0 320 180" width="320" role="img" aria-label="{図の要旨}">
    <g data-step="1"><!-- 1 つめの図形 --></g>
    <g data-step="2"><!-- 2 つめの図形 --></g>
  </svg>
  <figcaption>
    <ol>
      <li data-step="1">{1 つめの説明}</li>
      <li data-step="2">{2 つめの説明}</li>
    </ol>
  </figcaption>
</figure>
<style>
  .flow.is-stepped g[data-step] { opacity: .35; }
  .flow.is-stepped g[data-step].is-on { opacity: 1; }
  .flow.is-stepped li[data-step]:not(.is-on) { color: var(--muted); }
  .flow-bar { display: flex; gap: .5rem; align-items: center; }
  @media (prefers-reduced-motion: no-preference) {
    .flow.is-stepped g[data-step] { transition: opacity .3s; }
  }
</style>
<script>
document.querySelectorAll('[data-flow]').forEach(function (fig) {
  var steps = Array.prototype.slice.call(fig.querySelectorAll('[data-step]'));
  var last = Math.max.apply(null, steps.map(function (s) { return Number(s.dataset.step); }));
  var now = last, timer = null;
  var bar = document.createElement('div');
  bar.className = 'flow-bar';
  var status = document.createElement('span');
  status.setAttribute('aria-live', 'polite');
  function button(text, onClick) {
    var b = document.createElement('button');
    b.type = 'button';
    b.textContent = text;
    b.addEventListener('click', onClick);
    bar.appendChild(b);
    return b;
  }
  function show(n) {
    now = Math.min(Math.max(n, 1), last);
    steps.forEach(function (s) { s.classList.toggle('is-on', Number(s.dataset.step) <= now); });
    status.textContent = 'ステップ ' + now + ' / ' + last;
  }
  function stop() { clearInterval(timer); timer = null; play.textContent = '再生'; }
  button('前へ', function () { stop(); show(now - 1); });
  button('次へ', function () { stop(); show(now + 1); });
  var play = button('再生', function () {
    if (timer) { stop(); return; }
    show(1);
    play.textContent = '一時停止';
    timer = setInterval(function () { if (now >= last) { stop(); } else { show(now + 1); } }, 1500);
  });
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { play.hidden = true; }
  bar.appendChild(status);
  fig.insertBefore(bar, fig.querySelector('figcaption'));
  fig.classList.add('is-stepped');
  show(last);
});
</script>
```

再生できるフロー図も、主役図か補助図のどちらかとして置く（`<figure class="main flow" data-flow>` か `<figure class="aside flow" data-flow>`）。`<figcaption>` の `<ol>` には、本文にあった手順の箇条をそのまま移す。本文に同じ箇条を残して二重に持たない。図の番号と見出し（「図 3：…」）は、`<ol>` の前の `<p>` に書く。補助図のキャプションの淡い色と小さい字を手順の箇条に掛けないよう、次の CSS を足す。

```css
.flow > figcaption { text-align: left; font-size: 1em; color: var(--fg); }
.flow.is-stepped li[data-step]:not(.is-on) { color: var(--muted); }
```

文書の中で流れを主に説明する図（手順の節の主役図など）は、この再生できる形にする。分岐や例外を 1 か所だけ見せる図は、静止した図のままでよい。

上の例は読みやすさのために図と並べて書いている。実際のページでは、CSS は文書の先頭にある `<style>` へ統合し、`<script>` は対象の `<figure>` より後ろに置く。`<script>` を図より前に置くと、読み込み時に図が見つからず、操作ボタンが出ない。

page-skeleton.md はページの JS を「テーマの切り替え」のボタンだけとしており、この再生の仕掛けは例外である。外部スクリプトは読まず、上のようにインラインで書く。

## アクセシビリティ

- アニメーションと自動再生は `prefers-reduced-motion` で止める。`@media (prefers-reduced-motion: no-preference)` の中でだけ動きを有効にし、`reduce` の読者には遷移も自動再生も出さない（上の例はこの形）。ステップ送りのボタンは動きを伴わないので残す
- JS なしでも本文が読めることを要件にする。本文と図を JS で組み立てない。JS が担うのは操作ボタンの追加とステップの強調だけで、止まっても全ステップが読める状態が既定になる
- 図には `role="img"` と、その図の要旨を書いた `aria-label` を付ける
- 色だけで区別しない。凡例や線種、ラベルの文言でも区別できるようにする
- 操作はボタン要素で作り、キーボードで押せるようにする

## スクリーンショット確認

HTML を納品する前に、実際に描画した画面を見る。ソースを読むだけでは、はみ出したラベルや交差した線に気づけない。

### 道具の順序

次の順に試し、最初に使えた道具で確認する。

| 順 | 道具 | 使い方 |
|----|------|--------|
| 1 | claude-in-chrome | 保存した HTML を開き、ウィンドウ幅を変えて撮る |
| 2 | chrome-devtools | ページを開き、`emulate` の `viewport`（例：`390x844x1`）で幅を変え、`take_screenshot` で撮る。`resize_page` はウィンドウの大きさを変えるだけで、500px 前後より狭くできない |
| 3 | Playwright | 環境にあるときだけ使う。`playwright screenshot` に `--viewport-size` と `--full-page` を付けて撮る。依存としてインストールしない |
| 4 | ヘッドレスの Chrome | `google-chrome` か `chromium` が環境にあるときだけ使う。`--headless=new --window-size=1280,6000 --screenshot=<出力先> file://<HTML のパス>` で撮る。ダークは `--force-dark-mode --blink-settings=preferredColorScheme=0` を足す。幅を測るときは、測る `<script>` を足した写しを `--dump-dom` で開き、結果を読む |

道具が無い・接続できない・保存ファイルを開けないときは、使えないものとして次の道具へ移る。

### 手順

1. 保存した HTML を、広い幅（1280px 前後）と狭い幅（390px 前後）の 2 つで全面撮る。ダーク用の色定義（`prefers-color-scheme: dark` など）を持つ文書は、ライトとダークの両方を撮る。ダークは chrome-devtools の `emulate` の `colorScheme: dark` で配色を切り替えて撮る。切り替えられないときは、ダーク側のトークンの定義をソースで確認し、納品報告に「ダーク未確認」と書く。テーマの切り替えのボタンは、OS をダークにした状態で「ライト」を押した画面も撮り、表の字が本文と同じ濃さで出ることを見る。閲覧環境のテーマとの組み合わせも、根要素に `data-theme="light"` を付けて確かめる（chrome-devtools の `evaluate_script` などで付ける。claude.ai の Artifact で閲覧者がライトを選んだ状態と同じ印である）。OS がダークでも白地になり、「自動」を押しても白地のままで、「ダーク」を押すと暗くなることを見る再生できるフロー図は、既定の表示（最終ステップ）に加えて、「前へ」で最初のステップに戻した状態も撮る。ソースで代えるときは、最初のステップの図形と説明文だけが強調される CSS になっているかを読む
2. 撮った画像を、次節の目視チェックリストと突き合わせる。幅のそろいは目で見るだけにせず、描画したページで本文の列の各要素の左端と右端を測る（page-skeleton.md の「レイアウト」）
3. 崩れを見つけたら直して撮り直す。直せなかった崩れは、納品報告に 1 件ずつ並べる

### 全滅したとき

4 つとも使えないときは、HTML のソースを目視チェックリストの各項目と照らして確認する。そのうえで、納品報告に「スクショ未確認」と書く。確認した気にならないために、未確認であることを報告に残す。

## 目視チェックリスト

スクリーンショットを見るとき、道具が全滅してソースで代えるときの両方で使う。

- [ ] はみ出したラベルがない（箱や図の外へ出た文字、途中で切れた文字）
- [ ] 矢印に付けた札が、どの箱にも重なっていない
- [ ] 日付・版番号が、見出しでも本文でもハイフンや点の後ろで割れていない（広い幅と狭い幅の両方で見る）
- [ ] 交差した線がない（矢印や接続線が、関係のない図形や他の線をまたいでいない）
- [ ] 狭い幅（390px 前後）で、ページ本体が横スクロールしない（表とコードは容器の中だけがスクロールする）。2 列の表は横スクロールせず、セルの中で折り返す
- [ ] 冒頭の帯・図・表・見出し・段落の左端と右端が、上から下まで同じ線にそろっている（本文の外へ張り出す要素も、本文の横に並ぶ要素もない）
- [ ] 構造・流れ・段階・比較・前提・時間の経過を文で説明している節に、図がある。図の無いそうした節があれば、置かない理由を言える
- [ ] 図に、本文に無い事実を足していない。原典に無い図には、キャプションでそう書いてある
- [ ] 主役図がひと目で見つかり、補助図が主役図より目立っていない
- [ ] 補助図は 1 枚ごとに、担う役を「この図は〇〇を見せる」と一文で言える
- [ ] 区別の色を使った文書は、同じ対象に図・見出しの帯・表・札のどこでも同じ色が当たっている。色は 3 色までで、橙・赤茶に寄っていない
- [ ] 残したい一文が、図に囲まれて埋もれていない
- [ ] ダーク用の色定義がある文書は、ダークテーマで線・文字・背景が溶け合っていない
- [ ] テーマの切り替えのボタンが右上にあり、「自動」「ライト」「ダーク」のどれを押しても、表の字が本文と同じ色と大きさで出る
- [ ] 根要素に `data-theme` を付けた状態で「自動」を押すと、その印のテーマで表示される（ボタンが `data-theme` を書き換えていない）
- [ ] 再生できるフロー図は、最初のステップと最後のステップのどちらでも読める
- [ ] AI 生成の目印が無い。次のどれも出ていないことを確かめる
  - 見出しの上の小ラベル（見出しの前に置いた、大文字や色付きの小さな分類語）
  - セクションごとのフェードイン（スクロールに合わせて節が浮き出る動き）
  - 中点で区切ったメタ情報（「5 分で読める・2026 年・初級」のような 1 行）
  - 順序のない内容に付けた番号（手順でも順位でもない項目の「01」「02」）
  - 全ブロックに付けた角丸と影（どの段落や節もカードのように浮かせた形）
  - 絵文字の見出し（見出しの先頭や末尾の絵文字）
  - クリームとテラコッタの配色（クリーム色の地にテラコッタ・橙のアクセント。page-skeleton.md の「色と字」の表の色だけを使う）
- [ ] 出典は上付きの番号で、本文の中に「（出典 n）」やリンクの色が散らばっていない

## スキルごとの個別規則

retention-write と tech-write の HTML には、上の共通部分に加えて次の規則を当てる。どちらも文書の中身や見出しの順は変えず、組み方だけを決める。

### retention-write：結論の一文

retention-write の HTML では、結論の一文（読者に持ち帰らせたい断定の一文）だけを本文より一段大きく組む。`<p class="conclusion">` に入れ、1 文書に 1 か所だけにする。ほかの段落・引用・要点の箇条を同じ大きさにしない。大きくする文が 2 か所以上あると、どれが結論かが分からなくなる。

```html
<p class="conclusion">{結論の断定一文}</p>
<style>
  .conclusion {
    font-family: var(--font-head); font-size: 1.25em; font-weight: 700; line-height: 1.6; margin: 1.5em 0;
    color: var(--accent); padding-left: 1rem; border-left: 2px solid currentColor;
  }
</style>
```

台紙・影で囲まない。大きさ・アクセントの色・左の細い線・前後の空きで目立たせる。

### tech-write：左に固定する目次

tech-write の HTML では、`<h2>` が 4 個以上あり、かつ画面幅が 1100px 以上のときだけ、目次を左に固定する。`<h2>` が 3 個以下の文書には目次を出さない（`<nav class="toc">` ごと書かない）。画面幅が 1100px 未満のときは目次を表示しない。本文の 40em の左に、目次を置ける余白が残るのは 1100px 以上の幅だけである。

```html
<nav class="toc" aria-label="目次">
  <ol>
    <li><a href="#h2-1">{1 つめの h2 の文}</a></li>
  </ol>
</nav>
<style>
  .toc { display: none; }
  @media (min-width: 1100px) {
    .toc {
      display: block;
      position: fixed;
      top: 2rem;
      left: 1.5rem;
      width: calc((100vw - 42.5rem) / 2 - 3rem);
      max-height: calc(100vh - 4rem);
      overflow-y: auto;
      font-size: .875rem;
      line-height: 1.6;
    }
    .toc ol { list-style: none; margin: 0; padding: 0; border-left: 1px solid var(--rule); }
    .toc a {
      display: block; padding: .3em 0 .3em .8em; margin-left: -2px;
      color: var(--muted); text-decoration: none; border-left: 3px solid var(--sec, transparent);
    }
    .toc a:hover { color: var(--fg); }
  }
</style>
```

- 目次の項目は `<h2>` だけにする。`<h3>` は載せない
- 各 `<h2>` に `id` を付け、目次のリンク先にする。目次の文は `<h2>` の文と同じにする
- 区別の色を決めた節の項目は、リンクに節と同じ `class="is-cN"` を付ける。項目の左の線がその色になり、目次でも対象を見分けられる
- 目次は JS を使わずに作る。現在位置の強調やスクロールに合わせた動きは付けない

## 納品報告に書くこと

HTML を納品するときは、確認の結果を報告に添える。

- どの道具で、どの幅を確認したか。道具が全滅したときは「スクショ未確認」、ダークを確認できなかったときは「ダーク未確認」
- 直せなかった崩れの一覧（なければ書かない）

## エラー時

| 状況 | 挙動 |
|------|------|
| スクショ道具がどれも使えない | 目視チェックリストでソースを確認し、納品報告に「スクショ未確認」と書く |
| スクショで崩れを見つけた | 直して撮り直す。直せなかった崩れは納品報告に並べる |
| page-skeleton.md を読めない | 参照確認の失敗を報告する。縮退出力する場合は上の最小骨格で代える |
| 補助図の役を一文で言えない、または本文に無い事実が図に入っている | 役を一文で言える形に描き直す。描き直せないなら削る。本文に無い事実は図から外す |
| 構造・流れ・段階・比較などを説明する節に図が無い | 図にする。図にしない理由を一文で言えるときだけ、図を置かずに残す |
| 流れの図が JS なしで読めない | 既定を全ステップ表示に戻し、ボタンの挿入を JS 側へ移す |
