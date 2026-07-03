"""Command parser & handlers. Each player command turns into one of the
do_* functions below, operating on a CommandContext (engine + player)."""
from __future__ import annotations
import random
import re
import time
from . import auth
from . import colors as c
from . import npc_ai
from . import persistence

DIRECTIONS = {
    "n": "north", "s": "south", "e": "east", "w": "west", "u": "up", "d": "down",
    "north": "north", "south": "south", "east": "east", "west": "west", "up": "up", "down": "down",
}

OPPOSITE_DIRECTION = {
    "north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up",
}

ABILITIES = {
    # ---- Mage spells ----
    "missile": {"class": "mage", "type": "spell", "level_req": 1, "cost": 8, "learn_cost": 0,
                "kind": "damage", "dmg_min": 4, "dmg_max": 10, "verb": "missile of force"},
    "spark": {"class": "mage", "type": "spell", "level_req": 5, "cost": 5, "learn_cost": 30,
              "kind": "damage", "dmg_min": 2, "dmg_max": 6, "verb": "spark of flame"},
    "frost_lance": {"class": "mage", "type": "spell", "level_req": 12, "cost": 14, "learn_cost": 80,
                    "kind": "damage", "dmg_min": 10, "dmg_max": 18, "verb": "lance of frost"},
    "veil": {"class": "mage", "type": "spell", "level_req": 20, "cost": 18, "learn_cost": 150,
             "kind": "invisibility", "duration": 90, "verb": "a veil of unseeing"},
    "mind_spike": {"class": "mage", "type": "spell", "level_req": 35, "cost": 20, "learn_cost": 250,
                   "kind": "damage", "dmg_min": 18, "dmg_max": 28, "verb": "spike of pure thought"},
    "arcane_bolt": {"class": "mage", "type": "spell", "level_req": 50, "cost": 26, "learn_cost": 400,
                    "kind": "damage", "dmg_min": 26, "dmg_max": 40, "verb": "arcane bolt"},
    "font_of_mana": {"class": "mage", "type": "spell", "level_req": 65, "cost": 0, "learn_cost": 550,
                      "kind": "mana_restore", "amount_min": 30, "amount_max": 50, "verb": "the font of mana"},
    "shatter_ward": {"class": "mage", "type": "spell", "level_req": 80, "cost": 36, "learn_cost": 750,
                      "kind": "damage", "dmg_min": 40, "dmg_max": 60, "verb": "wave of shattering force"},
    "arcane_nova": {"class": "mage", "type": "spell", "level_req": 95, "cost": 45, "learn_cost": 1000,
                    "kind": "damage", "dmg_min": 55, "dmg_max": 80, "verb": "nova of raw arcane force"},

    # ---- Cleric spells ----
    "heal": {"class": "cleric", "type": "spell", "level_req": 1, "cost": 10, "learn_cost": 0,
             "kind": "heal", "heal_min": 12, "heal_max": 22, "verb": "channel divine light"},
    "bless": {"class": "cleric", "type": "spell", "level_req": 5, "cost": 8, "learn_cost": 30,
              "kind": "buff_dmg", "amount": 3, "duration": 60, "verb": "Bless"},
    "mend": {"class": "cleric", "type": "spell", "level_req": 12, "cost": 16, "learn_cost": 80,
             "kind": "heal", "heal_min": 22, "heal_max": 34, "verb": "channel mending light"},
    "smite": {"class": "cleric", "type": "spell", "level_req": 20, "cost": 14, "learn_cost": 150,
              "kind": "damage", "dmg_min": 12, "dmg_max": 20, "verb": "radiant smite"},
    "ward": {"class": "cleric", "type": "spell", "level_req": 35, "cost": 14, "learn_cost": 250,
             "kind": "buff_armor", "amount": 4, "duration": 60, "verb": "Ward"},
    "greater_heal": {"class": "cleric", "type": "spell", "level_req": 50, "cost": 24, "learn_cost": 400,
                      "kind": "heal", "heal_min": 36, "heal_max": 54, "verb": "channel radiant light"},
    "sanctuary": {"class": "cleric", "type": "spell", "level_req": 65, "cost": 0, "learn_cost": 550,
                  "kind": "full_restore", "verb": "Sanctuary"},
    "judgment": {"class": "cleric", "type": "spell", "level_req": 80, "cost": 32, "learn_cost": 750,
                 "kind": "damage", "dmg_min": 36, "dmg_max": 56, "verb": "lance of judgment"},
    "divine_grace": {"class": "cleric", "type": "spell", "level_req": 95, "cost": 40, "learn_cost": 1000,
                      "kind": "heal", "heal_min": 70, "heal_max": 100, "verb": "channel divine grace"},

    # ---- Warrior skills ----
    "bash": {"class": "warrior", "type": "skill", "level_req": 1, "cooldown": 6, "learn_cost": 0,
             "kind": "attack_bonus", "bonus_min": 4, "bonus_max": 8, "verb": "bash"},
    "rally": {"class": "warrior", "type": "skill", "level_req": 5, "cooldown": 30, "learn_cost": 30,
              "kind": "buff_dmg", "amount": 4, "duration": 30, "verb": "rally"},
    "cleave": {"class": "warrior", "type": "skill", "level_req": 12, "cooldown": 8, "learn_cost": 80,
               "kind": "attack_bonus", "bonus_min": 8, "bonus_max": 14, "verb": "cleave"},
    "guard_stance": {"class": "warrior", "type": "skill", "level_req": 20, "cooldown": 30, "learn_cost": 150,
                      "kind": "buff_armor", "amount": 5, "duration": 45, "verb": "guard stance"},
    "second_wind": {"class": "warrior", "type": "skill", "level_req": 35, "cooldown": 60, "learn_cost": 250,
                     "kind": "self_heal", "heal_min": 20, "heal_max": 35, "verb": "second wind"},
    "relentless_strike": {"class": "warrior", "type": "skill", "level_req": 50, "cooldown": 10, "learn_cost": 400,
                            "kind": "attack_bonus", "bonus_min": 16, "bonus_max": 24, "verb": "relentless strike"},
    "battle_shout": {"class": "warrior", "type": "skill", "level_req": 65, "cooldown": 45, "learn_cost": 550,
                       "kind": "buff_dmg", "amount": 8, "duration": 45, "verb": "battle shout"},
    "execute": {"class": "warrior", "type": "skill", "level_req": 80, "cooldown": 12, "learn_cost": 750,
                "kind": "attack_bonus", "bonus_min": 20, "bonus_max": 30, "execute_mult": 3, "verb": "execute"},
    "warlords_fury": {"class": "warrior", "type": "skill", "level_req": 95, "cooldown": 15, "learn_cost": 1000,
                        "kind": "attack_bonus", "bonus_min": 30, "bonus_max": 45, "verb": "warlord's fury"},

    # ---- Rogue skills ----
    "backstab": {"class": "rogue", "type": "skill", "level_req": 1, "cooldown": 0, "learn_cost": 0,
                 "kind": "backstab", "mult": 3, "verb": "backstab"},
    "stealth": {"class": "rogue", "type": "skill", "level_req": 5, "cooldown": 30, "learn_cost": 30,
                "kind": "invisibility", "duration": 60, "verb": "stealth"},
    "vanish": {"class": "rogue", "type": "skill", "level_req": 12, "cooldown": 45, "learn_cost": 80,
               "kind": "vanish", "duration": 20, "verb": "vanish"},
    "poison_blade": {"class": "rogue", "type": "skill", "level_req": 20, "cooldown": 10, "learn_cost": 150,
                      "kind": "attack_bonus", "bonus_min": 10, "bonus_max": 16, "verb": "poison blade"},
    "dirty_trick": {"class": "rogue", "type": "skill", "level_req": 35, "cooldown": 8, "learn_cost": 250,
                     "kind": "attack_bonus", "bonus_min": 14, "bonus_max": 22, "verb": "dirty trick"},
    "shadowstep": {"class": "rogue", "type": "skill", "level_req": 50, "cooldown": 20, "learn_cost": 400,
                    "kind": "backstab", "mult": 4, "ignore_target": True, "verb": "shadowstep"},
    "ambush": {"class": "rogue", "type": "skill", "level_req": 65, "cooldown": 25, "learn_cost": 550,
               "kind": "backstab", "mult": 5, "verb": "ambush"},
    "assassinate": {"class": "rogue", "type": "skill", "level_req": 80, "cooldown": 30, "learn_cost": 750,
                      "kind": "backstab", "mult": 6, "verb": "assassinate"},
    "master_thiefs_strike": {"class": "rogue", "type": "skill", "level_req": 95, "cooldown": 35, "learn_cost": 1000,
                                "kind": "backstab", "mult": 8, "verb": "a master thief's strike"},
}

