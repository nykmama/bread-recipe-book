#!/usr/bin/env python3
"""
gift/gift_data.json の自動更新スクリプト
- src が "確定" の項目は絶対に上書きしない
- recipes/*.json に存在するが gift_data に未登録（または src="自動"）の番号を追加・更新する
"""
import json, os, re
from pathlib import Path

GIFT_PATH = Path('gift/gift_data.json')
RECIPES_DIR = Path('recipes')

EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF"
    "\U0001F000-\U0001F0FF" "←-⇿" "✀-➿" "]+",
    flags=re.UNICODE)

def extract_text(recipe):
    """全テキスト（reheat検知用）"""
    parts = []
    for row in recipe.get('ing_rows', []):
        if row.get('kind') in ('normal', 'total') and row.get('name'):
            parts.append(row['name'])
    for s in recipe.get('steps', []):
        for k in ('detail', 'name'):
            v = s.get(k)
            if v: parts.append(v)
    parts.extend(p for p in recipe.get('points', []) if p)
    for k in ('memo', 'sub', 'name'):
        v = recipe.get(k)
        if v: parts.append(v)
    return ' '.join(parts)

def extract_ing_text(recipe):
    """材料名のみ（アレルゲン検知用 - 手順文の誤検知を防ぐ）"""
    parts = []
    for row in recipe.get('ing_rows', []):
        if row.get('kind') in ('normal', 'total') and row.get('name'):
            parts.append(row['name'])
    # sub/name も含めて具材を補完
    for k in ('sub', 'name'):
        v = recipe.get(k)
        if v: parts.append(v)
    return ' '.join(parts)

def detect_allergens(recipe):
    text = extract_ing_text(recipe)
    allergens = ['小麦']
    kakohin = False

    checks = [
        ('乳', ['バター', '牛乳', '生クリーム', 'チーズ', 'スキムミルク', '脱脂粉乳',
                 'クリームチーズ', 'マスカルポーネ', 'コンデンスミルク', 'カスタード',
                 'ヨーグルト', 'ミルク', 'ホイップ', 'ホワイトチョコ', 'ガナッシュ']),
        ('卵',  ['卵', '全卵', '卵黄', '卵白', 'たまご']),
        ('大豆', ['大豆', '豆乳', 'きなこ', 'きな粉', '枝豆', '味噌', 'みそ',
                  '醤油', 'しょうゆ', '大豆粉']),
        ('落花生', ['ピーナッツ', '落花生']),
        ('えび',   ['えび', '海老', 'エビ', '桜えび', '桜エビ']),
        ('かに',   ['かに', 'カニ', 'かにかま', 'カニカマ']),
        ('アーモンド', ['アーモンド', 'アマンド', 'ダマンド', 'クランブル', 'フラジパーヌ']),
        ('くるみ',      ['くるみ', '胡桃', 'ウォルナット']),
        ('マカダミアナッツ', ['マカダミア']),
        ('ヘーゼルナッツ',   ['ヘーゼルナッツ', 'ジャンドゥーヤ', 'ジャンドゥジャ']),
        ('ごま',  ['ごま', 'ゴマ', '胡麻', 'セサミ', '黒ごま', '白ごま']),
    ]
    for label, kws in checks:
        if any(k in text for k in kws):
            allergens.append(label)

    # 豚肉
    pork_kw = ['ベーコン', 'ソーセージ', 'ウインナー', 'ウィンナー', 'ハム',
               'ポーク', 'サラミ', 'プロシュート', 'パンチェッタ', 'ジョンソンヴィル', '豚']
    if any(k in text for k in pork_kw):
        allergens.append('豚肉'); kakohin = True

    # 鶏肉
    if any(k in text for k in ['鶏', 'チキン']):
        allergens.append('鶏肉'); kakohin = True

    # 牛肉
    if any(k in text for k in ['牛肉', 'ビーフ', 'ミートソース']):
        allergens.append('牛肉'); kakohin = True

    # いか
    if any(k in text for k in ['いか', 'イカ', '烏賊']):
        allergens.append('いか'); kakohin = True

    # 果物アレルゲン
    if any(k in text for k in ['りんご', 'リンゴ', 'アップル']):
        allergens.append('りんご')
    if any(k in text for k in ['もも', '桃', 'ピーチ']):
        allergens.append('もも')
    if 'オレンジ' in text:
        allergens.append('オレンジ')

    # 加工品フラグ（豚肉・鶏肉・牛肉・いか以外の要確認加工品）
    kakohin_kw = [
        'チョコレート', 'チョコ', 'ホワイトチョコ',  # チョコ系
        'カレー',                                        # カレールー/粉
        'たらこ', '明太', '明太子',                      # 魚卵加工品
        'ツナ', 'アンチョビ',                            # 魚加工缶
        '粒あん', 'こしあん', 'かぼちゃあん', 'きなこあん',
        '小倉あん', '白あん', 'さくらあん', 'あんこ',    # 市販あん類
        'かにかま', 'カニカマ',                          # かにかま
        'ミートソース', 'バジルソース',                  # ソース類
        '明太マヨ',
        'あん（', 'あんこ', 'あん)', 'あん　',           # 市販あん汎用（前後に文字がない形）
        'の餡', 'お好みの餡', '餡子',                   # 漢字の餡
    ]
    if any(k in text for k in kakohin_kw):
        kakohin = True

    result = '・'.join(allergens)
    if kakohin:
        result += ' ※加工品は要確認'
    return result

