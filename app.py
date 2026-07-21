import streamlit as st
import pandas as pd
import numpy as np
import pulp
import plotly.express as px

st.set_page_config(
    page_title="MRO 통합 자재 최적화 대시보드",
    page_icon="✈️",
    layout="wide",
)

# ------------------------------------------------------------------
# 1. Design tokens (dataviz palette — categorical slot 1/2, chrome & ink)
# ------------------------------------------------------------------
COLOR_MEGAHUB = "#2a78d6"   # categorical slot 1 (blue)
COLOR_SUBWH = "#008300"    # categorical slot 2 (green)
SURFACE = "#fcfcfb"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
STATUS_WARN = "#fab219"
STATUS_CRIT = "#d03b3b"
STATUS_GOOD = "#0ca30c"
FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif"

# ------------------------------------------------------------------
# 2. Synthetic data — A330 공통 기종 핵심 부품 20종
#    (대한항공-아시아나 통합 이후 확정된 가상 통합 수요 기준)
# ------------------------------------------------------------------
PART_CATALOG = [
    ("CFM56-5B 엔진 팬 블레이드", "A"),
    ("IDG (교류발전기 구동장치)", "A"),
    ("메인 랜딩기어 액추에이터", "A"),
    ("APU (보조동력장치)", "A"),
    ("스타터 제너레이터", "A"),
    ("FMS 항법 컴퓨터", "B"),
    ("유압 펌프 어셈블리", "B"),
    ("탄소 브레이크 어셈블리", "B"),
    ("기상 레이더 안테나", "B"),
    ("에어데이터 모듈 (ADM)", "B"),
    ("노즈 랜딩기어 휠", "B"),
    ("엔진 연료 노즐", "B"),
    ("카고 도어 액추에이터", "C"),
    ("캐빈 여압 밸브", "C"),
    ("산소 발생기", "C"),
    ("연료량 지시계", "C"),
    ("플랩 트랙 롤러", "C"),
    ("윈도우 히트 컨트롤러", "C"),
    ("연기 감지기", "C"),
    ("유압 리저버", "C"),
]

# ABC 등급별 파라미터 범위: A(고가/대형/AOG 치명적) → C(저가/소형/다수)
CLASS_RANGES = {
    "A": dict(cost=(60_000, 150_000), volume=(1.5, 4.0), stock=(2, 6), penalty=100),
    "B": dict(cost=(8_000, 25_000), volume=(0.8, 2.0), stock=(4, 10), penalty=40),
    "C": dict(cost=(300, 3_000), volume=(0.15, 0.7), stock=(10, 25), penalty=10),
}

# 보관 비용률(연간 재고유지비 비율): 메가허브는 규모의 경제로 저렴, 서브창고는 소규모 운영으로 상대적 고비용
RATE_MEGAHUB = 0.12
RATE_SUBWH = 0.22


