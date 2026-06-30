"""Loads the static world (rooms, mobs, items) from data/*.json, and --
for in-game room building -- saves it back out.

The world data is split across several files rather than one big
world.json: data/items.json, data/mobs.json, and data/rooms_1.json /
data/rooms_2.json (rooms are sharded across two files purely to keep
any single file small; the split is rebalanced on every save() and
carries no semantic meaning -- a room's shard is just whichever half
it landed in alphabetically by room id)."""
from __future__ import annotations
import json
import os
import re
from dataclasses import fields as dc_fields
from .models import Room, ItemTemplate, MobTemplate, Container, Trainer

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ITEMS_PATH = os.path.join(DATA_DIR, "items.json")
MOBS_PATH = os.path.join(DATA_DIR, "mobs.json")
ROOM_SHARD_PATHS = [os.path.join(DATA_DIR, "rooms_1.json"), os.path.join(DATA_DIR, "rooms_2.json")]
# Legacy single-file layout, still read transparently if present (e.g. an
# older checkout that hasn't been migrated) but never written.
LEGACY_WORLD_PATH = os.path.join(DATA_DIR, "world.json")
ROOM_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")


class World:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        items_path = os.path.join(data_dir, "items.json")
        if os.path.exists(items_path):
            with open(items_path, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
            with open(os.path.join(data_dir, "mobs.json"), "r", encoding="utf-8") as f:
                raw_mobs = json.load(f)
            raw_rooms: dict = {}
            for shard_path in (os.path.join(data_dir, "rooms_1.json"), os.path.join(data_dir, "rooms_2.json")):
                if os.path.exists(shard_path):
                    with open(shard_path, "r", encoding="utf-8") as f:
                        raw_rooms.update(json.load(f))
        else:
            # Fall back to the legacy monolithic data/world.json.
            with open(os.path.join(data_dir, "world.json"), "r", encoding="utf-8") as f:
                raw = json.load(f)
            raw_items, raw_mobs, raw_rooms = raw["items"], raw["mobs"], raw["rooms"]

        self.items: dict[str, ItemTemplate] = {
            iid: ItemTemplate(id=iid, **idata) for iid, idata in raw_items.items()
        }
        self.mobs: dict[str, MobTemplate] = {
            mid: MobTemplate(id=mid, **mdata) for mid, mdata in raw_mobs.items()
        }
        self.rooms: dict[str, Room] = {}
        for rid, rdata in raw_rooms.items():
            container = None
            if rdata.get("container"):
                container = Container(**rdata["container"])
            trainer = None
            if rdata.get("trainer"):
                trainer = Trainer(**rdata["trainer"])
            self.rooms[rid] = Room(
                id=rid,
                name=rdata["name"],
                description=rdata["description"],
                exits=rdata.get("exits", {}),
                safe=rdata.get("safe", True),
                mob_spawns=rdata.get("mob_spawns", []),
                shop=rdata.get("shop", []),
                services=rdata.get("services", []),
                container=container,
                lore=rdata.get("lore", ""),
                trainer=trainer,
            )

    def get_room(self, room_id: str) -> Room | None:
        return self.rooms.get(room_id)

    def get_item(self, item_id: str) -> ItemTemplate | None:
        return self.items.get(item_id)

    def get_mob_template(self, mob_id: str) -> MobTemplate | None:
        return self.mobs.get(mob_id)

    # ---- in-game building (admin OLC commands) -----------------------------
    def is_valid_room_id(self, room_id: str) -> bool:
        return bool(ROOM_ID_RE.match(room_id or ""))

    def add_room(self, room_id: str, name: str, description: str, safe: bool = True) -> Room:
        room = Room(id=room_id, name=name, description=description, exits={}, safe=safe)
        self.rooms[room_id] = room
        return room

    def save(self) -> None:
        """Write items/mobs/rooms back to data/items.json, data/mobs.json,
        and data/rooms_1.json + data/rooms_2.json, atomically (each file is
        written to a .tmp path and replaced in place). Only room data is
        ever mutated at runtime today, but everything is re-serialized so
        every file stays a complete, consistent snapshot. Rooms are
        re-sharded alphabetically by id on every save, so the two shards
        stay roughly balanced regardless of what got added or removed."""
        items_data = {iid: self._template_to_dict(t) for iid, t in self.items.items()}
        mobs_data = {mid: self._template_to_dict(t) for mid, t in self.mobs.items()}
        room_ids = sorted(self.rooms.keys())
        midpoint = (len(room_ids) + 1) // 2
        shard_1 = {rid: self._room_to_dict(self.rooms[rid]) for rid in room_ids[:midpoint]}
        shard_2 = {rid: self._room_to_dict(self.rooms[rid]) for rid in room_ids[midpoint:]}

        self._write_json(os.path.join(self.data_dir, "items.json"), items_data)
        self._write_json(os.path.join(self.data_dir, "mobs.json"), mobs_data)
        self._write_json(os.path.join(self.data_dir, "rooms_1.json"), shard_1)
        self._write_json(os.path.join(self.data_dir, "rooms_2.json"), shard_2)

    @staticmethod
    def _write_json(path: str, data: dict) -> None:
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)

    @staticmethod
    def _template_to_dict(t) -> dict:
        # Generic shallow copy of every dataclass field except "id" (which is
        # the outer dict key in world.json, not stored inside the value).
        # Safe for ItemTemplate/MobTemplate: no live framework objects, just
        # plain JSON-safe values, so this is a plain attribute copy --
        # NOT dataclasses.asdict() (which deep-copies and would be overkill,
        # though harmless here; we avoid it mainly for consistency with the
        # Player model's hand-written to_dict()).
        return {f.name: getattr(t, f.name) for f in dc_fields(t) if f.name != "id"}

    @staticmethod
    def _room_to_dict(r: Room) -> dict:
        return {
            "name": r.name,
            "description": r.description,
            "exits": dict(r.exits),
            "safe": r.safe,
            "mob_spawns": list(r.mob_spawns),
            "shop": list(r.shop),
            "services": list(r.services),
            "lore": r.lore,
            "container": (
                {
                    "name": r.container.name,
                    "requires_key": r.container.requires_key,
                    "loot": list(r.container.loot),
                    "opened": r.container.opened,
                }
                if r.container else None
            ),
            "trainer": (
                {
                    "name": r.trainer.name,
                    "klass": r.trainer.klass,
                    "title": r.trainer.title,
                    "description": r.trainer.description,
                    "level": r.trainer.level,
                }
                if r.trainer else None
            ),
        }
