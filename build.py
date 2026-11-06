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
            # PDFサイズ抑制（GitHubの100MB制限）のため縮小して埋め込む
            if side > 1200:
                img = img.resize((1200, 1200), Image.LANCZOS)
            tmp = os.path.join(tempfile.gettempdir(), f'_recipe_photo_{data["no"]}.jpg')
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

    photo_mtime = {}
    for fpath in glob.glob('photos/*'):
        fname = os.path.basename(fpath)
        photo_mtime[fname] = int(os.path.getmtime(fpath))
    photo_mtime_json = json.dumps(photo_mtime, ensure_ascii=False)

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
  header h1 {{ font-size: 24px; font-weight: 700; letter-spacing: 0.08em; color: #b5541b; line-height: 1.3; }}
  header h1 .e-wobble {{ font-size: 26px; display: inline-block; animation: wobble 2.5s ease-in-out infinite; }}
  header h1 .e-bounce {{ font-size: 26px; display: inline-block; animation: bounce 1.8s ease-in-out infinite; }}
  header h1 .e-spin {{ font-size: 26px; display: inline-block; animation: spin 3s linear infinite; }}
  @keyframes wobble {{ 0%,100% {{ transform: rotate(-10deg); }} 50% {{ transform: rotate(10deg); }} }}
  @keyframes bounce {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-5px); }} }}
  @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
  header p.subtitle-main {{ font-size: 13px; color: #d4845a; margin-top: 4px; font-style: italic; letter-spacing: 0.05em; }}
  header p.subtitle {{ font-size: 11px; color: var(--sub); margin-top: 1px; }}
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
  .search-wrap {{
    padding: 10px 16px;
    background: #fff;
    border-bottom: 1px solid var(--border);
  }}
  .search-input {{
    width: 100%;
    border: 2px solid var(--border);
    border-radius: 20px;
    padding: 9px 16px 9px 38px;
    font-size: 14px;
    font-family: inherit;
    background: #faf8f5 url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23aaa' stroke-width='2'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cpath d='m21 21-4.35-4.35'/%3E%3C/svg%3E") no-repeat 12px center;
    outline: none;
    color: #2c2c2c;
    transition: border-color 0.2s;
    -webkit-appearance: none;
  }}
  .search-input:focus {{ border-color: #3d2b1f; background-color: #fff; }}
  .search-input::placeholder {{ color: #bbb; }}
  .filter-wrap {{
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding: 10px 16px;
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
      <h1><span class="e-wobble">🍞</span> NYKMAMAのパンレシピ <span class="e-bounce">🥐</span></h1>
      <p class="subtitle-main"><span class="e-spin" style="font-size:13px;">🌸</span> きみたちが食べてくれた分だけ、幸せなレシピが増えた。</p>
      <p class="subtitle" id="count-label"></p>
    </div>
    <div style="display:flex;gap:8px;flex-shrink:0;align-items:flex-start;margin-top:2px;">
      <a class="pdf-btn" href="output/bread_recipes.pdf" download="パンレシピ集.pdf">📄 PDF</a>
      <a class="pdf-btn" href="gift.html" style="background:#6a3d7a;">🎁 おすそ分けシート</a>
    </div>
  </div>
</header>
<div class="search-wrap">
  <input class="search-input" id="search-input" type="search" placeholder="材料名で検索（例: クリームチーズ）">
</div>
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
const PHOTO_MTIME = {photo_mtime_json};
const CAT_EMOJI = {{'食パン':'🍞','ハード系':'🥖','惣菜パン':'🥗','菓子パン':'🍫','季節系':'🌸','テーブルパン':'🧈','ピザ・ベーグル':'🍕'}};
let currentCat = 'すべて';
let searchQuery = '';

function matchesSearch(r) {{
  if (!searchQuery) return true;
  const q = searchQuery.toLowerCase();
  return (r.ing_rows || []).some(row =>
    row.kind === 'normal' && row.name && row.name.toLowerCase().includes(q)
  );
}}

function getCats() {{
  const seen = new Set(); const cats = ['すべて'];
  RECIPES.forEach(r => {{ if (!seen.has(r.cat_name)) {{ seen.add(r.cat_name); cats.push(r.cat_name); }} }});
  return cats;
}}
function filtered() {{
  return RECIPES.filter(r =>
    (currentCat === 'すべて' || r.cat_name === currentCat) && matchesSearch(r)
  );
}}
function photoPath(r) {{ if (!r.photo_file) return null; const v = PHOTO_MTIME[r.photo_file] || '0'; return `photos/${{r.photo_file}}?v=${{v}}`; }}
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

// 材料検索
document.getElementById('search-input').addEventListener('input', e => {{
  searchQuery = e.target.value.trim();
  renderGrid();
}});

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


def build_gift_html():
    recipe_files = sorted(glob.glob('recipes/*.json'))
    recipes_slim = []
    for f in recipe_files:
        with open(f, encoding='utf-8') as fp:
            r = json.load(fp)
        recipes_slim.append({
            'no': r.get('no',''),
            'name': r.get('name',''),
            'cat_name': r.get('cat_name',''),
            'cat_color': r.get('cat_color','#888'),
            'photo_file': r.get('photo_file',''),
            'sub': r.get('sub',''),
        })

    gift_path = os.path.join('gift', 'gift_data.json')
    if os.path.exists(gift_path):
        with open(gift_path, encoding='utf-8') as fp:
            gift_data = json.load(fp)
    else:
        gift_data = {'defaults': {}, 'items': {}}

    recipes_json = json.dumps(recipes_slim, ensure_ascii=False)
    gift_json = json.dumps(gift_data, ensure_ascii=False)

    photo_mtime = {}
    for fpath in glob.glob('photos/*'):
        fname = os.path.basename(fpath)
        photo_mtime[fname] = int(os.path.getmtime(fpath))
    photo_mtime_json = json.dumps(photo_mtime, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>おすそ分けシート – NYKMAMAのパンレシピ</title>
<style>
:root {{
  --bg: #faf8f5;
  --card-bg: #fff;
  --text: #2c2c2c;
  --sub: #777;
  --border: #e8e4de;
  --accent: #6a3d7a;
  --red: #c0392b;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
}}
/* ── スクリーン用レイアウト ── */
.screen-header {{
  background: #fff;
  border-bottom: 1px solid var(--border);
  padding: 14px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 100;
}}
.screen-header h1 {{ font-size: 18px; font-weight: 800; color: var(--accent); flex: 1; }}
.screen-header a {{ font-size: 12px; color: #888; text-decoration: none; }}
.screen-header a:hover {{ color: var(--text); }}
.main-layout {{
  display: flex;
  height: calc(100vh - 54px);
}}
/* 左：レシピ一覧 */
.sidebar {{
  width: 340px;
  min-width: 260px;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  background: #fff;
  overflow: hidden;
}}
.sidebar-top {{
  padding: 12px;
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 8px;
}}
.search-input {{
  width: 100%;
  border: 1.5px solid var(--border);
  border-radius: 20px;
  padding: 8px 14px 8px 36px;
  font-size: 13px;
  font-family: inherit;
  background: #faf8f5 url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%23aaa' stroke-width='2'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cpath d='m21 21-4.35-4.35'/%3E%3C/svg%3E") no-repeat 11px center;
  outline: none;
  color: #2c2c2c;
}}
.search-input:focus {{ border-color: var(--accent); }}
.cat-filter {{
  display: flex;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
  padding-bottom: 2px;
}}
.cat-filter::-webkit-scrollbar {{ display: none; }}
.cat-btn {{
  flex-shrink: 0;
  border: none;
  border-radius: 14px;
  padding: 5px 11px;
  font-size: 11px;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  background: #f0ede8;
  color: #555;
  white-space: nowrap;
}}
.cat-btn.active {{ color: #fff; background: var(--accent); }}
.selected-count {{
  font-size: 11px;
  color: var(--sub);
  padding: 4px 12px;
  border-bottom: 1px solid var(--border);
  background: #faf8f5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.clear-btn {{
  font-size: 11px;
  color: var(--accent);
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
  font-weight: 600;
  padding: 0;
}}
.recipe-list {{
  overflow-y: auto;
  flex: 1;
}}
.recipe-item {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-bottom: 1px solid #f5f3f0;
  cursor: pointer;
  transition: background 0.1s;
  -webkit-tap-highlight-color: transparent;
}}
.recipe-item:hover {{ background: #faf8f5; }}
.recipe-item.checked {{ background: #f4eef7; }}
.recipe-cb {{ width: 18px; height: 18px; accent-color: var(--accent); cursor: pointer; flex-shrink: 0; }}
.recipe-thumb {{
  width: 36px;
  height: 36px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
  background: #ede8e0;
}}
.recipe-thumb-ph {{
  width: 36px;
  height: 36px;
  border-radius: 6px;
  background: #ede8e0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}}
.recipe-info {{ flex: 1; min-width: 0; }}
.recipe-name {{ font-size: 13px; font-weight: 700; color: #2c2c2c; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.recipe-no {{ font-size: 10px; color: #aaa; font-weight: 600; }}
.badge-auto {{
  font-size: 9px;
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffc107;
  border-radius: 4px;
  padding: 1px 5px;
  font-weight: 700;
  flex-shrink: 0;
}}
.badge-miss {{
  font-size: 9px;
  background: #f8d7da;
  color: #842029;
  border: 1px solid #f5c2c7;
  border-radius: 4px;
  padding: 1px 5px;
  font-weight: 700;
  flex-shrink: 0;
}}
/* 右：プレビューエリア */
.preview-area {{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}
.controls-bar {{
  background: #fff;
  border-bottom: 1px solid var(--border);
  padding: 10px 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}}
.ctrl-group {{
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text);
  font-weight: 600;
}}
.ctrl-group label {{ font-size: 12px; color: var(--sub); font-weight: 600; }}
.ctrl-input {{
  border: 1.5px solid var(--border);
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 13px;
  font-family: inherit;
  color: var(--text);
  background: #faf8f5;
  outline: none;
}}
.ctrl-input:focus {{ border-color: var(--accent); }}
.ctrl-select {{
  border: 1.5px solid var(--border);
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 13px;
  font-family: inherit;
  color: var(--text);
  background: #faf8f5;
  outline: none;
  cursor: pointer;
}}
.print-btn {{
  margin-left: auto;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 20px;
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;
}}
.print-btn:disabled {{ background: #ccc; cursor: not-allowed; }}
.print-btn:not(:disabled):active {{ opacity: 0.85; }}
.preview-scroll {{
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #e8e4de;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}}
.preview-empty {{
  color: var(--sub);
  font-size: 14px;
  text-align: center;
  margin-top: 60px;
}}
/* ── A4シート ── */
.sheet {{
  background: #fff;
  width: 210mm;
  min-height: 297mm;
  box-shadow: 0 4px 24px rgba(0,0,0,0.15);
  padding: 10mm;
  display: flex;
  flex-direction: column;
  position: relative;
  flex-shrink: 0;
}}
.sheet-header {{
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 5mm;
  padding-bottom: 3mm;
  border-bottom: 0.5mm solid #2c2c2c;
}}
.sheet-to {{
  font-size: 14pt;
  font-weight: 800;
  color: #2c2c2c;
  min-width: 60mm;
}}
.sheet-to span {{ font-size: 9pt; color: #888; font-weight: 500; display: block; margin-bottom: 1mm; }}
.sheet-from {{
  font-size: 9pt;
  color: #888;
  text-align: right;
  line-height: 1.6;
}}
.sheet-items {{
  flex: 1;
  display: grid;
  gap: 3mm;
}}
.grid-2x2 {{ grid-template-columns: 1fr 1fr; }}
.grid-2x3 {{ grid-template-columns: 1fr 1fr; }}
.grid-2x4 {{ grid-template-columns: 1fr 1fr; }}
.item-card {{
  border: 0.3mm solid #d8d0be;
  border-radius: 2mm;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fffdf8;
}}
.item-photo {{
  width: 100%;
  object-fit: cover;
  display: block;
  background: #f0ede8;
}}
.item-photo-ph {{
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0ede8;
  font-size: 24pt;
  color: #ccc;
}}
.item-body {{
  padding: 2mm 3mm 2.5mm;
  flex: 1;
}}
.item-no {{ font-size: 7pt; color: #aaa; font-weight: 700; margin-bottom: 0.5mm; }}
.item-name {{ font-size: 10pt; font-weight: 800; color: #2c2c2c; line-height: 1.3; margin-bottom: 1mm; }}
.item-desc {{ font-size: 7.5pt; color: #555; line-height: 1.4; margin-bottom: 1.5mm; }}
.item-reheat {{ font-size: 7pt; line-height: 1.4; margin-bottom: 1mm; }}
.item-reheat.ok-heat {{ color: #2c2c2c; }}
.item-reheat.ng-heat {{ color: var(--red); font-weight: 700; }}
.item-allergy {{ font-size: 6.5pt; color: #666; line-height: 1.4; }}
.item-allergy strong {{ color: #2c2c2c; font-weight: 700; }}
.item-miss {{
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9pt;
  color: #aaa;
  font-style: italic;
  flex: 1;
  padding: 4mm;
}}
.sheet-footer {{
  margin-top: 4mm;
  padding-top: 3mm;
  border-top: 0.3mm solid #d8d0be;
  font-size: 7pt;
  color: #555;
  line-height: 1.6;
}}
.sheet-footer .storage-text {{ margin-bottom: 1.5mm; }}
.sheet-disclaimer {{
  margin-top: 2mm;
  font-size: 6pt;
  color: #aaa;
  text-align: right;
}}
/* ── 印刷 ── */
@media print {{
  .no-print {{ display: none !important; }}
  body {{ background: #fff; }}
  .preview-scroll {{ background: #fff; padding: 0; gap: 0; }}
  .sheet {{
    box-shadow: none;
    page-break-after: always;
    margin: 0;
    width: 100%;
    min-height: auto;
  }}
  .sheet:last-child {{ page-break-after: auto; }}
}}
@page {{
  size: A4;
  margin: 0;
}}
</style>
</head>
<body>
<header class="screen-header no-print">
  <h1>🎁 おすそ分けシート</h1>
  <a href="index.html">← レシピ一覧に戻る</a>
</header>
<div class="main-layout">
  <!-- 左サイドバー -->
  <aside class="sidebar no-print">
    <div class="sidebar-top">
      <input class="search-input" id="search-input" type="search" placeholder="名前で絞り込み">
      <div class="cat-filter" id="cat-filter"></div>
    </div>
    <div class="selected-count">
      <span id="sel-count">0件選択中</span>
      <button class="clear-btn" id="clear-btn" onclick="clearAll()">すべて解除</button>
    </div>
    <div class="recipe-list" id="recipe-list"></div>
  </aside>
  <!-- 右プレビューエリア -->
  <div class="preview-area">
    <div class="controls-bar no-print">
      <div class="ctrl-group">
        <label>宛名</label>
        <input class="ctrl-input" id="recipient" type="text" placeholder="○○さんへ" style="width:140px;" oninput="rerender()">
      </div>
      <div class="ctrl-group">
        <label>日付</label>
        <input class="ctrl-input" id="gift-date" type="date" oninput="rerender()">
      </div>
      <div class="ctrl-group">
        <label>1枚あたり</label>
        <select class="ctrl-select" id="per-sheet" onchange="rerender()">
          <option value="4">4品</option>
          <option value="6" selected>6品</option>
          <option value="8">8品</option>
        </select>
      </div>
      <div class="ctrl-group">
        <label>写真</label>
        <select class="ctrl-select" id="with-photo" onchange="rerender()">
          <option value="1">あり</option>
          <option value="0">なし</option>
        </select>
      </div>
      <button class="print-btn" id="print-btn" disabled onclick="handlePrint()">🖨️ 印刷</button>
    </div>
    <div class="preview-scroll" id="preview-scroll">
      <div class="preview-empty" id="preview-empty">左のリストからパンを選択してください</div>
    </div>
  </div>
</div>
<script>
const RECIPES = {recipes_json};
const GIFT_DATA = {gift_json};
const PHOTO_MTIME = {photo_mtime_json};
const CAT_EMOJI = {{'食パン':'🍞','ハード系':'🥖','惣菜パン':'🥗','菓子パン':'🍫','季節系':'🌸','テーブルパン':'🧈','ピザ・ベーグル':'🍕'}};

let selectedNos = [];
let catFilter = 'すべて';
let searchQuery = '';

function photoPath(r) {{
  if (!r.photo_file) return null;
  const v = PHOTO_MTIME[r.photo_file] || '0';
  return `photos/${{r.photo_file}}?v=${{v}}`;
}}

function getItem(no) {{ return (GIFT_DATA.items || {{}})[no] || null; }}

function getCats() {{
  const seen = new Set(); const cats = ['すべて'];
  RECIPES.forEach(r => {{ if (!seen.has(r.cat_name)) {{ seen.add(r.cat_name); cats.push(r.cat_name); }} }});
  return cats;
}}

function filteredRecipes() {{
  const q = searchQuery.toLowerCase();
  return RECIPES.filter(r =>
    (catFilter === 'すべて' || r.cat_name === catFilter) &&
    (!q || r.name.toLowerCase().includes(q) || r.no.toLowerCase().includes(q))
  );
}}

// カテゴリフィルター
function renderCats() {{
  const wrap = document.getElementById('cat-filter');
  wrap.innerHTML = '';
  getCats().forEach(cat => {{
    const btn = document.createElement('button');
    btn.className = 'cat-btn' + (cat === catFilter ? ' active' : '');
    btn.textContent = cat === 'すべて' ? 'すべて' : (CAT_EMOJI[cat]||'') + ' ' + cat;
    btn.addEventListener('click', () => {{ catFilter = cat; renderCats(); renderList(); }});
    wrap.appendChild(btn);
  }});
}}

// レシピ一覧
function renderList() {{
  const list = document.getElementById('recipe-list');
  list.innerHTML = '';
  filteredRecipes().forEach(r => {{
    const checked = selectedNos.includes(r.no);
    const item = getItem(r.no);
    const isAuto = item && item.src === '自動';
    const isMiss = !item;
    const div = document.createElement('div');
    div.className = 'recipe-item' + (checked ? ' checked' : '');
    const photo = photoPath(r);
    const thumbHtml = photo
      ? `<img class="recipe-thumb" src="${{photo}}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" loading="lazy"><div class="recipe-thumb-ph" style="display:none">${{CAT_EMOJI[r.cat_name]||'🍞'}}</div>`
      : `<div class="recipe-thumb-ph">${{CAT_EMOJI[r.cat_name]||'🍞'}}</div>`;
    const badgeHtml = isMiss
      ? '<span class="badge-miss">未記入</span>'
      : (isAuto ? '<span class="badge-auto">自動下書き</span>' : '');
    div.innerHTML = `<input type="checkbox" class="recipe-cb" ${{checked ? 'checked' : ''}} onclick="event.stopPropagation();toggleSelect('${{r.no}}')">${{thumbHtml}}<div class="recipe-info"><div class="recipe-name">${{r.name}}</div><div class="recipe-no">${{r.no}}</div></div>${{badgeHtml}}`;
    div.addEventListener('click', () => toggleSelect(r.no));
    list.appendChild(div);
  }});
  document.getElementById('sel-count').textContent = selectedNos.length + '件選択中';
  document.getElementById('print-btn').disabled = selectedNos.length === 0;
}}

function toggleSelect(no) {{
  const idx = selectedNos.indexOf(no);
  if (idx >= 0) selectedNos.splice(idx, 1);
  else selectedNos.push(no);
  renderList();
  renderPreview();
}}

function clearAll() {{
  selectedNos = [];
  renderList();
  renderPreview();
}}

// プレビュー
function rerender() {{ renderPreview(); }}

function reheatText(h) {{
  const defs = GIFT_DATA.defaults || {{}};
  if (!h || h === 'ok') return {{ text: defs.reheat_ok || '', ng: false }};
  if (h.startsWith('ng:')) {{
    const reason = h.slice(3);
    const tmpl = defs.reheat_ng || '温めNG（{{reason}}）。解凍したままお召し上がりください。';
    return {{ text: tmpl.replace('{{{{reason}}}}', reason), ng: true }};
  }}
  return {{ text: h, ng: false }};
}}

function buildCard(no, perSheet, withPhoto) {{
  const recipe = RECIPES.find(r => r.no === no);
  if (!recipe) return '<div class="item-card"><div class="item-miss">データなし</div></div>';
  const item = getItem(no);
  const photo = photoPath(recipe);
  let photoHtml = '';
  const photoHeights = {{ 4: '32mm', 6: '22mm', 8: '15mm' }};
  const ph = photoHeights[perSheet] || '22mm';
  if (withPhoto && photo) {{
    photoHtml = `<img class="item-photo" src="${{photo}}" alt="${{recipe.name}}" style="height:${{ph}}" onerror="this.style.display='none'">`;
  }} else if (withPhoto && !photo) {{
    photoHtml = `<div class="item-photo-ph" style="height:${{ph}}">${{CAT_EMOJI[recipe.cat_name]||'🍞'}}</div>`;
  }}
  if (!item) {{
    return `<div class="item-card">${{photoHtml}}<div class="item-body"><div class="item-no">${{no}}</div><div class="item-name">${{recipe.name}}</div><div class="item-miss" style="font-size:7pt;color:#c0392b;padding:1mm 0;">⚠ ギフトデータ未登録</div></div></div>`;
  }}
  const rh = reheatText(item.h);
  const reheatHtml = rh.text
    ? `<div class="item-reheat ${{rh.ng ? 'ng-heat' : 'ok-heat'}}">🌡 ${{rh.text}}</div>`
    : '';
  const allergyHtml = item.a
    ? `<div class="item-allergy"><strong>アレルゲン：</strong>${{item.a}}</div>`
    : '';
  const descHtml = item.d ? `<div class="item-desc">${{item.d}}</div>` : '';
  return `<div class="item-card">${{photoHtml}}<div class="item-body"><div class="item-no">${{no}}</div><div class="item-name">${{recipe.name}}</div>${{descHtml}}${{reheatHtml}}${{allergyHtml}}</div></div>`;
}}

function buildSheet(nos, perSheet, withPhoto, recipient, dateStr, sheetIdx, totalSheets) {{
  const gridClass = {{ 4:'grid-2x2', 6:'grid-2x3', 8:'grid-2x4' }}[perSheet] || 'grid-2x3';
  const itemsHtml = nos.map(no => buildCard(no, perSheet, withPhoto)).join('');
  const toHtml = recipient
    ? `<div class="sheet-to"><span>To</span>${{recipient}} さんへ</div>`
    : `<div class="sheet-to"><span>To</span>　　　　　　　 さんへ</div>`;
  const dateHtml = dateStr || new Date().toLocaleDateString('ja-JP', {{year:'numeric',month:'long',day:'numeric'}});
  const pageLabel = totalSheets > 1 ? ` (${{sheetIdx+1}}/${{totalSheets}})` : '';
  const defs = GIFT_DATA.defaults || {{}};
  const storageText = defs.storage || '';
  return `<div class="sheet">
  <div class="sheet-header">
    ${{toHtml}}
    <div class="sheet-from">NYKMAMAのパン${{pageLabel}}<br>${{dateHtml}}</div>
  </div>
  <div class="sheet-items ${{gridClass}}">${{itemsHtml}}</div>
  <div class="sheet-footer">
    <div class="storage-text">📦 ${{storageText}}</div>
    <div class="sheet-disclaimer">原材料は加工品を含め必ず現物の表示でご確認ください</div>
  </div>
</div>`;
}}

function renderPreview() {{
  const scroll = document.getElementById('preview-scroll');
  const empty = document.getElementById('preview-empty');
  const perSheet = parseInt(document.getElementById('per-sheet').value);
  const withPhoto = document.getElementById('with-photo').value === '1';
  const recipient = document.getElementById('recipient').value.trim();
  const rawDate = document.getElementById('gift-date').value;
  const dateStr = rawDate ? new Date(rawDate).toLocaleDateString('ja-JP', {{year:'numeric',month:'long',day:'numeric'}}) : '';
  document.getElementById('sel-count').textContent = selectedNos.length + '件選択中';
  document.getElementById('print-btn').disabled = selectedNos.length === 0;
  if (selectedNos.length === 0) {{
    scroll.innerHTML = '';
    scroll.appendChild(empty);
    empty.style.display = '';
    return;
  }}
  empty.style.display = 'none';
  // ページ分割
  const pages = [];
  for (let i = 0; i < selectedNos.length; i += perSheet) {{
    pages.push(selectedNos.slice(i, i + perSheet));
  }}
  scroll.innerHTML = pages.map((nos, idx) =>
    buildSheet(nos, perSheet, withPhoto, recipient, dateStr, idx, pages.length)
  ).join('');
}}

function handlePrint() {{
  const autoItems = selectedNos.filter(no => {{
    const item = getItem(no);
    return item && item.src === '自動';
  }});
  if (autoItems.length > 0) {{
    const names = autoItems.map(no => {{
      const r = RECIPES.find(x => x.no === no);
      return (r ? r.name : no);
    }}).join('、');
    if (!confirm(`「自動下書き」の項目が${{autoItems.length}}件含まれています。\\n\\n${{names}}\\n\\n内容を確認の上、印刷してください。続けますか？`)) return;
  }}
  window.print();
}}

// 日付の初期値を今日に
document.getElementById('gift-date').value = new Date().toISOString().slice(0,10);

document.getElementById('search-input').addEventListener('input', e => {{
  searchQuery = e.target.value.trim();
  renderList();
}});

renderCats();
renderList();
renderPreview();
</script>
</body>
</html>'''

    with open('gift.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('gift.html 生成完了')


def normalize_photo_extensions():
    """photos/ フォルダ内の大文字拡張子ファイルを小文字にリネームする"""
    for fpath in glob.glob('photos/*'):
        base, ext = os.path.splitext(fpath)
        if ext != ext.lower():
            new_path = base + ext.lower()
            os.rename(fpath, new_path)
            print(f'リネーム: {os.path.basename(fpath)} → {os.path.basename(new_path)}')

def main():
    normalize_photo_extensions()

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
    build_gift_html()

if __name__ == '__main__':
    main()