HELP_TEXT = (
    "Available commands:<br>"
    "&nbsp;&nbsp;movement: north/south/east/west/up/down (n/s/e/w/u/d)<br>"
    "&nbsp;&nbsp;look [target], consider/con &lt;target&gt;, score, inventory (i), equipment (eq)<br>"
    "&nbsp;&nbsp;lore (history) &mdash; read the deeper history of where you stand, if any<br>"
    "&nbsp;&nbsp;say &lt;msg&gt;, emote &lt;action&gt;, shout &lt;msg&gt;, who<br>"
    "&nbsp;&nbsp;get &lt;item&gt;, drop &lt;item&gt;, wear/wield &lt;item&gt;, remove &lt;item&gt;<br>"
    "&nbsp;&nbsp;quaff/drink &lt;item&gt; &mdash; consume a potion or ration<br>"
    "&nbsp;&nbsp;kill &lt;target&gt;, flee, rest, wake<br>"
    "&nbsp;&nbsp;cast &lt;spell&gt; [target] &mdash; mage/cleric spells you've learned<br>"
    "&nbsp;&nbsp;bash &lt;target&gt; (warrior), backstab &lt;target&gt; (rogue) &mdash; starter skills<br>"
    "&nbsp;&nbsp;use &lt;skill&gt; [target] &mdash; any other warrior/rogue skill you've learned<br>"
    "&nbsp;&nbsp;skills &mdash; see your class's full ability list and what you've learned<br>"
    "&nbsp;&nbsp;learn &lt;ability&gt; &mdash; learn a spell/skill from your guild's trainer (must be present, leveled up, and pay the fee)<br>"
    "&nbsp;&nbsp;list, buy &lt;item&gt;, sell &lt;item&gt; &mdash; in shops<br>"
    "&nbsp;&nbsp;pray &mdash; at the Temple of the Dawn<br>"
    "&nbsp;&nbsp;open chest &mdash; where applicable<br>"
    "&nbsp;&nbsp;talk &lt;npc&gt; [message] &mdash; speak with a trainer, shopkeeper, or priestess<br>"
    "&nbsp;&nbsp;changepass &lt;old&gt; &lt;new&gt;<br>"
    "&nbsp;&nbsp;help, quit"
)

ADMIN_HELP_TEXT = (
    "<br>Staff commands (admin &amp; assistant admin):<br>"
    "&nbsp;&nbsp;kick &lt;character&gt; &mdash; disconnect an online player<br>"
    "&nbsp;&nbsp;listplayers &mdash; list all saved characters<br>"
    "&nbsp;&nbsp;setlevel &lt;character&gt; &lt;level&gt; &mdash; set a character's level<br>"
    "&nbsp;&nbsp;setstat &lt;character&gt; &lt;stat&gt; &lt;value&gt; &mdash; set str/dex/con/int/wis (1-25)<br>"
    "<br>Admin-only commands:<br>"
    "&nbsp;&nbsp;deleteplayer &lt;character&gt; &mdash; permanently delete a saved character<br>"
    "&nbsp;&nbsp;makeassistant &lt;character&gt; on|off &mdash; grant/revoke assistant admin<br>"
    "&nbsp;&nbsp;rooms &mdash; list every room id<br>"
    "&nbsp;&nbsp;goto &lt;room_id&gt; &mdash; teleport there<br>"
    "&nbsp;&nbsp;dig &lt;direction&gt; &lt;room_id&gt; [name...] &mdash; create a room, exit-linked both ways<br>"
    "&nbsp;&nbsp;rlink &lt;direction&gt; &lt;room_id&gt; &mdash; link an exit to an existing room (one-way)<br>"
    "&nbsp;&nbsp;runlink &lt;direction&gt; &mdash; remove an exit from the current room<br>"
    "&nbsp;&nbsp;rname &lt;text&gt;, rdesc &lt;text&gt; &mdash; rename / redescribe the current room<br>"
    "&nbsp;&nbsp;rlore &lt;text&gt; &mdash; set the current room's 'lore' text (read with the lore command)<br>"
    "&nbsp;&nbsp;rsafe on|off &mdash; toggle whether combat is allowed in the current room<br>"
    "&nbsp;&nbsp;setpass &lt;character&gt; &lt;newpassword&gt; &mdash; reset anyone's password<br>"
    "&nbsp;&nbsp;makeadmin &lt;character&gt; on|off &mdash; grant/revoke admin<br>"
    "&nbsp;&nbsp;setmaxplayers &lt;n&gt; &mdash; cap total accounts (0 = unlimited)<br>"
    "&nbsp;&nbsp;lockregistration on|off &mdash; block/allow new account creation<br>"
    "&nbsp;&nbsp;checkai &mdash; test connectivity to the Ollama NPC AI server"
)


class QuitRequested(Exception):
    """Raised by do_quit and propagated up to main.py to close the socket."""


class CommandContext:
    def __init__(self, engine, player):
        self.engine = engine
        self.player = player
        self.world = engine.world


def _match_item_in_list(ctx, item_ids, keyword):
    keyword = (keyword or "").lower().strip()
    if not keyword:
        return None
    for iid in item_ids:
        tmpl = ctx.world.get_item(iid)
        name = tmpl.name.lower() if tmpl else iid
        if keyword in name or keyword in iid.replace("_", " "):
            return iid
    return None


