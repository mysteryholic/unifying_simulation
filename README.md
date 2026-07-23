# unifying_simulation — AOG 자재 수급 어시스턴트

AOG(Aircraft on Ground) 상황에서 **정해진 6단계 자재 수급 절차**를, 저장된 데이터에 근거해
자동으로 조회·추천하고 각 단계에서 실제 연락/메일까지 이어주는 Streamlit 대시보드입니다.
Google Colab 노트북 하나(`AOG_Dashboard.ipynb`)로 배포됩니다.

- **입력**: 기번(Registration) · 자재 파트넘버 · 발생 공항(Station)
- **원칙**: 모든 판단은 "데이터 관리"에 저장된 데이터로만 이루어짐(하드코딩 시나리오 없음)
- **부가**: 자재별 과거 **수배 이력**·**결함 조치 이력** 자동 표시, 실시간 운항/허브 현황, 전문가형 GUI

---

## 1. 실행 방법

1. `AOG_Dashboard.ipynb`를 [Google Colab](https://colab.research.google.com/)에서 엽니다.
2. **Cell 1 → 2 → 3** 순서로 실행합니다(Cell 1은 강제 재시작 없이 설치만).
3. Cell 3이 `google.colab.output`으로 앱을 새 창에 띄웁니다(제3자 터널 미사용 → 사내망 안전).
4. 사이드바에서 **🚨 AOG 대시보드 / 🗺️ 실시간 운항 현황 / ⚙️ 데이터 관리** 를 전환합니다.

> 이전 버전의 `aog_db.json`이 남아 있어도 됩니다. 스키마 버전이 다르면 자동으로 `.bak` 백업 후
> 최신 스키마로 재생성하므로 오류 없이 동작합니다.

---

## 2. 데이터 모델 (상세)

데이터는 `aog_db.json` 하나에 저장되며, `_schema_version`으로 버전을 관리합니다. 모든 테이블은
"⚙️ 데이터 관리" 화면에서 직접 편집·저장할 수 있고, 저장 즉시 알고리즘에 반영됩니다.

### 2.1 기번 등록부 `aircraft_registry`
```json
{"registration": "HL7702", "aircraft_type": "A330-300"}
```
- **기번 → 기종** 매핑의 단일 근거. 사용자는 기번으로 입력하고, 내부적으로 기종을 결정합니다.
- 타 항공사는 우리 기번을 모르므로, Pooling·4·5단계 문의는 **기종**으로 나갑니다.

### 2.2 FAK 키트 `fak_kits` — 기종별 "패키지 묶음"
```json
{"aircraft_type": "A330-300", "kit_name": "A330-300 표준 FAK 패키지",
 "contents": [{"part_number": "OXY-GEN-A330-15", "part_name": "Chemical Oxygen Generator", "qty": 2}, ...]}
```
- **같은 기종이면 모든 기체가 동일한 키트 하나**(여러 자재가 든 패키지)를 기체와 한몸으로 탑재합니다.
- 따라서 데이터는 "기종별 패키지 1개 + 그 안의 `contents` 자재 리스트" 형태입니다.
- 키트는 기체와 함께 이동하므로 **AOG 발생 공항과 무관하게** 현장에서 사용 가능합니다.

### 2.3 Allocation `station_warehouses` — 공항별 "창고 묶음"
```json
{"airport": "ICN", "warehouse_name": "ICN 본사 통합 자재창고",
 "contents": [{"aircraft_type": "A330-300", "part_number": "FUEL-NOZ-A330-07", "part_name": "Engine Fuel Nozzle", "qty": 4}, ...]}
```
- 한 스테이션(공항) 창고 안에 여러 자재가 들어 있는 형태입니다.
- **발생 공항 창고에 (기종·자재)가 있어야만** 사용 가능하며, 없으면 Pooling으로 넘어갑니다.
- ICN(허브)이 최다 보유, 해외 지점(FRA/LAX/JFK/NRT/CDG/SIN/HKG/GMP/BKK/SYD)은 노선 특성에 맞게 소량 보유하도록 현실적으로 분포시켰습니다.

### 2.4 Pooling `pooling_partners` / `pooling_stock`
```json
// partner: 커버리지(지원 가능 공항) 포함
{"partner": "SIA Engineering (싱가포르)", "contact": "...", "email": "...", "coverage_airports": "SIN,HKG,BKK,NRT,ICN,SYD"}
// stock: 파트너가 실제 보유한 (기종·자재)
{"partner": "SIA Engineering (싱가포르)", "aircraft_type": "B737-800", "part_number": "HYD-PUMP-737-11", "part_name": "...", "qty": 1, "location": "SIN 창고"}
```
- 파트너가 재고를 보유해도 **`coverage_airports`에 발생 공항이 없으면 지원 불가**(예: 싱가포르 파트너는 JFK 커버 안 함).

### 2.5 타 항공사 `main_station_airlines` / `fleet_operators`
- `main_station_airlines`: 공항별 Main Station(허브)로 쓰는 항공사.
- `fleet_operators`: 기종을 운영하는 항공사(연락처·이메일 포함).
- 4단계 = 두 테이블의 **교집합**(발생 공항 기반 ∩ 우리 기종 운영사), 5단계 = 기종 운영사 전체.

### 2.6 연락처 `allocation_dept_contacts` / `customs_team`
- 공항별 Allocation 부서(2단계 성공 시 연락), 통관팀(6단계·사전 대비).

### 2.7 과거 이력 (신규)
```json
// sourcing_history: 자재를 과거에 어디서·어느 단계에서 확보했는지 + 성공 여부
{"date": "2026-05-12", "registration": "HL7710", "aircraft_type": "A330-300", "part_number": "IDG-A330-001",
 "airport": "FRA", "resolved_step": "3·Pooling", "source": "Lufthansa Technik (FRA)", "result": "성공", "lead_time_hours": 6}
// defect_history: 과거 결함을 어떻게 조치했는지(리셋 / 부품 교환 등)
{"date": "2026-02-20", "registration": "HL7702", "aircraft_type": "A330-300", "part_number": "IDG-A330-001",
 "defect": "IDG disconnect fault", "action": "리셋 후 재연결 (Reset & Reconnect)", "result": "정상 복구", "downtime_hours": 1}
```
- 대시보드에서 케이스를 진행하면 **해당 자재(part_number)의 과거 수배·결함 조치 이력이 자동 표시**되어,
  "지난번엔 어디서 얼마 만에 구했는지 / 리셋으로 됐는지 부품 교환했는지"를 즉시 참고할 수 있습니다.

---

## 3. 알고리즘 구현 방식 (상세)

### 3.1 입력 처리 — 자연어에서 3요소 추출
`parse_aog_message()`가 정규식 기반(즉시·0초)으로 **기번 / 파트넘버 / 공항**을 추출합니다.
- 기번: 등록부 목록 매칭 → `HL\d{3,4}` 패턴 → (없으면) 기종 직접 입력 허용.
- 공항: 한글 조사가 붙은 `ICN에서`도 인식하도록 lookaround 경계(`(?<![A-Z0-9])ICN(?![A-Z0-9])`) 사용.
- 파트넘버: 카탈로그 매칭 → `XXX-YYY` 형태의 파트넘버 패턴.
- 세 값 중 하나라도 못 찾으면 무엇이 빠졌는지 알려주고 '직접 입력' 폼에 인식값을 프리필합니다.
- 미등록 기번은 시작을 막고 "등록부에 추가하세요"로 안내합니다(멋대로 진행 금지).

### 3.2 기번 → 기종 변환
`resolve_aircraft_type()`가 `aircraft_registry`로 기종을 결정합니다. 이후 **FAK은 기종 패키지에서**,
Allocation은 (기종·공항)으로, Pooling·타사문의는 기종으로 조회합니다.

### 3.3 6단계 조회 로직 `evaluate_step()` — 전부 데이터 매칭
각 단계는 `(found, message, detail)`을 반환합니다. 핵심은 **묶음(contents) 안을 탐색**한다는 점입니다.

| 단계 | 매칭 규칙 | 데이터 근거 |
|---|---|---|
| 1 · FAK | 기종 키트의 `contents`에 파트넘버 존재 → 발생 공항과 무관하게 확보 | `fak_kits` |
| 2 · Allocation | **발생 공항 창고**의 `contents`에 (기종·파트넘버) 존재. 없으면 다른 공항 재고를 참고로 알려주고 Pooling으로 | `station_warehouses` |
| 3 · Pooling | 파트너가 재고 보유 **AND** `coverage_airports`에 발생 공항 포함 | `pooling_partners`+`pooling_stock` |
| 4 · Main Station 타사 | 발생 공항 Main Station 항공사 **∩** 우리 기종 운영사에 **영문 메일** 문의 | `main_station_airlines`∩`fleet_operators` |
| 5 · 동일 기종 타사 | 기종 운영 항공사 전체에 **영문 메일** 문의(타사 실재고는 기밀 → 항상 문의) | `fleet_operators` |
| 6 · Hand-carry | 통관팀 + 실시간 항공편에서 발생 공항행 가장 빠른 예정편 | `customs_team` + 항공편 피드 |

### 3.4 자동 진행 vs 승인 대기 (`_auto_sweep_silent_steps()`)
- **1~3단계**는 내부 재고 조회(판단 불필요)라 재고가 없으면 **자동으로 다음 단계까지** 확인합니다.
- **4단계**는 문의 대상(교집합)이 없으면 자동으로 5단계로 넘어갑니다.
- **문의 대상이 있는 4단계·5단계·재고 확보 지점·6단계**에서만 멈춰 사람의 **승인/거절**을 받습니다.
- 이렇게 해서 "AI가 순식간에 훑고, 사람은 실제 외부 연락이 필요한 지점에서만 결정" 하도록 했습니다.
  (LLM 함수호출/ReAct 대신 결정론적 파이썬으로 구현 — 고정된 회사 절차라 지연·환각 없이 정확.)

### 3.5 같은 기번·자재라도 공항에 따라 경로가 달라진다 (설계의 핵심)
- `IDG-A330-001`: **FRA**에서는 FRA 창고에 있어 2단계 종료 / **ICN**에서는 창고에도 없고 Pooling(LHT)도 FRA·CDG만 커버 → 4단계.
- `HYD-PUMP-737-11`: **SIN**에서는 SIA가 커버 → 3단계 / **JFK**에서는 SIA 미커버 → 5단계.
- `FUEL-NOZ-A330-07`: **ICN** 창고 보유 → 2단계 / **CDG**에서는 창고에도 없고 Pooling 커버리지도 안 맞아 → 5단계.

### 3.6 AI의 역할 (속도 우선)
- 좌측 "AI 상황 요약 & 추천 행동"은 **항상 규칙 기반으로 즉시(0초)** 표시됩니다(매 단계 LLM 호출 없음).
- 로컬 LLM(Qwen2.5-0.5B, 선택)은 **4·5단계 영문 요청 메일 문구를 다듬을 때만** 사용되며, 실패해도
  기본 영문 템플릿이 그대로 유지되어 앱이 멈추지 않습니다.

### 3.7 실시간 운항/허브 현황
- 항공편·정박 데이터는 더미 공급자(`_fetch_raw_flight_feed` / `fetch_airport_parking_status`)에서 오며,
  `FLIGHT_API_CONFIG` / `PARKING_API_CONFIG`의 `enabled`를 켜고 표시 지점에 실제 API 호출만 채우면
  나머지(지도·표·Hand-carry 후보)는 코드 변경 없이 동작합니다.
- 화면은 **최다 허브·주력 노선 KPI**, 마커 크기=운항량/색=정박 혼잡도, 노선 굵기=빈도, 허브/노선 랭킹 표로 구성됩니다.

---

## 4. 화면 & GUI

- **전문가형 테마**: 상단 히어로 배너, 카드형 정보 패널, `stMetric` 카드 스타일, 일관된 네이비/블루 팔레트.
- **한눈에 들어오는 진행 표시**: 케이스 시작 시 기번/기종·자재·공항·현재상태 **정보 카드**와, 1→6단계
  **가로 스텝퍼**(현재 단계 파랑, 확보 초록 ✓, 미확보 회색)를 표시합니다.
- **자재 이력 패널**: 진행 중인 자재의 과거 수배 이력·결함 조치 이력을 좌우 표로 자동 표시합니다.
- **단계별 실제 조치**: FAK→정비사 전화, Allocation→부서 전화/메일, Pooling→파트너 연락, 4·5→영문
  긴급 메일(대상 자동 산정) + Hand-carry 사전 준비(통관팀 병행 요청), 6→통관팀+편명 선택.

---

## 5. 테스트 시나리오 (채팅에 그대로 입력)

- **FAK 즉시 해결(공항 무관)**: `HL7702 CDG에서 AOG, 부품 OXY-GEN-A330-15 필요`
- **Allocation은 공항따라 갈림**: `HL7702 ICN에서 ... FUEL-NOZ-A330-07`(2단계) vs `HL7702 CDG에서 ... FUEL-NOZ-A330-07`(→5단계)
- **Pooling 커버리지**: `HL8259 SIN에서 ... HYD-PUMP-737-11`(3단계) vs `HL8259 JFK에서 ... HYD-PUMP-737-11`(→5단계)
- **끝까지 Hand-carry + 이력**: `HL8082 LAX에서 AOG, 부품 APU-787-01 필요` (4→5→6, APU-787-01 과거 이력 표시)
- **미등록 기번**: `HL9999 ICN에서 ... OXY-GEN-A330-15` → 등록부 안내

---

## 6. 검증 내역

`streamlit.testing.v1.AppTest`로 다음을 자동 검증했습니다.

- FAK 기종 패키지(contents) 매칭·공항 무관성, Allocation 공항별 창고 매칭·타 공항 참고 안내
- Pooling 커버리지 매칭, 같은 자재의 공항별 경로 분기(ICN/CDG, SIN/JFK)
- 4단계 교집합·문의 대상 없을 때 자동 통과, 5단계 전체 문의
- 영문 메일(제목+본문)·기종 기준 작성, 자동 진행/승인 경계
- 자재별 수배·결함 이력 자동 표시, 데이터 관리에서 편집→케이스 반영
- 히어로/스텝퍼/정보카드/이력 패널 렌더링, 스키마 버전 불일치 시 자동 백업·재생성
- 실 서버 기동(HTTP 200) 확인
