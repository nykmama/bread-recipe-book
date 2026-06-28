"""レシピNo削除・再編成スクリプト"""
import json, os, shutil

RECIPES_DIR = 'recipes'
PHOTOS_DIR = 'photos'

# 削除するNo
DELETE = ['HA-001', 'HA-002', 'KA-001', 'SE-001', 'SH-001']

# 旧No → (新No, cat_name, cat_color)
RENAME_MAP = {
    'SH-002': ('SH-001', '食パン',   '#4E342E'),
    'SH-003': ('SH-002', '食パン',   '#4E342E'),
    'HA-003': ('HA-001', 'ハード系', '#283593'),
    'HA-004': ('HA-002', 'ハード系', '#283593'),
    'HA-005': ('HA-003', 'ハード系', '#283593'),
    'HA-006': ('HA-004', 'ハード系', '#283593'),
    'KA-002': ('KA-001', '菓子パン', '#880E4F'),
    'KA-003': ('KA-002', '菓子パン', '#880E4F'),
    'KA-004': ('KA-003', '菓子パン', '#880E4F'),
    'SE-002': ('SE-001', '季節系',   '#E65100'),
    'SE-003': ('SE-002', '季節系',   '#E65100'),
}

NEW_ORDER = [
    'SH-001', 'SH-002',
    'HA-001', 'HA-002', 'HA-003', 'HA-004',
    'SO-001', 'SO-002', 'SO-003', 'SO-004', 'SO-005', 'SO-006', 'SO-007',
    'KA-001', 'KA-002', 'KA-003',
    'SE-001', 'SE-002',
    'TB-001', 'TB-002', 'TB-003',
    'PB-001', 'PB-002', 'PB-003', 'PB-004',
]

def main():
    # 1. 削除
    for no in DELETE:
        json_path = os.path.join(RECIPES_DIR, f'{no}.json')
        jpg_path  = os.path.join(PHOTOS_DIR,  f'{no}.jpg')
        if os.path.exists(json_path):
            os.remove(json_path)
            print(f'削除: {json_path}')
        if os.path.exists(jpg_path):
            os.remove(jpg_path)
            print(f'削除: {jpg_path}')

    # 2. 旧JSONを読み込んでメモリに保持
    data_map = {}
    for old_no, (new_no, new_cat, new_color) in RENAME_MAP.items():
        path = os.path.join(RECIPES_DIR, f'{old_no}.json')
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        data['no'] = new_no
        data['cat_name'] = new_cat
        data['cat_color'] = new_color
        if data.get('photo_file'):
            data['photo_file'] = f'{new_no}.jpg'
        data_map[old_no] = (new_no, data)

    # 3. 旧JSONを削除
    for old_no in RENAME_MAP:
        os.remove(os.path.join(RECIPES_DIR, f'{old_no}.json'))

    # 4. 新JSONを書き出し
    for old_no, (new_no, data) in data_map.items():
        path = os.path.join(RECIPES_DIR, f'{new_no}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'JSON: {old_no} → {new_no}')

    # 5. 写真リネーム（tmp経由で衝突回避）
    renames = []
    for old_no, (new_no, _) in data_map.items():
        old_jpg = os.path.join(PHOTOS_DIR, f'{old_no}.jpg')
        new_jpg = os.path.join(PHOTOS_DIR, f'{new_no}.jpg')
        if os.path.exists(old_jpg):
            renames.append((old_jpg, new_jpg))

    for old_jpg, _ in renames:
        shutil.move(old_jpg, old_jpg + '.tmp')
    for old_jpg, new_jpg in renames:
        tmp = old_jpg + '.tmp'
        if os.path.exists(tmp):
            shutil.move(tmp, new_jpg)
            print(f'写真: {os.path.basename(old_jpg)} → {os.path.basename(new_jpg)}')

    # 6. order.json更新
    with open('order.json', 'w', encoding='utf-8') as f:
        json.dump(NEW_ORDER, f, ensure_ascii=False, indent=2)
    print(f'\norder.json 更新: {len(NEW_ORDER)}件')
    print('完了！次に python build.py を実行してください。')

if __name__ == '__main__':
    main()
