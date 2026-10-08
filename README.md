# bb-doc-skills

Five Japanese writing, review, and visual explanation skills for Claude Code.

[日本語](README.ja.md)

Choose a skill by the job your reader needs to do:

| Skill | Use it for |
|---|---|
| `retention-write` | Writing proposals, design notes, and other prose that conveys a decision or argument |
| `retention-review` | Reviewing that prose for reasoning, structure, and Japanese style |
| `tech-write` | Writing reference documents such as READMEs, issues, procedures, and comments |
| `tech-review` | Reviewing reference documents against their purpose and style rules |
| `explain` | Explaining a topic in a local HTML page with diagrams, verification status, and limits of analogies |

The skill instructions and style checks are Japanese. An English README does not imply equivalent English style checking. All five skills, their shared references, and the [writing principles](memorable-doc-principles.md) ship together.

## Install

From your shell (user scope):

```sh
claude plugin marketplace add B16B1RD/bb-doc-skills
claude plugin install bb-doc-skills@bb-doc-skills-marketplace --scope user
claude plugin list
```

Start a new session after installation, then invoke a skill with its plugin prefix:

```text
/bb-doc-skills:retention-write Draft a proposal from these facts and the decision we need to make.
/bb-doc-skills:retention-review Review proposal.md and explain what needs to change.
/bb-doc-skills:tech-write Write a README from this repository's actual behavior.
/bb-doc-skills:tech-review Review README.md against the repository.
/bb-doc-skills:explain Explain DNS for a middle-school reader.
```

