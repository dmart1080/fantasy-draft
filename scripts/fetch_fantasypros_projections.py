"""
Fetches FantasyPros consensus projections for batters and pitchers.
Saves to data/fantasypros_projections.csv

Install deps:
    pip install requests beautifulsoup4 pandas

Run:
    python scripts/fetch_fantasypros_projections.py
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import time

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# FantasyPros projection URLs by position group
BATTER_URLS = {
    "C":  "https://www.fantasypros.com/mlb/projections/c.php",
    "1B": "https://www.fantasypros.com/mlb/projections/1b.php",
    "2B": "https://www.fantasypros.com/mlb/projections/2b.php",
    "3B": "https://www.fantasypros.com/mlb/projections/3b.php",
    "SS": "https://www.fantasypros.com/mlb/projections/ss.php",
    "OF": "https://www.fantasypros.com/mlb/projections/of.php",
    "DH": "https://www.fantasypros.com/mlb/projections/util.php",
}

PITCHER_URLS = {
    "SP": "https://www.fantasypros.com/mlb/projections/sp.php",
    "RP": "https://www.fantasypros.com/mlb/projections/rp.php",
}

# Map FantasyPros column headers -> our internal column names
BATTER_COL_MAP = {
    "Player":  "Name",
    "AB":      "AB",
    "R":       "R",
    "HR":      "HR",
    "RBI":     "RBI",
    "SB":      "SB",
    "AVG":     "AVG",
    "H":       "H",
    "2B":      "2B",
    "3B":      "3B",
    "BB":      "BB",
    "SO":      "K",      # strikeouts = K
    "K":       "K",
}

PITCHER_COL_MAP = {
    "Player":  "Name",
    "IP":      "IP",
    "W":       "W",
    "L":       "L",
    "ERA":     "ERA",
    "WHIP":    "WHIP",
    "SO":      "K_pitch",
    "K":       "K_pitch",
    "SV":      "SV",
    "HLD":     "HLD",
    "HD":      "HLD",
    "QS":      "QS",
    "ER":      "ER",
    "H":       "H_allowed",
    "BB":      "BB_issued",
    "CG":      "CG",
}


def scrape_table(url: str, pos: str, col_map: dict) -> pd.DataFrame:
    """Scrape a single FantasyPros projection page."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"id": "data"})
    if table is None:
        print(f"  ⚠ No table found at {url}")
        return pd.DataFrame()

    # Parse headers
    headers_raw = [th.text.strip() for th in table.find("thead").find_all("th")]

    rows = []
    for tr in table.find("tbody").find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 2:
            continue
        row = {}
        for i, th in enumerate(headers_raw):
            if i < len(cells):
                text = cells[i].text.strip()
                # Clean player name (remove team suffix like " - NYY")
                if th == "Player":
                    name_tag = cells[i].find("a")
                    text = name_tag.text.strip() if name_tag else text
                    text = text.split(" - ")[0].strip()
                row[th] = text
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Rename columns to internal names
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Keep only mapped columns that exist
    keep = ["Name"] + [v for v in col_map.values() if v != "Name" and v in df.columns]
    keep = list(dict.fromkeys(keep))  # dedupe preserving order
    df = df[[c for c in keep if c in df.columns]].copy()

    # Convert numeric columns
    for col in df.columns:
        if col != "Name":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Position"] = pos
    return df


def fetch_fantasypros_projections(out_path: str = "data/fantasypros_projections.csv") -> pd.DataFrame:
    all_dfs = []

    print("Fetching FantasyPros batter projections...")
    for pos, url in BATTER_URLS.items():
        print(f"  {pos}...", end=" ")
        try:
            df = scrape_table(url, pos, BATTER_COL_MAP)
            if not df.empty:
                all_dfs.append(df)
                print(f"{len(df)} players")
            else:
                print("empty")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.5)  # be polite

    print("\nFetching FantasyPros pitcher projections...")
    for pos, url in PITCHER_URLS.items():
        print(f"  {pos}...", end=" ")
        try:
            df = scrape_table(url, pos, PITCHER_COL_MAP)
            if not df.empty:
                all_dfs.append(df)
                print(f"{len(df)} players")
            else:
                print("empty")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.5)

    if not all_dfs:
        print("⚠ No data fetched.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)

    # Drop duplicate players (e.g. OF appears in multiple OF pages)
    combined = combined.drop_duplicates(subset="Name", keep="first")

    combined.to_csv(out_path, index=False)
    print(f"\n✓ Saved {len(combined)} players to {out_path}")
    return combined


if __name__ == "__main__":
    df = fetch_fantasypros_projections()
    print(df.head(10).to_string(index=False))
