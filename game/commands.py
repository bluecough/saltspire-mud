"""Command parser & handlers. Each player command turns into one of the
do_* functions below, operating on a CommandContext (engine + player)."""
from __future__ import annotations
import random
import time
from . import auth
from . import colors as c
from . import persistence

DIRECTIONS = {
    "n": "north", "s": "south", "e": "east", "w": "west", "u": "up", "d": "down",
    "north": "north", "south": "south", "east": "east", "west": "west", "up": "up", "down": "down",
}

OPPOSITE_DIRECTION = {
    "north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up",
}

SPELLS = {
    "missile": {"class": "mage", "cost": 8, "kind": "damage", "dmg_min": 4, "dmg_max": 10},
    "heal": {"class": "cleric", "cost": 10, "kind": "heal", "heal_min": 12, "heal_max": 22},
}

HELP_TEXT = (
    "Available commands:<br>"
    "&nbsp;&nbsp;movement: north/south/east/west/up/down (n/s/e/w/u/d)<br>"
    "&nbsp;&nbsp;look [target], score, inventory (i), equipment (eq)<br>"
    "&nbsp;&nbsp;say &lt;msg&gt;, emote &lt;action&gt;, shout &lt;msg&gt;, who<br>"
    "&nbsp;&nbsp;get &lt;item&gt;, drop &lt;item&gt;, wear/wield &lt;item&gt;, remove &lt;item&gt;<br>"
    "&nbsp;&nbsp;kill &lt;target&gt;, flee, rest, wake<br>"
    "&nbsp;&nbsp;cast &lt;spell&gt; [target] &mdash; mage: missile, cleric: heal<br>"
    "&nbsp;&nbsp;bash &lt;target&gt; (warrior), backstab &lt;target&gt; (rogue)<br>"
    "&nbsp;&nbsp;list, buy &lt;item&gt;, sell &lt;item&gt; &mdash; in shops<br>"
    "&nbsp;&nbsp;pray &mdash; at the Temple of the Dawn<br>"
    "&nbsp;&nbsp;open chest &mdash; where applicable<br>"
    "&nbsp;&nbsp;changepass &lt;old&gt; &lt;new&gt;<br>"
    "&nbsp;&nbsp;help, quit"
)

