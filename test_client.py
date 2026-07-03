"""Scripted smoke test: drives the game over a real WebSocket connection and
prints every line received, so we can eyeball correctness end-to-end.
Combat resolves on the server's 2s tick, so we collect messages with an
idle-timeout rather than expecting an immediate reply."""
import asyncio
import re
import sys
import websockets

URL = "ws://127.0.0.1:8000/ws"

# All test characters share this password. The bundled sample characters
# (Brogan, Thessaly, Elowen) predate the password feature and have none set,
# so the first run against each of them sets this password (the "legacy
# migration" prompt); every run after that logs in with it normally.
TEST_PASSWORD = "testpass1"

# Mirrors main.py's CTRL_PREFIX -- a null-byte-prefixed marker the server
# sends to tell the browser client to mask the input box during password
# prompts. It carries no content of its own, so this script just skips it.
CTRL_PREFIX = "\x00CTRL\x00"


def clean(line: str) -> str:
    line = line.replace("<br>", "\n   ").replace("&nbsp;", " ")
    line = line.replace("&mdash;", "-").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    line = re.sub(r"<[^>]+>", "", line)
    return line


async def recv_line(ws):
    """Receives one real (non-control) message, transparently skipping over
    any password-mask toggle markers along the way."""
    while True:
        msg = await ws.recv()
        if msg.startswith(CTRL_PREFIX):
            continue
        return clean(msg)


async def collect(ws, idle_timeout=0.8, max_total=4.0):
    loop = asyncio.get_event_loop()
    start = loop.time()
    out = []
    while loop.time() - start < max_total:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=idle_timeout)
            if msg.startswith(CTRL_PREFIX):
                continue
            out.append(clean(msg))
        except asyncio.TimeoutError:
            break
        except websockets.exceptions.ConnectionClosed:
            break
    return out


async def send_and_print(ws, cmd):
    print(f">>> {cmd}", flush=True)
    await ws.send(cmd)
    # Combat resolves on a 2s server tick -- idle_timeout must exceed that or
    # we'll bail out between ticks while the fight is still going.
    if cmd.startswith("kill") or cmd.startswith("bash"):
        idle_timeout, max_total = 2.5, 18.0
    elif cmd.startswith("cast"):
        idle_timeout, max_total = 2.5, 12.0
    else:
        idle_timeout, max_total = 0.8, 4.0
    for line in await collect(ws, idle_timeout=idle_timeout, max_total=max_total):
        print(line, flush=True)


async def run(name, race, klass, script, password=TEST_PASSWORD):
    async with websockets.connect(URL) as ws:
        print(f"\n===== session for {name} =====", flush=True)
        print(await recv_line(ws), flush=True)     # banner
        print(await recv_line(ws), flush=True)     # name prompt
        await ws.send(name)

        reply = await recv_line(ws)
        print(reply, flush=True)
        if "unknown" in reply:                          # server doesn't know this name yet
            await ws.send("yes")
            print(await recv_line(ws), flush=True)      # race prompt
            await ws.send(race)
            print(await recv_line(ws), flush=True)      # class prompt
            await ws.send(klass)
            print(await recv_line(ws), flush=True)      # "choose a password" prompt
            await ws.send(password)
            print(await recv_line(ws), flush=True)      # "confirm password" prompt
            await ws.send(password)
            print(await recv_line(ws), flush=True)      # welcome
        elif "no password set yet" in reply:            # legacy character (predates auth): claim it
            print(await recv_line(ws), flush=True)      # "new password" prompt
            await ws.send(password)
            print(await recv_line(ws), flush=True)      # "confirm password" prompt
            await ws.send(password)
            print(await recv_line(ws), flush=True)      # "password set, welcome back"
        else:                                            # existing character, already has a password
            # `reply` above *is* the "Password:" prompt -- ask_secret's CTRL_ON
            # marker was already transparently skipped by recv_line() when we
            # read `reply`, so don't try to read the prompt a second time here
            # (that would just block forever waiting for a message the server
            # has already sent). Just answer it.
            await ws.send(password)
            print(await recv_line(ws), flush=True)      # "welcome back" (or an error, if wrong)

        for line in await collect(ws, idle_timeout=0.8, max_total=2.5):
            print(line, flush=True)

        for cmd in script:
            await send_and_print(ws, cmd)

        print(f"===== end session for {name} =====", flush=True)


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "new"

    if mode == "new":
        await run("Thessaly", "human", "warrior", [
            "look",
            "score",
            "inventory",
            "equipment",
            "east",             # -> harbor_docks
            "down",             # -> sewer_entrance
            "north",            # -> sewer_tunnel_1 (rats)
            "kill rat",
            "score",
            "south", "up", "west", "north", "east",  # -> blacksmith
            "list",
            "buy short sword",
            "wear short sword",
            "sell rusty dagger",
            "west", "south", "south", "east",  # -> temple_of_dawn
            "pray",
            "score",
            "quit",
        ])
    elif mode == "reconnect":
        await run("Brogan", "human", "warrior", [
            "score",
            "inventory",
            "equipment",
            "quit",
        ])
    elif mode == "mage":
        await run("Elowen", "elf", "mage", [
            "score",
            "east", "east", "north", "north",  # -> wolf_den
            "cast missile wolf",
            "cast missile wolf",
            "cast missile wolf",
            "score",
            "quit",
        ])
    elif mode == "admin":
        # Requires an admin character to already exist -- run, e.g.:
        #   python3 create_admin.py Admin adminpass123
        # first, then: python3 test_client.py admin
        await run("Admin", "human", "warrior", [
            "rooms",
            "dig down vault A Hidden Vault",
            "goto vault",
            "rdesc A small vault, still smelling of fresh-turned earth.",
            "rsafe off",
            "look",
            "rsafe on",
            "who",
            "help",
            "quit",
        ], password="adminpass123")


if __name__ == "__main__":
    asyncio.run(main())