Supply the source material, intended audience, and output path with your request. Keep all five skills together because they share references and the scanner. For plugin management, see the [official instructions](https://code.claude.com/docs/en/discover-plugins).

## Migrate from the old symlink deployment

New users skip symlink removal and go straight to Install. Developers who keep symlinks should not enable the public plugin at the same time. The following steps are for existing users, using a POSIX shell and Python 3.

### 1. Inspect and record the targets

Change to your existing doc-skills checkout before running this. Confirm that `DOC_SKILLS_ROOT` is the root containing the original skill files. Stop for a regular directory, regular file, unexpected link, or broken link and inspect it individually. Do not move or delete source files. Only after all five links match the expected checkout does this read-only check save their original link strings and resolved targets.

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

Open `old-doc-skills-links.json` and confirm all five link strings and resolved targets. It contains your actual deployment locations: keep it locally; do not publish or send it externally. Existing records are not overwritten. If that filename exists, set `DOC_SKILLS_BACKUP` to another filename and rerun the inspection.

### 2. Remove each confirmed link individually

Use the same shell. `name` below selects one skill. Change it and run once for each of `retention-write`, `retention-review`, `tech-write`, `tech-review`, and `explain`, in that order. Stop if a link no longer matches its record. Source files, unrelated skills, and settings are retained.

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

Confirm that only the five old links are absent and that their source files and unrelated skills remain. On a partial failure, record which names were removed and follow Roll back. Do not use `rm -r`, `rm -rf`, or remove a link target.

### 3. Install and check for duplicates and readable references

Run the Install commands and start a new Claude Code session. In `claude plugin list`, check the version, scope, and enabled status of `bb-doc-skills@bb-doc-skills-marketplace`. In the `/` menu, confirm that each of the five skills appears once under `bb-doc-skills:` and that the old skills serving the same purpose are absent. If this plugin is enabled at another scope, stop and inspect that registration first.

Try all five skills with source material and output paths. Confirm from the execution that the full `memorable-doc-principles.md` and required shared references were read from the same distribution root. The principles are bundled once at the root and resolved from the skill's actual directory. File existence alone is not a successful read. A failed installation, unreadable principles or references, or remaining duplicates means migration is incomplete: roll back.

## Update

For a published new version, update the marketplace first, then update the plugin at the same user scope. Do not edit installed plugin files directly.

```sh
claude plugin marketplace update bb-doc-skills-marketplace
claude plugin update bb-doc-skills@bb-doc-skills-marketplace --scope user
claude plugin list
```

In a new session, confirm that the displayed version matches the intended release, all five skills are recognized, and the principles and shared references remain readable. If the version did not change, updating failed, or references cannot be read, do not report success: record the failure and roll back or retain the existing version. Installation and updates require a release in the public repository. A local-candidate check is separate from installation through GitHub.

## Roll back

Disable and uninstall the public plugin installed by these steps at user scope. Do not change unrelated plugins or settings at other scopes. If the same plugin exists at another scope, inspect the actual registrations before deciding how to proceed.

```sh
claude plugin disable bb-doc-skills@bb-doc-skills-marketplace --scope user
claude plugin uninstall bb-doc-skills@bb-doc-skills-marketplace --scope user
claude plugin list
```

In a new session, confirm that the plugin is no longer enabled. Then restore only the names you removed, individually, using `DOC_SKILLS_BACKUP` in the same shell. If you opened another shell, set this variable to your saved JSON file. Both absolute and relative links are restored with their original link strings. Stop without overwriting if a file, regular directory, or another link occupies a restore location.

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

Repeat for the other removed names. In a new session, confirm that only the old five skills are recognized, their source files and unrelated skills remain, and the principles and required shared references are readable. Remaining duplicates or failed references mean rollback is incomplete. If the original source was lost, stop rather than substituting unknown files.

## Requirements and behavior

Local validation uses Claude Code **2.1.292** and Python **3.12.12**. These are tested versions, not minimum supported versions. The Japanese prose scanner uses only the Python standard library; no additional Python packages are needed.

Allow Claude Code to read the plugin files and your supplied documents, run `python3` through its shell tool for scanning, and write requested outputs in your workspace. Retention and technical reviews use the scanner as a source of signals; the model still judges their context. They can also use an independent reader agent. Tool permissions remain subject to your Claude Code settings.

`explain` uses an independent Agent context and search/fetch tools to check facts before generating HTML. Context7 can help with library documentation when available; it is optional, with web search/fetch as the alternative. The plugin does not install an MCP server or supply credentials. Unavailable tools or unresolved facts remain unverified and are reported; they are not turned into verified facts.

HTML is saved in your workspace or at the path you specify. The default for `explain` is `explain-<slug>.html` in the current directory. An explicit request for “Artifact で” additionally asks for Artifact publishing, only where that tool is available. Artifact is not a standard requirement of Claude Code; if unavailable, the skill saves locally and reports that it did not publish. Browser-based visual checks also depend on available tools; a source-only check is reported as such.

The skills do not guarantee factual accuracy or long-term recall. Review generated documents and verification results before relying on them. The memory research informs design choices; these skills have not established those effects in AI-generated documents.

## Acknowledgements

The following public work informed specific parts of the design. The descriptions state the scope of that influence; they do not claim a wholesale port or reproduction of a research protocol.

| Work and author | Influence |
|---|---|
| [AIっぽい文章表現大全](https://note.com/yusuke_motoyama/n/n2a1218636f56) — もとやま | Japanese style checks in the principles and writing skills. |
| [yomiyasu](https://github.com/nanaism/yomiyasu) — nanaism | Bounded revision passes and preserving facts from the source. |
| [japanese-tech-writing](https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d/8f2d57610a73efc97d743c9b0b0ecb1002e09fa4) — k16shikano | Reasoning, reader effort, and point of view in the four writing and review skills. |
| [編集者は日本語をどうやって推敲しているか](https://golden-lucky.hatenablog.com/entry/2026/08/20/185818) — golden-lucky | Reading paragraph relationships and locating where a reader loses the thread. |
| [ELI5](https://github.com/anthropics/claude-plugins-community/tree/main/eli5) — Thariq Shihipar | Image-led panels with short explanations in explain. |
| [説明スキルの比較：ELI5、Archify、Explainer](https://blog.lai.so/eli5-archify-explainer-skills/) — laiso | The comparison that prompted the following explanation design changes. |
| [Explainer](https://github.com/mizchi/explainer) — mizchi | Through laiso's comparison: audience knowledge, unresolved questions, and checking executable examples. |
| [Archify](https://github.com/tt-a1i/archify) — tt-a1i | Through laiso's comparison: choosing branching, state, or request/response diagrams to suit the topic. |
| [Writes and Write-Nots](https://paulgraham.com/writes.html) — Paul Graham | Settling the author's decision and claim before polishing prose. |
| [Diátaxis](https://diataxis.fr/) — Daniele Procida and contributors | Selecting technical writing guidance by reader purpose; the four quadrants are not reproduced as-is. |
| [rite workflow](https://github.com/B16B1RD/cc-rite-workflow) — B16B1RD and contributors | Shared references, independent readers, and explicit fact-check verdicts. |
| [Memory and comprehension of narrative versus expository texts: A meta-analysis](https://doi.org/10.3758/s13423-020-01853-1) — Raymond A. Mar et al. | Causal narrative structure in the shared principles. |
| [Test-Enhanced Learning](https://doi.org/10.1111/j.1467-9280.2006.01693.x) — Henry L. Roediger III and Jeffrey D. Karpicke | Recall questions in the principles and retention skills. |
| [Levels of processing](https://doi.org/10.1016/S0022-5371(72)80001-X) — Fergus I. M. Craik and Robert S. Lockhart | Meaningful processing beyond surface fluency in the principles. |
| [Telling Lies to Children](https://serc.carleton.edu/earthandmind/posts/lies_children.html) — Kim Kastens and Dana Chayes | Distinguishing simplification from false claims that later need to be withdrawn. |
| [Chain-of-Verification](https://aclanthology.org/2024.findings-acl.212/) — Shehzaad Dhuliawala et al. | Checking facts in a separate context without the draft. |
| [Enabling Large Language Models to Generate Text with Citations](https://arxiv.org/abs/2305.14627) — Tianyu Gao et al. | Checking whether a source supports each claim. |
| [natural-japanese](https://github.com/coji/natural-japanese) — coji | Train/test separation and competing-trigger checks in development evaluations. |
| [skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) — Anthropic | Creating, trying, and refining the initial four skills. |
| [Defuddle](https://github.com/kepano/defuddle) — kepano and contributors | Extracting web article text for evaluation materials. |

Natural-japanese, skill-creator, and Defuddle are acknowledged for development and evaluation work; they are not runtime dependencies. The [writing principles](memorable-doc-principles.md) retain further research citations.

## License

[MIT](LICENSE). See the [changelog](CHANGELOG.md) for release changes.

This is an independent project, not an official Anthropic product and not endorsed by or affiliated with Anthropic. Product names identify compatibility or cited work.