async def dispatch(ctx: CommandContext, raw: str):
    raw = (raw or "").strip()
    if not raw:
        return
    if raw.startswith('"') or raw.startswith("'"):
        raw = "say " + raw[1:]

    parts = raw.split(None, 1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in DIRECTIONS:
        await do_move(ctx, DIRECTIONS[cmd])
    elif cmd in ("look", "l"):
        await do_look(ctx, arg)
    elif cmd in ("consider", "con"):
        await do_look(ctx, arg)
    elif cmd in ("lore", "history"):
        await do_lore(ctx)
    elif cmd == "say":
        await do_say(ctx, arg)
    elif cmd == "emote":
        await do_emote(ctx, arg)
    elif cmd in ("shout", "gossip"):
        await do_shout(ctx, arg)
    elif cmd == "who":
        await do_who(ctx)
    elif cmd in ("inventory", "i", "inv"):
        await do_inventory(ctx)
    elif cmd in ("equipment", "eq"):
        await do_equipment(ctx)
    elif cmd in ("score", "stats", "sc"):
        await do_score(ctx)
    elif cmd in ("get", "take"):
        await do_get(ctx, arg)
    elif cmd == "drop":
        await do_drop(ctx, arg)
    elif cmd in ("wear", "wield"):
        await do_wear(ctx, arg)
    elif cmd == "remove":
        await do_remove(ctx, arg)
    elif cmd in ("quaff", "drink"):
        await do_quaff(ctx, arg)
    elif cmd in ("kill", "attack", "k"):
        await do_kill(ctx, arg)
    elif cmd == "flee":
        await do_flee(ctx)
    elif cmd == "rest":
        await do_rest(ctx)
    elif cmd == "wake":
        await do_wake(ctx)
    elif cmd == "cast":
        await do_cast(ctx, arg)
    elif cmd == "bash":
        await do_bash(ctx, arg)
    elif cmd == "backstab":
        await do_backstab(ctx, arg)
    elif cmd == "use":
        await do_use(ctx, arg)
    elif cmd in ("skills", "spells", "abilities"):
        await do_skills(ctx)
    elif cmd == "learn":
        await do_learn(ctx, arg)
    elif cmd == "list":
        await do_list(ctx)
    elif cmd == "buy":
        await do_buy(ctx, arg)
    elif cmd == "sell":
        await do_sell(ctx, arg)
    elif cmd == "pray":
        await do_pray(ctx)
    elif cmd == "open":
        await do_open(ctx, arg)
    elif cmd == "talk":
        await do_talk(ctx, arg)
    elif cmd == "changepass":
        await do_changepass(ctx, arg)
    elif cmd == "kick":
        await do_kick(ctx, arg)
    elif cmd == "listplayers":
        await do_listplayers(ctx)
    elif cmd == "deleteplayer":
        await do_deleteplayer(ctx, arg)
    elif cmd == "setlevel":
        await do_setlevel(ctx, arg)
    elif cmd == "setstat":
        await do_setstat(ctx, arg)
    elif cmd == "makeassistant":
        await do_makeassistant(ctx, arg)
    elif cmd == "setpass":
        await do_setpass(ctx, arg)
    elif cmd == "makeadmin":
        await do_makeadmin(ctx, arg)
    elif cmd == "setmaxplayers":
        await do_setmaxplayers(ctx, arg)
    elif cmd == "lockregistration":
        await do_lockregistration(ctx, arg)
    elif cmd == "checkai":
        await do_checkai(ctx)
    elif cmd == "rooms":
        await do_rooms(ctx)
    elif cmd == "goto":
        await do_goto(ctx, arg)
    elif cmd == "dig":
        await do_dig(ctx, arg)
    elif cmd == "rlink":
        await do_rlink(ctx, arg)
    elif cmd == "runlink":
        await do_runlink(ctx, arg)
    elif cmd == "rname":
        await do_rname(ctx, arg)
    elif cmd == "rdesc":
        await do_rdesc(ctx, arg)
    elif cmd == "rlore":
        await do_rlore(ctx, arg)
    elif cmd == "rsafe":
        await do_rsafe(ctx, arg)
    elif cmd in ("help", "?"):
        text = HELP_TEXT + (ADMIN_HELP_TEXT if _is_staff(ctx.player) else "")
        await ctx.engine.send(ctx.player, c.help_(text))
    elif cmd == "quit":
        await do_quit(ctx)
    else:
        await ctx.engine.send(ctx.player, c.error(f"Unknown command: '{cmd}'. Type 'help' for a list."))


# ---------------------------------------------------------------------------
# Movement / look
# ---------------------------------------------------------------------------

async def do_move(ctx, direction):
    p = ctx.player
    if p.in_combat_with:
        await ctx.engine.send(p, c.error("You can't leave while fighting! Try to flee."))
        return
    room = ctx.world.get_room(p.room_id)
    dest_id = room.exits.get(direction)
    if not dest_id:
        await ctx.engine.send(p, c.error("You can't go that way."))
        return
    invisible = time.time() < p.invisible_until
    if not invisible:
        await ctx.engine.send_room(p.room_id, c.system(f"{p.name} leaves {direction}."), exclude_names=(p.name,))
    p.room_id = dest_id
    if not invisible:
        await ctx.engine.send_room(dest_id, c.system(f"{p.name} arrives."), exclude_names=(p.name,))
    await do_look(ctx, "")


def _mob_difficulty(player_level: int, mob_level: int) -> str:
    diff = mob_level - player_level
    if diff <= -6:
        return "It poses no real threat to you."
    elif diff <= -3:
        return "It looks manageable — well within your abilities."
    elif diff <= 2:
        return "It looks like a fair fight."
    elif diff <= 5:
        return "It looks dangerous. You should approach with caution."
    else:
        return "It would be deadly to face. Only a fool charges in unprepared."


def _player_appearance(other) -> str:
    race_desc = {
        "human":    "a human of average build",
        "elf":      "a slender elf with sharp eyes and long limbs",
        "dwarf":    "a stocky dwarf, broad-shouldered and solid as hearthstone",
        "halfling": "a small halfling, light-footed and keen-eyed",
    }.get(other.race, f"a {other.race}")
    class_desc = {
        "warrior": "bearing the hardened look of someone who has taken as many blows as they've dealt",
        "mage":    "with an air of intense focus and faint arcane residue clinging to their clothes",
        "cleric":  "moving with a serene deliberateness, as though guided by something you can't quite see",
        "rogue":   "carrying themselves with a quiet economy of movement that suggests old, careful habits",
    }.get(other.klass, "")
    return f"{race_desc}, {class_desc}"


def _player_worn_desc(other, world) -> str:
    worn = []
    for slot, iid in other.equipment.items():
        tmpl = world.get_item(iid)
        if tmpl:
            worn.append(tmpl.name)
    if worn:
        return "They are wearing: " + ", ".join(worn) + "."
    return "They wear no visible equipment."


async def do_look(ctx, arg):
    p = ctx.player
    room = ctx.world.get_room(p.room_id)

    if arg:
        if room.trainer and arg.lower() in room.trainer.name.lower():
            t = room.trainer
            await ctx.engine.send(
                p, f"{c.player(t.name)}, {c.esc(t.title)} of the {c.esc(t.klass.capitalize())}s' Guild "
                   f"(level {t.level}).<br>{c.esc(t.description)}")
            return
        mob = ctx.engine.find_mob_in_room(p.room_id, arg)
        if mob:
            tmpl = ctx.world.get_mob_template(mob.template_id)
            difficulty = _mob_difficulty(p.level, tmpl.level)
            await ctx.engine.send(
                p, f"{c.mob(tmpl.name)}<br>{c.esc(tmpl.description)}<br>{c.system(difficulty)}")
            return
        other = ctx.engine.find_player_in_room(p.room_id, arg, exclude=p.name)
        if other:
            appearance = _player_appearance(other)
            worn = _player_worn_desc(other, ctx.world)
            await ctx.engine.send(
                p, f"{c.player(other.name)} is {appearance}.<br>{c.esc(worn)}")
            return
        iid = _match_item_in_list(ctx, p.inventory, arg) or _match_item_in_list(ctx, ctx.engine.ground.get(p.room_id, []), arg)
        if iid:
            tmpl = ctx.world.get_item(iid)
            await ctx.engine.send(p, f"{c.item(tmpl.name)}<br>{c.esc(tmpl.description)}")
            return
        await ctx.engine.send(p, c.error("You don't see that here."))
        return

    lines = [c.room(c.esc(room.name)), c.esc(room.description)]
    exits = ", ".join(sorted(room.exits.keys())) or "none"
    lines.append(f"Exits: {c.exit_(exits)}")

    if room.trainer:
        t = room.trainer
        lines.append(f"{c.player(t.name)}, {c.esc(t.title)} of the {c.esc(t.klass.capitalize())}s' Guild, is here.")

    for m in ctx.engine.mobs_in_room(room.id):
        tmpl = ctx.world.get_mob_template(m.template_id)
        lines.append(f"{c.mob(tmpl.name.capitalize())} is here.")

    now = time.time()
    for other in ctx.engine.players_in_room(room.id, exclude=p.name):
        if now < other.invisible_until and not p.is_admin:
            continue
        lines.append(f"{c.player(other.name)} is here.")

    for iid in ctx.engine.ground.get(room.id, []):
        tmpl = ctx.world.get_item(iid)
        lines.append(f"{c.item(tmpl.name)} is on the ground.")

    if room.shop:
        lines.append(c.help_("The shopkeep eyes your coin purse. (try 'list', 'buy &lt;item&gt;', or 'talk shopkeeper')"))
    if "heal" in room.services:
        lines.append(c.help_("You may 'pray' here to be healed. The priestess is also willing to talk."))
    if room.trainer:
        lines.append(c.help_(f"(You can 'talk {room.trainer.name.split()[0].lower()}' to speak with the trainer.)"))
    if room.container and not ctx.engine.is_container_opened(room.id):
        lines.append(c.item(f"There is {room.container.name} here. (try 'open chest')"))
    if room.lore:
        lines.append(c.help_("There's a deeper history here. (try 'lore')"))

    await ctx.engine.send(p, "<br>".join(lines))


async def do_lore(ctx):
    p = ctx.player
    room = ctx.world.get_room(p.room_id)
    if not room.lore:
        await ctx.engine.send(p, c.system("There's nothing more to learn here."))
        return
    await ctx.engine.send(p, f"{c.help_('You recall what you know of this place:')}<br>{c.esc(room.lore)}")


async def do_say(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Say what?"))
        return
    await ctx.engine.send(p, f'You say, "{c.say(arg)}"')
    await ctx.engine.send_room(p.room_id, f'{c.player(p.name)} says, "{c.say(arg)}"', exclude_names=(p.name,))


async def do_emote(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Emote what?"))
        return
    await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} {c.say(arg)}")


async def do_shout(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Shout what?"))
        return
    await ctx.engine.broadcast(f'{c.player(p.name)} shouts, "{c.say(arg)}"')


async def do_who(ctx):
    p = ctx.player
    online = [x for x in ctx.engine.players.values() if x.connected]
    lines = [c.help_(f"Players online ({len(online)}):")]
    for other in online:
        tag = f" {c.admin('[admin]')}" if other.is_admin else ""
        lines.append(f"&nbsp;&nbsp;{c.player(other.name)} &mdash; level {other.level} {other.race} {other.klass}{tag}")
    await ctx.engine.send(p, "<br>".join(lines))


async def do_inventory(ctx):
    p = ctx.player
    if not p.inventory:
        await ctx.engine.send(p, c.system("You aren't carrying anything."))
        return
    lines = [c.help_("You are carrying:")]
    for iid in p.inventory:
        tmpl = ctx.world.get_item(iid)
        worn = " (worn)" if iid in p.equipment.values() else ""
        lines.append(f"&nbsp;&nbsp;{c.item(tmpl.name)}{worn}")
    await ctx.engine.send(p, "<br>".join(lines))


async def do_equipment(ctx):
    p = ctx.player
    if not p.equipment:
        await ctx.engine.send(p, c.system("You aren't wearing anything."))
        return
    lines = [c.help_("You are wearing:")]
    for slot, iid in p.equipment.items():
        tmpl = ctx.world.get_item(iid)
        lines.append(f"&nbsp;&nbsp;&lt;{slot}&gt; {c.item(tmpl.name)}")
    await ctx.engine.send(p, "<br>".join(lines))


async def do_score(ctx):
    p = ctx.player
    lines = [
        c.help_(f"{c.esc(p.name)} the {c.esc(p.race)} {c.esc(p.klass)} &mdash; Level {p.level}"),
        f"HP: {c.heal(p.hp)}/{p.max_hp} &nbsp; Mana: {c.tag(str(p.mana), 'c-mana')}/{p.max_mana} &nbsp; Gold: {c.gold(p.gold)}",
        f"XP: {p.xp}/{p.level * 100}",
        f"STR {p.stats.get('str')} &nbsp; DEX {p.stats.get('dex')} &nbsp; CON {p.stats.get('con')} &nbsp; "
        f"INT {p.stats.get('int')} &nbsp; WIS {p.stats.get('wis')}",
    ]
    await ctx.engine.send(p, "<br>".join(lines))


async def do_get(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Get what?"))
        return
    ground = ctx.engine.ground.get(p.room_id, [])
    iid = _match_item_in_list(ctx, ground, arg)
    if not iid:
        await ctx.engine.send(p, c.error("You don't see that here."))
        return
    ground.remove(iid)
    p.inventory.append(iid)
    tmpl = ctx.world.get_item(iid)
    await ctx.engine.send(p, f"You pick up {c.item(tmpl.name)}.")
    await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} picks up {c.item(tmpl.name)}.", exclude_names=(p.name,))


async def do_drop(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Drop what?"))
        return
    iid = _match_item_in_list(ctx, p.inventory, arg)
    if not iid:
        await ctx.engine.send(p, c.error("You aren't carrying that."))
        return
    for slot, eid in list(p.equipment.items()):
        if eid == iid:
            del p.equipment[slot]
    p.inventory.remove(iid)
    ctx.engine.ground.setdefault(p.room_id, []).append(iid)
    tmpl = ctx.world.get_item(iid)
    await ctx.engine.send(p, f"You drop {c.item(tmpl.name)}.")
    await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} drops {c.item(tmpl.name)}.", exclude_names=(p.name,))


async def do_wear(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Wear what?"))
        return
    iid = _match_item_in_list(ctx, p.inventory, arg)
    if not iid:
        await ctx.engine.send(p, c.error("You aren't carrying that."))
        return
    tmpl = ctx.world.get_item(iid)
    if tmpl.slot not in ("weapon", "armor", "shield"):
        await ctx.engine.send(p, c.error(f"You can't wear {tmpl.name}."))
        return
    p.equipment[tmpl.slot] = iid
    await ctx.engine.send(p, f"You wear {c.item(tmpl.name)}.")


async def do_remove(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Remove what?"))
        return
    iid = _match_item_in_list(ctx, list(p.equipment.values()), arg)
    if not iid:
        await ctx.engine.send(p, c.error("You aren't wearing that."))
        return
    for slot, eid in list(p.equipment.items()):
        if eid == iid:
            del p.equipment[slot]
    tmpl = ctx.world.get_item(iid)
    await ctx.engine.send(p, f"You remove {c.item(tmpl.name)}.")


async def do_quaff(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Quaff what?"))
        return
    iid = _match_item_in_list(ctx, p.inventory, arg)
    if not iid:
        await ctx.engine.send(p, c.error("You aren't carrying that."))
        return
    tmpl = ctx.world.get_item(iid)
    if tmpl.slot != "consumable":
        await ctx.engine.send(p, c.error(f"You can't quaff {tmpl.name}."))
        return
    p.inventory.remove(iid)
    parts = []
    if tmpl.heal:
        before = p.hp
        p.hp = min(p.max_hp, p.hp + tmpl.heal)
        restored = p.hp - before
        if restored:
            parts.append(f"{c.heal(str(restored))} hp")
    if tmpl.mana:
        before = p.mana
        p.mana = min(p.max_mana, p.mana + tmpl.mana)
        restored = p.mana - before
        if restored:
            parts.append(f"{c.tag(str(restored), 'c-mana')} mana")
    if parts:
        await ctx.engine.send(p, f"You quaff {c.item(tmpl.name)}, restoring {' and '.join(parts)}.")
    else:
        await ctx.engine.send(p, f"You consume {c.item(tmpl.name)}. It doesn't seem to do anything.")


async def do_kill(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Kill what?"))
        return
    room = ctx.world.get_room(p.room_id)
    if room.safe:
        await ctx.engine.send(p, c.error("You can't start a fight here."))
        return
    if p.in_combat_with:
        await ctx.engine.send(p, c.error("You're already fighting!"))
        return
    mob = ctx.engine.find_mob_in_room(p.room_id, arg)
    if not mob:
        await ctx.engine.send(p, c.error("You don't see that here."))
        return
    p.in_combat_with = mob.instance_id
    mob.target_name = p.name
    tmpl = ctx.world.get_mob_template(mob.template_id)
    await ctx.engine.send(p, f"You attack {c.mob(tmpl.name)}!")
    await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} attacks {c.mob(tmpl.name)}!", exclude_names=(p.name,))


async def do_flee(ctx):
    p = ctx.player
    if not p.in_combat_with:
        await ctx.engine.send(p, c.error("You aren't fighting anything."))
        return
    room = ctx.world.get_room(p.room_id)
    exits = list(room.exits.items())
    if not exits:
        await ctx.engine.send(p, c.error("There's nowhere to flee!"))
        return
    direction, dest = random.choice(exits)
    inst = ctx.engine.mobs.get(p.in_combat_with)
    if inst:
        inst.target_name = None
    p.in_combat_with = None
    await ctx.engine.send(p, f"You flee {direction}!")
    await ctx.engine.send_room(p.room_id, c.system(f"{p.name} flees {direction}!"), exclude_names=(p.name,))
    p.room_id = dest
    await ctx.engine.send_room(dest, c.system(f"{p.name} bursts in, fleeing!"), exclude_names=(p.name,))
    await do_look(ctx, "")


async def do_rest(ctx):
    p = ctx.player
    if p.in_combat_with:
        await ctx.engine.send(p, c.error("You can't rest while fighting!"))
        return
    p.resting = True
    await ctx.engine.send(p, c.system("You sit down and rest, recovering faster."))


async def do_wake(ctx):
    p = ctx.player
    p.resting = False
    await ctx.engine.send(p, c.system("You stand up."))


async def do_cast(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Cast what?"))
        return
    parts = arg.split(None, 1)
    spell = parts[0].lower()
    target_kw = parts[1].strip() if len(parts) > 1 else ""
    spec = ABILITIES.get(spell)
    if not spec or spec["type"] != "spell":
        await ctx.engine.send(p, c.error("You don't know that spell."))
        return
    if p.klass != spec["class"]:
        await ctx.engine.send(p, c.error("You don't know how to cast that."))
        return
    if spell not in p.known_skills:
        await ctx.engine.send(p, c.error("You haven't learned that spell yet."))
        return
    if p.level < spec["level_req"]:
        await ctx.engine.send(p, c.error(f"You must be level {spec['level_req']} to cast that."))
        return
    if p.mana < spec["cost"]:
        await ctx.engine.send(p, c.error("You don't have enough mana."))
        return

    kind = spec["kind"]

    if kind == "damage":
        room = ctx.world.get_room(p.room_id)
        if room.safe:
            await ctx.engine.send(p, c.error("You can't start a fight here."))
            return
        mob = ctx.engine.mobs.get(p.in_combat_with) if p.in_combat_with else None
        if not mob and target_kw:
            mob = ctx.engine.find_mob_in_room(p.room_id, target_kw)
        if not mob:
            await ctx.engine.send(p, c.error("Cast it at what?"))
            return
        p.mana -= spec["cost"]
        tmpl = ctx.world.get_mob_template(mob.template_id)
        dmg = random.randint(spec["dmg_min"], spec["dmg_max"])
        mob.hp -= dmg
        p.in_combat_with = mob.instance_id
        mob.target_name = p.name
        await ctx.engine.send(p, f"Your {spec['verb']} strikes {c.mob(tmpl.name)} for {c.dmg(dmg)} damage!")
        await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} hurls {spec['verb']} at {c.mob(tmpl.name)}!",
                                    exclude_names=(p.name,))
        if mob.hp <= 0:
            await ctx.engine.resolve_mob_death(mob, tmpl, p)

    elif kind == "heal":
        target = p
        if target_kw:
            other = ctx.engine.find_player_in_room(p.room_id, target_kw)
            if other:
                target = other
        p.mana -= spec["cost"]
        amount = random.randint(spec["heal_min"], spec["heal_max"])
        target.hp = min(target.max_hp, target.hp + amount)
        await ctx.engine.send(p, f"You {spec['verb']}, healing {c.heal(amount)} points.")
        if target is not p:
            await ctx.engine.send(target, f"{c.player(p.name)} heals you for {c.heal(amount)} points.")

    elif kind == "buff_dmg":
        target = p
        if target_kw:
            other = ctx.engine.find_player_in_room(p.room_id, target_kw)
            if other:
                target = other
        p.mana -= spec["cost"]
        target.dmg_buff_until = time.time() + spec["duration"]
        target.dmg_buff_amount = spec["amount"]
        await ctx.engine.send(p, f"You cast {spec['verb']}!")
        if target is not p:
            await ctx.engine.send(target, f"{c.player(p.name)} casts {spec['verb']} on you!")

    elif kind == "buff_armor":
        target = p
        if target_kw:
            other = ctx.engine.find_player_in_room(p.room_id, target_kw)
            if other:
                target = other
        p.mana -= spec["cost"]
        target.armor_buff_until = time.time() + spec["duration"]
        target.armor_buff_amount = spec["amount"]
        await ctx.engine.send(p, f"You cast {spec['verb']}!")
        if target is not p:
            await ctx.engine.send(target, f"{c.player(p.name)} casts {spec['verb']} on you!")

    elif kind == "invisibility":
        p.mana -= spec["cost"]
        p.invisible_until = time.time() + spec["duration"]
        await ctx.engine.send(p, f"You weave {spec['verb']} and fade from sight for {spec['duration']}s.")

    elif kind == "mana_restore":
        p.mana -= spec["cost"]
        amount = random.randint(spec["amount_min"], spec["amount_max"])
        p.mana = min(p.max_mana, p.mana + amount)
        await ctx.engine.send(p, f"You draw upon {spec['verb']}, restoring {c.tag(str(amount), 'c-mana')} mana.")

    elif kind == "full_restore":
        p.mana -= spec["cost"]
        p.hp = p.max_hp
        p.mana = p.max_mana
        await ctx.engine.send(p, f"You invoke {spec['verb']}! You are fully restored.")


async def do_bash(ctx, arg):
    p = ctx.player
    if p.klass != "warrior":
        await ctx.engine.send(p, c.error("You don't know how to bash."))
        return
    now = time.time()
    if now < p.cooldown_until:
        await ctx.engine.send(p, c.error(f"You're not ready to bash again ({int(p.cooldown_until - now)}s)."))
        return
    room = ctx.world.get_room(p.room_id)
    if room.safe:
        await ctx.engine.send(p, c.error("You can't start a fight here."))
        return
    mob = ctx.engine.mobs.get(p.in_combat_with) if p.in_combat_with else None
    if not mob and arg:
        mob = ctx.engine.find_mob_in_room(p.room_id, arg)
    if not mob:
        await ctx.engine.send(p, c.error("Bash what?"))
        return
    tmpl = ctx.world.get_mob_template(mob.template_id)
    dmg = ctx.engine.roll_player_damage(p) + random.randint(4, 8)
    mob.hp -= dmg
    p.in_combat_with = mob.instance_id
    mob.target_name = p.name
    p.cooldown_until = now + 6
    await ctx.engine.send(p, f"You bash {c.mob(tmpl.name)} for {c.dmg(dmg)} damage!")
    await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} bashes {c.mob(tmpl.name)}!", exclude_names=(p.name,))
    if mob.hp <= 0:
        await ctx.engine.resolve_mob_death(mob, tmpl, p)


async def do_backstab(ctx, arg):
    p = ctx.player
    if p.klass != "rogue":
        await ctx.engine.send(p, c.error("You don't know how to backstab."))
        return
    if p.in_combat_with:
        await ctx.engine.send(p, c.error("You can only backstab from outside combat."))
        return
    if not arg:
        await ctx.engine.send(p, c.error("Backstab what?"))
        return
    room = ctx.world.get_room(p.room_id)
    if room.safe:
        await ctx.engine.send(p, c.error("You can't start a fight here."))
        return
    mob = ctx.engine.find_mob_in_room(p.room_id, arg)
    if not mob:
        await ctx.engine.send(p, c.error("You don't see that here."))
        return
    if mob.target_name:
        await ctx.engine.send(p, c.error("It's already fighting someone -- too risky to sneak up now."))
        return
    tmpl = ctx.world.get_mob_template(mob.template_id)
    dmg = ctx.engine.roll_player_damage(p) * 3
    mob.hp -= dmg
    await ctx.engine.send(p, f"You sink your blade into {c.mob(tmpl.name)}'s back for {c.dmg(dmg)} damage!")
    await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} backstabs {c.mob(tmpl.name)}!", exclude_names=(p.name,))
    if mob.hp <= 0:
        await ctx.engine.resolve_mob_death(mob, tmpl, p)
        return
    p.in_combat_with = mob.instance_id
    mob.target_name = p.name


async def do_use(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Use what skill?"))
        return
    parts = arg.split(None, 1)
    skill = parts[0].lower()
    target_kw = parts[1].strip() if len(parts) > 1 else ""

    if skill == "bash":
        await do_bash(ctx, target_kw)
        return
    if skill == "backstab":
        await do_backstab(ctx, target_kw)
        return

    spec = ABILITIES.get(skill)
    if not spec or spec["type"] != "skill":
        await ctx.engine.send(p, c.error("You don't know that skill."))
        return
    if p.klass != spec["class"]:
        await ctx.engine.send(p, c.error("You don't know how to use that."))
        return
    if skill not in p.known_skills:
        await ctx.engine.send(p, c.error("You haven't learned that skill yet."))
        return
    if p.level < spec["level_req"]:
        await ctx.engine.send(p, c.error(f"You must be level {spec['level_req']} to use that."))
        return
    now = time.time()
    ready_at = p.skill_cooldowns.get(skill, 0.0)
    if now < ready_at:
        await ctx.engine.send(p, c.error(f"You aren't ready to do that again ({int(ready_at - now)}s)."))
        return

    kind = spec["kind"]

    if kind == "attack_bonus":
        room = ctx.world.get_room(p.room_id)
        if room.safe:
            await ctx.engine.send(p, c.error("You can't start a fight here."))
            return
        mob = ctx.engine.mobs.get(p.in_combat_with) if p.in_combat_with else None
        if not mob and target_kw:
            mob = ctx.engine.find_mob_in_room(p.room_id, target_kw)
        if not mob:
            await ctx.engine.send(p, c.error(f"Use {spec['verb']} on what?"))
            return
        tmpl = ctx.world.get_mob_template(mob.template_id)
        bonus = random.randint(spec["bonus_min"], spec["bonus_max"])
        dmg = ctx.engine.roll_player_damage(p) + bonus
        if spec.get("execute_mult") and mob.hp <= mob.max_hp * 0.2:
            dmg *= spec["execute_mult"]
        mob.hp -= dmg
        p.in_combat_with = mob.instance_id
        mob.target_name = p.name
        p.skill_cooldowns[skill] = now + spec["cooldown"]
        await ctx.engine.send(p, f"You {spec['verb']} {c.mob(tmpl.name)} for {c.dmg(dmg)} damage!")
        await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} uses {spec['verb']} on {c.mob(tmpl.name)}!",
                                    exclude_names=(p.name,))
        if mob.hp <= 0:
            await ctx.engine.resolve_mob_death(mob, tmpl, p)

    elif kind == "backstab":
        ignore = spec.get("ignore_target", False)
        if p.in_combat_with and not ignore:
            await ctx.engine.send(p, c.error("You can only do that from outside combat."))
            return
        mob = ctx.engine.mobs.get(p.in_combat_with) if p.in_combat_with else None
        if not mob and target_kw:
            mob = ctx.engine.find_mob_in_room(p.room_id, target_kw)
        if not mob:
            await ctx.engine.send(p, c.error(f"Use {spec['verb']} on what?"))
            return
        if mob.target_name and mob.target_name != p.name and not ignore:
            await ctx.engine.send(p, c.error("It's already fighting someone -- too risky to sneak up now."))
            return
        tmpl = ctx.world.get_mob_template(mob.template_id)
        dmg = ctx.engine.roll_player_damage(p) * spec["mult"]
        mob.hp -= dmg
        p.skill_cooldowns[skill] = now + spec["cooldown"]
        await ctx.engine.send(p, f"You {spec['verb']} {c.mob(tmpl.name)} for {c.dmg(dmg)} damage!")
        await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} uses {spec['verb']} on {c.mob(tmpl.name)}!",
                                    exclude_names=(p.name,))
        if mob.hp <= 0:
            await ctx.engine.resolve_mob_death(mob, tmpl, p)
            return
        p.in_combat_with = mob.instance_id
        mob.target_name = p.name

    elif kind == "buff_dmg":
        p.dmg_buff_until = now + spec["duration"]
        p.dmg_buff_amount = spec["amount"]
        p.skill_cooldowns[skill] = now + spec["cooldown"]
        await ctx.engine.send(p, f"You use {spec['verb']}! Your attacks are empowered for {spec['duration']}s.")
        await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} uses {spec['verb']}!", exclude_names=(p.name,))

    elif kind == "buff_armor":
        p.armor_buff_until = now + spec["duration"]
        p.armor_buff_amount = spec["amount"]
        p.skill_cooldowns[skill] = now + spec["cooldown"]
        await ctx.engine.send(p, f"You use {spec['verb']}! Your defenses are bolstered for {spec['duration']}s.")
        await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} uses {spec['verb']}!", exclude_names=(p.name,))

    elif kind == "self_heal":
        amount = random.randint(spec["heal_min"], spec["heal_max"])
        p.hp = min(p.max_hp, p.hp + amount)
        p.skill_cooldowns[skill] = now + spec["cooldown"]
        await ctx.engine.send(p, f"You use {spec['verb']}, recovering {c.heal(amount)} hp.")

    elif kind in ("invisibility", "vanish"):
        duration = spec["duration"]
        p.invisible_until = now + duration
        p.skill_cooldowns[skill] = now + spec["cooldown"]
        if kind == "vanish" and p.in_combat_with:
            inst = ctx.engine.mobs.get(p.in_combat_with)
            if inst:
                inst.target_name = None
            p.in_combat_with = None
        await ctx.engine.send(p, f"You use {spec['verb']} and fade from sight for {duration}s.")
        await ctx.engine.send_room(p.room_id, c.system(f"{p.name} vanishes!"), exclude_names=(p.name,))


