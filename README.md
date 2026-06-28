# 🍞 NYKMAMA BREAD RECIPE BOOK

パンレシピ管理システム。レシピの追加・編集からPDF・Web生成まで一括で行えます。

## 閲覧URL

**Web版（iPhone/iPad対応）**
https://nykmama.github.io/bread-recipe-book/

**PDF版**
https://nykmama.github.io/bread-recipe-book/output/bread_recipes.pdf

---

## フォルダ構成

```
recipe_book/
  recipes/       ← レシピデータ（JSON形式）
  photos/        ← 写真ファイル（JPG形式、ファイル名=レシピNo）
  output/        ← 生成されたPDF
  build.py       ← ビルドスクリプト（PDF・HTML・iCloud Drive一括更新）
  order.json     ← PDFのページ順序
  index.html     ← Web版（自動生成）
```

## レシピNoの命名規則

| prefix | カテゴリ |
|--------|--------|
| SH     | 食パン |
| HA     | ハード系 |
| SO     | 惣菜パン |
| KA     | 菓子パン |
| SE     | 季節系 |
| TA     | テーブルパン |
| PB     | ピザ・ベーグル |

---

## セットアップ（初回のみ）

```bash
pip install reportlab pillow pypdf beautifulsoup4
```

---

## 操作手順

### ビルド（共通）

レシピや写真を変更したら必ず実行します。

```bash
cd C:\Users\nykma\recipe_book
python build.py
```

PDF・index.html・iCloud Drive への同期が自動で行われます。

### GitHubへのプッシュ（共通）

ビルド後にWeb版を更新するには以下を実行します。1〜2分後にGitHub Pagesに反映されます。

```bash
git -C "C:\Users\nykma\recipe_book" add -A
git -C "C:\Users\nykma\recipe_book" commit -m "変更内容のメモ"
git -C "C:\Users\nykma\recipe_book" push origin main
```

---

### レシピを追加する

**Step 1: JSONファイルを作成**

`recipes/` フォルダに新しいJSONファイルを追加します（例: `recipes/SO-012.json`）。
既存のJSONファイルをコピーして内容を編集してください。

**Step 2: order.jsonに追記**

`order.json` を開き、表示したい位置にレシピNoを追記します。

```json
[
  ...
  "SO-012"
]
```

**Step 3: ビルド＆プッシュ**

```bash
python build.py
git -C "C:\Users\nykma\recipe_book" add -A
git -C "C:\Users\nykma\recipe_book" commit -m "add SO-012"
git -C "C:\Users\nykma\recipe_book" push origin main
```

---

### 写真を追加・差し替える

**Step 1: 写真ファイルを保存**

写真を `photos/レシピNo.jpg`（例: `photos/SO-012.jpg`）として保存します。

**Step 2: JSONを編集**

該当レシピのJSONの `photo_file` を設定します。

```json
"photo_file": "SO-012.jpg"
```

**Step 3: ビルド＆プッシュ**

```bash
python build.py
git -C "C:\Users\nykma\recipe_book" add -A
git -C "C:\Users\nykma\recipe_book" commit -m "add photo SO-012"
git -C "C:\Users\nykma\recipe_book" push origin main
```

---

### 写真を90度回転する

該当レシピのJSONの `photo_rotated` を `true` に変更します。

```json
"photo_rotated": true
```

その後ビルド＆プッシュを実行します。

---

## JSONの主なフィールド

```json
{
  "no": "SO-012",
  "cat_name": "惣菜パン",
  "cat_color": "#1B5E20",
  "name": "レシピ名",
  "sub": "サブタイトル・製法など",
  "photo_file": "SO-012.jpg",
  "photo_rotated": false,
  "meta_items": [
    { "label": "製法", "val": "ストレート法" },
    { "label": "加水率", "val": "65%" },
    { "label": "粉の種類", "val": "強力粉 100%" },
    { "label": "焼成温度", "val": "200℃" },
    { "label": "焼成時間", "val": "13分〜" }
  ],
  "ing_rows": [
    { "kind": "group", "name": "粉類" },
    { "kind": "normal", "name": "強力粉", "bp": "100", "weight": "150.0g" },
    { "kind": "total", "name": "合計", "bp": "—", "weight": "150.0g" }
  ],
  "points": ["ポイント1", "ポイント2"],
  "steps": [
    { "num": "1", "name": "工程名", "detail": "詳細", "time": "15分" }
  ],
  "memo": "メモ欄",
  "sake_callout": null
}
```

### cat_colorの対応表

| カテゴリ | カラーコード |
|--------|------------|
| 食パン  | `#4E342E`  |
| ハード系 | `#283593`  |
| 惣菜パン | `#1B5E20`  |
| 菓子パン | `#880E4F`  |
| 季節系  | `#E65100`  |
| テーブルパン | `#F57F17`  |
| ピザ・ベーグル | `#00695C`  |

---

## Claudeにレシピ追加を依頼する場合

レシピのURLやテキストをClaude Code（またはClaude.ai）に貼り付けて：

「SO-012のJSONを生成してください」

と依頼するとJSONを出力してくれます。
それを `recipes/SO-012.json` に保存してビルド＆プッシュするだけです。
