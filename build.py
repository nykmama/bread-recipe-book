"""
パンレシピ集 PDFビルドスクリプト
使い方: python build.py
出力:   output/bread_recipes.pdf
"""
import glob, json, math, os, re, shutil, tempfile
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from PIL import Image

# ── フォント設定（Windowsの場合） ──────────────────────────
import platform
if platform.system() == 'Windows':
    FONT_PATH = 'C:/Windows/Fonts/meiryo.ttc'
    if not os.path.exists(FONT_PATH):
        FONT_PATH = 'C:/Windows/Fonts/msgothic.ttc'
else:
    FONT_PATH = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'

pdfmetrics.registerFont(TTFont('F', FONT_PATH))
pdfmetrics.registerFont(TTFont('FB', FONT_PATH))

# ── ページ設定 ───────────────────────────────────────────
W, H = A4
ML = MR = 18 * mm
MT = MB = 16 * mm
CW = W - ML - MR
FOOTER_H = 11 * mm
CONTENT_BOTTOM = FOOTER_H + 6 * mm

# ── カラーパレット ────────────────────────────────────────
PAPER  = colors.HexColor('#FFFDF8')
PAPER2 = colors.HexColor('#F7F3EA')
PAPER3 = colors.HexColor('#EFE9DA')
INK    = colors.HexColor('#2B2620')
INK2   = colors.HexColor('#5C5448')
INK3   = colors.HexColor('#8A8070')
RULE   = colors.HexColor('#D8D0BE')
ACCENT = colors.HexColor('#A1664F')
GOLD   = colors.HexColor('#B8860B')
GREEN  = colors.HexColor('#3A5A2A')
GREEN2 = colors.HexColor('#EAF1E6')

EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF"
    "\U0001F000-\U0001F0FF" "\u2190-\u21FF" "\u2700-\u27BF" "]+",
    flags=re.UNICODE)

def clean(text):
    if not text: return ''
    return re.sub(r'\s{2,}', ' ', EMOJI_RE.sub('', text)).strip()

def wrap(text, max_w, font='F', size=9):
    lines, cur = [], ''
    for ch in text:
        if stringWidth(cur+ch, font, size) <= max_w:
            cur += ch
        else:
            lines.append(cur); cur = ch
    if cur: lines.append(cur)
    return lines or ['']

SCALE_OPTIONS = [
    (9, 8, 4.0*mm, 8), (8.5, 7.5, 3.6*mm, 7.5),
    (8, 7, 3.3*mm, 7),  (7.5, 6.5, 3.0*mm, 6.5),
    (7, 6, 2.7*mm, 6),  (6.5, 5.5, 2.5*mm, 6),
    (6, 5, 2.2*mm, 5.5),(5.5, 4.5, 2.0*mm, 5),
]

def measure_steps(steps, pcw, name_sz, det_sz, line_h):
    h = 6*mm
    for s in steps:
        lines = wrap(clean(s['detail']), pcw-11*mm, 'F', det_sz)
        h += 5.0*mm + len(lines)*line_h + (line_h if s.get('time') else 0) + 2.2*mm
    return h

def pick_scale(steps, avail_h):
    if not steps: return SCALE_OPTIONS[0], True
    mid = math.ceil(len(steps)/2)
    subset = steps[:mid]
    pcw = CW/2 - 5*mm
    for opt in SCALE_OPTIONS:
        ns, ds, lh, _ = opt
        if measure_steps(subset, pcw, ns, ds, lh) <= avail_h:
            return opt, True
    return SCALE_OPTIONS[-1], False

def draw_footer(cv, data, label=''):
    cv.setFillColor(PAPER2)
    cv.rect(0, 0, W, FOOTER_H, fill=1, stroke=0)
    cv.setStrokeColor(RULE); cv.setLineWidth(0.6)
    cv.line(0, FOOTER_H, W, FOOTER_H)
    cv.setFont('F', 8); cv.setFillColor(INK3)
    txt = f"NYKMAMA BREAD RECIPE BOOK  |  {data['cat_name']}"
    if label: txt += f'  ({label})'
    cv.drawString(ML, 4*mm, txt)
    cv.drawRightString(ML+CW, 4*mm, f"{data['no']}  |  2026")

