def calculate_points(row):
    # Check if hitter
    if row["Position"] in ["C","1B","2B","3B","SS","OF","CI","MI","DH"]:
        # Total bases
        singles = row["H"] - row["2B"] - row["3B"] - row["HR"]
        TB = singles + 2*row["2B"] + 3*row["3B"] + 4*row["HR"]
        # Points = TB + R + RBI + BB + SB
        points = TB + row["R"] + row["RBI"] + row["BB"] + row["SB"]
    # Check if pitcher
    elif row["Position"] in ["SP","RP"]:
        points = (
            row["IP"]
            + row["K"]
            + 2*row["QS"]
            + 5*row["SV"]
            + 2*row["HLD"]
        )
    else:
        points = 0

    return points
