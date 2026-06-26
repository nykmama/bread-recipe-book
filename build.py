"""
パンレシピ集 PDFビルドスクリプト
使い方: python build.py
出力:   output/bread_recipes.pdf
"""
import json, math, os, re, tempfile
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
    txt = f"ORIGINAL BREAD RECIPE BOOK  |  {data['cat_name']}"
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

if __name__ == '__main__':
    main()
