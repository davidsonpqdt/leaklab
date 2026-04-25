"""Gera os JSONs dos ranges GTO transcritos das prints do GTO Wizard.

REGRA: meu range deve ser >= GTO. Se GTO joga uma mao em qualquer %, marco como
in-range. Resultado: meu % sempre >= GTO %.

Cada range marca cada mao como raise=100 ou fold=100 (binario).
"transcribed_from_screenshot": true pra usuario validar depois.
"""
import json, os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "ranges")

RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]

def all_hands():
    out = []
    for i in range(13):
        for j in range(13):
            r1, r2 = RANKS[i], RANKS[j]
            if i == j: out.append(r1 + r2)
            elif j > i: out.append(r1 + r2 + "s")
            else: out.append(r2 + r1 + "o")
    return list(set(out))


def make_range(meta: dict, in_range_hands: set, raise_size: str = "raise_2x") -> dict:
    hands = {}
    for h in all_hands():
        if h in in_range_hands:
            hands[h] = {raise_size: 100, "fold": 0}
        else:
            hands[h] = {raise_size: 0, "fold": 100}
    return {
        **meta,
        "transcribed_from_screenshot": True,
        "actions": [raise_size, "fold"],
        "hands": hands
    }


def parse_hand_list(spec: str) -> set[str]:
    out = set()
    for tok in spec.split():
        tok = tok.strip()
        if not tok: continue
        if "+" in tok:
            base = tok.replace("+", "")
            if len(base) == 2 and base[0] == base[1]:
                start = RANKS.index(base[0])
                for i in range(start, -1, -1):
                    out.add(RANKS[i] + RANKS[i])
            elif base.endswith("s") and len(base) == 3:
                hi, lo = base[0], base[1]
                lo_i = RANKS.index(lo)
                hi_i = RANKS.index(hi)
                for i in range(lo_i, hi_i, -1):
                    out.add(hi + RANKS[i] + "s")
            elif base.endswith("o") and len(base) == 3:
                hi, lo = base[0], base[1]
                lo_i = RANKS.index(lo)
                hi_i = RANKS.index(hi)
                for i in range(lo_i, hi_i, -1):
                    out.add(hi + RANKS[i] + "o")
        else:
            out.add(tok)
    return out


def combos_pct(hands_set: set) -> float:
    total = 0
    for h in hands_set:
        if len(h) == 2 and h[0] == h[1]: total += 6
        elif h.endswith("s"): total += 4
        elif h.endswith("o"): total += 12
    return 100 * total / 1326


# ============= TRANSCRICOES =============
# Cada range tem GTO target — meu deve ser >= que esse target.

# BTN 30bb (GTO 48.7%) — meu 49.9% ✓
btn_30 = parse_hand_list("""
22+
A2s+ K2s+ Q4s+ Q3s J4s+ J3s T5s+ 95s+ 94s 84s+ 74s+ 64s+ 53s+ 54s 43s
A2o+ K7o+ Q8o+ J8o+ T8o+ 98o
""")

# BTN 50bb (GTO 53.8%) — vou adicionar 1 mao pra ficar acima
btn_50 = parse_hand_list("""
22+
A2s+ K2s+ Q2s+ J2s+ T4s+ 93s+ 83s+ 73s+ 63s+ 53s+ 43s 32s
A2o+ K6o+ Q7o+ J8o+ T8o+ 98o 87o
""")

# BTN 80bb (GTO 54.6%) — meu 56% ✓
btn_80 = parse_hand_list("""
22+
A2s+ K2s+ Q2s+ J2s+ T4s+ 93s+ 83s+ 73s+ 63s+ 53s+ 43s 32s
A2o+ K5o+ Q7o+ J8o+ T8o+ 98o 87o 76o
""")

# CO 30bb (GTO 36.3%) — precisa subir; meu antigo 34.2%
co_30 = parse_hand_list("""
22+
A2s+ K6s+ Q8s+ J8s+ T7s+ 97s+ 86s+ 75s+ 64s+ 54s 53s 43s
A2o+ K9o+ Q9o+ JTo T9o 98o
""")

# HJ 30bb (GTO 29.1%) — re-revisado
hj_30 = parse_hand_list("""
22+
A2s+ K8s+ Q8s+ J8s+ T8s+ 97s+ 86s+ 75s+ 64s+ 53s 54s
A8o+ KTo+ QTo+ JTo T9o 98o
""")

# MP 30bb (GTO 24.5%) — re-revisado
mp_30 = parse_hand_list("""
22+
A2s+ K9s+ Q9s+ J9s+ T9s 98s 87s 86s 76s 75s 65s 64s 54s
A9o+ A5o KTo+ QJo JTo
""")

# EP 30bb (GTO 21.3%) — meu 22.5% ✓
ep_30 = parse_hand_list("""
22+
A2s+ K9s+ Q9s+ J9s+ T9s 98s 97s 87s 86s 76s 75s 65s 64s 54s
ATo+ KTo+ QJo
""")

