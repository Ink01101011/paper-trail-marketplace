#!/usr/bin/env python3
"""PostToolUse hook: log a file I/O event whenever Claude reads or writes.

Reads the hook payload from stdin, figures out how much text moved and in
which direction, attributes it to the model active in the transcript, and
appends one JSON line to the session's log. ALWAYS exits 0 so a failure here
can never interfere with Claude's normal operation.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import ptlib
except Exception:
    sys.exit(0)


def read_tool_text(tool_name, tool_input, tool_response):
    """Return (direction, text) for the relevant tool, or (None, '')."""
    ti = tool_input if isinstance(tool_input, dict) else {}

    if tool_name == "Read":
        # Prefer the actual response text (honours offset/limit); fall back
        # to reading the file from disk.
        text = _coerce_text(tool_response)
        if not text:
            fp = ti.get("file_path")
            if fp and os.path.exists(fp):
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                        text = fh.read()
                except Exception:
                    text = ""
        return "read", text or ""

    if tool_name == "Write":
        return "write", ti.get("content", "") or ""

    if tool_name == "Edit":
        return "write", ti.get("new_string", "") or ""

    if tool_name == "MultiEdit":
        edits = ti.get("edits", [])
        parts = []
        if isinstance(edits, list):
            for e in edits:
                if isinstance(e, dict):
                    parts.append(e.get("new_string", "") or "")
        return "write", "".join(parts)

    if tool_name == "NotebookEdit":
        return "write", ti.get("new_source", "") or ""

    return None, ""


def _coerce_text(resp):
    """Pull human text out of a Read tool_response of unknown shape."""
    if resp is None:
        return ""
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict):
        for key in ("content", "text", "output", "fileContents"):
            v = resp.get(key)
            if isinstance(v, str):
                return v
        f = resp.get("file")
        if isinstance(f, dict):
            for key in ("content", "text"):
                v = f.get(key)
                if isinstance(v, str):
                    return v
    return ""


def main():
    raw = sys.stdin.read()
    if not raw:
        return
    try:
        payload = json.loads(raw)
    except Exception:
        return
    if not isinstance(payload, dict):
        return

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Read", "Write", "Edit", "MultiEdit", "NotebookEdit"):
        return

    session_id = payload.get("session_id") or "unknown"
    transcript_path = payload.get("transcript_path")
    tool_input = payload.get("tool_input", {})
    tool_response = payload.get("tool_response", payload.get("tool_output"))

    direction, text = read_tool_text(tool_name, tool_input, tool_response)
    if direction is None:
        return

    ptlib.ensure_config_file()
    ptlib.ensure_statusline_launcher()

    model = ptlib.last_model_in_transcript(transcript_path) or "unknown"
    fp = tool_input.get("file_path") if isinstance(tool_input, dict) else None

    record = {
        "ts": time.time(),
        "tool": tool_name,
        "direction": direction,            # "read" or "write"
        "model": model,
        "file": fp,
        "chars": len(text),
        "words": ptlib.count_words(text),
    }
    ptlib.append_io_event(session_id, record)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
