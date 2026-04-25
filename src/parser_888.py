"""Parser de hand histories do 888poker (formato texto, .pt incluido).

Converte pra mesmo dict shape do parser iPoker.

Uso:
    python parser_888.py /pasta/com/txts -o hands.json [--slim] [--hero NAME]

Formato 888 (exemplo):
    ***** 888.pt Hand History for Game 632679447 *****
    200/400 Blinds No Limit Holdem - *** 22 04 2026 18:50:54
    Tournament #289763590 4,95 € + 0,55 € - Table #3 8 Max (Real Money)
    Seat 1 is the button
    Total number of players : 8
    Seat 1: Aton1978 ( 4.170 )
    ...
    speedybolt posts ante [50]
    pikilavi14 posts small blind [200]
    speedybolt posts big blind [400]
    ** Dealing down cards **
    Dealt to NAME [ Kd, Jh ]
    NAME raises [800]
    ...
    ** Dealing flop ** [ Qh, 8d, Th ]
    ...
    ** Dealing turn ** [ 3h ]
    ** Dealing river ** [ 3s ]
    ** Summary **
    NAME shows [ ... ]
    NAME collected [ amount ]

Numeros: "10.382" usa "." como separador de milhar (formato europeu).
"""
from __future__ import annotations
import os, re, glob, json, argparse
from typing import Iterator, Optional

SUIT_MAP = {"h": "H", "d": "D", "c": "C", "s": "S"}
RANK_MAP = {"2":"2","3":"3","4":"4","5":"5","6":"6","7":"7","8":"8","9":"9",
            "T":"10","J":"J","Q":"Q","K":"K","A":"A"}

ACT_FOLD, ACT_SB, ACT_BB, ACT_CALL, ACT_CHECK = 0, 1, 2, 3, 4
ACT_BET, ACT_ALLIN, ACT_ANTE, ACT_RAISE = 5, 7, 15, 23
AGGRESSIVE = {ACT_BET, ACT_ALLIN, ACT_RAISE}


def card_to_ipoker(c: str) -> str:
    """'Kd' -> 'DK'. 888 usa 'T' pra 10."""
    c = c.strip()
    if not c or len(c) != 2: return ""
    suit = SUIT_MAP.get(c[1].lower(), "")
    rank = RANK_MAP.get(c[0].upper(), c[0])
    return suit + rank


def parse_cards_888(s: str) -> str:
    """'Kd, Jh' -> 'DK HJ'."""
    return " ".join(card_to_ipoker(c.strip()) for c in s.replace(",", " ").split() if c.strip())


def num_888(s: str) -> int:
    """'10.382' -> 10382 (dot=thousand sep). '4,95' (raro) -> trata como dot=int."""
    if not s: return 0
    # Remove qualquer naipe nao-digito (888 usa . como separador de milhar)
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else 0


def position_label(seats, hero_seat, btn_seat):
    """Posicao do hero. Suporta 'dead button' (btn em seat vazio)."""
    if hero_seat not in seats: return None
    # Se btn_seat nao tem player (dead button), inclui virtualmente na rotacao
    if btn_seat not in seats:
        all_seats = sorted(set(seats + [btn_seat]))
        btn_idx = all_seats.index(btn_seat)
        rotated_with_dead = all_seats[btn_idx:] + all_seats[:btn_idx]
        # Rota: BTN(dead), proximos sao SB, BB, ...
        # Como BTN ta vazio, hero pega posicao baseado no idx_real
        if hero_seat == btn_seat: return None  # nao deveria acontecer
        h = rotated_with_dead.index(hero_seat)
        n = len(rotated_with_dead)
        if n == 2: return "BB"  # so hero e dead btn (impossivel mas seguro)
        if h == 1: return "SB"
        if h == 2: return "BB"
        pf_pos = h - 2; n_pf = n - 3
        if pf_pos == n_pf: return "CO"
        if pf_pos == n_pf - 1: return "HJ"
        if pf_pos == n_pf - 2: return "MP"
        return "EP"
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


