# Data Pipeline

Full workflow to build a consensus draft board from real data.

## Install deps
```bash
pip install requests beautifulsoup4 pandas thefuzz python-Levenshtein
```

---

## Projections (run once before draft season, refresh as needed)

```bash
# 1. FantasyPros consensus projections (free, no login)
python scripts/fetch_fantasypros_projections.py

# 2. FanGraphs Steamer projections (free, no login)
python scripts/fetch_fangraphs_projections.py

# 3. Baseball Savant xStats as baseline (free, no login)
python scripts/fetch_bbref_projections.py

# 4. Combine into weighted consensus (FP=45%, FG=35%, BR=20%)
python scripts/combine_projections.py
```
Outputs: `data/projections.csv`

---

## ADP (refresh weekly as draft approaches)

```bash
# 1. FantasyPros consensus ADP (free, no login)
python scripts/fetch_fantasypros_adp.py

# 2. ESPN ADP (requires browser cookies)
#    Get espn_s2 and SWID from browser DevTools -> Application -> Cookies
$env:ESPN_S2 = "AEB..."
$env:SWID = "{YOUR-SWID}"
python scripts/fetch_espn_adp.py

# 3. Combine into consensus ADP
python scripts/combine_adp.py
```
Outputs: `data/adp.csv`

---

## Build draft board

```bash
python main.py
```
Outputs: `output/draft_board.html` and `output/draft_board.csv`

---

## Projection weights
Edit `scripts/combine_projections.py` to change source weights:
```python
WEIGHTS = {
    "fp": 0.45,   # FantasyPros (already a consensus)
    "fg": 0.35,   # FanGraphs Steamer
    "br": 0.20,   # Baseball Savant xStats
}
```
