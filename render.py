"""News front page renderer for 21 November 2026.

Pure standard library: own 5x7 bitmap font, own PNG encoder (zlib + struct).
No network, no randomness, no time dependence: two runs are byte-identical.
"""

import math
import struct
import zlib

# ---------------------------------------------------------------- font
# Each glyph is 7 rows of 5 bits, packed as 7 base32 chars (0-9, a-v).
# Bit 4 (value 16) is the leftmost pixel of the row.
FONT = {
    " ": "0000000", "!": "4444404", '"': "aa00000", "#": "aavavaa",
    "$": "4fke5u4", "%": "pq248bj", "&": "cik8lid", "'": "4480000",
    "(": "2488842", ")": "8422248", "*": "0lele00", "+": "044v440",
    ",": "0000c48", "-": "000v000", ".": "00000cc", "/": "122488g",
    "0": "ehjlphe", "1": "4c4444e", "2": "eh168gv", "3": "v2421he",
    "4": "26aiv22", "5": "vgu11he", "6": "68guhhe", "7": "v124888",
    "8": "ehhehhe", "9": "ehhf12c", ":": "0cc0cc0", ";": "0cc0c48",
    "<": "248g842", "=": "00v0v00", ">": "8421248", "?": "eh16404",
    "@": "ehnlmge", "A": "ehhvhhh", "B": "uhhuhhu", "C": "ehggghe",
    "D": "uhhhhhu", "E": "vgguggv", "F": "vgguggg", "G": "ehgnhhf",
    "H": "hhhvhhh", "I": "e44444e", "J": "72222ic", "K": "hikokih",
    "L": "ggggggv", "M": "hrllhhh", "N": "hpljhhh", "O": "ehhhhhe",
    "P": "uhhuggg", "Q": "ehhhlid", "R": "uhhukih", "S": "fgge11u",
    "T": "v444444", "U": "hhhhhhe", "V": "hhhhha4", "W": "hhhllrh",
    "X": "hha4ahh", "Y": "hha4444", "Z": "v1248gv", "[": "e88888e",
    "]": "e22222e", "^": "4a00000", "_": "000000v", "a": "00e1fhf",
    "b": "ggmphhu", "c": "00egghe", "d": "11djhhf", "e": "00ehvge",
    "f": "698u888", "g": "0fhhf1e", "h": "ggmphhh", "i": "40c444e",
    "j": "20622ic", "k": "ggikoki", "l": "c44444e", "m": "00qllll",
    "n": "00mphhh", "o": "00ehhhe", "p": "00mphug", "q": "00djhf1",
    "r": "00mpggg", "s": "00fge1u", "t": "88u8886", "u": "00hhhjd",
    "v": "00hhha4", "w": "00hllla", "x": "00ha4ah", "y": "00hhb5e",
    "z": "00v248v", "|": "4444444", "~": "009m000",
    "°": "cic0000", "•": "00cc000",
}

# Map stray unicode punctuation to plain ASCII equivalents.
_NORMALIZE = {
    "–": "-", "—": "-", "−": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", "×": "x", "·": "-",
}


def _norm(text):
    return "".join(_NORMALIZE.get(ch, ch) for ch in text)


def _glyph_rows(ch):
    packed = FONT.get(ch)
    if packed is None:
        packed = FONT["?"]
    return [int(c, 32) for c in packed]


