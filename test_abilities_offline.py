"""Offline smoke test for the new guild/skill/spell/trainer feature -- runs
directly against the game package (no server/websocket needed) so it can
exercise every ability kind and the learn/use/cast gating logic quickly and
deterministically. Not part of the persisted save data; doesn't touch
players/*.json."""
import asyncio
import time

from game.world import World
from game.engine import GameEngine
from game.models import Player, MAX_LEVEL
from game import commands as cmd

LOG = []


async def fake_send(self, player, html):
    LOG.append(f"[{player.name}] {html}")


async def fake_send_room(self, room_id, html, exclude_names=()):
    LOG.append(f"[room:{room_id}] {html}")


GameEngine.send = fake_send
GameEngine.send_room = fake_send_room


def find_unsafe_room_with_mob(engine):
    for room in engine.world.rooms.values():
        if not room.safe and engine.mobs_in_room(room.id):
            return room.id
    raise RuntimeError("no unsafe room with a live mob found")


async def test_trainer_attached_and_unattackable(engine):
    for rid, klass in (
        ("warriors_guild", "warrior"), ("mages_guild", "mage"),
        ("clerics_guild", "cleric"), ("rogues_guild", "rogue"),
    ):
        room = engine.world.get_room(rid)
        assert room is not None, f"missing room {rid}"
        assert room.trainer is not None, f"{rid} has no trainer"
        assert room.trainer.klass == klass
        assert room.trainer.level == MAX_LEVEL, f"{rid} trainer not level {MAX_LEVEL}"
        # The whole point: trainers are never spawned as MobInstances, so
        # find_mob_in_room (what 'kill'/'bash'/'backstab' use to find a
        # target) can never resolve to them.
        mob = engine.find_mob_in_room(rid, room.trainer.name.split()[0].lower())
        assert mob is None, f"trainer in {rid} resolved as an attackable mob!"
    print("OK: all 4 guild trainers present, level 100, structurally unattackable")


async def test_learn_gating(engine):
    p = Player.new_character("OfflineTestMage", "human", "mage")
    p.level = 1
    p.gold = 500
    p.room_id = "mages_guild"
    engine.players[p.name.lower()] = p
    ctx = cmd.CommandContext(engine, p)

    # starter spell already known, free, shouldn't be (re)learnable
    await cmd.do_learn(ctx, "missile")
    assert "already know" in LOG[-1].lower()

    # level too low for 'spark' (requires 5)
    await cmd.do_learn(ctx, "spark")
    assert "spark" not in p.known_skills
    assert "level 5" in LOG[-1]

    # bump to level 5, learn it for gold
    p.level = 5
    before_gold = p.gold
    await cmd.do_learn(ctx, "spark")
    assert "spark" in p.known_skills, LOG[-1]
    assert p.gold == before_gold - cmd.ABILITIES["spark"]["learn_cost"]

    # wrong-class ability
    await cmd.do_learn(ctx, "bash")
    assert "isn't one of your class" in LOG[-1].lower()

    # no trainer present -> can't learn even if eligible
    p.room_id = "tavern"
    p.level = 12
    await cmd.do_learn(ctx, "frost_lance")
    assert "frost_lance" not in p.known_skills
    assert "no trainer here" in LOG[-1].lower()
    print("OK: learn gating (level/gold/class/trainer-presence/already-known) all enforced")


async def test_cast_all_kinds(engine):
    p = Player.new_character("OfflineTestCleric", "human", "cleric")
    p.level = MAX_LEVEL
    p.gold = 100000
    p.recalc_max_stats()
    p.known_skills = [aid for aid, spec in cmd.ABILITIES.items() if spec["class"] == "cleric"]
    engine.players[p.name.lower()] = p
    ctx = cmd.CommandContext(engine, p)
    unsafe_room = find_unsafe_room_with_mob(engine)

    # heal / mend / greater_heal / divine_grace (kind: heal)
    p.room_id = "temple_of_dawn"
    for spell in ("heal", "mend", "greater_heal", "divine_grace"):
        p.hp = 1
        p.mana = p.max_mana
        await cmd.do_cast(ctx, spell)
        assert p.hp > 1, f"{spell} did not heal"

    # bless (buff_dmg)
    p.mana = p.max_mana
    await cmd.do_cast(ctx, "bless")
    assert time.time() < p.dmg_buff_until and p.dmg_buff_amount == cmd.ABILITIES["bless"]["amount"]

    # ward (buff_armor)
    p.mana = p.max_mana
    await cmd.do_cast(ctx, "ward")
    assert time.time() < p.armor_buff_until and p.armor_buff_amount == cmd.ABILITIES["ward"]["amount"]

    # sanctuary (full_restore)
    p.hp, p.mana = 1, 0
    await cmd.do_cast(ctx, "sanctuary")
    assert p.hp == p.max_hp and p.mana == p.max_mana

    # smite / judgment (damage) -- need a live target
    p.room_id = unsafe_room
    mob = engine.mobs_in_room(unsafe_room)[0]
    p.in_combat_with = mob.instance_id
    mob.target_name = p.name
    p.mana = p.max_mana
    hp_before = mob.hp
    await cmd.do_cast(ctx, "smite")
    assert mob.hp < hp_before or mob.hp <= 0, "smite did no damage"
    print("OK: cleric spells (heal/buff_dmg/buff_armor/full_restore/damage) all resolve")

    # mage-only kinds not covered above: invisibility, mana_restore
    m = Player.new_character("OfflineTestMage2", "human", "mage")
    m.level = MAX_LEVEL
    m.recalc_max_stats()
    m.known_skills = [aid for aid, spec in cmd.ABILITIES.items() if spec["class"] == "mage"]
    m.room_id = "mages_guild"
    engine.players[m.name.lower()] = m
    mctx = cmd.CommandContext(engine, m)

    m.mana = m.max_mana
    await cmd.do_cast(mctx, "veil")
    assert time.time() < m.invisible_until

    m.mana = 5
    await cmd.do_cast(mctx, "font_of_mana")
    assert m.mana > 5
    print("OK: mage invisibility (veil) and mana_restore (font_of_mana) resolve")


