# Saltspire MUD

A small, browser-playable MUD (Multi-User Dungeon) in the style of classic Diku/Merc/ROM-derived games — the same codebase lineage the real Waterdeep ("City of Splendors") MUD is built on. Players connect from a browser over WebSockets to a green-on-black terminal and play entirely with typed text commands.

## About the setting

The real Waterdeep MUD runs on a proprietary codebase and uses Wizards of the Coast's Forgotten Realms IP — it isn't open source and its specific names, lore, and text can't legally be reused. Saltspire borrows the *genre conventions* of that era of MUD (rooms, exits, mobs, shops, levels, classes) but uses an entirely original setting: a port town called Saltspire, with its own map, monsters, and item names. Nothing here is copied from Waterdeep or any Forgotten Realms material.

## Features

- 20 connected rooms across three areas: the town of Saltspire, the sewers beneath it, and the coast road north of the gate
- 4 races (human, elf, dwarf, halfling) and 4 classes (warrior, mage, cleric, rogue), each with their own stats, HP/mana curve, and starting gear
- Real-time tick-based combat (server resolves a round every 2 seconds), plus instant special attacks: `bash` (warrior), `backstab` (rogue), and spells (`cast missile`, `cast heal`)
- 6 monster types with levels, loot tables, gold/XP rewards, and timed respawns
- Shops (buy/sell), a healer you can `pray` to, and a locked chest that needs a key
- Leveling, persistent characters (JSON file per player), say/emote/shout/who
- A minimal vanilla-JS browser terminal frontend — no build step, no frameworks
- Password-protected logins (salted PBKDF2 hashes, no plaintext anywhere) with a self-service `changepass`, and an admin role that can reset anyone's password and build new rooms in-game without hand-editing `data/world.json`

## Requirements

- Python 3.10+

## Quick start

```bash
cd saltspire-mud
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000/** in a browser. Type a character name:

- **New name** → confirm, pick a race and class, then choose a password (4-64 characters, masked in the input box).
- **Existing name** → enter your password. Five wrong attempts in a row disconnects you.
- **Existing name with no password yet** (e.g. one of the sample characters below, or any save from before this feature existed) → you'll be asked to set one on the spot; nobody is locked out.

Type `help` once you're in.

## How to play

Movement: `north`/`south`/`east`/`west`/`up`/`down` (or `n`/`s`/`e`/`w`/`u`/`d`)

| Command | Effect |
|---|---|
| `look [target]` | Look at the room, or examine a mob/player/item |
| `score`, `inventory` (`i`), `equipment` (`eq`) | Check your character |
| `say <msg>`, `emote <action>`, `shout <msg>`, `who` | Talk to other players |
| `get <item>`, `drop <item>`, `wear <item>`, `remove <item>` | Manage items |
| `kill <target>`, `flee`, `rest`, `wake` | Combat basics |
| `cast missile <target>` (mage), `cast heal [target]` (cleric) | Spells, cost mana |
| `bash <target>` (warrior), `backstab <target>` (rogue) | Class specials, no mana cost |
| `list`, `buy <item>`, `sell <item>` | Shop in town |
| `pray` | Full heal at the Temple of the Dawn, for a small donation |
| `open chest` | Open containers where present (some need a key) |
| `changepass <old> <new>` | Change your own password |
| `help`, `quit` | Help text; saves and disconnects |

Combat is room-gated: you can only `kill` something in a room marked unsafe, and you can't leave a room while fighting (use `flee` instead). Once a fight starts, the server resolves a round every couple of seconds until one side dies, you flee, or the mob is already dead.

A rough map: the **Rusty Anchor** tavern is the spawn point and hub, with the **Market Square** (blacksmith, general store, High Ward) to the north, the **Harbor Docks** to the east (harbormaster, fish market, and a sewer entrance leading to rats, goblins, and a goblin brute guarding a locked chest), and **Temple Row**/the **Guildhall** rounding out the town. Past the **Coast Gate**, the **Coast Road** leads to a wolf den and a bandit camp (with a tougher bandit leader) for higher-level fights.

## Admin role & building rooms in-game

Characters with `is_admin: true` get an extra set of commands (shown in their own `help` block) for account recovery and for extending the map without ever hand-editing `data/world.json`.

**Bootstrapping the first admin.** Nobody can grant admin in-game until at least one admin already exists, so create the first one from the server's shell (not in the browser):

```bash
python3 create_admin.py <name> <password> [race] [klass]
# e.g.
python3 create_admin.py Admin adminpass123
```

If `<name>` doesn't exist yet, this creates it (race/klass default to human/warrior) and marks it admin. If it already exists, this resets its password and grants admin without touching anything else — so it's also how you recover a lost admin password. Safe to re-run any time.

**Account commands** (admin only):

| Command | Effect |
|---|---|
| `setpass <character> <newpassword>` | Reset any character's password, online or offline |
| `makeadmin <character> on\|off` | Grant or revoke admin |

**Building commands** (admin only) — every change here is written straight back to `data/world.json` (atomically, so a crash mid-save can't corrupt it), so it survives a server restart:

| Command | Effect |
|---|---|
| `rooms` | List every room's id and name |
| `goto <room_id>` | Teleport to any room by id |
| `dig <direction> <room_id> [name...]` | Create a new room and link it both ways via `<direction>` from your current room |
| `rlink <direction> <room_id>` | Link an exit to an existing room (one-way; run it from both sides for a return exit) |
| `runlink <direction>` | Remove an exit from your current room |
| `rname <text>` / `rdesc <text>` | Rename / redescribe your current room |
| `rsafe on\|off` | Toggle whether combat is allowed in your current room |

A typical session: `dig east newroom The Old Pier`, `goto newroom`, `rdesc <something better than the placeholder>`, `rsafe off` if it should allow fighting.

## Project structure

```
saltspire-mud/
  main.py              FastAPI app + WebSocket endpoint (login, character creation, game loop)
  create_admin.py      CLI script to bootstrap/recover an admin character (run outside the live game)
  requirements.txt
  data/world.json       All rooms, mobs, and items -- also the save target for in-game room building
  game/
    models.py           Player/Room/MobTemplate/etc. dataclasses
    world.py             Loads data/world.json, and saves it back out for OLC building commands
    engine.py            Live game state + combat/respawn/regen tick loop
    commands.py          Command parsing and every do_* handler
    persistence.py       JSON-file save/load for characters
    auth.py              Salted PBKDF2 password hashing (stdlib only)
    colors.py            HTML-escaping + color-tagging helpers for the terminal UI
  static/
    index.html, style.css, app.js   Browser terminal frontend (incl. password-field masking)
  players/                One JSON file per saved character (includes password hash + admin flag)
  test_client.py          Scripted WebSocket smoke test (see Testing, below)
  Dockerfile, .dockerignore, docker-compose.yml   Container packaging
  AWS_DEPLOYMENT.md       Guide for running this on AWS