def parse_hand_text(text: str, hero_filter: Optional[str] = None) -> Optional[dict]:
    lines = text.strip().split("\n")
    if not lines: return None

    # Header: "***** 888.pt Hand History for Game 632679447 *****"
    m = re.match(r"\*+\s*([\w.]+)\s*Hand History for Game (\d+)", lines[0])
    if not m: return None
    site = m.group(1)
    gamecode = m.group(2)

    # Blinds line: "200/400 Blinds No Limit Holdem - *** date"
    blinds_line = lines[1] if len(lines) > 1 else ""
    bm = re.match(r"([\d.]+)/([\d.]+) Blinds", blinds_line)
    if not bm: return None
    sb_amount = num_888(bm.group(1))
    bb_amount = num_888(bm.group(2))

    # Date
    date_m = re.search(r"\*\*\*\s+(\d+\s+\d+\s+\d+\s+\d+:\d+:\d+)", blinds_line)
    startdate = date_m.group(1) if date_m else ""

    # Tournament info: "Tournament #N BUYIN - Table #X N Max"
    tour_line = lines[2] if len(lines) > 2 else ""
    tcode_m = re.match(r"Tournament #(\d+)\s+(.+?)\s*-\s*Table\s+#(\S+)\s+(\d+)\s+Max", tour_line)
    tournament_code = tcode_m.group(1) if tcode_m else ""
    buyin = (tcode_m.group(2) or "").strip() if tcode_m else ""
    table_size = int(tcode_m.group(4)) if tcode_m else 0

    # Button seat: "Seat N is the button"
    btn_seat = 0
    for line in lines[:8]:
        bm = re.match(r"Seat (\d+) is the button", line)
        if bm: btn_seat = int(bm.group(1)); break

    # Players
    players = []
    for m in re.finditer(r"Seat (\d+):\s*(\S+)\s*\(\s*([\d.]+)\s*\)", text):
        seat = int(m.group(1))
        name = m.group(2)
        chips = num_888(m.group(3))
        players.append({"seat": seat, "name": name, "chips": chips,
                        "dealer": (seat == btn_seat), "win": 0, "bet": 0, "muck": "1"})
    if not players: return None
    seats = sorted(p["seat"] for p in players)

    # Antes/Blinds
    ante_amount = 0
    rounds = {0: [], 1: [], 2: [], 3: [], 4: []}
    action_no = 1

    # Encontra todas as poses iniciais
    for line in lines:
        m = re.match(r"(\S+)\s+posts ante\s*\[(\d+)\]", line)
        if m:
            sum_v = int(m.group(2))
            ante_amount = max(ante_amount, sum_v)
            rounds[0].append({"no": action_no, "player": m.group(1), "type": ACT_ANTE, "sum": sum_v})
            action_no += 1; continue
        m = re.match(r"(\S+)\s+posts small blind\s*\[(\d+)\]", line)
        if m:
            rounds[0].append({"no": action_no, "player": m.group(1), "type": ACT_SB, "sum": int(m.group(2))})
            action_no += 1; continue
        m = re.match(r"(\S+)\s+posts big blind\s*\[(\d+)\]", line)
        if m:
            rounds[0].append({"no": action_no, "player": m.group(1), "type": ACT_BB, "sum": int(m.group(2))})
            action_no += 1; continue

    if bb_amount <= 0: return None

    # Hero detection
    hero_m = re.search(r"Dealt to (\S+) \[\s*([^\]]+)\s*\]", text)
    if not hero_m: return None
    hero = hero_m.group(1)
    if hero_filter and hero != hero_filter:
        return None
    hero_cards_raw = parse_cards_888(hero_m.group(2))
    hero_player = next((p for p in players if p["name"] == hero), None)
    if not hero_player: return None
    hero_seat = hero_player["seat"]
    hero_chips = hero_player["chips"]

    pos = position_label(seats, hero_seat, btn_seat)
    if pos is None: return None

    # Streets — sao delimitadas por "** Dealing flop **", etc.
    # Vou procurar essas marcas pra dividir.
    flop_m = re.search(r"\*\*\s*Dealing flop\s*\*\*\s*\[\s*([^\]]+)\s*\]", text)
    turn_m = re.search(r"\*\*\s*Dealing turn\s*\*\*\s*\[\s*([^\]]+)\s*\]", text)
    river_m = re.search(r"\*\*\s*Dealing river\s*\*\*\s*\[\s*([^\]]+)\s*\]", text)
    summary_pos = text.find("** Summary **")

    board_cards = {}
    if flop_m: board_cards[2] = parse_cards_888(flop_m.group(1))
    if turn_m: board_cards[3] = card_to_ipoker(turn_m.group(1).strip())
    if river_m: board_cards[4] = card_to_ipoker(river_m.group(1).strip())

    # Pega regions: preflop = entre "Dealt to" e flop_m (ou summary)
    dealt_pos = hero_m.end()
    flop_pos = flop_m.start() if flop_m else (summary_pos if summary_pos >= 0 else len(text))
    turn_pos = turn_m.start() if turn_m else (summary_pos if summary_pos >= 0 else len(text))
    river_pos = river_m.start() if river_m else (summary_pos if summary_pos >= 0 else len(text))
    if summary_pos < 0: summary_pos = len(text)

    preflop_text = text[dealt_pos:flop_pos]
    flop_text = text[flop_pos:turn_pos] if flop_m else ""
    turn_text = text[turn_pos:river_pos] if turn_m else ""
    river_text = text[river_pos:summary_pos] if river_m else ""

    def parse_actions(section_text: str, round_no: int):
        nonlocal action_no
        for line in section_text.split("\n"):
            line = line.strip()
            if not line: continue
            m = re.match(r"(\S+)\s+folds", line)
            if m:
                rounds[round_no].append({"no": action_no, "player": m.group(1), "type": ACT_FOLD, "sum": 0})
                action_no += 1; continue
            m = re.match(r"(\S+)\s+checks", line)
            if m:
                rounds[round_no].append({"no": action_no, "player": m.group(1), "type": ACT_CHECK, "sum": 0})
                action_no += 1; continue
            m = re.match(r"(\S+)\s+calls\s*\[\s*([\d.]+)\s*\]", line)
            if m:
                rounds[round_no].append({"no": action_no, "player": m.group(1), "type": ACT_CALL, "sum": num_888(m.group(2))})
                action_no += 1; continue
            m = re.match(r"(\S+)\s+bets\s*\[\s*([\d.]+)\s*\]", line)
            if m:
                rounds[round_no].append({"no": action_no, "player": m.group(1), "type": ACT_BET, "sum": num_888(m.group(2))})
                action_no += 1; continue
            m = re.match(r"(\S+)\s+raises\s*\[\s*([\d.]+)\s*\]", line)
            if m:
                rounds[round_no].append({"no": action_no, "player": m.group(1), "type": ACT_RAISE, "sum": num_888(m.group(2))})
                action_no += 1; continue
            m = re.match(r"(\S+)\s+goes all-in\s*\[?\s*([\d.]*)\s*\]?", line)
            if m:
                rounds[round_no].append({"no": action_no, "player": m.group(1), "type": ACT_ALLIN, "sum": num_888(m.group(2))})
                action_no += 1; continue

    parse_actions(preflop_text, 1)
    parse_actions(flop_text, 2)
    parse_actions(turn_text, 3)
    parse_actions(river_text, 4)

    # 888 raises são INCREMENTAIS (não cumulativos como iPoker).
    # Calcula bet cumulativo por player na street pra ficar igual ao iPoker
    for street_no in (1, 2, 3, 4):
        per_player = {}  # nome -> total ate agora
        for a in rounds[street_no]:
            pl = a["player"]
            if a["type"] in (ACT_FOLD, ACT_CHECK):
                continue
            if a["type"] == ACT_CALL:
                # 888 call: amount = quanto a mais pra igualar. Total = max + amount
                # Mas pra simplificar, total = bet maximo na rua + algo... vou apenas registrar incrementos
                # e deixar pra app interpretar.
                per_player[pl] = per_player.get(pl, 0) + a["sum"]
                a["sum"] = per_player[pl]
            elif a["type"] in (ACT_BET, ACT_RAISE, ACT_ALLIN):
                # 888 raises [X] = AMOUNT TOTAL na rua (a partir do que vi no exemplo)
                # exemplo: raise [800] depois de BB 400 = total 800 (não cumulativo de bet anterior)
                # Mas check carefully - looking at exemplo:
                # "FavoriteSong raises [800]" — apos BB de 400. Se total=800 ele põe 800 a mais (não 400)
                # Hmm ambíguo. Vou tratar como TOTAL na rua que o player tem.
                per_player[pl] = a["sum"]

    # Antes/Blinds: rounds[0] já está corretos (quantia exata posta)

    # Win parsing from Summary
    summary_text = text[summary_pos:]
    for line in summary_text.split("\n"):
        m = re.search(r"(\S+)\s+collected\s*\[\s*([\d.]+)\s*\]", line)
        if m:
            name = m.group(1); won = num_888(m.group(2))
            for p in players:
                if p["name"] == name:
                    p["win"] += won; break
        # Mucks/shows from summary tambem
        m = re.match(r"(\S+)\s+shows\s*\[\s*([^\]]+)\s*\]", line)
        if m:
            for p in players:
                if p["name"] == m.group(1):
                    p["muck"] = "0"; break

    # bet attribute = total chips committed
    for p in players:
        total_bet = 0
        for r in rounds.values():
            max_bet = 0
            for a in r:
                if a["player"] == p["name"]: max_bet = max(max_bet, a["sum"])
            total_bet += max_bet
        p["bet"] = total_bet

    hero_p = next((p for p in players if p["name"] == hero), None)
    hero_win = hero_p["win"] if hero_p else 0
    hero_bet = hero_p["bet"] if hero_p else 0

    # PFA detect & faced/action
    pf = rounds.get(1, [])
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
    s1, r1 = cards[0][0], cards[0][1:]; s2, r2 = cards[1][0], cards[1][1:]
    if RANKS_ORDER.index(r1) > RANKS_ORDER.index(r2):
        s1, r1, s2, r2 = s2, r2, s1, r1
    rl1 = "T" if r1 == "10" else r1; rl2 = "T" if r2 == "10" else r2
    hand_label = rl1 + rl2 if r1 == r2 else rl1 + rl2 + ("s" if s1 == s2 else "o")

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
        "hero_name": hero, "tournament_name": "",
        "tournament_code": tournament_code, "buyin": buyin,
        "tablesize": str(table_size), "startdate": startdate,
        "site": site, "__dataset": "888",
    }


