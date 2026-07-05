# Saltspire MUD

A small, browser-playable MUD (Multi-User Dungeon) in the style of classic Diku/Merc/ROM-derived games — the same codebase lineage the real Waterdeep ("City of Splendors") MUD is built on. Players connect from a browser over WebSockets to a green-on-black terminal and play entirely with typed text commands.

## About the setting

The real Waterdeep MUD runs on a proprietary codebase and uses Wizards of the Coast's Forgotten Realms IP — it isn't open source and its specific names, lore, and text can't legally be reused. Saltspire borrows the *genre conventions* of that era of MUD (rooms, exits, mobs, shops, levels, classes, wards, guilds, an undercity, a criminal underworld) but uses an entirely original setting and history: nothing here is copied from Waterdeep or any Forgotten Realms material.

Saltspire was founded roughly 340 years ago by "the First Hundred," refugees who washed ashore beneath the town's namesake black spire fleeing the sudden sinking of their homeland, Old Vael. The town is governed openly by the Harbor Concord, seven Wardens elected by the wards rather than any secretive council — a deliberate contrast to the masked-and-whispered politics of older fantasy capitals. Beneath the streets, the flooded ruins of Old Vael itself are still reachable through the sewers, guarded by what's left of its drowned faithful. Two centuries ago the town's founders broke a pirate fleet called the Red Tide at what's now known as the salt fields, and a criminal syndicate called the Undertow has run the docks' smuggling trade since before the Concord existed. Much of this history is discoverable in-game: many rooms have extra depth readable with the `lore` command.

## Features

