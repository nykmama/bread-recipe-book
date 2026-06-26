# パンレシピ集 ビルドシステム

## フォルダ構成
```
recipe_book/
  recipes/          ← レシピデータ（JSON形式）
    SH-001.json
    HA-001.json
    ...
  photos/           ← 写真ファイル（JPG形式）
    SH-002.jpg      ← ファイル名 = レシピNo
    HA-003.jpg
    ...
  output/           ← 生成されたPDF
    bread_recipes.pdf
  build.py          ← PDFビルドスクリプト
  add_recipe.py     ← レシピ追加CLIツール
  order.json        ← PDFのページ順序
  README.md         ← このファイル
```

## セットアップ（初回のみ）
```bash
pip install reportlab pillow pypdf beautifulsoup4
```

## 使い方

### PDFを生成する
```bash
python build.py
```
→ `output/bread_recipes.pdf` が生成されます

### 新しいレシピを追加する

**Step 1: テンプレート生成**
```bash
python add_recipe.py
# または番号を指定
python add_recipe.py SO-012
```

**Step 2: JSONを編集**
生成された `recipes/SO-012.json` をテキストエディタで開いて編集

**Step 3: 写真を追加**
写真を `photos/SO-012.jpg` として保存（任意）

**Step 4: PDF生成**
```bash
python build.py
```

### レシピ追加と同時にビルド
```bash
python add_recipe.py --build
```

## レシピNoの命名規則
| prefix | カテゴリ |
|--------|--------|
| SH     | 食パン |
| HA     | ハード系 |
| SO     | 惣菜パン |
| KA     | 菓子パン |
| SE     | 季節系 |

## 写真の追加方法
1. 写真を `photos/レシピNo.jpg` として保存
2. `recipes/レシピNo.json` の `photo_file` を `"レシピNo.jpg"` に変更
3. 写真が縦向き（右90度回転が必要）の場合は `photo_rotated` を `true` に
4. `python build.py` を実行

## Claudeにレシピを追加してもらう場合
URLやテキストをClaude.aiに貼り付けて：
「SO-012のJSONを生成してください」
と依頼すると、JSONを出力してくれます。
それを `recipes/SO-012.json` にコピーして保存するだけです。
