"""Agrega maos parsed em stats HUD e renderiza como HTML.

Uso:
    python hud_generator.py /pasta --hero Noshovepls -o hud.html
"""
from __future__ import annotations
import os, argparse
from collections import defaultdict

from parser import (
    iter_hands_in_folder, ACT_FOLD, ACT_CALL, ACT_CHECK, AGGRESSIVE,
)


# Ordem de exibicao das posicoes no HUD
POSITIONS = ["EP", "MP", "HJ", "CO", "BTN", "SB", "BB"]


def aggregate(folder: str, hero: str | None) -> dict:
    """Percorre maos parsed e tabula contadores HUD."""
    s = defaultdict(int)
    rfi_pos = defaultdict(lambda: {"ch": 0, "did": 0})
    flat_pos = defaultdict(lambda: {"ch": 0, "did": 0})
    threeb_pos = defaultdict(lambda: {"ch": 0, "did": 0})
    bb_steal = {"ch": 0, "fold": 0, "call": 0, "_3bet": 0}
    n = 0

    for h in iter_hands_in_folder(folder, hero):
        n += 1
        pos = h["pos"]
        rounds = h["rounds"]
        hero_name = h["hero_name"]
        was_pfa = (h["hero_action"] == "raise" and h["faced"] in ("unopened", "limped"))

        # ----- Preflop -----
        s["pfr"] += int(h["hero_action"] == "raise")
        s["vpip"] += int(h["hero_action"] in ("call", "raise"))
        s["limp"] += int(h["faced"] == "unopened" and h["hero_action"] == "call")

        # 3bet (face a um raise)
        if h["faced"] == "raised":
            threeb_pos[pos]["ch"] += 1
            flat_pos[pos]["ch"] += 1
            if h["hero_action"] == "raise":
                threeb_pos[pos]["did"] += 1
            elif h["hero_action"] == "call":
                flat_pos[pos]["did"] += 1

        # 4bet (vs 3bet) — usa o NOVO faced_3bet_after_open OU faced=="3bet" na 1a decisao
        if h.get("faced_3bet_after_open"):
            s["f4b_ch"] += 1
            if h.get("hero_4bet_response") == "raise":
                s["f4b_did"] += 1
        elif h["faced"] == "3bet":
            s["f4b_ch"] += 1
            if h["hero_action"] == "raise":
                s["f4b_did"] += 1

        # RFI por posicao
        if h["faced"] == "unopened":
            rfi_pos[pos]["ch"] += 1
            if h["hero_action"] == "raise":
                rfi_pos[pos]["did"] += 1

        # BB defense vs steal
        if pos == "BB" and h["faced"] == "raised" and h["villain_pos"] in ("CO", "BTN", "SB"):
            bb_steal["ch"] += 1
            if h["hero_action"] == "fold": bb_steal["fold"] += 1
            elif h["hero_action"] == "call": bb_steal["call"] += 1
            elif h["hero_action"] == "raise": bb_steal["_3bet"] += 1

        # ----- Postflop -----
        def hero_did_aggr(s_no): return any(a["player"] == hero_name and a["type"] in AGGRESSIVE for a in rounds.get(s_no, []))
        def hero_did_call(s_no): return any(a["player"] == hero_name and a["type"] == ACT_CALL for a in rounds.get(s_no, []))
        def hero_did_check(s_no): return any(a["player"] == hero_name and a["type"] == ACT_CHECK for a in rounds.get(s_no, []))
        def hero_did_fold(s_no): return any(a["player"] == hero_name and a["type"] == ACT_FOLD for a in rounds.get(s_no, []))
        def hero_present(s_no): return any(a["player"] == hero_name for a in rounds.get(s_no, []))

        if h["saw_flop"]:
            s["saw_flop"] += 1
            if h["hero_win"] > 0:
                s["wwsf"] += 1
            on_river = hero_present(4)
            folded_river = hero_did_fold(4)
            others_on_river = {a["player"] for a in rounds.get(4, []) if a["player"] != hero_name and a["type"] != ACT_FOLD}
            if on_river and not folded_river and others_on_river:
                s["wtsd"] += 1
                if h["hero_win"] > 0:
                    s["won_sd"] += 1

        # C-bet flop -> turn -> river (so se hero foi PFA)
        if was_pfa and h["saw_flop"]:
            s["cbet_f_ch"] += 1
            if hero_did_aggr(2):
                s["cbet_f_did"] += 1
                if hero_present(3):
                    s["cbet_t_ch"] += 1
                    if hero_did_aggr(3):
                        s["cbet_t_did"] += 1
                        if hero_present(4):
                            s["cbet_r_ch"] += 1
                            if hero_did_aggr(4):
                                s["cbet_r_did"] += 1

        # Face C-bet flop (hero pagou preflop, opener apostou flop)
        if (not was_pfa) and h["saw_flop"] and h["first_aggressor"]:
            opener = h["first_aggressor"]
            if any(a["player"] == opener and a["type"] in AGGRESSIVE for a in rounds.get(2, [])):
                s["face_cbet_ch"] += 1
                if hero_did_fold(2): s["face_cbet_fold"] += 1
                elif hero_did_call(2): s["face_cbet_call"] += 1
                elif hero_did_aggr(2): s["face_cbet_raise"] += 1

        # Aggression (acoes por street)
        for label, street in [("f", 2), ("t", 3), ("r", 4)]:
            if hero_did_aggr(street): s[f"agg_{label}"] += 1
            if hero_did_call(street): s[f"call_{label}"] += 1
            if hero_did_check(street): s[f"check_{label}"] += 1

    s["n"] = n
    return {"stats": s, "rfi_pos": rfi_pos, "flat_pos": flat_pos,
            "threeb_pos": threeb_pos, "bb_steal": bb_steal}


