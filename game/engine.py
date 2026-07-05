"""
Core runtime engine: holds all live state (connected players, mob instances,
dropped items, opened containers) and runs the combat/respawn/regen tick.
"""
from __future__ import annotations
import asyncio
import random
import time
from . import colors as c
from . import persistence
from . import time as gametime
from .models import Player, MobInstance, CLASS_INFO, MAX_LEVEL
from .weather import WeatherState
from .world import World

TICK_SECONDS   = 2.0
SAVE_INTERVAL  = 30.0
WANDER_TICKS   = 10    # check wandering every N ticks (10 × 2 s = 20 s real = ~4 game min)
WANDER_CHANCE  = 0.30  # probability a qualifying mob wanders per check

# Rooms grouped into zones; mobs only wander to adjacent rooms in the same zone.
_ZONES: dict[str, frozenset] = {
    "town": frozenset({
        "tavern", "market_square", "fish_market", "blacksmith", "apothecary",
        "general_store", "tannery", "jeweler", "pawnshop", "counting_house",
        "drowned_lantern_inn", "the_gilt_lantern", "weavers_row", "manor_row",
        "gildwater_promenade", "town_archive", "mercenary_board", "guildhall",
        "press_gang_corner", "temple_row", "scholars_chapel",
        "bakers_row", "sweetbread_nook", "market_south_lane",
        "curiosity_cabinet", "trinket_alley",
    }),
    "harbor": frozenset({
        "harbor_docks", "harbor_pier", "harbormaster_office", "city_gate",
        "warehouse_row", "smugglers_alley",
    }),
    "sewers": frozenset({
        "sewer_entrance", "sewer_tunnel_1", "sewer_tunnel_2", "sewer_tunnel_3",
        "sewer_lair", "flooded_cistern", "flooded_vault", "the_low_tunnel",
    }),
    "coast": frozenset({
        "coast_road", "bandit_camp", "lighthouse_base", "lighthouse_top",
        "sea_cave_mouth", "smugglers_cove", "smugglers_den", "hidden_grotto",
        "windswept_bluffs",
    }),
    "foothills": frozenset({
        "foothill_path", "boggy_shallows", "the_fenmire", "drowned_thicket",
        "wolf_den", "hamlet_road", "salt_fields", "tallows_reach",
        "hollow_moor", "weeping_willow", "druids_grove",
    }),
    "high_ward": frozenset({
        "high_ward", "high_ward_gate", "silver_court", "keep_courtyard",
        "keep_armory", "keep_barracks", "keep_dungeon", "warden_gate",
        "old_graves", "mausoleum_row",
    }),
    "old_vael": frozenset({
        "old_vael_archive", "old_vael_plaza", "old_vael_shrine",
        "old_sentinel_base", "old_sentinel_top", "the_bone_warden_hall",
        "the_sealed_crypt", "the_deep_maw", "undercity_stair",
    }),
    "wilderness": frozenset({
        "hollow_yard", "hollow_yard_gate", "greyfang_pass", "terraced_gardens",
        "crossroads_shrine",
    }),
    "shrines": frozenset({
        "shrine_walk", "shrine_of_embers", "shrine_of_tides",
        "sunken_shrine_of_the_fen",
    }),
    "galley": frozenset({
        "galley_hold", "moored_galley_deck",
    }),
}
_ROOM_ZONE: dict[str, str] = {
    rid: zn for zn, rooms in _ZONES.items() for rid in rooms
}


