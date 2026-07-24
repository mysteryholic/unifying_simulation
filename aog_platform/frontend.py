# -*- coding: utf-8 -*-
# ============================================================================
#  frontend.py  —  [프론트엔드 담당자 영역]  (설정 기반 렌더러 · 단일 파일)
#  실행: streamlit run frontend.py     (VS Code 터미널 / Windows OK)
#  화면 구성은 config/app_config.yaml 만 편집하면 됩니다(코드 수정 불필요).
#  데이터/조회 로직은 backend.py 가 담당합니다.
#  UI 톤: Flexport 등 물류 SaaS — 밝은 배경 · 네이비 좌측 레일 · 블루 액센트 · 고밀도 표 · 상태 chip.
# ============================================================================
import os
import sys
import urllib.parse

import pandas as pd
import streamlit as st
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backend  # noqa: E402

st.set_page_config(page_title="AOG Command Center", page_icon="🛩️", layout="wide")

CFG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "app_config.yaml"), "r", encoding="utf-8"))
ACCENT = CFG.get("accent", "#2563EB")


# ---------------------------------------------------------------------------
#  UI 스타일 (Flexport 톤)
# ---------------------------------------------------------------------------
def inject_css():
    st.markdown(f"""
    <style>
    :root {{ --accent:{ACCENT}; --navy:#0e2438; --ink:#1b2733; --muted:#5b6b7b; --line:#e5e8ec; --bg:#f6f8fa; }}
    .stApp {{ background:var(--bg); }}
    header[data-testid="stHeader"] {{ background:transparent; }}
    .block-container {{ padding-top:1.4rem; max-width:1500px; }}
    /* 좌측 사이드바 = 네이비 레일 */
    section[data-testid="stSidebar"] {{ background:var(--navy); }}
    section[data-testid="stSidebar"] * {{ color:#cfdae6 !important; }}
    section[data-testid="stSidebar"] .stRadio label {{ font-weight:600; }}
    section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,section[data-testid="stSidebar"] h3 {{ color:#fff !important; }}
    h1,h2,h3,h4 {{ color:var(--ink); letter-spacing:-.01em; }}
    /* 상단 타이틀바 */
    .cc-topbar {{ display:flex; align-items:baseline; gap:12px; border-bottom:1px solid var(--line);
        padding:2px 0 12px; margin-bottom:14px; }}
    .cc-topbar .t {{ font-size:1.15rem; font-weight:800; color:var(--navy); }}
    .cc-topbar .crumb {{ font-size:.8rem; color:var(--muted); }}
    /* KPI 타일 */
    .cc-kpis {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:6px; }}
    .cc-kpi {{ flex:1; min-width:150px; background:#fff; border:1px solid var(--line); border-radius:10px; padding:12px 14px; }}
    .cc-kpi .l {{ font-size:.68rem; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }}
    .cc-kpi .v {{ font-size:1.5rem; font-weight:800; color:var(--navy); font-variant-numeric:tabular-nums; }}
    /* 카드 & 섹션 제목 */
    .cc-sec {{ font-size:.9rem; font-weight:700; color:var(--ink); margin:14px 0 6px; }}
    .cc-card {{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:14px 16px; margin-bottom:8px; }}
    /* 상태 chip */
    .chip {{ display:inline-block; padding:2px 9px; border-radius:6px; font-size:.72rem; font-weight:700; font-variant-numeric:tabular-nums; }}
    .chip.ok {{ background:#e3f2e6; color:#1a7f37; }} .chip.no {{ background:#eef1f4; color:#68788a; }}
    .chip.warn {{ background:#fdeceb; color:#c0392b; }} .chip.info {{ background:#e7eefc; color:#1b4fd0; }}
    /* 단계 행 */
    .cc-step {{ display:flex; align-items:center; gap:10px; padding:8px 10px; border:1px solid var(--line);
        border-radius:8px; margin-bottom:6px; background:#fff; }}
    .cc-step .n {{ width:22px; height:22px; border-radius:6px; background:#eef1f4; color:#68788a; font-weight:800;
        display:flex; align-items:center; justify-content:center; font-size:.75rem; }}
    .cc-step.hit .n {{ background:var(--accent); color:#fff; }}
    .cc-step .nm {{ font-weight:700; color:var(--ink); min-width:150px; font-size:.86rem; }}
    .cc-step .ms {{ color:var(--muted); font-size:.84rem; }}
    a.cc-link {{ color:var(--accent); font-weight:600; text-decoration:none; }}
    .stButton>button {{ border-radius:8px; border:1px solid var(--line); font-weight:600; }}
    [data-testid="stDataFrame"] {{ border:1px solid var(--line); border-radius:8px; }}
    code {{ background:#eef1f4; color:#0e2438; }}
    </style>""", unsafe_allow_html=True)


def topbar(page_name):
    st.markdown(f'<div class="cc-topbar"><span class="t">{CFG.get("app_title","AOG")}</span>'
                f'<span class="crumb">{CFG.get("app_subtitle","")} &nbsp;/&nbsp; {page_name}</span></div>',
                unsafe_allow_html=True)


