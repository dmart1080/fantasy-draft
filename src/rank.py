import pandas as pd


def merge_adp(df: pd.DataFrame, adp_path: str = "data/adp.csv") -> pd.DataFrame:
    """
    Merge consensus ADP into the player DataFrame.
    Players without ADP get 999 so they sort last.
    """
    try:
        adp_df = pd.read_csv(adp_path)
        adp_df = adp_df.drop_duplicates(subset="Name", keep="first")
        df = df.merge(adp_df[["Name", "ADP"]], on="Name", how="left")
        df["ADP"] = df["ADP"].fillna(999.0)
    except FileNotFoundError:
        print(f"Warning: ADP file not found at {adp_path}.")
        df["ADP"] = 999.0
    return df


def compute_value_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Value = ADP rank minus VORP rank.
    Positive = steal (going later than their value warrants).
    Negative = reach (going earlier than their value warrants).
    """
    df = df.copy()
    df["VORP_Rank"] = df["VORP"].rank(ascending=False).astype(int)
    df["ADP_Rank"]  = df["ADP"].rank(ascending=True, method="first").astype(int)
    df["Value"]     = df["ADP_Rank"] - df["VORP_Rank"]
    return df


def build_draft_board(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sort by VORP desc, ADP asc as tiebreaker.
    Add Draft_Rank and estimated round (12-team league).
    """
    df = df.sort_values(["VORP", "ADP"], ascending=[False, True]).reset_index(drop=True)
    df["Draft_Rank"] = df.index + 1
    df["Est_Round"]  = ((df["Draft_Rank"] - 1) // 12) + 1

    cols = ["Draft_Rank", "Name", "Position", "projected_points", "VORP", "ADP", "Value", "Est_Round"]
    return df[[c for c in cols if c in df.columns]]
