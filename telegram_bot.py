"""Telegram bot for Golf Agent.

Long polling only. The token and chat id come from the environment.
Live Anthropic calls happen only when GOLF_LIVE=1 in this process.
"""

import argparse
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import generate

DAILY_LIMIT = 30
LOG_PATH = Path(__file__).resolve().parent / "bot_log.jsonl"
CORPUS = [
    Path(__file__).resolve().parent / "golf-fault-corpus-v3.md",
    Path(__file__).resolve().parent / "golf-out-of-scope-entries.md",
]
START_TEXT = (
    "Describe a bad shot in your own words. "
    "I'll tell you what happened and what to try next time."
)
ERROR_TEXT = "Something went wrong, try again"
LIMIT_TEXT = "Daily limit reached"
NOTE_PROMPT = "What was off?"


def phone_text(row):
    """Plain answer for a phone screen. Entry tags and the sources line stay out."""
    if row.get("refused") or row.get("clarified"):
        return row["message"]
    advice = row["advice"]
    lines = [f"What happened: {advice['what_happened']}"]
    if advice.get("setup_steps"):
        lines.append("Before your next shot:")
        lines.extend(f"- {step['text']}" for step in advice["setup_steps"])
    headline = "Key thought" if str(advice.get("entry_id", ""))[:1] in ("S", "C") else "Swing thought"
    lines.append(f"{headline}: {advice['swing_thought']}")
    lines.append(f"Why: {advice['why']}")
    if advice.get("if_it_keeps_happening"):
        lines.append(f"If it keeps happening: {advice['if_it_keeps_happening']}")
    return "\n".join(lines)


def entries_used(row):
    advice = row.get("advice") or {}
    sources = advice.get("sources") or []
    if sources:
        return sources
    if row.get("entry_id"):
        return [row["entry_id"]]
    return list(row.get("retrieved") or [])


class GolfSession:
    """One chat. Uses generate.answer, so the checks stay in generate.py."""

    def __init__(self, chat_id, retriever, differentials, entry_ids, log_path=LOG_PATH, stub=None):
        self.chat_id = str(chat_id)
        self.retriever = retriever
        self.differentials = differentials
        self.entry_ids = entry_ids
        self.log_path = Path(log_path)
        self.stub = stub
        self.live_override = None
        self.pending_note_id = None

    def allows(self, chat_id):
        return str(chat_id) == self.chat_id

    def _live(self):
        if self.live_override is not None:
            return self.live_override
        return generate.live_enabled()

    def _read(self):
        if not self.log_path.exists():
            return []
        rows = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def _write(self, rows):
        text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        self.log_path.write_text(text, encoding="utf-8")

    def _append(self, row):
        rows = self._read()
        rows.append(row)
        self._write(rows)
        return row

    def _update(self, answer_id, **fields):
        rows = self._read()
        for row in rows:
            if row.get("id") == answer_id:
                row.update(fields)
                self._write(rows)
                return row
        return None

    def answers_today(self):
        today = datetime.now().astimezone().date().isoformat()
        count = 0
        for row in self._read():
            if not str(row.get("time", "")).startswith(today):
                continue
            if row.get("limited") or row.get("error"):
                continue
            if row.get("question"):
                count += 1
        return count

    def take_question(self, text):
        """Run one golfer message through the same answer path as generate.py."""
        if self.answers_today() >= DAILY_LIMIT:
            self._append({
                "id": uuid.uuid4().hex[:12],
                "time": datetime.now().astimezone().isoformat(timespec="seconds"),
                "question": text,
                "answer": LIMIT_TEXT,
                "entries": [],
                "cost": 0,
                "rating": None,
                "note": None,
                "limited": True,
            })
            return {"text": LIMIT_TEXT, "answer_id": None}

        calls = {"made": 0, "max": 25, "spend": 0.0}
        try:
            found = self.retriever.search(text)
            row = generate.answer(
                text, found, self.differentials, self.entry_ids,
                live=self._live(), stub=self.stub, calls=calls,
            )
        except (Exception, SystemExit) as exc:
            self._append({
                "id": uuid.uuid4().hex[:12],
                "time": datetime.now().astimezone().isoformat(timespec="seconds"),
                "question": text,
                "answer": ERROR_TEXT,
                "entries": [],
                "cost": 0,
                "rating": None,
                "note": None,
                "error": str(exc),
            })
            return {"text": ERROR_TEXT, "answer_id": None}

        answer_id = uuid.uuid4().hex[:12]
        shown = phone_text(row)
        self._append({
            "id": answer_id,
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "question": text,
            "answer": shown,
            "entries": entries_used(row),
            "retrieved": list(row.get("retrieved") or []),
            "sources": list((row.get("advice") or {}).get("sources") or []),
            "cost": round(calls.get("spend", 0.0), 6),
            "rating": None,
            "note": None,
        })
        buttons = not row.get("refused") and not row.get("clarified")
        return {"text": shown, "answer_id": answer_id if buttons else None}

    def rate(self, answer_id, rating):
        self._update(answer_id, rating=rating)
        if rating == "Not right":
            self.pending_note_id = answer_id
            return NOTE_PROMPT
        self.pending_note_id = None
        return None

    def save_note(self, text):
        answer_id = self.pending_note_id
        self.pending_note_id = None
        if answer_id:
            self._update(answer_id, note=text)
        return answer_id