def detect_reheat(recipe):
    ng_kw = ['バタークリーム', '生クリーム', 'ホイップクリーム', 'ホイップ']
    steps = recipe.get('steps', [])
    bake_found = False
    for step in steps:
        combined = (step.get('detail', '') or '') + ' ' + (step.get('name', '') or '')
        if any(k in combined for k in ['焼成', '焼く', 'オーブン', '揚げる', '揚げ']):
            bake_found = True
        if bake_found:
            for ng in ng_kw:
                if ng in combined:
                    reason = ng if ng != 'ホイップ' else 'ホイップクリーム'
                    return f'ng:{reason}のため'
    for pt in recipe.get('points', []):
        for ng in ng_kw:
            if ng in pt:
                reason = ng if ng != 'ホイップ' else 'ホイップクリーム'
                return f'ng:{reason}のため'
    # マリトッツォ special case
    all_text = extract_text(recipe)
    if 'マリトッツォ' in all_text and '生クリーム' in all_text:
        return 'ng:生クリームのため'
    return 'ok'

def gen_desc(recipe):
    name = EMOJI_RE.sub('', recipe.get('name', '')).strip()
    if len(name) <= 25:
        return name
    return name[:24] + '…'

def main():
    with open(GIFT_PATH, 'r', encoding='utf-8') as f:
        gift_data = json.load(f)

    confirmed = {k for k, v in gift_data['items'].items() if v.get('src') == '確定'}
    added = []
    updated = []

    for rf in sorted(RECIPES_DIR.glob('*.json')):
        no = rf.stem
        if no in confirmed:
            continue
        with open(rf, 'r', encoding='utf-8') as f:
            recipe = json.load(f)

        entry = {
            'd': gen_desc(recipe),
            'h': detect_reheat(recipe),
            'a': detect_allergens(recipe),
            'src': '自動'
        }
        is_new = no not in gift_data['items']
        gift_data['items'][no] = entry
        if is_new:
            added.append({'no': no, 'name': recipe.get('name', ''), **entry})
        else:
            updated.append(no)

    with open(GIFT_PATH, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(gift_data, f, ensure_ascii=False, indent=2)

    print(f'新規追加: {len(added)} 件  更新(自動→自動): {len(updated)} 件')
    if added:
        print(f'\n{"番号":<10} {"名称":<30} {"d":<27} {"h":<24} a')
        print('-' * 115)
        for item in added:
            print(f'{item["no"]:<10} {item["name"][:28]:<30} {item["d"]:<27} {item["h"]:<24} {item["a"]}')

if __name__ == '__main__':
    main()
