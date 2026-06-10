# paper-trail

Turns Claude's reading and writing into **pages of paper**.

Every session, `paper-trail` tracks how much each Claude model read and wrote —
from two independent streams — and converts it into a page count you can see
live in the statusline and in a full `/pages` report.

| Stream | "Read" means | "Wrote" means | How it's counted |
| --- | --- | --- | --- |
| **Session tokens** | `input_tokens` (prompt + cache) | `output_tokens` (completion) | from the transcript usage records, per model |
| **File I/O** | text the `Read` tool pulled in | text the `Write`/`Edit` tools put out | from the `PostToolUse` hook, per model |

Default conversion: **250 words/page** (~333 tokens/page). Fully configurable.

## Components

- **Hook** (`PostToolUse` on `Read|Write|Edit|MultiEdit|NotebookEdit`) — logs
  every file read/write with its word/token count and the active model into
  `~/.claude/paper-trail/sessions/<session_id>.jsonl`.
- **Skill** `pages` — run `/pages` (or ask "how many pages did you read?") for a
  per-model report of both streams.
- **Statusline script** — a live one-liner. Opt-in (see setup below).

## Setup

### 1. Install the plugin

Add the marketplace, then install the plugin:

```
/plugin marketplace add Ink01101011/paper-trail-marketplace
/plugin install paper-trail@paper-trail
```

The hook and the `/pages` skill work immediately — no configuration required.

Try it:

```
/pages
```

### 2. (Optional) Enable the live statusline

Claude Code does not let a plugin register a statusline, so wire it once in
your **`~/.claude/settings.json`**:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 \"$HOME/.claude/plugins/cache/paper-trail/paper-trail/0.1.0/scripts/statusline.py\"",
    "padding": 0
  }
}
```

> **Important:** `${CLAUDE_PLUGIN_ROOT}` is *not* expanded inside
> `statusLine.command` (Claude Code issue #52079), so use the real absolute
> path to the installed script. A marketplace install lands under
> `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`, so the path
> above includes the `0.1.0` version segment — update it when the plugin
> version bumps (run `ls ~/.claude/plugins/cache/paper-trail/paper-trail`
> to see the installed version).

Live output looks like:

```
📄 read 12.4pg · wrote 3.1pg · 📂 4.20pg I/O · 🤖 Opus 4.8
```

## Configuration

On first run the plugin writes `~/.claude/paper-trail/config.json`:

```json
{
  "words_per_page": 250,
  "words_per_token": 0.75,
  "chars_per_token": 4
}
```

- `words_per_page` — page size. 250 = manuscript page; set 500 for a dense
  printed page.
- `words_per_token` — how token counts map to words (~0.75 for English).
  Together with `words_per_page` this sets tokens/page.
- `chars_per_token` — fallback estimate when only a character count is known.

Edit the file and the change applies to the next report / statusline refresh.

## Usage

- **Live counter:** glance at the statusline (once enabled).
- **Full report:** `/pages`, or "show my page count", "how many pages did you
  write this session". Add detail by running the engine directly:

  ```bash
  python3 "$HOME/.claude/plugins/cache/paper-trail/paper-trail/0.1.0/scripts/report.py" --json
  python3 "$HOME/.claude/plugins/cache/paper-trail/paper-trail/0.1.0/scripts/report.py" --transcript /path/to/session.jsonl
  ```

## Data & privacy

Everything stays local under `~/.claude/paper-trail/`. The hook stores only
counts (chars, words, token estimates), the file path, the tool name, and the
model id — never file contents. Delete the folder any time to reset.

## Requirements

- Python 3 (standard library only — no pip installs).
