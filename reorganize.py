"""レシピNo再構成スクリプト"""
import json, os, shutil

RECIPES_DIR = 'recipes'
PHOTOS_DIR = 'photos'

# 旧No → (新No, 新cat_name, 新cat_color)
RENAME_MAP = {
    # 移動
    'SO-001': ('TB-001', 'テーブルパン', '#F57F17'),
    'KA-005': ('TB-002', 'テーブルパン', '#F57F17'),
    'HA-006': ('TB-003', 'テーブルパン', '#F57F17'),
    'HA-005': ('PB-001', 'ピザ・ベーグル', '#00695C'),
    'SO-003': ('PB-002', 'ピザ・ベーグル', '#00695C'),
    'SO-005': ('PB-003', 'ピザ・ベーグル', '#00695C'),
    'SO-004': ('PB-004', 'ピザ・ベーグル', '#00695C'),
    # HA 繰り上げ
    'HA-007': ('HA-005', 'ハード系', '#283593'),
    'HA-008': ('HA-006', 'ハード系', '#283593'),
    # SO 繰り上げ
    'SO-002': ('SO-001', '惣菜パン', '#1B5E20'),
    'SO-006': ('SO-002', '惣菜パン', '#1B5E20'),
    'SO-007': ('SO-003', '惣菜パン', '#1B5E20'),
    'SO-008': ('SO-004', '惣菜パン', '#1B5E20'),
    'SO-009': ('SO-005', '惣菜パン', '#1B5E20'),
    'SO-010': ('SO-006', '惣菜パン', '#1B5E20'),
    'SO-011': ('SO-007', '惣菜パン', '#1B5E20'),
}

# order.jsonの新しい順序
NEW_ORDER = [
    'SH-001', 'SH-002', 'SH-003',
    'HA-001', 'HA-002', 'HA-003', 'HA-004', 'HA-005', 'HA-006',
    'SO-001', 'SO-002', 'SO-003', 'SO-004', 'SO-005', 'SO-006', 'SO-007',
    'KA-001', 'KA-002', 'KA-003', 'KA-004',
    'SE-001', 'SE-002', 'SE-003',
    'TB-001', 'TB-002', 'TB-003',
    'PB-001', 'PB-002', 'PB-003', 'PB-004',
]

def main():
    # 1. 旧JSONを読み込んでメモリに保持
    data_map = {}
    for old_no, (new_no, new_cat, new_color) in RENAME_MAP.items():
        path = os.path.join(RECIPES_DIR, f'{old_no}.json')
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        data['no'] = new_no
        data['cat_name'] = new_cat
        data['cat_color'] = new_color
        # photo_fileも更新
        if data.get('photo_file'):
            ext = os.path.splitext(data['photo_file'])[1]
            data['photo_file'] = f'{new_no}{ext}'
        data_map[old_no] = (new_no, data)

    # 2. 旧JSONを削除
    for old_no in RENAME_MAP:
        path = os.path.join(RECIPES_DIR, f'{old_no}.json')
        os.remove(path)
        print(f'削除: {path}')

    # 3. 新JSONを書き出し
    for old_no, (new_no, data) in data_map.items():
        path = os.path.join(RECIPES_DIR, f'{new_no}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'作成: {path}  ({old_no} → {new_no})')

    # 4. 写真ファイルをリネーム（一時名を経由して衝突回避）
    photo_renames = []
    for old_no, (new_no, data) in data_map.items():
        old_jpg = os.path.join(PHOTOS_DIR, f'{old_no}.jpg')
        new_jpg = os.path.join(PHOTOS_DIR, f'{new_no}.jpg')
        if os.path.exists(old_jpg):
            photo_renames.append((old_jpg, new_jpg))

    # 一時ファイルに退避
    for old_jpg, new_jpg in photo_renames:
        tmp = old_jpg + '.tmp'
        shutil.move(old_jpg, tmp)

    # 本命名
    for old_jpg, new_jpg in photo_renames:
        tmp = old_jpg + '.tmp'
        if os.path.exists(tmp):
            shutil.move(tmp, new_jpg)
            print(f'写真: {os.path.basename(old_jpg)} → {os.path.basename(new_jpg)}')

    # 5. order.json更新
    with open('order.json', 'w', encoding='utf-8') as f:
        json.dump(NEW_ORDER, f, ensure_ascii=False, indent=2)
    print(f'\norder.json 更新完了: {len(NEW_ORDER)}件')
    print('完了！次に python build.py を実行してください。')

if __name__ == '__main__':
    main()