# ---------------------------------------------------------------------------
#  범용 위젯 (app_config.yaml 의 섹션 렌더)
# ---------------------------------------------------------------------------
def _df(data, name, columns=None):
    df = pd.DataFrame(data.get(name, []))
    if columns and not df.empty:
        columns = [c for c in columns if c in df.columns]
        df = df[columns]
    return df


def w_kpi_row(data, sec):
    tiles = []
    for it in sec.get("items", []):
        rows = data.get(it["dataset"], [])
        if it.get("agg") == "sum" and it.get("column"):
            val = sum(float(r.get(it["column"], 0) or 0) for r in rows)
            val = f"{val:,.0f}"
        else:
            val = f"{len(rows):,}"
        tiles.append(f'<div class="cc-kpi"><div class="l">{it["label"]}</div><div class="v">{val}</div></div>')
    st.markdown(f'<div class="cc-kpis">{"".join(tiles)}</div>', unsafe_allow_html=True)


def w_table(data, sec):
    if sec.get("title"):
        st.markdown(f'<div class="cc-sec">{sec["title"]}</div>', unsafe_allow_html=True)
    df = _df(data, sec["dataset"], sec.get("columns"))
    if df.empty:
        st.caption("데이터 없음.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, height=sec.get("height"))


def w_chart(data, sec):
    if sec.get("title"):
        st.markdown(f'<div class="cc-sec">{sec["title"]}</div>', unsafe_allow_html=True)
    df = pd.DataFrame(data.get(sec["dataset"], []))
    x = sec.get("x")
    if df.empty or x not in df.columns:
        st.caption("데이터 없음."); return
    agg = df.groupby(x).size().reset_index(name="건수").set_index(x)
    st.bar_chart(agg, height=260, color=ACCENT)


def w_markdown(data, sec):
    st.markdown(sec.get("body", ""))


# ---------------------------------------------------------------------------
#  AOG 조회 화면 (엔진 결과 렌더)
# ---------------------------------------------------------------------------
def _mailto(emails, subject, body):
    return ("mailto:" + ",".join(emails) + "?subject=" + urllib.parse.quote(subject) + "&body=" + urllib.parse.quote(body))


def w_aog_query(data, sec):
    regs = [r["registration"] for r in data.get("aircraft_registry", [])]
    parts = sorted({r["part_number"] for k in ("fak_kits", "allocation_stock", "alliance_stock", "pooling_stock")
                    for r in data.get(k, [])})
    airports = sorted({r["airport_code"] for r in data.get("station_handlers", [])}
                      | {r["airport_code"] for r in data.get("allocation_stock", [])})
    with st.form("aog"):
        c1, c2, c3, c4 = st.columns([1.1, 1.4, 1, 0.8])
        reg = c1.selectbox("기번 (Registration)", regs, index=regs.index("HL8259") if "HL8259" in regs else 0)
        part = c2.text_input("자재 파트넘버", value="HYD-PUMP-737-11")
        ap = c3.selectbox("발생 공항", airports, index=airports.index("JFK") if "JFK" in airports else 0)
        go = c4.form_submit_button("🎯 조회", use_container_width=True, type="primary")
    if not go:
        st.caption("기번·파트넘버·공항을 넣고 조회하면 7단계 조달 경로와 최적안·연락처·양식이 나옵니다.")
        return

    r = backend.resolve_aog(reg, part, ap, data)
    if not r.get("ok"):
        st.error(r.get("error")); return

    jin = r["steps"][6]["detail"]
    op_chip = '<span class="chip warn">진에어</span>' if jin.get("is_jinair") else '<span class="chip info">대한항공</span>'
    st.markdown(f'<div class="cc-card"><b>{r["registration"]}</b> · {r["aircraft_type"]} {op_chip} &nbsp; '
                f'자재 <code>{r["part_number"]}</code> &nbsp; 공항 <b>{r["airport"]}</b> &nbsp; '
                f'→ 권장 확보 단계: <span class="chip ok">{r["resolved_step"]} · {backend.STEP_NAMES[r["resolved_step"]]}</span></div>',
                unsafe_allow_html=True)

    if r["recommendation"]:
        st.markdown('<div class="cc-sec">🔔 추천</div>', unsafe_allow_html=True)
        for ln in r["recommendation"]:
            st.markdown(f'<div class="cc-card">• {ln}</div>', unsafe_allow_html=True)

    st.markdown('<div class="cc-sec">조달 경로 7단계</div>', unsafe_allow_html=True)
    for s in r["steps"]:
        cls = "hit" if s["found"] else ""
        icon = "✓" if s["found"] else s["step"]
        st.markdown(f'<div class="cc-step {cls}"><div class="n">{icon}</div>'
                    f'<div class="nm">{s["step"]}. {s["name"]}</div><div class="ms">{s["message"]}</div></div>',
                    unsafe_allow_html=True)

    # 6단계 이송 옵션표
    opts = r["steps"][5]["detail"].get("options")
    if opts:
        st.markdown('<div class="cc-sec">🚚 이송 최적화 — 전 경로 비교</div>', unsafe_allow_html=True)
        df = pd.DataFrame(opts).rename(columns={"kind": "유형", "from": "출발", "holder": "보유처", "qty": "수량", "lead": "예상(h)"})
        st.dataframe(df, use_container_width=True, hide_index=True)

    # 4·5단계 문의 메일
    col = st.columns(2)
    for i, (label, key) in enumerate([("4단계 Main Station 문의", 3), ("5단계 동일기종 전체 문의", 4)]):
        airlines = r["steps"][key]["detail"].get("queried_airlines", [])
        emails = [a["email"] for a in airlines if a.get("email")]
        with col[i]:
            st.markdown(f'<div class="cc-sec">{label} · {len(emails)}곳</div>', unsafe_allow_html=True)
            if emails:
                subj = f"[AOG - URGENT] {r['aircraft_type']} / {r['part_number']} / {r['airport']}"
                st.markdown(f'<a class="cc-link" target="_blank" href="{_mailto(emails, subj, r["email_draft"])}">✉️ 영문 대여요청 메일 작성({len(emails)})</a>', unsafe_allow_html=True)
                st.caption(", ".join(a["airline"] for a in airlines))
            else:
                st.caption("대상 없음")

    # 7단계 파송
    st.markdown('<div class="cc-sec">🧳 7단계 · 파송 (통관·인보이스)</div>', unsafe_allow_html=True)
    if jin.get("is_jinair") and not jin.get("jinair_auth"):
        st.markdown(f'<div class="cc-card"><span class="chip warn">진에어 화물인가 없음</span> '
                    f'{r["airport"]}은 자사 카고 파송 불가 → Hand-carry/우회 이송 필수.</div>', unsafe_allow_html=True)
    elif jin.get("is_jinair"):
        st.markdown('<div class="cc-card"><span class="chip ok">진에어 화물인가 유효</span> 자사 카고 파송 가능.</div>', unsafe_allow_html=True)
    hq = r["hq_contacts"]
    parts_txt = " · ".join(f"{t}: {hq[t]['contact']} / {hq[t]['email']}" for t in hq)
    st.markdown(f'<div class="cc-card">파송 부서 — {parts_txt}<br>현지 Allocation — '
                f'{r["allocation_dept"].get("department","-")}: {r["allocation_dept"].get("contact","-")}</div>', unsafe_allow_html=True)
    dept_emails = [hq[t]["email"] for t in hq] + ([r["allocation_dept"].get("email")] if r["allocation_dept"].get("email") else [])
    isubj = f"[AOG 파송요청] {r['registration']}({r['aircraft_type']}) / {r['part_number']} → {r['airport']}"
    st.markdown(f'<a class="cc-link" target="_blank" href="{_mailto(dept_emails, isubj, r["invoice_draft"])}">📨 내부 파송 Request 메일(통관·카고·현지 Allocation)</a>', unsafe_allow_html=True)
    with st.expander("🧾 AI 인보이스 / 신고서 (조업사 주소 자동 반영)"):
        st.code(r["invoice_draft"], language="text")

    # 이력
    with st.expander("📖 이 자재 참고 이력 (수배 · 결함 조치)"):
        c1, c2 = st.columns(2)
        with c1:
            st.caption("과거 수배(대여) 이력")
            sh = pd.DataFrame(r["history_sourcing"])
            st.dataframe(sh, use_container_width=True, hide_index=True) if not sh.empty else st.caption("없음")
        with c2:
            st.caption("과거 결함 조치 이력")
            dh = pd.DataFrame(r["history_defect"])
            st.dataframe(dh, use_container_width=True, hide_index=True) if not dh.empty else st.caption("없음")


_WIDGETS = {"kpi_row": w_kpi_row, "table": w_table, "chart": w_chart, "markdown": w_markdown, "aog_query": w_aog_query}


# ---------------------------------------------------------------------------
#  메인
# ---------------------------------------------------------------------------
def main():
    inject_css()
    data = backend.load_packaged(rebuild=True)  # 개발 중: 매번 raw에서 재가공
    with st.sidebar:
        st.markdown(f"### 🛩️ {CFG.get('app_title','AOG')}")
        st.caption(CFG.get("app_subtitle", ""))
        st.divider()
        pages = CFG.get("pages", [])
        labels = [f"{p.get('icon','•')}  {p['name']}" for p in pages]
        choice = st.radio("메뉴", labels, label_visibility="collapsed")
        st.divider()
        st.caption("데이터: config/data_sources.yaml")
        st.caption("화면: config/app_config.yaml")
    page = pages[labels.index(choice)]
    topbar(page["name"])
    for sec in page.get("sections", []):
        _WIDGETS.get(sec["type"], lambda *_: st.warning(f"알 수 없는 섹션 type: {sec['type']}"))(data, sec)


if __name__ == "__main__":
    main()
