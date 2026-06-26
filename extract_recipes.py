"""
HTMLから全レシピをJSON化し、写真をjpgファイルとして書き出すスクリプト
"""
import json, re, base64, os
from bs4 import BeautifulSoup

HTML_PATH = '/mnt/user-data/outputs/bread_recipes_all.html'  # outputs内のHTMLを参照
RECIPES_DIR = 'recipes'
PHOTOS_DIR = 'photos'

ORDER = [
    'SH-001','SH-002','SH-003',
    'HA-001','HA-002','HA-003','HA-004','HA-005','HA-006','HA-007','HA-008',
    'SO-001','SO-002','SO-003','SO-004','SO-005','SO-006','SO-007','SO-008',
    'SO-009','SO-010','SO-011',
    'KA-001','KA-002','KA-003','KA-004','KA-005',
    'SE-001','SE-002','SE-003',
]

def extract_block(html, no):
    start_marker = f'id="page-{no}"'
    idx = html.find(start_marker)
    if idx == -1: return None
    div_start = html.rfind('<div class="page"', 0, idx)
    depth = 0
    tag_re = re.compile(r'<div\b[^>]*>|</div>')
    end = None
    for m in tag_re.finditer(html, div_start):
        if m.group().startswith('<div'): depth += 1
        else:
            depth -= 1
            if depth == 0: end = m.end(); break
    return html[div_start:end]

def parse_block(block_html, no):
    soup = BeautifulSoup(block_html, 'html.parser')

    # 基本情報
    recipe_no = soup.find('div', class_='recipe-no').get_text()
    cat_dot = soup.find('span', class_='cat-dot')
    cat_color = cat_dot.get('style','').split('background:')[-1].strip(';').strip() if cat_dot else '#000'
    cat_name = recipe_no.split('|')[-1].strip()
    name = soup.find('div', class_='recipe-name').get_text(strip=True)
    sub_div = soup.find('div', class_='recipe-sub')
    sub = sub_div.get_text(strip=True) if sub_div else ''

    # 写真
    img_tag = soup.find('img')
    photo_file = None
    photo_rotated = False
    if img_tag and img_tag.get('src','').startswith('data:image'):
        src = img_tag['src']
        _, b64data = src.split(',', 1)
        img_bytes = base64.b64decode(b64data)
        photo_file = f'{no}.jpg'
        with open(os.path.join(PHOTOS_DIR, photo_file), 'wb') as f:
            f.write(img_bytes)
        photo_rotated = 'rotate(90deg)' in img_tag.get('style','')

    # メタ情報
    meta_items = []
    meta_row = soup.find('div', class_='meta-row')
    if meta_row:
        for item in meta_row.find_all('div', class_='meta-item'):
            label = item.find('div', class_='meta-label').get_text(strip=True)
            val = item.find('div', class_='meta-val').get_text(strip=True)
            meta_items.append({'label': label, 'val': val})

    # 配合
    ing_rows = []
    table = soup.find('table', class_='ing-table')
    if table:
        for tr in table.find('tbody').find_all('tr'):
            cls = tr.get('class', [])
            tds = tr.find_all('td')
            if 'ing-group' in cls:
                ing_rows.append({'kind': 'group', 'name': tds[0].get_text(strip=True)})
            elif 'ing-total' in cls:
                vals = [td.get_text(strip=True) for td in tds]
                ing_rows.append({'kind': 'total', 'name': vals[0], 'bp': vals[1] if len(vals)>1 else '', 'weight': vals[2] if len(vals)>2 else ''})
            elif len(tds) == 1:
                ing_rows.append({'kind': 'sep', 'name': tds[0].get_text(strip=True)})
            elif len(tds) == 3:
                ing_rows.append({'kind': 'normal', 'name': tds[0].get_text(strip=True), 'bp': tds[1].get_text(strip=True), 'weight': tds[2].get_text(strip=True)})

    # ポイント
    points = []
    point_list = soup.find('div', class_='point-list')
    if point_list:
        for item in point_list.find_all('div', class_='point-item'):
            divs = item.find_all('div')
            points.append(divs[-1].get_text(strip=True))

    # メモ
    memo_box = soup.find('div', class_='memo-box')
    memo = memo_box.get_text(strip=True) if memo_box else ''

    # 酒種コールアウト
    sake_callout = None
    sake_div = soup.find('div', class_='sake-callout')
    if sake_div:
        title = sake_div.find('div', class_='sake-callout-title').get_text(strip=True)
        grid = sake_div.find('div', class_='sake-grid')
        items = []
        for d in grid.find_all('div', recursive=False):
            span = d.find('span')
            val = span.get_text(strip=True) if span else ''
            label = d.get_text(strip=True).replace(val, '').strip()
            items.append({'label': label, 'val': val})
        sake_callout = {'title': title, 'items': items}

    # 製造工程
    steps = []
    proc_flow = soup.find('div', class_='process-flow')
    if proc_flow:
        for step in proc_flow.find_all('div', class_='proc-step'):
            num = step.find('div', class_='proc-num').get_text(strip=True)
            name_d = step.find('div', class_='proc-name').get_text(strip=True)
            detail_d = step.find('div', class_='proc-detail').get_text(strip=True)
            time_d = step.find('div', class_='proc-time')
            time_text = time_d.get_text(strip=True).replace('⏱','').strip() if time_d else None
            steps.append({'num': num, 'name': name_d, 'detail': detail_d, 'time': time_text})

    return {
        'no': no,
        'cat_name': cat_name,
        'cat_color': cat_color,
        'name': name,
        'sub': sub,
        'photo_file': photo_file,
        'photo_rotated': photo_rotated,
        'meta_items': meta_items,
        'ing_rows': ing_rows,
        'points': points,
        'memo': memo,
        'sake_callout': sake_callout,
        'steps': steps,
    }

def main():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    os.makedirs(RECIPES_DIR, exist_ok=True)
    os.makedirs(PHOTOS_DIR, exist_ok=True)

    results = []
    for no in ORDER:
        block = extract_block(html, no)
        if not block:
            print(f'{no}: NOT FOUND')
            continue
        data = parse_block(block, no)
        json_path = os.path.join(RECIPES_DIR, f'{no}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        photo_info = f"photo={data['photo_file']}" if data['photo_file'] else 'no photo'
        print(f'{no}: {data["name"]} ({photo_info})')
        results.append(no)

    # order.json
    with open('order.json', 'w', encoding='utf-8') as f:
        json.dump(ORDER, f, ensure_ascii=False, indent=2)

    print(f'\n完了: {len(results)}レシピをJSON化、写真をphotos/に書き出し')

if __name__ == '__main__':
    main()