# ---------------------------------------------------------------- canvas
PAPER = (247, 243, 234)
INK = (26, 26, 26)
NAVY = (20, 33, 61)
RED = (176, 42, 42)
GREY = (110, 108, 100)
LIGHT = (233, 228, 216)
GOLD = (196, 148, 44)
SKY = (38, 68, 110)
SEA = (46, 110, 160)
LEAF = (74, 140, 74)


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.buf), 3):
            self.buf[i] = r
            self.buf[i + 1] = g
            self.buf[i + 2] = b

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i], self.buf[i + 1], self.buf[i + 2] = color

    def rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        r, g, b = color
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.buf[i] = r
                self.buf[i + 1] = g
                self.buf[i + 2] = b

    def hline(self, x0, x1, y, color):
        if x0 > x1:
            x0, x1 = x1, x0
        for x in range(max(0, x0), min(self.w, x1 + 1)):
            self.set(x, y, color)

    def vline(self, x, y0, y1, color):
        if y0 > y1:
            y0, y1 = y1, y0
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            self.set(x, y, color)

    def line(self, x0, y0, x1, y1, color):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color, fill=True):
        if fill:
            for dy in range(-r, r + 1):
                dx = int(math.sqrt(max(0, r * r - dy * dy)))
                self.hline(cx - dx, cx + dx, cy + dy, color)
        else:
            steps = max(24, int(2 * math.pi * r))
            for k in range(steps):
                a = 2 * math.pi * k / steps
                self.set(int(cx + r * math.cos(a)), int(cy + r * math.sin(a)), color)

    def poly_fill(self, pts, color):
        # Even-odd scanline fill.
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            nodes = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    nodes.append(int(x0 + (y - y0) * (x1 - x0) / (y1 - y0)))
            nodes.sort()
            for k in range(0, len(nodes) - 1, 2):
                self.hline(nodes[k], nodes[k + 1], y, color)

    # -- text ------------------------------------------------------
    def text_w(self, s, scale):
        s = _norm(s)
        return max(0, len(s) * 6 - 1) * scale

    def text(self, x, y, s, scale, color, bold=False):
        s = _norm(s)
        cx = x
        for ch in s:
            rows = _glyph_rows(ch)
            for ry in range(7):
                bits = rows[ry]
                for rx in range(5):
                    if bits & (16 >> rx):
                        self.rect(cx + rx * scale, y + ry * scale,
                                  scale, scale, color)
            if bold:
                for ry in range(7):
                    bits = rows[ry]
                    for rx in range(5):
                        if bits & (16 >> rx):
                            self.rect(cx + rx * scale + 1, y + ry * scale,
                                      scale, scale, color)
            cx += 6 * scale
        return cx

    def text_centred(self, cx, y, s, scale, color, bold=False):
        w = self.text_w(s, scale) + (scale if bold else 0)
        return self.text(cx - w // 2, y, s, scale, color, bold)

    def wrap(self, s, maxw, scale):
        words = _norm(s).split(" ")
        lines = []
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if self.text_w(trial, scale) <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, y, s, maxw, scale, color, lh, bold=False, max_lines=None):
        lines = self.wrap(s, maxw, scale)
        if max_lines is not None:
            lines = lines[:max_lines]
        for i, line in enumerate(lines):
            self.text(x, y + i * lh, line, scale, color, bold)
        return len(lines) * lh

    def png(self):
        raw = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            raw.append(0)
            raw += self.buf[y * stride:(y + 1) * stride]
        comp = zlib.compress(bytes(raw), 9)

        def chunk(tag, data):
            out = struct.pack(">I", len(data)) + tag + data
            out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            return out

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- artwork
def art_blast(cv, x, y, w, h):
    """Night strike over a city: dark sky, buildings, blast burst."""
    cv.rect(x, y, w, h, SKY)
    cv.circle(x + w - 18, y + 16, 9, (240, 220, 140))
    # buildings
    for bx, bw, bh in [(0, 34, 46), (40, 26, 60), (72, 40, 38),
                       (118, 30, 54), (154, 36, 42), (196, 30, 58),
                       (232, 40, 36), (276, 34, 50)]:
        cv.rect(x + bx, y + h - bh, bw, bh, (16, 22, 40))
        for wy in range(y + h - bh + 6, y + h - 6, 12):
            for wx in range(x + bx + 5, x + bx + bw - 4, 10):
                cv.rect(wx, wy, 3, 4, (240, 200, 90))
    # blast burst above the roofs, low over the skyline
    cx, cy = x + 150, y + 34
    for k in range(12):
        a = 2 * math.pi * k / 12
        cv.line(cx, cy, int(cx + 30 * math.cos(a)), int(cy + 30 * math.sin(a)),
                (255, 190, 60))
    cv.circle(cx, cy, 12, (255, 210, 80))
    cv.circle(cx, cy, 6, (255, 240, 170))
    cv.circle(x + 118, y + 16, 8, (90, 90, 90))
    cv.circle(x + 132, y + 10, 6, (110, 110, 110))
    cv.circle(x + 60, y + 20, 7, (150, 150, 150))
    cv.circle(x + 80, y + 14, 9, (170, 170, 170))


