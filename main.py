import pandas as pd
from src.scoring import calculate_points
from src.scarcity import compute_vorp
from src.rank import merge_adp, compute_value_score, build_draft_board
from src.export import export_html, export_csv
import os

def load_exclusions(path: str = "data/injured_out.csv") -> list:
    try:
        df = pd.read_csv(path)
        names = df["Name"].tolist()
        print(f"Excluding {len(names)} players: {', '.join(names)}")
        return names
    except FileNotFoundError:
        return []

def apply_position_overrides(df: pd.DataFrame, path: str = "data/position_overrides.csv") -> pd.DataFrame:
    """Override positions for misclassified players."""
    try:
        overrides = pd.read_csv(path)
        for _, row in overrides.iterrows():
            mask = df["Name"] == row["Name"]
            if mask.any():
                old = df.loc[mask, "Position"].values[0]
                df.loc[mask, "Position"] = row["Position"]
                print(f"  Position override: {row['Name']} {old} -> {row['Position']}")
        return df
    except FileNotFoundError:
        return df

def main():
    df = pd.read_csv("data/projections.csv")

    # Remove excluded players
    excluded = load_exclusions("data/injured_out.csv")
    if excluded:
        df = df[~df["Name"].isin(excluded)].reset_index(drop=True)

    # Fix misclassified positions
    print("Applying position overrides...")
    df = apply_position_overrides(df)

    # For pitchers, remap K_pitch -> K before scoring
    def calculate_points_row(row):
        if row["Position"] in {"SP", "RP", "P"}:
            row = row.copy()
            row["K"] = row.get("K_pitch", 0)
        return calculate_points(row)

    df["projected_points"] = df.apply(calculate_points_row, axis=1)

    df = compute_vorp(df, eligibility_path="data/espn_eligibility.csv")
    df = merge_adp(df, adp_path="data/adp.csv")
    df = compute_value_score(df)

    board = build_draft_board(df)

    pd.set_option("display.max_rows", 35)
    pd.set_option("display.width", 130)
    print("\n=== FANTASY DRAFT BOARD (Top 35) ===\n")
    print(board.head(35).to_string(index=False))

    os.makedirs("output", exist_ok=True)
    export_csv(board, path="output/draft_board.csv")
    export_html(board, path="output/draft_board.html")
    print("\n✓ Exported: output/draft_board.csv")
    print("✓ Exported: output/draft_board.html")

if __name__ == "__main__":
    main()
