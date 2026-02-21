import pandas as pd

# Define number of starters per position
STARTERS = {
    "C": 12,
    "1B": 12,
    "2B": 12,
    "SS": 12,
    "3B": 12,
    "OF": 48,   # 4 per team × 12 teams
    "CI": 12,
    "MI": 12,
    "DH": 12,
    "SP": 84,   # 7 per team × 12
    "RP": 24    # example, adjust if needed
}

def compute_vorp(df):
    """
    Input: df with columns 'Name', 'Position', 'projected_points'
    Output: df with new column 'VORP'
    """
    df = df.copy()
    vorp_list = []

    for pos, num_starters in STARTERS.items():
        # Filter players at this position
        pos_df = df[df["Position"] == pos]

        # If fewer players than starters, use lowest as replacement
        if len(pos_df) >= num_starters:
            replacement_points = pos_df["projected_points"].nlargest(num_starters).min()
        else:
            replacement_points = pos_df["projected_points"].min() if len(pos_df) > 0 else 0

        # Compute VORP for players at this position
        df.loc[df["Position"] == pos, "VORP"] = df.loc[df["Position"] == pos, "projected_points"] - replacement_points

    # Fill any missing VORP with 0
    df["VORP"] = df["VORP"].fillna(0)

    # Sort by VORP descending
    df = df.sort_values("VORP", ascending=False).reset_index(drop=True)

    return df
