"""Targeted smoke test for the expanded world: new zones, the lore/rlore
commands, the quaff command, a new shop, and fights against new mobs in
new dungeons. Uses the Admin character's goto/rooms commands to jump
straight to new rooms rather than walking the whole map.

Requires an admin character to already exist (see README):
    python3 create_admin.py Admin adminpass123
Run a server, then in another terminal:
    python3 test_new_world.py
"""
import asyncio
from test_client import run

SCRIPT = [
    "rooms",
    # -- new shop (apothecary, Trade Quarter expansion) --
    "goto apothecary",
    "look",
    "list",
    "buy mana draught",
    # -- lore command on a room with new lore text --
    "goto silver_court",
    "look",
    "lore",
    # -- rlore admin command: set, read, then clear --
    "rlore A test line written by the smoke test.",
    "lore",
    "rlore -",
    "lore",
    # -- quaff, plus a fight against a new mob in a new unsafe room --
    "goto hidden_grotto",
    "look",
    "kill serpent",
    "quaff healing potion",
    "score",
    # -- a brand-new dungeon zone with a tougher new mob --
    "goto the_sealed_crypt",
    "look",
    "kill wight",
    "score",
    "quit",
]


async def main():
    await run("Admin", "human", "warrior", SCRIPT, password="adminpass123")


if __name__ == "__main__":
    asyncio.run(main())
