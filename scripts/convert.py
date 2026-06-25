#!/usr/bin/env python3
"""
convert.py — Convert the two-layer security skill sources into per-agent formats.

Source layout (input):
    sources/
    ├── securedevelopment.md        # central, language-agnostic skill (always-on)
    └── languages/
        ├── python.md               # language implementation (glob-scoped to *.py)
        ├── go.md                   # (future)
        └── _template.md            # skeleton for new languages (ignored: leading _)

Output model (per agent):
  * Rule-file agents (Cursor, Windsurf, Copilot, Antigravity):
      - the central skill becomes an ALWAYS-ON rule
      - each language file becomes a GLOB-SCOPED rule (from its `globs:` field)
  * Skill agents (Claude Code, Codex, OpenCode):
      - ONE skill named after the central file (id: securedevelopment)
      - its SKILL.md body is the central content
      - language files are bundled under the skill's `languages/` subdirectory,
        which the central skill's routing instructions tell the agent to load.

Note on frontmatter field names: each agent ecosystem uses slightly different
keys for "always apply" vs "glob-scoped" rules. The mappings below are a
reasonable baseline; verify against current agent docs before company rollout
and adjust the per-agent generators (they are the only thing that needs to
change).

Usage:
    python scripts/convert.py                          # all agents → dist/
    python scripts/convert.py --agents cursor copilot  # specific agents only
    python scripts/convert.py --source sources --output dist
"""

from __future__ import annotations

