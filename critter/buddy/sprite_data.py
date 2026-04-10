"""
ASCII sprite data for all 18 buddy species.
Ported from Buddi's SpriteData.swift - identical art.
"""

from .identity import Eye, Hat, Species

# {E} is replaced with the eye character at render time.
# Each species has 3 animation frames, each frame has 5 lines.
BODIES: dict[Species, list[list[str]]] = {
    Species.DUCK: [
        ["            ", "    __      ", "  <({E} )___  ", "   (  ._>   ", "    `--\u00b4    "],
        ["            ", "    __      ", "  <({E} )___  ", "   (  ._>   ", "    `--\u00b4~   "],
        ["            ", "    __      ", "  <({E} )___  ", "   (  .__>  ", "    `--\u00b4    "],
    ],
    Species.GOOSE: [
        ["            ", "     ({E}>    ", "     ||     ", "   _(__)_   ", "    ^^^^    "],
        ["            ", "    ({E}>     ", "     ||     ", "   _(__)_   ", "    ^^^^    "],
        ["            ", "     ({E}>>   ", "     ||     ", "   _(__)_   ", "    ^^^^    "],
    ],
    Species.BLOB: [
        ["            ", "   .----.   ", "  ( {E}  {E} )  ", "  (      )  ", "   `----\u00b4   "],
        ["            ", "  .------.  ", " (  {E}  {E}  ) ", " (        ) ", "  `------\u00b4  "],
        ["            ", "    .--.    ", "   ({E}  {E})   ", "   (    )   ", "    `--\u00b4    "],
    ],
    Species.CAT: [
        ["            ", "   /\\_/\\    ", "  ( {E}   {E})  ", "  (  \u03c9  )   ", '  (")\\_(")\\ '],
        ["            ", "   /\\_/\\    ", "  ( {E}   {E})  ", "  (  \u03c9  )   ", '  (")\\_(")\\ '],
        ["            ", "   /\\-/\\    ", "  ( {E}   {E})  ", "  (  \u03c9  )   ", '  (")\\_(")\\ '],
    ],
    Species.DRAGON: [
        ["            ", "  /^\\  /^\\  ", " <  {E}  {E}  > ", " (   ~~   ) ", "  `-vvvv-\u00b4  "],
        ["            ", "  /^\\  /^\\  ", " <  {E}  {E}  > ", " (        ) ", "  `-vvvv-\u00b4  "],
        ["   ~    ~   ", "  /^\\  /^\\  ", " <  {E}  {E}  > ", " (   ~~   ) ", "  `-vvvv-\u00b4  "],
    ],
    Species.OCTOPUS: [
        ["            ", "   .----.   ", "  ( {E}  {E} )  ", "  (______)  ", "  /\\/\\/\\/\\  "],
        ["            ", "   .----.   ", "  ( {E}  {E} )  ", "  (______)  ", "  \\/\\/\\/\\/  "],
        ["     o      ", "   .----.   ", "  ( {E}  {E} )  ", "  (______)  ", "  /\\/\\/\\/\\  "],
    ],
    Species.OWL: [
        ["            ", "   /\\  /\\   ", "  (({E})({E}))  ", "  (  ><  )  ", "   `----\u00b4   "],
        ["            ", "   /\\  /\\   ", "  (({E})({E}))  ", "  (  ><  )  ", "   .----.   "],
        ["            ", "   /\\  /\\   ", "  (({E})(-))  ", "  (  ><  )  ", "   `----\u00b4   "],
    ],
    Species.PENGUIN: [
        ["            ", "  .---.     ", "  ({E}>{E})     ", " /(   )\\    ", "  `---\u00b4     "],
        ["            ", "  .---.     ", "  ({E}>{E})     ", " |(   )|    ", "  `---\u00b4     "],
        ["  .---.     ", "  ({E}>{E})     ", " /(   )\\    ", "  `---\u00b4     ", "   ~ ~      "],
    ],
    Species.TURTLE: [
        ["            ", "   _,--._   ", "  ( {E}  {E} )  ", " /[______]\\ ", "  ``    ``  "],
        ["            ", "   _,--._   ", "  ( {E}  {E} )  ", " /[______]\\ ", "   ``  ``   "],
        ["            ", "   _,--._   ", "  ( {E}  {E} )  ", " /[======]\\ ", "  ``    ``  "],
    ],
    Species.SNAIL: [
        ["            ", " {E}    .--.  ", "  \\  ( @ )  ", "   \\_`--\u00b4   ", "  ~~~~~~~   "],
        ["            ", "  {E}   .--.  ", "  |  ( @ )  ", "   \\_`--\u00b4   ", "  ~~~~~~~   "],
        ["            ", " {E}    .--.  ", "  \\  ( @  ) ", "   \\_`--\u00b4   ", "   ~~~~~~   "],
    ],
    Species.GHOST: [
        ["            ", "   .----.   ", "  / {E}  {E} \\  ", "  |      |  ", "  ~`~``~`~  "],
        ["            ", "   .----.   ", "  / {E}  {E} \\  ", "  |      |  ", "  `~`~~`~`  "],
        ["    ~  ~    ", "   .----.   ", "  / {E}  {E} \\  ", "  |      |  ", "  ~~`~~`~~  "],
    ],
    Species.AXOLOTL: [
        ["            ", "}~(______)~{", "}~({E} .. {E})~{", "  ( .--. )  ", "  (_/  \\_)  "],
        ["            ", "~}(______){~", "~}({E} .. {E}){~", "  ( .--. )  ", "  (_/  \\_)  "],
        ["            ", "}~(______)~{", "}~({E} .. {E})~{", "  (  --  )  ", "  ~_/  \\_~  "],
    ],
    Species.CAPYBARA: [
        ["            ", "  n______n  ", " ( {E}    {E} ) ", " (   oo   ) ", "  `------\u00b4  "],
        ["            ", "  n______n  ", " ( {E}    {E} ) ", " (   Oo   ) ", "  `------\u00b4  "],
        ["    ~  ~    ", "  u______n  ", " ( {E}    {E} ) ", " (   oo   ) ", "  `------\u00b4  "],
    ],
    Species.CACTUS: [
        ["            ", " n  ____  n ", " | |{E}  {E}| | ", " |_|    |_| ", "   |    |   "],
        ["            ", "    ____    ", " n |{E}  {E}| n ", " |_|    |_| ", "   |    |   "],
        [" n        n ", " |  ____  | ", " | |{E}  {E}| | ", " |_|    |_| ", "   |    |   "],
    ],
    Species.ROBOT: [
        ["            ", "   .[||].   ", "  [ {E}  {E} ]  ", "  [ ==== ]  ", "  `------\u00b4  "],
        ["            ", "   .[||].   ", "  [ {E}  {E} ]  ", "  [ -==- ]  ", "  `------\u00b4  "],
        ["     *      ", "   .[||].   ", "  [ {E}  {E} ]  ", "  [ ==== ]  ", "  `------\u00b4  "],
    ],
    Species.RABBIT: [
        ["            ", "   (\\__/)   ", "  ( {E}  {E} )  ", " =(  ..  )= ", '  (")__(")  '],
        ["            ", "   (|__/)   ", "  ( {E}  {E} )  ", " =(  ..  )= ", '  (")__(")  '],
        ["            ", "   (\\__/)   ", "  ( {E}  {E} )  ", " =( .  . )= ", '  (")__(")  '],
    ],
    Species.MUSHROOM: [
        ["            ", " .-o-OO-o-. ", "(__________)", "   |{E}  {E}|   ", "   |____|   "],
        ["            ", " .-O-oo-O-. ", "(__________)", "   |{E}  {E}|   ", "   |____|   "],
        ["   . o  .   ", " .-o-OO-o-. ", "(__________)", "   |{E}  {E}|   ", "   |____|   "],
    ],
    Species.CHONK: [
        ["            ", "  /\\    /\\  ", " ( {E}    {E} ) ", " (   ..   ) ", "  `------\u00b4  "],
        ["            ", "  /\\    /|  ", " ( {E}    {E} ) ", " (   ..   ) ", "  `------\u00b4  "],
        ["            ", "  /\\    /\\  ", " ( {E}    {E} ) ", " (   ..   ) ", "  `------\u00b4~ "],
    ],
}

