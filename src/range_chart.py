"""Gera matriz 13x13 (range chart) a partir de maos filtradas.

Filtros:
    --position {EP,MP,HJ,CO,BTN,SB,BB}
    --villain-position {mesmo conjunto}
    --faced {unopened,limped,raised,3bet,4bet,5bet+}
    --action {fold,call,raise,check}
    --min-bb / --max-bb
    --gto path/to/range.json   (overlay; mostra mistakes em vermelho)

Uso:
    python range_chart.py /pasta/dos/xmls \\
        --position BTN --faced unopened --action fold --min-bb 30 \\
        --gto data/ranges/btn_30bb_unopened_chipev.json \\
        -o range_btn_fold_30bb.html
"""
from __future__ import annotations
import json, argparse
from collections import defaultdict

from parser import iter_hands_in_folder, RANKS, RANK_LABEL


def matrix_label(i: int, j: int) -> str:
    r1, r2 = RANKS[i], RANKS[j]
    if i == j: return RANK_LABEL[r1] + RANK_LABEL[r2]
    if j > i:  return RANK_LABEL[r1] + RANK_LABEL[r2] + "s"   # triangulo superior
    return RANK_LABEL[r2] + RANK_LABEL[r1] + "o"              # triangulo inferior


def build_chart(folders: list[str], hero: str | None, filt: dict) -> tuple[dict[str, int], int]:
    counts: dict[str, int] = defaultdict(int)
    total = 0
    for folder in folders:
        for h in iter_hands_in_folder(folder, hero):
            if filt.get("position") and h["pos"] != filt["position"]: continue
            if filt.get("villain_position") and h["villain_pos"] != filt["villain_position"]: continue
            if filt.get("faced") and h["faced"] != filt["faced"]: continue
            if filt.get("action") and h["hero_action"] != filt["action"]: continue
            if filt.get("min_bb") is not None and h["stack_bb"] < filt["min_bb"]: continue
            if filt.get("max_bb") is not None and h["stack_bb"] > filt["max_bb"]: continue
            counts[h["hero_cards_label"]] += 1
            total += 1
    return counts, total


def load_gto_range(path: str) -> set[str]:
    """Carrega range GTO e retorna o conjunto de labels que GTO joga (raise/open/allin)."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    open_hands = set()
    for label, info in data.get("hands", {}).items():
        for k, v in info.items():
            if (k.startswith("raise") or k in ("open", "allin", "all-in", "shove")) \
                    and isinstance(v, (int, float)) and v > 0:
                open_hands.add(label)
                break
    return open_hands


def render(counts: dict[str, int], total: int, title: str, filters_text: str,
           gto_open: set[str] | None = None, action_label: str = "fold") -> str:
    cells = []
    for i in range(13):
        for j in range(13):
            lbl = matrix_label(i, j)
            cells.append((lbl, counts.get(lbl, 0)))
    max_count = max([c for _, c in cells] + [1])
    mistakes = sum(c for lbl, c in cells if c > 0 and gto_open and lbl in gto_open) if gto_open else 0
    correct = sum(c for lbl, c in cells if c > 0 and (not gto_open or lbl not in gto_open)) if gto_open else 0

    def cell_html(lbl: str, n: int) -> str:
        in_gto = bool(gto_open and lbl in gto_open)
        if n == 0:
            cls = "c empty gto-open" if in_gto else "c empty"
            return f'<div class="{cls}"><div class="lbl">{lbl}</div></div>'
        intensity = 0.30 + 0.70 * (n / max_count)
        if gto_open is None:
            bg = f"rgba(122,162,90,{intensity:.2f})"
            cls = "c filled"
        elif in_gto:
            bg = f"rgba(216,89,89,{intensity:.2f})"
            cls = "c filled mistake"
        else:
            bg = f"rgba(122,162,90,{intensity:.2f})"
            cls = "c filled correct"
        return f'<div class="{cls}" style="background:{bg}"><div class="lbl">{lbl}</div><div class="cnt">{n}</div></div>'

    grid = "".join(cell_html(lbl, n) for lbl, n in cells)
    totals_html = ""
    if gto_open:
        if action_label == "fold":
            mistake_caption = "Folds que <b>deveriam ter sido open</b> (GTO)"
            correct_caption = "Folds corretos"
            pct_caption = "% maos foldadas que eram opens"
        else:
            mistake_caption = f"{action_label.capitalize()}s em maos que GTO joga"
            correct_caption = f"{action_label.capitalize()}s em maos que GTO foldaria"
            pct_caption = f"% {action_label}s coincidentes com range GTO"
        totals_html = f"""