def load_session(chat_id, log_path=LOG_PATH):
    corpus = [str(path) for path in CORPUS]
    retriever = generate.Retriever(corpus)
    entries = generate.parse_corpus(corpus)
    by_id = {entry["id"]: entry for entry in entries}
    return GolfSession(
        chat_id, retriever, generate.parse_differentials(corpus), list(by_id), log_path,
    )


def keyboard_for(answer_id):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Useful", callback_data=f"useful:{answer_id}"),
        InlineKeyboardButton("Not right", callback_data=f"not_right:{answer_id}"),
    ]])


async def on_start(update, context):
    session = context.bot_data["session"]
    if not session.allows(update.effective_chat.id):
        return
    await update.message.reply_text(START_TEXT)


async def on_text(update, context):
    session = context.bot_data["session"]
    if update.effective_chat is None or not session.allows(update.effective_chat.id):
        return
    if update.message is None or not update.message.text:
        return
    text = update.message.text.strip()
    if not text:
        return
    if session.pending_note_id:
        session.save_note(text)
        return
    result = session.take_question(text)
    markup = keyboard_for(result["answer_id"]) if result["answer_id"] else None
    await update.message.reply_text(result["text"], reply_markup=markup)


async def on_rating(update, context):
    session = context.bot_data["session"]
    query = update.callback_query
    if query is None or query.message is None or not session.allows(query.message.chat.id):
        return
    await query.answer()
    kind, _, answer_id = query.data.partition(":")
    rating = "Useful" if kind == "useful" else "Not right"
    reply = session.rate(answer_id, rating)
    if reply:
        await query.message.reply_text(reply)


def build_app(token, session):
    from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
    app = Application.builder().token(token).build()
    app.bot_data["session"] = session
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(CallbackQueryHandler(on_rating))
    return app


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID. No call was made.")
    session = load_session(chat_id)
    build_app(token, session).run_polling()


