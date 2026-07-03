"""JSON file-based player persistence. One file per character, keyed by
lowercased name. Each save includes a salted password hash (see game/auth.py)
checked at login time in main.py. This is still a demo-grade store --
fine for a single-user or trusted-group prototype, not a hardened production
auth system."""
from __future__ import annotations
import json
import os
import re
from .models import Player

PLAYERS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "players")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{1,15}$")


def is_valid_name(name: str) -> bool:
    return bool(NAME_RE.match(name or ""))


def _path_for(name: str) -> str:
    safe = name.strip().lower()
    return os.path.join(PLAYERS_DIR, f"{safe}.json")


def exists(name: str) -> bool:
    return os.path.isfile(_path_for(name))


def load(name: str) -> Player | None:
    path = _path_for(name)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Player.from_dict(data)


def save(player: Player) -> None:
    os.makedirs(PLAYERS_DIR, exist_ok=True)
    path = _path_for(player.name)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(player.to_dict(), f, indent=2)
    os.replace(tmp_path, path)


def list_players() -> list[str]:
    """Return sorted list of all saved character names (lowercase)."""
    if not os.path.isdir(PLAYERS_DIR):
        return []
    return sorted(
        fname[:-5] for fname in os.listdir(PLAYERS_DIR)
        if fname.endswith(".json") and not fname.endswith(".tmp")
    )


def delete_player(name: str) -> bool:
    """Delete a player's save file. Returns True if deleted, False if not found."""
    path = _path_for(name)
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


# ---------------------------------------------------------------------------
# Server configuration (player cap, registration lock)
# ---------------------------------------------------------------------------

SERVER_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "server_config.json"
)


def _load_server_config() -> dict:
    if os.path.isfile(SERVER_CONFIG_PATH):
        with open(SERVER_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"max_players": 0, "registration_locked": False}


def _save_server_config(cfg: dict) -> None:
    os.makedirs(os.path.dirname(SERVER_CONFIG_PATH), exist_ok=True)
    tmp = SERVER_CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, SERVER_CONFIG_PATH)


def get_max_players() -> int:
    """Return the player cap. 0 = unlimited."""
    return int(_load_server_config().get("max_players", 0))


def set_max_players(n: int) -> None:
    """Set the player cap. 0 = unlimited."""
    cfg = _load_server_config()
    cfg["max_players"] = n
    _save_server_config(cfg)


def is_registration_locked() -> bool:
    """Return True if new account creation is blocked."""
    return bool(_load_server_config().get("registration_locked", False))


def set_registration_locked(locked: bool) -> None:
    """Block or allow new account creation."""
    cfg = _load_server_config()
    cfg["registration_locked"] = locked
    _save_server_config(cfg)


# ---------------------------------------------------------------------------
# Login history
# ---------------------------------------------------------------------------

LOGIN_HISTORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "login_history.json"
)
DEFAULT_HISTORY_SIZE = 200


def _load_login_history_data() -> dict:
    if os.path.isfile(LOGIN_HISTORY_PATH):
        with open(LOGIN_HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"max_size": DEFAULT_HISTORY_SIZE, "entries": []}


def _save_login_history_data(data: dict) -> None:
    os.makedirs(os.path.dirname(LOGIN_HISTORY_PATH), exist_ok=True)
    tmp = LOGIN_HISTORY_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, LOGIN_HISTORY_PATH)


def record_login(name: str, ip: str, action: str = "login") -> None:
    """Record a login or registration event. action is 'login' or 'register'."""
    import time
    data = _load_login_history_data()
    data["entries"].append({
        "name": name,
        "time": int(time.time()),
        "action": action,
        "ip": ip or "unknown",
    })
    max_size = int(data.get("max_size", DEFAULT_HISTORY_SIZE))
    if max_size > 0:
        data["entries"] = data["entries"][-max_size:]
    _save_login_history_data(data)


def get_login_history(limit: int | None = None) -> list[dict]:
    """Return login entries newest-first. limit caps the result count."""
    data = _load_login_history_data()
    entries = list(reversed(data.get("entries", [])))
    if limit is not None:
        entries = entries[:limit]
    return entries


def get_login_history_size() -> int:
    """Return the configured max history size (0 = unlimited)."""
    return int(_load_login_history_data().get("max_size", DEFAULT_HISTORY_SIZE))


def set_login_history_size(n: int) -> None:
    """Set max history size and trim existing entries if needed."""
    data = _load_login_history_data()
    data["max_size"] = n
    if n > 0:
        data["entries"] = data["entries"][-n:]
    _save_login_history_data(data)