def pct(num, den) -> float:
    return (100.0 * num / den) if den else 0.0


def render_html(label: str, agg: dict) -> str:
    s, rfi, flat, threeb, bb_steal = (agg["stats"], agg["rfi_pos"], agg["flat_pos"],
                                       agg["threeb_pos"], agg["bb_steal"])
    n = s["n"]
    P = lambda num, den: f"{pct(num, den):.1f}" if den else "—"

    rfi_row = "".join(f"<td>{P(rfi[p]['did'], rfi[p]['ch'])}</td>" for p in POSITIONS)
    rfi_ss  = "".join(f"<td class='ss'>{rfi[p]['ch']}</td>" for p in POSITIONS)
    flat_row = "".join(f"<td>{P(flat[p]['did'], flat[p]['ch'])}</td>" for p in POSITIONS)
    flat_ss  = "".join(f"<td class='ss'>{flat[p]['ch']}</td>" for p in POSITIONS)
    threeb_row = "".join(f"<td>{P(threeb[p]['did'], threeb[p]['ch'])}</td>" for p in POSITIONS)
    threeb_ss  = "".join(f"<td class='ss'>{threeb[p]['ch']}</td>" for p in POSITIONS)

    body = f"""
<div class="hud">
  <h1>HUD — {label} <span class="hands">{n} maos</span></h1>
  <div class="row">
    <div class="card box">
      <h2>Pre-Flop Geral</h2>
      <table class="kv">
        <tr><td>VPIP</td><td>{P(s['vpip'], n)}</td></tr>
        <tr><td>PFR</td><td>{P(s['pfr'], n)}</td></tr>
        <tr><td>Limp</td><td>{P(s['limp'], n)}</td></tr>
        <tr><td>3bet (vs raise)</td><td>{P(threeb_total_did(threeb), threeb_total_ch(threeb))}</td></tr>
        <tr><td>4bet (vs 3bet)</td><td>{P(s['f4b_did'], s['f4b_ch'])}</td></tr>
      </table>
    </div>
    <div class="card box wide">
      <h2>Pre-Flop por Posicao</h2>
      <table class="pos">
        <tr><th></th>{''.join(f'<th>{p}</th>' for p in POSITIONS)}</tr>
        <tr><td>RFI %</td>{rfi_row}</tr>
        <tr><td class="ss">amostra</td>{rfi_ss}</tr>
        <tr><td>Flat % (vs raise)</td>{flat_row}</tr>
        <tr><td class="ss">amostra</td>{flat_ss}</tr>
        <tr><td>3bet %</td>{threeb_row}</tr>
        <tr><td class="ss">amostra</td>{threeb_ss}</tr>
      </table>
    </div>
  </div>
  <div class="row">
    <div class="card box">
      <h2>Pos-Flop</h2>
      <table>
        <tr><th>Stat</th><th>%</th><th>Amostra</th></tr>
        <tr><td>C-bet Flop (PFA)</td><td>{P(s['cbet_f_did'], s['cbet_f_ch'])}</td><td class="ss">{s['cbet_f_did']}/{s['cbet_f_ch']}</td></tr>
        <tr><td>C-bet Turn</td><td>{P(s['cbet_t_did'], s['cbet_t_ch'])}</td><td class="ss">{s['cbet_t_did']}/{s['cbet_t_ch']}</td></tr>
        <tr><td>C-bet River</td><td>{P(s['cbet_r_did'], s['cbet_r_ch'])}</td><td class="ss">{s['cbet_r_did']}/{s['cbet_r_ch']}</td></tr>
        <tr><td>Fold to C-bet (Flop)</td><td>{P(s['face_cbet_fold'], s['face_cbet_ch'])}</td><td class="ss">{s['face_cbet_fold']}/{s['face_cbet_ch']}</td></tr>
      </table>
    </div>
    <div class="card box">
      <h2>Showdown</h2>
      <table>
        <tr><th>Stat</th><th>%</th><th>Amostra</th></tr>
        <tr><td>Saw Flop</td><td>{P(s['saw_flop'], n)}</td><td class="ss">{s['saw_flop']}/{n}</td></tr>
        <tr><td>WWSF</td><td>{P(s['wwsf'], s['saw_flop'])}</td><td class="ss">{s['wwsf']}/{s['saw_flop']}</td></tr>
        <tr><td>WTSD</td><td>{P(s['wtsd'], s['saw_flop'])}</td><td class="ss">{s['wtsd']}/{s['saw_flop']}</td></tr>
        <tr><td>W$SD</td><td>{P(s['won_sd'], s['wtsd'])}</td><td class="ss">{s['won_sd']}/{s['wtsd']}</td></tr>
      </table>
    </div>
    <div class="card box">
      <h2>BB Defense vs Steal</h2>
      <table>
        <tr><th>Stat</th><th>%</th><th>Amostra</th></tr>
        <tr><td>Fold</td><td>{P(bb_steal['fold'], bb_steal['ch'])}</td><td class="ss">{bb_steal['fold']}/{bb_steal['ch']}</td></tr>
        <tr><td>Call</td><td>{P(bb_steal['call'], bb_steal['ch'])}</td><td class="ss">{bb_steal['call']}/{bb_steal['ch']}</td></tr>
        <tr><td>3bet</td><td>{P(bb_steal['_3bet'], bb_steal['ch'])}</td><td class="ss">{bb_steal['_3bet']}/{bb_steal['ch']}</td></tr>
      </table>
    </div>
  </div>
</div>
"""

    return f"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><title>HUD — {label}</title>
