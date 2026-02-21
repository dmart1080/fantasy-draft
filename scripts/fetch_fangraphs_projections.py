"""
Fetches FanGraphs Steamer projections for batters and pitchers.
FanGraphs provides downloadable CSV exports — this script pulls them directly.
Saves to data/fangraphs_projections.csv

Install deps:
    pip install requests pandas

Run:
    python scripts/fetch_fangraphs_projections.py

Note: FanGraphs has a public CSV export endpoint that doesn't require login.
We use the 'steamer' system by default. Change PROJ_SYSTEM to 'zips' or 'atc' if preferred.
"""

import requests
import pandas as pd
import io

PROJ_SYSTEM = "steamer"   # options: steamer, zips, atc, thebat, fangraphsdc

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# FanGraphs CSV export URLs
# pos=all gets all players; type=1 = batters, type=1 pitcher side varies
BATTER_URL = (
    "https://www.fangraphs.com/projections.aspx"
    f"?pos=all&stats=bat&type={PROJ_SYSTEM}&team=0&lg=all&players=0&download=1"
)

PITCHER_URL = (
    "https://www.fangraphs.com/projections.aspx"
    f"?pos=all&stats=pit&type={PROJ_SYSTEM}&team=0&lg=all&players=0&download=1"
)

# Fallback: direct export API (more reliable)
BATTER_API  = f"https://www.fangraphs.com/api/projections?type={PROJ_SYSTEM}&stats=bat&pos=all&team=0&players=0"
PITCHER_API = f"https://www.fangraphs.com/api/projections?type={PROJ_SYSTEM}&stats=pit&pos=all&team=0&players=0"

# Column mapping: FanGraphs name -> our internal name
BATTER_COL_MAP = {
    "PlayerName": "Name",
    "Name":       "Name",
    "G":          "G",
    "AB":         "AB",
    "PA":         "PA",
    "H":          "H",
    "2B":         "2B",
    "3B":         "3B",
    "HR":         "HR",
    "R":          "R",
    "RBI":        "RBI",
    "BB":         "BB",
    "SO":         "K",
    "K":          "K",
    "SB":         "SB",
    "CS":         "CS",
    "AVG":        "AVG",
    "OBP":        "OBP",
    "SLG":        "SLG",
}

PITCHER_COL_MAP = {
    "PlayerName": "Name",
    "Name":       "Name",
    "W":          "W",
    "L":          "L",
    "GS":         "GS",
    "G":          "G",
    "SV":         "SV",
    "HLD":        "HLD",
    "IP":         "IP",
    "H":          "H_allowed",
    "ER":         "ER",
    "HR":         "HR_allowed",
    "BB":         "BB_issued",
    "SO":         "K_pitch",
    "K":          "K_pitch",
    "ERA":        "ERA",
    "WHIP":       "WHIP",
    "QS":         "QS",
    "CG":         "CG",
}


def fetch_json_api(url: str, col_map: dict, pos_label: str) -> pd.DataFrame:
    """Try FanGraphs JSON API endpoint."""
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    data = resp.json()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Ensure Name column exists
    if "Name" not in df.columns:
        for alt in ["PlayerName", "name", "player_name"]:
            if alt in df.columns:
                df = df.rename(columns={alt: "Name"})
                break

    if "Name" not in df.columns:
        print(f"  ⚠ Could not find Name column in {pos_label} data. Columns: {list(df.columns)}")
        return pd.DataFrame()

    # Convert numerics
    for col in df.columns:
        if col != "Name":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Position"] = pos_label
    return df


def fetch_csv_download(url: str, col_map: dict, pos_label: str) -> pd.DataFrame:
    """Fallback: try CSV download endpoint."""
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text))
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename)

    if "Name" not in df.columns:
        return pd.DataFrame()

    for col in df.columns:
        if col != "Name":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Position"] = pos_label
    return pd.DataFrame()


def fetch_fangraphs_projections(
    out_path: str = "data/fangraphs_projections.csv",
    proj_system: str = PROJ_SYSTEM,
) -> pd.DataFrame:
    all_dfs = []

    batter_api  = f"https://www.fangraphs.com/api/projections?type={proj_system}&stats=bat&pos=all&team=0&players=0"
    pitcher_api = f"https://www.fangraphs.com/api/projections?type={proj_system}&stats=pit&pos=all&team=0&players=0"

    print(f"Fetching FanGraphs {proj_system.upper()} batter projections...")
    try:
        df_bat = fetch_json_api(batter_api, BATTER_COL_MAP, "BAT")
        if not df_bat.empty:
            print(f"  ✓ {len(df_bat)} batters")
            all_dfs.append(df_bat)
        else:
            raise ValueError("Empty response")
    except Exception as e:
        print(f"  ⚠ JSON API failed ({e}), trying CSV download...")
        try:
            batter_csv = f"https://www.fangraphs.com/projections.aspx?pos=all&stats=bat&type={proj_system}&team=0&lg=all&players=0&download=1"
            df_bat = fetch_csv_download(batter_csv, BATTER_COL_MAP, "BAT")
            if not df_bat.empty:
                print(f"  ✓ {len(df_bat)} batters (CSV)")
                all_dfs.append(df_bat)
        except Exception as e2:
            print(f"  ✗ CSV also failed: {e2}")

    print(f"Fetching FanGraphs {proj_system.upper()} pitcher projections...")
    try:
        df_pit = fetch_json_api(pitcher_api, PITCHER_COL_MAP, "PIT")
        if not df_pit.empty:
            print(f"  ✓ {len(df_pit)} pitchers")
            all_dfs.append(df_pit)
        else:
            raise ValueError("Empty response")
    except Exception as e:
        print(f"  ⚠ JSON API failed ({e}), trying CSV download...")
        try:
            pitcher_csv = f"https://www.fangraphs.com/projections.aspx?pos=all&stats=pit&type={proj_system}&team=0&lg=all&players=0&download=1"
            df_pit = fetch_csv_download(pitcher_csv, PITCHER_COL_MAP, "PIT")
            if not df_pit.empty:
                print(f"  ✓ {len(df_pit)} pitchers (CSV)")
                all_dfs.append(df_pit)
        except Exception as e2:
            print(f"  ✗ CSV also failed: {e2}")

    if not all_dfs:
        print("⚠ No FanGraphs data fetched.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset="Name", keep="first")
    combined.to_csv(out_path, index=False)
    print(f"\n✓ Saved {len(combined)} players to {out_path}")
    return combined


if __name__ == "__main__":
    df = fetch_fangraphs_projections()
    if not df.empty:
        print(df.head(10).to_string(index=False))
