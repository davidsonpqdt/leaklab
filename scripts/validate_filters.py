"""
Valida que applyFilterForStat() casa com os numeradores da HUD.
Replica em Python a logica de filtros e a logica de calculo de stats da HUD,
e compara para cada stat o filter_count vs HUD numerator.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDS_PATH = ROOT / "outputs" / "hands.json"

AGGR = {5, 7, 23}


def hero_acts(rounds, street_no, hero_name):
    """Sequencia de acoes do hero numa street, em ordem."""
    acts = (rounds or {}).get(str(street_no)) or (rounds or {}).get(street_no) or []
    out = []
    for a in acts:
        if a.get("player") != hero_name:
            continue
        t = a.get("type")
        if t == 0: out.append("fold")
        elif t == 4: out.append("check")
        elif t == 3: out.append("call")
        elif t in (5, 7): out.append("bet")
        elif t == 23: out.append("raise")
    return out


def match_seq(hero_actions, seq):
    """Igual a checkSequence do JS: suporta `!` exato, single token, multi-step ordenado."""
    exact = seq.endswith("!")
    seq_clean = seq[:-1] if exact else seq
    parts = seq_clean.split("-")
    if not hero_actions:
        return False
    if exact:
        if len(hero_actions) != len(parts):
            return False
        return all(hero_actions[k] == parts[k] for k in range(len(parts)))
    if len(parts) == 1:
        return parts[0] in hero_actions
    i = 0
    for action in hero_actions:
        if action == parts[i]:
            i += 1
        if i >= len(parts):
            return True
    return False


def passes(h, F):
    """Replica passesFilter do JS para os campos relevantes."""
    if F.get("positions") and h.get("pos") not in F["positions"]:
        return False
    if F.get("villain_positions"):
        # vilao = oponente principal (opener / first_aggressor) ou em multiway = qualquer
        vp = h.get("villain_pos")
        if vp not in F["villain_positions"]:
            # tentar via first aggressor pos (BB defenses)
            return False
    if F.get("faced") and h.get("faced") not in F["faced"]:
        return False
    if F.get("actions") and h.get("hero_action") not in F["actions"]:
        return False
    if F.get("is_pfa") is not None and bool(h.get("is_pfa")) != F["is_pfa"]:
        return False
    if F.get("pos_relative") is not None and h.get("pos_relative_to_pfa") != F["pos_relative"]:
        return False
    if F.get("saw_flop") is not None and bool(h.get("saw_flop")) != F["saw_flop"]:
        return False
    if F.get("saw_turn") is not None and bool(h.get("saw_turn")) != F["saw_turn"]:
        return False
    if F.get("saw_river") is not None and bool(h.get("saw_river")) != F["saw_river"]:
        return False
    if F.get("n_to_flop_min") is not None and (h.get("n_to_flop") or 0) < F["n_to_flop_min"]:
        return False
    if F.get("n_to_flop_max") is not None and (h.get("n_to_flop") or 0) > F["n_to_flop_max"]:
        return False
    if F.get("allin_street") and h.get("allin_street") not in F["allin_street"]:
        return False
    rounds = h.get("rounds") or {}
    hero_n = h.get("hero_name")
    for st_key, st_no in [("flop_seq", 2), ("turn_seq", 3), ("river_seq", 4)]:
        seq_set = F.get(st_key)
        if not seq_set:
            continue
        ha = hero_acts(rounds, st_no, hero_n)
        if not any(match_seq(ha, s) for s in seq_set):
            return False
    return True


def make_F():
    return {
        "positions": set(), "villain_positions": set(), "faced": set(),
        "actions": set(), "flop_seq": set(), "turn_seq": set(), "river_seq": set(),
        "is_pfa": None, "pos_relative": None, "saw_flop": None, "saw_turn": None, "saw_river": None,
        "n_to_flop_min": None, "n_to_flop_max": None, "allin_street": set(),
    }


def filter_for(stat):
    F = make_F()
    if stat == "rfi_EP":
        F["positions"].add("EP"); F["faced"].add("unopened"); F["actions"].add("raise")
    elif stat == "rfi_BTN":
        F["positions"].add("BTN"); F["faced"].add("unopened"); F["actions"].add("raise")
    elif stat == "cbet_oop":
        F["is_pfa"] = True; F["saw_flop"] = True; F["flop_seq"].add("bet"); F["positions"].add("SB")
        F["n_to_flop_min"] = 2; F["n_to_flop_max"] = 2
    elif stat == "check_raise":
        F["saw_flop"] = True; F["flop_seq"].add("check-raise")
    elif stat == "river_bet":
        F["saw_river"] = True; F["river_seq"].add("bet")
    elif stat == "bb_xf":
        F["positions"].add("BB"); F["faced"].add("raised"); F["actions"].add("call")
        F["saw_flop"] = True; F["flop_seq"].add("check-fold")
    elif stat == "prob_turn":
        F["positions"].add("BB"); F["faced"].add("raised"); F["actions"].add("call")
        F["saw_turn"] = True; F["flop_seq"].add("check!"); F["turn_seq"].add("bet")
    return F


def hud_compute(hands):
    """Recalcula HUD numerador e denominador para os stats em teste."""
    out = {}
    rfi_ch = {"EP": 0, "BTN": 0}; rfi_did = {"EP": 0, "BTN": 0}
    cbet_oop_ch = 0; cbet_oop_did = 0
    cr_ch = 0; cr_did = 0
    river_bet_ch = 0; river_bet_did = 0
    bb_xf_ch = 0; bb_xf_did = 0
    prob_turn_ch = 0; prob_turn_did = 0

    for h in hands:
        pos = h.get("pos")
        rounds = h.get("rounds") or {}
        hero_n = h.get("hero_name")
        # RFI denom: hero EP/BTN, faced unopened
        if h.get("faced") == "unopened" and pos in ("EP", "BTN"):
            rfi_ch[pos] += 1
            if h.get("hero_action") == "raise":
                rfi_did[pos] += 1
        # cbet_oop denom: hero is PFA, SB, saw_flop, HU vs 1 villain (flopParticipants size = 1)
        if h.get("is_pfa") and pos == "SB" and h.get("saw_flop"):
            flop = (rounds.get("2") or rounds.get(2) or [])
            participants = {a.get("player") for a in flop if a.get("player") != hero_n}
            if len(participants) == 1:
                cbet_oop_ch += 1
                if h.get("cbet_flop"):
                    cbet_oop_did += 1
        # check_raise denom: hero OOP and checked flop
        if h.get("saw_flop"):
            flop = (rounds.get("2") or rounds.get(2) or [])
            hero_checked = False; hero_raised = False
            for a in flop:
                if a.get("player") != hero_n:
                    continue
                if a.get("type") == 4: hero_checked = True
                elif hero_checked and a.get("type") in AGGR: hero_raised = True; break
            hero_oop = h.get("pos_relative_to_pfa") == "oop" or (h.get("is_pfa") and pos in ("SB", "BB"))
            if hero_oop and hero_checked:
                cr_ch += 1
                if hero_raised: cr_did += 1
        # river_bet denom: saw_river, hero first-action with no pending bet
        if h.get("saw_river"):
            river = (rounds.get("4") or rounds.get(4) or [])
            pending = False
            for a in river:
                if a.get("player") == hero_n:
                    if not pending:
                        river_bet_ch += 1
                        if a.get("type") in AGGR: river_bet_did += 1
                    break
                if a.get("type") in AGGR: pending = True
        # bb_xf denom: BB defended PF, opener cbet flop, BB responded
        if pos == "BB" and h.get("faced") == "raised" and h.get("hero_action") == "call" and h.get("saw_flop") and h.get("first_aggressor"):
            opener = h.get("first_aggressor")
            flop = (rounds.get("2") or rounds.get(2) or [])
            opener_cbet = False
            for a in flop:
                if a.get("player") == opener and a.get("type") in AGGR:
                    opener_cbet = True; break
                if a.get("player") != opener and a.get("type") in AGGR:
                    break
            if opener_cbet:
                bb_action = None
                for a in flop:
                    if a.get("player") != hero_n: continue
                    if a.get("type") == 4: continue
                    if a.get("type") == 0: bb_action = "fold"; break
                    if a.get("type") == 3: bb_action = "call"; break
                    if a.get("type") in AGGR: bb_action = "raise"; break
                if bb_action == "fold":
                    bb_xf_ch += 1; bb_xf_did += 1
                elif bb_action in ("call", "raise"):
                    bb_xf_ch += 1
        # prob_turn denom: BB defended PF, opener checked flop, BB first to act on turn
        if pos == "BB" and h.get("faced") == "raised" and h.get("hero_action") == "call" and h.get("saw_turn") and h.get("first_aggressor"):
            opener = h.get("first_aggressor")
            flop = (rounds.get("2") or rounds.get(2) or [])
            opener_checked_back = not any(a.get("player") == opener and a.get("type") in AGGR for a in flop)
            if opener_checked_back:
                turn = (rounds.get("3") or rounds.get(3) or [])
                for a in turn:
                    if a.get("player") != hero_n:
                        if a.get("player") != opener: continue
                        break
                    prob_turn_ch += 1
                    if a.get("type") in AGGR: prob_turn_did += 1
                    break

    out["rfi_EP"] = (rfi_did["EP"], rfi_ch["EP"])
    out["rfi_BTN"] = (rfi_did["BTN"], rfi_ch["BTN"])
    out["cbet_oop"] = (cbet_oop_did, cbet_oop_ch)
    out["check_raise"] = (cr_did, cr_ch)
    out["river_bet"] = (river_bet_did, river_bet_ch)
    out["bb_xf"] = (bb_xf_did, bb_xf_ch)
    out["prob_turn"] = (prob_turn_did, prob_turn_ch)
    return out


def main():
    print(f"Lendo {HANDS_PATH} ...", file=sys.stderr)
    with open(HANDS_PATH, encoding="utf-8") as f:
        hands = json.load(f)
    print(f"  {len(hands)} maos carregadas", file=sys.stderr)

    hud = hud_compute(hands)

    stats = ["rfi_EP", "rfi_BTN", "cbet_oop", "check_raise", "river_bet", "bb_xf", "prob_turn"]
    print(f"\n{'STAT':<14} {'FILTER':>8} {'HUD_NUM':>8} {'HUD_DEN':>8} {'HUD%':>7} {'FLT%':>7}  STATUS")
    print("-" * 70)
    for stat in stats:
        F = filter_for(stat)
        n_filter = sum(1 for h in hands if passes(h, F))
        num, den = hud[stat]
        hud_pct = (num * 100.0 / den) if den else 0
        flt_pct = (n_filter * 100.0 / den) if den else 0
        diff = abs(flt_pct - hud_pct)
        status = "OK" if diff < 0.5 else f"DIFF ({diff:.1f}%)"
        print(f"{stat:<14} {n_filter:>8} {num:>8} {den:>8} {hud_pct:>6.1f}% {flt_pct:>6.1f}%  {status}")


if __name__ == "__main__":
    main()
