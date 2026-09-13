import pulp


def optimize_fee(
    n,
    total_payment,
    unit=500,
    min_recovery_rate=0.98,
    beta=0.6,
):
    """
    飲み会の等級別集金額をMILPで最適化する。

    Parameters
    ----------
    n : list[int]
        各等級の人数。
        下位等級 -> 上位等級の順。

    total_payment : int
        支払総額 [円]

    unit : int
        集金額の最小単位 [円]

    min_recovery_rate : float
        最低回収率。
        0.98なら総回収額 >= 支払総額の98%

    beta : float
        傾斜の上限。
        d_{G-1} <= beta * (d_1 + d_2)

    Returns
    -------
    dict
        最適化結果
    """

    G = len(n)

    if G < 3:
        raise ValueError("等級数は3以上にしてください。")

    if any(num <= 0 for num in n):
        raise ValueError("各等級の人数は正である必要があります。")

    if unit <= 0:
        raise ValueError("unitは正にしてください。")

    if not 0 < min_recovery_rate <= 1:
        raise ValueError(
            "min_recovery_rateは0より大きく1以下にしてください。"
        )

    if beta < 0.5:
        raise ValueError(
            "beta < 0.5では、d1 <= ... <= dG-1 <= beta(d1+d2) "
            "を満たせない場合があります。"
        )

    # ============================================================
    # モデル
    # ============================================================

    model = pulp.LpProblem(
        "DrinkingFeeOptimization",
        pulp.LpMinimize,
    )

    # ============================================================
    # 決定変数
    # ============================================================

    # k[g]:
    #   x_g = unit * k[g]
    #
    # 集金額そのものではなく、unit単位の整数として持つ。
    k = [
        pulp.LpVariable(
            f"k_{g}",
            lowBound=0,
            cat=pulp.LpInteger,
        )
        for g in range(G)
    ]

    # 総回収額と支払総額との差の絶対値
    error = pulp.LpVariable(
        "error",
        lowBound=0,
        cat=pulp.LpContinuous,
    )

    # ============================================================
    # 補助式
    # ============================================================

    # 各等級の集金額
    x = [unit * k[g] for g in range(G)]

    # 隣接等級間の差
    d = [x[g + 1] - x[g] for g in range(G - 1)]

    # 総回収額
    total_collection = pulp.lpSum(n[g] * x[g] for g in range(G))

    # ============================================================
    # 目的関数
    #
    # min |総回収額 - 支払総額|
    # ============================================================

    model += error

    # ------------------------------------------------------------
    # |C - P| <= error
    # ------------------------------------------------------------

    model += (total_collection - total_payment <= error)
    model += (total_payment - total_collection <= error)

    # ============================================================
    # 制約
    # ============================================================

    # ------------------------------------------------------------
    # (1) 最低回収率
    #
    # C >= (1-alpha) * P
    # ------------------------------------------------------------

    model += (total_collection >= min_recovery_rate * total_payment)

    # ------------------------------------------------------------
    # (2) 隣接等級間の差 >= unit
    #
    # d_g >= unit
    # ------------------------------------------------------------

    for g in range(G - 1):
        model += (d[g] >= unit)

    # ------------------------------------------------------------
    # (3) 上位等級ほど傾斜を大きくする
    #
    # d_1 <= d_2 <= ... <= d_{G-1}
    # ------------------------------------------------------------

    for g in range(G - 2):
        model += (d[g] <= d[g + 1])

    # ------------------------------------------------------------
    # (4) 傾斜の上限
    #
    # d_{G-1} <= beta * (d_1 + d_2)
    # ------------------------------------------------------------

    model += (d[G - 2] <= beta * (d[0] + d[1]))

    # ============================================================
    # 求解
    # ============================================================

    solver = pulp.PULP_CBC_CMD(msg=True)

    status = model.solve(solver)

    # ============================================================
    # 結果
    # ============================================================

    status_str = pulp.LpStatus[status]

    if status_str != "Optimal":
        raise RuntimeError(f"最適解が得られませんでした: {status_str}")

    # 集金額
    fees = [int(round(pulp.value(x[g]))) for g in range(G)]

    # 等級間差
    differences = [fees[g + 1] - fees[g] for g in range(G - 1)]

    # 総回収額
    collection = sum(
        n[g] * fees[g]
        for g in range(G)
    )

    return {
        "fees": fees,
        "differences": differences,
        "total_collection": collection,
        "total_payment": total_payment,
        "difference": abs(collection - total_payment),
        "recovery_rate": collection / total_payment,
        "status": status_str,
    }


if __name__ == "__main__":

    # ============================================================
    # 使用例
    # ============================================================

    # 下位 -> 上位
    #
    # 一般社員: 10人
    # 主任:      6人
    # 課長:      3人
    # 部長:      1人
    n = [10, 6, 3, 1]

    result = optimize_fee(
        n=n,
        total_payment=100_000,
        unit=500,
        min_recovery_rate=0.98,
        beta=0.6,
    )

    print("\n=== 最適化結果 ===")

    for g, fee in enumerate(result["fees"], start=1):
        print(
            f"Grade {g}: {fee:,} 円"
        )

    print()
    print(
        "等級間差:",
        [f"{d:,} 円" for d in result["differences"]]
    )

    print(
        f"総回収額: {result['total_collection']:,} 円"
    )

    print(
        f"支払総額: {result['total_payment']:,} 円"
    )

    print(
        f"差額:     {result['difference']:,} 円"
    )

    print(
        f"回収率:   {result['recovery_rate']:.2%}"
    )