async def do_skills(ctx):
    p = ctx.player
    own = sorted(
        ((aid, spec) for aid, spec in ABILITIES.items() if spec["class"] == p.klass),
        key=lambda pair: pair[1]["level_req"],
    )
    label = "spells" if p.klass in ("mage", "cleric") else "skills"
    lines = [c.help_(f"Your {label} ({p.klass}):")]
    for aid, spec in own:
        known = aid in p.known_skills
        if known:
            status = c.heal("known")
        elif p.level < spec["level_req"]:
            status = c.error(f"requires level {spec['level_req']}")
        else:
            status = f"learnable from your guild trainer ({c.gold(spec['learn_cost'])} gold)"
        cost = f"{spec['cost']} mana" if spec["type"] == "spell" else (
            f"{spec['cooldown']}s cooldown" if spec["cooldown"] else "no cooldown")
        lines.append(f"&nbsp;&nbsp;{c.esc(aid)} (lvl {spec['level_req']}, {cost}) &mdash; {status}")
    await ctx.engine.send(p, "<br>".join(lines))


async def do_learn(ctx, arg):
    p = ctx.player
    if not arg:
        await ctx.engine.send(p, c.error("Learn what?"))
        return
    skill = arg.strip().lower()
    spec = ABILITIES.get(skill)
    if not spec or spec["class"] != p.klass:
        await ctx.engine.send(p, c.error("That isn't one of your class's abilities."))
        return
    room = ctx.world.get_room(p.room_id)
    trainer = room.trainer
    if not trainer or trainer.klass != p.klass:
        await ctx.engine.send(p, c.error("There's no trainer here to teach you that."))
        return
    if skill in p.known_skills:
        await ctx.engine.send(p, c.error("You already know that."))
        return
    if p.level < spec["level_req"]:
        await ctx.engine.send(p, c.error(f"{trainer.name} shakes their head: \"Come back at level {spec['level_req']}.\""))
        return
    cost = spec["learn_cost"]
    if p.gold < cost:
        await ctx.engine.send(p, c.error(f"{trainer.name} wants {c.gold(cost)} gold for that -- you don't have enough."))
        return
    p.gold -= cost
    p.known_skills.append(skill)
    verb = spec["verb"]
    word = "spell" if spec["type"] == "spell" else "skill"
    if cost:
        await ctx.engine.send(p, f"{c.player(trainer.name)} teaches you the {word} {c.help_(verb)} for {c.gold(cost)} gold.")
    else:
        await ctx.engine.send(p, f"{c.player(trainer.name)} teaches you the {word} {c.help_(verb)}.")


