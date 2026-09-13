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

    with st.sidebar:
        st.header("計算条件")
        total_payment = st.number_input(
            "支払総額（円）",
            min_value=1_000,
            value=100_000,
            step=1_000,
        )
        unit = st.number_input(
            "集金額の単位（円）",
            min_value=1,
            value=500,
            step=100,
        )
        min_recovery_rate = st.slider(
            "最低回収率",
            min_value=0.90,
            max_value=1.00,
            value=0.99,
            step=0.01,
            format="%.2f%%",
        )
        beta = st.slider(
            "傾斜の上限パラメータ β",
            min_value=0.50,
            max_value=1.50,
            value=1.00,
            step=0.01,
            format="%.2f",
        )

    grade_count = st.number_input(
        "等級数",
        min_value=3,
        max_value=10,
        value=4,
        step=1,
        help="人数は下位等級から上位等級の順に入力してください。",
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
                        value=max(1, 10 - index * 3),
                        step=1,
                        key=f"grade_count_{index}",
                    )
                )

        submitted = st.form_submit_button("集金額を計算", type="primary")

    if not submitted:
        st.info("条件を入力して「集金額を計算」を押してください。")
        return

    try:
        result = optimize_fee(
            n=grade_counts,
            total_payment=total_payment,
            unit=unit,
            min_recovery_rate=min_recovery_rate,
            beta=beta,
        )
    except (RuntimeError, ValueError) as error:
        st.error(str(error))
        return

    st.subheader("計算結果")
    metric_columns = st.columns(4)
    metric_columns[0].metric("総回収額", f"¥{result['total_collection']:,}")
    metric_columns[1].metric("支払総額との差", f"¥{result['difference']:,}")
    metric_columns[2].metric("回収率", f"{result['recovery_rate']:.2%}")
    metric_columns[3].metric("ステータス", result["status"])

    rows = []
    for index, (name, count, fee) in enumerate(
        zip(grade_names, grade_counts, result["fees"])
    ):
        rows.append(
            {
                "等級": name or f"等級 {index + 1}",
                "人数": count,
                "1人あたり": f"¥{fee:,}",
                "等級間差額": (
                    "-"
                    if index == 0
                    else f"¥{result['differences'][index - 1]:,}"
                ),
                "等級合計": f"¥{count * fee:,}",
            }
        )

    st.dataframe(rows, hide_index=True, use_container_width=True)

    if result["total_collection"] >= result["total_payment"]:
        st.success("支払総額以上を回収する結果です。")
    else:
        st.warning("支払総額を下回る結果です。最低回収率の条件は満たしています。")


if __name__ == "__main__":
    main()
