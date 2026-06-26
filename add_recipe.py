"""
新しいレシピを追加するCLIツール
使い方:
  python add_recipe.py              # 対話式でテンプレート生成
  python add_recipe.py SO-012       # 指定Noのテンプレートを生成
  python add_recipe.py --build      # テンプレート生成後にPDFビルドも実行
"""
import json, os, sys, subprocess

CATEGORIES = {
    'SH': ('食パン',    '#8B5A2B'),
    'HA': ('ハード系',  '#283593'),
    'SO': ('惣菜パン',  '#C0392B'),
    'KA': ('菓子パン',  '#6A1B9A'),
    'SE': ('季節系',    '#6D4C41'),
}

def next_no(prefix):
    """既存JSONから次の番号を自動決定"""
    existing = [f for f in os.listdir('recipes') if f.startswith(prefix) and f.endswith('.json')]
    if not existing:
        return f'{prefix}-001'
    nums = [int(f[len(prefix)+1:-5]) for f in existing]
    return f'{prefix}-{max(nums)+1:03d}'

def make_template(no):
    prefix = no[:2]
    cat_name, cat_color = CATEGORIES.get(prefix, ('未分類', '#000000'))
    return {
        "no": no,
        "cat_name": cat_name,
        "cat_color": cat_color,
        "name": "レシピ名を入力",
        "sub": "酒種・直捏ね法 / ○個分（元○g→150g換算）",
        "photo_file": None,
        "photo_rotated": False,
        "meta_items": [
            {"label": "製法",   "val": "酒種・直捏ね"},
            {"label": "加水率", "val": "○%"},
            {"label": "粉の種類","val": "強力粉100%"},
            {"label": "焼成温度","val": "○℃"},
            {"label": "焼成時間","val": "○分"}
        ],
        "ing_rows": [
            {"kind": "normal", "name": "強力粉",               "bp": "100", "weight": "150.0g"},
            {"kind": "normal", "name": "インスタントドライイースト","bp": "1",   "weight": "1.5g"},
            {"kind": "normal", "name": "砂糖",                 "bp": "○",   "weight": "○g"},
            {"kind": "normal", "name": "塩",                   "bp": "○",   "weight": "○g"},
            {"kind": "normal", "name": "💧 水",                "bp": "○",   "weight": "○g"},
            {"kind": "normal", "name": "無塩バター",            "bp": "○",   "weight": "○g"},
            {"kind": "total",  "name": "生地合計",              "bp": "—",   "weight": "○g"}
        ],
        "points": [
            "ポイント1",
            "ポイント2"
        ],
        "memo": "メモを入力",
        "sake_callout": {
            "title": "🌿 酒種酵母 変換配合（イースト→酒種・BP20%・水分90%）",
            "items": [
                {"label": "酒種酵母", "val": "30.0g（BP20%・イーストと置換）"},
                {"label": "調整後加水", "val": "水○gに変更（牛乳○gはそのまま）"}
            ]
        },
        "steps": [
            {"num": "1", "name": "生地をこねる",  "detail": "詳細を入力", "time": "○分"},
            {"num": "2", "name": "一次発酵",      "detail": "詳細を入力", "time": "○分"},
            {"num": "3", "name": "分割・ベンチタイム","detail": "詳細を入力","time": "○分"},
            {"num": "4", "name": "成形",          "detail": "詳細を入力", "time": None},
            {"num": "5", "name": "二次発酵",      "detail": "詳細を入力", "time": "○分"},
            {"num": "6", "name": "焼成",          "detail": "詳細を入力", "time": "○℃×○分"}
        ]
    }

def update_order(no):
    with open('order.json', encoding='utf-8') as f:
        order = json.load(f)
    if no not in order:
        order.append(no)
        with open('order.json', 'w', encoding='utf-8') as f:
            json.dump(order, f, ensure_ascii=False, indent=2)
        print(f'order.json に {no} を追加しました')

def main():
    args = sys.argv[1:]
    do_build = '--build' in args
    args = [a for a in args if a != '--build']

    if args:
        no = args[0].upper()
    else:
        print('カテゴリを選択してください:')
        for k, (name, _) in CATEGORIES.items():
            print(f'  {k}: {name}')
        prefix = input('prefix (例: SO): ').strip().upper()
        no = next_no(prefix)
        print(f'→ No: {no} として作成します')

    json_path = os.path.join('recipes', f'{no}.json')
    if os.path.exists(json_path):
        print(f'すでに存在します: {json_path}')
        print('編集する場合はそのまま編集してください')
    else:
        template = make_template(no)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        print(f'テンプレートを作成しました: {json_path}')
        print(f'\n次のステップ:')
        print(f'  1. recipes/{no}.json を編集してレシピを入力')
        print(f'  2. 写真があれば photos/{no}.jpg として保存')
        print(f'  3. python build.py を実行してPDF生成')

    update_order(no)

    if do_build:
        print('\nPDFをビルド中...')
        subprocess.run([sys.executable, 'build.py'])

if __name__ == '__main__':
    main()
