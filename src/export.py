import pandas as pd
import os


def export_csv(df: pd.DataFrame, path: str = "output/draft_board.csv") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def export_html(df: pd.DataFrame, path: str = "output/draft_board.html") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Position color mapping
    pos_colors = {
        "SP": "#3b82f6",
        "RP": "#8b5cf6",
        "OF": "#10b981",
        "1B": "#f59e0b",
        "2B": "#f59e0b",
        "3B": "#f59e0b",
        "SS": "#f59e0b",
        "C":  "#ef4444",
        "CI": "#f97316",
        "MI": "#f97316",
        "DH": "#6b7280",
    }

    def value_badge(v):
        if pd.isna(v):
            return '<span class="badge neutral">–</span>'
        v = int(v)
        if v >= 10:
            return f'<span class="badge steal">+{v} steal</span>'
        elif v >= 3:
            return f'<span class="badge value">+{v}</span>'
        elif v <= -10:
            return f'<span class="badge reach">{v} reach</span>'
        elif v <= -3:
            return f'<span class="badge slight-reach">{v}</span>'
        else:
            return f'<span class="badge neutral">{v}</span>'

    rows_html = ""
    for _, row in df.iterrows():
        pos = row.get("Position", "")
        color = pos_colors.get(pos, "#6b7280")
        adp = row.get("ADP", 999)
        adp_display = "–" if adp >= 999 else f"{adp:.1f}"
        vorp = row.get("VORP", 0)
        val = row.get("Value", 0)
        pts = row.get("projected_points", 0)
        rnd = row.get("Est_Round", "–")
        rank = int(row.get("Draft_Rank", 0))
        name = row.get("Name", "")

        rows_html += f"""
        <tr>
            <td class="rank-cell">#{rank}</td>
            <td class="name-cell">
                <span class="player-name">{name}</span>
            </td>
            <td><span class="pos-badge" style="background:{color}22;color:{color};border:1px solid {color}44">{pos}</span></td>
            <td class="num-cell">{pts:.0f}</td>
            <td class="num-cell vorp-cell">{vorp:.1f}</td>
            <td class="num-cell">{adp_display}</td>
            <td>{value_badge(val)}</td>
            <td class="num-cell round-cell">Rd {rnd}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fantasy Draft Board</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg: #0d0f14;
    --surface: #13161d;
    --border: #1e2330;
    --text: #e8eaf0;
    --muted: #5a6070;
    --accent: #e8ff47;
    --accent2: #47d4ff;
  }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Mono', monospace;
    min-height: 100vh;
    padding: 40px 24px;
  }}

  .header {{
    max-width: 960px;
    margin: 0 auto 40px;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
  }}

  .title {{
    font-family: 'Syne', sans-serif;
    font-size: clamp(28px, 5vw, 48px);
    font-weight: 800;
    line-height: 1;
    letter-spacing: -1px;
  }}

  .title span {{
    color: var(--accent);
  }}

  .subtitle {{
    font-size: 12px;
    color: var(--muted);
    margin-top: 8px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }}

  .legend {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    justify-content: flex-end;
    font-size: 11px;
    color: var(--muted);
  }}

  .legend-item {{
    display: flex;
    align-items: center;
    gap: 5px;
  }}

  .legend-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }}

  .table-wrapper {{
    max-width: 960px;
    margin: 0 auto;
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    background: var(--surface);
  }}

  .filter-bar {{
    display: flex;
    gap: 10px;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
    align-items: center;
  }}

  .filter-label {{
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-right: 4px;
  }}

  .filter-btn {{
    background: transparent;
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 4px 12px;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.15s;
  }}

  .filter-btn:hover, .filter-btn.active {{
    border-color: var(--accent);
    color: var(--accent);
    background: rgba(232,255,71,0.06);
  }}

  .search-box {{
    margin-left: auto;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 4px 12px;
    color: var(--text);
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    outline: none;
    width: 180px;
    transition: border-color 0.15s;
  }}

  .search-box:focus {{
    border-color: var(--accent2);
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
  }}

  thead tr {{
    background: var(--bg);
  }}

  th {{
    padding: 10px 16px;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    text-align: left;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
  }}

  th:hover {{ color: var(--text); }}
  th.sorted {{ color: var(--accent); }}

  td {{
    padding: 11px 16px;
    font-size: 13px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }}

  tr:last-child td {{ border-bottom: none; }}

  tr:hover td {{
    background: rgba(255,255,255,0.02);
  }}

  .rank-cell {{
    color: var(--muted);
    font-size: 11px;
    width: 40px;
  }}

  .name-cell {{
    min-width: 160px;
  }}

  .player-name {{
    font-weight: 500;
    color: var(--text);
  }}

  .num-cell {{
    text-align: right;
    font-variant-numeric: tabular-nums;
  }}

  .vorp-cell {{
    color: var(--accent);
    font-weight: 500;
  }}

  .round-cell {{
    color: var(--muted);
    font-size: 11px;
  }}

  .pos-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.05em;
  }}

  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
  }}

  .badge.steal {{ background: rgba(16,185,129,0.15); color: #10b981; }}
  .badge.value {{ background: rgba(71,212,255,0.1); color: #47d4ff; }}
  .badge.neutral {{ background: rgba(255,255,255,0.05); color: var(--muted); }}
  .badge.slight-reach {{ background: rgba(249,115,22,0.1); color: #f97316; }}
  .badge.reach {{ background: rgba(239,68,68,0.1); color: #ef4444; }}

  .hidden {{ display: none; }}

  @media (max-width: 640px) {{
    .header {{ flex-direction: column; align-items: flex-start; }}
    .legend {{ justify-content: flex-start; }}
    td, th {{ padding: 8px 10px; }}
  }}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="title">DRAFT<span>BOARD</span></div>
    <div class="subtitle">12-team league · {len(df)} players ranked by VORP</div>
  </div>
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#10b981"></div>Steal</div>
    <div class="legend-item"><div class="legend-dot" style="background:#47d4ff"></div>Value</div>
    <div class="legend-item"><div class="legend-dot" style="background:#6b7280"></div>Fair</div>
    <div class="legend-item"><div class="legend-dot" style="background:#f97316"></div>Slight Reach</div>
    <div class="legend-item"><div class="legend-dot" style="background:#ef4444"></div>Reach</div>
  </div>
</div>

<div class="table-wrapper">
  <div class="filter-bar">
    <span class="filter-label">Filter:</span>
    <button class="filter-btn active" onclick="filterPos('ALL')">All</button>
    <button class="filter-btn" onclick="filterPos('SP')">SP</button>
    <button class="filter-btn" onclick="filterPos('RP')">RP</button>
    <button class="filter-btn" onclick="filterPos('OF')">OF</button>
    <button class="filter-btn" onclick="filterPos('1B')">1B</button>
    <button class="filter-btn" onclick="filterPos('2B')">2B</button>
    <button class="filter-btn" onclick="filterPos('SS')">SS</button>
    <button class="filter-btn" onclick="filterPos('3B')">3B</button>
    <button class="filter-btn" onclick="filterPos('C')">C</button>
    <button class="filter-btn" onclick="filterPos('DH')">DH</button>
    <input class="search-box" type="text" placeholder="Search player..." oninput="searchPlayers(this.value)">
  </div>

  <table id="draft-table">
    <thead>
      <tr>
        <th onclick="sortTable(0)">#</th>
        <th onclick="sortTable(1)">Player</th>
        <th onclick="sortTable(2)">Pos</th>
        <th onclick="sortTable(3)" style="text-align:right">Pts</th>
        <th onclick="sortTable(4)" style="text-align:right">VORP VORP ↓darr;</th>
        <th onclick="sortTable(5)" style="text-align:right">ADP</th>
        <th onclick="sortTable(6)">Value</th>
        <th onclick="sortTable(7)" style="text-align:right">Round</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</div>

<script>
  let currentPos = 'ALL';
  let currentSearch = '';
  let sortCol = -1;
  let sortAsc = true;

  function filterPos(pos) {{
    currentPos = pos;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    applyFilters();
  }}

  function searchPlayers(val) {{
    currentSearch = val.toLowerCase();
    applyFilters();
  }}

  function applyFilters() {{
    document.querySelectorAll('#draft-table tbody tr').forEach(row => {{
      const pos = row.querySelector('.pos-badge')?.textContent?.trim() || '';
      const name = row.querySelector('.player-name')?.textContent?.toLowerCase() || '';
      const posMatch = currentPos === 'ALL' || pos === currentPos;
      const searchMatch = !currentSearch || name.includes(currentSearch);
      row.classList.toggle('hidden', !(posMatch && searchMatch));
    }});
  }}

  function sortTable(col) {{
    const table = document.getElementById('draft-table');
    const tbody = table.querySelector('tbody');
    const ths = table.querySelectorAll('th');
    ths.forEach(th => th.classList.remove('sorted'));
    ths[col].classList.add('sorted');

    if (sortCol === col) sortAsc = !sortAsc;
    else {{ sortCol = col; sortAsc = true; }}

    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort((a, b) => {{
      const aText = a.cells[col]?.textContent?.trim() || '';
      const bText = b.cells[col]?.textContent?.trim() || '';
      const aNum = parseFloat(aText.replace(/[^0-9.\\-]/g, ''));
      const bNum = parseFloat(bText.replace(/[^0-9.\\-]/g, ''));
      if (!isNaN(aNum) && !isNaN(bNum)) return sortAsc ? aNum - bNum : bNum - aNum;
      return sortAsc ? aText.localeCompare(bText) : bText.localeCompare(aText);
    }});
    rows.forEach(r => tbody.appendChild(r));
  }}
</script>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
