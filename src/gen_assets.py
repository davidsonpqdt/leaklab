"""Gera assets de SEO/share/PWA: og-image.png, favicon PNGs (16/32/180).

Roda manualmente quando quiser regenerar:
    python src/gen_assets.py

Os arquivos saem em docs/.
"""
from __future__ import annotations
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
ICONS_DIR = os.path.join(DOCS, "icons")

# Brand colors
BG_DARK = (13, 13, 15)
BG_DARKER = (10, 10, 12)
ACCENT = (45, 212, 191)         # turquesa
ACCENT_2 = (240, 196, 25)       # gold
GOOD = (93, 214, 132)
BAD = (237, 106, 106)
WARN = (245, 193, 74)
FG = (230, 230, 232)
FG_DIM = (184, 184, 189)


def _try_font(names: list[str], size: int):
    """Tenta carregar a 1ª fonte da lista que existir; cai pro default."""
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def make_favicon(size: int) -> Image.Image:
    """Favicon: círculo de pôquer com gradiente + miolo vermelho (mesmo conceito do SVG)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Background com cantos arredondados (rounded square)
    radius = int(size * 0.18)
    d.rounded_rectangle([0, 0, size-1, size-1], radius=radius, fill=BG_DARKER)
    # Anel externo turquesa
    margin1 = int(size * 0.16)
    d.ellipse([margin1, margin1, size-margin1, size-margin1],
              outline=ACCENT, width=max(1, int(size * 0.04)))
    # Anel interno gold
    margin2 = int(size * 0.30)
    d.ellipse([margin2, margin2, size-margin2, size-margin2],
              outline=ACCENT_2, width=max(1, int(size * 0.03)))
    # Miolo vermelho
    margin3 = int(size * 0.42)
    d.ellipse([margin3, margin3, size-margin3, size-margin3], fill=BAD)
    return img


def make_og_image() -> Image.Image:
    """OG image 1200x630 — capa pra share em WhatsApp/Telegram/Discord/Twitter."""
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BG_DARKER)
    d = ImageDraw.Draw(img)

    # Gradient fake (linhas horizontais com interp manual)
    for y in range(H):
        t = y / H
        r = int(BG_DARKER[0] + (BG_DARK[0] - BG_DARKER[0]) * t)
        g = int(BG_DARKER[1] + (BG_DARK[1] - BG_DARKER[1]) * t)
        b = int(BG_DARKER[2] + (BG_DARK[2] - BG_DARKER[2]) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # Glow turquesa no canto sup-esquerdo (radial fake)
    glow_r = 350
    for r in range(glow_r, 0, -10):
        alpha = int(40 * (1 - r / glow_r))
        if alpha <= 0:
            continue
        gx, gy = 0, 0
        d.ellipse([gx - r, gy - r, gx + r, gy + r],
                  fill=(min(255, BG_DARK[0] + ACCENT[0] * alpha // 255),
                        min(255, BG_DARK[1] + ACCENT[1] * alpha // 255),
                        min(255, BG_DARK[2] + ACCENT[2] * alpha // 255)))

    # Layout: matriz menor, mais pro canto direito; texto ganha espaço.
    # Matriz 13x13 — cell 24px, total ~338px (cabe em 380px da direita)
    grid_cell = 24
    grid_gap = 2
    grid_w = 13 * (grid_cell + grid_gap) - grid_gap
    grid_h = grid_w
    grid_x = W - grid_w - 60        # 60px de margem direita
    grid_y = (H - grid_h) // 2 - 20

    # Largura disponível pra texto (esquerda da matriz com 50px de gap)
    text_max_w = grid_x - 60 - 70   # margem esquerda 70 + gap 50

    # Texto
    font_brand = _try_font(["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"], 120)
    font_body = _try_font(["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"], 42)
    font_tag = _try_font(["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"], 28)
    font_meta = _try_font(["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"], 22)
    font_url = _try_font(["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"], 22)

    # LeakLab (brand)
    d.text((70, 90), "LeakLab", font=font_brand, fill=ACCENT)
    # Tagline em 2 linhas pra caber
    d.text((75, 240), "Quiz GTO + HUD", font=font_body, fill=FG)
    d.text((75, 290), "Análise de Leaks", font=font_body, fill=FG)
    d.text((75, 355), "Pôquer MTT · PT-BR", font=font_tag, fill=FG_DIM)

    # 3 tags compactas (sem ✓ — bolinha custom em vez do glyph que pode faltar)
    tags = [("Grátis", GOOD), ("Sem instalação", ACCENT), ("Privacidade total", ACCENT_2)]
    x = 75
    for txt, col in tags:
        bbox = d.textbbox((0, 0), txt, font=font_meta)
        tw = bbox[2] - bbox[0]
        # Bolinha colorida + texto, agrupados num "chip"
        chip_w = tw + 38
        d.rounded_rectangle([x, 425, x + chip_w, 465], radius=10,
                            outline=col, width=2)
        # Bolinha
        d.ellipse([x + 12, 437, x + 24, 449], fill=col)
        d.text((x + 30, 432), txt, font=font_meta, fill=col)
        x += chip_w + 14
        if x > text_max_w + 70:
            break  # safety

    # URL no rodapé
    d.text((75, 540), "leaklab.pokermtts.com.br", font=font_url, fill=FG_DIM)

    # Matriz 13x13 simulada (visual)
    raises = [(0, 0), (0, 1), (0, 2), (0, 3), (1, 1), (1, 2), (2, 2),
              (3, 3), (4, 4), (5, 5), (6, 6),
              (1, 0), (2, 0), (3, 0), (2, 1), (3, 1)]
    mixed = [(4, 0), (5, 0), (6, 0), (3, 2), (4, 2), (4, 1), (5, 1)]
    for i in range(13):
        for j in range(13):
            cx = grid_x + j * (grid_cell + grid_gap)
            cy = grid_y + i * (grid_cell + grid_gap)
            color = (35, 35, 42)  # default empty
            if (i, j) in raises:
                color = ACCENT
            elif (i, j) in mixed:
                color = ACCENT_2
            d.rounded_rectangle([cx, cy, cx + grid_cell, cy + grid_cell], radius=3, fill=color)

    # Label "Matriz GTO" abaixo do grid
    label_y = grid_y + grid_h + 14
    d.text((grid_x, label_y), "Matriz GTO 13x13", font=font_meta, fill=FG_DIM)

    return img


def main():
    os.makedirs(ICONS_DIR, exist_ok=True)

    # Favicons
    for sz, name in [(16, "icon-16.png"), (32, "icon-32.png"), (180, "apple-touch-icon.png")]:
        img = make_favicon(sz)
        out = os.path.join(ICONS_DIR, name)
        img.save(out, "PNG")
        print(f"  + {out} ({sz}x{sz})")

    # OG image
    og = make_og_image()
    out = os.path.join(DOCS, "og-image.png")
    og.save(out, "PNG", optimize=True)
    print(f"  + {out} (1200x630)")
    print("\nDone.")


if __name__ == "__main__":
    main()
