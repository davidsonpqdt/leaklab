"""Parser de hand histories iPoker XML.

Le arquivos .xml no formato iPoker e gera um dict por mao com tudo que e
necessario para HUD, range charts e replay de maos.

Uso programatico:
    from parser import iter_hands_in_folder

    for h in iter_hands_in_folder("/caminho/da/pasta"):
        print(h["pos"], h["hero_cards_label"], h["faced"], h["hero_action"])

Uso CLI (exporta todas as maos de uma pasta para JSON):
    python parser.py /caminho/da/pasta --hero Noshovepls -o hands.json

Se --hero nao for passado, o hero e auto-detectado por reg_code == sessioncode.
"""
from __future__ import annotations
import os, glob, json, argparse
from collections import defaultdict
from xml.etree import ElementTree as ET
from typing import Iterator, Optional

# Codigos de tipo de acao no XML iPoker
ACT_FOLD, ACT_SB, ACT_BB, ACT_CALL, ACT_CHECK = 0, 1, 2, 3, 4
ACT_BET, ACT_ALLIN, ACT_ANTE, ACT_RAISE = 5, 7, 15, 23
AGGRESSIVE = {ACT_BET, ACT_ALLIN, ACT_RAISE}

# Ranks do mais alto pro mais baixo. iPoker usa "10" e nao "T".
RANKS = ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"]
RANK_VAL = {r: 14 - i for i, r in enumerate(RANKS)}
RANK_LABEL = {r: ("T" if r == "10" else r) for r in RANKS}


def position_label(seats: list[int], hero_seat: int, btn_seat: int) -> Optional[str]:
    """Retorna a posicao do hero (BTN/SB/BB/CO/HJ/MP/EP) dado o layout dos seats."""
    if hero_seat not in seats or btn_seat not in seats:
        return None
    btn_idx = seats.index(btn_seat)
    rotated = seats[btn_idx:] + seats[:btn_idx]
    h = rotated.index(hero_seat)
    n = len(rotated)
    if n == 2:
        return "BTN" if h == 0 else "BB"
    if h == 0: return "BTN"
    if h == 1: return "SB"
    if h == 2: return "BB"
    pf_pos = h - 2          # 1 = primeiro a agir depois da BB (UTG-ish)
    n_pf = n - 3            # quantos atores preflop apos a BB
    if pf_pos == n_pf: return "CO"
    if pf_pos == n_pf - 1: return "HJ"
    if pf_pos == n_pf - 2: return "MP"
    return "EP"


def parse_cards(s: str):
    """'H10 D8' -> ('10', '8', suited=False).  Rank mais alto primeiro."""
    parts = s.strip().split()
    if len(parts) != 2:
        return None
    parsed = []
    for p in parts:
        if not p:
            return None
        suit = p[0]
        rank = p[1:]
        if rank not in RANK_VAL:
            return None
        parsed.append((suit, rank))
    (s1, r1), (s2, r2) = parsed
    if RANK_VAL[r1] < RANK_VAL[r2]:
        s1, r1, s2, r2 = s2, r2, s1, r1
    return r1, r2, (s1 == s2)


def hand_label(r1: str, r2: str, suited: bool) -> str:
    """Label da matriz, ex.: 'AKs', 'AKo', 'TT'."""
    if r1 == r2:
        return RANK_LABEL[r1] + RANK_LABEL[r2]
    return RANK_LABEL[r1] + RANK_LABEL[r2] + ("s" if suited else "o")


def card_to_compact(card: str) -> str:
    """'H10' -> 'Th'.  Util pro replay."""
    if not card or len(card) < 2:
        return ""
    suit = card[0].lower()  # H/S/C/D -> h/s/c/d
    rank = card[1:]
    return RANK_LABEL.get(rank, rank) + suit


def _int(s: str) -> int:
    try:
        return int(str(s).replace(",", ""))
    except (ValueError, AttributeError, TypeError):
        return 0


