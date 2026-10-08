# HTML 出力の共有 reference

文書系スキルが「HTML で」と頼まれて納品するときに使う。骨格、図の決め方、再生できるフロー図、アクセシビリティ、スクリーンショット確認、目視チェックリストを 1 か所で引けるようにして、スキルごとに書き方がずれないようにする。

各スキルは `<このスキルのディレクトリ>/../retention-write/references/html-output.md` で読む。
このディレクトリは呼出し元が解決したスキルの実体を指す。兄弟の参照も、呼出し元から受け取った
実体のパスを使う。規範は同じルートの全文 1 部を使い、参照内で置換変数を再解決しない。
成果物は利用者の作業領域へ保存し、参照元やプラグインキャッシュへ保存しない。

本 reference が決めるのは HTML にするときの共通部分だけである。文書の中身（結論の置き方、見出しの順、文体）は各スキルの規定のままで、HTML にしても変えない。

## 骨格

`<body>` の中身だけを書く形、`<title>` の置き場所、`<meta charset>` と Google Fonts の扱い、色と字のトークン、外部依存の禁止、横スクロールの扱いは、`<このスキルのディレクトリ>/../explain/references/page-skeleton.md` の「ファイルの形」「色と字」「外部依存」「レイアウト」に従う。ここでは写さない。二重に持つと、片方だけが更新されて食い違う。

page-skeleton.md が上の階・下の階として決める本文の構成（パネル・着地・事実リスト）は explain 専用である。文書系スキルは、自分の文書の構成を `<h1>`・`<h2>`・段落・表・リストへそのまま写す。

page-skeleton.md の読取に失敗した場合、次の最小骨格で縮退出力できるが、参照確認は失敗として報告する。

```html
<meta charset="utf-8">
<title>{文書のタイトル}</title>
<style>/* :root にトークンを定義し、body の背景を明示する */</style>
<h1>{文書のタイトル}</h1>
```

- 自前の CSS と JS はインラインに書く。外部スクリプトと外部画像は使わない
- 色は `:root` のトークン経由で引き、生の色値を要素に直書きしない
- ページ本体は横スクロールさせない。横に長い表とコードは `overflow-x: auto` の容器に入れ、容器の中だけがスクロールする形にする。SVG は `max-width: 100%` で縮める

## 主役図と補助図

図は、文書の結論を支えるために置く。結論は文で書き、図は文を補う。図にしか書かれていない結論を作らない。

### 主役図

主役図は 1 枚である。文書が読者に持ち帰らせたい一文（結論の断定一文）を、構造・関係・流れのどれかで絵にしたものを選ぶ。置く位置は、その一文の直後か直前の近くにする。

### 補助図

補助図は、枚数で制限しない。主題によって必要な枚数が大きく違うためである。要否は次の 3 基準で決める。

| 基準 | 確かめ方 |
|------|---------|
| 担う役を一文で言える | 「この図は〇〇を見せる」と書ける。書けない図は、何のためにあるか決まっていない |
| 主役図と張り合わない | 大きさ・色の強さ・置く位置が主役図より控えめで、主役図と同じ主張を言い直していない |
| 消して失うものがなければ削る | その図を外して本文を読み直し、読者が分からなくなることがなければ削る |

3 基準を満たす補助図は何枚あってもよく、満たさない図は 1 枚でも削る。枚数を数えて判断しない。判定は目視のセルフチェックで行う。`scan.py` では判定できない。

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

上の例は読みやすさのために図と並べて書いている。実際のページでは、CSS は文書の先頭にある `<style>` へ統合し、`<script>` は対象の `<figure>` より後ろに置く。`<script>` を図より前に置くと、読み込み時に図が見つからず、操作ボタンが出ない。

page-skeleton.md はページの JS を「ほぼ不要」としており、この再生の仕掛けだけが例外である。外部スクリプトは読まず、上のようにインラインで書く。

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
| 2 | chrome-devtools | ページを開き、`resize_page` で幅を変え、`take_screenshot` で撮る |
| 3 | Playwright | 環境にあるときだけ使う。`playwright screenshot` に `--viewport-size` と `--full-page` を付けて撮る。依存としてインストールしない |

道具が無い・接続できない・保存ファイルを開けないときは、使えないものとして次の道具へ移る。

### 手順

1. 保存した HTML を、広い幅（1280px 前後）と狭い幅（390px 前後）の 2 つで全面撮る。ダーク用の色定義（`prefers-color-scheme: dark` など）を持つ文書は、ライトとダークの両方を撮る。ダークは chrome-devtools の `emulate` の `colorScheme: dark` で配色を切り替えて撮る。切り替えられないときは、ダーク側のトークンの定義をソースで確認し、納品報告に「ダーク未確認」と書く。再生できるフロー図は、既定の表示（最終ステップ）に加えて、「前へ」で最初のステップに戻した状態も撮る。ソースで代えるときは、最初のステップの図形と説明文だけが強調される CSS になっているかを読む
2. 撮った画像を、次節の目視チェックリストと突き合わせる
3. 崩れを見つけたら直して撮り直す。直せなかった崩れは、納品報告に 1 件ずつ並べる

### 全滅したとき

3 つとも使えないときは、HTML のソースを目視チェックリストの各項目と照らして確認する。そのうえで、納品報告に「スクショ未確認」と書く。確認した気にならないために、未確認であることを報告に残す。

## 目視チェックリスト

スクリーンショットを見るとき、道具が全滅してソースで代えるときの両方で使う。

- [ ] はみ出したラベルがない（箱や図の外へ出た文字、途中で切れた文字）
- [ ] 交差した線がない（矢印や接続線が、関係のない図形や他の線をまたいでいない）
- [ ] 狭い幅（390px 前後）で、ページ本体が横スクロールしない（表とコードは容器の中だけがスクロールする）
- [ ] 主役図がひと目で見つかり、補助図が主役図より目立っていない
- [ ] 補助図は 1 枚ごとに、担う役を「この図は〇〇を見せる」と一文で言える
- [ ] 補助図を 1 枚ずつ外して本文を読み直しても分からなくなる箇所が出ない図は、削ってある
- [ ] 残したい一文が、図に囲まれて埋もれていない
- [ ] ダーク用の色定義がある文書は、ダークテーマで線・文字・背景が溶け合っていない
- [ ] 再生できるフロー図は、最初のステップと最後のステップのどちらでも読める

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
| 補助図が 3 基準のどれかを満たさない | 削る。満たす形に描き直せるなら描き直す |
| 流れの図が JS なしで読めない | 既定を全ステップ表示に戻し、ボタンの挿入を JS 側へ移す |