<style>
  body{{background:#1a1a1a;color:#dcdcdc;font-family:'Segoe UI',Arial,sans-serif;margin:0;padding:20px}}
  h1{{color:#f0c419;text-align:center;margin:0 0 8px 0;font-size:22px}}
  h1 .hands{{color:#9bc1ff;font-size:14px;margin-left:10px;font-weight:400}}
  h2{{color:#9bc1ff;font-size:13px;margin:0 0 10px 0;border-bottom:1px solid #333;padding-bottom:6px;text-transform:uppercase;letter-spacing:0.5px}}
  .hud{{max-width:1280px;margin:0 auto}}
  .row{{display:flex;gap:14px;margin-top:14px;flex-wrap:wrap}}
  .card{{background:#222;border:1px solid #2e2e2e;border-radius:8px;padding:14px;flex:1;min-width:300px}}
  .card.wide{{flex:2;min-width:540px}}
  table{{width:100%;border-collapse:collapse;font-size:12.5px}}
  th{{color:#888;font-weight:500;text-transform:uppercase;letter-spacing:.4px;font-size:11px}}
  td,th{{padding:5px 8px;border-bottom:1px solid #2a2a2a;text-align:center}}
  table.kv td:first-child{{text-align:left;color:#aaa}}
  table.kv td:last-child{{color:#f0c419;font-weight:600}}
  table.pos td:first-child,table.pos th:first-child{{text-align:left;color:#aaa}}
  td.ss,.ss{{color:#666;font-size:11px;font-style:italic}}
</style></head><body>
{body}
</body></html>"""


def threeb_total_did(threeb): return sum(d["did"] for d in threeb.values())
def threeb_total_ch(threeb):  return sum(d["ch"]  for d in threeb.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="Pasta com XMLs")
    ap.add_argument("--hero", default=None, help="Nome do hero (default: auto-detecta)")
    ap.add_argument("--output", "-o", default="hud.html")
    ap.add_argument("--label", default=None, help="Titulo no topo do HUD")
    args = ap.parse_args()
    label = args.label or os.path.basename(os.path.normpath(args.folder)) or "Hands"
    agg = aggregate(args.folder, args.hero)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(render_html(label.upper(), agg))
    s = agg["stats"]
    print(f"{label}: n={s['n']}  VPIP={pct(s['vpip'], s['n']):.1f}  PFR={pct(s['pfr'], s['n']):.1f}")
    print(f"-> {args.output}")


if __name__ == "__main__":
    main()
