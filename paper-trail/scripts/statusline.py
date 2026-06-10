#!/usr/bin/env python3
"""paper-trail statusline.

Reads the statusLine payload from stdin and prints one compact line showing,
for the current session, how many pages the model has read and written --
plus the live file I/O page count from the hook log. Never errors out: on any
problem it prints a minimal line and exits 0.

Example output:
  📄 read 12.4pg · wrote 3.1pg · 📂 4.20pg I/O · 🤖 Opus 4.8
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import ptlib
except Exception:
    print("📄 paper-trail")
    sys.exit(0)


def main():
    raw = sys.stdin.read()
    payload = {}
    if raw:
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}

    cfg = ptlib.load_config()

    # --- model label ---
    model = payload.get("model") if isinstance(payload, dict) else None
    if isinstance(model, dict):
        label = model.get("display_name") or ptlib.model_label(model.get("id"))
    else:
        label = ptlib.model_label(model)

    # --- session read/write tokens (live, straight from the payload) ---
    cw = payload.get("context_window") if isinstance(payload, dict) else None
    read_tok = write_tok = None
    if isinstance(cw, dict):
        read_tok = cw.get("total_input_tokens")
        write_tok = cw.get("total_output_tokens")

    # Fallback: derive from the transcript if the payload lacks the fields.
    if read_tok is None or write_tok is None:
        tpath = payload.get("transcript_path") if isinstance(payload, dict) else None
        usage = ptlib.session_usage_by_model(tpath)
        ri = sum(v["input"] for v in usage.values())
        wo = sum(v["output"] for v in usage.values())
        read_tok = ri if read_tok is None else read_tok
        write_tok = wo if write_tok is None else write_tok

    read_pg = ptlib.pages_from_tokens(read_tok or 0, cfg)
    write_pg = ptlib.pages_from_tokens(write_tok or 0, cfg)

    parts = [
        "📄 read {}pg".format(ptlib.fmt_pages(read_pg)),
        "wrote {}pg".format(ptlib.fmt_pages(write_pg)),
    ]

    # --- live file I/O pages from the hook log ---
    sid = payload.get("session_id") if isinstance(payload, dict) else None
    if sid:
        events = ptlib.read_io_events(sid)
        if events:
            io_words = sum(e.get("words", 0) or 0 for e in events)
            io_pg = ptlib.pages_from_words(io_words, cfg)
            parts.append("📂 {}pg I/O".format(ptlib.fmt_pages(io_pg)))

    if label and label != "unknown":
        parts.append("🤖 {}".format(label))

    print(" · ".join(parts))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("📄 paper-trail")
    sys.exit(0)
