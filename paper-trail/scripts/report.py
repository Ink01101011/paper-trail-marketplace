#!/usr/bin/env python3
"""paper-trail report -- the engine behind /pages.

Prints a per-model breakdown of how much Claude read and wrote in a session,
in pages, from two independent streams:

  - Session tokens : input_tokens (read) / output_tokens (written) from the
                     transcript usage records.
  - File I/O       : real text moved by Read / Write / Edit, from the hook log.

Usage:
  report.py                          # auto-detect newest transcript + session
  report.py --transcript PATH        # use a specific transcript
  report.py --session SESSION_ID     # use a specific file I/O log
  report.py --json                   # machine-readable output
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ptlib


def session_id_from_transcript(path):
    if not path:
        return None
    base = os.path.basename(path)
    if base.endswith(".jsonl"):
        return base[:-6]
    return base


def build(transcript_path, session_id, cfg):
    usage = ptlib.session_usage_by_model(transcript_path)
    events = ptlib.read_io_events(session_id) if session_id else []

    # ---- session tokens per model ----
    models = {}
    for model_id, u in usage.items():
        label = ptlib.model_label(model_id)
        m = models.setdefault(label, _blank())
        m["session_read_tokens"] += u["input"]
        m["session_cache_read_tokens"] += u.get("cache_read", 0)
        m["session_write_tokens"] += u["output"]

    # ---- file I/O per model ----
    for e in events:
        label = ptlib.model_label(e.get("model"))
        m = models.setdefault(label, _blank())
        if e.get("direction") == "read":
            m["io_read_words"] += e.get("words", 0) or 0
            m["io_read_files"] += 1
        elif e.get("direction") == "write":
            m["io_write_words"] += e.get("words", 0) or 0
            m["io_write_files"] += 1

    # ---- convert to pages ----
    for m in models.values():
        m["session_read_pages"] = ptlib.pages_from_tokens(m["session_read_tokens"], cfg)
        m["session_write_pages"] = ptlib.pages_from_tokens(m["session_write_tokens"], cfg)
        m["io_read_pages"] = ptlib.pages_from_words(m["io_read_words"], cfg)
        m["io_write_pages"] = ptlib.pages_from_words(m["io_write_words"], cfg)

    return models


def _blank():
    return {
        "session_read_tokens": 0, "session_cache_read_tokens": 0,
        "session_write_tokens": 0,
        "io_read_words": 0, "io_write_words": 0,
        "io_read_files": 0, "io_write_files": 0,
    }


def render_text(models, cfg, transcript_path, session_id):
    fp = ptlib.fmt_pages
    wpp = cfg["words_per_page"]
    tpp = (wpp / cfg["words_per_token"]) if cfg["words_per_token"] else wpp

    lines = []
    lines.append("📄  PAPER TRAIL — session page report")
    lines.append("=" * 52)
    lines.append("conversion: {:.0f} words/page  (~{:.0f} tokens/page)".format(wpp, tpp))
    lines.append("")

    if not models:
        lines.append("No activity found yet for this session.")
        lines.append("(transcript: {})".format(transcript_path or "not found"))
        return "\n".join(lines)

    tot = _blank()
    tot_pages = {"sr": 0.0, "sw": 0.0, "ir": 0.0, "iw": 0.0}

    for label in sorted(models.keys()):
        m = models[label]
        lines.append("🤖 {}".format(label))
        lines.append("   Session tokens")
        lines.append("      read  : {:>9}pg   ({:,} tokens)".format(
            fp(m["session_read_pages"]), m["session_read_tokens"]))
        if m["session_cache_read_tokens"]:
            lines.append("              (+{:,} cached re-read tokens, not counted)".format(
                m["session_cache_read_tokens"]))
        lines.append("      wrote : {:>9}pg   ({:,} tokens)".format(
            fp(m["session_write_pages"]), m["session_write_tokens"]))
        lines.append("   File I/O")
        lines.append("      read  : {:>9}pg   ({:,} words, {} files)".format(
            fp(m["io_read_pages"]), m["io_read_words"], m["io_read_files"]))
        lines.append("      wrote : {:>9}pg   ({:,} words, {} files)".format(
            fp(m["io_write_pages"]), m["io_write_words"], m["io_write_files"]))
        lines.append("")

        for k in tot:
            tot[k] += m[k]
        tot_pages["sr"] += m["session_read_pages"]
        tot_pages["sw"] += m["session_write_pages"]
        tot_pages["ir"] += m["io_read_pages"]
        tot_pages["iw"] += m["io_write_pages"]

    lines.append("-" * 52)
    lines.append("TOTAL")
    lines.append("   Session : read {}pg · wrote {}pg".format(
        fp(tot_pages["sr"]), fp(tot_pages["sw"])))
    lines.append("   File I/O : read {}pg · wrote {}pg".format(
        fp(tot_pages["ir"]), fp(tot_pages["iw"])))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript")
    ap.add_argument("--session")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg = ptlib.load_config()

    # Resolve the transcript for *this* session: an explicit --session wins,
    # then --transcript, then the newest transcript whose recorded cwd matches
    # the current directory, and only as a last resort the globally-newest one.
    if args.session:
        transcript_path = args.transcript or ptlib.find_transcript_by_session(args.session) \
            or ptlib.latest_transcript_for_cwd() or ptlib.latest_transcript()
    else:
        transcript_path = args.transcript or ptlib.latest_transcript_for_cwd() \
            or ptlib.latest_transcript()
    session_id = args.session or session_id_from_transcript(transcript_path)

    models = build(transcript_path, session_id, cfg)

    if args.json:
        print(json.dumps({
            "config": cfg,
            "transcript": transcript_path,
            "session_id": session_id,
            "models": models,
        }, indent=2))
    else:
        print(render_text(models, cfg, transcript_path, session_id))


if __name__ == "__main__":
    main()
