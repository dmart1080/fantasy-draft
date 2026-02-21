"""
Combines projection data from FantasyPros, FanGraphs, and Baseball Savant/BBRef
into a single weighted consensus projections file.

Weights: FantasyPros=0.45, FanGraphs=0.35, BBRef/Savant=0.20
(FantasyPros is already a consensus, so it gets the most weight)

Run after all three fetch scripts:
    python scripts/fetch_fantasypros_projections.py
    python scripts/fetch_fangraphs_projections.py
    python scripts/fetch_bbref_projections.py
    python scripts/combine_projections.py

Outputs:
    data/projections.csv   <- replaces the hand-built file, used by main.py
"""

import pandas as pd
import numpy as np
from thefuzz import process as fuzz_process

# Source files
FP_PATH    = "data/fantasypros_projections.csv"
FG_PATH    = "data/fangraphs_projections.csv"
BR_PATH    = "data/bbref_projections.csv"

OUT_PATH   = "data/projections.csv"

# Source weights (must sum to 1.0 across available sources)
WEIGHTS = {
    "fp": 0.45,
    "fg": 0.35,
    "br": 0.20,
}

FUZZY_THRESHOLD = 88

# Stats we care about — map to internal column names used by scoring.py
# Batters
BATTER_STATS = ["H", "2B", "3B", "HR", "R", "RBI", "BB", "K", "SB"]
# Pitchers
PITCHER_STATS = ["IP", "ER", "K_pitch", "QS", "SV", "HLD", "H_allowed", "BB_issued", "CG", "NH", "PG", "GS"]

# Rare events — set to 0 (can't project these reliably)
RARE_EVENTS = {"CYC": 0, "GSHR": 0, "NH": 0, "PG": 0}


def fuzzy_match_name(name: str, candidates: list, threshold: int = FUZZY_THRESHOLD):
    result = fuzz_process.extractOne(name, candidates)
    if result and result[1] >= threshold:
        return result[0]
    return None


def normalize_weights(available_sources: list) -> dict:
    """Redistribute weights if a source is missing."""
    total = sum(WEIGHTS[s] for s in available_sources)
    return {s: WEIGHTS[s] / total for s in available_sources}


def load_source(path: str, label: str) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(path)
        print(f"✓ Loaded {label}: {len(df)} players")
        return df
    except FileNotFoundError:
        print(f"⚠ {label} not found at {path} — skipping")
        return None