def art_shield(cv, x, y, w, h):
    """Gold badge shield on a deep red field."""
    cv.rect(x, y, w, h, (122, 30, 30))
    for dx in range(0, w, 26):
        cv.circle(x + dx + 8, y + h - 10, 2, (150, 45, 45))
    cx = x + w // 2
    top = y + 8
    pts = [(cx - 52, top), (cx + 52, top), (cx + 52, top + 34),
           (cx, top + 68), (cx - 52, top + 34)]
    cv.poly_fill(pts, GOLD)
    cv.poly_fill([(cx - 44, top + 6), (cx + 44, top + 6), (cx + 44, top + 32),
                  (cx, top + 60), (cx - 44, top + 32)], (232, 190, 80))
    # five-point star in the shield
    sx, sy, r = cx, top + 30, 16
    star = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.42
        star.append((int(sx + rr * math.cos(ang)), int(sy + rr * math.sin(ang))))
    cv.poly_fill(star, (122, 30, 30))


def art_globe(cv, x, y, w, h):
    """Globe with land blobs and a rising sun."""
    cv.rect(x, y, w, h, (214, 232, 240))
    cv.circle(x + w - 26, y + 18, 11, (240, 190, 60))
    for k in range(8):
        a = 2 * math.pi * k / 8
        cv.line(x + w - 26, y + 18,
                int(x + w - 26 + 18 * math.cos(a)),
                int(y + 18 + 18 * math.sin(a)), (240, 190, 60))
    cx, cy, r = x + w // 2, y + h // 2 + 4, 34
    cv.circle(cx, cy, r, SEA)
    cv.circle(cx - 12, cy - 8, 9, LEAF)
    cv.circle(cx + 10, cy + 6, 11, LEAF)
    cv.circle(cx + 14, cy - 14, 6, LEAF)
    cv.circle(cx - 14, cy + 14, 6, LEAF)
    cv.circle(cx, cy, r, (255, 255, 255), fill=False)
    cv.circle(cx, cy, int(r * 0.55), (255, 255, 255), fill=False)
    cv.hline(cx - r, cx + r, cy, (255, 255, 255))
    cv.hline(cx - int(r * 0.86), cx + int(r * 0.86), cy - int(r * 0.5),
             (255, 255, 255))
    cv.hline(cx - int(r * 0.86), cx + int(r * 0.86), cy + int(r * 0.5),
             (255, 255, 255))


ART = {"blast": art_blast, "shield": art_shield, "globe": art_globe}


# ---------------------------------------------------------------- stories
# All stories verified with web search as having happened, or first been
# reported, on Saturday 21 November 2026.
TITLE = "THE DAY IN WORLD NEWS"
DATE_LINE = "SATURDAY 21 NOVEMBER 2026"
SUB_LINE = ("Every story on this page happened, or was first reported, "
            "on 21 November 2026.")

LEADS = [
    {
        "tag": "UKRAINE - CONFLICT",
        "art": "blast",
        "title": "Russian strike kills boy, 7, in Zelenskyy's hometown",
        "body": ("Ballistic missiles and drones hit a restaurant car park in "
                 "Kryvyi Rih on Friday night, killing a seven-year-old boy "
                 "and a 20-year-old paramedic and wounding 60. Rescuers were "
                 "hit by follow-up strikes."),
    },
    {
        "tag": "MEXICO - CRIME",
        "art": "shield",
        "title": "FBI most-wanted cartel boss seized; 11 killed in backlash",
        "body": ("Mexican special forces captured Fausto Isidro Meza Flores, "
                 "'El Chapo Isidro', in Guasave with US intelligence. Gunmen "
                 "torched trucks and fired on a baseball game as troops flew "
                 "him to Mexico City."),
    },
    {
        "tag": "TURKEY - CLIMATE",
        "art": "globe",
        "title": "COP31 runs into overtime as fossil fuels vanish from draft",
        "body": ("Nearly 200 nations are deadlocked in Antalya after a "
                 "slimmed-down draft dropped every mention of fossil fuels "
                 "and a $120bn adaptation target. The EU warned of a "
                 "'fossil summit'."),
    },
]

