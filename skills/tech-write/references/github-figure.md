# GitHub の本文に添付する図

PR 本文・Issue 本文・Issue/PR コメントで、文を読み比べないと構造が見えない箇所には、SVG の図を添付する。図は文を補うもので、結論は図の外の文で書く。図にしか書かれていない結論を作らない。

## 図を置くか

`<このスキルのディレクトリ>/../retention-write/references/html-output.md` の「図を置く箇所」の表で決める。文が構造・分類、流れ・手順・因果、段階、比較・対比（変更の前と後を含む）、前提、時間の経過を説明していれば、その箇所に図を置く。どれも説明していなければ置かない。表の写しはここに置かない。

- 変更の前と後で処理の流れや部品の関係が変わる PR、再現の手順に分岐がある不具合の Issue は、たいてい表に当たる
- 1〜2 文の返信・質問・進捗の報告のような短いコメントは、たいてい表に当たらない。当たらない文書に図を足さない
- 同じ構造を説明する箇所が 2 つあれば、詳しく説明している方に 1 枚だけ置く
- 図ごとに、担う役を「この図は〇〇を見せる」と 1 文で言えることを確かめる。言えない図は置かない
- 図に書くのは、本文に書いてある事実と語だけにする。図のために事実を足さない

## SVG の書き方

描き方は `<このスキルのディレクトリ>/../explain/references/page-skeleton.md` の「inline SVG の規則」に従う（ラベルの主従、矢印の向き、矩形と短いパス、線幅、角の丸め、字の幅の見積もり、札を箱に重ねない）。GitHub の添付は単体のファイルで、ページの CSS の変数を引けないので、次の点だけを変える。

