"""
Auditoria COMPLETA: replica em Python a logica JS de:
- computeStats() - calculos da HUD
- applyFilterForStat() - filtro de click

Para cada stat:
- Roda computeStats em todas as 99k mãos -> obtem (num, denom, %)
- Roda o filtro click-to-filter -> obtem N hands matching
- Compara N filter vs num HUD: deveriam ser iguais ou muito proximos
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDS_PATH = ROOT / "outputs" / "hands.json"
AGGR = {5, 7, 23}
POSITIONS = ["EP", "MP", "HJ", "CO", "BTN", "SB", "BB"]


def hero_acts(rounds, st_no, hero_n):
    acts = (rounds or {}).get(str(st_no)) or (rounds or {}).get(st_no) or []
    out = []
    for a in acts:
        if a.get("player") != hero_n: continue
        t = a.get("type")
        if t == 0: out.append("fold")
        elif t == 4: out.append("check")
        elif t == 3: out.append("call")
        elif t in (5, 7): out.append("bet")
        elif t == 23: out.append("raise")
    return out


def match_seq(ha, seq):
    exact = seq.endswith("!")
    seq_clean = seq[:-1] if exact else seq
    parts = seq_clean.split("-")
    if not ha: return False
    if exact:
        if len(ha) != len(parts): return False
        return all(ha[k] == parts[k] for k in range(len(parts)))
    if len(parts) == 1: return parts[0] in ha
    i = 0
    for action in ha:
        if action == parts[i]: i += 1
        if i >= len(parts): return True
    return False


def passes(h, F):
    if F.get("positions") and h.get("pos") not in F["positions"]: return False
    if F.get("villain_positions") and h.get("villain_pos") not in F["villain_positions"]: return False
    if F.get("faced") and h.get("faced") not in F["faced"]: return False
    if F.get("actions") and h.get("hero_action") not in F["actions"]: return False
    if F.get("is_pfa") is not None and bool(h.get("is_pfa")) != F["is_pfa"]: return False
    if F.get("pos_relative") is not None and h.get("pos_relative_to_pfa") != F["pos_relative"]: return False
    if F.get("is_squeeze") is not None and bool(h.get("is_squeeze")) != F["is_squeeze"]: return False
    if F.get("is_bvb") is not None and bool(h.get("is_bvb")) != F["is_bvb"]: return False
    if F.get("saw_flop") is not None and bool(h.get("saw_flop")) != F["saw_flop"]: return False
    if F.get("saw_turn") is not None and bool(h.get("saw_turn")) != F["saw_turn"]: return False
    if F.get("saw_river") is not None and bool(h.get("saw_river")) != F["saw_river"]: return False
    if F.get("went_to_sd") is not None and bool(h.get("went_to_sd")) != F["went_to_sd"]: return False
    if F.get("result_min") is not None and (h.get("won_bb") or 0) < F["result_min"]: return False
    if F.get("n_to_flop_min") is not None and (h.get("n_to_flop") or 0) < F["n_to_flop_min"]: return False
    if F.get("n_to_flop_max") is not None and (h.get("n_to_flop") or 0) > F["n_to_flop_max"]: return False
    if F.get("allin_street") and h.get("allin_street") not in F["allin_street"]: return False
    # Novas flags
    if F.get("faced_3bet_after_open") is True and not h.get("faced_3bet_after_open"): return False
    if F.get("hero_4bet_response") and h.get("hero_4bet_response") not in F["hero_4bet_response"]: return False
    if F.get("cbet_flop") is True and not h.get("cbet_flop"): return False
    if F.get("cbet_turn") is True and not h.get("cbet_turn"): return False
    if F.get("cbet_river") is True and not h.get("cbet_river"): return False
    if F.get("flop_villain_pos") and flop_villain_pos(h) not in F["flop_villain_pos"]: return False
    if F.get("threebettor_pos") and threebettor_pos(h) not in F["threebettor_pos"]: return False
    rounds = h.get("rounds") or {}
    hero_n = h.get("hero_name")
    for sk, sn in [("flop_seq", 2), ("turn_seq", 3), ("river_seq", 4)]:
        ss = F.get(sk)
        if not ss: continue
        ha = hero_acts(rounds, sn, hero_n)
        if not any(match_seq(ha, s) for s in ss): return False
    return True


def make_F():
    return {
        "positions": set(), "villain_positions": set(), "faced": set(),
        "actions": set(), "flop_seq": set(), "turn_seq": set(), "river_seq": set(),
        "is_pfa": None, "pos_relative": None, "is_squeeze": None, "is_bvb": None,
        "saw_flop": None, "saw_turn": None, "saw_river": None, "went_to_sd": None,
        "result_min": None, "n_to_flop_min": None, "n_to_flop_max": None,
        "allin_street": set(),
        "faced_3bet_after_open": None, "hero_4bet_response": set(),
        "cbet_flop": None, "cbet_turn": None, "cbet_river": None,
        "flop_villain_pos": set(), "threebettor_pos": set(),
    }


def calc_pos(player_seat, btn_seat, players):
    if not players or player_seat is None or btn_seat is None: return None
    seats = sorted([p.get("seat") for p in players])
    if btn_seat not in seats: return None
    bi = seats.index(btn_seat)
    rotated = seats[bi:] + seats[:bi]
    if player_seat not in rotated: return None
    idx = rotated.index(player_seat); n = len(rotated)
    if n == 2: return "BTN" if idx == 0 else "BB"
    if idx == 0: return "BTN"
    if idx == 1: return "SB"
    if idx == 2: return "BB"
    pf = idx-2; npf = n-3
    if pf == npf: return "CO"
    if pf == npf-1: return "HJ"
    if pf == npf-2: return "MP"
    return "EP"


def flop_villain_pos(h):
    flop = (h.get("rounds") or {}).get("2") or (h.get("rounds") or {}).get(2) or []
    parts = {a.get("player") for a in flop} - {h.get("hero_name")}
    if len(parts) != 1: return None
    op = next(iter(parts))
    op_p = next((p for p in (h.get("players") or []) if p.get("name") == op), None)
    if not op_p: return None
    return calc_pos(op_p.get("seat"), h.get("btn_seat"), h.get("players"))


def threebettor_pos(h):
    pf = (h.get("rounds") or {}).get("1") or (h.get("rounds") or {}).get(1) or []
    hero_n = h.get("hero_name")
    hero_raised = False; threebettor = None
    for a in pf:
        if a.get("type") in (1, 2, 15): continue
        if a.get("player") == hero_n:
            if a.get("type") in AGGR: hero_raised = True; continue
            if hero_raised: break
        elif hero_raised and a.get("type") in AGGR:
            threebettor = a.get("player"); break
    if not threebettor: return None
    tp = next((p for p in (h.get("players") or []) if p.get("name") == threebettor), None)
    if not tp: return None
    return calc_pos(tp.get("seat"), h.get("btn_seat"), h.get("players"))


def filter_for(stat):
    """Replica applyFilterForStat() do JS."""
    F = make_F()
    if stat == "vpip" or stat == "pfr": pass
    elif stat.startswith("rfi_"):
        pos = stat.replace("rfi_", "")
        if pos in POSITIONS:
            F["positions"].add(pos); F["faced"].add("unopened"); F["actions"].add("raise")
    elif stat.startswith("flat_ip_"):
        pos = stat.replace("flat_ip_", "")
        if pos in POSITIONS:
            F["positions"].add(pos); F["faced"].add("raised"); F["pos_relative"] = "ip"; F["actions"].add("call")
    elif stat.startswith("flat_oop_"):
        pos = stat.replace("flat_oop_", "")
        if pos in POSITIONS:
            F["positions"].add(pos); F["faced"].add("raised"); F["pos_relative"] = "oop"; F["actions"].add("call")
    elif stat.startswith("3bet_nai_"):
        pos = stat.replace("3bet_nai_", "")
        if pos in POSITIONS:
            F["positions"].add(pos); F["faced"].add("raised"); F["actions"].add("raise")
    elif stat == "3bet_tot_nai" or stat == "3bet_tot":
        F["faced"].add("raised"); F["actions"].add("raise")
    elif stat == "3bet_tot_ai":
        F["faced"].add("raised"); F["actions"].add("raise"); F["allin_street"].add(1)
    elif stat == "f3bet_tot_nai" or stat == "f3bet_tot":
        F["faced_3bet_after_open"] = True; F["hero_4bet_response"].add("fold")
    elif stat == "f3bet_tot_ai":
        F["faced_3bet_after_open"] = True; F["hero_4bet_response"].add("fold"); F["allin_street"].add(1)
    elif stat == "f3bet_blind_nai" or stat == "f3bet_blind_tot":
        F["faced_3bet_after_open"] = True; F["hero_4bet_response"].add("fold"); F["threebettor_pos"].update(["SB","BB"])
    elif stat == "f3bet_blind_ai":
        F["faced_3bet_after_open"] = True; F["hero_4bet_response"].add("fold"); F["allin_street"].add(1); F["threebettor_pos"].update(["SB","BB"])
    elif stat == "4bet_tot_nai" or stat == "4bet_tot":
        F["faced_3bet_after_open"] = True; F["hero_4bet_response"].add("raise")
    elif stat == "4bet_tot_ai":
        F["faced_3bet_after_open"] = True; F["hero_4bet_response"].add("raise"); F["allin_street"].add(1)
    elif stat == "squeeze_nai" or stat == "squeeze_tot": F["is_squeeze"] = True
    elif stat == "squeeze_ai": F["is_squeeze"] = True; F["allin_street"].add(1)
    elif stat == "squeeze_ip_nai" or stat == "squeeze_ip_tot":
        F["is_squeeze"] = True; F["pos_relative"] = "ip"
    elif stat == "squeeze_ip_ai":
        F["is_squeeze"] = True; F["pos_relative"] = "ip"; F["allin_street"].add(1)
    elif stat == "squeeze_oop_nai" or stat == "squeeze_oop_tot":
        F["is_squeeze"] = True; F["pos_relative"] = "oop"
    elif stat == "squeeze_oop_ai":
        F["is_squeeze"] = True; F["pos_relative"] = "oop"; F["allin_street"].add(1)
    elif stat == "cbet_ip_vs_bb":
        F["is_pfa"] = True; F["saw_flop"] = True; F["cbet_flop"] = True
        F["positions"].update(["BTN","CO","HJ","MP","EP"])
        F["n_to_flop_min"] = 2; F["n_to_flop_max"] = 2
        F["flop_villain_pos"].add("BB")
    elif stat == "bet_turn_ip":
        F["is_pfa"] = True; F["saw_turn"] = True; F["cbet_flop"] = True; F["cbet_turn"] = True
        F["positions"].update(["BTN","CO","HJ","MP","EP"])
        F["n_to_flop_min"] = 2; F["n_to_flop_max"] = 2
        F["flop_villain_pos"].add("BB")
    elif stat == "bet_river_ip":
        F["is_pfa"] = True; F["saw_river"] = True; F["cbet_flop"] = True; F["cbet_turn"] = True; F["cbet_river"] = True
        F["positions"].update(["BTN","CO","HJ","MP","EP"])
        F["n_to_flop_min"] = 2; F["n_to_flop_max"] = 2
        F["flop_villain_pos"].add("BB")
    elif stat == "bet_vs_missed":
        F["is_pfa"] = True; F["saw_turn"] = True; F["turn_seq"].add("bet"); F["flop_seq"].add("check!")
        F["positions"].add("SB")
    elif stat == "cbet_oop":
        F["is_pfa"] = True; F["saw_flop"] = True; F["cbet_flop"] = True; F["positions"].add("SB")
        F["n_to_flop_min"] = 2; F["n_to_flop_max"] = 2
    elif stat == "bet_turn_oop":
        F["is_pfa"] = True; F["saw_turn"] = True; F["cbet_flop"] = True; F["cbet_turn"] = True; F["positions"].add("SB")
        F["n_to_flop_min"] = 2; F["n_to_flop_max"] = 2
    elif stat == "bet_river_oop":
        F["is_pfa"] = True; F["saw_river"] = True; F["cbet_flop"] = True; F["cbet_turn"] = True; F["cbet_river"] = True; F["positions"].add("SB")
        F["n_to_flop_min"] = 2; F["n_to_flop_max"] = 2
    elif stat == "check_raise":
        F["saw_flop"] = True; F["flop_seq"].add("check-raise")
    elif stat == "river_bet":
        F["saw_river"] = True; F["river_seq"].add("bet")
    elif stat == "call_river":
        F["saw_river"] = True; F["river_seq"].add("call")
    elif stat == "bb_f2_steal":
        F["positions"].add("BB"); F["faced"].add("raised"); F["actions"].add("fold")
        F["villain_positions"].update(["CO","BTN","SB"])
    elif stat in ("bb_xf","bb_xc","bb_xr"):
        F["positions"].add("BB"); F["faced"].add("raised"); F["actions"].add("call"); F["saw_flop"] = True
        if stat == "bb_xf": F["flop_seq"].add("check-fold")
        elif stat == "bb_xc": F["flop_seq"].add("check-call")
        else: F["flop_seq"].add("check-raise")
    elif stat == "prob_turn":
        F["positions"].add("BB"); F["faced"].add("raised"); F["actions"].add("call"); F["saw_turn"] = True
        F["flop_seq"].add("check!"); F["turn_seq"].add("bet")
    elif stat == "bb_prob_river":
        F["positions"].add("BB"); F["faced"].add("raised"); F["actions"].add("call"); F["saw_river"] = True
        F["turn_seq"].add("check!"); F["river_seq"].add("bet")
    elif stat == "agg_flop": F["saw_flop"] = True
    elif stat == "agg_turn": F["saw_turn"] = True
    elif stat == "agg_river": F["saw_river"] = True
    elif stat == "saw_flop": F["saw_flop"] = True
    elif stat == "wwsf": F["saw_flop"] = True; F["result_min"] = 0.01
    elif stat == "wtsd": F["went_to_sd"] = True
    elif stat == "won_sd": F["went_to_sd"] = True; F["result_min"] = 0.01
    elif stat == "sb_cbet_flop":
        F["is_bvb"] = True; F["is_pfa"] = True; F["positions"].add("SB"); F["saw_flop"] = True; F["cbet_flop"] = True
    elif stat == "sb_cbet_turn":
        F["is_bvb"] = True; F["is_pfa"] = True; F["positions"].add("SB"); F["saw_turn"] = True; F["cbet_flop"] = True; F["cbet_turn"] = True
    elif stat == "sb_cbet_river":
        F["is_bvb"] = True; F["is_pfa"] = True; F["positions"].add("SB"); F["saw_river"] = True; F["cbet_flop"] = True; F["cbet_turn"] = True; F["cbet_river"] = True
    elif stat == "bb_f2_sb_steal":
        F["positions"].add("BB"); F["faced"].add("raised"); F["actions"].add("fold"); F["villain_positions"].add("SB")
    elif stat == "bb_3bet_bw":
        F["positions"].add("BB"); F["faced"].add("raised"); F["actions"].add("raise"); F["villain_positions"].add("SB")
    elif stat == "bb_fold_vs_stab":
        F["positions"].add("BB"); F["saw_flop"] = True; F["flop_seq"].add("check-fold")
    elif stat == "3bet_btn_oa":
        F["positions"].add("BTN"); F["faced"].add("raised"); F["actions"].add("raise"); F["allin_street"].add(1)
    elif stat == "3bet_sb_oa":
        F["positions"].add("SB"); F["faced"].add("raised"); F["actions"].add("raise"); F["allin_street"].add(1)
    elif stat == "3bet_bb_oa":
        F["positions"].add("BB"); F["faced"].add("raised"); F["actions"].add("raise"); F["allin_street"].add(1)
    elif stat == "3bet_ip_no_btn_oa":
        F["positions"].update(["CO","HJ","MP","EP"]); F["faced"].add("raised"); F["actions"].add("raise")
        F["allin_street"].add(1); F["pos_relative"] = "ip"
    elif stat == "3bet_sb_lp_oa":
        F["positions"].add("SB"); F["faced"].add("raised"); F["actions"].add("raise"); F["allin_street"].add(1)
        F["villain_positions"].update(["EP","MP"])
    elif stat == "3bet_bb_lp_oa":
        F["positions"].add("BB"); F["faced"].add("raised"); F["actions"].add("raise"); F["allin_street"].add(1)
        F["villain_positions"].update(["CO","BTN","HJ"])
    return F


def hud_compute(hands):
    """Replica computeStats do JS para todas as stats."""
    out = {"vpip": [0,0], "pfr": [0,0]}
    rfi = {p: [0,0] for p in POSITIONS}
    flat_ip = {p: [0,0] for p in POSITIONS}
    flat_oop = {p: [0,0] for p in POSITIONS}
    threeb = {p: [0,0] for p in POSITIONS}
    threeb_tot = [0,0]; threeb_tot_nai = [0,0]; threeb_tot_ai = [0,0]
    f3b_nai = [0,0]; f3b_ai = [0,0]
    f3b_blind_nai = [0,0]; f3b_blind_ai = [0,0]
    fb4_nai = [0,0]; fb4_ai = [0,0]
    sq = [0,0]; sq_nai = [0,0]; sq_ai = [0,0]
    sq_ip = [0,0]; sq_ip_nai = [0,0]; sq_ip_ai = [0,0]
    sq_oop = [0,0]; sq_oop_nai = [0,0]; sq_oop_ai = [0,0]
    bb_f2_steal = [0,0]; bb_f2_sb = [0,0]; bb_3bet_bw = [0,0]
    sb_cbet_f = [0,0]; sb_cbet_t = [0,0]; sb_cbet_r = [0,0]
    cbet_ip = [0,0]; bet_turn_ip = [0,0]; bet_river_ip = [0,0]
    cbet_oop = [0,0]; bet_turn_oop = [0,0]; bet_river_oop = [0,0]
    bet_vs_missed = [0,0]
    cr = [0,0]; river_bet = [0,0]; call_river = [0,0]
    bb_xf = [0,0]; bb_xc = [0,0]; bb_xr = [0,0]
    prob_turn = [0,0]; bb_prob_river = [0,0]
    bb_fold_stab = [0,0]
    saw_flop_n = 0; saw_turn_n = 0; saw_river_n = 0
    sd = 0; won_sd = 0; wwsf_did = 0
    agg_f = [0,0]; agg_t = [0,0]; agg_r = [0,0]  # aggr, pass

    n = len(hands)
    for h in hands:
        pos = h.get("pos")
        rounds = h.get("rounds") or {}
        hero_n = h.get("hero_name")
        if h.get("hero_action") == "raise": out["pfr"][0] += 1
        if h.get("hero_action") in ("call", "raise"): out["vpip"][0] += 1

        if h.get("faced") == "unopened" and pos in POSITIONS:
            rfi[pos][1] += 1
            if h.get("hero_action") == "raise": rfi[pos][0] += 1

        if h.get("faced") == "raised":
            if h.get("pos_relative_to_pfa") == "ip" and pos in POSITIONS:
                flat_ip[pos][1] += 1
                if h.get("hero_action") == "call": flat_ip[pos][0] += 1
            if h.get("pos_relative_to_pfa") == "oop" and pos in POSITIONS:
                flat_oop[pos][1] += 1
                if h.get("hero_action") == "call": flat_oop[pos][0] += 1

        if h.get("faced") == "raised":
            threeb_tot[1] += 1
            # squeeze opp: priorCallers > 0
            pf1 = (rounds.get("1") or rounds.get(1) or [])
            prior_callers = 0
            for a in pf1:
                if a.get("player") == hero_n: break
                if a.get("type") == 3: prior_callers += 1
            sq_opp = prior_callers > 0
            if sq_opp:
                sq[1] += 1; sq_nai[1] += 1; sq_ai[1] += 1
                if h.get("pos_relative_to_pfa") == "ip":
                    sq_ip[1] += 1; sq_ip_nai[1] += 1; sq_ip_ai[1] += 1
                elif h.get("pos_relative_to_pfa") == "oop":
                    sq_oop[1] += 1; sq_oop_nai[1] += 1; sq_oop_ai[1] += 1
            if pos in POSITIONS:
                threeb[pos][1] += 1
                if h.get("hero_action") == "raise":
                    threeb[pos][0] += 1
                    threeb_tot[0] += 1
                    if h.get("allin_street") == 1: threeb_tot_ai[0] += 1
                    else: threeb_tot_nai[0] += 1
                    if h.get("is_squeeze"):
                        sq[0] += 1
                        if h.get("allin_street") == 1: sq_ai[0] += 1
                        else: sq_nai[0] += 1
                        if h.get("pos_relative_to_pfa") == "ip":
                            sq_ip[0] += 1
                            if h.get("allin_street") == 1: sq_ip_ai[0] += 1
                            else: sq_ip_nai[0] += 1
                        elif h.get("pos_relative_to_pfa") == "oop":
                            sq_oop[0] += 1
                            if h.get("allin_street") == 1: sq_oop_ai[0] += 1
                            else: sq_oop_nai[0] += 1

        if h.get("faced_3bet_after_open"):
            ai = h.get("allin_street") == 1
            if ai:
                f3b_ai[1] += 1
                if h.get("hero_4bet_response") == "fold": f3b_ai[0] += 1
                fb4_ai[1] += 1
                if h.get("hero_4bet_response") == "raise": fb4_ai[0] += 1
            else:
                f3b_nai[1] += 1
                if h.get("hero_4bet_response") == "fold": f3b_nai[0] += 1
                fb4_nai[1] += 1
                if h.get("hero_4bet_response") == "raise": fb4_nai[0] += 1
            # vs blind v2: detect 3bettor real
            heroRaised = False; threebettor = None
            for a in (rounds.get("1") or rounds.get(1) or []):
                if a.get("type") in (1,2,15): continue
                if a.get("player") == hero_n:
                    if a.get("type") in AGGR: heroRaised = True; continue
                    if heroRaised: break
                elif heroRaised and a.get("type") in AGGR:
                    threebettor = a.get("player"); break
            if threebettor:
                players = h.get("players") or []
                p3 = next((p for p in players if p.get("name") == threebettor), None)
                if p3:
                    seats = sorted([p.get("seat") for p in players])
                    btn = h.get("btn_seat")
                    if btn in seats:
                        bi = seats.index(btn)
                        rot = seats[bi:] + seats[:bi]
                        idx = rot.index(p3.get("seat")); nn = len(rot)
                        if nn == 2: pos3 = "BTN" if idx == 0 else "BB"
                        elif idx == 0: pos3 = "BTN"
                        elif idx == 1: pos3 = "SB"
                        elif idx == 2: pos3 = "BB"
                        else:
                            pf = idx-2; npf = nn-3
                            if pf == npf: pos3 = "CO"
                            elif pf == npf-1: pos3 = "HJ"
                            elif pf == npf-2: pos3 = "MP"
                            else: pos3 = "EP"
                        if pos3 in ("SB","BB"):
                            if ai:
                                f3b_blind_ai[1] += 1
                                if h.get("hero_4bet_response") == "fold": f3b_blind_ai[0] += 1
                            else:
                                f3b_blind_nai[1] += 1
                                if h.get("hero_4bet_response") == "fold": f3b_blind_nai[0] += 1

        if pos == "BB" and h.get("faced") == "raised" and h.get("villain_pos") in ("CO","BTN","SB"):
            bb_f2_steal[1] += 1
            if h.get("hero_action") == "fold": bb_f2_steal[0] += 1
            if h.get("villain_pos") == "SB":
                bb_f2_sb[1] += 1
                if h.get("hero_action") == "fold": bb_f2_sb[0] += 1
                bb_3bet_bw[1] += 1
                if h.get("hero_action") == "raise": bb_3bet_bw[0] += 1

        if h.get("is_bvb") and h.get("is_pfa") and pos == "SB" and h.get("saw_flop"):
            sb_cbet_f[1] += 1
            if h.get("cbet_flop"): sb_cbet_f[0] += 1
            if h.get("cbet_flop") and h.get("saw_turn"):
                sb_cbet_t[1] += 1
                if h.get("cbet_turn"): sb_cbet_t[0] += 1
                if h.get("cbet_turn") and h.get("saw_river"):
                    sb_cbet_r[1] += 1
                    if h.get("cbet_river"): sb_cbet_r[0] += 1

        if h.get("is_pfa") and h.get("saw_flop"):
            flop = (rounds.get("2") or rounds.get(2) or [])
            participants = {a.get("player") for a in flop} - {hero_n}
            players = h.get("players") or []
            if len(participants) == 1:
                op_name = next(iter(participants))
                op_player = next((p for p in players if p.get("name") == op_name), None)
                if op_player:
                    seats = sorted([p.get("seat") for p in players])
                    btn = h.get("btn_seat")
                    if btn in seats:
                        bi = seats.index(btn)
                        rot = seats[bi:] + seats[:bi]
                        idx = rot.index(op_player.get("seat")); nn = len(rot)
                        if nn == 2: opPos = "BTN" if idx == 0 else "BB"
                        elif idx == 0: opPos = "BTN"
                        elif idx == 1: opPos = "SB"
                        elif idx == 2: opPos = "BB"
                        else:
                            pf = idx-2; npf = nn-3
                            if pf == npf: opPos = "CO"
                            elif pf == npf-1: opPos = "HJ"
                            elif pf == npf-2: opPos = "MP"
                            else: opPos = "EP"
                        if opPos == "BB" and pos in ("BTN","CO","HJ","MP","EP"):
                            cbet_ip[1] += 1
                            if h.get("cbet_flop"): cbet_ip[0] += 1
                            if h.get("cbet_flop") and h.get("saw_turn"):
                                bet_turn_ip[1] += 1
                                if h.get("cbet_turn"): bet_turn_ip[0] += 1
                                if h.get("cbet_turn") and h.get("saw_river"):
                                    bet_river_ip[1] += 1
                                    if h.get("cbet_river"): bet_river_ip[0] += 1
                        if pos == "SB":
                            cbet_oop[1] += 1
                            if h.get("cbet_flop"): cbet_oop[0] += 1
                            if h.get("cbet_flop") and h.get("saw_turn"):
                                bet_turn_oop[1] += 1
                                if h.get("cbet_turn"): bet_turn_oop[0] += 1
                                if h.get("cbet_turn") and h.get("saw_river"):
                                    bet_river_oop[1] += 1
                                    if h.get("cbet_river"): bet_river_oop[0] += 1

            if h.get("saw_turn"):
                heroBetFlop = any(a.get("player") == hero_n and a.get("type") in AGGR for a in flop)
                if not heroBetFlop:
                    turn = (rounds.get("3") or rounds.get(3) or [])
                    if turn and turn[0].get("player") == hero_n:
                        bet_vs_missed[1] += 1
                        if turn[0].get("type") in AGGR: bet_vs_missed[0] += 1

        if h.get("saw_flop"): saw_flop_n += 1
        if h.get("saw_turn"): saw_turn_n += 1
        if h.get("saw_river"): saw_river_n += 1
        if h.get("went_to_sd"):
            sd += 1
            if (h.get("won_bb") or 0) > 0: won_sd += 1
        if h.get("saw_flop") and (h.get("won_bb") or 0) > 0: wwsf_did += 1

        # Aggression
        for st_no, key in [(2, "f"), (3, "t"), (4, "r")]:
            for a in (rounds.get(str(st_no)) or rounds.get(st_no) or []):
                if a.get("player") != hero_n: continue
                t = a.get("type")
                if t in AGGR:
                    if key == "f": agg_f[0] += 1
                    elif key == "t": agg_t[0] += 1
                    else: agg_r[0] += 1
                elif t in (3, 0):
                    if key == "f": agg_f[1] += 1
                    elif key == "t": agg_t[1] += 1
                    else: agg_r[1] += 1

        # Check-raise
        if h.get("saw_flop"):
            flop = (rounds.get("2") or rounds.get(2) or [])
            heroChecked = False; heroRaised = False
            for a in flop:
                if a.get("player") != hero_n: continue
                if a.get("type") == 4: heroChecked = True
                elif heroChecked and a.get("type") in AGGR: heroRaised = True; break
            heroIsOOP = h.get("pos_relative_to_pfa") == "oop" or (h.get("is_pfa") and pos in ("SB","BB"))
            if heroIsOOP and heroChecked:
                cr[1] += 1
                if heroRaised: cr[0] += 1

        # River bet/call
        if h.get("saw_river"):
            river = (rounds.get("4") or rounds.get(4) or [])
            pending = False
            for a in river:
                if a.get("player") == hero_n:
                    if not pending:
                        river_bet[1] += 1
                        if a.get("type") in AGGR: river_bet[0] += 1
                    break
                if a.get("type") in AGGR: pending = True
            pending = False
            for a in river:
                if a.get("player") != hero_n:
                    if a.get("type") in AGGR: pending = True
                else:
                    if pending:
                        call_river[1] += 1
                        if a.get("type") == 3: call_river[0] += 1
                        break

        # BB defense postflop
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
                    bb_xf[1] += 1; bb_xf[0] += 1
                    bb_xc[1] += 1; bb_xr[1] += 1
                elif bb_action == "call":
                    bb_xc[1] += 1; bb_xc[0] += 1
                    bb_xf[1] += 1; bb_xr[1] += 1
                elif bb_action == "raise":
                    bb_xr[1] += 1; bb_xr[0] += 1
                    bb_xf[1] += 1; bb_xc[1] += 1

        # Probe turn
        if pos == "BB" and h.get("faced") == "raised" and h.get("hero_action") == "call" and h.get("saw_turn") and h.get("first_aggressor"):
            opener = h.get("first_aggressor")
            flop = (rounds.get("2") or rounds.get(2) or [])
            ocb = not any(a.get("player") == opener and a.get("type") in AGGR for a in flop)
            if ocb:
                turn = (rounds.get("3") or rounds.get(3) or [])
                for a in turn:
                    if a.get("player") != hero_n:
                        if a.get("player") != opener: continue
                        break
                    prob_turn[1] += 1
                    if a.get("type") in AGGR: prob_turn[0] += 1
                    break

        # Probe river
        if pos == "BB" and h.get("faced") == "raised" and h.get("hero_action") == "call" and h.get("saw_river") and h.get("first_aggressor"):
            opener = h.get("first_aggressor")
            turn = (rounds.get("3") or rounds.get(3) or [])
            tcb = not any(a.get("player") == opener and a.get("type") in AGGR for a in turn)
            if tcb:
                river = (rounds.get("4") or rounds.get(4) or [])
                for a in river:
                    if a.get("player") != hero_n:
                        if a.get("player") != opener: continue
                        break
                    bb_prob_river[1] += 1
                    if a.get("type") in AGGR: bb_prob_river[0] += 1
                    break

        # BB fold vs stab
        if pos == "BB" and h.get("saw_flop"):
            flop = (rounds.get("2") or rounds.get(2) or [])
            bb_checked = False; villain_bet = False; bb_resp = None
            for a in flop:
                if a.get("player") == hero_n:
                    if not bb_checked and a.get("type") == 4:
                        bb_checked = True; continue
                    if villain_bet:
                        bb_resp = a.get("type"); break
                elif bb_checked and a.get("type") in AGGR:
                    villain_bet = True
            if bb_checked and villain_bet:
                bb_fold_stab[1] += 1
                if bb_resp == 0: bb_fold_stab[0] += 1

    # Now construct out: out[stat] = (num, denom)
    out["vpip"] = (out["vpip"][0], n)
    out["pfr"] = (out["pfr"][0], n)
    for p in POSITIONS:
        out[f"rfi_{p}"] = tuple(rfi[p])
        out[f"flat_ip_{p}"] = tuple(flat_ip[p])
        out[f"flat_oop_{p}"] = tuple(flat_oop[p])
        out[f"3bet_nai_{p}"] = tuple(threeb[p])
    # Squeeze: HUD usa sq_opps como denom
    out["squeeze_nai"] = (sq_nai[0], sq[1]); out["squeeze_ai"] = (sq_ai[0], sq[1]); out["squeeze_tot"] = (sq[0], sq[1])
    out["squeeze_ip_nai"] = (sq_ip_nai[0], sq_ip[1]); out["squeeze_ip_ai"] = (sq_ip_ai[0], sq_ip[1]); out["squeeze_ip_tot"] = (sq_ip[0], sq_ip[1])
    out["squeeze_oop_nai"] = (sq_oop_nai[0], sq_oop[1]); out["squeeze_oop_ai"] = (sq_oop_ai[0], sq_oop[1]); out["squeeze_oop_tot"] = (sq_oop[0], sq_oop[1])
    # 3bet totais: denom = faced_raised total
    fr_total = sum(threeb[p][1] for p in POSITIONS)  # sum of all faced=raised by pos
    out["3bet_tot_nai"] = (threeb_tot_nai[0], fr_total)
    out["3bet_tot_ai"] = (threeb_tot_ai[0], fr_total)
    out["3bet_tot"] = (threeb_tot[0], fr_total)
    out["f3bet_tot_nai"] = tuple(f3b_nai); out["f3bet_tot_ai"] = tuple(f3b_ai)
    out["f3bet_tot"] = (f3b_nai[0]+f3b_ai[0], f3b_nai[1]+f3b_ai[1])
    out["4bet_tot_nai"] = tuple(fb4_nai); out["4bet_tot_ai"] = tuple(fb4_ai)
    out["4bet_tot"] = (fb4_nai[0]+fb4_ai[0], fb4_nai[1]+fb4_ai[1])
    out["f3bet_blind_nai"] = tuple(f3b_blind_nai); out["f3bet_blind_ai"] = tuple(f3b_blind_ai)
    out["f3bet_blind_tot"] = (f3b_blind_nai[0]+f3b_blind_ai[0], f3b_blind_nai[1]+f3b_blind_ai[1])
    out["bb_f2_steal"] = tuple(bb_f2_steal); out["bb_f2_sb_steal"] = tuple(bb_f2_sb); out["bb_3bet_bw"] = tuple(bb_3bet_bw)
    out["sb_cbet_flop"] = tuple(sb_cbet_f); out["sb_cbet_turn"] = tuple(sb_cbet_t); out["sb_cbet_river"] = tuple(sb_cbet_r)
    out["cbet_ip_vs_bb"] = tuple(cbet_ip); out["bet_turn_ip"] = tuple(bet_turn_ip); out["bet_river_ip"] = tuple(bet_river_ip)
    out["cbet_oop"] = tuple(cbet_oop); out["bet_turn_oop"] = tuple(bet_turn_oop); out["bet_river_oop"] = tuple(bet_river_oop)
    out["bet_vs_missed"] = tuple(bet_vs_missed)
    out["check_raise"] = tuple(cr); out["river_bet"] = tuple(river_bet); out["call_river"] = tuple(call_river)
    out["bb_xf"] = tuple(bb_xf); out["bb_xc"] = tuple(bb_xc); out["bb_xr"] = tuple(bb_xr)
    out["prob_turn"] = tuple(prob_turn); out["bb_prob_river"] = tuple(bb_prob_river)
    out["bb_fold_vs_stab"] = tuple(bb_fold_stab)
    out["saw_flop"] = (saw_flop_n, n); out["wwsf"] = (wwsf_did, saw_flop_n)
    out["wtsd"] = (sd, saw_flop_n); out["won_sd"] = (won_sd, sd)
    out["agg_flop"] = (agg_f[0], agg_f[0]+agg_f[1])
    out["agg_turn"] = (agg_t[0], agg_t[0]+agg_t[1])
    out["agg_river"] = (agg_r[0], agg_r[0]+agg_r[1])
    return out


def main():
    print(f"Lendo {HANDS_PATH} ...", file=sys.stderr)
    with open(HANDS_PATH, encoding="utf-8") as f:
        hands = json.load(f)
    print(f"  {len(hands)} maos carregadas", file=sys.stderr)

    print("Calculando HUD...", file=sys.stderr)
    hud = hud_compute(hands)

    # Lista todas as stats em ordem
    all_stats = ["vpip", "pfr"]
    for p in POSITIONS: all_stats.append(f"rfi_{p}")
    for p in ["EP","MP","HJ","CO","BTN"]: all_stats.append(f"flat_ip_{p}")
    for p in ["SB","BB"]: all_stats.append(f"flat_oop_{p}")
    for p in POSITIONS: all_stats.append(f"3bet_nai_{p}")
    all_stats += ["3bet_tot_nai","3bet_tot_ai","3bet_tot","f3bet_tot_nai","f3bet_tot_ai","f3bet_tot",
                  "f3bet_blind_nai","f3bet_blind_ai","f3bet_blind_tot","4bet_tot_nai","4bet_tot_ai","4bet_tot"]
    all_stats += ["squeeze_nai","squeeze_ai","squeeze_tot","squeeze_ip_nai","squeeze_ip_ai","squeeze_ip_tot",
                  "squeeze_oop_nai","squeeze_oop_ai","squeeze_oop_tot"]
    all_stats += ["3bet_btn_oa","3bet_sb_oa","3bet_bb_oa","3bet_ip_no_btn_oa","3bet_sb_lp_oa","3bet_bb_lp_oa"]
    all_stats += ["cbet_ip_vs_bb","bet_turn_ip","bet_river_ip","bet_vs_missed",
                  "cbet_oop","bet_turn_oop","bet_river_oop","check_raise"]
    all_stats += ["river_bet","call_river"]
    all_stats += ["bb_f2_steal","bb_xf","bb_xc","bb_xr","prob_turn","bb_prob_river"]
    all_stats += ["agg_flop","agg_turn","agg_river"]
    all_stats += ["saw_flop","wwsf","wtsd","won_sd"]
    all_stats += ["sb_cbet_flop","sb_cbet_turn","sb_cbet_river","bb_f2_sb_steal","bb_3bet_bw","bb_fold_vs_stab"]

    print(f"\n{'STAT':<20} {'FILTER':>7} {'NUM':>7} {'DEN':>7}  {'HUD%':>7} {'FLT%':>7}  STATUS")
    print("-" * 75)
    ok = 0; warn = 0; bad = 0; missing = 0
    bad_stats = []
    for stat in all_stats:
        if stat not in hud:
            print(f"{stat:<20}  -- HUD missing"); missing += 1; continue
        num, den = hud[stat]
        F = filter_for(stat)
        # vpip e pfr nao tem filtro especifico, sao denom = total hands
        if stat in ("vpip", "pfr"):
            n_filter = num  # filter wouldn't make sense here
            status = "OK (no filter)"
        else:
            n_filter = sum(1 for h in hands if passes(h, F))
            hud_pct = (num*100.0/den) if den else 0
            flt_pct = (n_filter*100.0/den) if den else 0
            diff = abs(flt_pct - hud_pct)
            if diff < 0.5: status = "OK"; ok += 1
            elif diff < 3.0: status = f"WARN ({diff:.1f}%)"; warn += 1
            else:
                status = f"DIFF ({diff:.1f}%)"; bad += 1
                bad_stats.append((stat, num, n_filter, den, hud_pct, flt_pct, diff))
        hud_pct = (num*100.0/den) if den else 0
        flt_pct = (n_filter*100.0/den) if den else 0
        print(f"{stat:<20} {n_filter:>7} {num:>7} {den:>7}  {hud_pct:>6.1f}% {flt_pct:>6.1f}%  {status}")

    print("-" * 75)
    print(f"OK={ok}  WARN={warn}  DIFF={bad}  MISSING={missing}  TOTAL={len(all_stats)}")
    if bad_stats:
        print("\n--- DIFFs >3% ---")
        for s, num, fn, den, hp, fp, d in sorted(bad_stats, key=lambda x: -x[6]):
            print(f"  {s:<22} num={num} filter={fn} den={den} HUD={hp:.1f}% FLT={fp:.1f}% diff={d:.1f}%")


if __name__ == "__main__":
    main()