SECONDARY = [
    {
        "tag": "EUROPE - SECURITY",
        "title": "Russian missiles land in Poland; NATO calls it a violation",
        "body": ("One missile was confirmed down in Nowy Lipowiec; Warsaw "
                 "called it a provocation as allies weighed a response."),
    },
    {
        "tag": "MIDDLE EAST - CONFLICT",
        "title": "Strike on Gaza aid van kills three",
        "body": ("A drone hit a food-aid vehicle in Gaza City; four "
                 "Palestinians were killed on Saturday and 1,671 have died "
                 "since the October 2025 ceasefire."),
    },
    {
        "tag": "FINLAND - CONFLICT",
        "title": "Drones hit Russian ship in Gulf of Finland",
        "body": ("The Sparta II, bound for Kaliningrad, was hit by two drones "
                 "and its crew evacuated; a Russian helicopter then violated "
                 "Finnish airspace."),
    },
    {
        "tag": "MARKETS - ECONOMY",
        "title": "AI sell-off drags world markets into correction",
        "body": ("The S&P 500 fell 3.7% on Friday; the Nikkei dropped 5.06% "
                 "and the Hang Seng 3.79%, leaving indexes 10% or more below "
                 "recent highs."),
    },
    {
        "tag": "THE HAGUE - JUSTICE",
        "title": "World court: Myanmar guilty of Rohingya genocide",
        "body": ("The ICJ found Myanmar responsible for genocide against the "
                 "Rohingya - the first time any court has found a state "
                 "guilty of genocide."),
    },
    {
        "tag": "GULF - ENERGY",
        "title": "Tankers hit near Hormuz as US-Iran talks stall",
        "body": ("Iran struck three tankers and two more attacks were "
                 "reported near Oman's Khasab, as Trump weighed new strikes "
                 "on Iran."),
    },
    {
        "tag": "ASIA - DISASTER",
        "title": "Magnitude 7.2 quake strikes Indonesia's Maluku",
        "body": ("The quake struck Maluku with no tsunami threat; hours "
                 "earlier a 5.6-magnitude quake hit Qinghai in north-west "
                 "China."),
    },
    {
        "tag": "BRITAIN - SOCIETY",
        "title": "Princess Catherine speaks of her cancer journey",
        "body": ("In a new documentary the Princess of Wales reflects for "
                 "the first time on her diagnosis: 'It changes your body.'"),
    },
    {
        "tag": "TECH - SCIENCE",
        "title": "Mathematician claims AI helped prove Riemann",
        "body": ("Anthropic's Levent Alpoge says he and Claude formalised a "
                 "proof of the Riemann hypothesis. It has not been "
                 "independently verified."),
    },
]

NUMBERS = [
    ("-3.7%", "S&P 500 slide"),
    ("60", "wounded in Kryvyi Rih"),
    ("7.2", "Maluku quake magnitude"),
    ("11", "killed in Sinaloa violence"),
]

TIMELINE = [
    ("02:32 UTC", "5.6 quake hits Qinghai, China"),
    ("02:48 UTC", "7.2 quake strikes Maluku, Indonesia"),
    ("11:53 UTC", "Mexico confirms capture of 'El Chapo Isidro'"),
    ("12:29 UTC", "Gaza aid-van strike first reported"),
    ("15:22 UTC", "Gaza strike toll put at three dead"),
    ("19:15 UTC", "IDF says it struck three militants in Gaza"),
]

