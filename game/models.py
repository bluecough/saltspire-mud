"""
Data structures for Saltspire MUD.

Templates (Room, ItemTemplate, MobTemplate) are static, loaded once from
data/items.json, data/mobs.json, and data/rooms_1.json/rooms_2.json (see
game/world.py). Instances (MobInstance, Player) are runtime/mutable state.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import time

# ---------------------------------------------------------------------------
# Static templates (loaded from world.json)
# ---------------------------------------------------------------------------

@dataclass
class ItemTemplate:
    id: str
    name: str
    description: str
    slot: str  # weapon | shield | armor | consumable | key | treasure
    dmg_min: int = 0
    dmg_max: int = 0
    armor: int = 0
    heal: int = 0
    mana: int = 0
    value: int = 0


@dataclass
class MobTemplate:
    id: str
    name: str
    description: str
    level: int
    max_hp: int
    dmg_min: int
    dmg_max: int
    armor: int
    xp_reward: int
    gold_min: int
    gold_max: int
    respawn_seconds: int
    loot: list = field(default_factory=list)  # [{"item": id, "chance": 0..1}]
    wander: bool = True                        # may this mob wander within its zone?


@dataclass
class Container:
    name: str
    requires_key: Optional[str]
    loot: list
    opened: bool = False


@dataclass
class Trainer:
    """A guild trainer NPC. Trainers are flavor/utility fixtures attached
    directly to a Room (see below) -- they are never spawned as a
    MobInstance, so there is no combat target with their name and players
    have no way to attack them. 'level' is purely descriptive (shown via
    'look')."""
    name: str
    klass: str  # which class this trainer teaches: warrior/mage/cleric/rogue
    title: str
    description: str
    level: int = 100


@dataclass
class GuideNPC:
    """An immortal, helpful guide fixture. Shown in rooms, talkable, not attackable."""
    name: str
    description: str
    equipment_desc: str  # shown when player looks at the guide directly


@dataclass
class Room:
    id: str
    name: str
    description: str
    exits: dict  # direction -> room_id
    safe: bool = True
    mob_spawns: list = field(default_factory=list)  # [{"mob": id, "max": n}]
    shop: list = field(default_factory=list)  # item ids sold here
    services: list = field(default_factory=list)  # e.g. ["heal"]
    container: Optional[Container] = None
    lore: str = ""  # optional extended history/flavor text, read with 'lore'
    trainer: Optional[Trainer] = None  # guild trainer NPC, if any (see learn/use)
    guide: Optional[GuideNPC] = None   # immortal guide fixture, if any (spawn rooms)


# ---------------------------------------------------------------------------
# Runtime instances
# ---------------------------------------------------------------------------

@dataclass
class MobInstance:
    instance_id: str
    template_id: str
    room_id: str
    hp: int
    max_hp: int
    alive: bool = True
    respawn_at: float = 0.0
    target_name: Optional[str] = None  # player currently fighting it


RACE_MODS = {
    "human":    {"str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0},
    "elf":      {"str": -1, "dex": 2, "con": -1, "int": 1, "wis": 0},
    "dwarf":    {"str": 1, "dex": -1, "con": 2, "int": -1, "wis": 0},
    "halfling": {"str": -2, "dex": 3, "con": -1, "int": 0, "wis": 1},
}

CLASS_INFO = {
    "warrior": {"base_hp": 30, "hp_per_level": 8, "base_mana": 0, "mana_per_level": 0,
                "primary": "str", "start_weapon": "rusty_dagger", "start_armor": "leather_armor"},
    "mage":    {"base_hp": 18, "hp_per_level": 4, "base_mana": 30, "mana_per_level": 8,
                "primary": "int", "start_weapon": "oak_staff", "start_armor": None},
    "cleric":  {"base_hp": 22, "hp_per_level": 5, "base_mana": 25, "mana_per_level": 6,
                "primary": "wis", "start_weapon": "rusty_dagger", "start_armor": None},
    "rogue":   {"base_hp": 24, "hp_per_level": 6, "base_mana": 10, "mana_per_level": 2,
                "primary": "dex", "start_weapon": "rusty_dagger", "start_armor": None},
}

BASE_STAT = 10
MAX_LEVEL = 100

# The one ability each class starts with, already known -- everything else
# in commands.ABILITIES must be learned from that class's guild trainer.
STARTER_SKILL = {"warrior": "bash", "mage": "missile", "cleric": "heal", "rogue": "backstab"}


@dataclass
class Player:
    name: str
    race: str
    klass: str
    level: int = 1
    xp: int = 0
    gold: int = 20
    hp: int = 1
    max_hp: int = 1
    mana: int = 0
    max_mana: int = 0
    room_id: str = "tavern"
    inventory: list = field(default_factory=list)         # list of item ids
    equipment: dict = field(default_factory=dict)          # slot -> item id
    stats: dict = field(default_factory=dict)               # str/dex/con/int/wis
    in_combat_with: Optional[str] = None                    # mob instance_id
    cooldown_until: float = 0.0
    resting: bool = False
    password_hash: str = ""
    password_salt: str = ""
    is_admin: bool = False
    is_assistant_admin: bool = False
    known_skills: list = field(default_factory=list)        # ability ids learned from guild trainers

    # --- runtime-only, never persisted: combat buffs reset on reconnect ---
    websocket: object = field(default=None, repr=False, compare=False)
    connected: bool = field(default=False, repr=False, compare=False)
    last_save: float = field(default=0.0, repr=False, compare=False)
    dmg_buff_until: float = field(default=0.0, repr=False, compare=False)
    dmg_buff_amount: int = field(default=0, repr=False, compare=False)
    armor_buff_until: float = field(default=0.0, repr=False, compare=False)
    armor_buff_amount: int = field(default=0, repr=False, compare=False)
    invisible_until: float = field(default=0.0, repr=False, compare=False)
    skill_cooldowns: dict = field(default_factory=dict, repr=False, compare=False)  # ability id -> ready-at timestamp

    PERSIST_FIELDS = (
        "name", "race", "klass", "level", "xp", "gold", "hp", "max_hp", "mana",
        "max_mana", "room_id", "inventory", "equipment", "stats",
        "password_hash", "password_salt", "is_admin", "is_assistant_admin", "known_skills",
    )

    def stat_mod(self, stat: str) -> int:
        return (self.stats.get(stat, BASE_STAT) - BASE_STAT) // 2

    def recalc_max_stats(self):
        info = CLASS_INFO[self.klass]
        con_mod = self.stat_mod("con")
        self.max_hp = max(1, info["base_hp"] + con_mod * 2 + (self.level - 1) * info["hp_per_level"])
        primary_mod = self.stat_mod(info["primary"]) if info["base_mana"] > 0 or info["mana_per_level"] > 0 else 0
        self.max_mana = max(0, info["base_mana"] + primary_mod * 2 + (self.level - 1) * info["mana_per_level"])

    def to_dict(self) -> dict:
        # Built manually (not via dataclasses.asdict) so we never touch the
        # live `websocket` field -- asdict() deep-copies every field
        # including that one, which recurses into Starlette's internals.
        return {
            "name": self.name, "race": self.race, "klass": self.klass,
            "level": self.level, "xp": self.xp, "gold": self.gold,
            "hp": self.hp, "max_hp": self.max_hp, "mana": self.mana, "max_mana": self.max_mana,
            "room_id": self.room_id, "inventory": list(self.inventory),
            "equipment": dict(self.equipment), "stats": dict(self.stats),
            "password_hash": self.password_hash, "password_salt": self.password_salt,
            "is_admin": self.is_admin, "is_assistant_admin": self.is_assistant_admin,
            "known_skills": list(self.known_skills),
        }

    @classmethod
    def new_character(cls, name: str, race: str, klass: str,
                       password_hash: str = "", password_salt: str = "",
                       is_admin: bool = False) -> "Player":
        mods = RACE_MODS[race]
        stats = {s: BASE_STAT + mods[s] for s in ("str", "dex", "con", "int", "wis")}
        p = cls(name=name, race=race, klass=klass, stats=stats,
                password_hash=password_hash, password_salt=password_salt, is_admin=is_admin,
                known_skills=[STARTER_SKILL[klass]])
        p.recalc_max_stats()
        p.hp = p.max_hp
        p.mana = p.max_mana
        info = CLASS_INFO[klass]
        if info["start_weapon"]:
            p.inventory.append(info["start_weapon"])
            p.equipment["weapon"] = info["start_weapon"]
        if info["start_armor"]:
            p.inventory.append(info["start_armor"])
            p.equipment["armor"] = info["start_armor"]
        p.inventory.append("healing_potion")
        return p

    @classmethod
    def from_dict(cls, d: dict) -> "Player":
        known_skills = list(d.get("known_skills", []))
        # Backward compat: saves from before this feature existed (or that
        # somehow lost their starter ability) still know their class's
        # innate starter skill -- it was never something you had to learn.
        starter = STARTER_SKILL.get(d["klass"])
        if starter and starter not in known_skills:
            known_skills.append(starter)
        p = cls(
            name=d["name"], race=d["race"], klass=d["klass"], level=d.get("level", 1),
            xp=d.get("xp", 0), gold=d.get("gold", 20), hp=d.get("hp", 1), max_hp=d.get("max_hp", 1),
            mana=d.get("mana", 0), max_mana=d.get("max_mana", 0), room_id=d.get("room_id", "tavern"),
            inventory=list(d.get("inventory", [])), equipment=dict(d.get("equipment", {})),
            stats=dict(d.get("stats", {})),
            password_hash=d.get("password_hash", ""), password_salt=d.get("password_salt", ""),
            is_admin=bool(d.get("is_admin", False)),
            is_assistant_admin=bool(d.get("is_assistant_admin", False)),
            known_skills=known_skills,
        )
        return p