- 根要素に `xmlns="http://www.w3.org/2000/svg"`、`viewBox`、`viewBox` と同じ `width` と `height` を付ける。幅は 760 までにする。広い図は本文の列に合わせて縮み、字も小さくなる
- 先頭に `<title>` を置き、図の要旨を書く
- Web フォント・外部の画像・`<script>`・外部への参照を入れない。`font-family` は末尾を `sans-serif` にする
- 図の全面に不透明な背景の矩形を敷く。透明な地のままにすると、GitHub のダークテーマで黒い字が地に沈む
- 色は SVG の中の `<style>` で、page-skeleton.md の「色と字」と同じ名前の変数として `svg` に定義し、クラスの規則から `var()` で引く。値は同じ節の tech-write の行と共通の無彩色を使う。ダークの値は同じ `<style>` の `@media (prefers-color-scheme: dark)` で上書きする。GitHub はテーマに合わせて画像の配色を切り替え、切り替わらない閲覧環境でも、明るい台紙の図として読める

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 240" width="640" height="240">
  <title>{図の要旨}</title>
  <style>
    svg { --bg: #ffffff; --fg: #222222; --muted: #5c5c5c; --line: #222222; --fill: #f2f2f2;
          --accent: #1a7f37; --hi: #dcf0e1; --c1: #1f5fbf; --c1-soft: #e2ecfa;
          --c2: #7c3aad; --c2-soft: #efe4f8; --c3: #be185d; --c3-soft: #fbe4ef; }
    @media (prefers-color-scheme: dark) {
      svg { --bg: #171717; --fg: #e6e6e6; --muted: #9e9e9e; --line: #e6e6e6; --fill: #262626;
            --accent: #3fb950; --hi: #1c3524; --c1: #79aef0; --c1-soft: #1b2c44;
            --c2: #c39be6; --c2-soft: #2e2240; --c3: #f07aae; --c3-soft: #3d1a2b; }
    }
    .bg { fill: var(--bg); }
    .box { fill: var(--fill); stroke: var(--line); stroke-width: 1.5; }
    .arrow { fill: none; stroke: var(--line); stroke-width: 1.5; }
    text { fill: var(--fg); font-family: "IBM Plex Sans JP", "Hiragino Sans", "Yu Gothic", sans-serif; font-size: 16px; }
    .sub { fill: var(--muted); font-size: 13px; }
  </style>
  <rect class="bg" width="640" height="240"/>
  …
</svg>
```

色をつけるときは、SVG の要素の属性に `var()` を書かず、上の例のようにクラスを付けて `<style>` の規則で塗る。

## 本文への置き方

図は、説明する文の直後か直前に、`![{図の要旨。本文にある事実だけで 1〜2 文}](./fig-1.svg)` の形の Markdown の画像で置く。パスは本文のファイルからの相対パスにする。

- 代替テキスト（`![` と `]` の間）には、図の要旨を本文にある語で書く。画像が読めない読者と、文脈を持たない読み手は、この文で図を受け取る
- 図の前後の文で、図が示す結論を書く。「下の図のとおり」だけで済ませない
- ファイル名は図の順の番号にする（`fig-1.svg`、`fig-2.svg`）

## 描画の確認

納品する前に、SVG を `<img>` で埋めた使い捨ての HTML を、ライトとダークのページで描画して見る。ソースを読むだけでは、はみ出したラベルや交差した線に気づけない。

```html
<!doctype html>
<html style="color-scheme: dark; background: #0d1117">
<body><img src="fig-1.svg"></body>
</html>
```

`color-scheme` を `light`（地は `#ffffff`）と `dark` の 2 通りにして撮る。撮る道具の順と使い方は、html-output.md の「スクリーンショット確認」の表に従う。確かめるのは、html-output.md の「目視チェックリスト」のうち図の項目（はみ出したラベル、箱に重なった札、交差した線、ダークで溶け合う線と字、本文に無い事実）である。道具が全滅したときは、SVG のソースをその項目と照らし、納品報告に「スクショ未確認」と書く。

## 納品と投稿

本文の Markdown と SVG を、利用者の作業領域の同じフォルダに保存する。投稿は、利用者が投稿を頼んだときだけ行う。頼まれていなければ、そのまま実行できるコマンドを納品報告に添える。

| 投稿する本文 | コマンド |
|---|---|
| PR 本文 | `gh pr create --body-file body.md --attach ./fig-1.svg`（更新は `gh pr edit <番号> --body-file body.md --attach ./fig-1.svg`） |
| Issue 本文 | `gh issue create --body-file body.md --attach ./fig-1.svg`（更新は `gh issue edit <番号> …`） |
| PR コメント | `gh pr comment <番号> --body-file body.md --attach ./fig-1.svg` |
| Issue コメント | `gh issue comment <番号> --body-file body.md --attach ./fig-1.svg` |

- `--attach` は図ごとに 1 回ずつ付ける。本文に `![…](./fig-1.svg)` があれば、gh はその参照を上げたファイルの URL に書き換える。代替テキストは本文に書いたものが残る
- `--body-file` の中の相対パスは、そのファイルのあるフォルダから解決される。コマンドはそのフォルダで実行する
- `--attach` は gh 2.99.0 で入った。`gh --version` が古ければ、gh を更新するか、GitHub の Web の編集画面に SVG をドラッグして貼るよう案内する
- `gh pr review` には `--attach` が無い。レビューの本文に図を入れたいときは、`gh pr comment` のコメントにする
- private のリポジトリに上げた図は、そのリポジトリを読める人だけが見られる

## 投稿済みの図を取り出す

投稿済みの本文の図は `https://github.com/user-attachments/assets/<ID>` の URL になっている。公開リポジトリなら、そのまま取得できる。private のリポジトリでは、認証なしの取得は 404 になるので、gh の認証で取得する。

```bash
curl -sL -H "Authorization: token $(gh auth token)" -o fig.svg 'https://github.com/user-attachments/assets/<ID>'
```

取得したファイルが SVG（`<svg` で始まる）でなければ、PNG などの画像として扱う。

## レビューチェックリスト

- [ ] 図を置く箇所の表に当たる箇所に、図があるか。当たらない文書に図を足していないか
- [ ] 図ごとに、担う役を 1 文で言えるか。同じ構造の図が 2 枚ないか
- [ ] 図のラベルと代替テキストに、本文に無い事実がないか。本文と同じ語で書いているか
- [ ] 結論が図の外の文にあるか
- [ ] SVG に不透明な背景とダークの配色があり、外部への参照がないか
- [ ] ライトとダークで描画して、はみ出したラベル・重なった札・交差した線がないか
