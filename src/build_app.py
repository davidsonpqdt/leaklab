"""Gera o app HTML single-file com dados embutidos.

Le pastas de XMLs (auto-classifica em vanilla/bounty_ko/mystery por nome do
torneio), parseia todas as maos, carrega todos os ranges GTO da pasta
data/ranges/, e injeta tudo em uma copia de app_template.html.

Resultado: um unico arquivo .html que o usuario pode abrir no browser
sem precisar de servidor nem dos jsons separados.

Uso:
    python build_app.py /pasta/com/xmls --hero Noshovepls -o app.html
    python build_app.py data/samples -o app_demo.html
    python build_app.py /pasta1 /pasta2 /pasta3 -o app.html   # multiplas pastas
"""
from __future__ import annotations
import os, sys, json, glob, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

sys.path.insert(0, HERE)
from parser import iter_hands_in_folder
from tournament_classifier import classify


def collect_hands(folders: list[str], hero: str | None) -> list[dict]:
    out = []
    for folder in folders:
        if not os.path.isdir(folder):
            print(f"  ! pasta nao encontrada: {folder}")
            continue
        n_before = len(out)
        for h in iter_hands_in_folder(folder, hero):
            # marca o dataset baseado no nome do torneio
            tname = h.get("tournament_name", "")
            buyin = h.get("buyin", "")
            tipo = classify(buyin, tname)
            ds_map = {"Bounty/KO": "bounty_ko", "Mystery": "mystery", "Vanilla": "vanilla"}
            h["__dataset"] = ds_map.get(tipo, "vanilla")
            out.append(h)
        print(f"  + {folder}: {len(out) - n_before} maos")
    return out


def collect_ranges(ranges_dir: str) -> list[dict]:
    """Coleta ranges recursivamente. Ignora arquivos que comecem com `_`
    (manifests, scripts auxiliares como _index.json)."""
    out = []
    seen_ids = set()
    if not os.path.isdir(ranges_dir):
        return out
    # Walk recursivo
    for root, _, files in os.walk(ranges_dir):
        for fname in sorted(files):
            if fname.startswith("_") or not fname.endswith(".json"):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    r = json.load(fh)
                rid = r.get("id")
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    out.append(r)
                    rel = os.path.relpath(path, ranges_dir)
                    print(f"  + range: {rid}  ({rel})")
            except Exception as e:
                print(f"  ! falha em {path}: {e}")
    return out


def build(folders: list[str], hero: str | None, output: str,
          ranges_dir: str | None = None, template_path: str | None = None,
          benchmarks_path: str | None = None) -> None:
    template_path = template_path or os.path.join(HERE, "leaklab.html")
    ranges_dir = ranges_dir or os.path.join(ROOT, "data", "ranges")
    benchmarks_path = benchmarks_path or os.path.join(ROOT, "data", "benchmarks_default.json")

    print("Lendo template:", template_path)
    with open(template_path, "r", encoding="utf-8") as fh:
        tpl = fh.read()

    print("Coletando maos:")
    hands = collect_hands(folders, hero)
    print(f"  total: {len(hands)} maos")

    print("Coletando ranges GTO:")
    ranges = collect_ranges(ranges_dir)
    print(f"  total: {len(ranges)} ranges")

    benchmarks = None
    if os.path.exists(benchmarks_path):
        with open(benchmarks_path, "r", encoding="utf-8") as fh:
            benchmarks = json.load(fh)
        print(f"Benchmarks: {os.path.basename(benchmarks_path)}")

    # injeta os dados antes do init
    inject = (
        "window.__BAKED_HANDS__ = " + json.dumps(hands, ensure_ascii=False) + ";\n"
        "window.__BAKED_RANGES__ = " + json.dumps(ranges, ensure_ascii=False) + ";\n"
        "window.__BAKED_BENCHMARKS__ = " + json.dumps(benchmarks, ensure_ascii=False) + ";\n"
    )
    # marcador no leaklab.html: "// ===== Init ====="
    marker = "// ===== Init ====="
    if marker in tpl:
        tpl = tpl.replace(marker, inject + marker)
    else:
        tpl = tpl.replace("</script>", inject + "</script>", 1)

    with open(output, "w", encoding="utf-8") as fh:
        fh.write(tpl)
    size_mb = os.path.getsize(output) / 1024 / 1024
    print(f"\n=> {output}  ({size_mb:.2f} MB)")
    print(f"   Abra no navegador: file:///{os.path.abspath(output).replace(os.sep, '/')}")


def main():
    ap = argparse.ArgumentParser(description="Gera app HTML single-file com dados embutidos.")
    ap.add_argument("folders", nargs="+", help="Pasta(s) com .xml (pode passar varias)")
    ap.add_argument("--hero", default=None, help="Nome do hero (default: auto-detecta)")
    ap.add_argument("--output", "-o", default="app.html", help="Caminho do HTML gerado")
    ap.add_argument("--ranges-dir", default=None, help="Pasta com ranges GTO (default: data/ranges/)")
    ap.add_argument("--template", default=None, help="Path para template HTML alternativo (default: leaklab.html)")
    ap.add_argument("--benchmarks", default=None, help="Path para benchmarks JSON (default: data/benchmarks_default.json)")
    args = ap.parse_args()
    build(args.folders, args.hero, args.output, args.ranges_dir, args.template, args.benchmarks)


if __name__ == "__main__":
    main()
