# bb-doc-skills

Claude Code で使う、日本語の執筆・レビュー・図解の 5 スキルです。

[English](README.md)

読者が何をするための文書かに合わせて、スキルを選びます。

| スキル | 用途 |
|---|---|
| `retention-write` | 提案書・設計メモなど、判断や主張を伝える散文を書く |
| `retention-review` | その散文の論証・構成・日本語の文体をレビューする |
| `tech-write` | README・Issue・手順書・コメントなどの参照文書を書く |
| `tech-review` | 参照文書を、目的と文体の原則に沿ってレビューする |
| `explain` | 図・裏取りの状態・比喩の限界を持つローカル HTML で題材を説明する |

スキルの指示と文体検査は日本語です。英語の README があることは、英語でも同等の文体検査ができるという意味ではありません。5 スキル、共有 references、[文書設計の規範](memorable-doc-principles.md)をまとめて配布します。

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

## 旧 symlink 配備からの移行

初めて導入する人は、この節のリンク解除を行わず「導入」へ進んでください。開発用 symlink を続ける人は、公開版を同時に有効化しません。既存利用者だけが以下を行います。POSIX の shell と Python 3 を使う手順です。

### 1. 対象と復元先を記録する

旧配備の実体がある自分の doc-skills checkout へ移動してから実行します。`DOC_SKILLS_ROOT` がその実体の root であることを確認してください。通常ディレクトリ・通常ファイル・想定外のリンク・切れたリンクなら停止し、個別に対象を確認します。実体を移動・削除しません。旧リンクの位置とリンク先を確認し、全 5 件が想定と一致した場合だけ復元用 JSON を作ります。

```sh
# Run from your existing doc-skills checkout.
export DOC_SKILLS_ROOT="$(pwd -P)"
export DOC_SKILLS_BACKUP="$PWD/old-doc-skills-links.json"
python3 - <<'PYTHON'
from pathlib import Path
import json, os
root = Path(os.environ["DOC_SKILLS_ROOT"]).resolve(strict=True)
base = Path.home() / ".claude" / "skills"
names = ("retention-write", "retention-review", "tech-write", "tech-review", "explain")
links = {}
for name in names:
    link = base / name
    expected = root / "skills" / name
    if not link.is_symlink():
        raise SystemExit(f"STOP: {name} is not a symlink")
    if link.resolve(strict=True) != expected.resolve(strict=True):
        raise SystemExit(f"STOP: unexpected target for {name}")
    if not (expected / "SKILL.md").is_file():
        raise SystemExit(f"STOP: missing SKILL.md for {name}")
    links[name] = {"target": os.readlink(link), "resolved": str(link.resolve(strict=True))}
with open(os.environ["DOC_SKILLS_BACKUP"], "x", encoding="utf-8") as out:
    json.dump(links, out, ensure_ascii=False, indent=2)
print("Checked and recorded all five symlinks; nothing removed.")
PYTHON
```

`old-doc-skills-links.json` を開いて、5 件のリンク先と解決後の実体を確認してください。実際の配置情報が含まれるので、自分の手元だけに保管し、公開・外部送信しません。既存の同名記録は上書きしません。記録先が既にあれば別名を `DOC_SKILLS_BACKUP` に指定してやり直します。

### 2. 確認したリンクを 1 件ずつ外す

上と同じ shell で実行します。次の `name` は 1 件の名前です。`retention-write`、`retention-review`、`tech-write`、`tech-review`、`explain` の順に、名前を変えて 1 件ずつ実行してください。記録時のリンクと一致しなければ停止します。実体・無関係なスキル・設定は削除しません。

```sh
name=retention-write
python3 - "$name" <<'PYTHON'
from pathlib import Path
import json, os, sys
saved = json.loads(Path(os.environ["DOC_SKILLS_BACKUP"]).read_text(encoding="utf-8"))
name = sys.argv[1]
if name not in ("retention-write", "retention-review", "tech-write", "tech-review", "explain"):
    raise SystemExit("STOP: unknown skill")
link = Path.home() / ".claude" / "skills" / name
entry = saved[name]
if not link.is_symlink() or os.readlink(link) != entry["target"]:
    raise SystemExit("STOP: link changed since recording")
if str(link.resolve(strict=True)) != entry["resolved"]:
    raise SystemExit("STOP: resolved target changed")
link.unlink()
print(f"Removed only the {name} symlink.")
PYTHON
```

解除後、5 件の旧リンクだけがなく、実体と無関係なスキルが残っていることを確認します。作業途中で失敗したら、解除済みの名前を控えて「失敗時に戻す」へ進みます。`rm -r`、`rm -rf`、リンク先の削除は使いません。

