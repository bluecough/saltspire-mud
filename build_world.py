"""
One-shot generator: expands the world data with new districts/zones,
mobs, and items, on top of the existing hand-written content. Run once
from the project root:  python3 build_world.py
Safe to re-run: it always starts from a fresh read of the *current*
world data and is idempotent as long as the new ids below haven't
already been added (re-running after a successful run will just
re-add/overwrite the same keys with the same values).

Reads/writes the same split-file layout as game/world.py (data/items.json,
data/mobs.json, data/rooms_1.json, data/rooms_2.json), falling back to a
legacy monolithic data/world.json if the split files aren't present.
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.path.join(BASE_DIR, "data", "items.json")
MOBS_PATH = os.path.join(BASE_DIR, "data", "mobs.json")
ROOM_SHARD_PATHS = [os.path.join(BASE_DIR, "data", "rooms_1.json"), os.path.join(BASE_DIR, "data", "rooms_2.json")]
LEGACY_WORLD_PATH = os.path.join(BASE_DIR, "data", "world.json")

OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}


def link(rooms, a, direction, b):
    rooms[a]["exits"][direction] = b
    rooms[b]["exits"][OPPOSITE[direction]] = a


# ---------------------------------------------------------------------------
# NEW CONTENT (filled in by section below)
# ---------------------------------------------------------------------------

NEW_ITEMS = {
    # -- Gildwater Heights / Warden Keep --
    "steel_longsword": {
        "name": "a steel longsword",
        "description": "A keep-quartermaster's blade, straight and well-oiled, stamped with the Concord's anchor sigil.",
        "slot": "weapon", "dmg_min": 3, "dmg_max": 8, "value": 60,
    },
    "tower_shield": {
        "name": "a tower shield",
        "description": "A heavy iron-banded shield, tall enough to crouch behind.",
        "slot": "shield", "armor": 3, "value": 70,
    },
    "plate_armor": {
        "name": "a suit of plate armor",
        "description": "Polished steel plate, the kind only a Warden's guard is issued.",
        "slot": "armor", "armor": 6, "value": 150,
    },
    "warden_seal": {
        "name": "a tarnished warden's seal",
        "description": "A wax-seal stamp bearing the Harbor Concord's anchor -- it has no business being on a renegade guard.",
        "slot": "treasure", "value": 40,
    },
    # -- Dockside --
    "fishhook_knife": {
        "name": "a fishhook knife",
        "description": "A short, curved gutting blade, more tool than weapon, but it'll do in a pinch.",
        "slot": "weapon", "dmg_min": 1, "dmg_max": 3, "value": 8,
    },
    "ships_log": {
        "name": "a water-stained ship's log",
        "description": "A logbook gone soft with damp. The last entries describe cargo that was never declared to the harbormaster.",
        "slot": "treasure", "value": 15,
    },
    "stolen_ledger": {
        "name": "a stolen ledger",
        "description": "Names, weights, and prices in a cramped hand -- a record the Undertow would pay dearly to get back.",
        "slot": "treasure", "value": 35,
    },
    "undertow_signet": {
        "name": "an undertow signet ring",
        "description": "A black iron ring etched with a wave swallowing a coin -- the mark of the dockside syndicate.",
        "slot": "treasure", "value": 55,
    },
    "spyglass": {
        "name": "a brass spyglass",
        "description": "A dented but functional spyglass, its lens still clear.",
        "slot": "treasure", "value": 25,
    },
    "tin_amulet": {
        "name": "a cheap tin amulet",
        "description": "A worthless little charm, sold to sailors who want to believe it's lucky.",
        "slot": "treasure", "value": 18,
    },
    # -- Sewers / Old Vael --
    "vael_sigil": {
        "name": "a corroded vael sigil",
        "description": "A coin-sized disc of green-black metal, warm to the touch. It fits a lock somewhere in the drowned ruins.",
        "slot": "key", "value": 0,
    },
    "tide_idol": {
        "name": "a small tide idol",
        "description": "A carved figure, half-eroded, of a many-armed shape rising from waves.",
        "slot": "treasure", "value": 45,
    },
    "drowned_crown": {
        "name": "the drowned crown",
        "description": "A crown of fused coral and silver, salt-crusted, heavier than it looks. Old Vael's last king wore this.",
        "slot": "treasure", "value": 220,
    },
    "vael_trident": {
        "name": "a vael war-trident",
        "description": "A barbed bronze trident, etched with spiraling script no living scholar can fully read.",
        "slot": "weapon", "dmg_min": 5, "dmg_max": 12, "value": 160,
    },
    "tidewarden_heart": {
        "name": "the tidewarden's heart",
        "description": "A fist-sized lump of something between coral and crystal, still faintly pulsing with cold light.",
        "slot": "treasure", "value": 120,
    },
    # -- Temple Row / Hollow Yard --
    "warden_femur_blade": {
        "name": "a femur blade",
        "description": "A short sword crudely ground from bone, dark with age. It feels wrong to hold.",
        "slot": "weapon", "dmg_min": 4, "dmg_max": 9, "value": 90,
    },
    "grave_gold": {
        "name": "a handful of grave gold",
        "description": "Coins buried with the dead, green with tarnish and best spent far from Temple Row.",
        "slot": "treasure", "value": 60,
    },
    # -- Trade Quarter --
    "padded_tunic": {
        "name": "a padded tunic",
        "description": "Quilted cloth armor, light enough to wear under a cloak.",
        "slot": "armor", "armor": 1, "value": 12,
    },
    "woolen_cloak": {
        "name": "a woolen cloak",
        "description": "A traveler's cloak, dyed a deep harbor-grey.",
        "slot": "armor", "armor": 1, "value": 18,
    },
    "soothing_tonic": {
        "name": "a soothing tonic",
        "description": "A bitter apothecary's draught that settles the stomach and the nerves alike.",
        "slot": "consumable", "heal": 10, "value": 8,
    },
    "greater_healing_potion": {
        "name": "a greater healing potion",
        "description": "A larger, darker vial than the common healing potion -- the apothecary's strongest brew.",
        "slot": "consumable", "heal": 40, "value": 25,
    },
    "mana_draught": {
        "name": "a mana draught",
        "description": "A faintly luminous blue liquid that smells of crushed quartz.",
        "slot": "consumable", "mana": 20, "value": 20,
    },
    "garnet_ring": {
        "name": "a garnet ring",
        "description": "A simple gold band set with a deep red stone, catching what little light there is.",
        "slot": "treasure", "value": 70,
    },
    "engraved_locket": {
        "name": "an engraved locket",
        "description": "A locket engraved with initials that mean nothing to anyone left in Saltspire.",
        "slot": "treasure", "value": 50,
    },
    # -- Coast Road / Hamlet / Fens / Mountains --
    "dried_rations": {
        "name": "dried rations",
        "description": "Salted fish and hard biscuit, wrapped in oilcloth. Filling, if not appetizing.",
        "slot": "consumable", "heal": 6, "value": 3,
    },
    "fishing_net": {
        "name": "a fishing net",
        "description": "A coil of tarred netting, mended many times over.",
        "slot": "treasure", "value": 10,
    },
    "sentinels_badge": {
        "name": "a sentinel's badge",
        "description": "A corroded badge from a watch disbanded long before anyone alive remembers why.",
        "slot": "treasure", "value": 30,
    },
    "captains_cutlass": {
        "name": "the red tide captain's cutlass",
        "description": "A curved blade with a basket hilt, still sharp despite two centuries under the salt fields.",
        "slot": "weapon", "dmg_min": 4, "dmg_max": 10, "value": 120,
    },
    "red_tide_standard": {
        "name": "a tattered red tide standard",
        "description": "A faded banner, once carried by a pirate fleet that broke itself against Saltspire's founders.",
        "slot": "treasure", "value": 100,
    },
    "drake_scale": {
        "name": "an ash-scaled drake scale",
        "description": "A single scale, the size of a shield, still warm and smelling faintly of cinders.",
        "slot": "treasure", "value": 250,
    },
    "ashwing_fang": {
        "name": "an ashwing fang",
        "description": "A drake's fang as long as a forearm, the edge wickedly serrated.",
        "slot": "weapon", "dmg_min": 7, "dmg_max": 15, "value": 300,
    },
    "hag_eye": {
        "name": "a hag's preserved eye",
        "description": "Kept in a jar of murky brine, it seems to track you even now.",
        "slot": "treasure", "value": 90,
    },
    "fen_mothers_staff": {
        "name": "the fen mother's staff",
        "description": "A gnarled staff wound with river reeds and small bones, still humming faintly with old magic.",
        "slot": "weapon", "dmg_min": 4, "dmg_max": 10, "value": 150,
    },
}

NEW_MOBS = {
    # -- Gildwater Heights / Warden Keep (lvl 5-6) --
    "garden_serpent": {
        "name": "a garden serpent", "description": "A jewel-scaled snake coiled in the hedges, more territorial than venomous.",
        "level": 5, "max_hp": 42, "dmg_min": 4, "dmg_max": 9, "armor": 1,
        "xp_reward": 45, "gold_min": 0, "gold_max": 5, "respawn_seconds": 50, "loot": [],
    },
    "renegade_guard": {
        "name": "a renegade keep guard", "description": "A guard in Concord colors whose loyalty has plainly been bought by someone else.",
        "level": 6, "max_hp": 65, "dmg_min": 6, "dmg_max": 11, "armor": 3,
        "xp_reward": 65, "gold_min": 10, "gold_max": 20, "respawn_seconds": 70,
        "loot": [{"item": "warden_seal", "chance": 0.5}],
    },
    # -- Dockside (lvl 1-7) --
    "bilge_rat": {
        "name": "a bilge rat", "description": "A fat, slow rat that's clearly never gone hungry in this ship's hold.",
        "level": 1, "max_hp": 10, "dmg_min": 1, "dmg_max": 2, "armor": 0,
        "xp_reward": 7, "gold_min": 0, "gold_max": 2, "respawn_seconds": 25, "loot": [],
    },
    "press_gang_thug": {
        "name": "a press-gang thug", "description": "A broad-shouldered tough with a cudgel, sizing up passersby for a ship that's short on crew.",
        "level": 4, "max_hp": 38, "dmg_min": 4, "dmg_max": 8, "armor": 1,
        "xp_reward": 34, "gold_min": 5, "gold_max": 12, "respawn_seconds": 45, "loot": [],
    },
    "undertow_cutthroat": {
        "name": "an undertow cutthroat", "description": "A wiry knife-fighter with a wave-and-coin tattoo on one forearm.",
        "level": 5, "max_hp": 48, "dmg_min": 4, "dmg_max": 9, "armor": 2,
        "xp_reward": 48, "gold_min": 10, "gold_max": 20, "respawn_seconds": 55,
        "loot": [{"item": "stolen_ledger", "chance": 0.25}],
    },
    "undertow_enforcer": {
        "name": "an undertow enforcer", "description": "A scarred bruiser who keeps the syndicate's debts collected, by whatever means needed.",
        "level": 7, "max_hp": 110, "dmg_min": 8, "dmg_max": 15, "armor": 4,
        "xp_reward": 130, "gold_min": 30, "gold_max": 50, "respawn_seconds": 150,
        "loot": [{"item": "undertow_signet", "chance": 0.5}, {"item": "stolen_ledger", "chance": 0.3}],
    },
    # -- Sewers / Old Vael (lvl 2-10) --
    "cave_rat": {
        "name": "a cave rat", "description": "Pale and half-blind from a life lived underground.",
        "level": 2, "max_hp": 18, "dmg_min": 1, "dmg_max": 4, "armor": 0,
        "xp_reward": 14, "gold_min": 0, "gold_max": 4, "respawn_seconds": 30, "loot": [],
    },
    "blind_eel": {
        "name": "a blind eel", "description": "A long, pale shape that whips out of the dark water before you fully see it.",
        "level": 3, "max_hp": 26, "dmg_min": 2, "dmg_max": 6, "armor": 0,
        "xp_reward": 22, "gold_min": 0, "gold_max": 2, "respawn_seconds": 35, "loot": [],
    },
    "vael_wretch": {
        "name": "a vael wretch", "description": "Something that was once a person, bloated and waterlogged, shambling on bone-white legs.",
        "level": 6, "max_hp": 60, "dmg_min": 5, "dmg_max": 11, "armor": 1,
        "xp_reward": 68, "gold_min": 5, "gold_max": 12, "respawn_seconds": 70, "loot": [],
    },
    "drowned_cultist": {
        "name": "a drowned cultist", "description": "A robed figure chanting to a god that drowned along with everyone else here.",
        "level": 6, "max_hp": 58, "dmg_min": 5, "dmg_max": 11, "armor": 1,
        "xp_reward": 68, "gold_min": 8, "gold_max": 16, "respawn_seconds": 70, "loot": [],
    },
    "cult_zealot": {
        "name": "a vael cult zealot", "description": "A wild-eyed believer clutching a tide idol, certain Old Vael will rise in their lifetime.",
        "level": 7, "max_hp": 90, "dmg_min": 7, "dmg_max": 14, "armor": 2,
        "xp_reward": 95, "gold_min": 10, "gold_max": 20, "respawn_seconds": 90,
        "loot": [{"item": "tide_idol", "chance": 0.3}],
    },
    "archive_construct": {
        "name": "an archive construct", "description": "A coral-and-bronze guardian, still patiently warding a library no one living can read.",
        "level": 7, "max_hp": 120, "dmg_min": 7, "dmg_max": 14, "armor": 5,
        "xp_reward": 140, "gold_min": 0, "gold_max": 0, "respawn_seconds": 180,
        "loot": [{"item": "vael_sigil", "chance": 1.0}],
    },
    "the_tidewarden": {
        "name": "the tidewarden", "description": "A towering, coral-fused construct, ancient and patient, the last thing standing between Saltspire and Old Vael's deepest vault.",
        "level": 10, "max_hp": 260, "dmg_min": 12, "dmg_max": 20, "armor": 6,
        "xp_reward": 340, "gold_min": 60, "gold_max": 100, "respawn_seconds": 450,
        "loot": [{"item": "drowned_crown", "chance": 0.3}, {"item": "tidewarden_heart", "chance": 0.5}],
    },
    # -- Temple Row / Hollow Yard (lvl 2-9) --
    "graveyard_rat": {
        "name": "a graveyard rat", "description": "A rat grown fat and bold on offerings left for the dead.",
        "level": 2, "max_hp": 16, "dmg_min": 1, "dmg_max": 3, "armor": 0,
        "xp_reward": 13, "gold_min": 0, "gold_max": 3, "respawn_seconds": 30, "loot": [],
    },
    "restless_spirit": {
        "name": "a restless spirit", "description": "A cold, half-seen shape that drifts between the headstones, unwilling or unable to move on.",
        "level": 4, "max_hp": 34, "dmg_min": 3, "dmg_max": 8, "armor": 0,
        "xp_reward": 36, "gold_min": 0, "gold_max": 0, "respawn_seconds": 50, "loot": [],
    },
    "skeletal_sentry": {
        "name": "a skeletal sentry", "description": "Old bones in older armor, still standing the post it died at.",
        "level": 5, "max_hp": 50, "dmg_min": 4, "dmg_max": 9, "armor": 3,
        "xp_reward": 50, "gold_min": 5, "gold_max": 10, "respawn_seconds": 60, "loot": [],
    },
    "ghoul": {
        "name": "a ghoul", "description": "A hunched, grave-pale thing with too many teeth, dragging itself between the mausoleums.",
        "level": 6, "max_hp": 70, "dmg_min": 6, "dmg_max": 12, "armor": 2,
        "xp_reward": 72, "gold_min": 10, "gold_max": 18, "respawn_seconds": 75, "loot": [],
    },
    "crypt_wight": {
        "name": "a crypt wight", "description": "A withered guardian bound to the sealed crypt long before the Concord ever existed.",
        "level": 7, "max_hp": 95, "dmg_min": 7, "dmg_max": 14, "armor": 3,
        "xp_reward": 98, "gold_min": 12, "gold_max": 22, "respawn_seconds": 90, "loot": [],
    },
    "the_bone_warden": {
        "name": "the bone warden", "description": "An armored colossus of fused bone and rusted iron, raised to guard the crypt's last secret forever.",
        "level": 9, "max_hp": 200, "dmg_min": 10, "dmg_max": 18, "armor": 5,
        "xp_reward": 260, "gold_min": 50, "gold_max": 90, "respawn_seconds": 360,
        "loot": [{"item": "warden_femur_blade", "chance": 0.4}, {"item": "grave_gold", "chance": 1.0}],
    },
    # -- Coast Road / Hamlet / Fens / Mountains (lvl 4-12) --
    "cave_crab": {
        "name": "a cave crab", "description": "A crab the size of a hound, claws scraping loudly against the sea-cave stone.",
        "level": 4, "max_hp": 40, "dmg_min": 3, "dmg_max": 7, "armor": 3,
        "xp_reward": 35, "gold_min": 2, "gold_max": 6, "respawn_seconds": 40, "loot": [],
    },
    "will_o_wisp": {
        "name": "a will-o-wisp", "description": "A cold, drifting light that lures the unwary off the safe path through the moor.",
        "level": 5, "max_hp": 36, "dmg_min": 5, "dmg_max": 10, "armor": 0,
        "xp_reward": 50, "gold_min": 0, "gold_max": 0, "respawn_seconds": 55, "loot": [],
    },
    "fallen_marauder": {
        "name": "a fallen marauder", "description": "A rotted remnant of the Red Tide fleet, still fighting a battle that ended two centuries ago.",
        "level": 5, "max_hp": 52, "dmg_min": 5, "dmg_max": 10, "armor": 2,
        "xp_reward": 52, "gold_min": 8, "gold_max": 16, "respawn_seconds": 60, "loot": [],
    },
    "bog_leech": {
        "name": "a bog leech", "description": "A leech the length of a forearm, surfacing silently from the mire.",
        "level": 5, "max_hp": 44, "dmg_min": 4, "dmg_max": 9, "armor": 0,
        "xp_reward": 46, "gold_min": 0, "gold_max": 3, "respawn_seconds": 50, "loot": [],
    },
    "moor_wraith": {
        "name": "a moor wraith", "description": "A tall, hollow shape that walks the hollow moor at the edge of sight, never quite approaching directly.",
        "level": 6, "max_hp": 64, "dmg_min": 6, "dmg_max": 12, "armor": 1,
        "xp_reward": 72, "gold_min": 0, "gold_max": 0, "respawn_seconds": 75, "loot": [],
    },
    "tower_brigand": {
        "name": "a tower brigand", "description": "A squatter living in the ruined watchtower, armed and unwelcoming of company.",
        "level": 6, "max_hp": 66, "dmg_min": 6, "dmg_max": 12, "armor": 2,
        "xp_reward": 72, "gold_min": 12, "gold_max": 22, "respawn_seconds": 75, "loot": [],
    },
    "undertow_smuggler": {
        "name": "an undertow smuggler", "description": "A rope-scarred sailor moving crates through the sea cave, well past the harbormaster's notice.",
        "level": 6, "max_hp": 68, "dmg_min": 6, "dmg_max": 12, "armor": 2,
        "xp_reward": 74, "gold_min": 15, "gold_max": 25, "respawn_seconds": 75, "loot": [],
    },
    "mire_kin": {
        "name": "a mire-kin", "description": "A lean, gray-skinned fenwalker, more at home in the muck than any road.",
        "level": 6, "max_hp": 70, "dmg_min": 6, "dmg_max": 13, "armor": 2,
        "xp_reward": 75, "gold_min": 5, "gold_max": 12, "respawn_seconds": 75, "loot": [],
    },
    "swamp_stalker": {
        "name": "a swamp stalker", "description": "A lurking, long-limbed predator that the mire-kin themselves are wary of.",
        "level": 7, "max_hp": 92, "dmg_min": 7, "dmg_max": 14, "armor": 2,
        "xp_reward": 96, "gold_min": 10, "gold_max": 20, "respawn_seconds": 90, "loot": [],
    },
    "red_tide_captain": {
        "name": "the red tide captain", "description": "The drowned captain of the fleet that broke itself on Saltspire's founders, still standing his ground at the salt fields.",
        "level": 8, "max_hp": 160, "dmg_min": 9, "dmg_max": 16, "armor": 4,
        "xp_reward": 200, "gold_min": 40, "gold_max": 70, "respawn_seconds": 300,
        "loot": [{"item": "captains_cutlass", "chance": 0.4}, {"item": "red_tide_standard", "chance": 0.2}],
    },
    "fen_mother": {
        "name": "the fen mother", "description": "An ancient hag who has ruled the fenmire since long before Saltspire had a name.",
        "level": 9, "max_hp": 210, "dmg_min": 10, "dmg_max": 19, "armor": 4,
        "xp_reward": 270, "gold_min": 50, "gold_max": 90, "respawn_seconds": 360,
        "loot": [{"item": "fen_mothers_staff", "chance": 0.35}, {"item": "hag_eye", "chance": 0.5}],
    },
    "ashwing_drake": {
        "name": "the ashwing drake", "description": "A young drake, ash-scaled and watchful, that's claimed the mountain pass as its own -- a sign of larger, wilder country beyond Saltspire's reach.",
        "level": 12, "max_hp": 380, "dmg_min": 15, "dmg_max": 26, "armor": 7,
        "xp_reward": 520, "gold_min": 100, "gold_max": 180, "respawn_seconds": 600,
        "loot": [{"item": "drake_scale", "chance": 0.6}, {"item": "ashwing_fang", "chance": 0.3}],
    },
}

NEW_ROOMS = {
    # ===================== ZONE: Gildwater Heights / Warden Keep =====================
    "gildwater_promenade": {
        "name": "Gildwater Promenade",
        "description": "A wide, lamplit avenue paved in pale stone, lined with topiary trimmed into the shapes of ships and anchors. The wealth here is loud in its quietness.",
        "safe": True,
    },
    "manor_row": {
        "name": "Manor Row",
        "description": "Tall iron-fenced manors face each other across a narrow private lane, every window dark or curtained.",
        "safe": True,
    },
    "the_gilt_lantern": {
        "name": "The Gilt Lantern",
        "description": "A masquerade hall hung with gold-leafed lanterns. Even empty at this hour, it smells of spilled wine and old secrets.",
        "safe": True,
        "lore": "The Gilt Lantern hosts a masked ball every solstice, ostensibly for the merchant houses to mingle. In practice, half the deals struck under those gold lanterns are Undertow business laundered through noble guests who'd never admit to knowing the syndicate's name.",
    },
    "terraced_gardens": {
        "name": "Terraced Gardens",
        "description": "Stepped flowerbeds climb toward the cliff face, fed by a system of stone channels older than the manors around them.",
        "safe": True,
    },
    "hidden_grotto": {
        "name": "Hidden Grotto",
        "description": "A secluded hollow behind a curtain of vines, cool and damp, where something rustles unseen among the roots.",
        "safe": False,
        "mob_spawns": [{"mob": "garden_serpent", "max": 1}],
    },
    "silver_court": {
        "name": "Silver Court",
        "description": "A plaza of pale flagstones centers on a weathered statue: a man and woman standing back to back, facing the sea on one side and the cliffs on the other.",
        "safe": True,
        "lore": "The statue depicts two of the First Hundred -- the refugees who washed ashore beneath the black spire some three hundred and forty years ago, fleeing the sinking of their homeland, Old Vael. Their names are worn off the plaque, but every Saltspire schoolchild can still recite the lines once carved beneath it: we did not choose the tide, but we chose what we built after it.",
    },
    "counting_house": {
        "name": "Ashgrave & Voss Counting House",
        "description": "Ledgers stack floor to ceiling behind a barred teller's window. A clerk eyes you the way clerks eye everyone: as a possible liability.",
        "safe": True,
    },
    "warden_gate": {
        "name": "Warden Gate",
        "description": "A fortified gatehouse of black spire-stone marks the boundary of Warden Keep proper. The guards here don't bother with practiced suspicion -- they're openly suspicious.",
        "safe": True,
    },
    "keep_courtyard": {
        "name": "Keep Courtyard",
        "description": "A drilling yard within the keep walls, ringed by barracks, armory, and the squat tower that houses the Concord's council chamber.",
        "safe": True,
    },
    "keep_barracks": {
        "name": "Keep Barracks",
        "description": "Rows of narrow cots and footlockers, every blanket folded with the same regulation precision.",
        "safe": True,
    },
    "keep_armory": {
        "name": "Keep Armory",
        "description": "Standard-issue Concord steel, racked and oiled. The quartermaster sizes you up without much interest.",
        "safe": True,
        "shop": ["steel_longsword", "tower_shield", "plate_armor"],
    },
    "concord_chamber": {
        "name": "Concord Chamber",
        "description": "Seven high-backed chairs ring a round table inlaid with a map of the Greywash coast. Six are empty; the seventh Warden's seat looks no less empty for being occupied most days.",
        "safe": True,
        "lore": "The Harbor Concord is seven Wardens, one elected by each ward's guilds and households, who govern Saltspire openly -- no secrecy, no masks, unlike the whispered habits of older, grander cities. In practice the Wardens spend more time arguing over harbor tariffs than ruling, and everyone in the room knows the Undertow's coin reaches at least two of the seven chairs.",
    },
    "keep_dungeon": {
        "name": "Keep Dungeon",
        "description": "A row of iron-barred cells beneath the keep, damp and unevenly lit. Most stand empty. One does not.",
        "safe": False,
        "mob_spawns": [{"mob": "renegade_guard", "max": 1}],
    },

    # ===================== ZONE: Dockside expansion =====================
    "harbor_pier": {
        "name": "The Long Pier",
        "description": "A pier of black timber reaches far out over the water, gulls wheeling above the masts of moored fishing boats.",
        "safe": True,
    },
    "warehouse_row": {
        "name": "Warehouse Row",
        "description": "Squat timber warehouses crowd the pier's edge, padlocked and unmarked. More goods move through here at night than the harbormaster ever sees by day.",
        "safe": True,
    },
    "smugglers_alley": {
        "name": "Smugglers' Alley",
        "description": "A cramped gap between warehouses, just wide enough for a loaded handcart and a guilty conscience.",
        "safe": True,
    },
    "smugglers_den": {
        "name": "The Undertow's Den",
        "description": "A hidden cellar beneath the warehouses, lit by shuttered lanterns. Crates of unlabeled cargo line every wall, and the wave-and-coin sigil is scratched into the support beams.",
        "safe": False,
        "mob_spawns": [{"mob": "undertow_cutthroat", "max": 1}, {"mob": "undertow_enforcer", "max": 1}],
        "lore": "The Undertow runs every illicit good that crosses Saltspire's docks -- smuggled spice, unregistered cargo, the occasional debt collected with a knife rather than a ledger. They've operated since before the Concord existed and answer to no Warden, only to whoever currently holds the syndicate's signet.",
    },
    "the_low_tunnel": {
        "name": "The Low Tunnel",
        "description": "A cramped, low passage that smells of brine and tar in equal measure -- somewhere between sewer, sea cave, and smuggler's shortcut.",
        "safe": True,
    },
    "moored_galley_deck": {
        "name": "Deck of a Moored Galley",
        "description": "The weathered deck of an old trading galley, sails furled, ropes coiled with more care than the rest of the ship deserves.",
        "safe": True,
    },
    "galley_hold": {
        "name": "Galley Hold",
        "description": "A dark, low-ceilinged hold stacked with barrels, most of them long since claimed by vermin.",
        "safe": False,
        "mob_spawns": [{"mob": "bilge_rat", "max": 2}],
    },
    "lighthouse_base": {
        "name": "Lighthouse Base",
        "description": "A squat stone lighthouse stands at the end of the pier, its iron door propped open with a chock of driftwood.",
        "safe": True,
    },
    "lighthouse_top": {
        "name": "Lighthouse Top",
        "description": "Wind tears at you the moment you step out onto the gallery. The lamp's great lens turns slowly behind you, and the whole curve of the Greywash coast spreads out below.",
        "safe": True,
        "lore": "On a clear night the lighthouse keeper claims you can see all the way to the foothills past the coast road -- and, if the old stories hold any truth, the dark line of mountains beyond that no one from Saltspire has mapped in living memory.",
    },
    "pawnshop": {
        "name": "The Anchor & Coin Pawnshop",
        "description": "A cramped shop crowded with secondhand goods of dubious origin. The proprietor doesn't ask questions, and would rather you didn't either.",
        "safe": True,
        "shop": ["fishhook_knife", "spyglass", "tin_amulet"],
    },
    "drowned_lantern_inn": {
        "name": "The Drowned Lantern",
        "description": "A sailors' flophouse thick with pipe smoke, where the patrons talk in low voices and stop talking entirely when strangers walk in.",
        "safe": True,
    },
    "press_gang_corner": {
        "name": "Press-Gang Corner",
        "description": "A dim alley behind the harbormaster's office, the kind of place where a careless drunk wakes up aboard a ship he never signed onto.",
        "safe": False,
        "mob_spawns": [{"mob": "press_gang_thug", "max": 1}],
    },

    # ===================== ZONE: Sewers / Old Vael undercity =====================
    "sewer_tunnel_3": {
        "name": "Sewer Tunnel, Third Branch",
        "description": "The channel here runs faster and colder than the tunnels above, as if fed from somewhere deeper than the town's own waste.",
        "safe": False,
        "mob_spawns": [{"mob": "cave_rat", "max": 2}],
    },
    "flooded_cistern": {
        "name": "Flooded Cistern",
        "description": "A vaulted brick chamber, half-submerged, older brickwork than anything else in the sewers. Whatever this was built to hold, it wasn't waste.",
        "safe": False,
        "mob_spawns": [{"mob": "cave_rat", "max": 1}, {"mob": "blind_eel", "max": 2}],
    },
    "undercity_stair": {
        "name": "The Undercity Stair",
        "description": "A wide stone stairway, its steps worn into smooth curves, descends past the cistern into deeper dark. The brickwork here gives way entirely to older, stranger stonework.",
        "safe": True,
        "lore": "These stairs were carved before the Concord, before the Counting House, before even the Rusty Anchor -- some say by the First Hundred themselves, in the years right after they washed ashore, back when the spire's roots were the only shelter anyone had.",
    },
    "old_vael_plaza": {
        "name": "Old Vael Plaza",
        "description": "A sunken square opens around you, columns and rooflines barely recognizable under centuries of silt and brine. This was a town once, whole and lit, before the sea came back for it.",
        "safe": False,
        "mob_spawns": [{"mob": "vael_wretch", "max": 2}, {"mob": "drowned_cultist", "max": 1}],
    },
    "old_vael_archive": {
        "name": "The Drowned Archive",
        "description": "Waterlogged shelving lines a half-collapsed reading hall, the books long since dissolved to pulp. A construct of coral and bronze still stands guard over what's left.",
        "safe": False,
        "mob_spawns": [{"mob": "archive_construct", "max": 1}],
        "lore": "Old Vael was a seafaring realm with its own kings, its own gods, and -- by the look of this hall -- its own scholars, before a single storm and a wave that never receded took the whole island in one night. The First Hundred who survived rarely spoke of what they saw that night; this archive may be the closest thing left to their side of the story.",
    },
    "old_vael_shrine": {
        "name": "Shrine of the Drowned Choir",
        "description": "A circular shrine, its altar carved with many-armed shapes rising from waves. Candles that shouldn't still be burning down here flicker in wall niches.",
        "safe": False,
        "mob_spawns": [{"mob": "cult_zealot", "max": 1}],
        "lore": "The Drowned Choir cultists believe Old Vael's patron never died with the island -- only slept -- and that enough devotion (or enough sacrifice) will wake it, and the island, both. The Concord has hunted this cult out of the city proper twice. They keep coming back to the ruins instead.",
    },
    "flooded_vault": {
        "name": "Flooded Vault",
        "description": "A small chamber behind a corroded bronze door, the air inside strangely dry compared to everything around it.",
        "safe": True,
        "container": {"name": "a corroded bronze door", "requires_key": "vael_sigil", "loot": ["vael_trident", "healing_potion"]},
    },
    "the_deep_maw": {
        "name": "The Deep Maw",
        "description": "The plaza floor gives way entirely here, into a black, water-filled pit ringed by broken stone teeth. Something vast moves at the edge of your lantern light.",
        "safe": False,
        "mob_spawns": [{"mob": "the_tidewarden", "max": 1}],
        "lore": "Whatever the tidewarden once guarded, it has had three centuries alone down here to forget everything except guarding it. Killing it doesn't feel like a victory so much as an apology, several hundred years overdue, for whatever the First Hundred did to escape Old Vael in the first place.",
    },

    # ===================== ZONE: Temple Row / Hollow Yard =====================
    "shrine_walk": {
        "name": "Shrine Walk",
        "description": "A short colonnade off Temple Row, lined with smaller shrines tended by whichever priest has time that day.",
        "safe": True,
    },
    "shrine_of_tides": {
        "name": "Shrine of the Tideful Mother",
        "description": "A weather-worn shrine open to the sea air, hung with nets, shells, and small carved boats left as offerings.",
        "safe": True,
        "lore": "Sailors leave a carved boat here before any long voyage, and another if they make it back. The Tideful Mother is older than the Dawnmother's temple by most accounts -- older, some say, than Saltspire itself, brought ashore in the memory of the First Hundred rather than built fresh.",
    },
    "shrine_of_embers": {
        "name": "Shrine of the Emberfather",
        "description": "A small forge-shrine, its single hearth never quite allowed to go cold, tended in shifts by off-duty smiths.",
        "safe": True,
        "lore": "Brackwater the blacksmith lights this hearth himself most mornings before opening the forge. The Emberfather has no temple of his own, only this hearth and whatever smiths keep it burning -- which suits the guild just fine.",
    },
    "scholars_chapel": {
        "name": "The Scholar's Chapel",
        "description": "A quiet, book-lined chapel dedicated to careful thought rather than miracles. A single robed keeper reads by a shuttered lamp.",
        "safe": True,
        "lore": "The Keeper of Pages asks nothing of worshippers except that they read something true before bed. The chapel's modest shelves are the only surviving copies of several First Hundred accounts -- the town archive across the city has long wanted to buy them and been politely, permanently refused.",
    },
    "hollow_yard_gate": {
        "name": "Hollow Yard Gate",
        "description": "A low iron gate, more symbolic than functional, marks the edge of the cemetery grounds.",
        "safe": True,
    },
    "hollow_yard": {
        "name": "The Hollow Yard",
        "description": "Rows of leaning headstones spread out under a permanently overcast patch of sky. The grass here never seems to grow past ankle height.",
        "safe": False,
        "mob_spawns": [{"mob": "graveyard_rat", "max": 2}, {"mob": "restless_spirit", "max": 1}],
    },
    "old_graves": {
        "name": "The Old Graves",
        "description": "The oldest section of the yard, headstones worn smooth and unreadable, dating back to the city's first decades.",
        "safe": False,
        "mob_spawns": [{"mob": "skeletal_sentry", "max": 1}],
    },
    "weeping_willow": {
        "name": "The Weeping Willow",
        "description": "A single ancient willow stands over a small, fenced plot, its branches trailing low enough to brush the ground.",
        "safe": True,
        "lore": "No one buried under the willow has a name on record. Locals call it the First Hundred's plot, on the theory that the last of the original refugees are here -- unmarked on purpose, since none of them wanted a monument grander than the people who didn't survive the crossing.",
    },
    "mausoleum_row": {
        "name": "Mausoleum Row",
        "description": "Stone mausoleums line a narrow gravel path, doors long since rusted shut -- except one, hanging open at an angle that suggests it wasn't opened politely.",
        "safe": False,
        "mob_spawns": [{"mob": "ghoul", "max": 1}],
    },
    "the_sealed_crypt": {
        "name": "The Sealed Crypt",
        "description": "A descending stair behind the broken mausoleum door, air thick with dust that hasn't moved in a very long time.",
        "safe": False,
        "mob_spawns": [{"mob": "crypt_wight", "max": 1}],
    },
    "the_bone_warden_hall": {
        "name": "Hall of the Bone Warden",
        "description": "A burial hall at the crypt's lowest point, centered on a sarcophagus too large for any person. It is, regrettably, not empty.",
        "safe": False,
        "mob_spawns": [{"mob": "the_bone_warden", "max": 1}],
        "lore": "No record in the town archive explains who the bone warden was meant to guard, or from what. Whoever sealed this crypt clearly expected someone to come digging eventually -- and built accordingly.",
    },

    # ===================== ZONE: Trade Quarter expansion =====================
    "mercenary_board": {
        "name": "The Mercenary Board",
        "description": "A weathered board outside the guildhall, pinned thick with contracts, bounty notices, and at least one challenge to a duel that's clearly gone unanswered for weeks.",
        "safe": True,
        "lore": "Guild contracts here range from 'clear the rats from my cellar' to bounties on named Undertow lieutenants, posted (unofficially) by Concord guards who can't act on them directly. Read close enough and you can track most of Saltspire's quiet conflicts just from what's nailed to this board.",
    },
    "tannery": {
        "name": "The Tannery",
        "description": "The smell hits before the doorway does -- hides stretched on racks, vats of curing solution, and a tanner who's long since stopped noticing the stench.",
        "safe": True,
    },
    "weavers_row": {
        "name": "Weavers' Row",
        "description": "Looms clatter behind open shopfronts, bolts of dyed cloth hung to air in the salt breeze.",
        "safe": True,
        "shop": ["padded_tunic", "woolen_cloak"],
    },
    "town_archive": {
        "name": "The Town Archive",
        "description": "Tall shelves of bound ledgers and survivor accounts fill a surprisingly grand reading room for such a young city. An archivist watches you over half-moon spectacles.",
        "safe": True,
        "lore": "The archive holds Saltspire's official memory: the First Hundred's landing, the founding of the Harbor Concord, the breaking of the Red Tide fleet at what's now called the salt fields, and the long, still-unfinished argument over how much of Old Vael's fall their ancestors actually caused. The archivist will tell you, if asked directly, that the missing pages were missing long before she took the job.",
    },
    "apothecary": {
        "name": "The Apothecary",
        "description": "Shelves of corked vials and dried herbs in precise rows. The apothecary measures every dose twice and trusts no one's description of their own symptoms.",
        "safe": True,
        "shop": ["greater_healing_potion", "mana_draught", "soothing_tonic"],
    },
    "jeweler": {
        "name": "Tessaline's Jewels",
        "description": "A narrow shop crowded with display cases, each piece individually lit to look more valuable than the last.",
        "safe": True,
        "shop": ["garnet_ring", "engraved_locket"],
    },

    # ===================== ZONE: Guild Concourse =====================
    "guild_concourse": {
        "name": "The Hall of Banners",
        "description": "A vaulted concourse north of the mercenary board, four banners hanging from the rafters -- crossed blades, an open eye, a raised hand wreathed in light, and a banner with no device at all. Each marks the entrance to one of the city's professional guilds.",
        "safe": True,
        "lore": "Saltspire's four guilds predate the Harbor Concord itself -- the First Hundred organized along trade lines before they'd finished agreeing on a government. The Concord has tried, more than once, to fold them into something more official. All four have politely and unanimously declined.",
    },
    "warriors_guild": {
        "name": "The Warriors' Guild",
        "description": "A high-ceilinged training hall, weapon racks lining every wall and a sand-floored sparring ring at its center. The air smells of oiled steel and old sweat.",
        "safe": True,
        "trainer": {
            "name": "Garrick Stonefist",
            "klass": "warrior",
            "title": "Guildmaster",
            "description": "A broad-shouldered veteran with a nose broken in at least three different decades, Garrick watches every sparring match like he's grading it. He's outlived three duels he wasn't supposed to win.",
            "level": 100,
        },
    },
    "mages_guild": {
        "name": "The Mages' Guild",
        "description": "Built into the lowest chamber of the black spire that gave the city its name, this circular hall is lined with shelved tomes and humming with a faint, ever-present charge. Sigils chalked on the floor are redrawn fresh every morning.",
        "safe": True,
        "trainer": {
            "name": "Ottoline Vance",
            "klass": "mage",
            "title": "Archmagister",
            "description": "Ottoline speaks slowly and precisely, as though every sentence costs mana too. She has spent forty years studying the black spire from the inside and still won't say what, exactly, it is.",
            "level": 100,
        },
    },
    "clerics_guild": {
        "name": "The Clerics' Guild",
        "description": "A quiet chapter house of pale stone, distinct from the worship halls of Temple Row -- this is where the Dawnmother's clergy (and a few of the older household faiths besides) actually train.",
        "safe": True,
        "trainer": {
            "name": "Brother Aldous Wren",
            "klass": "cleric",
            "title": "High Hand",
            "description": "Aldous keeps his hands folded and his voice gentle, but he's blunt about doctrine and blunter about technique. He trained under three different faiths before the Concord made the chapter house non-denominational.",
            "level": 100,
        },
    },
    "rogues_guild": {
        "name": "The Rogues' Guild",
        "description": "A low, lamplit den beneath the concourse, reached by a trapdoor no map of Saltspire bothers to show. It isn't Undertow territory -- the two organizations simply agree not to ask too many questions about each other's business.",
        "safe": True,
        "trainer": {
            "name": "Sable Quick",
            "klass": "rogue",
            "title": "Guildmaster",
            "description": "Sable never quite seems to be looking at you and never quite seems to be anywhere else either. She took over the guild by out-waiting the last three guildmasters, which she considers a perfectly respectable method.",
            "level": 100,
        },
        "lore": "The Rogues' Guild predates the Undertow by at least a generation, and its charter -- such as it is -- specifically forbids smuggling, to keep the two outfits from ever formally merging. Whether that line has ever actually held is a question Sable answers with a smile and nothing else.",
    },

    # ===================== ZONE: Coast Road extended =====================
    "crossroads_shrine": {
        "name": "Crossroads Shrine",
        "description": "A small wayside shrine where the coast road forks, its stone worn smooth by generations of travelers touching it for luck.",
        "safe": True,
        "lore": "One road continues north along the bluffs toward Tallow's Reach; the other cuts south across open ground the locals still call the salt fields, where Saltspire's founders broke the Red Tide pirate fleet two hundred years ago. Most travelers touch the shrine before choosing either.",
    },
    "windswept_bluffs": {
        "name": "Windswept Bluffs",
        "description": "The road climbs along bare cliffs here, wind strong enough to lean into. The sea below churns white against black rock.",
        "safe": True,
    },
    "hamlet_road": {
        "name": "Hamlet Road",
        "description": "A gentler stretch of road descends toward the sound of gulls and the smell of drying nets.",
        "safe": True,
    },
    "tallows_reach": {
        "name": "Tallow's Reach",
        "description": "A small fishing hamlet of weathered cottages and drying racks, independent of Saltspire in name only. A trader's cart does brisk business near the well.",
        "safe": True,
        "shop": ["dried_rations", "fishing_net"],
        "lore": "Tallow's Reach predates Saltspire's outer walls -- a handful of First Hundred families settled here first, before the harbor town grew big enough to need its own High Ward. The Reach still elects its own headman and largely ignores the Concord's tariffs, and the Concord has decided, wisely, not to push the matter.",
    },
    "hollow_moor": {
        "name": "The Hollow Moor",
        "description": "Flat, marshy ground stretches inland from the hamlet, dotted with standing stones and the kind of mist that doesn't burn off by midday.",
        "safe": False,
        "mob_spawns": [{"mob": "will_o_wisp", "max": 1}, {"mob": "moor_wraith", "max": 1}],
    },
    "old_sentinel_base": {
        "name": "Old Sentinel, Base",
        "description": "A crumbling watchtower rises from the moor, its lower door long since kicked in.",
        "safe": False,
        "mob_spawns": [{"mob": "tower_brigand", "max": 1}],
    },
    "old_sentinel_top": {
        "name": "Old Sentinel, Top",
        "description": "The tower's upper room is open to the sky where the roof used to be. An old footlocker sits wedged in the corner, somehow undisturbed.",
        "safe": True,
        "container": {"name": "a weathered footlocker", "requires_key": None, "loot": ["sentinels_badge", "healing_potion"]},
        "lore": "Old Sentinel was the northernmost of three watchtowers built to give Tallow's Reach warning of another Red Tide-style raid. The other two collapsed into the sea decades ago. No one has formally decommissioned this one; no one has manned it either.",
    },
    "sea_cave_mouth": {
        "name": "Sea Cave Mouth",
        "description": "A wide cave opens at the foot of the bluffs, tide pools glittering near the entrance before the dark swallows the rest.",
        "safe": False,
        "mob_spawns": [{"mob": "cave_crab", "max": 2}],
    },
    "smugglers_cove": {
        "name": "Smugglers' Cove",
        "description": "A hidden cove deep in the sea caves, lantern-lit and stacked with crates -- the Undertow's other door into the city, far from any harbormaster's eyes.",
        "safe": False,
        "mob_spawns": [{"mob": "undertow_smuggler", "max": 2}],
        "lore": "This cove connects, by a long and unpleasant tunnel, all the way back to the warehouse district and the sewers beneath Saltspire proper. The Undertow has been moving goods through this exact route since before the current syndicate leadership was even born.",
    },
    "salt_fields": {
        "name": "The Salt Fields",
        "description": "Open, salt-crusted ground south of the crossroads, oddly barren even by coastal standards. Old wreckage -- timber, rusted blades, the curve of a hull -- still surfaces after hard rain.",
        "safe": False,
        "mob_spawns": [{"mob": "fallen_marauder", "max": 2}, {"mob": "red_tide_captain", "max": 1}],
        "lore": "Two hundred years ago the Red Tide fleet beached here intending to sack Saltspire while it was still a fraction of its current size. The town's founders -- still calling themselves the First Hundred's children -- met them on this field and won decisively enough that no pirate fleet has tried Saltspire since. Nothing grows here anymore. Locals have theories; none of them agree.",
    },
    "foothill_path": {
        "name": "Foothill Path",
        "description": "The coast road gives way to a rougher trail climbing into the hills, grass replaced by scree and wind-bent pine.",
        "safe": True,
    },
    "druids_grove": {
        "name": "The Old Grove",
        "description": "A circle of ancient trees stands undisturbed on the hillside, older than the road that now skirts around it out of what looks like respect.",
        "safe": True,
        "lore": "The grove predates Saltspire entirely -- predates the First Hundred's landing, by the look of the oldest trunks. A solitary warden who answers to no guild and no Concord seat tends it, and has for as long as anyone in Tallow's Reach can remember asking.",
    },
    "greyfang_pass": {
        "name": "Greyfang Pass",
        "description": "The trail ends at a narrow pass between two scarred peaks, scorched stone underfoot. Whatever made those scorch marks is plainly still in residence.",
        "safe": False,
        "mob_spawns": [{"mob": "ashwing_drake", "max": 1}],
        "lore": "No map made in Saltspire shows anything past Greyfang Pass -- not because nothing's there, but because no expedition has come back with enough notes to draw one. The ashwing drake seems content to guard the pass rather than range toward the coast, which everyone in the Concord has agreed, by unspoken consensus, not to test.",
    },
    "boggy_shallows": {
        "name": "Boggy Shallows",
        "description": "The foothill trail drops into wet ground here, reeds and standing water replacing solid earth underfoot.",
        "safe": False,
        "mob_spawns": [{"mob": "bog_leech", "max": 2}],
    },
    "the_fenmire": {
        "name": "The Fenmire",
        "description": "A sprawling, fog-choked swamp, all standing water and half-sunken deadwood. Distant, unhurried splashes suggest you're being watched from several directions at once.",
        "safe": False,
        "mob_spawns": [{"mob": "mire_kin", "max": 2}],
    },
    "drowned_thicket": {
        "name": "The Drowned Thicket",
        "description": "A dense stand of dead, waterlogged trees, branches knitted together overhead into a permanent twilight.",
        "safe": False,
        "mob_spawns": [{"mob": "swamp_stalker", "max": 1}],
    },
    "sunken_shrine_of_the_fen": {
        "name": "Sunken Shrine of the Fen",
        "description": "A half-collapsed stone shrine sinks slowly into the mire, moss-thick and reeking of stagnant water. Something old and unhappy with visitors lives here.",
        "safe": False,
        "mob_spawns": [{"mob": "fen_mother", "max": 1}],
        "lore": "The fen mother predates every record in the town archive and most of the legends in Tallow's Reach besides. She's never once come looking for Saltspire. Successive Wardens have all, eventually, agreed it's best to leave that arrangement exactly as it is.",
    },
}

EXISTING_ROOM_LORE = {
    "tavern": "The Rusty Anchor has stood on this corner since the town was a few dozen huts clustered at the base of the black spire. Records in the town archive credit its first hearth to one of the First Hundred outright, though three centuries of rebuilding mean nothing of the original timber survives.",
    "market_square": "The square was the First Hundred's original trading ground -- back when there was nothing to trade but salvage, salt fish, and whatever each family had managed to carry off a sinking island. The fountain at its center is a much later addition, paid for by guild coin once Saltspire could afford to be sentimental.",
    "high_ward": "Gildwater Heights rises just beyond this courtyard -- manors, the counting houses, and Warden Keep itself, where the Harbor Concord governs in full view of anyone who cares to watch the gate.",
    "temple_of_dawn": "The Dawnmother is Saltspire's newest faith, embraced widely only in the last century, but the older household gods -- the Tideful Mother, the Emberfather, the Keeper of Pages -- still keep their own quiet shrines along Temple Row for anyone who prefers older company.",
    "sewer_entrance": "Sewer crews who go too far down occasionally come back with stories of older brickwork, stranger stonework, and stairs that lead somewhere the city engineers never authorized. Most crews stop digging well before they'd find out for themselves.",
    "guildhall": "Half the contracts on the mercenary board just north of here started as a problem someone brought to this hall first, and got told -- not unkindly -- to go post it themselves.",
    "city_gate": "Beyond this gate the coast road runs north past Tallow's Reach and the salt fields, and -- if you believe the lighthouse keeper's stories -- toward foothills and mountains that no Saltspire survey has ever properly mapped.",
    "coast_road": "Somewhere past the treeline and the rocks, the road forks at a wayside shrine: one way toward a fishing hamlet that predates Saltspire itself, the other south toward the open ground where the Red Tide fleet met its end two centuries ago.",
}

LINKS = [
    # -- Gildwater Heights / Warden Keep --
    ("high_ward", "north", "gildwater_promenade"),
    ("gildwater_promenade", "east", "manor_row"),
    ("gildwater_promenade", "west", "the_gilt_lantern"),
    ("gildwater_promenade", "north", "silver_court"),
    ("manor_row", "north", "terraced_gardens"),
    ("terraced_gardens", "east", "hidden_grotto"),
    ("silver_court", "east", "counting_house"),
    ("silver_court", "north", "warden_gate"),
    ("warden_gate", "north", "keep_courtyard"),
    ("keep_courtyard", "east", "keep_barracks"),
    ("keep_courtyard", "west", "keep_armory"),
    ("keep_courtyard", "north", "concord_chamber"),
    ("concord_chamber", "down", "keep_dungeon"),

    # -- Dockside expansion --
    ("harbor_docks", "up", "harbor_pier"),
    ("harbor_pier", "north", "warehouse_row"),
    ("warehouse_row", "east", "smugglers_alley"),
    ("smugglers_alley", "down", "smugglers_den"),
    ("smugglers_den", "south", "the_low_tunnel"),
    ("harbor_pier", "west", "moored_galley_deck"),
    ("moored_galley_deck", "down", "galley_hold"),
    ("harbor_pier", "east", "lighthouse_base"),
    ("lighthouse_base", "up", "lighthouse_top"),
    ("fish_market", "east", "pawnshop"),
    ("fish_market", "south", "drowned_lantern_inn"),
    ("harbormaster_office", "east", "press_gang_corner"),

    # -- Sewers / Old Vael undercity --
    ("sewer_tunnel_2", "east", "sewer_tunnel_3"),
    ("sewer_tunnel_3", "south", "flooded_cistern"),
    ("sewer_lair", "down", "flooded_cistern"),
    ("flooded_cistern", "down", "undercity_stair"),
    ("undercity_stair", "down", "old_vael_plaza"),
    ("old_vael_plaza", "north", "old_vael_archive"),
    ("old_vael_archive", "down", "flooded_vault"),
    ("old_vael_plaza", "east", "old_vael_shrine"),
    ("old_vael_plaza", "south", "the_deep_maw"),

    # -- Temple Row / Hollow Yard --
    ("temple_row", "west", "shrine_walk"),
    ("temple_row", "south", "hollow_yard_gate"),
    ("shrine_walk", "north", "shrine_of_tides"),
    ("shrine_walk", "south", "shrine_of_embers"),
    ("shrine_walk", "west", "scholars_chapel"),
    ("hollow_yard_gate", "south", "hollow_yard"),
    ("hollow_yard", "east", "old_graves"),
    ("hollow_yard", "west", "weeping_willow"),
    ("hollow_yard", "south", "mausoleum_row"),
    ("mausoleum_row", "down", "the_sealed_crypt"),
    ("the_sealed_crypt", "down", "the_bone_warden_hall"),

    # -- Trade Quarter expansion --
    ("guildhall", "north", "mercenary_board"),
    ("guildhall", "south", "tannery"),
    ("guildhall", "west", "weavers_row"),
    ("mercenary_board", "east", "town_archive"),
    ("tannery", "east", "apothecary"),
    ("weavers_row", "south", "jeweler"),
    ("mercenary_board", "north", "guild_concourse"),
    ("guild_concourse", "north", "warriors_guild"),
    ("guild_concourse", "east", "mages_guild"),
    ("guild_concourse", "west", "clerics_guild"),
    ("guild_concourse", "down", "rogues_guild"),

    # -- Coast Road extended --
    ("coast_road", "west", "crossroads_shrine"),
    ("crossroads_shrine", "north", "windswept_bluffs"),
    ("crossroads_shrine", "south", "salt_fields"),
    ("windswept_bluffs", "north", "hamlet_road"),
    ("windswept_bluffs", "down", "sea_cave_mouth"),
    ("hamlet_road", "north", "tallows_reach"),
    ("tallows_reach", "east", "hollow_moor"),
    ("hollow_moor", "north", "old_sentinel_base"),
    ("old_sentinel_base", "up", "old_sentinel_top"),
    ("sea_cave_mouth", "west", "smugglers_cove"),
    ("bandit_camp", "north", "foothill_path"),
    ("foothill_path", "north", "druids_grove"),
    ("foothill_path", "west", "greyfang_pass"),
    ("foothill_path", "east", "boggy_shallows"),
    ("boggy_shallows", "south", "the_fenmire"),
    ("the_fenmire", "east", "drowned_thicket"),
    ("the_fenmire", "south", "sunken_shrine_of_the_fen"),

    # -- Cross-zone shortcut: dockside <-> sewers <-> sea caves --
    ("the_low_tunnel", "west", "sewer_tunnel_3"),
    ("the_low_tunnel", "south", "smugglers_cove"),
]

# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def _write_json(path, data):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def main():
    if os.path.exists(ITEMS_PATH):
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            items = json.load(f)
        with open(MOBS_PATH, "r", encoding="utf-8") as f:
            mobs = json.load(f)
        rooms = {}
        for shard_path in ROOM_SHARD_PATHS:
            if os.path.exists(shard_path):
                with open(shard_path, "r", encoding="utf-8") as f:
                    rooms.update(json.load(f))
    else:
        with open(LEGACY_WORLD_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        items, mobs, rooms = data["items"], data["mobs"], data["rooms"]

    items.update(NEW_ITEMS)
    mobs.update(NEW_MOBS)

    for rid, rdata in NEW_ROOMS.items():
        rdata.setdefault("exits", {})
        rdata.setdefault("safe", True)
        rdata.setdefault("mob_spawns", [])
        rdata.setdefault("shop", [])
        rdata.setdefault("services", [])
        rdata.setdefault("lore", "")
        rdata.setdefault("container", None)
        rooms[rid] = rdata

    for rid, lore in EXISTING_ROOM_LORE.items():
        rooms[rid]["lore"] = lore

    for a, direction, b in LINKS:
        link(rooms, a, direction, b)

    room_ids = sorted(rooms.keys())
    midpoint = (len(room_ids) + 1) // 2
    shard_1 = {rid: rooms[rid] for rid in room_ids[:midpoint]}
    shard_2 = {rid: rooms[rid] for rid in room_ids[midpoint:]}

    _write_json(ITEMS_PATH, items)
    _write_json(MOBS_PATH, mobs)
    _write_json(ROOM_SHARD_PATHS[0], shard_1)
    _write_json(ROOM_SHARD_PATHS[1], shard_2)
    print(f"Wrote {len(rooms)} rooms, {len(mobs)} mobs, {len(items)} items "
          f"to {ITEMS_PATH}, {MOBS_PATH}, and room shard files.")


if __name__ == "__main__":
    main()
