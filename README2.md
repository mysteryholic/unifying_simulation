# README2 — 작업 인수인계 / 이어서 진행 가이드 (Handoff)

> 이 문서는 **토큰이 부족해도 다음 세션에서 이어서 진행**할 수 있도록 목표·현재 상태·구현 범위·남은 일을
> 기록한 살아있는 핸드오프 문서입니다. 새 세션은 **이 문서를 먼저 읽고** `## 다음에 할 일`부터 진행하세요.
> (기존 `README.md`는 Streamlit '프로토타입(단일 앱)' 설명 문서이며 그대로 둡니다.)

---

## 1. 최종 목표

AOG(Aircraft on Ground) 자재 수급 대시보드를 **실제 앱/웹앱으로 배포**한다. 협업·유지보수가 쉽고,
서버 없이 **구글 드라이브를 데이터 서버**로 사용하며, 나중에 네이티브 앱/웹앱으로 확장하기 쉬운 구조.

### 협업 역할 분리 (둘 다 코딩 초보 · 앱개발 경험 없음)
- **프론트엔드 담당**: `config/app_config.yaml`만 편집해 **PPT 짜듯이** 화면(페이지·위젯)을 구성. 코드 거의 안 봄.
- **백엔드 담당**: `backend.py`(단일 파일) + `config/data_sources.yaml`만 관리. 드라이브의 raw CSV를 읽어
  가공(clean/join) → 프론트가 쓸 **packaged 데이터(JSON)** 로 포장해서 넘김.

### 확정된 설계 원칙 (사용자 지시)
- 백엔드는 **하나(또는 몇 개) 파일**로 유지 — `backend.py` 단일 파일 지향.
- **구글 코랩 불필요** → **VS Code / Windows 로컬 실행** 기준. 배포 쉬운 형태(예: Streamlit Cloud).
- 프로토타입 **UI 톤**: **Flexport · Samsara · Linear · Palantir Foundry / Command Center** 느낌
  (다크, 데이터-옵스 대시보드, 고밀도, 모노스페이스 악센트, 좌측 내비, 상태 chip, 표 중심, 미니멀 크롬).
- 지금은 실데이터 없음 → **더미 CSV로 테스트**(사용자가 드라이브에 업로드해서 확인 예정).
- 데이터 계약(packaged JSON) = 나중에 실 API로 바꿔도 프론트 그대로 → 앱/웹앱 확장 용이.

---

## 2. 폴더 구조 (현재)

```
KE_unify_OZ/                      # git repo (origin: github.com/mysteryholic/unifying_simulation)
├─ AOG_Dashboard.ipynb           # [기존] Streamlit 프로토타입(7단계 엔진 단일 노트북) — 유지
├─ README.md                     # [기존] 프로토타입 상세 설명 — 유지
├─ README2.md                    # ← 이 핸드오프 문서
└─ aog_platform/                 # [신규] 배포용 플랫폼 (프론트/백엔드 분리 구조)
   ├─ backend.py                 # (예정) 단일 백엔드: config 로드 + CSV(드라이브/로컬) 읽기 + 가공 + 패키징 + AOG 엔진
   ├─ frontend.py                # (예정) 설정(YAML) 기반 Streamlit 렌더러 (커맨드센터 UI)
   ├─ requirements.txt           # (예정)
   ├─ README.md                  # (예정) 플랫폼 사용법(역할별)·실행(VS Code/Win)·드라이브 연동·배포
   ├─ config/
   │  ├─ data_sources.yaml       # (예정) 백엔드 영역: 데이터셋별 드라이브 파일ID 또는 로컬경로 + mode(local/drive)
   │  └─ app_config.yaml         # (예정) 프론트 영역: 페이지/위젯 선언(PPT식)
   ├─ tools/
   │  └─ make_dummy_data.py      # [완료] 더미 CSV·템플릿 생성기 (실행: python tools/make_dummy_data.py)
   ├─ templates/
   │  ├─ aog_support_request_en.txt  # [완료] 영문 대여요청 메일 양식(뼈대, {필드} 치환)
   │  └─ aog_invoice_template.txt    # [완료] 영문 파송 인보이스/신고서 양식(뼈대)
   └─ data/
      ├─ raw/*.csv               # [완료] 더미 원본 CSV 13종 (아래 목록)
      └─ packaged/               # (예정) backend가 생성하는 가공 데이터(app_data.json)
```

