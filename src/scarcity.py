import pandas as pd

TEAMS = 12

STARTERS = {
    "C":  1 * TEAMS,   # 12
    "1B": 1 * TEAMS,   # 12
    "2B": 1 * TEAMS,   # 12
    "3B": 1 * TEAMS,   # 12
    "SS": 1 * TEAMS,   # 12
    "OF": 4 * TEAMS,   # 48
    "DH": 1 * TEAMS,   # 12
    "SP": 5 * TEAMS,   # 60  — 5 SP slots per team
    "RP": 2 * TEAMS,   # 24  — 2 RP slots per team
}


def load_eligibility(path: str = "data/espn_eligibility.csv") -> dict:
    try:
        df = pd.read_csv(path)
        eligibility = {}
        for _, row in df.iterrows():
            name    = row["Name"]
            primary = row.get("Primary_Position", "")
            extras  = str(row.get("Eligible_Positions", ""))
            all_pos = [primary] if primary else []
            if extras and extras != "nan":
                all_pos += [p.strip() for p in extras.split(",") if p.strip()]
            eligibility[name] = list(dict.fromkeys(all_pos))
        print(f"✓ Loaded eligibility for {len(eligibility)} players")
        return eligibility
    except FileNotFoundError:
        print("⚠ No eligibility file found — using single position per player")
        return {}


def get_all_positions(player_name: str, primary_pos: str, eligibility: dict) -> list:
    if player_name in eligibility:
        positions = eligibility[player_name]
        if primary_pos not in positions:
            positions = [primary_pos] + positions
        return positions
    return [primary_pos]


def compute_vorp(df: pd.DataFrame, eligibility_path: str = "data/espn_eligibility.csv") -> pd.DataFrame:
    """
    Compute VORP with split SP/RP slots (5 SP + 2 RP per team).
    SP and RP now have separate replacement levels — closers compete
    only against other closers for 24 slots, not 84 combined pitcher slots.
    """
    df = df.copy()
    eligibility = load_eligibility(eligibility_path)

    # Build position pools
    pos_pools = {pos: [] for pos in STARTERS}

    for _, row in df.iterrows():
        all_pos = get_all_positions(row["Name"], row["Position"], eligibility)
        for pos in all_pos:
            if pos in pos_pools:
                pos_pools[pos].append(row["projected_points"])

    # DH is a flex hitter slot — use OF replacement level since any hitter can DH.
    # This prevents a single player like Ohtani from having 0 VORP due to tiny pool.
    pos_pools["DH"] = pos_pools["OF"].copy()

    # Compute replacement levels
    replacement_levels = {}
    for pos, num_starters in STARTERS.items():
        points = sorted(pos_pools[pos], reverse=True)
        if len(points) >= num_starters:
            replacement_levels[pos] = points[num_starters - 1]
        elif points:
            replacement_levels[pos] = points[-1]
        else:
            replacement_levels[pos] = 0
        print(f"  Replacement level {pos:3}: {replacement_levels[pos]:.1f} pts  ({len(points)} players, {num_starters} slots)")

    # Assign each player VORP at their best position
    vorp_list     = []
    best_pos_list = []

    for _, row in df.iterrows():
        all_pos  = get_all_positions(row["Name"], row["Position"], eligibility)
        best_vorp = None
        best_pos  = row["Position"]

        for pos in all_pos:
            if pos not in replacement_levels:
                continue
            vorp = row["projected_points"] - replacement_levels[pos]
            if best_vorp is None or vorp > best_vorp:
                best_vorp = vorp
                best_pos  = pos

        vorp_list.append(round(best_vorp, 1) if best_vorp is not None else 0.0)
        best_pos_list.append(best_pos)

    df["VORP"]     = vorp_list
    df["Best_Pos"] = best_pos_list

    df["Eligibility"] = df["Name"].apply(
        lambda n: "/".join(eligibility.get(n, [])) if n in eligibility else df.loc[df["Name"] == n, "Position"].values[0]
    )

    df = df.sort_values("VORP", ascending=False).reset_index(drop=True)
    return df