### 3. 公開版を導入し、重複と参照を確認する

「導入」のコマンドを実行し、新しい Claude Code セッションを開始します。`claude plugin list` で `bb-doc-skills@bb-doc-skills-marketplace` の版・scope・enabled 状態を確認し、`/` の候補に `bb-doc-skills:` 付きの 5 スキルが各 1 件あることを確認します。旧来の同用途のスキルが残っていないことも確認してください。別 scope の同プラグインが有効なら、その設定を確認するまで操作を止めます。

元の資料と保存先を渡し、5 スキルをそれぞれ試します。実行中に、規範 `memorable-doc-principles.md` の全文と必要な共有 references を同じ配布ルートから読めたことを確認してください。規範はルートに 1 部あり、スキルの実体から解決します。存在確認だけで読取成功にしません。規範・参照が読めない、導入が失敗する、二重登録が残る場合は移行完了にせず、復元へ進みます。

## 更新

公開された新版を使うときは、marketplace の情報を更新してから同じ user scope の plugin を更新します。インストール済みファイルを直接編集しません。

```sh
claude plugin marketplace update bb-doc-skills-marketplace
claude plugin update bb-doc-skills@bb-doc-skills-marketplace --scope user
claude plugin list
```

更新後は新しいセッションで、表示された版が配布予定の版へ変わり、5 スキルの認識と規範・共有資料の読取りが継続していることを確認します。版が変わらない、更新が失敗する、参照に失敗する場合は成功とせず、失敗内容を控えて復元するか、既存の版を維持します。公開リポジトリへ版が配布されるまでは導入・更新できません。ローカル候補での確認は GitHub 経由の公開導入とは区別します。

## 失敗時に戻す

この手順で導入した user scope の公開版を無効化してから撤去します。他の scope の設定・無関係な plugin は変更しません。別 scope に同 plugin がある場合は、実際の登録を確認してから判断します。

```sh
claude plugin disable bb-doc-skills@bb-doc-skills-marketplace --scope user
claude plugin uninstall bb-doc-skills@bb-doc-skills-marketplace --scope user
claude plugin list
```

新しいセッションで同 plugin が有効でないことを確認してから、解除した名前だけを 1 件ずつ戻します。上と同じ shell の `DOC_SKILLS_BACKUP` を使います。shell を開き直した場合は、自分が保存した JSON をこの変数へ設定してください。絶対リンクも相対リンクも、控えた元のリンク文字列で復元します。復元先にファイル・通常ディレクトリ・別リンクがあれば上書きせず停止します。

```sh
name=retention-write
python3 - "$name" <<'PYTHON'
from pathlib import Path
import json, os, sys
saved = json.loads(Path(os.environ["DOC_SKILLS_BACKUP"]).read_text(encoding="utf-8"))
name = sys.argv[1]
if name not in ("retention-write", "retention-review", "tech-write", "tech-review", "explain"):
    raise SystemExit("STOP: unknown skill")
link = Path.home() / ".claude" / "skills" / name
entry = saved[name]
if os.path.lexists(link):
    raise SystemExit("STOP: restore location is occupied; do not overwrite")
if not (Path(entry["resolved"]) / "SKILL.md").is_file():
    raise SystemExit("STOP: original source is unavailable")
os.symlink(entry["target"], link)
print(f"Restored the {name} symlink.")
PYTHON
```

解除したほかの名前でも繰り返し、新しいセッションで旧 5 スキルだけが認識され、実体・無関係なスキルが残り、規範と必要な共有資料を読めることを確認します。二重登録や参照失敗が残るなら復元完了としません。旧配備の実体が失われている場合も、未知の内容をコピーして埋めず停止します。

## 前提と動作

ローカル検証には Claude Code **2.1.292** と Python **3.12.12** を使います。検証した版であり、最小対応版を表すものではありません。日本語文体のスキャナーは Python 標準ライブラリだけを使い、追加の Python パッケージは不要です。

Claude Code がプラグインと指定資料を読み、shell ツールで `python3` の検査を実行し、指定された成果物を利用者の作業領域へ保存できる権限が必要です。文書のレビューではスキャナーの出力をシグナルとして使い、文脈に照らした判断はモデルが行います。独立した読み手の Agent を使う場合もあります。道具の利用許可は、利用者の Claude Code の設定に従います。

`explain` は、草稿と独立した Agent と検索・取得の道具で事実を裏取りしてから HTML を作ります。Context7 は利用できる場合のライブラリ文書の取得手段で、必須ではありません。使えない場合は Web の検索・取得へ進みます。このプラグインは MCP server の導入や認証情報の提供を行いません。道具が使えない場合や確認がつかない事実は、未検証として報告し、検証済みにはしません。

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
