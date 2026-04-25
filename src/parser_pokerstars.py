"""Parser de hand histories do PokerStars (formato texto plano).

Converte pra mesmo dict shape do parser iPoker, pra app usar igual.

Uso:
    python parser_pokerstars.py /pasta/com/txts -o hands.json

Formato PokerStars (exemplo):
    PokerStars Hand #123456789: Tournament #987654321, $5.00+$0.50 USD Hold'em No Limit -
    Level III (50/100) - 2026/04/01 12:34:56 ET
    Table '987654321 5' 9-max Seat #3 is the button
    Seat 1: Player1 (5000 in chips)
    ...
    Player3: posts small blind 50
    Player4: posts big blind 100
    *** HOLE CARDS ***
    Dealt to Hero [Ah Kd]
    Player5: folds
    Player6: raises 200 to 300
    ...
    *** FLOP *** [Kh 7d 2c]
    ...
"""
from __future__ import annotations
import os, re, glob, json, argparse
from typing import Iterator, Optional

# Card mapping pra formato comum (igual iPoker)
SUIT_MAP = {"h": "H", "d": "D", "c": "C", "s": "S"}
RANK_MAP = {"2":"2","3":"3","4":"4","5":"5","6":"6","7":"7","8":"8","9":"9",
            "T":"10","J":"J","Q":"Q","K":"K","A":"A"}

# Action types alinhados com iPoker
ACT_FOLD, ACT_SB, ACT_BB, ACT_CALL, ACT_CHECK = 0, 1, 2, 3, 4
ACT_BET, ACT_ALLIN, ACT_ANTE, ACT_RAISE = 5, 7, 15, 23

POSITIONS = ["EP", "MP", "HJ", "CO", "BTN", "SB", "BB"]


def card_to_ipoker(c: str) -> str:
    """'Ah' -> 'HA', 'Td' -> 'D10'."""
    if not c or len(c) != 2: return ""
    suit = SUIT_MAP.get(c[1].lower(), "")
    rank = RANK_MAP.get(c[0].upper(), c[0])
    return suit + rank


def parse_cards(s: str) -> str:
    """'Ah Kd' -> 'HA DK'."""
    return " ".join(card_to_ipoker(c.strip()) for c in s.replace(",", " ").split() if c.strip())


def position_label(seats: list[int], hero_seat: int, btn_seat: int) -> Optional[str]:
    if hero_seat not in seats or btn_seat not in seats:
        return None
    btn_idx = seats.index(btn_seat)
    rotated = seats[btn_idx:] + seats[:btn_idx]
    h = rotated.index(hero_seat); n = len(rotated)
    if n == 2: return "BTN" if h == 0 else "BB"
    if h == 0: return "BTN"
    if h == 1: return "SB"
    if h == 2: return "BB"
    pf_pos = h - 2; n_pf = n - 3
    if pf_pos == n_pf: return "CO"
    if pf_pos == n_pf - 1: return "HJ"
    if pf_pos == n_pf - 2: return "MP"
    return "EP"


