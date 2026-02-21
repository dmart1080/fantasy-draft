# ADP Fetching & Combining

Run these three scripts in order to build a consensus ADP from FantasyPros + ESPN.

## Setup
```bash
pip install requests beautifulsoup4 pandas thefuzz python-Levenshtein
```

## Step 1 — FantasyPros (no login needed)
```bash
python scripts/fetch_fantasypros_adp.py
```
Outputs: `data/fantasypros_adp.csv`

## Step 2 — ESPN ADP

**Public ADP (no login):**
```bash
python scripts/fetch_espn_adp.py
```

**Your league's specific ADP (recommended):**

ESPN requires two cookies from your browser session.

1. Open Chrome → log into https://fantasy.espn.com
2. Press F12 → Application tab → Cookies → https://fantasy.espn.com
3. Copy the values for `espn_s2` and `SWID`

Then run:
```bash
export ESPN_S2="AEBxxxxxxxxxxxxxxx..."
export SWID="{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}"
python scripts/fetch_espn_adp.py
```

Outputs: `data/espn_adp.csv`

## Step 3 — Combine into consensus
```bash
python scripts/combine_adp.py
```
Outputs: `data/adp.csv` — this is what `main.py` reads automatically.

The combiner uses fuzzy name matching to handle differences like  
"Ronald Acuña Jr." (ESPN) vs "Ronald Acuna Jr." (FantasyPros).  
Any matches below 95% confidence are flagged for manual review.

## Step 4 — Rebuild draft board
```bash
python main.py
```