BRIEFS = [
    "WASHINGTON - Trump tells Europe to defund Ukraine after Putin summit.",
    "KYIV - Zelenskyy calls the Shenzhen summit 'very unsuccessful' for Putin.",
    "KYIV - PM says Ukraine received about 8 billion euros from the EU.",
    "WASHINGTON - Judge blocks Trump's 250-foot arch near Arlington.",
    "WASHINGTON - Judge blocks Trump bid to shift $1.3bn from housing aid.",
    "WASHINGTON - Court lets Trump halt restoration of Venezuelan TPS.",
    "WASHINGTON - Trump threatens a 'tremendous tax' on data centres abroad.",
    "WASHINGTON - US Agriculture Dept hit by cyberattack this week, NBC says.",
    "ALASKA - Trump team drops Senate lawsuit after Peltola's victory.",
    "WASHINGTON - Trump floats Stephen Miller for the 2028 race, reports say.",
    "YEMEN - Houthis and Saudi-led coalition trade strikes: 71 in 24 hours.",
    "BASRA - Power station fire kills four and injures 35.",
    "GAZA - 350,000 families left homeless, officials say.",
    "BAHRAIN - Government issues an urgent public safety alert.",
    "WEST BANK - Settler guards shoot dead a Palestinian, 42, near Ramallah.",
    "LISBON - Portugal approves a VAT exemption on basic foods.",
    "ROME - Ex-police chief found dead amid a 1992 bombing inquiry.",
    "LONDON - Prince Harry's US visa troubles reported behind UK move.",
    "BEIJING - Xi projects global influence after hosting Trump and Putin.",
    "TAIPEI - Taiwan warns Canada faces the China risks Carney flagged.",
    "PAKISTAN - Suicide car bombing at a checkpoint kills five, injures 13.",
    "SAN SALVADOR - Bukele seeks a third term while fighting gangs in Haiti.",
    "BRAZIL - Bacteria-carrying mosquitoes cut dengue cases by 69%.",
    "SOUTH AFRICA - Phumzile Mlambo-Ngcuka, ex-deputy president, dies at 71.",
    "AUSTRALIA - Study finds genetic clues to why ageing raises cancer risk.",
    "JAPAN - Heavy snow isolates 1,400 people in a north-eastern village.",
    "TECH - Thinking Machines ships Inkling 2 Mini, a 26B model for laptops.",
    "TECH - Cursor tells US House it may drop Chinese open-weight models.",
    "TECH - TSMC pauses shipments as new US chip rules bite.",
    "TECH - Amazon: China-linked hackers used AI agents in an 11-minute hack.",
    "TECH - RIKEN: intruder took 430 Fugaku keys; 4,222 users affected.",
    "SPORT - Leeds stun Chelsea 4-1 at Stamford Bridge.",
    "SPORT - Newcastle fight back to draw 2-2 with Arsenal.",
    "SPORT - England hand All Blacks a record defeat; Fiji edge Italy.",
]

SOURCES = ("Sources: AP, Reuters, AFP, Al Jazeera, CNN, BBC, NYT, WSJ, Dawn, "
           "The Statesman, The Peninsula. All stories happened or were first "
           "reported on 21 November 2026. Disputed claims are attributed.")

STORY_COUNT = 3 + len(SECONDARY) + len(BRIEFS)
REGIONS = 7


