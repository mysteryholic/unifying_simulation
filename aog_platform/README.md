# AOG Command Center — 배포용 플랫폼

AOG(Aircraft-on-Ground) 자재 수급 대시보드. **서버 없이 구글 드라이브를 데이터 서버**로 쓰고,
**프론트엔드/백엔드 역할을 분리**해 코딩 초보자도 쉽게 협업·유지보수하도록 설계했습니다.
로컬(VS Code/Windows)에서 바로 실행되고, 그대로 웹에 배포할 수 있습니다.

```
aog_platform/
├─ frontend.py                # 프론트엔드: 코드 기반 UI 프레임워크(테마·위젯·렌더러)
├─ backend.py                 # 백엔드: 단일 파일 (CSV 읽기→가공→패키징 + AOG 조회 엔진)
├─ config/
│  ├─ app_config.yaml         # ← 프론트 담당: PPT처럼 페이지/위젯 편집 (세부 화면 구성)
│  └─ data_sources.yaml       # ← 백엔드 담당: 데이터 위치(드라이브 파일ID/로컬)
├─ tools/make_dummy_data.py   # 더미 CSV 생성기
├─ templates/                 # 영문 메일·인보이스 양식(뼈대)
└─ data/
   ├─ raw/*.csv               # 원본 CSV(=드라이브에 올릴 파일)
   └─ packaged/app_data.json  # 백엔드가 만든 가공 데이터(프론트가 읽음)
```

---

## 역할 분담 (핵심)

### 프론트엔드 담당 — "전체 틀은 코드, 세부는 PPT처럼"
- **전체 UI 느낌**(색·레이아웃·위젯 종류)은 `frontend.py` 에 **코드로** 정의되어 있습니다(테마 CSS, 위젯 렌더러).
  → UI 톤을 크게 바꾸고 싶을 때만 이 파일을 만집니다.
- **세부 화면 구성**(어떤 페이지에 어떤 표/숫자/차트를 놓을지)은 `config/app_config.yaml` 에서
  **PPT 슬라이드 짜듯이** 선언만 하면 됩니다. **코드 수정 불필요.**
  ```yaml
  pages:
    - name: "재고 현황"
      icon: "📦"
      sections:
        - type: kpi_row
          items: [{ label: "등록 기번", dataset: aircraft_registry, agg: count }]
        - type: table
          title: "제휴 창고 재고"
          dataset: alliance_stock
          columns: [airport_code, partner, part_number, qty]
  ```
  섹션 `type`: `aog_query`(AOG 조회 화면) · `kpi_row` · `table` · `chart` · `markdown`.

### 백엔드 담당 — "raw 데이터를 가공해 프론트에 넘기기"
- `backend.py` **한 파일**만 관리합니다. raw CSV(드라이브/로컬)를 읽어 정리(clean)하고,
  프론트가 그대로 쓰는 **패키지 데이터(app_data.json)** 로 포장합니다. + **AOG 7단계 조회 엔진**(`resolve_aog`) 포함.
- 데이터 위치는 `config/data_sources.yaml` 에서 지정합니다(로컬 파일 또는 드라이브 파일ID).
- 새 데이터셋 추가: `data_sources.yaml` 에 항목 추가 → 필요 시 `backend.py`의 `_clean()` 규칙만 손보면 끝.

> 프론트는 backend 의 **딱 두 함수**만 씁니다: `load_packaged()`(표/차트 데이터), `resolve_aog(기번, 파트, 공항)`(조회 결과).
> 이 "데이터 계약"이 고정이라, 나중에 백엔드를 실제 API 서버로 바꿔도 프론트는 그대로 → **앱/웹앱 확장이 쉽습니다.**

---

## 실행 (VS Code / Windows / macOS 공통)

```bash
# 1) (최초 1회) 가상환경 + 설치
python -m venv .venv
# Windows:  .venv\Scripts\activate     |  macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

# 2) 더미 데이터 생성(최초 1회, 이미 있으면 생략 가능)
python tools/make_dummy_data.py

# 3) 실행
streamlit run frontend.py
```
브라우저가 자동으로 열립니다(기본 http://localhost:8501). 코랩 불필요.

---

## 구글 드라이브를 데이터 서버로 쓰기

1. `data/raw/` 의 CSV들을 구글 드라이브 폴더에 업로드합니다(팀이 함께 편집).
2. 각 CSV를 **'링크가 있는 모든 사용자 - 뷰어'** 로 공유하고, 링크의 파일 ID를 복사합니다.
   (`https://drive.google.com/file/d/`**`파일ID`**`/view`)
3. `config/data_sources.yaml` 에서 `mode: drive` 로 바꾸고 각 데이터셋 `drive_id: "파일ID"` 를 채웁니다.
   백엔드가 실행 시마다 드라이브에서 최신 CSV를 자동 다운로드합니다(읽기 전용, 인증 불필요).

> 팀은 **CSV만 드라이브에서 편집**하면 됩니다. 코드 배포 없이 데이터가 갱신됩니다.

---

## 웹 배포 (서버 구매 전 무료 옵션)

- **Streamlit Community Cloud**: GitHub 저장소를 연결하고 main 파일을 `aog_platform/frontend.py` 로 지정하면 웹앱이 뜹니다.
  `mode: drive` 로 두면 드라이브 CSV를 그대로 읽습니다.
- 이후 트래픽/보안이 필요해지면: `backend.py`의 순수 함수(`resolve_aog`, `load_packaged`)를 그대로 **FastAPI** 등으로
  감싸 실제 API 서버로 승격하고, 프론트(웹/모바일 앱)는 같은 데이터 계약으로 붙이면 됩니다.

---

## 데이터셋 (컬럼)
`tools/make_dummy_data.py` 참고. 요약: 기번등록부 · FAK키트 · 로컬창고 · 제휴창고 · Pooling(재고/파트너사) ·
기종별운영사 · 공항취항사 · 공항/조업사(진에어인가) · 내부연락망(Allocation/통관·카고) · 수배이력 · 결함조치이력.

## AOG 조회 7단계 (backend.resolve_aog)
1 FAK → 2 로컬 Allocation → 3 Pooling(커버리지) → 4 Main Station 타사 → 5 동일기종 타사 →
6 이송 최적화(자사 타 스테이션 + 제휴 Non-Pool, Lead Time 최단) → 7 파송(진에어 화물인가·부서연락·인보이스).
같은 자재라도 **발생 공항/운영사**에 따라 결과가 달라집니다.