def detect_hero_name(root) -> Optional[str]:
    """Auto-detecta o hero pelo reg_code == sessioncode."""
    sessioncode = root.attrib.get("sessioncode", "")
    if not sessioncode:
        return None
    for game in root.findall("game"):
        general = game.find("general")
        if general is None:
            continue
        players = general.find("players")
        if players is None:
            continue
        for p in players.findall("player"):
            if p.attrib.get("reg_code", "") == sessioncode:
                return p.attrib.get("name", "")
    return None


def parse_game(game_elem, hero: str) -> Optional[dict]:
    """Parse de um <game> e retorna o dict da mao (ou None pra pular)."""
    general = game_elem.find("general")
    if general is None:
        return None
    players_node = general.find("players")
    if players_node is None:
        return None

    players = []
    hero_seat = btn_seat = None
    hero_chips = hero_win = hero_bet = 0
    villain_cards: dict[str, str] = {}
    for p in players_node.findall("player"):
        seat = int(p.attrib.get("seat", 0))
        name = p.attrib.get("name", "")
        dealer = p.attrib.get("dealer", "0") == "1"
        chips = _int(p.attrib.get("chips", "0"))
        win = _int(p.attrib.get("win", "0"))
        bet = _int(p.attrib.get("bet", "0"))
        muck = p.attrib.get("muck", "1")
        players.append({
            "seat": seat, "name": name, "chips": chips,
            "dealer": dealer, "win": win, "bet": bet, "muck": muck,
        })
        if name == hero:
            hero_seat = seat; hero_chips = chips; hero_win = win; hero_bet = bet
        if dealer:
            btn_seat = seat
    if hero_seat is None or btn_seat is None or hero_chips <= 0:
        return None

    seats = sorted(p["seat"] for p in players)
    pos = position_label(seats, hero_seat, btn_seat)
    if pos is None:
        return None

    rounds: dict[int, list[dict]] = defaultdict(list)
    hero_cards_raw = None
    bb_amount = 0
    sb_amount = 0
    ante_amount = 0
    board_cards: dict[int, str] = {}  # round -> str de cartas comunitarias
    for r in game_elem.findall("round"):
        rno = int(r.attrib.get("no", "-1"))
        for a in r.findall("action"):
            t = int(a.attrib.get("type", -1))
            sum_v = _int(a.attrib.get("sum", "0"))
            rounds[rno].append({
                "no": int(a.attrib.get("no", 0)),
                "player": a.attrib.get("player", ""),
                "type": t,
                "sum": sum_v,
            })
            if t == ACT_BB and bb_amount == 0:
                bb_amount = sum_v
            elif t == ACT_SB and sb_amount == 0:
                sb_amount = sum_v
            elif t == ACT_ANTE:
                ante_amount = max(ante_amount, sum_v)
        for c in r.findall("cards"):
            ctype = c.attrib.get("type", "")
            cplayer = c.attrib.get("player", "")
            text = (c.text or "").strip()
            if ctype == "Pocket":
                if cplayer == hero:
                    hero_cards_raw = text
                elif text and "X" not in text:
                    villain_cards[cplayer] = text
            elif ctype in ("Flop", "Turn", "River"):
                board_cards[rno] = text

    if not hero_cards_raw or bb_amount <= 0:
        return None
    cards = parse_cards(hero_cards_raw)
    if not cards:
        return None
    r1, r2, suited = cards
    stack_bb = hero_chips / bb_amount

    # Sequencia preflop: descobre a 1a situacao do hero, depois continua
    # pra capturar 4bets/calls subsequentes.
    pf = rounds.get(1, [])
    prior_raises = prior_callers = 0
    first_aggressor = None
    hero_acted = False
    hero_first_action = None
    faced = None
    hero_actions_pf: list[str] = []      # sequencia completa do hero (ex: ["raise", "raise"])
    hero_faced_pf: list[str] = []        # situacao em cada decisao (ex: ["unopened", "3bet"])

    for a in pf:
        t = a["type"]; pl = a["player"]
        if t in (ACT_SB, ACT_BB, ACT_ANTE):
            continue
        if pl == hero:
            # decide a situacao que o hero esta enfrentando agora
            if prior_raises == 0 and prior_callers == 0:
                cur_faced = "unopened"
            elif prior_raises == 0 and prior_callers >= 1:
                cur_faced = "limped"
            elif prior_raises == 1:
                cur_faced = "raised"
            elif prior_raises == 2:
                cur_faced = "3bet"
            elif prior_raises == 3:
                cur_faced = "4bet"
            else:
                cur_faced = "5bet+"
            if t == ACT_FOLD: cur_action = "fold"
            elif t == ACT_CHECK: cur_action = "check"
            elif t == ACT_CALL: cur_action = "call"
            elif t in AGGRESSIVE: cur_action = "raise"
            else: cur_action = "?"
            hero_actions_pf.append(cur_action)
            hero_faced_pf.append(cur_faced)
            if not hero_acted:
                hero_acted = True
                faced = cur_faced
                hero_first_action = cur_action
            if cur_action == "fold":
                # hero foldou: nao age mais nesta mao
                break
            if cur_action == "raise":
                prior_raises += 1
                if first_aggressor is None:
                    first_aggressor = hero
            # Se foi all-in, hero nao tem mais chips pra agir, mas o loop continua
            # rastreando vilaos. Nao breaka pra capturar acoes posteriores corretamente.
        else:
            if t == ACT_FOLD:
                continue
            if t in AGGRESSIVE:
                prior_raises += 1
                if first_aggressor is None:
                    first_aggressor = pl
            elif t == ACT_CALL:
                prior_callers += 1

    if not hero_acted:
        return None  # walked the BB ou foi dealt out

    # 4bet face: o hero abriu, vilao 3-betou, hero respondeu?
    faced_3bet_after_open = False
    hero_4bet_response = None  # "fold" / "call" / "raise" (4bet)
    if len(hero_actions_pf) >= 2 and hero_actions_pf[0] == "raise":
        if hero_faced_pf[1] == "3bet":
            faced_3bet_after_open = True
            hero_4bet_response = hero_actions_pf[1]

    villain_pos = None
    if first_aggressor and first_aggressor != hero:
        fa_seat = next((p["seat"] for p in players if p["name"] == first_aggressor), None)
        if fa_seat is not None:
            villain_pos = position_label(seats, fa_seat, btn_seat)

    # PFA (preflop aggressor) = ultimo raiser do preflop entre os que continuam ate o flop
    pfa_player = None
    last_raiser = None
    folded_pf: set[str] = set()
    for a in pf:
        t = a["type"]
        if t in (ACT_SB, ACT_BB, ACT_ANTE):
            continue
        if t == ACT_FOLD:
            folded_pf.add(a["player"])
        elif t in AGGRESSIVE:
            last_raiser = a["player"]
    if last_raiser and last_raiser not in folded_pf:
        pfa_player = last_raiser

    is_pfa = (pfa_player == hero)
    is_squeeze = (hero_first_action == "raise" and faced == "raised" and prior_callers >= 1
                  if False else  # placeholder
                  (len(hero_actions_pf) > 0 and hero_actions_pf[0] == "raise"
                   and faced == "raised" and any(
                       a["type"] == ACT_CALL and a["player"] != hero
                       for a in pf if a["type"] not in (ACT_SB, ACT_BB, ACT_ANTE)
                   )))
    # versao simples: se faced=raised e teve >=1 caller antes do hero raise
    is_squeeze = False
    if hero_first_action == "raise" and faced == "raised":
        callers_before_hero = 0
        for a in pf:
            if a["player"] == hero:
                break
            t = a["type"]
            if t in (ACT_SB, ACT_BB, ACT_ANTE, ACT_FOLD):
                continue
            if t == ACT_CALL:
                callers_before_hero += 1
        if callers_before_hero >= 1:
            is_squeeze = True

    # Posicao relativa ao PFA (importante pra cbet IP/OOP, etc.)
    # No postflop, IP = age por ultimo (mais perto do BTN).
    pos_relative_to_pfa = None  # "self" | "ip" | "oop"
    if pfa_player == hero:
        pos_relative_to_pfa = "self"
    elif pfa_player:
        pfa_seat = next((p["seat"] for p in players if p["name"] == pfa_player), None)
        if pfa_seat is not None:
            # postflop: ordem comeca no SB e vai aumentando. Quem age depois e IP.
            sb_seat = None
            btn_idx = seats.index(btn_seat)
            rotated = seats[btn_idx:] + seats[:btn_idx]
            if len(rotated) > 1:
                sb_seat = rotated[1] if len(rotated) > 2 else rotated[1]
            # heuristica: o jogador com seat "depois" do PFA na ordem postflop e IP do PFA
            # ordem postflop: SB, BB, EP, MP, HJ, CO, BTN
            postflop_order = rotated[1:] + [rotated[0]]  # SB, BB, ..., BTN
            try:
                hero_idx_pf = postflop_order.index(hero_seat)
                pfa_idx_pf = postflop_order.index(pfa_seat)
                pos_relative_to_pfa = "ip" if hero_idx_pf > pfa_idx_pf else "oop"
            except ValueError:
                pass

    # All-in detectado em qualquer street?
    allin_street = None
    for s in (1, 2, 3, 4):
        for a in rounds.get(s, []):
            if a["type"] == ACT_ALLIN:
                allin_street = s; break
        if allin_street:
            break

    # Postflop participation
    def acted_on(s: int) -> bool:
        return any(a["player"] == hero for a in rounds.get(s, []))
    saw_flop = any(acted_on(s) for s in (2, 3, 4))
    saw_turn = any(acted_on(s) for s in (3, 4))
    saw_river = acted_on(4)

    # Quantos jogadores foram pro flop (nao foldaram preflop)
    n_to_flop = len(players) - len(folded_pf)

    # Blind vs Blind: so SB e BB foram pro flop, sem walks
    is_bvb = (saw_flop and n_to_flop == 2 and pos in ("SB", "BB")
              and villain_pos in ("SB", "BB", None))

    # Acoes do hero por street (sequencia)
    hero_actions_by_street: dict[int, list[str]] = {}
    for s in (2, 3, 4):
        seq: list[str] = []
        for a in rounds.get(s, []):
            if a["player"] != hero:
                continue
            t = a["type"]
            if t == ACT_FOLD: seq.append("fold")
            elif t == ACT_CHECK: seq.append("check")
            elif t == ACT_CALL: seq.append("call")
            elif t == ACT_BET: seq.append("bet")
            elif t == ACT_RAISE: seq.append("raise")
            elif t == ACT_ALLIN: seq.append("allin")
        hero_actions_by_street[s] = seq

    # Hero foi PFA e fez cbet em cada street?
    cbet_flop = False
    cbet_turn = False
    cbet_river = False
    if is_pfa and saw_flop:
        # cbet flop = primeira aposta do hero no flop antes de qualquer outra aposta
        flop_acts = rounds.get(2, [])
        first_bet_player = None
        for a in flop_acts:
            if a["type"] in (ACT_BET, ACT_RAISE, ACT_ALLIN):
                first_bet_player = a["player"]; break
        cbet_flop = (first_bet_player == hero)
        if cbet_flop and saw_turn:
            turn_acts = rounds.get(3, [])
            first_bet_turn = None
            for a in turn_acts:
                if a["type"] in (ACT_BET, ACT_RAISE, ACT_ALLIN):
                    first_bet_turn = a["player"]; break
            cbet_turn = (first_bet_turn == hero)
            if cbet_turn and saw_river:
                river_acts = rounds.get(4, [])
                first_bet_river = None
                for a in river_acts:
                    if a["type"] in (ACT_BET, ACT_RAISE, ACT_ALLIN):
                        first_bet_river = a["player"]; break
                cbet_river = (first_bet_river == hero)

    # WW $D / WTSD
    on_river = acted_on(4)
    folded_river = any(a["player"] == hero and a["type"] == ACT_FOLD for a in rounds.get(4, []))
    others_on_river = {a["player"] for a in rounds.get(4, [])
                        if a["player"] != hero and a["type"] != ACT_FOLD}
    went_to_sd = bool(on_river and not folded_river and others_on_river)

    return {
        "gamecode": game_elem.attrib.get("gamecode", ""),
        "n_players": len(players),
        "n_to_flop": n_to_flop,
        "pos": pos,
        "villain_pos": villain_pos,
        "first_aggressor": first_aggressor,
        "pfa_player": pfa_player,
        "is_pfa": is_pfa,
        "is_squeeze": is_squeeze,
        "pos_relative_to_pfa": pos_relative_to_pfa,
        "is_bvb": is_bvb,
        "faced": faced,
        "hero_action": hero_first_action,
        "hero_actions_pf": hero_actions_pf,
        "hero_faced_pf": hero_faced_pf,
        "hero_actions_by_street": hero_actions_by_street,
        "faced_3bet_after_open": faced_3bet_after_open,
        "hero_4bet_response": hero_4bet_response,
        "hero_cards_raw": hero_cards_raw,
        "hero_cards_label": hand_label(r1, r2, suited),
        "stack_bb": round(stack_bb, 2),
        "hero_chips": hero_chips,
        "bb": bb_amount,
        "sb": sb_amount,
        "ante": ante_amount,
        "hero_win": hero_win,
        "hero_bet": hero_bet,
        "won_bb": round((hero_win - hero_bet) / bb_amount, 2),
        "saw_flop": saw_flop,
        "saw_turn": saw_turn,
        "saw_river": saw_river,
        "went_to_sd": went_to_sd,
        "allin_street": allin_street,
        "cbet_flop": cbet_flop,
        "cbet_turn": cbet_turn,
        "cbet_river": cbet_river,
        "rounds": dict(rounds),
        "players": players,
        "hero_seat": hero_seat,
        "btn_seat": btn_seat,
        "board": board_cards,
        "villain_cards": villain_cards,
    }