<div class="totals">
  <div class="stat"><div class="v">{total}</div><div class="l">Total {action_label}s</div></div>
  <div class="stat mistake"><div class="v">{mistakes}</div><div class="l">{mistake_caption}</div></div>
  <div class="stat correct"><div class="v">{correct}</div><div class="l">{correct_caption}</div></div>
  <div class="stat"><div class="v">{(100.0*mistakes/total if total else 0):.1f}%</div><div class="l">{pct_caption}</div></div>
</div>"""

    return f"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><title>{title}</title>
<style>
  body{{background:#1a1a1a;color:#dcdcdc;font-family:'Segoe UI',Arial,sans-serif;margin:0;padding:20px}}
  h1{{color:#f0c419;margin:0 0 6px 0;font-size:20px}}
  .meta{{color:#9bc1ff;font-size:13px;margin-bottom:14px}}
  .meta .pill{{display:inline-block;background:#3a4424;color:#cfdba0;padding:3px 10px;border-radius:14px;margin-right:6px;font-size:12px}}
  .totals{{display:flex;gap:16px;margin:8px 0 14px 0;flex-wrap:wrap}}
  .stat{{background:#222;border:1px solid #2a2a2a;border-radius:8px;padding:10px 14px}}
  .stat .v{{color:#f0c419;font-weight:700;font-size:22px}}
  .stat.mistake .v{{color:#e07a7a}}
  .stat.correct .v{{color:#9bd47a}}
  .stat .l{{color:#9bc1ff;font-size:12px;margin-top:2px}}
  .grid{{display:grid;grid-template-columns:repeat(13,minmax(54px,1fr));gap:2px;max-width:980px}}
  .c{{aspect-ratio:1/1;border-radius:3px;background:#222;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:12px;border:1px solid #2a2a2a}}
  .c.empty{{color:#5a5a5a}}
  .c.empty.gto-open{{background:repeating-linear-gradient(45deg,#222,#222 4px,#2a2418 4px,#2a2418 8px);color:#7a6a3a}}
  .c.filled{{color:#fff}}
  .c.mistake{{outline:1px solid #d85959}}
  .c .lbl{{font-weight:600;letter-spacing:.5px}}
  .c .cnt{{font-size:13px;font-weight:700;color:#fffbe0}}
</style></head><body>
<h1>{title}</h1>
<div class="meta">{filters_text}</div>
{totals_html}
<div class="grid">{grid}</div>
</body></html>"""


def filters_to_pills(f: dict) -> str:
    parts = []
    for k, label_fn in (
        ("position", lambda v: f"Posicao: {v}"),
        ("villain_position", lambda v: f"Posicao Vilao: {v}"),
        ("faced", lambda v: f"Faced: {v}"),
        ("action", lambda v: f"Preflop: {v}"),
    ):
        if f.get(k): parts.append(label_fn(f[k]))
    if f.get("min_bb") is not None and f.get("max_bb") is not None:
        parts.append(f"{f['min_bb']} <= Stack <= {f['max_bb']} BB")
    elif f.get("min_bb") is not None:
        parts.append(f"{f['min_bb']} <= Stack")
    elif f.get("max_bb") is not None:
        parts.append(f"Stack <= {f['max_bb']} BB")
    return "".join(f'<span class="pill">{p}</span>' for p in parts) or "(sem filtros)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="+", help="Uma ou mais pastas com .xml")
    ap.add_argument("--hero", default=None, help="Nome do hero (default: auto-detecta)")
    ap.add_argument("--position", choices=["EP","MP","HJ","CO","BTN","SB","BB"])
    ap.add_argument("--villain-position", dest="villain_position", choices=["EP","MP","HJ","CO","BTN","SB","BB"])
    ap.add_argument("--faced", choices=["unopened","limped","raised","3bet","4bet","5bet+"])
    ap.add_argument("--action", choices=["fold","call","raise","check"])
    ap.add_argument("--min-bb", type=float, dest="min_bb")
    ap.add_argument("--max-bb", type=float, dest="max_bb")
    ap.add_argument("--gto", help="Path para range JSON GTO (overlay com mistakes)")
    ap.add_argument("--output", "-o", default="range.html")
    ap.add_argument("--title", default="Hand Range")
    args = ap.parse_args()

    filt = {k: getattr(args, k) for k in
            ("position", "villain_position", "faced", "action", "min_bb", "max_bb")}
    counts, total = build_chart(args.folders, args.hero, filt)
    gto = load_gto_range(args.gto) if args.gto else None
    html = render(counts, total, args.title, filters_to_pills(filt), gto,
                  action_label=(args.action or "match"))
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"{total} maos correspondem.  -> {args.output}")
    if gto:
        mistakes = sum(c for lbl, c in counts.items() if lbl in gto)
        print(f"Mistakes (action {args.action} no range GTO): {mistakes}")


if __name__ == "__main__":
    main()
