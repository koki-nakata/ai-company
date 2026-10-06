#!/usr/bin/env python3
"""Patch today's task list when the cloud /task run read stale checklist state.

The cloud run decides carry-over from tasks/daily/_vault-state.md, which
pull-vault-state.yml refreshes from the Obsidian vault overnight. When GitHub
delays that job past the ~08:10 JST cloud run, the cloud run reads an older
note: tasks the user added to the previous day's note by hand are dropped, and
items they ticked come back unchecked (this happened on 2026-10-06).

This script repairs the already-generated note in place instead of
regenerating it, so anything the user has ticked in today's note since the
morning is preserved. It only acts on what the cloud run could not have known:

  seen   -- the _vault-state.md the cloud run actually read
  fresh  -- the _vault-state.md as it should have been (correct previous day)
  today  -- today's note in obsidian-tasks-sync (edited in place)

  * unchecked in fresh, absent from seen, absent from today  -> added to today
  * checked in fresh, not checked in seen                   -> ticked in today

Usage: repair_carryover.py SEEN FRESH TODAY
Prints a one-line summary; exits 0 whether or not anything changed.
"""
import re
import sys

CHECK_RE = re.compile(r"^(\s*)- \[(.)\] (.+)$")
# Lines that end the ✅ checklist block and start the rest of the note.
SECTION_END_RE = re.compile(r"^(#|📅|📌|📋|🎯|⏳|⚠️|💡|🔧)")
REPAIR_NOTE = "GitHub同期遅延のため自動補完"


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def key(text: str) -> str:
    """The stable head of a checklist line.

    The cloud run rewrites the parenthesised annotation every day (dates, status),
    but keeps the task name in front of it, so match on the part before the first
    bracket. Fall back to a fixed-length prefix if that leaves almost nothing.
    """
    head = re.split(r"[（(]", text, maxsplit=1)[0].strip()
    if len(head) < 4:
        head = text[:20]
    return norm(head)


def items(lines):
    """[(key, checked, text)] for every checklist line."""
    out = []
    for line in lines:
        m = CHECK_RE.match(line)
        if m:
            out.append((key(m.group(3)), m.group(2).strip() != "", m.group(3)))
    return out


def body(path):
    with open(path, encoding="utf-8") as f:
        return [l.rstrip("\n") for l in f if not l.startswith("<!-- ")]


def source_date(path):
    with open(path, encoding="utf-8") as f:
        m = re.search(r"(\d{4}-\d{2}-\d{2})\.md -->", f.readline())
    return m.group(1) if m else "?"


def main(seen_path, fresh_path, today_path):
    seen = {k: c for k, c, _ in items(body(seen_path))}
    fresh = items(body(fresh_path))
    with open(today_path, encoding="utf-8") as f:
        today = f.read().split("\n")
    today_norm = norm("\n".join(today))

    to_add = [t for k, c, t in fresh if not c and k not in seen and k not in today_norm]
    done_keys = [k for k, c, _ in fresh if c and not seen.get(k, False)]

    ticked = 0
    for i, line in enumerate(today):
        m = CHECK_RE.match(line)
        if m and m.group(2).strip() == "" and any(k in norm(m.group(3)) for k in done_keys):
            today[i] = f"{m.group(1)}- [x] {m.group(3)}"
            ticked += 1

    if to_add:
        # Insert under 🟡 (priority unknown for hand-written items), otherwise at
        # the end of the ✅ checklist block.
        start = next((i for i, l in enumerate(today) if "✅" in l), 0)
        end = next((i for i in range(start + 1, len(today)) if SECTION_END_RE.match(today[i])), len(today))
        yellow = next((i for i in range(start, end) if today[i].startswith("🟡")), None)
        at = None
        scan_from = yellow if yellow is not None else start
        for i in range(scan_from + 1, end):
            if CHECK_RE.match(today[i]):
                at = i + 1
            elif today[i].strip() and yellow is not None:
                break  # left the 🟡 group
        if at is None:
            at = (yellow + 1) if yellow is not None else end
        # Keep the line verbatim: it may carry the user's own hand-written edits.
        new = [f"- [ ] {t}（{REPAIR_NOTE}）" for t in to_add]
        today[at:at] = new

    if not to_add and not ticked:
        print("nothing to repair")
        return

    banner = (f"> 🔧 前日のチェック状態の同期がクラウド実行に間に合わなかったため、"
              f"{source_date(fresh_path)} のノートで自動補完しました"
              f"（追加 {len(to_add)} 件・完了反映 {ticked} 件）")
    first_quote = next((i for i, l in enumerate(today) if l.startswith("> ")), None)
    today.insert(first_quote + 1 if first_quote is not None else 0, banner)

    with open(today_path, "w", encoding="utf-8") as f:
        f.write("\n".join(today))
    print(f"repaired: added={len(to_add)} ticked={ticked}")
    for t in to_add:
        print(f"  + {t}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
