def calculate_points(row) -> float:
    """
    Calculate projected fantasy points based on actual league scoring settings.

    BATTING:
      R=1, TB=1, RBI=1, BB=1, K=-1, SB=1, CYC=8, GSHR=4

    PITCHING:
      IP=3, ER=-2, K=1, SV=5, H=-1, BB=-1, QS=2, CG=4, NH=6, PG=10, HD=2
    """
    hitter_positions = {"C", "1B", "2B", "3B", "SS", "OF", "CI", "MI", "DH"}
    pitcher_positions = {"SP", "RP", "P"}

    if row["Position"] in hitter_positions:
        singles = row["H"] - row["2B"] - row["3B"] - row["HR"]
        TB = singles + 2 * row["2B"] + 3 * row["3B"] + 4 * row["HR"]
        return (
            row["R"]             * 1
            + TB                 * 1
            + row["RBI"]         * 1
            + row["BB"]          * 1
            + row["K"]           * -1
            + row["SB"]          * 1
            + row.get("CYC", 0)  * 8
            + row.get("GSHR", 0) * 4
        )

    elif row["Position"] in pitcher_positions:
        return (
            row["IP"]                                       * 3    # changed from 1 to 3
            + row.get("ER", 0)                              * -2
            + row["K"]                                      * 1
            + row["SV"]                                     * 5
            + row.get("H_allowed", row.get("HA", 0))        * -1
            + row.get("BB_issued", row.get("BBI", 0))       * -1
            + row["QS"]                                     * 2
            + row.get("CG", 0)                              * 4
            + row.get("NH", 0)                              * 6
            + row.get("PG", 0)                              * 10
            + row["HLD"]                                    * 2
        )

    return 0.0
