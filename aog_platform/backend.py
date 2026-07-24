# -*- coding: utf-8 -*-
# ============================================================================
#  backend.py  —  [백엔드 담당자 영역]  (단일 파일)
#  역할: 구글 드라이브(또는 로컬)의 raw CSV를 읽어 가공하고, 프론트엔드가 그대로 쓰는
#        "패키지 데이터"로 포장한다. + AOG 조회 엔진(resolve_aog)을 제공한다.
#
#  프론트엔드는 backend 의 두 가지만 사용한다:
#     load_packaged()                         -> 표/KPI/차트에 쓰는 가공 데이터(dict)
#     resolve_aog(reg, part_number, airport)  -> AOG 7단계 조회 결과(dict)
#
#  유지보수 포인트(초보자용):
#   - 새 CSV를 추가하려면: (1) data_sources.yaml 에 항목 추가 (2) 필요하면 아래 _clean() 규칙만 손대면 됨.
#   - 컬럼명은 CSV 헤더와 동일하게 유지. 공항코드/기종은 자동 대문자·공백제거로 매칭 안정화됨.
# ============================================================================
import io
import json
import os

import pandas as pd

try:
    import yaml
except ImportError:  # pyyaml 미설치 시 친절 안내
    raise SystemExit("pyyaml 이 필요합니다.  pip install pyyaml")

BASE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE, "data", "raw")
PACKAGED_DIR = os.path.join(BASE, "data", "packaged")
CONFIG_PATH = os.path.join(BASE, "config", "data_sources.yaml")
TEMPLATE_DIR = os.path.join(BASE, "templates")

# 이송 Lead Time 계산용 최소 상수 (프로토타입과 동일 개념). 실제로는 항공편 API로 대체 가능.
_ROUTE_HOURS = {  # ICN 기준 편도 비행시간(대략)
    "LAX": 11.2, "JFK": 14.0, "CDG": 12.5, "FRA": 11.7, "SIN": 6.5, "HKG": 3.7,
    "NRT": 2.5, "HND": 2.5, "BKK": 5.9, "SYD": 10.5, "GMP": 1.0, "ICN": 0.0,
}
_CARGO_BOOKING = {"대한항공": 3.0, "진에어": 4.0}
STEP_NAMES = {
    1: "FAK 키트", 2: "로컬 Allocation", 3: "Pooling", 4: "Main Station 타사",
    5: "동일 기종 타사", 6: "이송 최적화", 7: "Hand-carry/Cargo 파송",
}