### 완료된 더미 CSV (data/raw/) — 컬럼은 '실데이터 요청 목록'과 동일
| 파일 | 컬럼 | 용도(단계) |
|---|---|---|
| aircraft_registry.csv | registration, aircraft_type, operator | 기번→기종·운영사 |
| fak_kits.csv | aircraft_type, kit_name, part_number, part_name, qty | 1 FAK |
| allocation_stock.csv | airport_code, warehouse_name, aircraft_type, part_number, part_name, qty | 2 로컬 / 6 이송 |
| alliance_stock.csv | airport_code, partner, aircraft_type, part_number, part_name, qty | 6 이송(Non-Pool) |
| pooling_stock.csv | partner, location_airport, aircraft_type, part_number, part_name, qty | 3 Pooling |
| pooling_partners.csv | partner, contact, email, coverage_airports | 3 Pooling(커버리지) |
| fleet_operators.csv | aircraft_type, airline, contact, email | 5 동일기종 |
| station_airlines.csv | airport_code, airline, contact, email | 4 Main Station |
| station_handlers.csv | airport_code, handling_agent, address, jinair_cargo_auth | 7 인보이스/진에어인가 |
| allocation_contacts.csv | airport_code, department, contact, email | 2·7 내부 |
| hq_contacts.csv | team, contact, email (통관팀/카고팀) | 2·7 내부 |
| sourcing_history.csv | date, registration, aircraft_type, part_number, airport, source, method, lead_time_hours, result | 이력/추천 |
| defect_history.csv | date, registration, defect, resolution, parts_scope, tools_required, downtime_hours | 이력 |

---

## 3. AOG 프로세스 알고리즘 (프로토타입에서 검증됨 → 백엔드로 이식할 것)

입력: **기번 · 자재 파트넘버 · 발생 공항**. 순서(사용자 확정):
1. **FAK 키트** (기종별 소모품 패키지, 기체 탑재 → 공항 무관)
2. **로컬 Allocation** (발생 공항 자사 창고)
3. **Pooling** (파트너 재고 + coverage 공항 일치)
4. **Main Station 타사** (발생 공항 취항사 ∩ 기종 운영사, 영문 메일)
5. **동일 기종 타사 전체** (영문 메일)
6. **이송 최적화** (타 공항 자사창고 + 제휴창고 Non-Pool, Lead Time 최단 추천)
7. **Hand-carry/Cargo 파송** (진에어 화물인가 검증 + 부서 즉시연락/내부Request + AI 인보이스 + 야간통관 가이드)

- 자동 진행: 1~3 재고없으면 자동, 4는 대상없으면 자동, 6은 이송안없으면 자동 → 4·5(문의)·확보지점·7에서만 사람 승인.
- **핵심 규칙**: 같은 자재라도 발생 공항/운영사에 따라 결과가 달라짐(창고 공항일치, 풀 커버리지, 진에어 인가).
- **주의(과거 버그)**: FAK 키트에 로터블(교환품) 넣으면 모든 케이스가 1단계에서 오종료 → FAK엔 소모품만.
- `calculate_lead_time(origin,dest,operator)` = 운송(직항/ICN경유) + 조업 + 카고부킹.
- 프로토타입 원본 로직/데이터: `AOG_Dashboard.ipynb`의 Cell 2 및 프로토타입 `README.md` 참고.

---

## 4. 지금까지 구현 (DONE) — 플랫폼 MVP 완성

