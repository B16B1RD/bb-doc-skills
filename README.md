# bb-doc-skills

Claude Code で使う、日本語の執筆・レビュー・図解の 5 スキルです。

紹介動画（56 秒）です。5 つのスキルを、公開版を入れた Claude Code で実際に動かして録りました。作業の部分は早送りです。

https://github.com/user-attachments/assets/96a6f9f3-4dbb-4fa6-b1c6-c713486cf6e4

読者が何をするための文書かに合わせて、スキルを選びます。

| スキル | 用途 |
|---|---|
| `retention-write` | 提案書・設計メモなど、判断や主張を伝える散文を書く |
| `retention-review` | その散文の論証・構成・日本語の文体をレビューする |
| `tech-write` | README・Issue・手順書・コメントなどの参照文書と、書き手の意見を足さない論文・記事の紹介を書く。比較や計測の調査も自分で行い、確かめた方法を添えた調査レポートを書く。Git Flow のような技術トピックの解説も、出典を添えて書き手の評価を足さずに書く |
| `tech-review` | 参照文書を目的と文体の原則に沿ってレビューし、論文・記事の紹介は原典と照合し、調査レポートは確かめた方法をたどり直し、技術トピックの解説は出典と時点を確かめる |
| `explain` | 図・裏取りの状態・比喩の限界を持つローカル HTML で題材を説明する |

スキルの指示と文体検査は日本語です。5 スキル、共有 references、[文書設計の規範](memorable-doc-principles.md)をまとめて配布します。

## 導入

shell から user scope へ導入します。

```sh
claude plugin marketplace add B16B1RD/bb-doc-skills
claude plugin install bb-doc-skills@bb-doc-skills-marketplace --scope user
claude plugin list
```

導入後に新しいセッションを開始し、プラグイン名を付けて呼び出します。

```text
/bb-doc-skills:retention-write この事実と決めたいことを基に提案書を書いて。
/bb-doc-skills:retention-review proposal.md をレビューし、直すべき点を説明して。
/bb-doc-skills:tech-write このリポジトリの実際の動作を基に README を書いて。
/bb-doc-skills:tech-review README.md をリポジトリと照らしてレビューして。
/bb-doc-skills:explain DNS を中学生向けに説明して。
```

