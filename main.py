import streamlit as st

from warican import optimize_fee


st.set_page_config(
    page_title="割り勘最適化",
    page_icon="¥",
    layout="wide",
)


def main():
    st.title("割り勘最適化")
    st.caption("等級ごとの人数と条件から、傾斜をつけた集金額を計算します。")

    total_payment = st.number_input(
            "支払総額（円）",
            min_value=1_000,
            value=100_000,
            step=1_000,
        )
    
    grade_count = st.number_input(
        "等級数",
        min_value=3,
        max_value=10,
        value=4,
        step=1,
        help="人数は下位等級から上位等級の順に入力してください。",
    )

    with st.sidebar:
        st.header("計算条件")
        unit = st.number_input(
            "集金額の単位（円）",
            min_value=1,
            value=500,
            step=100,
            help="支払総額の下3桁が251~749で、奇数人の等級がある場合は500がおすすめ。他は1000がおすすめ。"
        )
        min_payment = st.number_input(
            "最低支払額（円）",
            min_value=0,
            value=unit,
            step=unit,
        )
        max_payment = st.number_input(
            "最高支払額（円）",
            min_value=min_payment + unit * grade_count,
            value=total_payment,
            step=unit,
        )
        min_recovery_rate = st.slider(
            "最低回収率",
            min_value=90.0,
            max_value=100.0,
            value=99.0,
            step=1.0,
            format="%.1f%%",
        ) / 100
        beta = st.slider(
            "傾斜の上限パラメータ β",
            min_value=0.50,
            max_value=1.50,
            value=1.00,
            step=0.01,
            format="%.2f",
            help="最高等級と2番目に高い等級の一人当たりの支払金額の差 ≦ β(最低等級と3番目に低い等級の一人当たりの支払金額の差)"
        )

    with st.form("fee_form"):
        st.subheader("等級と人数")
        st.caption("上位等級ほど右側に入力します。")
        grade_columns = st.columns(grade_count)
        grade_names = []
        grade_counts = []

        for index, column in enumerate(grade_columns):
            with column:
                grade_names.append(
                    st.text_input(
                        "等級名",
                        value=f"等級 {index + 1}",
                        key=f"grade_name_{index}",
                    )
                )
                grade_counts.append(
                    st.number_input(
                        "人数",
                        min_value=1,
                        value=1,
                        step=1,
                        key=f"grade_count_{index}",
                    )
                )

        submitted = st.form_submit_button("集金額を計算", type="primary")

    if not submitted:
        st.info("条件を入力して「集金額を計算」を押してください。")
        return

    results_summary = st.empty()
    results_container = st.container()

    def show_solution(solution, solution_index):
        with results_container:
            with st.expander(
                f"最適解 {solution_index}",
                expanded=solution_index == 1,
            ):
                rows = []
                for index, (name, count, fee) in enumerate(
                    zip(grade_names, grade_counts, solution["fees"])
                ):
                    rows.append(
                        {
                            "等級": name or f"等級 {index + 1}",
                            "人数": count,
                            "1人あたり": f"¥{fee:,}",
                            "等級間差額": (
                                "-"
                                if index == 0
                                else f"¥{solution['differences'][index - 1]:,}"
                            ),
                            "等級合計": f"¥{count * fee:,}",
                        }
                    )
                st.dataframe(rows, hide_index=True, use_container_width=True)

    def on_solution(solutions):
        solution_index = len(solutions)
        results_summary.info(
            f"最適解を{solution_index}件見つけました。引き続き探索中です..."
        )
        show_solution(solutions[-1], solution_index)

    try:
        result = optimize_fee(
            n=grade_counts,
            total_payment=total_payment,
            unit=unit,
            min_recovery_rate=min_recovery_rate,
            beta=beta,
            on_solution=on_solution,
            min_payment=min_payment,
            max_payment=max_payment
        )
    except (RuntimeError, ValueError) as error:
        st.error(str(error))
        return

    solutions = result["solutions"]
    results_summary.success(f"最適解を{len(solutions)}件見つけました。")
    st.subheader(f"計算結果（{len(solutions)}通りの最適解）")
    metric_columns = st.columns(4)
    metric_columns[0].metric("総回収額", f"¥{solutions[0]['total_collection']:,}")
    metric_columns[1].metric("支払総額との差", f"¥{solutions[0]['difference']:,}")
    metric_columns[2].metric("回収率", f"{solutions[0]['recovery_rate']:.2%}")
    metric_columns[3].metric("ステータス", result["status"])

    if solutions[0]["total_collection"] > solutions[0]["total_payment"]:
        st.success("支払総額を上回る結果です。")
    elif solutions[0]["total_collection"] == solutions[0]["total_payment"]:
            st.success("支払総額ちょうどを回収する結果です。")
    else:
        st.warning("支払総額を下回る結果です。最低回収率の条件は満たしています。")


if __name__ == "__main__":
    main()