HAT_LINES: dict[Hat, str] = {
    Hat.NONE: "",
    Hat.CROWN: "   \\^^^/    ",
    Hat.TOPHAT: "   [___]    ",
    Hat.PROPELLER: "    -+-     ",
    Hat.HALO: "   (   )    ",
    Hat.WIZARD: "    /^\\     ",
    Hat.BEANIE: "   (___)    ",
    Hat.TINYDUCK: "    ,>      ",
}


def face(species: Species, eye: Eye) -> str:
    """One-line face string for a species + eye combo."""
    e = eye.value
    match species:
        case Species.DUCK | Species.GOOSE:
            return f"({e}>"
        case Species.BLOB:
            return f"({e}{e})"
        case Species.CAT:
            return f"={e}\u03c9{e}="
        case Species.DRAGON:
            return f"<{e}~{e}>"
        case Species.OCTOPUS:
            return f"~({e}{e})~"
        case Species.OWL:
            return f"({e})({e})"
        case Species.PENGUIN:
            return f"({e}>)"
        case Species.TURTLE:
            return f"[{e}_{e}]"
        case Species.SNAIL:
            return f"{e}(@)"
        case Species.GHOST:
            return f"/{e}{e}\\"
        case Species.AXOLOTL:
            return f"}}{e}.{e}{{"
        case Species.CAPYBARA:
            return f"({e}oo{e})"
        case Species.CACTUS:
            return f"|{e}  {e}|"
        case Species.ROBOT:
            return f"[{e}{e}]"
        case Species.RABBIT:
            return f"({e}..{e})"
        case Species.MUSHROOM:
            return f"|{e}  {e}|"
        case Species.CHONK:
            return f"({e}.{e})"


def render_frame(
    species: Species, eye: Eye, hat: Hat, frame: int
) -> list[str]:
    """Render a full multi-line sprite frame."""
    frames = BODIES.get(species, [])
    if not frames:
        return []

    body = frames[frame % len(frames)]
    lines = [line.replace("{E}", eye.value) for line in body]

    # Replace first blank line with hat if applicable
    if hat != Hat.NONE and lines and lines[0].strip() == "":
        hat_line = HAT_LINES.get(hat, "")
        if hat_line:
            lines[0] = hat_line

    # Strip leading blank line if all frames have one
    if (
        lines
        and lines[0].strip() == ""
        and all(
            (f[0].strip() == "" if f else True) for f in frames
        )
    ):
        lines = lines[1:]

    return lines
