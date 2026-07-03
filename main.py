"""
Saltspire MUD -- a small browser-playable MUD in the style of classic
Diku/Merc/ROM-derived games (the lineage the real Waterdeep MUD comes from).

Run with:  uvicorn main:app --host 0.0.0.0 --port 8000
Then open: http://localhost:8000/
"""
from __future__ import annotations
import asyncio
import os

# Load .env for local development (no-op if file absent or python-dotenv not installed)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from game import auth
from game import colors as c
from game import persistence
from game.commands import CommandContext, dispatch, QuitRequested
from game.engine import GameEngine
from game.models import Player, RACE_MODS, CLASS_INFO
from game.world import World

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(title="Saltspire MUD")
world = World()
engine = GameEngine(world)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

RACES = list(RACE_MODS.keys())
CLASSES = list(CLASS_INFO.keys())
MAX_LOGIN_ATTEMPTS = 5

# Sent before/after a password prompt so the browser client can swap the
# input box to type="password" and avoid echoing it into the scrollback.
CTRL_PREFIX = "\x00CTRL\x00"

_FALLBACK_BANNER = (
    "================================================<br>"
    "&nbsp;&nbsp;SALTSPIRE &mdash; a small browser MUD<br>"
    "&nbsp;&nbsp;(in the style of classic Diku/Merc/ROM MUDs)<br>"
    "================================================<br>"
)


def _load_banner() -> str:
    """Load banner.txt from the project root and wrap in <pre> so ASCII art
    whitespace is preserved.  Falls back to a plain text banner if the file
    is missing or unreadable."""
    banner_path = os.path.join(BASE_DIR, "banner.txt")
    try:
        with open(banner_path, "r") as fh:
            return "<pre>" + fh.read() + "</pre>"
    except OSError:
        return _FALLBACK_BANNER


BANNER = _load_banner()


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "players_online": len(engine.players)})


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(engine.tick_loop())


async def ask(websocket: WebSocket, prompt: str) -> str:
    await websocket.send_text(c.help_(prompt))
    raw = await websocket.receive_text()
    return raw.strip()


async def ask_secret(websocket: WebSocket, prompt: str) -> str:
    """Like ask(), but tells the client to mask the input box while typing."""
    await websocket.send_text(CTRL_PREFIX + "PASSWORD_ON")
    try:
        await websocket.send_text(c.help_(prompt))
        raw = await websocket.receive_text()
        return raw.strip()
    finally:
        try:
            await websocket.send_text(CTRL_PREFIX + "PASSWORD_OFF")
        except Exception:
            pass


async def choose_from(websocket: WebSocket, prompt: str, options: list) -> str:
    opts_line = ", ".join(options)
    while True:
        answer = (await ask(websocket, f"{prompt} ({opts_line}):")).lower()
        if answer in options:
            return answer
        await websocket.send_text(c.error(f"Please choose one of: {opts_line}"))


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text(BANNER)

    player = None
    failed_attempts = {}  # name.lower() -> count, scoped to this connection only
    try:
        while player is None:
            name = await ask(websocket, "What is your name, traveler?")
            if not persistence.is_valid_name(name):
                await websocket.send_text(c.error(
                    "Names must be 2-16 letters/numbers/underscores, starting with a letter."))
                continue
            if engine.is_online(name):
                await websocket.send_text(c.error("That character is already adventuring. Try another name."))
                continue

            existing = persistence.load(name)
            if existing:
                if not existing.password_hash:
                    await websocket.send_text(c.system(
                        f"'{name}' has no password set yet. Set one now to secure this character."))
                    pw1 = await ask_secret(websocket, "New password (4-64 characters):")
                    if not auth.is_valid_password(pw1):
                        await websocket.send_text(c.error("Password must be 4-64 characters. Try again."))
                        continue
                    pw2 = await ask_secret(websocket, "Confirm password:")
                    if pw1 != pw2:
                        await websocket.send_text(c.error("Passwords didn't match. Try again."))
                        continue
                    existing.password_hash, existing.password_salt = auth.hash_password(pw1)
                    persistence.save(existing)
                    player = existing
                    await websocket.send_text(c.system(f"Password set. Welcome back, {name}."))
                else:
                    pw = await ask_secret(websocket, "Password:")
                    if auth.verify_password(pw, existing.password_salt, existing.password_hash):
                        player = existing
                        await websocket.send_text(c.system(f"Welcome back, {name}."))
                    else:
                        key = name.lower()
                        failed_attempts[key] = failed_attempts.get(key, 0) + 1
                        if failed_attempts[key] >= MAX_LOGIN_ATTEMPTS:
                            await websocket.send_text(c.error("Too many failed attempts. Disconnecting."))
                            await websocket.close()
                            return
                        await websocket.send_text(c.error(
                            f"Incorrect password. ({failed_attempts[key]}/{MAX_LOGIN_ATTEMPTS} attempts)"))
                        continue
            else:
                if persistence.is_registration_locked():
                    await websocket.send_text(c.error(
                        "New account creation is currently disabled by the administrator."))
                    continue
                max_p = persistence.get_max_players()
                if max_p > 0 and len(persistence.list_players()) >= max_p:
                    await websocket.send_text(c.error(
                        f"The server has reached its player limit ({max_p}). "
                        "No new accounts can be created at this time."))
                    continue
                confirm = await ask(
                    websocket, f"'{name}' is unknown. Create a new character with that name? (yes/no)")
                if confirm.lower() not in ("y", "yes"):
                    continue
                race = await choose_from(websocket, "Choose a race", RACES)
                klass = await choose_from(websocket, "Choose a class", CLASSES)

                pw1 = await ask_secret(websocket, "Choose a password (4-64 characters):")
                if not auth.is_valid_password(pw1):
                    await websocket.send_text(c.error(
                        "Password must be 4-64 characters. Type your name again to restart."))
                    continue
                pw2 = await ask_secret(websocket, "Confirm password:")
                if pw1 != pw2:
                    await websocket.send_text(c.error(
                        "Passwords didn't match. Type your name again to restart."))
                    continue
                pw_hash, pw_salt = auth.hash_password(pw1)

                player = Player.new_character(name, race, klass, password_hash=pw_hash, password_salt=pw_salt)
                persistence.save(player)
                await websocket.send_text(c.system(
                    f"Welcome, {name} the {race} {klass}! You awaken in The Rusty Anchor."))

        engine.connect_player(player, websocket)
        ctx = CommandContext(engine, player)
        await engine.send_room(player.room_id, c.system(f"{player.name} arrives."), exclude_names=(player.name,))
        await dispatch(ctx, "look")

        while True:
            raw = await websocket.receive_text()
            try:
                await dispatch(ctx, raw)
            except QuitRequested:
                break

    except WebSocketDisconnect:
        pass
    except QuitRequested:
        pass
    finally:
        if player is not None:
            room_id = player.room_id
            engine.disconnect_player(player)
            try:
                await engine.send_room(room_id, c.system(f"{player.name} leaves the realm."),
                                        exclude_names=(player.name,))
            except Exception:
                pass
        try:
            await websocket.close()
        except Exception:
            pass
