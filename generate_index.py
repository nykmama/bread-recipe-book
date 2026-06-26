"""index.html生成スクリプト"""
import json, os, glob

# レシピ読み込み
recipe_files = sorted(glob.glob('recipes/*.json'))
recipes = []
for f in recipe_files:
    with open(f, encoding='utf-8') as fp:
        recipes.append(json.load(fp))

recipes_json = json.dumps(recipes, ensure_ascii=False, indent=None)

html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>パンレシピ集</title>
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

  /* ヘッダー */
  header {{
    background: #fff;
    border-bottom: 1px solid var(--border);
    padding: 20px 20px 16px;
    padding-top: calc(20px + env(safe-area-inset-top));
    position: sticky;
    top: 0;
    z-index: 100;
  }}
  header h1 {{
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: #3d2b1f;
  }}
  header p.subtitle {{
    font-size: 12px;
    color: var(--sub);
    margin-top: 2px;
  }}

  /* フィルタータブ */
  .filter-wrap {{
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding: 12px 16px 0;
    display: flex;
    gap: 8px;
    background: #fff;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
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
  .filter-btn.active {{
    color: #fff;
  }}

  /* カードグリッド */
  .grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    padding: 16px;
    max-width: 900px;
    margin: 0 auto;
  }}
  @media (min-width: 600px) {{
    .grid {{ grid-template-columns: repeat(3, 1fr); }}
  }}
  @media (min-width: 900px) {{
    .grid {{ grid-template-columns: repeat(4, 1fr); }}
  }}

  /* カード */
  .card {{
    background: var(--card-bg);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow);
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: transform 0.15s, box-shadow 0.15s;
    border: 1px solid var(--border);
    text-decoration: none;
    color: inherit;
    display: block;
  }}
  .card:active {{
    transform: scale(0.97);
    box-shadow: 0 1px 6px rgba(0,0,0,0.1);
  }}
  .card-photo {{
    width: 100%;
    aspect-ratio: 1/1;
    object-fit: cover;
    display: block;
    background: #f0ede8;
  }}
  .card-photo-placeholder {{
    width: 100%;
    aspect-ratio: 1/1;
    background: linear-gradient(135deg, #f5f0ea 0%, #ede8e0 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 36px;
  }}
  .card-body {{
    padding: 10px 12px 12px;
  }}
  .card-cat {{
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    border-radius: 4px;
    padding: 2px 7px;
    color: #fff;
    margin-bottom: 5px;
    letter-spacing: 0.03em;
  }}
  .card-name {{
    font-size: 14px;
    font-weight: 700;
    line-height: 1.35;
    color: #2c2c2c;
  }}
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
  .card-meta {{
    display: flex;
    gap: 6px;
    margin-top: 8px;
    flex-wrap: wrap;
  }}
  .card-tag {{
    font-size: 10px;
    background: #f0ede8;
    color: #666;
    border-radius: 4px;
    padding: 2px 6px;
  }}

  /* モーダル */
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
  @media (min-width: 600px) {{
    .modal-overlay.open {{ align-items: center; justify-content: center; }}
  }}
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
  @media (min-width: 600px) {{
    .modal {{
      border-radius: 24px;
      max-width: 540px;
      max-height: 85vh;
    }}
  }}
  @keyframes slideUp {{
    from {{ transform: translateY(30px); opacity: 0; }}
    to {{ transform: translateY(0); opacity: 1; }}
  }}
  .modal-handle {{
    width: 36px; height: 4px;
    background: #ddd;
    border-radius: 2px;
    margin: 12px auto 0;
  }}
  .modal-photo {{
    width: 100%;
    aspect-ratio: 4/3;
    object-fit: cover;
  }}
  .modal-photo-placeholder {{
    width: 100%;
    aspect-ratio: 4/3;
    background: linear-gradient(135deg, #f5f0ea 0%, #ede8e0 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 56px;
  }}
  .modal-content {{
    padding: 20px 20px 32px;
  }}
  .modal-cat {{
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    border-radius: 5px;
    padding: 3px 9px;
    color: #fff;
    margin-bottom: 8px;
  }}
  .modal-no {{
    font-size: 11px;
    color: #aaa;
    margin-left: 8px;
    font-weight: 600;
  }}
  .modal-name {{
    font-size: 22px;
    font-weight: 800;
    line-height: 1.3;
    color: #2c2c2c;
    margin-bottom: 4px;
  }}
  .modal-sub {{
    font-size: 13px;
    color: var(--sub);
    margin-bottom: 16px;
    line-height: 1.5;
  }}
  .section-title {{
    font-size: 13px;
    font-weight: 700;
    color: #888;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 20px 0 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
  }}
  .meta-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }}
  .meta-item {{
    background: #faf8f5;
    border-radius: 10px;
    padding: 10px 12px;
  }}
  .meta-label {{ font-size: 10px; color: #aaa; font-weight: 600; }}
  .meta-val {{ font-size: 14px; font-weight: 700; color: #2c2c2c; margin-top: 2px; }}

  /* 材料テーブル */
  .ing-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .ing-group td {{
    padding: 8px 0 2px;
    font-size: 11px;
    font-weight: 700;
    color: #aaa;
    letter-spacing: 0.05em;
    border-bottom: 1px solid #f0ede8;
  }}
  .ing-normal td {{
    padding: 7px 0;
    border-bottom: 1px solid #f5f3f0;
    vertical-align: top;
  }}
  .ing-name {{ color: #2c2c2c; }}
  .ing-bp {{ color: #aaa; font-size: 11px; text-align: right; padding-right: 8px; white-space: nowrap; }}
  .ing-weight {{ color: #2c2c2c; font-weight: 600; text-align: right; white-space: nowrap; }}
  .ing-total td {{
    padding: 10px 0 4px;
    font-weight: 700;
    color: #2c2c2c;
    border-top: 2px solid var(--border);
  }}

  /* 手順 */
  .steps-list {{ list-style: none; display: flex; flex-direction: column; gap: 12px; }}
  .step-item {{
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }}
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
  .step-time {{
    display: inline-block;
    font-size: 11px;
    background: #f0ede8;
    color: #888;
    border-radius: 4px;
    padding: 1px 7px;
    margin-top: 4px;
    font-weight: 600;
  }}

  /* ポイント */
  .points-list {{ list-style: none; display: flex; flex-direction: column; gap: 8px; }}
  .point-item {{
    display: flex;
    gap: 8px;
    font-size: 13px;
    line-height: 1.6;
    color: #444;
    align-items: flex-start;
  }}
  .point-item::before {{
    content: '✓';
    font-size: 12px;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 3px;
  }}

  /* メモ */
  .memo-box {{
    background: #fdf9f4;
    border-left: 3px solid #d4a96a;
    border-radius: 0 10px 10px 0;
    padding: 12px 14px;
    font-size: 13px;
    color: #555;
    line-height: 1.7;
  }}

  /* 酒種callout */
  .sake-box {{
    background: #f0f7f0;
    border-radius: 12px;
    padding: 14px 16px;
  }}
  .sake-title {{ font-size: 13px; font-weight: 700; color: #2e7d32; margin-bottom: 8px; }}
  .sake-items {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .sake-item {{ font-size: 13px; }}
  .sake-item span {{ font-weight: 700; color: #2e7d32; }}

  /* 閉じるボタン */
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

  /* 空状態 */
  .empty {{
    text-align: center;
    padding: 60px 20px;
    color: var(--sub);
    font-size: 15px;
    grid-column: 1 / -1;
  }}
</style>
</head>
<body>

<header>
  <h1>🍞 パンレシピ集</h1>
  <p class="subtitle" id="count-label"></p>
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

const CAT_EMOJI = {{
  '食パン': '🍞',
  'ハード系': '🥖',
  '惣菜パン': '🥗',
  '菓子パン': '🍫',
  '季節系': '🌸',
}};

let currentCat = 'すべて';

function getCats() {{
  const seen = new Set();
  const cats = ['すべて'];
  RECIPES.forEach(r => {{ if (!seen.has(r.cat_name)) {{ seen.add(r.cat_name); cats.push(r.cat_name); }} }});
  return cats;
}}

function filtered() {{
  return currentCat === 'すべて' ? RECIPES : RECIPES.filter(r => r.cat_name === currentCat);
}}

function photoPath(r) {{
  return r.photo_file ? `photos/${{r.photo_file}}` : null;
}}

function renderFilters() {{
  const wrap = document.getElementById('filter-wrap');
  getCats().forEach(cat => {{
    const btn = document.createElement('button');
    btn.className = 'filter-btn' + (cat === currentCat ? ' active' : '');
    if (cat !== 'すべて') {{
      btn.textContent = (CAT_EMOJI[cat] || '') + ' ' + cat;
      btn.style.background = cat === currentCat ? getCatColor(cat) : '';
    }} else {{
      btn.textContent = 'すべて';
      btn.style.background = cat === currentCat ? '#3d2b1f' : '';
    }}
    btn.addEventListener('click', () => {{
      currentCat = cat;
      renderFilters();
      renderGrid();
    }});
    wrap.appendChild(btn);
  }});
}}

function getCatColor(catName) {{
  const r = RECIPES.find(x => x.cat_name === catName);
  return r ? r.cat_color : '#888';
}}

function renderGrid() {{
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  const list = filtered();
  document.getElementById('count-label').textContent = list.length + '品';

  if (list.length === 0) {{
    grid.innerHTML = '<div class="empty">レシピが見つかりません</div>';
    return;
  }}

  list.forEach((r, i) => {{
    const card = document.createElement('div');
    card.className = 'card';
    const photo = photoPath(r);
    const photoHtml = photo
      ? `<img class="card-photo" src="${{photo}}" alt="${{r.name}}" loading="lazy" onerror="this.parentNode.innerHTML='<div class=\\"card-photo-placeholder\\">${{CAT_EMOJI[r.cat_name] || '🍞'}}</div>'">`
      : `<div class="card-photo-placeholder">${{CAT_EMOJI[r.cat_name] || '🍞'}}</div>`;
    const tags = r.meta_items.slice(0,2).map(m => `<span class="card-tag">${{m.val}}</span>`).join('');
    card.innerHTML = `
      ${{photoHtml}}
      <div class="card-body">
        <span class="card-cat" style="background:${{r.cat_color}}">${{r.cat_name}}</span>
        <div class="card-name">${{r.name}}</div>
        <div class="card-sub">${{r.sub || ''}}</div>
        <div class="card-meta">${{tags}}</div>
      </div>`;
    card.addEventListener('click', () => openModal(r));
    grid.appendChild(card);
  }});
}}

function openModal(r) {{
  const photo = photoPath(r);
  const photoHtml = photo
    ? `<img class="modal-photo" src="${{photo}}" alt="${{r.name}}" onerror="this.parentNode.innerHTML='<div class=\\"modal-photo-placeholder\\">${{CAT_EMOJI[r.cat_name] || '🍞'}}</div>'">`
    : `<div class="modal-photo-placeholder">${{CAT_EMOJI[r.cat_name] || '🍞'}}</div>`;

  // 材料
  const ingRows = (r.ing_rows || []).map(row => {{
    if (row.kind === 'group') return `<tr class="ing-group"><td colspan="3">${{row.name}}</td></tr>`;
    if (row.kind === 'total') return `<tr class="ing-total"><td class="ing-name">${{row.name}}</td><td class="ing-bp"></td><td class="ing-weight">${{row.weight}}</td></tr>`;
    return `<tr class="ing-normal"><td class="ing-name">${{row.name}}</td><td class="ing-bp">${{row.bp !== '—' ? 'BP' + row.bp + '%' : ''}}</td><td class="ing-weight">${{row.weight}}</td></tr>`;
  }}).join('');

  // 手順
  const steps = (r.steps || []).map(s => `
    <li class="step-item">
      <div class="step-num" style="background:${{r.cat_color}}">${{s.num}}</div>
      <div class="step-body">
        <div class="step-name">${{s.name}}</div>
        <div class="step-detail">${{s.detail}}</div>
        ${{s.time ? `<span class="step-time">⏱ ${{s.time}}</span>` : ''}}
      </div>
    </li>`).join('');

  // ポイント
  const points = (r.points || []).map(p => `<li class="point-item">${{p}}</li>`).join('');

  // メモ
  const memo = r.memo ? `<div class="section-title">メモ</div><div class="memo-box">${{r.memo}}</div>` : '';

  // メタ
  const meta = (r.meta_items || []).map(m => `
    <div class="meta-item">
      <div class="meta-label">${{m.label}}</div>
      <div class="meta-val">${{m.val}}</div>
    </div>`).join('');

  // 酒種
  const sake = r.sake_callout ? `
    <div class="section-title">酒種酵母 変換</div>
    <div class="sake-box">
      <div class="sake-title">${{r.sake_callout.title}}</div>
      <div class="sake-items">${{(r.sake_callout.items || []).map(i => `<div class="sake-item">${{i.label}}: <span>${{i.val}}</span></div>`).join('')}}</div>
    </div>` : '';

  document.getElementById('modal-inner').innerHTML = `
    ${{photoHtml}}
    <div class="modal-content">
      <div>
        <span class="modal-cat" style="background:${{r.cat_color}}">${{r.cat_name}}</span>
        <span class="modal-no">${{r.no}}</span>
      </div>
      <div class="modal-name">${{r.name}}</div>
      <div class="modal-sub">${{r.sub || ''}}</div>
      ${{meta ? `<div class="section-title">基本情報</div><div class="meta-grid">${{meta}}</div>` : ''}}
      ${{ingRows ? `<div class="section-title">材料</div><table class="ing-table">${{ingRows}}</table>` : ''}}
      ${{sake}}
      ${{steps ? `<div class="section-title">手順</div><ul class="steps-list">${{steps}}</ul>` : ''}}
      ${{points ? `<div class="section-title">ポイント</div><ul class="points-list">${{points}}</ul>` : ''}}
      ${{memo}}
    </div>`;

  const overlay = document.getElementById('modal-overlay');
  overlay.classList.add('open');
  document.getElementById('modal').scrollTop = 0;
  document.body.style.overflow = 'hidden';
}}

function closeModal() {{
  document.getElementById('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
}}

document.getElementById('close-btn').addEventListener('click', closeModal);
document.getElementById('modal-overlay').addEventListener('click', e => {{
  if (e.target === document.getElementById('modal-overlay')) closeModal();
}});

// 初期描画
renderFilters();
renderGrid();
</script>
</body>
</html>
'''

os.makedirs('output', exist_ok=True)
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("生成完了: index.html")
