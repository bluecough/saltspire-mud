"""Loads the static world (rooms, mobs, items) from data/world.json, and --
for in-game room building -- saves it back out."""
from __future__ import annotations
import json
import os
import re
from dataclasses import fields as dc_fields
from .models import Room, ItemTemplate, MobTemplate, Container

WORLD_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "world.json")
ROOM_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")


class World:
    def __init__(self, path: str = WORLD_PATH):
        self.path = path
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self.items: dict[str, ItemTemplate] = {
            iid: ItemTemplate(id=iid, **idata) for iid, idata in raw["items"].items()
        }
        self.mobs: dict[str, MobTemplate] = {
            mid: MobTemplate(id=mid, **mdata) for mid, mdata in raw["mobs"].items()
        }
        self.rooms: dict[str, Room] = {}
        for rid, rdata in raw["rooms"].items():
            container = None
            if rdata.get("container"):
                container = Container(**rdata["container"])
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
        """Write items/mobs/rooms back to data/world.json, atomically. Only
        room data is ever mutated at runtime today, but everything is
        re-serialized so the file stays a complete, consistent snapshot."""
        data = {
            "items": {iid: self._template_to_dict(t) for iid, t in self.items.items()},
            "mobs": {mid: self._template_to_dict(t) for mid, t in self.mobs.items()},
            "rooms": {rid: self._room_to_dict(r) for rid, r in self.rooms.items()},
        }
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self.path)

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
            "container": (
                {
                    "name": r.container.name,
                    "requires_key": r.container.requires_key,
                    "loot": list(r.container.loot),
                    "opened": r.container.opened,
                }
                if r.container else None
            ),
        }