# ---------------------------------------------------------------- layout
def build_page():
    w, h = 1024, 1024
    cv = Canvas(w, h, PAPER)
    mx = 24
    cw = w - 2 * mx  # 976

    # masthead
    cv.rect(0, 0, w, 104, NAVY)
    cv.rect(0, 104, w, 4, RED)
    cv.text_centred(w // 2, 14, TITLE, 4, (255, 255, 255), bold=True)
    cv.text(mx, 56, DATE_LINE, 2, (255, 255, 255), bold=True)
    right = "%d STORIES - %d REGIONS - ONE PAGE" % (STORY_COUNT, REGIONS)
    cv.text(w - mx - cv.text_w(right, 2), 56, right, 2, (240, 200, 90),
            bold=True)
    cv.text_centred(w // 2, 84, SUB_LINE, 1, (210, 215, 230))

    # three illustrated leads
    col_w = 317
    gap = 13
    y = 118
    for i, lead in enumerate(LEADS):
        x = mx + i * (col_w + gap)
        ART[lead["art"]](cv, x, y, col_w, 86)
        tag = lead["tag"]
        tw = cv.text_w(tag, 1) + 12
        cv.rect(x, y + 92, tw, 16, RED)
        cv.text(x + 6, y + 95, tag, 1, (255, 255, 255), bold=True)
        used = cv.para(x, y + 114, lead["title"], col_w, 2, INK, 16,
                       bold=True, max_lines=3)
        cv.para(x, y + 114 + used + 4, lead["body"], col_w, 1, INK, 9,
                max_lines=5)
    cv.hline(mx, mx + cw - 1, 330, GREY)

    # nine secondary stories, 3 x 3
    cell_h = 82
    cell_vgap = 8
    y0 = 342
    for idx, story in enumerate(SECONDARY):
        row, col = divmod(idx, 3)
        x = mx + col * (col_w + gap)
        yy = y0 + row * (cell_h + cell_vgap)
        cv.text(x, yy, story["tag"], 1, RED, bold=True)
        used = cv.para(x, yy + 11, story["title"], col_w, 1, INK, 9,
                       bold=True, max_lines=2)
        cv.para(x, yy + 11 + used + 2, story["body"], col_w, 1, INK, 9,
                max_lines=3)
        cv.hline(x, x + col_w - 1, yy + cell_h - 6, LIGHT)

    # by the numbers
    ny = 608
    cv.rect(mx, ny, cw, 58, NAVY)
    cv.text(mx + 16, ny + 24, "BY THE", 1, (240, 200, 90), bold=True)
    cv.text(mx + 16, ny + 35, "NUMBERS", 1, (240, 200, 90), bold=True)
    for i, (num, label) in enumerate(NUMBERS):
        cx = mx + 230 + i * 190
        cv.text_centred(cx, ny + 8, num, 3, (255, 255, 255), bold=True)
        cv.text_centred(cx, ny + 40, label, 1, (210, 215, 230))

    # UTC timeline
    ty = 684
    cv.text(mx, ty, "THE DAY IN UTC", 1, RED, bold=True)
    cv.hline(mx + 16, mx + cw - 16, ty + 26, GREY)
    slot = cw // len(TIMELINE)
    for i, (t, ev) in enumerate(TIMELINE):
        cx = mx + slot * i + slot // 2
        cv.circle(cx, ty + 26, 5, RED)
        cv.text_centred(cx, ty + 8, t, 1, INK, bold=True)
        lines = cv.wrap(ev, slot - 16, 1)
        for j, ln in enumerate(lines[:2]):
            cv.text_centred(cx, ty + 38 + j * 9, ln, 1, INK)

    # briefs
    by = 756
    cv.text(mx, by, "ALSO ON 21 NOVEMBER - %d MORE STORIES"
            % len(BRIEFS), 1, INK, bold=True)
    cv.hline(mx, mx + cw - 1, by + 12, INK)
    brief_y = by + 20
    half = (len(BRIEFS) + 1) // 2
    for col in range(2):
        x = mx + col * (cw // 2 + 12)
        for k in range(half):
            idx = col * half + k
            if idx >= len(BRIEFS):
                break
            line = "%d. %s" % (idx + 1, BRIEFS[idx])
            if cv.text_w(line, 1) > cw // 2:
                raise ValueError("brief too long: %r" % line)
            cv.text(x, brief_y + k * 11, line, 1, INK)

    # footer
    fy = 972
    cv.hline(mx, mx + cw - 1, fy, INK)
    cv.para(mx, fy + 8, SOURCES, cw, 1, GREY, 9, max_lines=2)
    cv.text_centred(w // 2, 1006,
                    "All stories happened or were first reported on "
                    "21 November 2026.",
                    1, INK, bold=True)
    return cv.png()