def parse_hand_text(text: str) -> Optional[dict]:
    """Parse 1 mao do PokerStars text format."""
    lines = text.strip().split("\n")
    if not lines: return None

    # Header: "PokerStars Hand #X: Tournament #Y, BUYIN GAMETYPE"
    m = re.match(r"PokerStars (?:Hand|Game) #(\d+):.*?Tournament #(\d+)?,?\s*([^-]+)?", lines[0])
    if not m: return None
    gamecode = m.group(1)
    tournament_code = m.group(2) or ""
    buyin_part = (m.group(3) or "").strip()

    # Table info: "Table 'X 5' 9-max Seat #3 is the button"
    table_m = re.search(r"Table '([^']+)' (\d+)-max Seat #(\d+) is the button", text)
    table_size = int(table_m.group(2)) if table_m else 0
    btn_seat = int(table_m.group(3)) if table_m else 0
    table_name = table_m.group(1) if table_m else ""

    # Players
    players = []
    for m in re.finditer(r"Seat (\d+): (\S+) \(([\d,]+) in chips\)", text):
        seat = int(m.group(1))
        name = m.group(2)
        chips = int(m.group(3).replace(",", ""))
        players.append({"seat": seat, "name": name, "chips": chips,
                        "dealer": (seat == btn_seat), "win": 0, "bet": 0, "muck": "1"})
    if not players: return None
    seats = sorted(p["seat"] for p in players)

    # Antes/Blinds
    ante_amount = 0; sb_amount = 0; bb_amount = 0
    rounds = {0: [], 1: [], 2: [], 3: [], 4: []}
    action_no = 1

    for line in lines:
        m = re.match(r"(\S+): posts the ante (\d+)", line)
        if m:
            sum_v = int(m.group(2))
            ante_amount = max(ante_amount, sum_v)
            rounds[0].append({"no": action_no, "player": m.group(1), "type": ACT_ANTE, "sum": sum_v})
            action_no += 1
            continue
        m = re.match(r"(\S+): posts small blind (\d+)", line)
        if m:
            sb_amount = int(m.group(2))
            rounds[0].append({"no": action_no, "player": m.group(1), "type": ACT_SB, "sum": sb_amount})
            action_no += 1
            continue
        m = re.match(r"(\S+): posts big blind (\d+)", line)
        if m:
            bb_amount = int(m.group(2))
            rounds[0].append({"no": action_no, "player": m.group(1), "type": ACT_BB, "sum": bb_amount})
            action_no += 1
            continue

    if bb_amount <= 0: return None

    # Hero detection: "Dealt to NAME [cards]"
    hero_m = re.search(r"Dealt to (\S+) \[([^\]]+)\]", text)
    if not hero_m: return None
    hero = hero_m.group(1)
    hero_cards_raw = parse_cards(hero_m.group(2))
    hero_player = next((p for p in players if p["name"] == hero), None)
    if not hero_player: return None
    hero_seat = hero_player["seat"]
    hero_chips = hero_player["chips"]

    pos = position_label(seats, hero_seat, btn_seat)
    if pos is None: return None

    # Streets parsing
    sections = re.split(r"\*\*\* (HOLE CARDS|FLOP|TURN|RIVER|SHOW DOWN|SUMMARY) \*\*\*", text)
    # sections[0] = pre header, sections[1] = "HOLE CARDS", sections[2] = preflop content, sections[3] = "FLOP", ...
    section_map = {}
    for i in range(1, len(sections), 2):
        section_map[sections[i]] = sections[i+1] if i+1 < len(sections) else ""

    board_cards = {}
    # Parse street content into rounds
    street_to_round = {"HOLE CARDS": 1, "FLOP": 2, "TURN": 3, "RIVER": 4}
    for street_name, round_no in street_to_round.items():
        content = section_map.get(street_name, "")
        if not content: continue
        # Board cards
        if street_name == "FLOP":
            m = re.search(r"\*\*\* FLOP \*\*\* \[([^\]]+)\]", text)
            if m: board_cards[2] = parse_cards(m.group(1))
        elif street_name == "TURN":
            m = re.search(r"\*\*\* TURN \*\*\* \[[^\]]+\] \[(\S+)\]", text)
            if m: board_cards[3] = card_to_ipoker(m.group(1))
        elif street_name == "RIVER":
            m = re.search(r"\*\*\* RIVER \*\*\* \[[^\]]+\] \[(\S+)\]", text)
            if m: board_cards[4] = card_to_ipoker(m.group(1))
        # Actions
        for line in content.split("\n"):
            line = line.strip()
            if not line: continue
            # Fold
            m = re.match(r"(\S+): folds", line)
            if m:
                rounds[round_no].append({"no": action_no, "player": m.group(1), "type": ACT_FOLD, "sum": 0})
                action_no += 1; continue
            # Check
            m = re.match(r"(\S+): checks", line)
            if m:
                rounds[round_no].append({"no": action_no, "player": m.group(1), "type": ACT_CHECK, "sum": 0})
                action_no += 1; continue
            # Call N
            m = re.match(r"(\S+): calls (\d+)(?:\s+and is all-in)?", line)
            if m:
                is_allin = "all-in" in line
                rounds[round_no].append({"no": action_no, "player": m.group(1),
                                          "type": ACT_ALLIN if is_allin else ACT_CALL,
                                          "sum": int(m.group(2))})
                action_no += 1; continue
            # Bet N
            m = re.match(r"(\S+): bets (\d+)(?:\s+and is all-in)?", line)
            if m:
                is_allin = "all-in" in line
                rounds[round_no].append({"no": action_no, "player": m.group(1),
                                          "type": ACT_ALLIN if is_allin else ACT_BET,
                                          "sum": int(m.group(2))})
                action_no += 1; continue
            # Raise N to M
            m = re.match(r"(\S+): raises (\d+) to (\d+)(?:\s+and is all-in)?", line)
            if m:
                is_allin = "all-in" in line
                rounds[round_no].append({"no": action_no, "player": m.group(1),
                                          "type": ACT_ALLIN if is_allin else ACT_RAISE,
                                          "sum": int(m.group(3))})
                action_no += 1; continue

    # Hero cards in pocket via Hole Cards section already captured

    # Win/bet parsing from Summary
    summary = section_map.get("SUMMARY", "")
    for line in summary.split("\n"):
        m = re.match(r"Seat \d+: (\S+) (?:\(button\) |\(small blind\) |\(big blind\) )?(?:showed|mucked|collected|folded)", line)
        if not m: continue
        name = m.group(1)
        win_m = re.search(r"collected \(([^)]+)\)", line)
        if win_m:
            won = int(win_m.group(1).replace(",", ""))
            for p in players:
                if p["name"] == name:
                    p["win"] += won
                    break

    # bet attribute = sum of all chips player put in
    for p in players:
        for r in rounds.values():
            # Sum max of each player's bets per round (since sum is cumulative)
            max_bet = 0
            for a in r:
                if a["player"] == p["name"]: max_bet = max(max_bet, a["sum"])
            p["bet"] += max_bet

    hero_p = next((p for p in players if p["name"] == hero), None)
    hero_win = hero_p["win"] if hero_p else 0
    hero_bet = hero_p["bet"] if hero_p else 0

    # Pega faced + hero_first_action via pf walk (simplificado)
    pf = rounds.get(1, [])
    AGGRESSIVE = {ACT_BET, ACT_ALLIN, ACT_RAISE}
    prior_raises = 0; prior_callers = 0
    hero_first_action = None; faced = None
    hero_actions_pf = []; hero_faced_pf = []
    first_aggressor = None

    for a in pf:
        if a["type"] in (ACT_SB, ACT_BB, ACT_ANTE): continue
        pl = a["player"]; t = a["type"]
        if pl == hero:
            if prior_raises == 0 and prior_callers == 0: cur_faced = "unopened"
            elif prior_raises == 0 and prior_callers >= 1: cur_faced = "limped"
            elif prior_raises == 1: cur_faced = "raised"
            elif prior_raises == 2: cur_faced = "3bet"
            elif prior_raises == 3: cur_faced = "4bet"
            else: cur_faced = "5bet+"
            if t == ACT_FOLD: cur_action = "fold"
            elif t == ACT_CHECK: cur_action = "check"
            elif t == ACT_CALL: cur_action = "call"
            elif t in AGGRESSIVE: cur_action = "raise"
            else: cur_action = "?"
            hero_actions_pf.append(cur_action); hero_faced_pf.append(cur_faced)
            if hero_first_action is None:
                hero_first_action = cur_action; faced = cur_faced
            if cur_action == "fold": break
            if cur_action == "raise":
                prior_raises += 1
                if first_aggressor is None: first_aggressor = hero
        else:
            if t == ACT_FOLD: continue
            if t in AGGRESSIVE:
                prior_raises += 1
                if first_aggressor is None: first_aggressor = pl
            elif t == ACT_CALL:
                prior_callers += 1

    if hero_first_action is None: return None

    # Hand label
    cards = hero_cards_raw.split()
    if len(cards) != 2: return None
    RANKS_ORDER = ["A","K","Q","J","10","9","8","7","6","5","4","3","2"]
    def parse_c(c):
        return c[0], c[1:]
    s1, r1 = parse_c(cards[0]); s2, r2 = parse_c(cards[1])
    if RANKS_ORDER.index(r1) > RANKS_ORDER.index(r2):
        s1, r1, s2, r2 = s2, r2, s1, r1
    rl1 = "T" if r1 == "10" else r1; rl2 = "T" if r2 == "10" else r2
    if r1 == r2: hand_label = rl1 + rl2
    else: hand_label = rl1 + rl2 + ("s" if s1 == s2 else "o")

    saw_flop = any(a["player"] == hero for a in rounds.get(2, []))
    saw_turn = any(a["player"] == hero for a in rounds.get(3, []))
    saw_river = any(a["player"] == hero for a in rounds.get(4, []))

    villain_pos = None
    if first_aggressor and first_aggressor != hero:
        fa_seat = next((p["seat"] for p in players if p["name"] == first_aggressor), None)
        if fa_seat is not None:
            villain_pos = position_label(seats, fa_seat, btn_seat)

    return {
        "gamecode": gamecode, "n_players": len(players),
        "pos": pos, "villain_pos": villain_pos,
        "first_aggressor": first_aggressor,
        "faced": faced, "hero_action": hero_first_action,
        "hero_actions_pf": hero_actions_pf, "hero_faced_pf": hero_faced_pf,
        "hero_cards_raw": hero_cards_raw, "hero_cards_label": hand_label,
        "stack_bb": round(hero_chips / bb_amount, 2),
        "hero_chips": hero_chips, "bb": bb_amount, "sb": sb_amount, "ante": ante_amount,
        "hero_win": hero_win, "hero_bet": hero_bet,
        "won_bb": round((hero_win - hero_bet) / bb_amount, 2),
        "saw_flop": saw_flop, "saw_turn": saw_turn, "saw_river": saw_river,
        "rounds": rounds, "players": players,
        "hero_seat": hero_seat, "btn_seat": btn_seat,
        "board": board_cards, "villain_cards": {},
        "hero_name": hero, "tournament_name": "", "tournament_code": tournament_code,
        "buyin": buyin_part, "tablesize": str(table_size), "startdate": "",
        "site": "PokerStars",
    }


def iter_hands_in_file(path: str) -> Iterator[dict]:
    """Itera as mãos de um arquivo .txt do PokerStars."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except Exception:
        return
    # Mãos separadas por linha em branco entre headers
    hands_text = re.split(r"\n\n+(?=PokerStars (?:Hand|Game) #)", text)
    fname = os.path.basename(path)
    for ht in hands_text:
        h = parse_hand_text(ht)
        if h is not None:
            h["source_file"] = fname
            h["sessioncode"] = ""
            yield h


def iter_hands_in_folder(folder: str) -> Iterator[dict]:
    for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
        yield from iter_hands_in_file(path)


def main():
    ap = argparse.ArgumentParser(description="Parse PokerStars hand histories (TXT) to JSON.")
    ap.add_argument("folder")
    ap.add_argument("-o", "--output", default="hands_pokerstars.json")
    args = ap.parse_args()
    hands = list(iter_hands_in_folder(args.folder))
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(hands, fh, ensure_ascii=False)
    print(f"Escrito {len(hands)} maos em {args.output} (PokerStars)")


if __name__ == "__main__":
    main()
