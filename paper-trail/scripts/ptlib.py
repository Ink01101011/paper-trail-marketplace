"""paper-trail shared library.

Conversion model, config loading, transcript parsing, and the per-session
file I/O log. Everything here is dependency-free (Python 3 stdlib only) and
written to never raise into a caller that cannot handle it.

Units
-----
We track two independent streams, exactly as configured:

  1. File I/O   -> what Claude's Read/Write/Edit tools moved on disk.
                   We have the real text, so we count words directly.
  2. Session    -> input_tokens (read) and output_tokens (written) reported
                   by the model in the transcript usage records.

Both are converted to "pages" through one knob, words_per_page:

  pages_from_words(w)  = w / words_per_page
  pages_from_tokens(t) = (t * words_per_token) / words_per_page

words_per_token defaults to 0.75 (~1 token ~= 0.75 English words), so at the
default 250 words/page a page is ~333 tokens.
"""

import json
import os
import glob

DEFAULT_CONFIG = {
    "words_per_page": 250,    # manuscript page (double-spaced, ~250 words)
    "words_per_token": 0.75,  # 1 token ~= 0.75 words
    "chars_per_token": 4,     # fallback estimate when only chars are known
}


def data_dir():
    base = os.environ.get("PAPER_TRAIL_HOME") or os.path.join(
        os.path.expanduser("~"), ".claude", "paper-trail"
    )
    return base


def sessions_dir():
    return os.path.join(data_dir(), "sessions")


def config_path():
    return os.path.join(data_dir(), "config.json")


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(config_path(), "r", encoding="utf-8") as fh:
            user = json.load(fh)
        if isinstance(user, dict):
            for k in DEFAULT_CONFIG:
                if k in user and isinstance(user[k], (int, float)) and user[k] > 0:
                    cfg[k] = user[k]
    except Exception:
        pass
    return cfg


def ensure_config_file():
    """Write a default config.json the first time so users have a knob to edit."""
    try:
        os.makedirs(data_dir(), exist_ok=True)
        if not os.path.exists(config_path()):
            with open(config_path(), "w", encoding="utf-8") as fh:
                json.dump(DEFAULT_CONFIG, fh, indent=2)
    except Exception:
        pass


# ---- conversion ----------------------------------------------------------

def count_words(text):
    if not text:
        return 0
    return len(text.split())


def est_tokens_from_text(text, cfg):
    if not text:
        return 0
    cpt = cfg.get("chars_per_token", 4) or 4
    return int(round(len(text) / cpt))


def pages_from_words(words, cfg):
    wpp = cfg.get("words_per_page", 250) or 250
    return words / wpp


def pages_from_tokens(tokens, cfg):
    wpp = cfg.get("words_per_page", 250) or 250
    wpt = cfg.get("words_per_token", 0.75) or 0.75
    return (tokens * wpt) / wpp


def fmt_pages(p):
    if p >= 100:
        return "{:.0f}".format(p)
    if p >= 10:
        return "{:.1f}".format(p)
    return "{:.2f}".format(p)


# ---- per-session file I/O log -------------------------------------------

def log_path(session_id):
    sid = session_id or "unknown"
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(sid))
    return os.path.join(sessions_dir(), safe + ".jsonl")


def append_io_event(session_id, record):
    try:
        os.makedirs(sessions_dir(), exist_ok=True)
        with open(log_path(session_id), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:
        pass


def read_io_events(session_id):
    events = []
    try:
        with open(log_path(session_id), "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass
    return events


# ---- transcript parsing --------------------------------------------------

def model_label(model_id):
    """Map a raw model id to a friendly label. Best-effort, never fails."""
    if not model_id:
        return "unknown"
    m = str(model_id).lower()
    table = [
        ("opus-4-8", "Opus 4.8"), ("opus-4-6", "Opus 4.6"),
        ("opus-4-1", "Opus 4.1"), ("opus-4", "Opus 4"),
        ("sonnet-4-6", "Sonnet 4.6"), ("sonnet-4-5", "Sonnet 4.5"),
        ("sonnet-4", "Sonnet 4"),
        ("haiku-4-5", "Haiku 4.5"), ("haiku-4", "Haiku 4"),
        ("3-7-sonnet", "Sonnet 3.7"), ("3-5-sonnet", "Sonnet 3.5"),
        ("3-5-haiku", "Haiku 3.5"), ("3-opus", "Opus 3"),
    ]
    for key, label in table:
        if key in m:
            return label
    return str(model_id)


def latest_transcript():
    """Most-recently-modified transcript JSONL under ~/.claude/projects/."""
    roots = [
        os.path.join(os.path.expanduser("~"), ".claude", "projects"),
        os.path.join(os.path.expanduser("~"), ".config", "claude", "projects"),
    ]
    best = None
    best_mtime = -1
    for root in roots:
        for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
            try:
                mt = os.path.getmtime(path)
            except Exception:
                continue
            if mt > best_mtime:
                best_mtime, best = mt, path
    return best


def last_model_in_transcript(transcript_path):
    """Scan from the end for the most recent assistant model id."""
    if not transcript_path or not os.path.exists(transcript_path):
        return None
    try:
        with open(transcript_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except Exception:
        return None
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        msg = obj.get("message") if isinstance(obj, dict) else None
        if isinstance(msg, dict) and msg.get("model"):
            return msg.get("model")
    return None


def session_usage_by_model(transcript_path):
    """Sum input/output tokens per model id across a transcript.

    Returns: { model_id: {"input": int, "output": int} }
    input  ~= tokens the model read   (prompt, incl. cache reads)
    output ~= tokens the model wrote  (completion)
    """
    out = {}
    if not transcript_path or not os.path.exists(transcript_path):
        return out
    try:
        with open(transcript_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except Exception:
        return out
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        usage = msg.get("usage")
        if not isinstance(usage, dict):
            continue
        model = msg.get("model") or "unknown"
        bucket = out.setdefault(model, {"input": 0, "output": 0})
        inp = (usage.get("input_tokens", 0) or 0) \
            + (usage.get("cache_read_input_tokens", 0) or 0) \
            + (usage.get("cache_creation_input_tokens", 0) or 0)
        bucket["input"] += int(inp)
        bucket["output"] += int(usage.get("output_tokens", 0) or 0)
    return out
