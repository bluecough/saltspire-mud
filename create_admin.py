#!/usr/bin/env python3
"""Bootstrap (or recover) an admin character, run from the server's shell --
outside the live game. Useful for creating the very first admin, since
nobody can grant admin in-game until at least one admin already exists.

Usage:
    python create_admin.py <name> <password> [race] [klass]

  - race defaults to "human", klass defaults to "warrior" (only used if the
    character doesn't already exist -- see RACE_MODS / CLASS_INFO in
    game/models.py for the other valid choices: elf, dwarf, halfling /
    mage, cleric, rogue).
  - If <name> already exists, this resets its password to <password> and
    grants it admin, leaving everything else (level, inventory, etc.)
    untouched. Safe to re-run any time, e.g. to recover a forgotten admin
    password.
"""
from __future__ import annotations
import sys

from game import auth, persistence
from game.models import Player, RACE_MODS, CLASS_INFO


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1

    name, password = argv[1], argv[2]
    race = argv[3].lower() if len(argv) > 3 else "human"
    klass = argv[4].lower() if len(argv) > 4 else "warrior"

    if not persistence.is_valid_name(name):
        print(f"Invalid character name: '{name}' (letters/digits/underscore, 2-16 chars, starting with a letter).")
        return 1
    if not auth.is_valid_password(password):
        print("Invalid password (must be 4-64 characters).")
        return 1
    if race not in RACE_MODS:
        print(f"Invalid race '{race}'. Choices: {', '.join(sorted(RACE_MODS))}")
        return 1
    if klass not in CLASS_INFO:
        print(f"Invalid class '{klass}'. Choices: {', '.join(sorted(CLASS_INFO))}")
        return 1

    pw_hash, pw_salt = auth.hash_password(password)

    existing = persistence.load(name)
    if existing:
        existing.password_hash, existing.password_salt = pw_hash, pw_salt
        existing.is_admin = True
        persistence.save(existing)
        print(f"'{existing.name}' already existed -- password reset and admin granted.")
        return 0

    player = Player.new_character(name, race, klass, password_hash=pw_hash, password_salt=pw_salt, is_admin=True)
    persistence.save(player)
    print(f"Created new admin character '{player.name}' ({race} {klass}). Log in with this name and password.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