依頼には、元の資料・想定読者・保存先も添えてください。共有 references とスキャナーを使うため、5 スキルはまとめて配置します。プラグインの管理方法は[公式の案内](https://code.claude.com/docs/en/discover-plugins)を参照してください。

## 更新

公開された新版を使うときは、marketplace の情報を更新してから同じ user scope の plugin を更新します。インストール済みファイルを直接編集しません。

```sh
claude plugin marketplace update bb-doc-skills-marketplace
claude plugin update bb-doc-skills@bb-doc-skills-marketplace --scope user
claude plugin list
```

更新後は新しいセッションで、表示された版が新しい版へ変わり、5 スキルの認識と規範・共有資料の読取りが継続していることを確認します。版が変わらない、更新が失敗する、参照に失敗する場合は成功とせず、失敗内容を控えます。使い続けられない場合は、次の「失敗時に戻す」で撤去します。

## 失敗時に戻す

この手順で導入した user scope の公開版を無効化してから撤去します。他の scope の設定・無関係な plugin は変更しません。別 scope に同 plugin がある場合は、実際の登録を確認してから判断します。

```sh
claude plugin disable bb-doc-skills@bb-doc-skills-marketplace --scope user
claude plugin uninstall bb-doc-skills@bb-doc-skills-marketplace --scope user
claude plugin list
```

新しいセッションで、同 plugin が有効でないことを確認します。

## 前提と動作

日本語文体のスキャナーは `python3` と Python 標準ライブラリだけで動き、追加の Python パッケージは不要です。

Claude Code がプラグインと指定資料を読み、shell ツールで `python3` の検査を実行し、指定された成果物を利用者の作業領域へ保存できる権限が必要です。文書のレビューではスキャナーの出力をシグナルとして使い、文脈に照らした判断はモデルが行います。独立した読み手の Agent を使う場合もあります。道具の利用許可は、利用者の Claude Code の設定に従います。

`explain` は、草稿と独立した Agent と検索・取得の道具で事実を裏取りしてから HTML を作ります。Context7 は利用できる場合のライブラリ文書の取得手段で、必須ではありません。使えない場合は Web の検索・取得へ進みます。このプラグインは MCP server の導入や認証情報の提供を行いません。道具が使えない場合や確認がつかない事実は、未検証として報告し、検証済みにはしません。納品前には読みやすさも点検します。日本語のページはスキャナーにかけ、どのページも独立した読み手の Agent に読ませます。

HTML は利用者の作業領域または指定された場所へ保存します。`explain` の既定はカレントディレクトリの `explain-<slug>.html` です。「Artifact で」と明示した場合は、その道具がある環境に限って Artifact 公開も行います。Artifact は Claude Code の標準的な必須機能ではなく、使えなければローカル保存だけを行い、未公開と報告します。ブラウザーによる目視確認も使える道具に依存し、ソースだけで確認した場合はその旨を報告します。

事実の正しさや長期記憶への定着を保証するものではありません。生成した文書と裏取りの結果を確認してから使ってください。記憶研究は設計上の参考であり、その効果を AI 生成文書で実証したものではありません。

## 謝辞

次の公開資料から、表に記した考え方を取り入れています。影響を受けた範囲を示すもので、実装全体の移植や研究手法の再現を意味しません。

| 資料・著者 | 取り入れた考え方 |
|---|---|
| [AIっぽい文章表現大全](https://note.com/yusuke_motoyama/n/n2a1218636f56) — もとやま | 規範と文書スキルの日本語文体の見直し。 |
| [yomiyasu](https://github.com/nanaism/yomiyasu) — nanaism | 修正回数の上限と、原文にない事実を補わない規則。 |
| [japanese-tech-writing](https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d/8f2d57610a73efc97d743c9b0b0ecb1002e09fa4) — k16shikano | 4 文書スキルの論証・読者負荷・視点。 |
| [編集者は日本語をどうやって推敲しているか](https://golden-lucky.hatenablog.com/entry/2026/08/20/185818) — golden-lucky | 段落の関係を読み、読者が迷う位置を見つける手順。 |
| [ELI5](https://github.com/anthropics/claude-plugins-community/tree/main/eli5) — Thariq Shihipar | explain の絵を主役にした短い説明。 |
| [説明スキルの比較：ELI5、Archify、Explainer](https://blog.lai.so/eli5-archify-explainer-skills/) — laiso | 説明手順の改善を検討するきっかけとなった比較。 |
| [Explainer](https://github.com/mizchi/explainer) — mizchi | laiso の比較記事を介した、配布先の既知・未解決の問い・実行による裏取りの発想。 |
| [Archify](https://github.com/tt-a1i/archify) — tt-a1i | laiso の比較記事を介した、題材に合う分岐・状態遷移・往復の図を選ぶ発想。 |
| [Writes and Write-Nots](https://paulgraham.com/writes.html) — Paul Graham | 文体を整える前に、書き手の決定と主張を確定する設計。 |
| [Diátaxis](https://diataxis.fr/) — Daniele Procida and contributors | 読者の目的に応じて技術文書の原則を選ぶ設計。四象限をそのまま実装したものではない。 |
| [rite workflow](https://github.com/B16B1RD/cc-rite-workflow) — B16B1RD and contributors | 共有 references、独立した読み手、裏取りの判定区分。 |
| [Memory and comprehension of narrative versus expository texts: A meta-analysis](https://doi.org/10.3758/s13423-020-01853-1) — Raymond A. Mar et al. | 規範の因果の物語による構成。 |
| [Test-Enhanced Learning](https://doi.org/10.1111/j.1467-9280.2006.01693.x) — Henry L. Roediger III and Jeffrey D. Karpicke | 規範と retention 系の想起を伴う読了チェック。 |
| [Levels of processing](https://doi.org/10.1016/S0022-5371(72)80001-X) — Fergus I. M. Craik and Robert S. Lockhart | 見た目の流暢さだけでなく、意味の処理を促す規範。 |
| [Telling Lies to Children](https://serc.carleton.edu/earthandmind/posts/lies_children.html) — Kim Kastens and Dana Chayes | explain で単純化と、後で撤回が必要になる虚偽を区別する考え方。 |
| [Chain-of-Verification](https://aclanthology.org/2024.findings-acl.212/) — Shehzaad Dhuliawala et al. | 草稿を見せない別文脈で事実を検証する発想。 |
| [Enabling Large Language Models to Generate Text with Citations](https://arxiv.org/abs/2305.14627) — Tianyu Gao et al. | 主張ごとに出典の支持を確認する考え方。 |
| [natural-japanese](https://github.com/coji/natural-japanese) — coji | 開発時の発動境界評価における train/test 分離と競合検出。 |
| [skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) — Anthropic | 初期 4 スキルの作成・試走・改善。 |
| [Defuddle](https://github.com/kepano/defuddle) — kepano and contributors | 評価資料の Web 本文抽出。 |

natural-japanese・skill-creator・Defuddle は開発と評価の道具としての謝辞であり、実行時の依存ではありません。[文書設計の規範](memorable-doc-principles.md)には、このほかの研究出典も残しています。

## ライセンス

[MIT](LICENSE)。版ごとの変更は[変更履歴](CHANGELOG.md)を参照してください。

独立したプロジェクトであり、Anthropic の公式製品ではなく、公認・提携を示すものでもありません。製品名は対応環境や参照資料を示すために記載しています。