def draw_photo(cv, data, x, y, w, h):
    pf = data.get('photo_file')
    path = os.path.join('photos', pf) if pf else None
    if path and os.path.exists(path):
        try:
            img = Image.open(path).convert('RGB')
            if data.get('photo_rotated'):
                img = img.rotate(-90, expand=True)
            iw, ih = img.size
            side = min(iw, ih)
            img = img.crop(((iw-side)//2,(ih-side)//2,(iw-side)//2+side,(ih-side)//2+side))
            tmp = os.path.join(tempfile.gettempdir(), '_recipe_photo.jpg')
            img.save(tmp, format='JPEG', quality=88)
            cv.drawImage(tmp, x, y, width=w, height=h, preserveAspectRatio=True, anchor='c')
            cv.setStrokeColor(RULE); cv.setLineWidth(0.5)
            cv.rect(x, y, w, h, fill=0, stroke=1)
            return
        except Exception as e:
            print(f"  写真エラー {pf}: {e}")
    # プレースホルダー
    cv.setFillColor(PAPER3); cv.setStrokeColor(RULE); cv.setLineWidth(0.5)
    cv.roundRect(x, y, w, h, 2*mm, fill=1, stroke=1)
    cv.setFont('F', 8); cv.setFillColor(INK3)
    cv.drawCentredString(x+w/2, y+h*0.45, '写真貼付エリア')

def draw_sec(cv, x, y, text, color, size=10):
    cv.setFillColor(color)
    cv.rect(x, y-2*mm, 2.2, 11, fill=1, stroke=0)
    cv.setFont('FB', size); cv.setFillColor(color)
    cv.drawString(x+4*mm, y, text)

def draw_ing(cv, ing_rows, x, y, w):
    cy = y
    draw_sec(cv, x, cy, '配合（ベーカーズ%）', ACCENT)
    cy -= 7*mm
    cv.setFillColor(PAPER3)
    cv.rect(x, cy-3.5*mm+1.5*mm, w, 5*mm, fill=1, stroke=0)
    cv.setFont('F', 8); cv.setFillColor(INK3)
    cv.drawString(x+2*mm, cy, '材料名')
    cv.drawRightString(x+w-22*mm, cy, 'BP%')
    cv.drawRightString(x+w-2*mm, cy, '重量')
    cv.setStrokeColor(RULE); cv.setLineWidth(0.5)
    cv.line(x, cy-1.5*mm, x+w, cy-1.5*mm)
    cy -= 5.5*mm
    for row in ing_rows:
        kind = row['kind']
        if kind in ('group','sep'):
            cv.setFont('F', 7.5); cv.setFillColor(INK3)
            cv.drawString(x+2*mm, cy, clean(row['name'])); cy -= 4.5*mm; continue
        rh = 5.2*mm
        if kind == 'total':
            cv.setFillColor(PAPER2)
            cv.rect(x, cy-rh+2*mm, w, rh, fill=1, stroke=0)
            cv.setFont('FB', 8.5); cv.setFillColor(INK)
        else:
            cv.setFont('F', 8.5); cv.setFillColor(INK)
        nm = clean(row['name'])
        max_w = w - 44*mm
        if stringWidth(nm, 'F', 8.5) > max_w:
            while stringWidth(nm+'…', 'F', 8.5) > max_w and len(nm) > 1:
                nm = nm[:-1]
            nm += '…'
        cv.drawString(x+2*mm, cy, nm)
        cv.drawRightString(x+w-22*mm, cy, row.get('bp',''))
        cv.drawRightString(x+w-2*mm, cy, row.get('weight',''))
        if kind != 'total':
            cv.setDash(1,2); cv.setStrokeColor(RULE); cv.setLineWidth(0.4)
            cv.line(x, cy-1.5*mm, x+w, cy-1.5*mm); cv.setDash()
        cy -= rh
    return cy

def draw_points_memo(cv, points, memo, x, y, w):
    cr = y
    draw_sec(cv, x, cr, 'ポイント', GOLD); cr -= 7*mm
    for pt in points:
        lines = wrap(clean(pt), w-7*mm, 'F', 8.5)
        cv.setFillColor(GOLD)
        cv.circle(x+1.8*mm, cr+1.8*mm, 1.4, fill=1, stroke=0)
        cv.setFont('F', 8.5); cv.setFillColor(INK2)
        for j, ln in enumerate(lines):
            cv.drawString(x+5*mm, cr-j*4.3*mm, ln)
        cr -= 4.3*mm*len(lines) + 2.2*mm
    cr -= 2*mm
    draw_sec(cv, x, cr, 'メモ', GREEN); cr -= 7*mm
    memo_lines = wrap(clean(memo), w-6*mm, 'F', 8) if memo else []
    memo_h = max(14*mm, 5*mm + len(memo_lines)*4.3*mm)
    cv.setFillColor(PAPER2); cv.setStrokeColor(RULE); cv.setLineWidth(0.5)
    cv.roundRect(x, cr-memo_h+4*mm, w, memo_h, 2*mm, fill=1, stroke=1)
    cv.setFont('F', 8); cv.setFillColor(INK2)
    my = cr - 1*mm
    for ln in memo_lines:
        cv.drawString(x+3*mm, my, ln); my -= 4.3*mm
    return cr - memo_h + 4*mm

def draw_sake(cv, sake_callout, x, y, w):
    if not sake_callout: return y
    title = clean(sake_callout['title'])
    items = sake_callout['items']
    h = 16*mm
    cv.setFillColor(GREEN2); cv.setStrokeColor(colors.HexColor('#A5C8A0')); cv.setLineWidth(0.6)
    cv.roundRect(x, y-h, w, h, 2*mm, fill=1, stroke=1)
    cv.setFont('FB', 9.5); cv.setFillColor(GREEN)
    cv.drawString(x+4*mm, y-6*mm, title)
    gw = w / max(len(items), 1)
    for i, item in enumerate(items):
        gx = x + i*gw + 4*mm
        cv.setFont('F', 8.5); cv.setFillColor(INK2)
        lbl = clean(item['label']) + '  '
        cv.drawString(gx, y-12*mm, lbl)
        lw = stringWidth(lbl, 'F', 8.5)
        cv.setFont('FB', 8.5); cv.setFillColor(GREEN)
        cv.drawString(gx+lw, y-12*mm, clean(item['val']))
    return y - h

def draw_steps_cols(cv, steps, top_y, opt):
    ns, ds, lh, nc = opt
    mid = math.ceil(len(steps)/2)
    pcw = CW/2 - 5*mm
    cols = [ML, ML+CW/2+5*mm]
    r = 3.6*mm if nc <= 7 else 4*mm

    def draw_col(subset, cx, sy):
        cy = sy - 6*mm
        for si, s in enumerate(subset):
            cv.setFillColor(ACCENT if s['num'] != '前' else colors.HexColor('#888888'))
            cv.circle(cx+r, cy-r, r, fill=1, stroke=0)
            cv.setFont('FB', nc if len(s['num'])<=2 else nc-1.5)
            cv.setFillColor(colors.white)
            cv.drawCentredString(cx+r, cy-r-1.2, s['num'])
            tx = cx+r*2+3*mm
            cv.setFont('FB', ns); cv.setFillColor(INK)
            cv.drawString(tx, cy-1*mm, clean(s['name']))
            consumed = 5.0*mm
            for ln in wrap(clean(s['detail']), pcw-(r*2+3*mm), 'F', ds):
                cv.setFont('F', ds); cv.setFillColor(INK2)
                cv.drawString(tx, cy-consumed, ln); consumed += lh
            if s.get('time'):
                cv.setFont('F', ds-0.5); cv.setFillColor(INK3)
                cv.drawString(tx, cy-consumed, f"時間: {clean(s['time'])}"); consumed += lh
            if si < len(subset)-1:
                cv.setStrokeColor(RULE); cv.setLineWidth(0.5)
                lt = cy-r*2-1*mm; lb = cy-consumed-1*mm
                if lt > lb: cv.line(cx+r, lt, cx+r, lb)
            cy -= consumed + 2.2*mm
        return cy

    b1 = draw_col(steps[:mid], cols[0], top_y)
    b2 = draw_col(steps[mid:], cols[1], top_y)
    return min(b1, b2)

def draw_recipe_page(cv, data):
    cv.setFillColor(PAPER); cv.rect(0,0,W,H,fill=1,stroke=0)
    top = H - MT
    img_w, img_h = 52*mm, 42*mm
    text_w = CW - img_w - 6*mm

    # ヘッダー
    cv.setFont('F', 9); cv.setFillColor(INK3)
    cv.drawString(ML, top-6*mm, f"No. {data['no']}  |  ")
    cv.setFillColor(colors.HexColor(data['cat_color']))
    cv.drawString(ML+28*mm, top-6*mm, data['cat_name'])
    cv.setFont('FB', 18); cv.setFillColor(INK)
    name_lines = wrap(clean(data['name']), text_w, 'FB', 18)
    ny = top-15*mm
    for ln in name_lines[:2]:
        cv.drawString(ML, ny, ln); ny -= 7.5*mm
    cv.setFont('F', 9.5); cv.setFillColor(INK2)
    sub_lines = wrap(clean(data['sub']), text_w, 'F', 9.5)
    sy = ny-2*mm
    for ln in sub_lines[:2]:
        cv.drawString(ML, sy, ln); sy -= 5*mm

    draw_photo(cv, data, ML+text_w+6*mm, top-img_h, img_w, img_h)

    header_bottom = min(sy-3*mm, top-img_h-4*mm)
    cv.setStrokeColor(RULE); cv.setLineWidth(1.2)
    cv.line(ML, header_bottom, ML+CW, header_bottom)

    # メタ行
    meta_y = header_bottom - 13*mm
    bh = 11*mm
    items = data['meta_items']
    cwm = CW / max(len(items),1)
    for i, item in enumerate(items):
        bx = ML + i*cwm
        cv.setFillColor(PAPER2); cv.setStrokeColor(RULE); cv.setLineWidth(0.5)
        cv.rect(bx, meta_y, cwm, bh, fill=1, stroke=1)
        cv.setFont('F', 7.5); cv.setFillColor(INK3)
        cv.drawCentredString(bx+cwm/2, meta_y+7.5*mm, clean(item['label']))
        val = clean(item['val'])
        fs = 9.5 if len(val) <= 8 else 7.5
        cv.setFont('FB', fs); cv.setFillColor(INK)
        vlines = wrap(val, cwm-4*mm, 'FB', fs)
        if len(vlines) > 1:
            cv.drawCentredString(bx+cwm/2, meta_y+5.5*mm, vlines[0])
            cv.drawCentredString(bx+cwm/2, meta_y+2.2*mm, vlines[1])
        else:
            cv.drawCentredString(bx+cwm/2, meta_y+3.5*mm, val)

    col_top = meta_y - 7*mm
    hw = CW/2 - 5*mm
    ing_b = draw_ing(cv, data['ing_rows'], ML, col_top, hw)
    memo_b = draw_points_memo(cv, data['points'], data['memo'], ML+CW/2+5*mm, col_top, hw)
    two_col_b = min(ing_b, memo_b)

    sec_y = two_col_b - 6*mm
    if data.get('sake_callout'):
        sec_y = draw_sake(cv, data['sake_callout'], ML, sec_y, CW)
        sec_y -= 5*mm

    draw_sec(cv, ML, sec_y, '製造工程', colors.HexColor('#1A5276'))
    proc_top = sec_y - 8*mm
    avail_h = proc_top - CONTENT_BOTTOM
    steps = data['steps']
    opt, fits = pick_scale(steps, avail_h)
    if fits:
        draw_steps_cols(cv, steps, proc_top, opt)
        draw_footer(cv, data)
        return None
    else:
        n_fit = 1
        best_opt = SCALE_OPTIONS[-1]
        for n in range(len(steps), 0, -1):
            o, f = pick_scale(steps[:n], avail_h)
            if f: n_fit = n; best_opt = o; break
        draw_steps_cols(cv, steps[:n_fit], proc_top, best_opt)
        draw_footer(cv, data, '1/2')
        return steps[n_fit:]

def draw_continuation(cv, data, remaining):
    cv.setFillColor(PAPER); cv.rect(0,0,W,H,fill=1,stroke=0)
    top = H - MT
    cv.setFont('F', 9); cv.setFillColor(INK3)
    cv.drawString(ML, top-6*mm, f"No. {data['no']}  |  ")
    cv.setFillColor(colors.HexColor(data['cat_color']))
    cv.drawString(ML+28*mm, top-6*mm, data['cat_name'])
    cv.setFont('FB', 14); cv.setFillColor(INK)
    cv.drawString(ML, top-13*mm, clean(data['name'])+'（製造工程 つづき）')
    rule_y = top - 18*mm
    cv.setStrokeColor(RULE); cv.setLineWidth(1.2)
    cv.line(ML, rule_y, ML+CW, rule_y)
    sec_y = rule_y - 8*mm
    avail_h = sec_y - CONTENT_BOTTOM
    opt, _ = pick_scale(remaining, avail_h)
    draw_steps_cols(cv, remaining, sec_y, opt)
    draw_footer(cv, data, '2/2')

ICLOUD_DIR = os.path.join(os.path.expanduser('~'), 'iCloudDrive', 'recipe_book')

def build_index_html():
    recipe_files = sorted(glob.glob('recipes/*.json'))
    recipes = []
    for f in recipe_files:
        with open(f, encoding='utf-8') as fp:
            recipes.append(json.load(fp))
    recipes_json = json.dumps(recipes, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>NYKMAMAのパンレシピ</title>
<style>
  :root {{
    --bg: #faf8f5;
    --card-bg: #ffffff;
    --text: #2c2c2c;
    --sub: #777;
    --border: #e8e4de;
    --shadow: 0 2px 12px rgba(0,0,0,0.08);
    --radius: 16px;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding-bottom: env(safe-area-inset-bottom);
  }}
  header {{
    background: #fff;
    border-bottom: 1px solid var(--border);
    padding: 20px 20px 16px;
    padding-top: calc(20px + env(safe-area-inset-top));
    position: sticky;
    top: 0;
    z-index: 100;
  }}
  .header-row {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }}
  header h1 {{ font-size: 22px; font-weight: 700; letter-spacing: 0.02em; color: #3d2b1f; }}
  header p.subtitle {{ font-size: 12px; color: var(--sub); margin-top: 2px; }}
  .pdf-btn {{
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #3d2b1f;
    color: #fff;
    border: none;
    border-radius: 20px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 700;
    font-family: inherit;
    cursor: pointer;
    text-decoration: none;
    -webkit-tap-highlight-color: transparent;
    white-space: nowrap;
    margin-top: 2px;
  }}
  .pdf-btn:active {{ opacity: 0.8; }}
  .filter-wrap {{
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding: 12px 16px;
    display: flex;
    gap: 8px;
    background: #fff;
    border-bottom: 1px solid var(--border);
  }}
  .filter-wrap::-webkit-scrollbar {{ display: none; }}
  .filter-btn {{
    flex-shrink: 0;
    border: none;
    border-radius: 20px;
    padding: 7px 16px;
    font-size: 13px;
    font-family: inherit;
    font-weight: 600;
    cursor: pointer;
    background: #f0ede8;
    color: #555;
    transition: all 0.18s;
    -webkit-tap-highlight-color: transparent;
  }}
  .filter-btn.active {{ color: #fff; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    padding: 16px;
    max-width: 900px;
    margin: 0 auto;
  }}
  @media (min-width: 600px) {{ .grid {{ grid-template-columns: repeat(3, 1fr); }} }}
  @media (min-width: 900px) {{ .grid {{ grid-template-columns: repeat(4, 1fr); }} }}
  .card {{
    background: var(--card-bg);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow);
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: transform 0.15s, box-shadow 0.15s;
    border: 1px solid var(--border);
    display: block;
  }}
  .card:active {{ transform: scale(0.97); box-shadow: 0 1px 6px rgba(0,0,0,0.1); }}
  .card-photo {{ width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block; background: #f0ede8; }}
  .card-photo-placeholder {{
    width: 100%;
    aspect-ratio: 1/1;
    background: linear-gradient(135deg, #f5f0ea 0%, #ede8e0 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 36px;
  }}
  .card-body {{ padding: 10px 12px 12px; }}
  .card-cat {{
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    border-radius: 4px;
    padding: 2px 7px;
    color: #fff;
    margin-bottom: 5px;
  }}
  .card-name {{ font-size: 14px; font-weight: 700; line-height: 1.35; color: #2c2c2c; }}
  .card-sub {{
    font-size: 11px;
    color: var(--sub);
    margin-top: 4px;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}
  .card-meta {{ display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }}
  .card-tag {{ font-size: 10px; background: #f0ede8; color: #666; border-radius: 4px; padding: 2px 6px; }}
  .modal-overlay {{
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    z-index: 200;
    -webkit-backdrop-filter: blur(4px);
    backdrop-filter: blur(4px);
  }}
  .modal-overlay.open {{ display: flex; align-items: flex-end; }}
  @media (min-width: 600px) {{ .modal-overlay.open {{ align-items: center; justify-content: center; }} }}
  .modal {{
    background: #fff;
    border-radius: 24px 24px 0 0;
    width: 100%;
    max-height: 88vh;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: env(safe-area-inset-bottom);
    animation: slideUp 0.25s ease;
  }}
  @media (min-width: 600px) {{ .modal {{ border-radius: 24px; max-width: 540px; max-height: 85vh; }} }}
  @keyframes slideUp {{ from {{ transform: translateY(30px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
  .modal-handle {{ width: 36px; height: 4px; background: #ddd; border-radius: 2px; margin: 12px auto 0; }}
  .modal-photo {{ width: 100%; aspect-ratio: 4/3; object-fit: cover; }}
  .modal-photo-placeholder {{
    width: 100%;
    aspect-ratio: 4/3;
    background: linear-gradient(135deg, #f5f0ea 0%, #ede8e0 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 56px;
  }}
  .modal-content {{ padding: 20px 20px 32px; }}
  .modal-cat {{ display: inline-block; font-size: 11px; font-weight: 700; border-radius: 5px; padding: 3px 9px; color: #fff; margin-bottom: 8px; }}
  .modal-no {{ font-size: 11px; color: #aaa; margin-left: 8px; font-weight: 600; }}
  .modal-name {{ font-size: 22px; font-weight: 800; line-height: 1.3; color: #2c2c2c; margin-bottom: 4px; }}
  .modal-sub {{ font-size: 13px; color: var(--sub); margin-bottom: 16px; line-height: 1.5; }}
  .section-title {{
    font-size: 13px;
    font-weight: 700;
    color: #888;
    letter-spacing: 0.08em;
    margin: 20px 0 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
  }}
  .meta-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }}
  .meta-item {{ background: #faf8f5; border-radius: 10px; padding: 10px 12px; }}
  .meta-label {{ font-size: 10px; color: #aaa; font-weight: 600; }}
  .meta-val {{ font-size: 14px; font-weight: 700; color: #2c2c2c; margin-top: 2px; }}
  .ing-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .ing-group td {{ padding: 8px 0 2px; font-size: 11px; font-weight: 700; color: #aaa; border-bottom: 1px solid #f0ede8; }}
  .ing-normal td {{ padding: 7px 0; border-bottom: 1px solid #f5f3f0; vertical-align: top; }}
  .ing-name {{ color: #2c2c2c; }}
  .ing-bp {{ color: #aaa; font-size: 11px; text-align: right; padding-right: 8px; white-space: nowrap; }}
  .ing-weight {{ color: #2c2c2c; font-weight: 600; text-align: right; white-space: nowrap; }}
  .ing-total td {{ padding: 10px 0 4px; font-weight: 700; color: #2c2c2c; border-top: 2px solid var(--border); }}
  .steps-list {{ list-style: none; display: flex; flex-direction: column; gap: 12px; }}
  .step-item {{ display: flex; gap: 12px; align-items: flex-start; }}
  .step-num {{
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 800;
    color: #fff;
    flex-shrink: 0;
    margin-top: 1px;
  }}
  .step-body {{ flex: 1; }}
  .step-name {{ font-size: 14px; font-weight: 700; color: #2c2c2c; }}
  .step-detail {{ font-size: 13px; color: #555; line-height: 1.6; margin-top: 3px; }}
  .step-time {{ display: inline-block; font-size: 11px; background: #f0ede8; color: #888; border-radius: 4px; padding: 1px 7px; margin-top: 4px; font-weight: 600; }}
  .points-list {{ list-style: none; display: flex; flex-direction: column; gap: 8px; }}
  .point-item {{ display: flex; gap: 8px; font-size: 13px; line-height: 1.6; color: #444; align-items: flex-start; }}
  .point-item::before {{ content: '✓'; font-size: 12px; font-weight: 700; flex-shrink: 0; margin-top: 3px; }}
  .memo-box {{ background: #fdf9f4; border-left: 3px solid #d4a96a; border-radius: 0 10px 10px 0; padding: 12px 14px; font-size: 13px; color: #555; line-height: 1.7; }}
  .sake-box {{ background: #f0f7f0; border-radius: 12px; padding: 14px 16px; }}
  .sake-title {{ font-size: 13px; font-weight: 700; color: #2e7d32; margin-bottom: 8px; }}
  .sake-items {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .sake-item {{ font-size: 13px; }}
  .sake-item span {{ font-weight: 700; color: #2e7d32; }}
  .close-btn {{
    position: sticky;
    top: 12px;
    float: right;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: rgba(0,0,0,0.08);
    border: none;
    font-size: 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #555;
    margin: 12px 12px 0 0;
    -webkit-tap-highlight-color: transparent;
  }}
  .empty {{ text-align: center; padding: 60px 20px; color: var(--sub); font-size: 15px; grid-column: 1 / -1; }}
  /* パスワード画面 */
  .pw-overlay {{
    position: fixed;
    inset: 0;
    background: #faf8f5;
    z-index: 999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }}
  .pw-box {{
    background: #fff;
    border-radius: 24px;
    padding: 36px 28px;
    width: 100%;
    max-width: 340px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.10);
    text-align: center;
  }}
  .pw-icon {{ font-size: 48px; margin-bottom: 12px; }}
  .pw-title {{ font-size: 20px; font-weight: 800; color: #3d2b1f; margin-bottom: 4px; }}
  .pw-sub {{ font-size: 13px; color: var(--sub); margin-bottom: 24px; }}
  .pw-input {{
    width: 100%;
    border: 2px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    font-size: 18px;
    font-family: inherit;
    text-align: center;
    letter-spacing: 0.1em;
    outline: none;
    color: #2c2c2c;
    background: #faf8f5;
    transition: border-color 0.2s;
  }}
  .pw-input:focus {{ border-color: #3d2b1f; }}
  .pw-input.error {{ border-color: #e53935; animation: shake 0.3s; }}
  .pw-btn {{
    width: 100%;
    margin-top: 14px;
    background: #3d2b1f;
    color: #fff;
    border: none;
    border-radius: 12px;
    padding: 14px;
    font-size: 15px;
    font-weight: 700;
    font-family: inherit;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }}
  .pw-btn:active {{ opacity: 0.8; }}
  .pw-error {{ color: #e53935; font-size: 13px; margin-top: 10px; min-height: 18px; }}
  @keyframes shake {{
    0%,100% {{ transform: translateX(0); }}
    25% {{ transform: translateX(-8px); }}
    75% {{ transform: translateX(8px); }}
  }}
</style>
</head>
<body>
<div class="pw-overlay" id="pw-overlay">
  <div class="pw-box">
    <div class="pw-icon">🍞</div>
    <div class="pw-title">NYKMAMAのパンレシピ</div>
    <div class="pw-sub">パスワードを入力してください</div>
    <input class="pw-input" id="pw-input" type="password" placeholder="••••••••••••" maxlength="20">
    <button class="pw-btn" id="pw-btn">開く</button>
    <div class="pw-error" id="pw-error"></div>
  </div>
</div>
<header>
  <div class="header-row">
    <div>
      <h1>🍞 NYKMAMAのパンレシピ</h1>
      <p class="subtitle" id="count-label"></p>
    </div>
    <a class="pdf-btn" href="output/bread_recipes.pdf" download="パンレシピ集.pdf">📄 PDF</a>
  </div>
</header>
<div class="filter-wrap" id="filter-wrap"></div>
<div class="grid" id="grid"></div>
<div class="modal-overlay" id="modal-overlay">
  <div class="modal" id="modal">
    <div class="modal-handle"></div>
    <button class="close-btn" id="close-btn">✕</button>
    <div id="modal-inner"></div>
  </div>
</div>
<script>
const RECIPES = {recipes_json};
const CAT_EMOJI = {{'食パン':'🍞','ハード系':'🥖','惣菜パン':'🥗','菓子パン':'🍫','季節系':'🌸'}};
let currentCat = 'すべて';
function getCats() {{
  const seen = new Set(); const cats = ['すべて'];
  RECIPES.forEach(r => {{ if (!seen.has(r.cat_name)) {{ seen.add(r.cat_name); cats.push(r.cat_name); }} }});
  return cats;
}}
function filtered() {{ return currentCat === 'すべて' ? RECIPES : RECIPES.filter(r => r.cat_name === currentCat); }}
function photoPath(r) {{ return r.photo_file ? `photos/${{r.photo_file}}` : null; }}
function getCatColor(cat) {{ const r = RECIPES.find(x => x.cat_name === cat); return r ? r.cat_color : '#888'; }}
function renderFilters() {{
  const wrap = document.getElementById('filter-wrap');
  wrap.innerHTML = '';
  getCats().forEach(cat => {{
    const btn = document.createElement('button');
    btn.className = 'filter-btn' + (cat === currentCat ? ' active' : '');
    btn.textContent = cat === 'すべて' ? 'すべて' : (CAT_EMOJI[cat] || '') + ' ' + cat;
    if (cat === currentCat) btn.style.background = cat === 'すべて' ? '#3d2b1f' : getCatColor(cat);
    btn.addEventListener('click', () => {{ currentCat = cat; renderFilters(); renderGrid(); }});
    wrap.appendChild(btn);
  }});
}}
function renderGrid() {{
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  const list = filtered();
  document.getElementById('count-label').textContent = list.length + '品';
  if (!list.length) {{ grid.innerHTML = '<div class="empty">レシピが見つかりません</div>'; return; }}
  list.forEach(r => {{
    const card = document.createElement('div');
    card.className = 'card';
    const photo = photoPath(r);
    const photoHtml = photo
      ? `<img class="card-photo" src="${{photo}}" alt="${{r.name}}" loading="lazy" onerror="this.parentNode.innerHTML='<div class=\\"card-photo-placeholder\\">${{CAT_EMOJI[r.cat_name]||'🍞'}}</div>'">`
      : `<div class="card-photo-placeholder">${{CAT_EMOJI[r.cat_name]||'🍞'}}</div>`;
    const tags = r.meta_items.slice(0,2).map(m => `<span class="card-tag">${{m.val}}</span>`).join('');
    card.innerHTML = `${{photoHtml}}<div class="card-body"><span class="card-cat" style="background:${{r.cat_color}}">${{r.cat_name}}</span><div class="card-name">${{r.name}}</div><div class="card-sub">${{r.sub||''}}</div><div class="card-meta">${{tags}}</div></div>`;
    card.addEventListener('click', () => openModal(r));
    grid.appendChild(card);
  }});
}}
function openModal(r) {{
  const photo = photoPath(r);
  const photoHtml = photo
    ? `<img class="modal-photo" src="${{photo}}" alt="${{r.name}}" onerror="this.parentNode.innerHTML='<div class=\\"modal-photo-placeholder\\">${{CAT_EMOJI[r.cat_name]||'🍞'}}</div>'">`
    : `<div class="modal-photo-placeholder">${{CAT_EMOJI[r.cat_name]||'🍞'}}</div>`;
  const ingRows = (r.ing_rows||[]).map(row => {{
    if (row.kind==='group') return `<tr class="ing-group"><td colspan="3">${{row.name}}</td></tr>`;
    if (row.kind==='total') return `<tr class="ing-total"><td class="ing-name">${{row.name}}</td><td class="ing-bp"></td><td class="ing-weight">${{row.weight}}</td></tr>`;
    return `<tr class="ing-normal"><td class="ing-name">${{row.name}}</td><td class="ing-bp">${{row.bp!=='—'?'BP'+row.bp+'%':''}}</td><td class="ing-weight">${{row.weight}}</td></tr>`;
  }}).join('');
  const steps = (r.steps||[]).map(s => `<li class="step-item"><div class="step-num" style="background:${{r.cat_color}}">${{s.num}}</div><div class="step-body"><div class="step-name">${{s.name}}</div><div class="step-detail">${{s.detail}}</div>${{s.time?`<span class="step-time">⏱ ${{s.time}}</span>`:''}}</div></li>`).join('');
  const points = (r.points||[]).map(p => `<li class="point-item">${{p}}</li>`).join('');
  const memo = r.memo ? `<div class="section-title">メモ</div><div class="memo-box">${{r.memo}}</div>` : '';
  const meta = (r.meta_items||[]).map(m => `<div class="meta-item"><div class="meta-label">${{m.label}}</div><div class="meta-val">${{m.val}}</div></div>`).join('');
  const sake = r.sake_callout ? `<div class="section-title">酒種酵母 変換</div><div class="sake-box"><div class="sake-title">${{r.sake_callout.title}}</div><div class="sake-items">${{(r.sake_callout.items||[]).map(i=>`<div class="sake-item">${{i.label}}: <span>${{i.val}}</span></div>`).join('')}}</div></div>` : '';
  document.getElementById('modal-inner').innerHTML = `${{photoHtml}}<div class="modal-content"><div><span class="modal-cat" style="background:${{r.cat_color}}">${{r.cat_name}}</span><span class="modal-no">${{r.no}}</span></div><div class="modal-name">${{r.name}}</div><div class="modal-sub">${{r.sub||''}}</div>${{meta?`<div class="section-title">基本情報</div><div class="meta-grid">${{meta}}</div>`:''}}${{ingRows?`<div class="section-title">材料</div><table class="ing-table">${{ingRows}}</table>`:''}}${{sake}}${{steps?`<div class="section-title">手順</div><ul class="steps-list">${{steps}}</ul>`:''}}${{points?`<div class="section-title">ポイント</div><ul class="points-list">${{points}}</ul>`:''}}${{memo}}</div>`;
  document.getElementById('modal-overlay').classList.add('open');
  document.getElementById('modal').scrollTop = 0;
  document.body.style.overflow = 'hidden';
}}
function closeModal() {{ document.getElementById('modal-overlay').classList.remove('open'); document.body.style.overflow = ''; }}
document.getElementById('close-btn').addEventListener('click', closeModal);
document.getElementById('modal-overlay').addEventListener('click', e => {{ if (e.target===document.getElementById('modal-overlay')) closeModal(); }});

// パスワード認証
const PW_HASH = '7f9b46856a96a72a759c5573671765d354aa29116e76a2ac1fe75f362c4e9004';
async function hashStr(s) {{
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,'0')).join('');
}}
async function checkPw() {{
  const val = document.getElementById('pw-input').value;
  const h = await hashStr(val);
  if (h === PW_HASH) {{
    document.getElementById('pw-overlay').style.display = 'none';
    sessionStorage.setItem('auth', '1');
  }} else {{
    const inp = document.getElementById('pw-input');
    inp.classList.add('error');
    document.getElementById('pw-error').textContent = 'パスワードが違います';
    setTimeout(() => inp.classList.remove('error'), 400);
  }}
}}
if (sessionStorage.getItem('auth') === '1') {{
  document.getElementById('pw-overlay').style.display = 'none';
}}
document.getElementById('pw-btn').addEventListener('click', checkPw);
document.getElementById('pw-input').addEventListener('keydown', e => {{ if (e.key === 'Enter') checkPw(); }});

renderFilters(); renderGrid();
</script>
</body>
</html>'''

    # recipe_book/index.html に書き出し
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('index.html 生成完了')

    # iCloud Drive にコピー
    if os.path.isdir(ICLOUD_DIR):
        shutil.copy2('index.html', os.path.join(ICLOUD_DIR, 'index.html'))
        # 写真も同期（新規・更新分のみ）
        icloud_photos = os.path.join(ICLOUD_DIR, 'photos')
        os.makedirs(icloud_photos, exist_ok=True)
        for jpg in glob.glob('photos/*.jpg'):
            shutil.copy2(jpg, icloud_photos)
        print(f'iCloud Drive に同期完了: {ICLOUD_DIR}')
    else:
        print(f'iCloud Drive フォルダが見つかりません（スキップ）: {ICLOUD_DIR}')


def main():
    # order.json を読む
    with open('order.json', encoding='utf-8') as f:
        order = json.load(f)

    os.makedirs('output', exist_ok=True)
    out_path = 'output/bread_recipes.pdf'
    cv = rl_canvas.Canvas(out_path, pagesize=A4)

    pages = 0
    overflow = []
    for no in order:
        json_path = os.path.join('recipes', f'{no}.json')
        if not os.path.exists(json_path):
            print(f'{no}: JSONなし → スキップ')
            continue
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)
        remaining = draw_recipe_page(cv, data)
        pages += 1; cv.showPage()
        if remaining:
            overflow.append(no)
            draw_continuation(cv, data, remaining)
            pages += 1; cv.showPage()
        status = ' [+続きページ]' if remaining else ''
        print(f'{no}: {data["name"]}{status}')

    cv.save()
    print(f'\n完了: {out_path}  ({pages}ページ)')
    if overflow:
        print(f'続きページあり: {overflow}')

    build_index_html()

if __name__ == '__main__':
    main()
