---
name: pages
description: >
  This skill should be used when the user asks "how many pages", runs "/pages",
  or wants a paper-trail report of how much Claude read and wrote in the current
  session — broken down per Claude model and converted into pages of paper.
  Trigger on phrases like "pages report", "how many pages did you read/write",
  "token to pages", "paper trail", or "show my page count".
metadata:
  version: "0.1.0"
---

# Pages report

Produce a per-model "pages of paper" report for the current session by running
the bundled `report.py`. The plugin tracks two independent streams and this
report shows both:

- **Session tokens** — `input_tokens` (read) and `output_tokens` (written)
  pulled from the transcript usage records, summed per model.
- **File I/O** — the real text moved by the Read / Write / Edit tools, captured
  by the PostToolUse hook into a per-session log.

## Steps

1. Run the report script with the plugin's bundled Python:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py"
   ```

   With no arguments it auto-detects the most recently modified transcript
   under `~/.claude/projects/` and the matching file I/O log. To target a
   specific session, pass `--transcript <path>` or `--session <session_id>`.
   For machine-readable output, add `--json`.

2. Present the script's output to the user. Keep the model breakdown and the
   conversion line (words/page and tokens/page) intact — they explain the
   numbers.

3. If the user asks to change the conversion (e.g. words per page), edit
   `~/.claude/paper-trail/config.json`. Keys: `words_per_page` (default 250)
   and `words_per_token` (default 0.75). Re-run the report afterward.

## Notes

- If the report says "No activity found yet", the hook has not logged anything
  for this session and the transcript has no usage records yet. This is normal
  at the very start of a session.
- The file I/O stream only has data once the `paper-trail` PostToolUse hook has
  fired at least once (i.e. after Claude has used Read / Write / Edit).
- Do not invent numbers. Always report exactly what `report.py` prints.