class GameEngine:
    def __init__(self, world: World):
        self.world = world
        self.players: dict[str, Player] = {}     # name.lower() -> Player
        self.mobs: dict[str, MobInstance] = {}    # instance_id -> MobInstance
        self.ground: dict[str, list] = {}         # room_id -> [item_id, ...] (not persisted)
        self._opened_containers: set[str] = set()
        self._mob_seq = 0
        self._wander_tick = 0
        self.weather = WeatherState(gametime.now().season)
        self._spawn_initial_mobs()

    # ---- world / mob spawning ------------------------------------------------
    def _spawn_initial_mobs(self):
        for room in self.world.rooms.values():
            for spawn in room.mob_spawns:
                for _ in range(spawn["max"]):
                    self._spawn_mob(spawn["mob"], room.id)

    def _spawn_mob(self, template_id: str, room_id: str) -> str:
        tmpl = self.world.get_mob_template(template_id)
        self._mob_seq += 1
        inst_id = f"{template_id}#{self._mob_seq}"
        self.mobs[inst_id] = MobInstance(
            instance_id=inst_id, template_id=template_id, room_id=room_id,
            hp=tmpl.max_hp, max_hp=tmpl.max_hp,
        )
        return inst_id

    # ---- containers ------------------------------------------------------
    def is_container_opened(self, room_id: str) -> bool:
        return room_id in self._opened_containers

    def mark_container_opened(self, room_id: str):
        self._opened_containers.add(room_id)

    # ---- lookups -----------------------------------------------------
    def mobs_in_room(self, room_id):
        return [m for m in self.mobs.values() if m.room_id == room_id and m.alive]

    def players_in_room(self, room_id, exclude=None):
        return [p for p in self.players.values()
                if p.room_id == room_id and p.connected and p.name != exclude]

    def find_mob_in_room(self, room_id, keyword):
        keyword = (keyword or "").lower()
        for m in self.mobs_in_room(room_id):
            tmpl = self.world.get_mob_template(m.template_id)
            if keyword and keyword in tmpl.name.lower():
                return m
        return None

    def find_player_in_room(self, room_id, keyword, exclude=None):
        keyword = (keyword or "").lower()
        for p in self.players_in_room(room_id, exclude=exclude):
            if keyword and p.name.lower().startswith(keyword):
                return p
        return None

    # ---- connection management -----------------------------------------------------
    def is_online(self, name: str) -> bool:
        p = self.players.get(name.lower())
        return bool(p and p.connected)

    def connect_player(self, player: Player, websocket):
        player.websocket = websocket
        player.connected = True
        player.last_save = time.time()
        self.players[player.name.lower()] = player

    def disconnect_player(self, player: Player):
        player.connected = False
        player.websocket = None
        persistence.save(player)

    # ---- messaging -----------------------------------------------------
    async def send(self, player: Player, html_line: str):
        if player.websocket is None:
            return
        try:
            await player.websocket.send_text(html_line)
        except Exception:
            pass

    async def send_room(self, room_id, html_line, exclude_names=()):
        for p in self.players_in_room(room_id):
            if p.name in exclude_names:
                continue
            await self.send(p, html_line)

    async def broadcast(self, html_line, exclude_names=()):
        for p in list(self.players.values()):
            if p.connected and p.name not in exclude_names:
                await self.send(p, html_line)

    # ---- combat helpers (also used by commands.py for spells/specials) --------
    def player_armor(self, player: Player) -> int:
        total = 0
        for slot in ("armor", "shield"):
            iid = player.equipment.get(slot)
            if iid:
                tmpl = self.world.get_item(iid)
                if tmpl:
                    total += tmpl.armor
        if time.time() < player.armor_buff_until:
            total += player.armor_buff_amount
        return total

    def player_weapon(self, player: Player):
        iid = player.equipment.get("weapon")
        return self.world.get_item(iid) if iid else None

    def roll_player_damage(self, player: Player) -> int:
        weapon = self.player_weapon(player)
        lo, hi = (weapon.dmg_min, weapon.dmg_max) if weapon else (1, 2)
        base = random.randint(lo, hi)
        info = CLASS_INFO[player.klass]
        bonus = max(0, player.stat_mod(info["primary"]) // 2)
        dmg_buff = player.dmg_buff_amount if time.time() < player.dmg_buff_until else 0
        return max(1, base + bonus + dmg_buff)

    def roll_mob_damage(self, tmpl, player: Player) -> int:
        base = random.randint(tmpl.dmg_min, tmpl.dmg_max)
        reduced = base - self.player_armor(player)
        return max(1, reduced)

    async def resolve_mob_death(self, inst: MobInstance, tmpl, killer: Player):
        inst.alive = False
        inst.hp = 0
        inst.respawn_at = time.time() + tmpl.respawn_seconds
        inst.target_name = None
        if killer.in_combat_with == inst.instance_id:
            killer.in_combat_with = None

        gold = random.randint(tmpl.gold_min, tmpl.gold_max)
        killer.gold += gold
        killer.xp += tmpl.xp_reward

        await self.send(killer, f"You have slain {c.mob(tmpl.name)}!")
        if gold:
            await self.send(killer, f"You loot {c.gold(gold)} gold from the body.")
        await self.send(killer, f"You gain {c.tag(str(tmpl.xp_reward), 'c-xp')} experience.")
        await self.send_room(inst.room_id, f"{c.player(killer.name)} has slain {c.mob(tmpl.name)}!",
                              exclude_names=(killer.name,))

        for drop in tmpl.loot:
            if random.random() <= drop["chance"]:
                killer.inventory.append(drop["item"])
                item_tmpl = self.world.get_item(drop["item"])
                await self.send(killer, f"{c.esc(tmpl.name.capitalize())} dropped {c.item(item_tmpl.name)}!")

        await self.maybe_level_up(killer)

    async def maybe_level_up(self, player: Player):
        if player.level >= MAX_LEVEL:
            player.xp = 0  # already capped -- nothing more to bank
            return
        threshold = player.level * 100
        leveled = False
        while player.level < MAX_LEVEL and player.xp >= threshold:
            player.xp -= threshold
            player.level += 1
            player.recalc_max_stats()
            player.hp = player.max_hp
            player.mana = player.max_mana
            leveled = True
            if player.level >= MAX_LEVEL:
                player.xp = 0
                break
            threshold = player.level * 100
        if leveled:
            msg = f"*** You are now level {player.level}! ***"
            if player.level >= MAX_LEVEL:
                msg += f" You have reached the maximum level of {MAX_LEVEL}."
            await self.send(player, c.tag(msg, "c-levelup"))

    # ---- tick loop -----------------------------------------------------
    async def tick_loop(self):
        while True:
            await asyncio.sleep(TICK_SECONDS)
            try:
                await self._tick()
            except Exception as e:  # keep the loop alive no matter what
                print("tick error:", repr(e))

    async def _tick(self):
        now = time.time()

        # weather transitions
        change_msg = self.weather.maybe_update(now, gametime.now().season)
        if change_msg:
            await self.broadcast(c.system(change_msg))

        # mob respawns
        for inst in list(self.mobs.values()):
            if not inst.alive and now >= inst.respawn_at:
                tmpl = self.world.get_mob_template(inst.template_id)
                inst.alive = True
                inst.hp = tmpl.max_hp
                inst.target_name = None
                await self.send_room(inst.room_id, c.system(f"{tmpl.name.capitalize()} skulks back into the area."))

        # mob wandering
        self._wander_tick += 1
        if self._wander_tick >= WANDER_TICKS:
            self._wander_tick = 0
            await self._do_mob_wander()

        # combat & passive regen for connected players
        for player in list(self.players.values()):
            if not player.connected:
                continue
            if player.in_combat_with:
                await self._resolve_combat_round(player)
            else:
                regen_mult = 3 if player.resting else 1
                if player.hp < player.max_hp:
                    player.hp = min(player.max_hp, player.hp + regen_mult)
                if player.mana < player.max_mana:
                    player.mana = min(player.max_mana, player.mana + regen_mult)

            if now - player.last_save > SAVE_INTERVAL:
                persistence.save(player)
                player.last_save = now

    async def _do_mob_wander(self):
        """Randomly move idle mobs to an adjacent room within the same zone."""
        for inst in list(self.mobs.values()):
            if not inst.alive or inst.target_name:
                continue   # dead or engaged in combat
            tmpl = self.world.get_mob_template(inst.template_id)
            if tmpl and not getattr(tmpl, "wander", True):
                continue   # template opts out of wandering
            if random.random() > WANDER_CHANCE:
                continue
            zone = _ROOM_ZONE.get(inst.room_id)
            if not zone:
                continue   # room not in any defined zone
            room = self.world.get_room(inst.room_id)
            if not room:
                continue
            neighbors = [
                dest for dest in room.exits.values()
                if _ROOM_ZONE.get(dest) == zone
                and self.world.get_room(dest) is not None
            ]
            if not neighbors:
                continue
            dest_id = random.choice(neighbors)
            await self.send_room(inst.room_id,
                c.system(f"{tmpl.name.capitalize()} moves away."))
            inst.room_id = dest_id
            await self.send_room(dest_id,
                c.system(f"{tmpl.name.capitalize()} arrives."))

    async def _resolve_combat_round(self, player: Player):
        inst = self.mobs.get(player.in_combat_with)
        if inst is None or not inst.alive or inst.room_id != player.room_id:
            player.in_combat_with = None
            return
        tmpl = self.world.get_mob_template(inst.template_id)

        dmg = self.roll_player_damage(player)
        inst.hp -= dmg
        await self.send(player, f"You hit {c.mob(tmpl.name)} for {c.dmg(dmg)} damage.")
        await self.send_room(player.room_id,
                              f"{c.player(player.name)} hits {c.mob(tmpl.name)} for {c.dmg(dmg)} damage.",
                              exclude_names=(player.name,))

        if inst.hp <= 0:
            await self.resolve_mob_death(inst, tmpl, player)
            return

        mdmg = self.roll_mob_damage(tmpl, player)
        player.hp -= mdmg
        await self.send(player, f"{c.mob(tmpl.name)} hits you for {c.dmg(mdmg)} damage.")
        await self.send_room(player.room_id,
                              f"{c.mob(tmpl.name)} hits {c.player(player.name)} for {c.dmg(mdmg)} damage.",
                              exclude_names=(player.name,))

        if player.hp <= 0:
            await self._player_dies(player, inst, tmpl)

    async def _player_dies(self, player: Player, inst: MobInstance, tmpl):
        player.in_combat_with = None
        inst.target_name = None
        await self.send(player, c.error("You have died! Your spirit drifts back to the Rusty Anchor."))
        await self.send_room(player.room_id, f"{c.player(player.name)} has been slain by {c.mob(tmpl.name)}!",
                              exclude_names=(player.name,))
        player.room_id = "tavern"
        player.hp = max(1, player.max_hp // 2)
        player.mana = player.max_mana
        persistence.save(player)