# SB 30bb open (raise+allin) — print 7.PNG do 30bbs
# Allin 2.3% + Raise 27.3% = 29.6% open total. Call (limp) e Fold nao contam.
sb_30 = parse_hand_list("""
22+
A2s+ K9s+ Q9s+ J9s+
T9s 98s 97s 87s 86s 76s 75s 65s 64s 54s 53s 43s
A2o+ K9o+ KQo
""")


# ============= GERA OS ARQUIVOS =============

ranges_to_write = [
    ("btn_30bb_unopened_chipev.json",
     {"id": "open_BTN_30bb_chipev_8max", "format": "8max", "stack_bb": 30, "icm": "chipev",
      "scenario": "open", "hero_pos": "BTN", "vs": None,
      "source": "GTO Wizard ChipEV (print 6.PNG do 30bbs)",
      "raise_size": "2x", "gto_target_pct": 48.7},
     btn_30, "raise_2x"),
    ("btn_50bb_unopened_chipev.json",
     {"id": "open_BTN_50bb_chipev_8max", "format": "8max", "stack_bb": 50, "icm": "chipev",
      "scenario": "open", "hero_pos": "BTN", "vs": None,
      "source": "GTO Wizard ChipEV (print 6.PNG do 50bbs)",
      "raise_size": "2.1x", "gto_target_pct": 53.8},
     btn_50, "raise_2.1x"),
    ("btn_80bb_unopened_chipev.json",
     {"id": "open_BTN_80bb_chipev_8max", "format": "8max", "stack_bb": 80, "icm": "chipev",
      "scenario": "open", "hero_pos": "BTN", "vs": None,
      "source": "GTO Wizard ChipEV (print 6.PNG do 80bbs)",
      "raise_size": "2.3x", "gto_target_pct": 54.6},
     btn_80, "raise_2.3x"),
    ("co_30bb_unopened_chipev.json",
     {"id": "open_CO_30bb_chipev_8max", "format": "8max", "stack_bb": 30, "icm": "chipev",
      "scenario": "open", "hero_pos": "CO", "vs": None,
      "source": "GTO Wizard ChipEV (print 5.PNG do 30bbs)",
      "raise_size": "2x", "gto_target_pct": 36.3},
     co_30, "raise_2x"),
    ("hj_30bb_unopened_chipev.json",
     {"id": "open_HJ_30bb_chipev_8max", "format": "8max", "stack_bb": 30, "icm": "chipev",
      "scenario": "open", "hero_pos": "HJ", "vs": None,
      "source": "GTO Wizard ChipEV (print 4.PNG do 30bbs)",
      "raise_size": "2x", "gto_target_pct": 29.1},
     hj_30, "raise_2x"),
    ("mp_30bb_unopened_chipev.json",
     {"id": "open_MP_30bb_chipev_8max", "format": "8max", "stack_bb": 30, "icm": "chipev",
      "scenario": "open", "hero_pos": "MP", "vs": None,
      "source": "GTO Wizard ChipEV (print 3.PNG do 30bbs)",
      "raise_size": "2x", "gto_target_pct": 24.5},
     mp_30, "raise_2x"),
    ("ep_30bb_unopened_chipev.json",
     {"id": "open_EP_30bb_chipev_8max", "format": "8max", "stack_bb": 30, "icm": "chipev",
      "scenario": "open", "hero_pos": "EP", "vs": None,
      "source": "GTO Wizard ChipEV (print 2.PNG do 30bbs)",
      "raise_size": "2x", "gto_target_pct": 21.3},
     ep_30, "raise_2x"),
    ("sb_30bb_unopened_chipev.json",
     {"id": "open_SB_30bb_chipev_8max", "format": "8max", "stack_bb": 30, "icm": "chipev",
      "scenario": "open", "hero_pos": "SB", "vs": None,
      "source": "GTO Wizard ChipEV (print 7.PNG do 30bbs) — somente raise+allin (limp/call NAO contam pra RFI)",
      "raise_size": "2x", "gto_target_pct": 29.6},
     sb_30, "raise_2x"),
]

print(f"{'Range':<48} {'Meu %':>8} {'GTO':>8} {'Diff':>7}")
print("-" * 75)
for fname, meta, in_range, raise_key in ranges_to_write:
    range_data = make_range(meta, in_range, raise_size=raise_key)
    path = os.path.join(OUT_DIR, fname)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(range_data, fh, ensure_ascii=False, indent=2)
    pct = combos_pct(in_range)
    target = meta.get("gto_target_pct")
    diff = (pct - target) if target else 0
    target_str = f"{target:.1f}%" if target else "—"
    diff_str = f"{diff:+.1f}" if target else "—"
    status = ""
    if target:
        if diff < 0: status = "  ABAIXO"
        elif diff < 0.5: status = "  =~"
        else: status = "  OK"
    print(f"  {fname:<46} {pct:>6.1f}% {target_str:>8} {diff_str:>7}{status}")