- 93 connected rooms across a dozen-plus areas: the original town core, plus Gildwater Heights and Warden Keep (the wealthy district and seat of government), an expanded dockside with its own smuggler's den and lighthouse, the flooded ruins of Old Vael beneath the sewers, Temple Row and the Hollow Yard cemetery (with a sealed crypt), an expanded Trade Quarter with a guild concourse and four class guild halls, and a much longer coast road running through a fishing hamlet, a haunted moor, sea caves, the salt fields, a mountain pass, and a swamp
- Extended lore: many rooms carry deeper history readable with `lore`/`history`, covering the town's founders, its government, its criminal underworld, and the drowned civilization beneath it — none of it reused from any Forgotten Realms or Waterdeep material
- 4 races (human, elf, dwarf, halfling) and 4 classes (warrior, mage, cleric, rogue), each with their own stats, HP/mana curve, and starting gear
- Levels 1-100, with 9 abilities per class unlocked across that range (level 1, 5, 12, 20, 35, 50, 65, 80, 95) — every class starts knowing one innate ability for free and learns the rest from its guild trainer as it levels up. Highlights: `veil` (mage invisibility), `bless` (cleric buff), plus warrior/rogue combat skills including `vanish` (rogue) and a stealth skill
- A guild hall for each class (Warriors', Mages', Clerics', Rogues') off a new concourse north of the Mercenary Board, each staffed by a level-100 guildmaster NPC who teaches that class's abilities via `learn` — these guildmasters are fixtures, not spawned mobs, so they can't be attacked
- Real-time tick-based combat (server resolves a round every 2 seconds), plus instant special attacks (`bash`, `backstab`, and the wider per-class skill list above via `use`) and spells via `cast`
- 37 monster types (levels 1-12) with loot tables, gold/XP rewards, and timed respawns, including several zone "boss" encounters
- 43 item types, including consumables that restore HP and/or mana via `quaff`
- Shops (buy/sell) in 10+ locations, a healer you can `pray` to, and several locked/unlocked containers
- Leveling, persistent characters (JSON file per player), say/emote/shout/who
- A minimal vanilla-JS browser terminal frontend — no build step, no frameworks
- **LLM-powered NPC dialogue.** Every NPC you can `talk` to — guild trainers, the shopkeeper, the temple priestess, and the spawn-room guide Old Rook — is backed by a locally-hosted LLM via [Ollama](https://ollama.com). Each NPC has a distinct system prompt encoding their personality, role, and knowledge of the world. The game falls back gracefully to a pool of hand-written lines if Ollama is unavailable, so it works without an LLM. The Ollama endpoint and model are configurable via environment variable (`OLLAMA_URL`, `OLLAMA_MODEL`); the default is `http://ollama:11434` with `llama3.2:3b`.
- Password-protected logins (salted PBKDF2 hashes, no plaintext anywhere) with a self-service `changepass`, and an admin role that can reset anyone's password and build new rooms in-game without hand-editing the world data files

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
| `lore` (`history`) | Read a room's deeper history, where present (look hints at it) |
| `say <msg>`, `emote <action>`, `shout <msg>`, `who` | Talk to other players |
| `get <item>`, `drop <item>`, `wear <item>`, `remove <item>` | Manage items |
| `quaff <item>` (`drink`/`use`) | Consume a potion or ration for its HP/mana |
| `kill <target>`, `flee`, `rest`, `wake` | Combat basics |
| `skills` | List your class's abilities, showing which you know, which you can learn now, and which need a higher level |
| `learn <ability>` | Learn a known-eligible ability from your class's guild trainer (must be at that guild, high enough level, and have the gold) |
| `cast <spell> [target]` (mage/cleric) | Cast a learned spell — damage, healing, buffs, invisibility, or mana restoration depending on the spell |
| `use <skill> [target]` (warrior/rogue) | Use a learned combat skill — bonus-damage attacks, buffs, self-heals, stealth, or vanish, depending on the skill |
| `bash <target>` (warrior), `backstab <target>` (rogue) | Each class's innate starter skill — known from creation, no need to learn it |
| `list`, `buy <item>`, `sell <item>` | Shop in town |
| `pray` | Full heal at the Temple of the Dawn, for a small donation |
| `open chest` | Open containers where present (some need a key) |
| `changepass <old> <new>` | Change your own password |
| `help`, `quit` | Help text; saves and disconnects |

Combat is room-gated: you can only `kill` something in a room marked unsafe, and you can't leave a room while fighting (use `flee` instead). Once a fight starts, the server resolves a round every couple of seconds until one side dies, you flee, or the mob is already dead. The level cap is 100; XP stops accumulating past it instead of overflowing.

A rough map: the **Rusty Anchor** tavern is still the spawn point and hub, with the original four exits leading to the **Market Square** (blacksmith, general store, and north to the **High Ward**, which now continues into **Gildwater Heights** — manor row, a masquerade hall, and **Warden Keep**, seat of the Harbor Concord), the **Harbor Docks** (harbormaster, fish market, and now a long pier with a lighthouse, a moored galley, a pawnshop, and the Undertow's hidden den, plus the original sewer entrance), **Temple Row** (now also leading to a row of minor shrines and the **Hollow Yard** cemetery, with a sealed crypt below it), and the **Guildhall** (now also the gateway to an expanded Trade Quarter: an archive, an apothecary, a jeweler, and a mercenary's job board, which in turn leads north to the **Hall of Banners** concourse and the four class guild halls — Warriors', Mages', Clerics', and Rogues' — where each class's trainer teaches its abilities).

The sewers still lead to the goblin lair, but now continue much further down into the flooded ruins of **Old Vael**, the drowned civilization Saltspire's founders fled — culminating in a guarded vault and a deep, ancient guardian. Past the **Coast Gate**, the **Coast Road** still has its wolf den and bandit camp, but a fork now continues north past a fishing hamlet, a haunted moor with an old watchtower, sea caves hiding a second Undertow smuggling route, and the salt fields where a pirate fleet met its end — and inland past the bandit camp into foothills, a sacred grove, a mountain pass guarded by a young drake, and a swamp ruled by something far older than the town itself. Several of these areas scale well past the original level range, for characters who outgrow the starting zones.

## Admin role & building rooms in-game

Characters with `is_admin: true` get an extra set of commands (shown in their own `help` block) for account recovery and for extending the map without ever hand-editing the world data files.

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

**Building commands** (admin only) — every change here is written straight back to the world data files (atomically, so a crash mid-save can't corrupt them), so it survives a server restart:

| Command | Effect |
|---|---|
| `rooms` | List every room's id and name |
| `goto <room_id>` | Teleport to any room by id |
| `dig <direction> <room_id> [name...]` | Create a new room and link it both ways via `<direction>` from your current room |
| `rlink <direction> <room_id>` | Link an exit to an existing room (one-way; run it from both sides for a return exit) |
| `runlink <direction>` | Remove an exit from your current room |
| `rname <text>` / `rdesc <text>` | Rename / redescribe your current room |
| `rlore <text>` | Set your current room's `lore` text (read with `lore`; `rlore -` clears it) |
| `rsafe on\|off` | Toggle whether combat is allowed in your current room |

A typical session: `dig east newroom The Old Pier`, `goto newroom`, `rdesc <something better than the placeholder>`, `rsafe off` if it should allow fighting.

## Project structure

```
saltspire-mud/
  main.py              FastAPI app + WebSocket endpoint (login, character creation, game loop)
  create_admin.py      CLI script to bootstrap/recover an admin character (run outside the live game)
  requirements.txt
  data/
    items.json           All item templates
    mobs.json             All mob templates
    rooms_1.json, rooms_2.json   All rooms, split across two files to keep each one small -- also the save target for in-game room building (re-sharded alphabetically on every save)
    world.json             Legacy monolithic format, no longer read unless items.json is missing (kept only for old checkouts)
  build_world.py        One-off generator script used to expand the original world into its current size (safe to re-run; re-applies the same data; reads/writes the split files above)
  game/
    models.py           Player/Room/MobTemplate/etc. dataclasses
    world.py             Loads data/items.json, data/mobs.json, data/rooms_1.json, data/rooms_2.json, and saves them back out for OLC building commands
    engine.py            Live game state + combat/respawn/regen tick loop
    commands.py          Command parsing and every do_* handler
    npc_ai.py            LLM-backed NPC dialogue: Ollama client, per-NPC system prompts, jailbreak filtering, and hand-written fallbacks
    persistence.py       JSON-file save/load for characters
    auth.py              Salted PBKDF2 password hashing (stdlib only)
    colors.py            HTML-escaping + color-tagging helpers for the terminal UI
    time.py              Game clock: 12x real-time scale, sun/moon phases, seasons
  static/
    index.html, style.css, app.js   Browser terminal frontend (incl. password-field masking)
  players/                One JSON file per saved character (includes password hash + admin flag)
  test_client.py          Scripted WebSocket smoke test (see Testing, below)
  test_new_world.py       Scripted smoke test focused on the expanded world's new zones, lore/quaff commands, and new mobs/shops
  test_guild_live.py      Scripted WebSocket smoke test for the guild halls: navigation, trainer `look`, `learn` gating, and confirming trainers can't be attacked
  test_abilities_offline.py   Offline test (imports the game package directly, no server needed) covering every spell/skill kind, learn gating, trainer setup, and the level-100 cap
  Dockerfile, .dockerignore, docker-compose.yml   Container packaging
  AWS_DEPLOYMENT.md       Guide for running this on AWS
```

## NPC AI (Ollama)

NPC dialogue is generated by a local LLM served through [Ollama](https://ollama.com). The relevant config lives in `game/npc_ai.py` and is controlled by two environment variables:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://ollama:11434` | Base URL of the Ollama instance. Change to `http://localhost:11434` for local dev outside Docker. For ECS, set this in your task definition's `environment` block. |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model to use. Must be pulled on the Ollama server first (`ollama pull llama3.2:3b`). |

Each NPC type (warrior trainer, mage trainer, cleric trainer, rogue trainer, shopkeeper, priestess, guide) has its own system prompt that constrains the character's voice, knowledge, and in-world role. Responses are sanitized to strip out-of-character content before being sent to the player. If Ollama is unreachable or returns an error, the game silently falls back to a pool of pre-written lines — no errors are shown to the player.

Admins can test the Ollama connection in-game with `checkai`.

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

```bash
python3 test_new_world.py  # tours the expanded world: a new shop, lore/rlore, quaff, and fights in new dungeons
```

This also requires the same `Admin` character (it uses `goto` to jump straight to the new zones rather than walking the whole map).

```bash
python3 test_guild_live.py  # walks a fresh mage to the Mages' Guild, checks skills/learn/trainer behavior
```

```bash
python3 test_abilities_offline.py  # no server needed -- exercises every spell/skill kind, learn gating, and the level cap directly against the game package
```

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
