import pandas as pd
from src.scoring import calculate_points
from src.scarcity import compute_vorp

def main():
    df = pd.read_csv("data/projections.csv")

    # Step 1: calculate projected points
    df["projected_points"] = df.apply(calculate_points, axis=1)

    # Step 2: calculate VORP
    df = compute_vorp(df)

    # Step 3: show top 20 draft candidates
    print(df[["Name", "Position", "projected_points", "VORP"]].head(20))

if __name__ == "__main__":
    main()