import argparse
import re
import shutil
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Frontmatter parser (no PyYAML dependency — keeps this zero-dep)
# ---------------------------------------------------------------------------

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (metadata dict, body) from a markdown file with YAML frontmatter."""
    m = FM_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    meta: dict = {}
    current_key = None
    list_buffer: list[str] = []

    for line in raw.splitlines():
        # continuation of a multi-line scalar (>- style)
        if current_key and line.startswith("  ") and not line.strip().startswith("- "):
            meta[current_key] = (str(meta.get(current_key, "")) + " " + line.strip()).strip()
            continue
        # list item
        if current_key and line.strip().startswith("- "):
            list_buffer.append(line.strip().lstrip("- ").strip())
            meta[current_key] = list_buffer
            continue
        # new key
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            current_key = key
            if val in (">-", ">", "|", "|-"):
                meta[key] = ""
            elif val.startswith("[") and val.endswith("]"):
                meta[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
                list_buffer = meta[key]
            elif (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                meta[key] = val[1:-1]
            elif val:
                meta[key] = val
            else:
                list_buffer = []

    body = text[m.end():]
    return meta, body


# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------

class Rule:
    """One loaded source file (central or language)."""

    def __init__(self, path: Path, meta: dict, body: str, is_central: bool):
        self.path = path
        self.meta = meta
        self.body = body
        self.is_central = is_central
        self.id = meta.get("id", path.stem)
        self.title = meta.get("title", self.id)
        self.description = " ".join(str(meta.get("description", "")).split())
        self.globs = meta.get("globs", "")  # empty for central (always-on)
        # language name, e.g. "python", used for the bundled filename
        langs = meta.get("languages") or []
        self.language = (langs[0] if isinstance(langs, list) and langs else path.stem)


def load_sources(source_dir: Path) -> tuple[Rule, list[Rule]]:
    """Load the central rule and the list of language rules."""
    central_path = source_dir / "securedevelopment.md"
    if not central_path.exists():
        raise SystemExit(f"Central skill not found: {central_path}")

    meta, body = parse_frontmatter(central_path.read_text(encoding="utf-8"))
    central = Rule(central_path, meta, body, is_central=True)

    languages: list[Rule] = []
    lang_dir = source_dir / "languages"
    if lang_dir.is_dir():
        for p in sorted(lang_dir.glob("*.md")):
            if p.stem.startswith("_"):  # skip _template.md and similar
                continue
            lmeta, lbody = parse_frontmatter(p.read_text(encoding="utf-8"))
            languages.append(Rule(p, lmeta, lbody, is_central=False))

    return central, languages


# ---------------------------------------------------------------------------
# Per-agent generators
# ---------------------------------------------------------------------------

AGENTS = {}


def agent(name: str):
    def decorator(fn):
        AGENTS[name] = fn
        return fn
    return decorator


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  ✓ {path}")


# ---- Rule-file agents -------------------------------------------------------

@agent("cursor")
def gen_cursor(central: Rule, languages: list[Rule], out: Path) -> None:
    """Cursor: .cursor/rules/<id>.mdc — central always-on, languages glob-scoped."""
    def emit(rule: Rule):
        if rule.is_central:
            fm = f'---\ndescription: "{rule.description}"\nalwaysApply: true\n---\n\n'
        else:
            fm = (f'---\ndescription: "{rule.description}"\n'
                  f'globs: "{rule.globs}"\nalwaysApply: false\n---\n\n')
        _write(out / ".cursor" / "rules" / f"{rule.id}.mdc", fm + rule.body)
    emit(central)
    for lang in languages:
        emit(lang)


@agent("windsurf")
def gen_windsurf(central: Rule, languages: list[Rule], out: Path) -> None:
    """Windsurf: .windsurf/rules/<id>.md — trigger=always_on vs glob."""
    def emit(rule: Rule):
        if rule.is_central:
            fm = "---\ntrigger: always_on\n---\n\n"
        else:
            fm = f'---\ntrigger: glob\nglobs: "{rule.globs}"\n---\n\n'
        _write(out / ".windsurf" / "rules" / f"{rule.id}.md", fm + rule.body)
    emit(central)
    for lang in languages:
        emit(lang)


@agent("copilot")
def gen_copilot(central: Rule, languages: list[Rule], out: Path) -> None:
    """GitHub Copilot: .github/instructions/<id>.instructions.md — applyTo glob."""
    def emit(rule: Rule):
        apply_to = "**" if rule.is_central else (rule.globs or "**")
        fm = f'---\napplyTo: "{apply_to}"\n---\n\n'
        _write(out / ".github" / "instructions" / f"{rule.id}.instructions.md", fm + rule.body)
    emit(central)
    for lang in languages:
        emit(lang)


@agent("antigravity")
def gen_antigravity(central: Rule, languages: list[Rule], out: Path) -> None:
    """Google Antigravity: .agents/rules/<id>.md — always-on vs glob-scoped."""
    def emit(rule: Rule):
        if rule.is_central:
            fm = "---\nactivation: always_on\n---\n\n"
        else:
            fm = f'---\nactivation: glob\nglobs: "{rule.globs}"\n---\n\n'
        _write(out / ".agents" / "rules" / f"{rule.id}.md", fm + rule.body)
    emit(central)
    for lang in languages:
        emit(lang)


# ---- Skill agents -----------------------------------------------------------

def _skill_frontmatter(rule: Rule) -> str:
    return (f"---\nname: {rule.id}\ndescription: >-\n  {rule.description}\n---\n\n")


def _emit_skill(base: Path, central: Rule, languages: list[Rule]) -> None:
    """One skill dir: SKILL.md (central body) + languages/<lang>.md bundled."""
    _write(base / "SKILL.md", _skill_frontmatter(central) + central.body)
    for lang in languages:
        _write(base / "languages" / f"{lang.language}.md",
               _skill_frontmatter(lang) + lang.body)


@agent("claude-code")
def gen_claude_code(central: Rule, languages: list[Rule], out: Path) -> None:
    """Claude Code: .claude/skills/<central-id>/SKILL.md + languages/."""
    _emit_skill(out / ".claude" / "skills" / central.id, central, languages)


@agent("codex")
def gen_codex(central: Rule, languages: list[Rule], out: Path) -> None:
    """OpenAI Codex: .agents/skills/<central-id>/SKILL.md + languages/."""
    _emit_skill(out / ".agents" / "skills" / central.id, central, languages)


@agent("opencode")
def gen_opencode(central: Rule, languages: list[Rule], out: Path) -> None:
    """OpenCode: .opencode/skills/<central-id>/SKILL.md + languages/."""
    _emit_skill(out / ".opencode" / "skills" / central.id, central, languages)


# Maps agent name → top-level dir it installs into (for install.sh + README).
AGENT_DIRS = {
    "cursor": ".cursor",
    "windsurf": ".windsurf",
    "copilot": ".github",
    "antigravity": ".agents",
    "claude-code": ".claude",
    "codex": ".agents",
    "opencode": ".opencode",
}


# ---------------------------------------------------------------------------
# install.sh writer
# ---------------------------------------------------------------------------

def write_install_script(out: Path) -> None:
    install_sh = out / "install.sh"
    install_sh.write_text(textwrap.dedent("""\
        #!/usr/bin/env bash
        # install.sh — copy generated rules/skills into a project directory.
        # Usage: ./install.sh /path/to/your/project [agent ...]
        #
        # Examples:
        #   ./install.sh ../my-app                  # all agents
        #   ./install.sh ../my-app cursor copilot   # specific agents only

        set -euo pipefail
        SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
        PROJECT="${1:?Usage: install.sh <project-dir> [agent ...]}"
        shift || true

        ALL=(cursor windsurf copilot antigravity claude-code codex opencode)
        if [ "$#" -gt 0 ]; then AGENTS=("$@"); else AGENTS=("${ALL[@]}"); fi

        declare -A DIRS=(
            [cursor]=.cursor
            [windsurf]=.windsurf
            [copilot]=.github
            [antigravity]=.agents
            [claude-code]=.claude
            [codex]=.agents
            [opencode]=.opencode
        )

        for name in "${AGENTS[@]}"; do
            dir="${DIRS[$name]:-}"
            if [ -z "$dir" ]; then echo "Unknown agent: $name" >&2; continue; fi
            if [ -d "${SCRIPT_DIR}/${dir}" ]; then
                echo "Installing ${name} → ${PROJECT}/${dir}/"
                mkdir -p "${PROJECT}"
                cp -r "${SCRIPT_DIR}/${dir}" "${PROJECT}/"
            fi
        done

        echo ""
        echo "Done. Restart your AI coding agent to load the new rules/skills."
    """), encoding="utf-8")
    install_sh.chmod(0o755)
    print(f"\n✓ Install script: {install_sh}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert the two-layer security skill into per-agent formats."
    )
    parser.add_argument("--source", type=Path, default=Path("sources"),
                        help="Source directory (default: sources/)")
    parser.add_argument("--output", "-o", type=Path, default=Path("dist"),
                        help="Output directory (default: dist/)")
    parser.add_argument("--agents", nargs="*", default=None,
                        help=f"Specific agents only. Options: {', '.join(sorted(AGENTS))}")
    args = parser.parse_args()

    central, languages = load_sources(args.source)

    targets = args.agents or list(AGENTS.keys())
    invalid = [t for t in targets if t not in AGENTS]
    if invalid:
        parser.error(f"Unknown agent(s): {', '.join(invalid)}. "
                     f"Available: {', '.join(sorted(AGENTS))}")

    if args.output.exists():
        shutil.rmtree(args.output)

    print(f"Central skill : {central.id}  ({central.path})")
    print(f"Languages     : {', '.join(l.language for l in languages) or '(none)'}")
    for name in targets:
        print(f"\n📦 {name}")
        AGENTS[name](central, languages, args.output)

    write_install_script(args.output)
    print("✓ Conversion complete.")


if __name__ == "__main__":
    main()