# ---------------------------------------------------------------------------
# 1) 설정 로드 + CSV 읽기 (로컬/드라이브)
# ---------------------------------------------------------------------------
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_csv(name, ds, mode):
    """하나의 데이터셋 CSV를 DataFrame으로 읽는다. drive 모드면 드라이브에서 다운로드."""
    if mode == "drive" and ds.get("drive_id"):
        url = f"https://drive.google.com/uc?export=download&id={ds['drive_id']}"
        return pd.read_csv(url, dtype=str, keep_default_na=False)
    path = os.path.join(RAW_DIR, ds["file"])
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _clean(name, df):
    """가공 규칙: 문자열 trim, 공항코드/기종 대문자화, 수량 정수화. (초보자는 여기만 수정)"""
    if df.empty:
        return df
    df = df.copy()
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
    for c in ("airport_code", "location_airport", "aircraft_type"):
        if c in df.columns:
            df[c] = df[c].str.upper()
    for c in ("qty", "lead_time_hours", "downtime_hours"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df


# ---------------------------------------------------------------------------
# 2) 패키징: raw -> 프론트가 쓰는 가공 데이터(dict of list[dict]) + JSON 저장
# ---------------------------------------------------------------------------
def build_packaged(save=True):
    cfg = load_config()
    mode = cfg.get("mode", "local")
    data = {}
    for name, ds in cfg["datasets"].items():
        data[name] = _clean(name, _read_csv(name, ds, mode)).to_dict("records")
    if save:
        os.makedirs(PACKAGED_DIR, exist_ok=True)
        with open(os.path.join(PACKAGED_DIR, "app_data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    return data


def load_packaged(rebuild=True):
    """프론트가 호출. rebuild=True면 raw에서 새로 가공(개발 중 권장)."""
    if rebuild:
        return build_packaged(save=True)
    p = os.path.join(PACKAGED_DIR, "app_data.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return build_packaged(save=True)


# ---------------------------------------------------------------------------
# 3) 조회 헬퍼
# ---------------------------------------------------------------------------
def _norm(s):
    return str(s or "").strip().upper()


def _rows(data, name, **flt):
    out = []
    for r in data.get(name, []):
        if all(_norm(r.get(k)) == _norm(v) for k, v in flt.items()):
            out.append(r)
    return out


def _first(data, name, **flt):
    rows = _rows(data, name, **flt)
    return rows[0] if rows else None


def resolve_aircraft(data, registration):
    r = _first(data, "aircraft_registry", registration=registration)
    if r:
        return r.get("aircraft_type"), r.get("operator", "대한항공")
    return None, None


def _lead_time(origin, dest, operator="대한항공"):
    if _norm(origin) == _norm(dest):
        return 3.0
    o, d = _ROUTE_HOURS.get(_norm(origin)), _ROUTE_HOURS.get(_norm(dest))
    if _norm(origin) == "ICN" and d is not None:
        transit = d
    elif _norm(dest) == "ICN" and o is not None:
        transit = o
    elif o is not None and d is not None:
        transit = o + d + 2.0  # ICN 허브 환적
    else:
        transit = 14.0
    return round(transit + 3.0 + _CARGO_BOOKING.get(operator, 3.0), 1)


def render_template(fname, **kw):
    p = os.path.join(TEMPLATE_DIR, fname)
    if not os.path.exists(p):
        return ""
    with open(p, "r", encoding="utf-8") as f:
        txt = f.read()
    for k, v in kw.items():
        txt = txt.replace("{" + k + "}", str(v))
    return txt


# ---------------------------------------------------------------------------
# 4) AOG 엔진: 7단계 조회 (순수 함수 — Streamlit 의존 없음)
# ---------------------------------------------------------------------------
def resolve_aog(reg, part_number, airport, data=None):
    if data is None:
        data = load_packaged(rebuild=False)
    reg, part, ap = _norm(reg), _norm(part_number), _norm(airport)
    atype, operator = resolve_aircraft(data, reg)
    if not atype:
        return {"ok": False, "error": f"기번 {reg} 미등록 — aircraft_registry.csv 에 추가 필요"}

    steps = []

    def add(step, found, message, detail=None):
        steps.append({"step": step, "name": STEP_NAMES[step], "found": found, "message": message, "detail": detail or {}})

    # 1 FAK
    it = _first(data, "fak_kits", aircraft_type=atype, part_number=part)
    add(1, bool(it), (f"FAK 키트 보유 — {it['part_name']} {it['qty']}EA (기체 탑재, 공항 무관)" if it
                      else "FAK 키트(소모품) 구성품 아님"), it)
    # 2 로컬 Allocation
    it = _first(data, "allocation_stock", airport_code=ap, aircraft_type=atype, part_number=part)
    add(2, bool(it), (f"로컬 Allocation 보유 — {it['warehouse_name']} · {it['qty']}EA" if it
                      else f"{ap} 자사 창고에 재고 없음"), it)
    # 3 Pooling
    pool = None
    for hit in _rows(data, "pooling_stock", aircraft_type=atype, part_number=part):
        pinfo = _first(data, "pooling_partners", partner=hit["partner"]) or {}
        cov = [c.strip().upper() for c in pinfo.get("coverage_airports", "").split(",") if c.strip()]
        if not cov or ap in cov:
            pool = {**hit, **{k: pinfo.get(k, "") for k in ("contact", "email", "coverage_airports")}}
            break
    add(3, bool(pool), (f"Pooling 지원 가능 — {pool['partner']} ({pool['location_airport']}) · {pool['qty']}EA" if pool
                        else "커버리지 내 Pooling 파트너 없음"), pool)
    # 4 Main Station 타사 (취항사 ∩ 기종 운영사)
    ops = {_norm(o["airline"]) for o in _rows(data, "fleet_operators", aircraft_type=atype)}
    queried4 = [a for a in _rows(data, "station_airlines", airport_code=ap) if _norm(a["airline"]) in ops]
    add(4, False, (f"{ap} 취항 {atype} 운영사 {len(queried4)}곳에 문의 필요" if queried4
                   else f"{ap} 취항사 중 {atype} 운영사 없음 → 5단계"), {"queried_airlines": queried4})
    # 5 동일 기종 타사 전체
    queried5 = _rows(data, "fleet_operators", aircraft_type=atype)
    add(5, False, f"{atype} 운영사 {len(queried5)}곳 전체에 문의 필요", {"queried_airlines": queried5})
    # 6 이송 최적화 (타 공항 자사 + 제휴 Non-Pool)
    options = []
    for r in data.get("allocation_stock", []):
        if _norm(r.get("airport_code")) != ap and _norm(r.get("aircraft_type")) == atype and _norm(r.get("part_number")) == part:
            options.append({"kind": "자사 타 스테이션", "from": r["airport_code"], "holder": r["warehouse_name"],
                            "qty": r["qty"], "lead": _lead_time(r["airport_code"], ap, operator)})
    for r in data.get("alliance_stock", []):
        if _norm(r.get("aircraft_type")) == atype and _norm(r.get("part_number")) == part:
            options.append({"kind": "제휴 창고(Non-Pool)", "from": r["airport_code"], "holder": r["partner"],
                            "qty": r["qty"], "lead": _lead_time(r["airport_code"], ap, operator)})
    options.sort(key=lambda x: x["lead"])
    best = options[0] if options else None
    add(6, bool(options), (f"이송 최적 추천 — {best['holder']}({best['from']}) · 약 {best['lead']}h" if best
                           else "타 공항 자사/제휴 창고에도 없음"), {"options": options, "best": best})
    # 7 파송
    sh = _first(data, "station_handlers", airport_code=ap) or {}
    is_jinair = _norm(operator) == _norm("진에어")
    jin_ok = _norm(sh.get("jinair_cargo_auth")) == "Y"
    add(7, True, "Hand-carry/Cargo 파송 (통관·인보이스 준비)", {"station_handler": sh, "is_jinair": is_jinair, "jinair_auth": jin_ok})

    # 확보(권장 종료) 단계: 확보된 첫 단계, 없으면 7
    resolved = next((s["step"] for s in steps if s["found"] and s["step"] in (1, 2, 3, 6)), 7)

    # 추천 멘션 (과거 이력)
    reco = []
    succ = [r for r in _rows(data, "sourcing_history", part_number=part) if str(r.get("result", "")).startswith("성공")]
    if succ:
        by = {}
        for r in succ:
            by.setdefault(r.get("source", ""), []).append(int(r.get("lead_time_hours", 0) or 0))
        src = max(by, key=lambda k: len(by[k]))
        avg = sum(by[src]) / len(by[src])
        reco.append(f"과거 이 자재는 '{src}'에서 {len(by[src])}건 확보 성공(평균 {avg:.0f}h) → 먼저 문의 권장")
    if queried5:
        reco.append(f"{atype} 운영사 문의 후보: " + ", ".join(o["airline"] for o in queried5[:6]))

    # 부서 연락처 + 양식 텍스트
    dept = _first(data, "allocation_contacts", airport_code=ap) or {}
    hq = {r["team"]: r for r in data.get("hq_contacts", [])}
    email_txt = render_template("aog_support_request_en.txt", aircraft_type=atype, part_number=part, airport=ap)
    from datetime import date
    invoice_txt = render_template("aog_invoice_template.txt", date=date.today().isoformat(), registration=reg,
                                  aircraft_type=atype, operator=operator, part_number=part, airport=ap,
                                  handling_agent=sh.get("handling_agent", "TBD"), address=sh.get("address", "TBD"))

    return {
        "ok": True, "registration": reg, "aircraft_type": atype, "operator": operator,
        "part_number": part, "airport": ap, "steps": steps, "resolved_step": resolved,
        "recommendation": reco, "allocation_dept": dept, "hq_contacts": hq,
        "email_draft": email_txt, "invoice_draft": invoice_txt,
        "history_sourcing": _rows(data, "sourcing_history", part_number=part),
        "history_defect": _rows(data, "defect_history", registration=reg),
    }


# CLI 테스트: python backend.py
if __name__ == "__main__":
    d = build_packaged()
    print("packaged datasets:", {k: len(v) for k, v in d.items()})
    r = resolve_aog("HL8259", "HYD-PUMP-737-11", "JFK", d)
    print("resolved_step:", r["resolved_step"], "| step6 found:", r["steps"][5]["found"], r["steps"][5]["message"])