- [x] 플랫폼 폴더 구조 생성
- [x] 더미 CSV 13종 (`data/raw/`) + 메일/인보이스 템플릿 2종 (`templates/`) + 생성기 `tools/make_dummy_data.py`
- [x] **`config/data_sources.yaml`** — 백엔드 데이터 위치(로컬/드라이브 file_id) 설정
- [x] **`backend.py`** (단일 파일) — CSV 읽기(로컬/드라이브)→가공(clean)→패키징(`app_data.json`) + **AOG 7단계 엔진**(`resolve_aog`). 순수 함수, Streamlit 비의존 → 실 API 이식 쉬움.
- [x] **`config/app_config.yaml`** — 프론트가 PPT처럼 편집하는 페이지/섹션 선언
- [x] **`frontend.py`** — 코드 기반 UI 프레임워크(Flexport 톤: 밝은 배경·네이비 좌측레일·블루 액센트·고밀도 표·상태 chip) + 설정 렌더러. 세부는 app_config.yaml로 편집.
- [x] **`requirements.txt`**, **`aog_platform/README.md`**(역할별 사용법·VS Code/Windows 실행·드라이브 연동·배포)
- [x] 테스트 통과: backend build(106행), 엔진 5개 시나리오(1·2·3·6·7단계) 정확, 진에어 CDG 화물인가 경고, 전 페이지 렌더 예외 없음, streamlit 부팅 HTTP 200
- [x] 핸드오프 문서(본 README2)

**아키텍처 요약**: 프론트(코드 UI 틀 `frontend.py` + PPT식 `app_config.yaml`) ↔ 데이터 계약(`load_packaged`, `resolve_aog`) ↔ 백엔드(`backend.py` + `data_sources.yaml`) ↔ raw CSV(구글 드라이브).

## 5. 다음에 할 일 (TODO — 우선순위)

1. **실행 확인(사용자)**: `cd aog_platform` → `pip install -r requirements.txt` → `python tools/make_dummy_data.py` → `streamlit run frontend.py`. UI/동작 확인.
2. **실데이터 연결**: 팀이 CSV를 구글 드라이브에 업로드 → 공유(뷰어) → `data_sources.yaml` `mode: drive` + 각 `drive_id` 채우기.
3. **양식 교체**: `templates/aog_support_request_en.txt`, `aog_invoice_template.txt` 를 실제 사내 공식 양식으로 교체(치환 필드 `{...}` 유지).
4. **UI 디테일 튜닝**: app_config.yaml에서 페이지/표/차트 배치 조정. 필요 시 frontend.py의 CSS/위젯 보강(예: 지도, 실시간 항공편 API 위젯).
5. **일괄 메일 타겟 로직 고도화**: 현재는 fleet_operators/station_airlines 매칭. 실 SQL/파라미터 확보 시 backend에 반영.
6. **실시간 항공편/정박 API**(요청목록 5번): 7단계 편명 매칭·지도. backend에 provider 함수 추가(프로토타입 `AOG_Dashboard.ipynb` 참고).
7. **배포**: Streamlit Community Cloud에 repo 연결, main=`aog_platform/frontend.py`. 이후 필요 시 backend를 FastAPI로 승격.
8. 매 작업 후 **git push** + 본 README2의 DONE/TODO 갱신.

### 검증용 시나리오(엔진 이식 후 확인)
- 1 FAK: `HL7702 / OXY-GEN-A330-15 / CDG` → 1단계
- 2 로컬: `HL7702 / FUEL-NOZ-A330-07 / ICN` → 2단계
- 3 Pooling: `HL8501 / APU-321N-30 / FRA` → 3단계
- 4 MainStn: `HL8008 / RARE-777-88 / HKG` → 4단계(문의)
- 5 동일기종: `HL8259 / RARE-737-99 / ICN` → 5단계
- 6 이송(제휴): `HL8259 / HYD-PUMP-737-11 / JFK` → (5 거절 후) 6단계
- 7 파송(진에어경고): `LJ2201 / RARE-737-99 / CDG` → (5 거절) 7단계 + CDG 화물인가 N 경고

---

## 6. 참고 / 환경

- git: repo 루트 `KE_unify_OZ`, origin `github.com/mysteryholic/unifying_simulation`, 기본 브랜치 `main`.
- 커밋 규칙: 작업 후 push. 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- 로컬 테스트 산출물(`data/packaged/`, `aog_db.json` 등)은 커밋 불필요 시 제외 가능.
- pyyaml/pandas/streamlit 로컬 설치 확인됨(테스트 환경). 실행 커맨드: `streamlit run aog_platform/frontend.py`.
