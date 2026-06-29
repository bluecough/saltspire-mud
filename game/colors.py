"""
Tiny helper for building lightly-colored HTML output that gets streamed to the
browser terminal. Anything that came from a player (names typed in, chat text)
MUST go through esc()/safe_tag() before being embedded, since the client
renders these strings with innerHTML.
"""
import html as _html

def esc(text) -> str:
    """Escape user-supplied text before embedding in HTML output."""
    return _html.escape(str(text), quote=False)

def tag(text: str, css_class: str) -> str:
    """Wrap already-safe (developer-authored) text in a colored span."""
    return f'<span class="{css_class}">{text}</span>'

def safe_tag(text, css_class: str) -> str:
    """Escape then wrap user-supplied text in a colored span."""
    return tag(esc(text), css_class)

# Convenience shorthands used throughout the engine/commands modules.
def room(text): return tag(text, "c-room")
def exit_(text): return tag(text, "c-exit")
def mob(text): return safe_tag(text, "c-mob")
def item(text): return safe_tag(text, "c-item")
def player(text): return safe_tag(text, "c-player")
def dmg(text): return tag(str(text), "c-dmg")
def heal(text): return tag(str(text), "c-heal")
def gold(text): return tag(str(text), "c-gold")
def say(text): return safe_tag(text, "c-say")
def system(text): return safe_tag(text, "c-system")
def error(text): return safe_tag(text, "c-error")
def help_(text): return tag(text, "c-help")
def admin(text): return safe_tag(text, "c-admin")
