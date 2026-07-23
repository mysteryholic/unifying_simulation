# unifying_simulation — AOG 자재 수급 어시스턴트 (최적화 및 자동화 고도화)

AOG(Aircraft on Ground) 상황에서 **정해진 7단계 자재 수급 절차**를, 저장된 데이터와 알고리즘에 근거해 자동으로 조회·추천하고 휴먼 에러를 방지하는 Streamlit 대시보드입니다. Google Colab 노트북 하나(`AOG_Dashboard.ipynb`)로 배포됩니다.

- **입력**: 기번(Registration) · 자재 파트넘버 · 발생 공항(Station)
- **원칙**: 모든 판단은 "데이터 관리"에 저장된 더미 데이터베이스를 기반으로 이루어집니다(하드코딩 시나리오 없음).
- **주요 알고리즘**: **소요 시간(Lead Time) 기반 이송 최적화**, **화물 인가(Cargo Auth) 검증**, **AI 기반 송장(Invoice) 자동화**
- **부가**: 자재별 과거 수배 이력·결함 조치 이력 자동 표시, 실시간 운항/허브 현황, 전문가형 GUI

---

## 1. 실행 방법

1. `AOG_Dashboard.ipynb`를 [Google Colab](https://colab.research.google.com/)에서 엽니다.
2. **Cell 1 → 2 → 3** 순서로 실행합니다(Cell 1은 강제 재시작 없이 설치만).
3. Cell 3이 `google.colab.output`으로 앱을 새 창에 띄웁니다(제3자 터널 미사용 → 사내망 안전).
4. 사이드바에서 **🚨 AOG 대시보드 / 🗺️ 실시간 운항 현황 / ⚙️ 데이터 관리** 를 전환하며 테스트를 진행합니다.

> 이전 버전의 `aog_db.json`이 남아 있어도 됩니다. 스키마 버전이 다르면 자동으로 `.bak` 백업 후
> 최신 스키마로 재생성하므로 오류 없이 동작합니다.

---

## 2. 데이터 모델 및 더미 데이터 (상세)

데이터는 `aog_db.json` 하나에 저장되며, 실무 환경의 변수(조업사, 화물 인가, 제휴 창고)를 현실적으로 반영하기 위해 더미 데이터가 고도화되었습니다. 모든 테이블은 "⚙️ 데이터 관리" 화면에서 직접 편집·저장할 수 있고, 저장 즉시 알고리즘에 반영됩니다.

### 2.1 기번 등록부 `aircraft_registry`
```json
{"registration": "LJ2201", "aircraft_type": "B737-800", "operator": "진에어"}
```
- 기번을 입력하면 기종뿐만 아니라 **운영사(operator)**(예: 대한항공, 진에어)를 함께 매핑합니다. 
- 타 항공사는 우리 기번을 모르므로, Pooling·타사 문의는 **기종**으로 나갑니다.
- **[NEW]** 운영사에 따라 화물 파송 로직(진에어 Auth 확인 등)이 7단계에서 분기됩니다.

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
- **발생 공항 창고에 (기종·자재)가 있어야만** 즉시 불출 가능하며, 없으면 최적화 또는 Pooling으로 넘어갑니다.
- ICN(허브)이 최다 보유, 해외 지점은 노선 특성에 맞게 소량 보유하도록 현실적으로 분포시켰습니다.

### 2.4 [NEW] 제휴 창고 `alliance_warehouses` (Non-Pool)
```json
{"airport": "JFK", "partner": "Delta TechOps (제휴)",
 "contents": [{"aircraft_type": "B737-800", "part_number": "HYD-PUMP-737-11", "part_name": "Engine-Driven Hydraulic Pump", "qty": 1}]}
```
- 정식 Pooling 계약은 없으나 파트너십을 통해 긴급히 자재를 땡겨올 수 있는 외부(조업사/제휴 MRO) 창고입니다. **3단계 이송 최적화**의 탐색 대상이 됩니다.
- 예: `HYD-PUMP-737-11`은 SIA 풀 계약이 **JFK를 커버하지 않지만**, JFK 제휴 창고(Delta TechOps)에 있어 3단계에서 땡겨올 수 있습니다("non-pool 자재도 수배" 케이스).
- ⚠️ **주의(중요)**: 제휴/자사 창고·Pooling에는 **로터블(교환품)** 만, FAK 키트에는 **소모품/비상품목**만 넣으세요. FAK에 로터블을 넣으면 그 자재의 모든 케이스가 1단계에서 잘못 종료됩니다(실제 발생했던 데이터 오류).

### 2.5 Pooling `pooling_partners` / `pooling_stock`
```json
// partner: 커버리지(지원 가능 공항) 포함
{"partner": "SIA Engineering (싱가포르)", "contact": "...", "email": "...", "coverage_airports": "SIN,HKG,BKK,NRT,ICN,SYD"}
// stock: 파트너가 실제 보유한 (기종·자재)
{"partner": "SIA Engineering (싱가포르)", "aircraft_type": "B737-800", "part_number": "HYD-PUMP-737-11", "part_name": "...", "qty": 1, "location": "SIN 창고"}
```
- 파트너가 재고를 보유해도 **`coverage_airports`에 발생 공항이 없으면 지원 불가**(예: 싱가포르 파트너는 JFK 커버 안 함).

### 2.6 타 항공사 `main_station_airlines` / `fleet_operators`
- `main_station_airlines`: 공항별 Main Station(허브)로 쓰는 항공사.
- `fleet_operators`: 기종을 운영하는 항공사(연락처·이메일 포함).
- 5단계 = 두 테이블의 **교집합**(발생 공항 기반 ∩ 우리 기종 운영사), 6단계 = 기종 운영사 전체.

### 2.7 [NEW] 공항 세부 정보 `station_info` (조업사 및 화물 인가)
```json
"JFK": {
  "jinair_cargo_auth": "N", 
  "handling_agent": "Delta Cargo", 
  "address": "JFK Int'l Airport, Cargo Bldg 75, Jamaica, NY 11430, USA"
}
```
- **화물 인가 (Cargo Auth)**: 진에어의 경우 해당 국가/공항에 화물 인가(`jinair_cargo_auth`)가 있는지 여부를 저장합니다.
- **조업사 및 주소**: 조업사 변경 등으로 인해 발생하는 배송 주소 오입력(Human Error)을 방지하기 위해 공항별 최신 정확한 주소를 관리합니다.

### 2.8 [NEW] 야간 통관 메뉴얼 `night_customs_manual`
- 야간(Hand-carry/Cargo 파송) 시 관세사 부재 상황을 대비해 담당자가 직접 수행해야 하는 통관 체크리스트 더미 데이터를 제공합니다.

### 2.9 연락처 `allocation_dept_contacts` / `customs_team`
- 공항별 Allocation 부서(2단계 성공 시 연락), 통관팀(7단계·사전 대비).

### 2.10 과거 이력 (참고자료)
```json
// sourcing_history: 자재를 과거에 어디서·어느 단계·어떤 방식으로 확보했고 성공/실패했는지(=빌린 이력)
{"date": "2026-05-12", "registration": "HL7710", "aircraft_type": "A330-300", "part_number": "IDG-A330-001",
 "airport": "FRA", "resolved_step": "3·Pooling", "source": "Lufthansa Technik (FRA)",
 "method": "대여(Loan)", "result": "성공", "lead_time_hours": 6}
// defect_history: 과거 결함을 어떻게 조치했는지 — 조치유형·수배범위·전용공구까지
{"date": "2026-05-12", "registration": "HL7710", "aircraft_type": "A330-300", "part_number": "IDG-A330-001",
 "defect": "IDG low oil pressure warning", "resolution": "부품 교환", "parts_scope": "패키지(어셈블리)",
 "tools_required": "IDG 인출 지그 JIG-IDG-01, 토크렌치", "result": "정상 복구", "downtime_hours": 6}
```
- 대시보드에서 케이스를 진행하면 **해당 자재(part_number)의 과거 이력이 참고자료로 자동 표시**됩니다.
- **수배(빌린) 이력**: 어디서·어떤 방식(`대여(Loan)`/`구매`/`Hand-carry`/`자체재고`)으로 확보했고 성공/실패했는지 — "지난번 이 자재는 어디서 빌려서 됐지?"를 즉시 확인. 
- **결함 조치 이력**: `resolution`(부품 교환 / 디퍼(MEL) / 리셋·재시동 / SW 리로드), `parts_scope`(단일 부품 vs 패키지 어셈블리), `tools_required`(전용 공구)까지 — "파츠 하나만 바꾸면 되는지, 패키지로 가야 하는지, 어떤 공구가 필요한지"를 진행 중에 바로 참고. 
- 현재는 더미 데이터이며, 실제로는 정비 sheet/시스템 연동으로 채우는 것을 가정합니다. 두 이력 모두 "데이터 관리"에서 편집 가능합니다.

---

## 3. 알고리즘 구현 방식 (상세)

단순한 조건부 검색을 넘어, **가장 빠르고 정확한 조달(최적화)**과 **휴먼 에러 방지(자동화)**에 초점을 맞춘 알고리즘이 적용되었습니다.

### 3.1 입력 처리 — 자연어에서 3요소 추출
`parse_aog_message()`가 정규식 기반(즉시·0초)으로 **기번 / 파트넘버 / 공항**을 추출합니다.
- 기번: 등록부 목록 매칭 → `HL\d{3,4}` 또는 `LJ\d{3,4}` 패턴 → (없으면) 기종 직접 입력 허용.
- 공항: 한글 조사가 붙은 `ICN에서`도 인식하도록 lookaround 경계(`(?<![A-Z0-9])ICN(?![A-Z0-9])`) 사용.
- 파트넘버: 카탈로그 매칭 → `XXX-YYY` 형태의 파트넘버 패턴.
- 세 값 중 하나라도 못 찾으면 무엇이 빠졌는지 알려주고 '직접 입력' 폼에 인식값을 프리필합니다.
- 미등록 기번은 시작을 막고 "등록부에 추가하세요"로 안내합니다(멋대로 진행 금지).

### 3.2 7단계 조회 로직 `evaluate_step()` — 전부 데이터 매칭
각 단계는 `(found, message, detail)`을 반환합니다. 핵심은 **묶음(contents) 안을 탐색**한다는 점입니다.

| 단계 | 매칭 규칙 | 데이터 근거 |
|---|---|---|
| 1 · FAK | 기종 키트의 `contents`에 파트넘버 존재 → 발생 공항과 무관하게 확보 | `fak_kits` |
| 2 · 로컬 Allocation | **발생 공항 창고**의 `contents`에 (기종·파트넘버) 존재 | `station_warehouses` |
| 3 · 이송 최적화 | **[NEW]** 타 공항 자사 창고 및 제휴 창고(Non-Pool) 탐색 및 Lead Time 계산 | `station_warehouses`, `alliance_warehouses` |
| 4 · Pooling | 파트너가 재고 보유 **AND** `coverage_airports`에 발생 공항 포함 | `pooling_partners`+`pooling_stock` |
| 5 · Main Station 타사 | 발생 공항 Main Station 항공사 **∩** 우리 기종 운영사에 **영문 메일** 문의 | `main_station_airlines`∩`fleet_operators` |
| 6 · 동일 기종 타사 | 기종 운영 항공사 전체에 **영문 메일** 문의(타사 실재고는 기밀 → 항상 문의) | `fleet_operators` |
| 7 · Hand-carry/Cargo | **[NEW]** 진에어 Auth 체크 + 실시간 항공편에서 가장 빠른 예정편 + AI 인보이스 | `station_info` + `customs_team` + 항공편 피드 |

### 3.3 [NEW] 3단계: 소요 시간(Lead Time) 기반 이송 최적화 알고리즘
발생 공항에 로컬 재고(1, 2단계)가 없을 경우, 무조건 Pooling으로 넘어가지 않고 **타 공항의 자사 재고**와 **제휴 창고(Non-Pool)** 재고를 우선 탐색합니다.
1. **탐색**: `station_warehouses`(타 공항) 및 `alliance_warehouses` 내의 해당 자재를 모두 쿼리(Query)합니다.
2. **비용 계산**: 출발 공항(origin)과 발생 공항(dest) 간의 가상 비행 시간 및 조업 시간을 합산하여 `calculate_lead_time()` 함수가 총 소요 시간(Lead Time)을 계산합니다.
3. **정렬 및 제안**: 소요 시간이 가장 짧은 순으로 배열(Sort)하여, 최단 시간에 자재를 땡겨올 수 있는 최적의 이송 경로와 업체를 추천합니다.

### 3.4 [NEW] 7단계: 진에어 화물 인가(Cargo Auth) 검증 알고리즘
카고/Hand-carry 파송 시, 운영사가 '진에어'인 경우 목적지 공항의 화물 인가 여부를 판별합니다.
1. **Condition Check**: `operator == "진에어"`일 때, `station_info[airport]["jinair_cargo_auth"]` 값을 참조합니다.
2. **Exception Handling**: 값이 `N`일 경우, 해당 공항으로 직접 카고를 실을 수 없음을 감지하고 **우회 이송 업체 수배 또는 Hand-carry 긴급 전환**을 유도하는 강력한 경고(Warning) 로직을 실행합니다.

### 3.5 [NEW] AI 기반 송장(Invoice) 자동화 및 휴먼 에러 방지 로직
AOG 자재 파송 시 송장에 수취인(조업사) 정보를 잘못 적는 휴먼 에러를 원천 차단합니다.
- **Data Binding**: 데이터베이스의 `station_info`에 등록된 검증된 주소(`address`)와 조업사(`handling_agent`) 데이터를 불러옵니다.
- **Auto-Generation**: 기번, 자재 정보, 도착지 정보를 조합하여 AOG 전용 영문 송장(Invoice) 텍스트를 버튼 클릭 한 번으로 무결성 있게 포맷팅하여 렌더링합니다.

### 3.6 자동 진행 vs 승인 대기 (`_auto_sweep_silent_steps()`)
- **1~4단계**는 내부 재고 조회 및 최적화 연산(판단 불필요)이라 재고가 없으면 **자동으로 다음 단계까지** 확인합니다.
- **5단계**는 문의 대상(교집합)이 없으면 자동으로 6단계로 넘어갑니다.
- **문의 대상이 있는 5단계·6단계·재고 확보 지점·7단계**에서만 멈춰 사람의 **승인/거절**을 받습니다.
- 이렇게 해서 "알고리즘이 순식간에 훑고, 사람은 실제 외부 연락이 필요한 지점에서만 결정" 하도록 했습니다.

### 3.7 AI의 역할 (속도 우선)
- 좌측 "AI 상황 요약 & 추천 행동"은 **항상 규칙 기반으로 즉시(0초)** 표시됩니다(매 단계 LLM 호출 없음).
- 로컬 LLM(Qwen2.5-0.5B, 선택)은 **5·6단계 영문 요청 메일 문구를 다듬을 때만** 사용되며, 실패해도 기본 영문 템플릿이 그대로 유지되어 앱이 멈추지 않습니다.

### 3.8 실시간 운항/허브 현황
- 항공편·정박 데이터는 더미 공급자(`_fetch_raw_flight_feed` / `fetch_airport_parking_status`)에서 오며, `FLIGHT_API_CONFIG` / `PARKING_API_CONFIG`의 `enabled`를 켜고 표시 지점에 실제 API 호출만 채우면 나머지(지도·표·Hand-carry 후보)는 코드 변경 없이 동작합니다.
- 화면은 **최다 허브·주력 노선 KPI**, 마커 크기=운항량/색=정박 혼잡도, 노선 굵기=빈도, 허브/노선 랭킹 표로 구성됩니다.

---

## 4. 화면 & GUI

- **전문가형 테마**: 상단 히어로 배너, 카드형 정보 패널, `stMetric` 카드 스타일, 일관된 네이비/블루 팔레트.
- **한눈에 들어오는 진행 표시**: 케이스 시작 시 기번/기종·자재·공항·현재상태 **정보 카드**와, 1→7단계 **가로 스텝퍼**(현재 단계 파랑, 확보 초록 ✓, 미확보 회색)를 표시합니다.
- **자재 이력 패널**: 진행 중인 자재의 과거 수배 이력·결함 조치 이력을 좌우 표로 자동 표시합니다.
- **단계별 실제 조치**: FAK→정비사 전화, Allocation→부서 전화/메일, 최적화→이송업체 수배, Pooling→파트너 연락, 5·6→영문 긴급 메일(대상 자동 산정), 7→통관팀+편명 선택+AI인보이스+야간통관가이드.

---

## 5. 테스트 시나리오 (채팅에 그대로 입력 — 7단계 전부 재현)

각 단계가 실제로 도달·해결되는 예시입니다. **같은 자재라도 발생 공항/운영사에 따라 결과가 달라지는 것**이 핵심입니다.

| # | 도달 단계 | 입력(채팅) | 기대 결과 |
|---|---|---|---|
| 1 | **1 FAK** | `HL7702 CDG에서 AOG, 부품 OXY-GEN-A330-15 필요` | 소모품(산소발생기)은 기체 탑재 키트 → **공항 무관** 즉시 해결 |
| 2 | **2 로컬창고** | `HL7702 ICN에서 AOG, 부품 FUEL-NOZ-A330-07 필요` | ICN 자사 창고 보유 → 즉시 불출 |
| 3 | **3 이송(자사)** | `HL7702 BKK에서 AOG, 부품 FUEL-NOZ-A330-07 필요` | BKK엔 없지만 ICN 자사 창고에서 이송 → Lead Time 계산·추천 |
| 3 | **3 이송(제휴)** | `HL8259 JFK에서 AOG, 부품 HYD-PUMP-737-11 필요` | 풀 계약은 JFK 미커버지만 **JFK 제휴 창고(Non-Pool)** 에서 땡겨옴 |
| 4 | **4 Pooling** | `HL8501 FRA에서 AOG, 부품 APU-321N-30 필요` | 자사·제휴에 없고 LHT 풀이 FRA 커버 → Pooling 대여 |
| 5 | **5 Main Station** | `HL8008 HKG에서 AOG, 부품 (희귀 P/N) 필요` | HKG 기반 Cathay가 B777 운영 → 영문 메일 문의 |
| 6 | **6 동일기종 타사** | `HL8259 ICN에서 AOG, 부품 (희귀 P/N) 필요` | ICN 기반 아시아나는 B737 미운영 → 5단계 자동 통과 → 6단계 전체 문의 |
| 7 | **7 파송(경고)** | `LJ2201 CDG에서 AOG, 부품 (희귀 P/N) 필요` | **진에어 + CDG(화물인가 N)** → 7단계에서 **자사 카고 불가 경고** + Hand-carry 유도 |
| 7 | **7 파송(정상)** | `LJ2201 NRT에서 AOG, 부품 (희귀 P/N) 필요` | 진에어 + NRT(화물인가 Y) → 자사 카고 파송 가능 안내 |

**7단계 도달 시 함께 확인**
- 🌙 **야간 통관 가이드**: 관세사 부재(야간) 대비 직접 통관 체크리스트(유니패스 신고 등) — 신고 누락(휴먼에러) 방지.
- 🧾 **AI 인보이스 생성**: `✨ 인보이스 생성/갱신` 클릭 → DB의 **검증된 조업사 주소(handling_agent/address)** 가 자동 반영된 영문 송장/신고서 초안. 조업사 변경으로 인한 오배송을 원천 차단.
- 📖 **과거 이력**: 진행 중 자재의 과거 수배(빌린)·결함 조치 이력이 자동 표로 표시 → "지난번 어디서 빌렸고, 리셋으로 됐는지 교환했는지" 참고.

> 참고: `(희귀 P/N)`은 데이터에 없는 임의 파트넘버(예: `RARE-777-PART-88`)를 넣으면 됩니다 — 어느 창고·풀에도 없어 타사 문의/파송 단계까지 진행됩니다.