```

## Persistence & limitations

This is a prototype, not a production game server. A few things to know:

- **Demo-grade auth, not a hardened production system.** Passwords are salted PBKDF2-HMAC-SHA256 hashes (stdlib only, `game/auth.py`) — never stored or logged in plaintext — checked with a constant-time comparison, with a 5-attempt lockout per connection. That's solid for a self-hosted/trusted-group game, but there's no password reset email, rate limiting across connections, or session management, so don't treat it as a substitute for a vetted auth system if this ever faces the open internet.
- **In-memory world state.** Mob HP/position, dropped ground items, and opened containers live only in server memory. Restarting the server respawns all mobs and clears the ground — only player characters (`players/*.json`) survive a restart.
- **Single process only.** All shared game state (connected players, mob instances, ground items) lives in one Python process's memory. This app cannot be horizontally scaled — running multiple instances behind a load balancer would split players across inconsistent, disconnected copies of the world. Keep it at exactly one running instance.
- **`players/*.json` currently contains sample characters** (Brogan, Thessaly, Elowen) created while testing this build. They predate the password feature, so logging in as one of them for the first time will prompt you to set a password on the spot. Delete them (or the whole `players/` folder) before you start playing for real — the folder will be recreated automatically. None of them are admins; bootstrap one with `create_admin.py` (see "Admin role & building rooms in-game" above).

## Testing

`test_client.py` is a scripted WebSocket client used during development to exercise login, character creation, movement, shopping, combat, spellcasting, death/respawn, and save/reconnect — useful as a smoke test after you make changes. Run a server, then in another terminal:

```bash
python3 test_client.py new         # fresh warrior, full town/sewer/shop walkthrough
python3 test_client.py reconnect   # loads an existing saved character
python3 test_client.py mage        # mage spellcasting + combat
python3 test_client.py admin       # admin commands: setpass/makeadmin/dig/rdesc/rsafe/etc.
```

All four log themselves in with a shared test password, setting one along the way for any sample character that doesn't have one yet. `admin` mode requires an admin character named `Admin` with password `adminpass123` to already exist — create it first with `python3 create_admin.py Admin adminpass123`.

## Running in Docker

```bash
docker build -t saltspire-mud .
docker run -p 8000:8000 -v "$(pwd)/players:/app/players" saltspire-mud
```

or with Compose:

```bash
docker compose up --build
```

The volume mount keeps character saves on your host across container restarts.

## Deploying to AWS

See [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md) for step-by-step options (EC2, ECS Fargate, App Runner) and the tradeoffs between them — the short version is that the single-process/in-memory design above means this should run as exactly one container/instance, not an autoscaled fleet.