def align_to_master(master_names: list, source_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each name in master_names, find the best fuzzy match in source_df.
    Returns a DataFrame indexed by master_names with source stats.
    """
    source_names = source_df["Name"].tolist()
    rows = []

    for name in master_names:
        match = fuzzy_match_name(name, source_names)
        if match:
            row = source_df[source_df["Name"] == match].iloc[0].to_dict()
            row["_matched_name"] = match
        else:
            row = {"Name": name, "_matched_name": None}
        row["_master_name"] = name
        rows.append(row)

    return pd.DataFrame(rows).set_index("_master_name")


def weighted_average_stats(sources: dict, weights: dict, stat_cols: list) -> pd.DataFrame:
    """
    Given multiple aligned DataFrames, compute weighted average for each stat.
    sources: {label: df} where df is indexed by master player name
    weights: {label: weight}
    stat_cols: list of stat column names to average
    """
    master_names = list(list(sources.values())[0].index)
    result = pd.DataFrame(index=master_names)

    for stat in stat_cols:
        weighted_sum = pd.Series(0.0, index=master_names)
        weight_total = pd.Series(0.0, index=master_names)

        for label, df in sources.items():
            if stat not in df.columns:
                continue
            w = weights[label]
            vals = pd.to_numeric(df[stat], errors="coerce").fillna(np.nan)
            # Only include in weighted avg where we have data
            has_data = vals.notna()
            weighted_sum[has_data] += vals[has_data] * w
            weight_total[has_data] += w

        # Normalize by actual weight available
        result[stat] = (weighted_sum / weight_total.replace(0, np.nan)).round(1).fillna(0)

    return result


def infer_position(fp_df, fg_df, br_df, name: str) -> str:
    """Get position from whichever source has it."""
    for df in [fp_df, fg_df, br_df]:
        if df is None or "Position" not in df.columns:
            continue
        match = df[df["Name"] == name]
        if not match.empty:
            pos = match.iloc[0].get("Position", "")
            if pos and pos not in ("BAT", "PIT", ""):
                return pos
    # Fall back to BAT/PIT label
    for df in [fp_df, fg_df, br_df]:
        if df is None or "Position" not in df.columns:
            continue
        match = df[df["Name"] == name]
        if not match.empty:
            return match.iloc[0].get("Position", "")
    return ""


def combine_projections(
    fp_path=FP_PATH,
    fg_path=FG_PATH,
    br_path=BR_PATH,
    out_path=OUT_PATH,
) -> pd.DataFrame:

    fp_df = load_source(fp_path, "FantasyPros")
    fg_df = load_source(fg_path, "FanGraphs")
    br_df = load_source(br_path, "BBRef/Savant")

    available = {k: df for k, df in [("fp", fp_df), ("fg", fg_df), ("br", br_df)] if df is not None}

    if not available:
        raise RuntimeError("No projection sources available. Run fetch scripts first.")

    weights = normalize_weights(list(available.keys()))
    print(f"\nUsing weights: { {k: f'{v:.0%}' for k, v in weights.items()} }")

    # Build master player list from FantasyPros (or best available)
    keys = list(available.keys()); primary = available[keys[0]]
    master_names = primary["Name"].tolist()
    print(f"\nMaster player list: {len(master_names)} players")

    # --- Separate batters and pitchers ---
    def is_pitcher(df, name):
        if df is None or "Position" not in df.columns:
            return False
        match = df[df["Name"] == name]
        if match.empty:
            return False
        pos = str(match.iloc[0].get("Position", ""))
        return pos in ("SP", "RP", "P", "PIT") or "K_pitch" in match.columns

    # Build combined output rows
    rows = []
    print("Building consensus projections...")

    for name in master_names:
        row = {"Name": name}

        # Determine if pitcher or batter from position
        pos = infer_position(fp_df, fg_df, br_df, name)
        pitcher = pos in ("SP", "RP", "P", "PIT") or (pos == "" and any(
            df is not None and name in df["Name"].values and
            df[df["Name"] == name].iloc[0].get("Position", "") in ("SP", "RP", "P", "PIT")
            for df in [fp_df, fg_df, br_df]
        ))

        # Assign clean position
        if pos in ("BAT", ""):
            pos = "OF"  # default; will be overridden if source has specific pos
        row["Position"] = pos

        # Get stats from each source
        stat_cols = PITCHER_STATS if pitcher else BATTER_STATS
        stat_vals = {stat: [] for stat in stat_cols}
        stat_weights = {stat: [] for stat in stat_cols}

        for label, df in available.items():
            match = fuzzy_match_name(name, df["Name"].tolist())
            if not match:
                continue
            src_row = df[df["Name"] == match].iloc[0]
            for stat in stat_cols:
                val = pd.to_numeric(src_row.get(stat, np.nan), errors="coerce")
                if not np.isnan(val):
                    stat_vals[stat].append(val * weights[label])
                    stat_weights[stat].append(weights[label])

        for stat in stat_cols:
            if stat_weights[stat]:
                total_w = sum(stat_weights[stat])
                row[stat] = round(sum(stat_vals[stat]) / total_w, 1)
            else:
                row[stat] = 0

        # Fill rare events with 0
        for stat, val in RARE_EVENTS.items():
            row[stat] = val

        # Ensure all required columns exist
        all_batter_cols = BATTER_STATS + ["CYC", "GSHR"]
        all_pitcher_cols = PITCHER_STATS

        if not pitcher:
            for c in all_batter_cols:
                row.setdefault(c, 0)
            for c in all_pitcher_cols:
                row.setdefault(c, 0)
            # Rename K_pitch to 0 for batters
            row["K_pitch"] = 0
        else:
            for c in all_pitcher_cols:
                row.setdefault(c, 0)
            for c in all_batter_cols:
                row.setdefault(c, 0)
            row["K"] = 0

        rows.append(row)

    df_out = pd.DataFrame(rows)

    # Final column order matching what main.py / scoring.py expects
    final_cols = [
        "Name", "Position",
        # Batter stats
        "H", "2B", "3B", "HR", "R", "RBI", "BB", "K", "SB", "CYC", "GSHR",
        # Pitcher stats
        "IP", "ER", "K_pitch", "QS", "SV", "HLD", "GS", "H_allowed", "BB_issued", "CG", "NH", "PG",
    ]
    df_out = df_out[[c for c in final_cols if c in df_out.columns]]

    df_out.to_csv(out_path, index=False)
    print(f"\n✓ Consensus projections saved: {len(df_out)} players → {out_path}")
    print(df_out.head(10).to_string(index=False))
    return df_out


if __name__ == "__main__":
    combine_projections()
