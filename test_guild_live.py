"""Live end-to-end smoke test for the new guild/trainer feature, driven over
a real WebSocket connection against a running server (python3 test_guild_live.py
while `uvicorn main:app` is up on port 8000). Walks a brand-new mage from the
tavern to the Mages' Guild, checks the trainer renders correctly, confirms
the trainer can't be targeted with 'kill', then quits."""
import asyncio
from test_client import run

SCRIPT = [
    "skills",
    "west",     # tavern -> guildhall
    "north",    # guildhall -> mercenary_board
    "north",    # mercenary_board -> guild_concourse
    "look",
    "east",     # guild_concourse -> mages_guild
    "look",
    "look ottoline",
    "learn spark",       # should fail: level 1 < required 5
    "kill ottoline",     # trainer must NOT be a valid combat target
    "kill vance",
    "quit",
]

asyncio.run(run("GuildTestMage", "human", "mage", SCRIPT))