def iter_hands_in_file(path: str, hero_filter: Optional[str] = None) -> Iterator[dict]:
    """Streaming pra arquivos grandes."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            buffer = []
            for line in fh:
                if line.startswith("*****") and "Hand History for Game" in line and buffer:
                    text = "".join(buffer)
                    h = parse_hand_text(text, hero_filter)
                    if h is not None:
                        h["source_file"] = os.path.basename(path)
                        h["sessioncode"] = ""
                        yield h
                    buffer = [line]
                else:
                    buffer.append(line)
            if buffer:
                text = "".join(buffer)
                h = parse_hand_text(text, hero_filter)
                if h is not None:
                    h["source_file"] = os.path.basename(path)
                    h["sessioncode"] = ""
                    yield h
    except Exception as e:
        print(f"  ! erro em {path}: {e}")
        return


def iter_hands_in_folder(folder: str, hero_filter: Optional[str] = None) -> Iterator[dict]:
    for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
        yield from iter_hands_in_file(path, hero_filter)


def main():
    ap = argparse.ArgumentParser(description="Parse 888poker hand histories (TXT) to JSON.")
    ap.add_argument("path", help="Arquivo ou pasta com .txt")
    ap.add_argument("-o", "--output", default="hands_888.json")
    ap.add_argument("--hero", default=None, help="Filtrar mãos só do nome especificado")
    ap.add_argument("--slim", action="store_true", help="Remove rounds/players (JSON menor, sem replay)")
    args = ap.parse_args()

    # Path pode ser arquivo unico ou pasta
    if os.path.isfile(args.path):
        hands = list(iter_hands_in_file(args.path, args.hero))
    else:
        hands = list(iter_hands_in_folder(args.path, args.hero))

    if args.slim:
        for h in hands:
            h.pop("rounds", None); h.pop("players", None)

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(hands, fh, ensure_ascii=False)
    heros = sorted({h.get("hero_name", "") for h in hands})
    print(f"Escrito {len(hands)} maos em {args.output} (888) (heroes: {', '.join(heros[:5])}{'...' if len(heros)>5 else ''})")


if __name__ == "__main__":
    main()
