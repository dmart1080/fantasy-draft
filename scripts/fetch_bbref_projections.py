"""
Fetches Baseball Reference PECOTA-style projections.
Note: Baseball Reference doesn't have a public projection API, but they publish
Marcel projections and partner with Baseball Prospectus.

This script fetches from the Baseball Reference / BR Bullpen projection pages.
If BR projections aren't available, it falls back to pulling from
baseballsavant.mlb.com Statcast expected stats as a proxy.

Install deps:
    pip install requests beautifulsoup4 pandas

Run:
    python scripts/fetch_bbref_projections.py
"""

import requests
import pandas as pd
import io
import json
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Baseball Savant leaderboard CSV export (xStats - expected stats based on Statcast)
# These aren't projections per se, but xBA/xSLG/xwOBA are strong forward-looking indicators
SAVANT_BATTER_URL = (
    "https://baseballsavant.mlb.com/leaderboard/expected_statistics"
    "?type=batter&year=2024&position=&team=&min=100&csv=true"
)

SAVANT_PITCHER_URL = (
    "https://baseballsavant.mlb.com/leaderboard/expected_statistics"
    "?type=pitcher&year=2024&position=&team=&min=50&csv=true"
)

# Baseball Reference standard stats (2024 actuals as projection baseline)
BBREF_BATTER_URL = "https://www.baseball-reference.com/leagues/majors/2024-standard-batting.shtml"
BBREF_PITCHER_URL = "https://www.baseball-reference.com/leagues/majors/2024-standard-pitching.shtml"

BATTER_COL_MAP = {
    "Name":        "Name",
    "last_name, first_name": "Name",
    "player_name": "Name",
    "G":           "G",
    "AB":          "AB",
    "R":           "R",
    "H":           "H",
    "2B":          "2B",
    "3B":          "3B",
    "HR":          "HR",
    "RBI":         "RBI",
    "SB":          "SB",
    "BB":          "BB",
    "SO":          "K",
    "BA":          "AVG",
    "batting_avg": "AVG",
    "xba":         "xAVG",
    "xslg":        "xSLG",
    "xwoba":       "xwOBA",
}

PITCHER_COL_MAP = {
    "Name":        "Name",
    "player_name": "Name",
    "G":           "G",
    "GS":          "GS",
    "IP":          "IP",
    "H":           "H_allowed",
    "ER":          "ER",
    "HR":          "HR_allowed",
    "BB":          "BB_issued",
    "SO":          "K_pitch",
    "ERA":         "ERA",
    "WHIP":        "WHIP",
    "SV":          "SV",
    "era":         "ERA",
    "xera":        "xERA",
    "xba":         "xBA_against",
}


def fetch_savant_csv(url: str, col_map: dict, pos_label: str) -> pd.DataFrame:
    """Fetch Baseball Savant CSV export."""
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text))

    # Handle "last_name, first_name" column
    if "last_name, first_name" in df.columns:
        df["Name"] = df["last_name, first_name"].apply(
            lambda x: " ".join(reversed([p.strip() for p in str(x).split(",")])) if "," in str(x) else str(x)
        )
        df = df.drop(columns=["last_name, first_name"])
    elif "player_name" in df.columns:
        df["Name"] = df["player_name"]

    rename = {k: v for k, v in col_map.items() if k in df.columns and k != "Name"}
    df = df.rename(columns=rename)

    if "Name" not in df.columns:
        print(f"  ⚠ No Name column found. Columns: {list(df.columns[:10])}")
        return pd.DataFrame()

    for col in df.columns:
        if col != "Name":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Position"] = pos_label
    df["Source"] = "BBSavant_2024"
    return df


def fetch_bbref_table(url: str, col_map: dict, pos_label: str) -> pd.DataFrame:
    """Scrape Baseball Reference standard stats table."""
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # BR uses id="batting_standard" or "pitching_standard"
    table_id = "batting_standard" if "batting" in url else "pitching_standard"
    table = soup.find("table", {"id": table_id})

    if table is None:
        # Try any stats table
        table = soup.find("table", {"class": "stats_table"})

    if table is None:
        print(f"  ⚠ No table found at {url}")
        return pd.DataFrame()

    rows = []
    for tr in table.find_all("tr"):
        # Skip header rows and separator rows
        if tr.get("class") and "thead" in tr.get("class", []):
            continue
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue

        row = {}
        for td in cells:
            col = td.get("data-stat", "")
            if col:
                # Get player name from link if available
                if col == "player":
                    link = td.find("a")
                    row["Name"] = link.text.strip() if link else td.text.strip()
                else:
                    row[col] = td.text.strip()
        if "Name" in row and row["Name"]:
            rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Map BR stat column names to our internal names
    br_col_map = {
        "R": "R", "H": "H", "2B": "2B", "3B": "3B", "HR": "HR",
        "RBI": "RBI", "SB": "SB", "BB": "BB", "SO": "K",
        "batting_avg": "AVG", "IP": "IP", "ER": "ER",
        "hits_allowed": "H_allowed", "bases_on_balls": "BB_issued",
        "strikeouts": "K_pitch", "earned_run_avg": "ERA",
        "whip": "WHIP", "sv": "SV", "G": "G", "GS": "GS",
    }

    df = df.rename(columns=br_col_map)

    for col in df.columns:
        if col != "Name":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Remove league average rows (Name is empty or team abbreviation)
    df = df[df["Name"].str.len() > 3]
    df = df.drop_duplicates(subset="Name", keep="first")

    df["Position"] = pos_label
    df["Source"] = "BBRef_2024"
    return df


def fetch_bbref_projections(out_path: str = "data/bbref_projections.csv") -> pd.DataFrame:
    all_dfs = []

    # Primary: Baseball Savant xStats (2024 actuals + expected stats)
    print("Fetching Baseball Savant batter xStats (2024)...")
    try:
        df = fetch_savant_csv(SAVANT_BATTER_URL, BATTER_COL_MAP, "BAT")
        if not df.empty:
            print(f"  ✓ {len(df)} batters")
            all_dfs.append(df)
    except Exception as e:
        print(f"  ⚠ Savant batters failed: {e}")

    print("Fetching Baseball Savant pitcher xStats (2024)...")
    try:
        df = fetch_savant_csv(SAVANT_PITCHER_URL, PITCHER_COL_MAP, "PIT")
        if not df.empty:
            print(f"  ✓ {len(df)} pitchers")
            all_dfs.append(df)
    except Exception as e:
        print(f"  ⚠ Savant pitchers failed: {e}")

    # Fallback: Baseball Reference 2024 actuals
    if not all_dfs:
        print("\nFalling back to Baseball Reference 2024 actuals...")
        try:
            df = fetch_bbref_table(BBREF_BATTER_URL, BATTER_COL_MAP, "BAT")
            if not df.empty:
                print(f"  ✓ {len(df)} batters (BR)")
                all_dfs.append(df)
        except Exception as e:
            print(f"  ⚠ BR batters failed: {e}")

        try:
            df = fetch_bbref_table(BBREF_PITCHER_URL, PITCHER_COL_MAP, "PIT")
            if not df.empty:
                print(f"  ✓ {len(df)} pitchers (BR)")
                all_dfs.append(df)
        except Exception as e:
            print(f"  ⚠ BR pitchers failed: {e}")

    if not all_dfs:
        print("⚠ No data fetched from any source.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset="Name", keep="first")
    combined.to_csv(out_path, index=False)
    print(f"\n✓ Saved {len(combined)} players to {out_path}")
    return combined


if __name__ == "__main__":
    df = fetch_bbref_projections()
    if not df.empty:
        print(df.head(10).to_string(index=False))