async def test_use_all_kinds(engine):
    unsafe_room = find_unsafe_room_with_mob(engine)

    w = Player.new_character("OfflineTestWarrior", "human", "warrior")
    w.level = MAX_LEVEL
    w.recalc_max_stats()
    w.hp = w.max_hp
    w.known_skills = [aid for aid, spec in cmd.ABILITIES.items() if spec["class"] == "warrior"]
    w.room_id = unsafe_room
    engine.players[w.name.lower()] = w
    wctx = cmd.CommandContext(engine, w)

    mob = engine.mobs_in_room(unsafe_room)[0]
    mob_tmpl = engine.world.get_mob_template(mob.template_id)
    mob_keyword = mob_tmpl.name.split()[-1]
    hp_before = mob.hp
    await cmd.do_use(wctx, f"cleave {mob_keyword}")  # attack_bonus, found by keyword
    assert mob.hp < hp_before or mob.hp <= 0, LOG[-1]
    assert "cleave" in w.skill_cooldowns

    await cmd.do_use(wctx, "rally")  # buff_dmg
    assert time.time() < w.dmg_buff_until

    await cmd.do_use(wctx, "guard_stance")  # buff_armor
    assert time.time() < w.armor_buff_until

    w.hp = 1
    await cmd.do_use(wctx, "second_wind")  # self_heal
    assert w.hp > 1
    print("OK: warrior 'use' skills (attack_bonus/buff_dmg/buff_armor/self_heal) resolve, cooldowns recorded")

    r = Player.new_character("OfflineTestRogue", "human", "rogue")
    r.level = MAX_LEVEL
    r.recalc_max_stats()
    r.known_skills = [aid for aid, spec in cmd.ABILITIES.items() if spec["class"] == "rogue"]
    r.room_id = unsafe_room
    engine.players[r.name.lower()] = r
    rctx = cmd.CommandContext(engine, r)

    # Mark every other mob in the room as not-alive first -- find_mob_in_room
    # (which 'ambush' uses to resolve its keyword target) only considers
    # alive mobs, and the warrior subtest above may have left its target
    # alive and mid-combat, which would otherwise shadow the fresh instance
    # spawned below (same template = same display name = same keyword).
    for m in engine.mobs_in_room(unsafe_room):
        m.alive = False

    mob2_id = engine._spawn_mob(engine.world.rooms[unsafe_room].mob_spawns[0]["mob"], unsafe_room)
    mob2 = engine.mobs[mob2_id]
    tmpl2 = engine.world.get_mob_template(mob2.template_id)
    keyword = tmpl2.name.split()[-1]  # find_mob_in_room matches by substring of the display name
    hp_before = mob2.hp
    await cmd.do_use(rctx, f"ambush {keyword}")  # backstab-kind, found by keyword
    assert mob2.hp < hp_before or mob2.hp <= 0, LOG[-1]
    assert "ambush" in r.skill_cooldowns
    print("OK: rogue ambush (backstab-kind 'use') resolves by keyword lookup")

    await cmd.do_use(rctx, "stealth")  # invisibility
    assert time.time() < r.invisible_until

    r.in_combat_with = mob2.instance_id
    mob2.target_name = r.name
    await cmd.do_use(rctx, "vanish")
    assert time.time() < r.invisible_until and r.in_combat_with is None
    print("OK: rogue 'use' skills (invisibility/vanish) resolve")


async def test_level_cap(engine):
    p = Player.new_character("OfflineTestCap", "human", "warrior")
    p.level = MAX_LEVEL - 1
    p.xp = (MAX_LEVEL - 1) * 100  # exactly enough to ding to MAX_LEVEL
    await engine.maybe_level_up(p)
    assert p.level == MAX_LEVEL, p.level
    assert p.xp == 0

    p.xp = 99999
    await engine.maybe_level_up(p)
    assert p.level == MAX_LEVEL, "level exceeded cap!"
    assert p.xp == 0, "xp not drained once capped"
    print(f"OK: level cap holds at {MAX_LEVEL}, xp drains instead of overflowing")


async def main():
    world = World()
    engine = GameEngine(world)

    await test_trainer_attached_and_unattackable(engine)
    await test_learn_gating(engine)
    await test_cast_all_kinds(engine)
    await test_use_all_kinds(engine)
    await test_level_cap(engine)

    print(f"\n{len(LOG)} log lines captured; sample tail:")
    for line in LOG[-8:]:
        print(" ", line)
    print("\nALL OFFLINE ABILITY/TRAINER/LEVEL-CAP TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