@st.cache_data(show_spinner=False)
def generate_part_data(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for part_name, abc_class in PART_CATALOG:
        cfg = CLASS_RANGES[abc_class]
        unit_cost = round(rng.uniform(*cfg["cost"]), -1)
        unit_volume = round(rng.uniform(*cfg["volume"]), 2)
        target_safety_stock = int(rng.integers(cfg["stock"][0], cfg["stock"][1] + 1))
        rows.append(
            dict(
                part_name=part_name,
                abc_class=abc_class,
                unit_cost=unit_cost,
                unit_volume=unit_volume,
                target_safety_stock=target_safety_stock,
                lead_time_penalty=cfg["penalty"],
            )
        )
    df = pd.DataFrame(rows)
    df = df.sort_values(["abc_class", "unit_cost"], ascending=[True, False]).reset_index(drop=True)
    return df


# ------------------------------------------------------------------
# 3. 최적화 엔진 — PuLP 정수계획법(Integer Programming)
# ------------------------------------------------------------------
def solve_allocation(df: pd.DataFrame, max_megahub_volume: float, weight_cost: float, weight_time: float):
    items = df.index.tolist()

    prob = pulp.LpProblem("MRO_Warehouse_Allocation", pulp.LpMinimize)

    X = pulp.LpVariable.dicts("MegaHub", items, lowBound=0, cat="Integer")
    Y = pulp.LpVariable.dicts("SubWH", items, lowBound=0, cat="Integer")

    # 제약 1: 수량 충족 — 두 창고 배치량의 합은 목표 안전재고와 정확히 일치
    for i in items:
        prob += X[i] + Y[i] == int(df.loc[i, "target_safety_stock"]), f"fulfill_{i}"

    # 제약 2: 메가 허브 물리적 공간 한도
    prob += (
        pulp.lpSum(X[i] * df.loc[i, "unit_volume"] for i in items) <= max_megahub_volume,
        "megahub_capacity",
    )

    # 목적함수 정규화 상수: 두 항의 스케일이 달라 가중치가 실질적으로 작동하도록 0~1 대역으로 스케일링
    #   - 최대 비용 시나리오: 전량 서브창고 보관(가장 비쌈)
    #   - 최대 페널티 시나리오: 전량 메가허브 보관(가장 리드타임 불리)
    max_cost_scenario = sum(df.loc[i, "unit_cost"] * RATE_SUBWH * df.loc[i, "target_safety_stock"] for i in items)
    max_penalty_scenario = sum(df.loc[i, "lead_time_penalty"] * df.loc[i, "target_safety_stock"] for i in items)
    max_cost_scenario = max_cost_scenario or 1.0
    max_penalty_scenario = max_penalty_scenario or 1.0

    # 목적함수: Minimize( Weight_Cost * 정규화비용 + Weight_Time * 정규화 리드타임페널티 )
    #   메가허브(X): 재고유지비는 저렴하지만 서브 기지까지의 운송으로 리드타임 페널티 발생
    #   서브창고(Y): 재고유지비는 비싸지만 전진배치로 리드타임 페널티 없음(0)
    obj_terms = []
    for i in items:
        cost_x = df.loc[i, "unit_cost"] * RATE_MEGAHUB
        cost_y = df.loc[i, "unit_cost"] * RATE_SUBWH
        penalty_x = df.loc[i, "lead_time_penalty"]

        coeff_x = weight_cost * (cost_x / max_cost_scenario) + weight_time * (penalty_x / max_penalty_scenario)
        coeff_y = weight_cost * (cost_y / max_cost_scenario)

        obj_terms.append(coeff_x * X[i])
        obj_terms.append(coeff_y * Y[i])

    prob += pulp.lpSum(obj_terms)

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    result = df.copy()
    result["megahub_qty"] = [int(pulp.value(X[i]) or 0) for i in items]
    result["subwh_qty"] = [int(pulp.value(Y[i]) or 0) for i in items]
    result["megahub_volume_used"] = result["megahub_qty"] * result["unit_volume"]
    result["total_value"] = result["target_safety_stock"] * result["unit_cost"]

    status = pulp.LpStatus[prob.status]
    objective_value = pulp.value(prob.objective)
    return result, status, objective_value


# ------------------------------------------------------------------
# 4. Sidebar — 시뮬레이션 셋업
# ------------------------------------------------------------------
df_parts = generate_part_data()
total_volume_needed = float((df_parts["unit_volume"] * df_parts["target_safety_stock"]).sum())
total_inventory_value = float((df_parts["unit_cost"] * df_parts["target_safety_stock"]).sum())

with st.sidebar:
    st.markdown("## 🛠️ 시뮬레이션 셋업")
    st.caption("대한항공(메가허브) · 아시아나(서브창고) 통합 자재 배치 최적화")

    st.markdown("### 1. 공간 제약 (Capacity Constraint)")
    max_megahub_volume = st.slider(
        "메가 허브 가용 공간 (㎥)",
        min_value=0.0,
        max_value=round(total_volume_needed, 1),
        value=round(total_volume_needed * 0.6, 1),
        step=round(total_volume_needed / 100, 1) or 0.1,
        help="메가 허브 창고의 물리적 최대 수용 부피 한도. 공간이 줄어들수록 저가치 부품이 서브 창고로 우선 이전됩니다.",
    )
    st.progress(min(max_megahub_volume / total_volume_needed, 1.0))
    st.caption(f"전체 요구 부피 대비 {max_megahub_volume / total_volume_needed:.0%} 수준")

    st.markdown("### 2. 목표 밸런싱 (Objective Weighting)")
    time_weight_pct = st.slider(
        "비용 최소화 ↔ 시간(리드타임) 최소화",
        min_value=0,
        max_value=100,
        value=50,
        help="0에 가까울수록 재고유지비용 최소화를, 100에 가까울수록 서브 창고 전진배치를 통한 리드타임 최소화를 우선합니다.",
    )
    weight_time = time_weight_pct / 100
    weight_cost = 1 - weight_time

    c1, c2 = st.columns(2)
    c1.metric("Weight_Cost", f"{weight_cost:.2f}")
    c2.metric("Weight_Time", f"{weight_time:.2f}")

    st.divider()
    st.caption("Engine: PuLP (CBC Solver) · Integer Programming")

# ------------------------------------------------------------------
# 5. 최적화 실행
# ------------------------------------------------------------------
result_df, solver_status, objective_value = solve_allocation(df_parts, max_megahub_volume, weight_cost, weight_time)

# ------------------------------------------------------------------
# 6. Main page — 결과 대시보드
# ------------------------------------------------------------------
st.title("✈️ MRO 통합 자재 공급망 최적화 대시보드")
st.caption(
    "대한항공-아시아나 통합 A330 기단 핵심 부품에 대한 메가허브 / 서브창고 배치 최적화 시뮬레이션 "
    "— 선형·정수계획법(Integer Programming) 기반 수학적 최적해"
)

if solver_status != "Optimal":
    st.error(f"최적해를 찾지 못했습니다 (Solver Status: {solver_status}). 제약 조건을 확인하세요.")

megahub_used = float(result_df["megahub_volume_used"].sum())
utilization = megahub_used / max_megahub_volume if max_megahub_volume > 0 else 0
subwh_qty_total = int(result_df["subwh_qty"].sum())
megahub_qty_total = int(result_df["megahub_qty"].sum())
total_qty = subwh_qty_total + megahub_qty_total

k1, k2, k3, k4 = st.columns(4)
k1.metric("총 투입 예산 (재고 가치)", f"${total_inventory_value:,.0f}")
k2.metric(
    "메가 허브 공간 사용률",
    f"{utilization:.1%}",
    delta="여유" if utilization < 0.9 else "포화 임박",
    delta_color="normal" if utilization < 0.9 else "inverse",
)
k3.metric("메가 허브 배치 수량", f"{megahub_qty_total:,} 개", f"{megahub_qty_total/total_qty:.0%}" if total_qty else None)
k4.metric("서브 창고 배치 수량", f"{subwh_qty_total:,} 개", f"{subwh_qty_total/total_qty:.0%}" if total_qty else None)

if utilization >= 0.98:
    st.warning("⚠️ 메가 허브 공간이 사실상 포화 상태입니다. 저가치(C등급) 부품이 서브 창고로 우선 밀려나고 있습니다.", icon="⚠️")

st.divider()

# ------------------------------------------------------------------
# 7. 시각화 — 누적 막대 그래프
# ------------------------------------------------------------------
st.subheader("창고별 부품 배치 현황")

chart_df = result_df.melt(
    id_vars=["part_name", "abc_class"],
    value_vars=["megahub_qty", "subwh_qty"],
    var_name="warehouse",
    value_name="quantity",
)
chart_df["warehouse"] = chart_df["warehouse"].map(
    {"megahub_qty": "메가 허브 (대한항공)", "subwh_qty": "서브 창고 (아시아나)"}
)

part_order = result_df.sort_values(["abc_class", "unit_cost"], ascending=[True, False])["part_name"].tolist()

fig = px.bar(
    chart_df,
    x="part_name",
    y="quantity",
    color="warehouse",
    category_orders={"part_name": part_order, "warehouse": ["메가 허브 (대한항공)", "서브 창고 (아시아나)"]},
    color_discrete_map={"메가 허브 (대한항공)": COLOR_MEGAHUB, "서브 창고 (아시아나)": COLOR_SUBWH},
    hover_data={"abc_class": True, "part_name": False},
    labels={"part_name": "", "quantity": "배치 수량", "warehouse": ""},
)
fig.update_traces(marker_line_color=SURFACE, marker_line_width=2)
fig.update_layout(
    barmode="stack",
    plot_bgcolor=SURFACE,
    paper_bgcolor=SURFACE,
    font=dict(family=FONT_FAMILY, color=INK_PRIMARY, size=13),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None, bgcolor="rgba(0,0,0,0)"),
    xaxis=dict(showgrid=False, tickangle=-40, linecolor=AXIS, tickfont=dict(color=INK_SECONDARY)),
    yaxis=dict(gridcolor=GRID, zerolinecolor=AXIS, title="수량 (개)", tickfont=dict(color=INK_MUTED)),
    hovermode="x unified",
    margin=dict(t=60, b=10, l=10, r=10),
    height=480,
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ------------------------------------------------------------------
# 8. 상세 데이터 테이블
# ------------------------------------------------------------------
st.subheader("부품별 최적화 배치 상세")

display_df = result_df[
    [
        "part_name",
        "abc_class",
        "unit_cost",
        "unit_volume",
        "target_safety_stock",
        "megahub_qty",
        "subwh_qty",
        "megahub_volume_used",
    ]
].rename(
    columns={
        "part_name": "부품명",
        "abc_class": "등급",
        "unit_cost": "단가($)",
        "unit_volume": "단위부피(㎥)",
        "target_safety_stock": "목표 안전재고",
        "megahub_qty": "메가허브(X)",
        "subwh_qty": "서브창고(Y)",
        "megahub_volume_used": "메가허브 사용부피(㎥)",
    }
)

st.dataframe(
    display_df.style.format(
        {"단가($)": "{:,.0f}", "단위부피(㎥)": "{:.2f}", "메가허브 사용부피(㎥)": "{:.2f}"}
    ),
    use_container_width=True,
    hide_index=True,
)

with st.expander("📊 최적화 엔진 정보"):
    st.markdown(
        f"""
- **Solver Status:** `{solver_status}`
- **정규화 목적함수 값:** `{objective_value:.4f}`
- **결정 변수:** 부품 {len(df_parts)}종 × 2개 창고(X, Y) = {len(df_parts) * 2}개 정수 변수
- **제약 조건:** 수량 충족 등식 {len(df_parts)}개 + 공간 한도 부등식 1개
- **비용 가정:** 메가허브 재고유지비율 {RATE_MEGAHUB:.0%} vs 서브창고 {RATE_SUBWH:.0%} (규모의 경제 차이)
- **리드타임 페널티:** ABC 등급별 차등 부여 (A등급 AOG 치명도 최고)
        """
    )