def iter_hands_in_file(path: str, hero: Optional[str] = None) -> Iterator[dict]:
    """Itera as maos de um arquivo. Se hero=None, auto-detecta."""
    try:
        tree = ET.parse(path)
    except Exception:
        return
    root = tree.getroot()
    sessioncode = root.attrib.get("sessioncode", "")
    use_hero = hero or detect_hero_name(root)
    if not use_hero:
        return
    fname = os.path.basename(path)
    # metadados do torneio
    g = root.find("general")
    tname = (g.findtext("tournamentname") or "") if g is not None else ""
    tcode = (g.findtext("tournamentcode") or "") if g is not None else ""
    buyin = (g.findtext("buyin") or "") if g is not None else ""
    tablesize = (g.findtext("tablesize") or "") if g is not None else ""
    startdate = (g.findtext("startdate") or "") if g is not None else ""
    for game in root.findall("game"):
        h = parse_game(game, use_hero)
        if h is not None:
            h["source_file"] = fname
            h["sessioncode"] = sessioncode
            h["hero_name"] = use_hero
            h["tournament_name"] = tname
            h["tournament_code"] = tcode
            h["buyin"] = buyin
            h["tablesize"] = tablesize
            h["startdate"] = startdate
            game_general = game.find("general")
            if game_general is not None:
                h["hand_startdate"] = game_general.findtext("startdate") or ""
            yield h


def iter_hands_in_folder(folder: str, hero: Optional[str] = None) -> Iterator[dict]:
    for path in sorted(glob.glob(os.path.join(folder, "*.xml"))):
        yield from iter_hands_in_file(path, hero)


def main():
    ap = argparse.ArgumentParser(description="Parse iPoker XML e exporta maos como JSON.")
    ap.add_argument("folder", help="Pasta contendo arquivos .xml")
    ap.add_argument("--hero", default=None, help="Nome do hero (default: auto-detecta por reg_code)")
    ap.add_argument("--output", "-o", default="hands.json", help="Arquivo JSON de saida")
    ap.add_argument("--slim", action="store_true", help="Omite rounds/players (JSON menor, sem replay)")
    args = ap.parse_args()

    hands = list(iter_hands_in_folder(args.folder, args.hero))
    if args.slim:
        for h in hands:
            h.pop("rounds", None)
            h.pop("players", None)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(hands, fh, ensure_ascii=False)
    heros = sorted({h.get("hero_name", "") for h in hands})
    print(f"Escrito {len(hands)} maos em {args.output}  (hero(s): {', '.join(heros) or '?'})")


if __name__ == "__main__":
    main()