async def do_list(ctx):
    p = ctx.player
    room = ctx.world.get_room(p.room_id)
    if not room.shop:
        await ctx.engine.send(p, c.error("There's no shop here."))
        return
    lines = [c.help_("For sale:")]
    for iid in room.shop:
        tmpl = ctx.world.get_item(iid)
        lines.append(f"&nbsp;&nbsp;{c.item(tmpl.name)} &mdash; {c.gold(tmpl.value)} gold")
    await ctx.engine.send(p, "<br>".join(lines))


async def do_buy(ctx, arg):
    p = ctx.player
    room = ctx.world.get_room(p.room_id)
    if not room.shop:
        await ctx.engine.send(p, c.error("There's no shop here."))
        return
    iid = _match_item_in_list(ctx, room.shop, arg)
    if not iid:
        await ctx.engine.send(p, c.error("They don't sell that here."))
        return
    tmpl = ctx.world.get_item(iid)
    if p.gold < tmpl.value:
        await ctx.engine.send(p, c.error("You can't afford that."))
        return
    p.gold -= tmpl.value
    p.inventory.append(iid)
    await ctx.engine.send(p, f"You buy {c.item(tmpl.name)} for {c.gold(tmpl.value)} gold.")


async def do_sell(ctx, arg):
    p = ctx.player
    room = ctx.world.get_room(p.room_id)
    if not room.shop:
        await ctx.engine.send(p, c.error("There's no shop here."))
        return
    iid = _match_item_in_list(ctx, p.inventory, arg)
    if not iid:
        await ctx.engine.send(p, c.error("You aren't carrying that."))
        return
    tmpl = ctx.world.get_item(iid)
    price = max(1, tmpl.value // 2)
    for slot, eid in list(p.equipment.items()):
        if eid == iid:
            del p.equipment[slot]
    p.inventory.remove(iid)
    p.gold += price
    await ctx.engine.send(p, f"You sell {c.item(tmpl.name)} for {c.gold(price)} gold.")


async def do_pray(ctx):
    p = ctx.player
    room = ctx.world.get_room(p.room_id)
    if "heal" not in room.services:
        await ctx.engine.send(p, c.error("Nothing happens."))
        return
    if p.hp >= p.max_hp and p.mana >= p.max_mana:
        await ctx.engine.send(p, c.system('The priestess smiles. "You are already at full strength."'))
        return
    cost = 10
    if p.gold < cost:
        await ctx.engine.send(p, c.error('The priestess says, "A small donation of 10 gold is customary."'))
        return
    p.gold -= cost
    p.hp = p.max_hp
    p.mana = p.max_mana
    await ctx.engine.send(p, c.heal("The priestess lays a hand on your shoulder. Warmth floods through you "
                                     "&mdash; fully healed!"))


async def do_open(ctx, arg):
    p = ctx.player
    room = ctx.world.get_room(p.room_id)
    if not room.container:
        await ctx.engine.send(p, c.error("There's nothing to open here."))
        return
    if ctx.engine.is_container_opened(room.id):
        await ctx.engine.send(p, c.error("It's already empty."))
        return
    cont = room.container
    if cont.requires_key:
        if cont.requires_key not in p.inventory:
            await ctx.engine.send(p, c.error(f"{cont.name} is locked. You'll need a key."))
            return
        p.inventory.remove(cont.requires_key)
    ctx.engine.mark_container_opened(room.id)
    lines = [f"You open {cont.name}!"]
    for iid in cont.loot:
        p.inventory.append(iid)
        tmpl = ctx.world.get_item(iid)
        lines.append(f"You find {c.item(tmpl.name)}!")
    await ctx.engine.send(p, "<br>".join(lines))
    await ctx.engine.send_room(room.id, f"{c.player(p.name)} opens {cont.name}.", exclude_names=(p.name,))


async def do_quit(ctx):
    p = ctx.player
    persistence.save(p)
    await ctx.engine.send(p, c.system("Your progress is saved. Farewell, traveler."))
    raise QuitRequested()


async def do_changepass(ctx, arg):
    p = ctx.player
    parts = (arg or "").split()
    if len(parts) != 2:
        await ctx.engine.send(p, c.error("Usage: changepass &lt;old password&gt; &lt;new password&gt; (no spaces in passwords)"))
        return
    old_pw, new_pw = parts
    if not auth.verify_password(old_pw, p.password_salt, p.password_hash):
        await ctx.engine.send(p, c.error("That's not your current password."))
        return
    if not auth.is_valid_password(new_pw):
        await ctx.engine.send(p, c.error("New password must be 4-64 characters."))
        return
    p.password_hash, p.password_salt = auth.hash_password(new_pw)
    persistence.save(p)
    await ctx.engine.send(p, c.system("Password changed."))


def _is_staff(player) -> bool:
    return player.is_admin or getattr(player, "is_assistant_admin", False)


def _find_target_player(ctx, name: str):
    online = ctx.engine.players.get((name or "").lower())
    if online:
        return online, True
    offline = persistence.load(name)
    if offline:
        return offline, False
    return None, False


async def do_setpass(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    parts = (arg or "").split()
    if len(parts) != 2:
        await ctx.engine.send(p, c.error("Usage: setpass &lt;character&gt; &lt;newpassword&gt;"))
        return
    target_name, new_pw = parts
    if not auth.is_valid_password(new_pw):
        await ctx.engine.send(p, c.error("New password must be 4-64 characters."))
        return
    target, online = _find_target_player(ctx, target_name)
    if not target:
        await ctx.engine.send(p, c.error("No character by that name."))
        return
    target.password_hash, target.password_salt = auth.hash_password(new_pw)
    persistence.save(target)
    await ctx.engine.send(p, c.admin(f"Password for {target.name} has been reset."))
    if online and target is not p:
        await ctx.engine.send(target, c.admin("An admin has reset your password."))


async def do_makeadmin(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    parts = (arg or "").split()
    if len(parts) != 2 or parts[1].lower() not in ("on", "off"):
        await ctx.engine.send(p, c.error("Usage: makeadmin &lt;character&gt; on|off"))
        return
    target_name = parts[0]
    flag = parts[1].lower() == "on"
    target, online = _find_target_player(ctx, target_name)
    if not target:
        await ctx.engine.send(p, c.error("No character by that name."))
        return
    target.is_admin = flag
    persistence.save(target)
    await ctx.engine.send(p, c.admin(f"{target.name} is {'now' if flag else 'no longer'} an admin."))
    if online and target is not p:
        verb = "granted" if flag else "stripped of"
        await ctx.engine.send(target, c.admin(f"You have been {verb} admin privileges."))


async def do_makeassistant(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    parts = (arg or "").split()
    if len(parts) != 2 or parts[1].lower() not in ("on", "off"):
        await ctx.engine.send(p, c.error("Usage: makeassistant &lt;character&gt; on|off"))
        return
    target_name = parts[0]
    flag = parts[1].lower() == "on"
    target, online = _find_target_player(ctx, target_name)
    if not target:
        await ctx.engine.send(p, c.error("No character by that name."))
        return
    target.is_assistant_admin = flag
    persistence.save(target)
    await ctx.engine.send(p, c.admin(f"{target.name} is {'now' if flag else 'no longer'} an assistant admin."))
    if online and target is not p:
        verb = "granted" if flag else "stripped of"
        await ctx.engine.send(target, c.admin(f"You have been {verb} assistant admin privileges."))


async def do_kick(ctx, arg):
    p = ctx.player
    if not _is_staff(p):
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    target_name = (arg or "").strip()
    if not target_name:
        await ctx.engine.send(p, c.error("Usage: kick &lt;character&gt;"))
        return
    target = ctx.engine.players.get(target_name.lower())
    if not target:
        await ctx.engine.send(p, c.error(f"'{target_name}' is not online."))
        return
    if target is p:
        await ctx.engine.send(p, c.error("You can't kick yourself."))
        return
    if target.is_admin and not p.is_admin:
        await ctx.engine.send(p, c.error("You cannot kick an admin."))
        return
    persistence.save(target)
    await ctx.engine.send(target, c.admin("You have been kicked from the server."))
    try:
        if target.websocket:
            await target.websocket.close()
    except Exception:
        pass
    await ctx.engine.send(p, c.admin(f"{target.name} has been kicked."))


async def do_listplayers(ctx):
    p = ctx.player
    if not _is_staff(p):
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    names = persistence.list_players()
    if not names:
        await ctx.engine.send(p, c.admin("No saved characters found."))
        return
    online_set = {n.lower() for n in ctx.engine.players}
    lines = [c.admin(f"Saved characters ({len(names)}):" )]
    for name in names:
        char = persistence.load(name)
        if char:
            role = "admin" if char.is_admin else ("staff" if getattr(char, "is_assistant_admin", False) else "")
            role_tag = f" [{role}]" if role else ""
            status = " <online>" if name.lower() in online_set else ""
            lines.append(
                f"&nbsp;&nbsp;{char.name} &mdash; {char.race} {char.klass} lvl {char.level}{role_tag}{status}"
            )
    await ctx.engine.send(p, "<br>".join(lines))


async def do_deleteplayer(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("Only admins can delete characters."))
        return
    target_name = (arg or "").strip()
    if not target_name:
        await ctx.engine.send(p, c.error("Usage: deleteplayer &lt;character&gt;"))
        return
    if target_name.lower() == p.name.lower():
        await ctx.engine.send(p, c.error("You can't delete yourself."))
        return
    if ctx.engine.players.get(target_name.lower()):
        await ctx.engine.send(p, c.error(f"'{target_name}' is currently online. Kick them first."))
        return
    deleted = persistence.delete_player(target_name)
    if deleted:
        await ctx.engine.send(p, c.admin(f"Character '{target_name}' has been permanently deleted."))
    else:
        await ctx.engine.send(p, c.error(f"No saved character named '{target_name}'."))


async def do_setlevel(ctx, arg):
    from .models import MAX_LEVEL
    p = ctx.player
    if not _is_staff(p):
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    parts = (arg or "").split()
    if len(parts) != 2:
        await ctx.engine.send(p, c.error("Usage: setlevel &lt;character&gt; &lt;level&gt;"))
        return
    target_name, level_str = parts
    try:
        new_level = int(level_str)
    except ValueError:
        await ctx.engine.send(p, c.error("Level must be a number."))
        return
    new_level = max(1, min(new_level, MAX_LEVEL))
    target, online = _find_target_player(ctx, target_name)
    if not target:
        await ctx.engine.send(p, c.error("No character by that name."))
        return
    if target.is_admin and not p.is_admin:
        await ctx.engine.send(p, c.error("You cannot modify an admin."))
        return
    target.level = new_level
    target.recalc_max_stats()
    target.hp = min(target.hp, target.max_hp)
    target.mana = min(target.mana, target.max_mana)
    persistence.save(target)
    await ctx.engine.send(p, c.admin(f"{target.name}'s level set to {new_level}."))
    if online and target is not p:
        await ctx.engine.send(target, c.admin(f"Your level has been set to {new_level} by {p.name}."))


async def do_setstat(ctx, arg):
    p = ctx.player
    if not _is_staff(p):
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    parts = (arg or "").split()
    if len(parts) != 3:
        await ctx.engine.send(p, c.error("Usage: setstat &lt;character&gt; &lt;stat&gt; &lt;value&gt;"))
        return
    target_name, stat, val_str = parts
    valid_stats = ("str", "dex", "con", "int", "wis")
    if stat.lower() not in valid_stats:
        await ctx.engine.send(p, c.error(f"Valid stats: {', '.join(valid_stats)}"))
        return
    try:
        new_val = int(val_str)
    except ValueError:
        await ctx.engine.send(p, c.error("Value must be a number."))
        return
    new_val = max(1, min(new_val, 25))
    target, online = _find_target_player(ctx, target_name)
    if not target:
        await ctx.engine.send(p, c.error("No character by that name."))
        return
    if target.is_admin and not p.is_admin:
        await ctx.engine.send(p, c.error("You cannot modify an admin."))
        return
    target.stats[stat.lower()] = new_val
    target.recalc_max_stats()
    target.hp = min(target.hp, target.max_hp)
    target.mana = min(target.mana, target.max_mana)
    persistence.save(target)
    await ctx.engine.send(p, c.admin(f"{target.name}'s {stat} set to {new_val}."))
    if online and target is not p:
        await ctx.engine.send(target, c.admin(f"Your {stat} has been set to {new_val} by {p.name}."))


async def do_rooms(ctx):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    lines = [c.admin(f"Rooms ({len(ctx.world.rooms)}):")]
    for rid in sorted(ctx.world.rooms.keys()):
        room = ctx.world.rooms[rid]
        lines.append(f"&nbsp;&nbsp;{rid} &mdash; {c.esc(room.name)}")
    await ctx.engine.send(p, "<br>".join(lines))


async def do_goto(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    room_id = (arg or "").strip().lower()
    dest = ctx.world.get_room(room_id)
    if not dest:
        await ctx.engine.send(p, c.error("No such room."))
        return
    await ctx.engine.send_room(p.room_id, c.system(f"{p.name} vanishes in a puff of smoke."), exclude_names=(p.name,))
    p.room_id = room_id
    await ctx.engine.send_room(room_id, c.system(f"{p.name} appears in a puff of smoke."), exclude_names=(p.name,))
    await do_look(ctx, "")


async def do_dig(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    parts = (arg or "").split(None, 2)
    if len(parts) < 2:
        await ctx.engine.send(p, c.error("Usage: dig &lt;direction&gt; &lt;room_id&gt; [name...]"))
        return
    direction = DIRECTIONS.get(parts[0].lower())
    if not direction:
        await ctx.engine.send(p, c.error("That's not a direction."))
        return
    room_id = parts[1].lower()
    if not ctx.world.is_valid_room_id(room_id):
        await ctx.engine.send(p, c.error("Room id must be lowercase letters/numbers/underscores, starting with a letter."))
        return
    if room_id in ctx.world.rooms:
        await ctx.engine.send(p, c.error("A room with that id already exists."))
        return
    name = parts[2].strip() if len(parts) > 2 else room_id.replace("_", " ").title()
    current = ctx.world.get_room(p.room_id)
    if direction in current.exits:
        await ctx.engine.send(p, c.error(f"There's already an exit {direction} from here."))
        return
    new_room = ctx.world.add_room(room_id, name, f"{name}. (undescribed -- use 'rdesc' to add detail)")
    current.exits[direction] = room_id
    new_room.exits[OPPOSITE_DIRECTION[direction]] = p.room_id
    ctx.world.save()
    await ctx.engine.send(p, c.admin(f"Dug a room '{room_id}' to the {direction}, linked both ways."))


async def do_rlink(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    parts = (arg or "").split()
    if len(parts) != 2:
        await ctx.engine.send(p, c.error("Usage: rlink &lt;direction&gt; &lt;room_id&gt;"))
        return
    direction = DIRECTIONS.get(parts[0].lower())
    if not direction:
        await ctx.engine.send(p, c.error("That's not a direction."))
        return
    room_id = parts[1].lower()
    if room_id not in ctx.world.rooms:
        await ctx.engine.send(p, c.error("No such room."))
        return
    current = ctx.world.get_room(p.room_id)
    current.exits[direction] = room_id
    ctx.world.save()
    await ctx.engine.send(p, c.admin(f"Linked {direction} to '{room_id}' (one-way -- use rlink the other side too if you want a return exit)."))


async def do_runlink(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    direction = DIRECTIONS.get((arg or "").strip().lower())
    if not direction:
        await ctx.engine.send(p, c.error("Usage: runlink &lt;direction&gt;"))
        return
    current = ctx.world.get_room(p.room_id)
    if direction not in current.exits:
        await ctx.engine.send(p, c.error(f"There's no exit {direction} from here."))
        return
    del current.exits[direction]
    ctx.world.save()
    await ctx.engine.send(p, c.admin(f"Removed the exit {direction}."))


async def do_rname(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    if not arg:
        await ctx.engine.send(p, c.error("Usage: rname &lt;new name&gt;"))
        return
    current = ctx.world.get_room(p.room_id)
    current.name = arg.strip()
    ctx.world.save()
    await ctx.engine.send(p, c.admin(f"Room renamed to '{current.name}'."))


async def do_rdesc(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    if not arg:
        await ctx.engine.send(p, c.error("Usage: rdesc &lt;new description&gt;"))
        return
    current = ctx.world.get_room(p.room_id)
    current.description = arg.strip()
    ctx.world.save()
    await ctx.engine.send(p, c.admin("Room description updated."))


async def do_rlore(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    if not arg:
        await ctx.engine.send(p, c.error("Usage: rlore &lt;text&gt; (empty text clears it -- use rlore - to clear)"))
        return
    current = ctx.world.get_room(p.room_id)
    current.lore = "" if arg.strip() == "-" else arg.strip()
    ctx.world.save()
    await ctx.engine.send(p, c.admin("Room lore updated." if current.lore else "Room lore cleared."))


async def do_rsafe(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    flag = (arg or "").strip().lower()
    if flag not in ("on", "off"):
        await ctx.engine.send(p, c.error("Usage: rsafe on|off"))
        return
    current = ctx.world.get_room(p.room_id)
    current.safe = (flag == "on")
    ctx.world.save()
    await ctx.engine.send(p, c.admin(f"This room is now {'safe' if current.safe else 'unsafe'}."))


async def do_setmaxplayers(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    try:
        n = int((arg or "").strip())
        if n < 0:
            raise ValueError
    except ValueError:
        await ctx.engine.send(p, c.error("Usage: setmaxplayers &lt;n&gt;  (0 = unlimited)"))
        return
    persistence.set_max_players(n)
    if n == 0:
        await ctx.engine.send(p, c.admin("Player cap removed -- new accounts allowed without limit."))
    else:
        current_count = len(persistence.list_players())
        await ctx.engine.send(p, c.admin(
            f"Player cap set to {n}. Current count: {current_count}/{n}."
        ))


async def do_lockregistration(ctx, arg):
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return
    flag = (arg or "").strip().lower()
    if flag not in ("on", "off"):
        await ctx.engine.send(p, c.error("Usage: lockregistration on|off"))
        return
    locked = (flag == "on")
    persistence.set_registration_locked(locked)
    if locked:
        await ctx.engine.send(p, c.admin(
            "Registration LOCKED. No new accounts can be created until you run 'lockregistration off'."
        ))
    else:
        await ctx.engine.send(p, c.admin("Registration OPEN. New accounts are allowed."))


# ---------------------------------------------------------------------------
# NPC dialogue
# ---------------------------------------------------------------------------

_SHOP_ALIASES   = frozenset({"shopkeeper", "shopkeep", "merchant", "vendor", "keeper", "shop"})
_HEALER_ALIASES = frozenset({"priestess", "sister", "healer", "cleric", "priest", "dawn"})

_BUY_INTENT_RE = re.compile(
    r"\b(buy|purchase|i'?ll take|i want to buy|get me|give me|i'?d like|can i (get|buy|have))\b",
    re.IGNORECASE,
)

_BUY_CONFIRM = [
    "Pleasure doing business. {gold} gold -- here you are.",
    "Good choice. {gold} gold, and it's yours.",
    "Here you go. {gold} gold. Come back any time.",
    "Sold. {gold} gold. Finest quality, I assure you.",
]
_BUY_CANT_AFFORD = [
    "That's {gold} gold. Come back when your purse is a little heavier.",
    "I'm afraid I can't do charity. {gold} gold is the price. No haggling.",
    "Short on coin? {gold} gold is what I need. No exceptions.",
]
_BUY_UNKNOWN = [
    "Not sure what you're after. Have a look at what I carry -- try 'list'.",
    "I don't think I stock that. Take a look at my wares with 'list'.",
    "Can't say I have that. Check the list and tell me what catches your eye.",
]


async def do_talk(ctx, arg):
    """talk <npc> [message] -- speak with an NPC in the current room."""
    p = ctx.player
    room = ctx.world.get_room(p.room_id)

    if not arg:
        available = []
        if room.trainer:
            available.append(room.trainer.name)
        if room.shop:
            available.append("the shopkeeper")
        if "heal" in room.services:
            available.append("the priestess")
        if not available:
            await ctx.engine.send(p, c.system("There is no one here to talk to."))
        else:
            names = ", ".join(available)
            await ctx.engine.send(p, c.help_(f"You could talk to: {names}. (usage: talk &lt;name&gt; &lt;message&gt;)"))
        return

    parts = arg.split(None, 1)
    npc_keyword = parts[0].lower()
    message = parts[1].strip() if len(parts) > 1 else "Hello."

    npc_type: str | None = None
    npc_name: str | None = None
    npc_desc: str | None = None
    shop_inventory: list[tuple[str, int]] | None = None

    if room.trainer:
        trainer = room.trainer
        t_first = trainer.name.split()[0].lower()
        if npc_keyword in trainer.name.lower() or npc_keyword == t_first:
            npc_type = f"{trainer.klass}_trainer"
            npc_name = trainer.name
            npc_desc = f"{trainer.title} of the {trainer.klass.capitalize()}s' Guild"

    if npc_type is None and npc_keyword in _SHOP_ALIASES and room.shop:
        npc_type = "shopkeeper"
        npc_name = "the shopkeeper"
        npc_desc = "a merchant who keeps shop here"
        shop_inventory = [
            (ctx.world.get_item(iid).name, ctx.world.get_item(iid).value)
            for iid in room.shop
            if ctx.world.get_item(iid)
        ]

    if npc_type is None and npc_keyword in _HEALER_ALIASES and "heal" in room.services:
        npc_type = "priestess"
        npc_name = "the priestess"
        npc_desc = "a priestess of the Temple of the Dawn"

    if npc_type is None:
        await ctx.engine.send(p, c.error("There is no one by that name to talk to here."))
        return

    await ctx.engine.send_room(
        p.room_id,
        c.system(f"{p.name} speaks with {npc_name}."),
        exclude_names=(p.name,),
    )

    # --- shopkeeper buy-intent shortcut ---
    if npc_type == "shopkeeper" and _BUY_INTENT_RE.search(message):
        msg_lower = message.lower()
        bought_iid: str | None = None
        for iid in room.shop:
            tmpl = ctx.world.get_item(iid)
            if not tmpl:
                continue
            if any(w in msg_lower for w in tmpl.name.lower().split() if len(w) > 2):
                bought_iid = iid
                break

        if not bought_iid:
            reply = random.choice(_BUY_UNKNOWN)
        elif p.gold < ctx.world.get_item(bought_iid).value:
            tmpl = ctx.world.get_item(bought_iid)
            reply = random.choice(_BUY_CANT_AFFORD).format(gold=tmpl.value)
        else:
            tmpl = ctx.world.get_item(bought_iid)
            p.gold -= tmpl.value
            p.inventory.append(bought_iid)
            reply = random.choice(_BUY_CONFIRM).format(gold=tmpl.value)
            await ctx.engine.send(p, f"You receive {c.item(tmpl.name)}. (Gold remaining: {c.gold(p.gold)})")

        await ctx.engine.send(p, f'{c.player(npc_name)} says, "{c.say(reply)}"')
        return

    response = await npc_ai.get_npc_response(npc_type, npc_name, npc_desc, message, shop_inventory)
    await ctx.engine.send(p, f'{c.player(npc_name)} says, "{c.say(response)}"')


async def do_checkai(ctx):
    """checkai -- admin: test connectivity to the Ollama NPC AI server."""
    p = ctx.player
    if not p.is_admin:
        await ctx.engine.send(p, c.error("You don't have the authority to do that."))
        return

    await ctx.engine.send(p, c.system("Checking Ollama connection..."))
    status = await npc_ai.check_ollama()

    if status["ok"]:
        model_tag = c.heal("available") if status["model_available"] else c.error("NOT pulled")
        others = ", ".join(m for m in status["models"] if m != status["model"]) or "none"
        lines = [
            c.admin("Ollama NPC AI -- CONNECTED"),
            f"&nbsp;&nbsp;URL: {c.esc(status['url'])}",
            f"&nbsp;&nbsp;Configured model ({c.esc(status['model'])}): {model_tag}",
            f"&nbsp;&nbsp;Other models on server: {c.esc(others)}",
        ]
        if not status["model_available"]:
            lines.append(c.error(
                f"  Run: docker exec -it &lt;ollama&gt; ollama pull {c.esc(status['model'])}"
            ))
    else:
        lines = [
            c.error("Ollama NPC AI -- UNREACHABLE (pre-scripted fallbacks active)"),
            f"&nbsp;&nbsp;URL: {c.esc(status['url'])}",
            f"&nbsp;&nbsp;Model: {c.esc(status['model'])}",
            f"&nbsp;&nbsp;Error: {c.esc(status['error'])}",
        ]

    await ctx.engine.send(p, "<br>".join(lines))