def run_offline_test():
    """Fake Telegram messages through the replay stub. No network calls."""
    import asyncio
    import tempfile

    entry = {
        "id": "F008",
        "name": "Thin",
        "text": (
            "**What it is:** Contact above the ball's middle.\n\n"
            "**Fixes**\n- Feel the clubhead brushing the ground after the ball.\n"
            "- Same as F009.\n\n**Evidence tier:** settled\n\n"
            "**Compensation risk:** This note must not reach the model.\n"
        ),
    }
    result = {
        "ids": ["F008"],
        "entries": [entry],
        "top_dense_sim": 0.5,
        "scores": {"F008": 0.01},
    }

    def stub(_payload, tool_name):
        if tool_name == "rewrite_field":
            return {"text": "The club met the ball above its middle."}
        return {
            "what_happened": "The club caught the ball above its middle.",
            "entry_id": "F008",
            "setup_steps": [{
                "entry_id": "F008",
                "fix_index": 0,
                "text": "Feel the clubhead brushing the ground after the ball.",
            }],
            "swing_thought": "Brush the ground just after the ball.",
            "why": (
                "The club met the ball too high \u2014 and this sentence keeps going with extra "
                "words about the strike, the loft, the hands, the ground and the follow through "
                "so the word limit forces one targeted repair."
            ),
        }

    class FakeChat:
        def __init__(self, chat_id):
            self.id = chat_id

    class FakeMessage:
        def __init__(self, text, chat_id):
            self.text = text
            self.chat = FakeChat(chat_id)
            self.replies = []

        async def reply_text(self, text, reply_markup=None):
            self.replies.append({"text": text, "markup": reply_markup})

    class FakeUpdate:
        def __init__(self, text, chat_id):
            self.message = FakeMessage(text, chat_id)
            self.effective_chat = self.message.chat
            self.callback_query = None

    class FakeQuery:
        def __init__(self, data, chat_id):
            self.data = data
            self.message = FakeMessage("", chat_id)
            self.answered = False

        async def answer(self):
            self.answered = True

    class FakeCallbackUpdate:
        def __init__(self, data, chat_id):
            self.callback_query = FakeQuery(data, chat_id)
            self.effective_chat = self.callback_query.message.chat
            self.message = None

    class Context:
        def __init__(self, session):
            self.bot_data = {"session": session}

    class Retriever:
        def search(self, _query):
            return result

    log_path = Path(tempfile.mkdtemp()) / "bot_log.jsonl"
    session = GolfSession("42", Retriever(), {}, ["F008"], log_path=log_path, stub=stub)
    session.live_override = False
    context = Context(session)

    update = FakeUpdate("stub query", 42)
    asyncio.run(on_text(update, context))
    reply = update.message.replies[0]
    assert "What happened:" in reply["text"]
    assert "Feel the clubhead brushing the ground after the ball." in reply["text"]
    assert "The club met the ball above its middle." in reply["text"]
    assert "Sources" not in reply["text"]
    assert "[F008]" not in reply["text"]
    assert reply["markup"] is not None
    logged = session._read()[0]
    assert logged["entries"] == ["F008"]
    assert logged["sources"] == ["F008"]
    assert logged["cost"] == 0
    assert logged["rating"] is None

    stranger = FakeUpdate("another shot", 99)
    asyncio.run(on_text(stranger, context))
    assert stranger.message.replies == []

    answer_id = logged["id"]
    useful = FakeCallbackUpdate(f"useful:{answer_id}", 42)
    asyncio.run(on_rating(useful, context))
    assert useful.callback_query.answered
    assert session._read()[0]["rating"] == "Useful"

    second = FakeUpdate("thin again", 42)
    asyncio.run(on_text(second, context))
    second_id = session._read()[1]["id"]
    not_right = FakeCallbackUpdate(f"not_right:{second_id}", 42)
    asyncio.run(on_rating(not_right, context))
    assert not_right.callback_query.message.replies[0]["text"] == NOTE_PROMPT
    note = FakeUpdate("the setup step was the wrong club", 42)
    asyncio.run(on_text(note, context))
    assert note.message.replies == []
    saved = session._read()[1]
    assert saved["rating"] == "Not right"
    assert saved["note"] == "the setup step was the wrong club"

    start = FakeUpdate("/start", 42)
    asyncio.run(on_start(start, context))
    assert start.message.replies[0]["text"] == START_TEXT

    def boom(_payload, tool_name):
        raise RuntimeError("api down")

    session.stub = boom
    failed = FakeUpdate("this one fails", 42)
    asyncio.run(on_text(failed, context))
    assert failed.message.replies[0]["text"] == ERROR_TEXT
    assert "api down" in session._read()[-1]["error"]

    session.stub = None
    missed = FakeUpdate("cache miss must not call out", 42)
    asyncio.run(on_text(missed, context))
    assert missed.message.replies[0]["text"] == ERROR_TEXT
    assert "No Anthropic call was made" in session._read()[-1]["error"]

    session.stub = stub
    rows = session._read()
    questions = [row for row in rows if row.get("question") and not row.get("error") and not row.get("limited")]
    for index in range(DAILY_LIMIT - len(questions)):
        session._append({
            "id": f"seed{index}",
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "question": f"seed {index}",
            "answer": "seed",
            "entries": [],
            "cost": 0,
            "rating": None,
            "note": None,
        })
    blocked = FakeUpdate("one more", 42)
    asyncio.run(on_text(blocked, context))
    assert blocked.message.replies[0]["text"] == LIMIT_TEXT
    print("Telegram bot offline test passed: stub answer, buttons, note, limit, no API call.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test:
        run_offline_test()
    else:
        main()
