"""
Combines FantasyPros and ESPN ADP into a consensus ADP file.
Run after both fetch scripts have been run.

    python scripts/combine_adp.py
"""

import pandas as pd
from thefuzz import process as fuzz_process

FP_PATH   = "data/fantasypros_adp.csv"
ESPN_PATH = "data/espn_adp.csv"
OUT_PATH  = "data/adp.csv"
FUZZY_THRESHOLD = 88


def fuzzy_merge(df_left, df_right, left_on, right_on, threshold=FUZZY_THRESHOLD):
    right_names = df_right[right_on].tolist()
    matched_rows = []

    for _, row in df_left.iterrows():
        query = row[left_on]
        result = fuzz_process.extractOne(query, right_names)
        if result is None:
            matched_rows.append(row.to_dict())
            continue

        # thefuzz returns (match, score) or (match, score, key) depending on version
        match = result[0]
        score = result[1]

        if score >= threshold:
            right_row = df_right[df_right[right_on] == match].iloc[0]
            merged = {**row.to_dict(), **right_row.to_dict()}
            merged["match_score"] = score
            matched_rows.append(merged)
        else:
            matched_rows.append(row.to_dict())

    return pd.DataFrame(matched_rows)


def combine_adp(fp_path=FP_PATH, espn_path=ESPN_PATH, out_path=OUT_PATH):
    sources = {}
    try:
        sources["fp"] = pd.read_csv(fp_path)
        print(f"✓ Loaded FantasyPros ADP: {len(sources['fp'])} players")
    except FileNotFoundError:
        print(f"⚠ {fp_path} not found")

    try:
        sources["espn"] = pd.read_csv(espn_path)
        print(f"✓ Loaded ESPN ADP: {len(sources['espn'])} players")
    except FileNotFoundError:
        print(f"⚠ {espn_path} not found")

    if not sources:
        raise RuntimeError("No ADP source files found.")

    if len(sources) == 1:
        key = list(sources.keys())[0]
        df = sources[key].copy()
        adp_col = "ADP_FP" if key == "fp" else "ADP_ESPN"
        df = df.rename(columns={adp_col: "ADP"})[["Name", "ADP"]]
        df.to_csv(out_path, index=False)
        print(f"✓ Saved {len(df)} players to {out_path}")
        return df

    fp_df   = sources["fp"][["Name", "ADP_FP"]].copy()
    espn_df = sources["espn"][["Name", "ADP_ESPN"]].copy()

    print(f"Fuzzy-merging {len(fp_df)} FantasyPros players against {len(espn_df)} ESPN players...")
    merged = fuzzy_merge(fp_df, espn_df, left_on="Name", right_on="Name")

    adp_cols = [c for c in ["ADP_FP", "ADP_ESPN"] if c in merged.columns]
    merged["ADP"] = merged[adp_cols].mean(axis=1).round(1)

    result = merged[["Name", "ADP"] + adp_cols].sort_values("ADP").reset_index(drop=True)
    result.to_csv(out_path, index=False)
    print(f"✓ Consensus ADP saved: {len(result)} players → {out_path}")

    if "match_score" in merged.columns:
        low_conf = merged[merged.get("match_score", pd.Series(dtype=float)) < 95][["Name", "match_score"]].dropna()
        if not low_conf.empty:
            print(f"\n⚠ {len(low_conf)} fuzzy matches below 95% confidence:")
            print(low_conf.head(20).to_string(index=False))

    print(f"\n=== Consensus ADP (Top 30) ===")
    print(result.head(30).to_string(index=False))
    return result


if __name__ == "__main__":
    combine_adp()
