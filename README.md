# Secure Development Skill

A secure-by-default skill set that guides AI coding agents (Claude Code, Codex,
Cursor, Windsurf, GitHub Copilot, OpenCode, Antigravity) to **generate secure
code as it is written**, rather than relying on a scanner to catch
vulnerabilities afterward. It is a preventive control that complements — not
replaces — our existing SAST.

## Structure

The skill is **two layers**: one central, language-agnostic skill plus a series
of language implementation files.

```
secure-code-skills/
├── sources/                      # single source of truth — edit here
│   ├── securedevelopment.md      # CENTRAL: principles + routing (always-on)
│   └── languages/
│       ├── python.md             # Python implementation (do/don't code)
│       ├── _template.md          # skeleton for adding a new language (ignored by build)
│       └── …                     # go.md, java.md, … (future)
├── scripts/
│   └── convert.py                # build: sources → per-agent formats
├── dist/                         # GENERATED — do not edit by hand
│   ├── .cursor/ .windsurf/ .github/ .agents/ .claude/ .opencode/
│   └── install.sh
└── README.md
```

- **`securedevelopment.md`** states the *what* — the eleven security categories
  (§1–§11) and the principle behind each, language-agnostic. It is marked
  always-on, so it applies to all code. It also tells the agent to load the
  matching language file.
- **`languages/<lang>.md`** states the *how* — the exact idiomatic do/don't code
  for that language, using the same §1–§11 numbering. Scoped to that language's
  files (e.g. `**/*.py`).

A developer reading only the language file gets enough to act; the central file
explains the reasoning and keeps the shared principles in one place.

## Build

Zero dependencies — standard-library Python 3.9+.

```bash
python scripts/convert.py                         # all agents → dist/
python scripts/convert.py --agents cursor copilot # specific agents only
```

The build regenerates `dist/` from scratch each time. Never edit `dist/` by
hand; edit `sources/` and rebuild.

## Install into a project

```bash
cd dist
./install.sh /path/to/your/project                 # all agents
./install.sh /path/to/your/project claude-code     # one agent
```

This copies the per-agent directories (`.claude/`, `.cursor/`, …) into the target
repo. Installing at the repository level means every team member picks up the
rules automatically on clone. Restart the agent afterward to load them.

### Where each agent looks

| Agent          | Installed path                                              | Form              |
|----------------|-------------------------------------------------------------|-------------------|
| Claude Code    | `.claude/skills/securedevelopment/`                         | skill + languages/|
| Codex          | `.agents/skills/securedevelopment/`                         | skill + languages/|
| OpenCode       | `.opencode/skills/securedevelopment/`                       | skill + languages/|
| Cursor         | `.cursor/rules/*.mdc`                                        | rule files        |
| Windsurf       | `.windsurf/rules/*.md`                                       | rule files        |
| GitHub Copilot | `.github/instructions/*.instructions.md`                    | rule files        |
| Antigravity    | `.agents/rules/*.md`                                         | rule files        |

> **Frontmatter field names** (always-on vs glob-scoped) differ per agent and
> evolve. The mappings live in the per-agent generators in `scripts/convert.py`
> and are a reasonable baseline — verify against each agent's current docs
> before a wide rollout and adjust there if needed.

## Adding a new language

1. Copy `sources/languages/_template.md` to `sources/languages/<lang>.md`.
2. Replace `LANG` / `EXT` and the frontmatter `id` / `globs`.
3. Keep all eleven sections in the same order and numbering — fill each with
   idiomatic do/don't code for that language.
4. Rebuild: `python scripts/convert.py`.

The central skill does not change when you add a language. That is the point of
the split: shared principles stay in one place, languages plug in underneath.

## Scope

This repo is the skill itself. Project tracking (objective, participants,
working group, challenges, actions, pilot plan) lives on the project's
Confluence page.