ADMIN_HELP_TEXT = (
    "<br>Admin commands:<br>"
    "&nbsp;&nbsp;rooms &mdash; list every room id<br>"
    "&nbsp;&nbsp;goto &lt;room_id&gt; &mdash; teleport there<br>"
    "&nbsp;&nbsp;dig &lt;direction&gt; &lt;room_id&gt; [name...] &mdash; create a room, exit-linked both ways<br>"
    "&nbsp;&nbsp;rlink &lt;direction&gt; &lt;room_id&gt; &mdash; link an exit to an existing room (one-way)<br>"
    "&nbsp;&nbsp;runlink &lt;direction&gt; &mdash; remove an exit from the current room<br>"
    "&nbsp;&nbsp;rname &lt;text&gt;, rdesc &lt;text&gt; &mdash; rename / redescribe the current room<br>"
    "&nbsp;&nbsp;rsafe on|off &mdash; toggle whether combat is allowed in the current room<br>"
    "&nbsp;&nbsp;setpass &lt;character&gt; &lt;newpassword&gt; &mdash; reset anyone's password<br>"
    "&nbsp;&nbsp;makeadmin &lt;character&gt; on|off &mdash; grant/revoke admin"
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
    elif cmd == "changepass":
        await do_changepass(ctx, arg)
    elif cmd == "setpass":
        await do_setpass(ctx, arg)
    elif cmd == "makeadmin":
        await do_makeadmin(ctx, arg)
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
    elif cmd == "rsafe":
        await do_rsafe(ctx, arg)
    elif cmd in ("help", "?"):
        text = HELP_TEXT + (ADMIN_HELP_TEXT if ctx.player.is_admin else "")
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
    await ctx.engine.send_room(p.room_id, c.system(f"{p.name} leaves {direction}."), exclude_names=(p.name,))
    p.room_id = dest_id
    await ctx.engine.send_room(dest_id, c.system(f"{p.name} arrives."), exclude_names=(p.name,))
    await do_look(ctx, "")


async def do_look(ctx, arg):
    p = ctx.player
    room = ctx.world.get_room(p.room_id)

    if arg:
        mob = ctx.engine.find_mob_in_room(p.room_id, arg)
        if mob:
            tmpl = ctx.world.get_mob_template(mob.template_id)
            await ctx.engine.send(p, f"{c.mob(tmpl.name)} ({mob.hp}/{tmpl.max_hp} hp)<br>{c.esc(tmpl.description)}")
            return
        other = ctx.engine.find_player_in_room(p.room_id, arg, exclude=p.name)
        if other:
            await ctx.engine.send(p, f"{c.player(other.name)} the {other.race} {other.klass}, level {other.level}.")
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

    for m in ctx.engine.mobs_in_room(room.id):
        tmpl = ctx.world.get_mob_template(m.template_id)
        lines.append(f"{c.mob(tmpl.name.capitalize())} is here.")

    for other in ctx.engine.players_in_room(room.id, exclude=p.name):
        lines.append(f"{c.player(other.name)} is here.")

    for iid in ctx.engine.ground.get(room.id, []):
        tmpl = ctx.world.get_item(iid)
        lines.append(f"{c.item(tmpl.name)} is on the ground.")

    if room.shop:
        lines.append(c.help_("The shopkeep eyes your coin purse. (try 'list', 'buy &lt;item&gt;')"))
    if "heal" in room.services:
        lines.append(c.help_("You may 'pray' here to be healed."))
    if room.container and not ctx.engine.is_container_opened(room.id):
        lines.append(c.item(f"There is {room.container.name} here. (try 'open chest')"))

    await ctx.engine.send(p, "<br>".join(lines))


# ---------------------------------------------------------------------------
# Communication
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Inventory / equipment
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Combat
# ---------------------------------------------------------------------------

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
    spec = SPELLS.get(spell)
    if not spec:
        await ctx.engine.send(p, c.error("You don't know that spell."))
        return
    if p.klass != spec["class"]:
        await ctx.engine.send(p, c.error("You don't know how to cast that."))
        return
    if p.mana < spec["cost"]:
        await ctx.engine.send(p, c.error("You don't have enough mana."))
        return

    if spec["kind"] == "damage":
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
        await ctx.engine.send(p, f"Your missile of force strikes {c.mob(tmpl.name)} for {c.dmg(dmg)} damage!")
        await ctx.engine.send_room(p.room_id, f"{c.player(p.name)} hurls a missile of force at {c.mob(tmpl.name)}!",
                                    exclude_names=(p.name,))
        if mob.hp <= 0:
            await ctx.engine.resolve_mob_death(mob, tmpl, p)

    elif spec["kind"] == "heal":
        target = p
        if target_kw:
            other = ctx.engine.find_player_in_room(p.room_id, target_kw)
            if other:
                target = other
        p.mana -= spec["cost"]
        amount = random.randint(spec["heal_min"], spec["heal_max"])
        target.hp = min(target.max_hp, target.hp + amount)
        await ctx.engine.send(p, f"You channel divine light, healing {c.heal(amount)} points.")
        if target is not p:
            await ctx.engine.send(target, f"{c.player(p.name)} heals you for {c.heal(amount)} points.")


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


# ---------------------------------------------------------------------------
# Shops / services
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

async def do_quit(ctx):
    p = ctx.player
    persistence.save(p)
    await ctx.engine.send(p, c.system("Your progress is saved. Farewell, traveler."))
    raise QuitRequested()


# ---------------------------------------------------------------------------
# Password management
# ---------------------------------------------------------------------------

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


def _find_target_player(ctx, name: str):
    """Returns (player, is_online) for an online or offline character by name,
    or (None, False) if no such character exists."""
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


# ---------------------------------------------------------------------------
# Admin / building (OLC)
# ---------------------------------------------------------------------------

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
