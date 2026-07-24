# -*- coding: utf-8 -*-
"""
더미 데이터 생성기 (테스트용)
- 실행: python tools/make_dummy_data.py
- 결과: data/raw/*.csv 와 templates/*.txt 생성
- 실제 운영 시에는 이 CSV들을 구글 드라이브에 올려서 사용하면 됩니다(각 CSV를 '링크가 있는 모든 사용자
  - 뷰어'로 공유 → data_sources.yaml에 파일 ID 붙여넣기). 지금은 로컬 테스트용 더미입니다.
컬럼 구성은 '[AOG 대시보드 프로젝트 실데이터 요청 목록]'과 동일합니다.
"""
import csv
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
TPL = os.path.join(BASE, "templates")
os.makedirs(RAW, exist_ok=True)
os.makedirs(TPL, exist_ok=True)


def write_csv(name, header, rows):
    path = os.path.join(RAW, name)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: 엑셀 한글 호환
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print("wrote", os.path.relpath(path, BASE), f"({len(rows)} rows)")


# 1) 기번 등록부 (operator: 대한항공/진에어 — 7단계 화물 인가 분기에 사용)
write_csv("aircraft_registry.csv",
    ["registration", "aircraft_type", "operator"],
    [["HL7702", "A330-300", "대한항공"], ["HL7710", "A330-300", "대한항공"],
     ["HL8008", "B777-300ER", "대한항공"], ["HL8009", "B777-300ER", "대한항공"],
     ["HL8259", "B737-800", "대한항공"], ["HL8260", "B737-800", "대한항공"],
     ["HL8501", "A321neo", "대한항공"], ["HL8081", "B787-9", "대한항공"],
     ["HL8360", "A350-900", "대한항공"],
     ["LJ2201", "B737-800", "진에어"], ["LJ2202", "B737-800", "진에어"],
     ["LJ7771", "B777-300ER", "진에어"]])

# 2) FAK 키트 구성표 (소모품/비상품목만)
write_csv("fak_kits.csv",
    ["aircraft_type", "kit_name", "part_number", "part_name", "qty"],
    [["A330-300", "A330-300 표준 FAK", "OXY-GEN-A330-15", "Chemical Oxygen Generator", 2],
     ["A330-300", "A330-300 표준 FAK", "SMK-DET-A330-21", "Cargo Smoke Detector", 3],
     ["A330-300", "A330-300 표준 FAK", "LIFE-VEST-A330-40", "Passenger Life Vest", 8],
     ["B777-300ER", "B777-300ER 표준 FAK", "OXY-GEN-777-15", "Chemical Oxygen Generator", 2],
     ["B777-300ER", "B777-300ER 표준 FAK", "SMK-DET-777-22", "Cargo Smoke Detector", 3],
     ["B737-800", "B737-800 표준 FAK", "OXY-GEN-737-15", "Chemical Oxygen Generator", 2],
     ["B737-800", "B737-800 표준 FAK", "SMK-DET-737-04", "Cargo Smoke Detector", 3],
     ["B737-800", "B737-800 표준 FAK", "LIFE-VEST-737-42", "Passenger Life Vest", 8],
     ["A321neo", "A321neo 표준 FAK", "OXY-GEN-321N-15", "Chemical Oxygen Generator", 2],
     ["A321neo", "A321neo 표준 FAK", "SMK-DET-321N-43", "Cargo Smoke Detector", 3],
     ["B787-9", "B787-9 표준 FAK", "OXY-GEN-787-15", "Chemical Oxygen Generator", 2],
     ["B787-9", "B787-9 표준 FAK", "SMK-DET-787-44", "Cargo Smoke Detector", 3],
     ["A350-900", "A350-900 표준 FAK", "OXY-GEN-350-19", "Chemical Oxygen Generator", 2],
     ["A350-900", "A350-900 표준 FAK", "SMOKE-DET-350-11", "Cargo Smoke Detector", 2]])

# 3) 자사 로컬 창고 재고 (Allocation, View Pool)
write_csv("allocation_stock.csv",
    ["airport_code", "warehouse_name", "aircraft_type", "part_number", "part_name", "qty"],
    [["ICN", "ICN 본사 통합 자재창고", "A330-300", "FUEL-NOZ-A330-07", "Engine Fuel Nozzle", 4],
     ["ICN", "ICN 본사 통합 자재창고", "A330-300", "IDG-A330-001", "Integrated Drive Generator", 2],
     ["ICN", "ICN 본사 통합 자재창고", "B777-300ER", "BRK-B777-CARBON-01", "Carbon Brake Assembly", 1],
     ["ICN", "ICN 본사 통합 자재창고", "B737-800", "STARTER-GEN-737-03", "Starter Generator", 2],
     ["ICN", "ICN 본사 통합 자재창고", "B787-9", "APU-787-01", "Auxiliary Power Unit", 1],
     ["GMP", "GMP 지점 자재창고", "B737-800", "WHL-MLG-737-25", "Main Landing Gear Wheel", 3],
     ["FRA", "FRA 해외지점 창고", "A330-300", "IDG-A330-001", "Integrated Drive Generator", 1],
     ["JFK", "JFK 해외지점 창고", "B787-9", "WHL-MLG-787-22", "Main Landing Gear Wheel", 2],
     ["BKK", "BKK 해외지점 창고", "A330-300", "BRK-A330-CARBON-12", "Carbon Brake Assembly", 1]])

# 4) 제휴 창고 재고 (Non-Pool)
write_csv("alliance_stock.csv",
    ["airport_code", "partner", "aircraft_type", "part_number", "part_name", "qty"],
    [["CDG", "Air France Industries (제휴)", "A330-300", "FUEL-NOZ-A330-07", "Engine Fuel Nozzle", 1],
     ["JFK", "Delta TechOps (제휴)", "B737-800", "HYD-PUMP-737-11", "Engine-Driven Hydraulic Pump", 1],
     ["FRA", "Lufthansa Technik (제휴)", "B777-300ER", "BRK-B777-CARBON-01", "Carbon Brake Assembly", 1],
     ["SIN", "SIA Engineering (제휴)", "B737-800", "HYD-PUMP-737-11", "Engine-Driven Hydraulic Pump", 2]])

# 5) Pooling 파트너 재고
write_csv("pooling_stock.csv",
    ["partner", "location_airport", "aircraft_type", "part_number", "part_name", "qty"],
    [["Lufthansa Technik", "FRA", "A321neo", "APU-321N-30", "Auxiliary Power Unit", 1],
     ["HAECO", "HKG", "B777-300ER", "WHL-MLG-777-06", "Main Landing Gear Wheel", 2],
     ["AAR Corp", "JFK", "A321neo", "AVIONICS-FMS-321N-04", "Flight Management Computer", 1],
     ["ANA Base Maintenance", "NRT", "B787-9", "CARGO-DOOR-ACT-787-03", "Cargo Door Actuator", 1],
     ["SIA Engineering", "SIN", "A350-900", "BRK-350-CARBON-29", "Carbon Brake Assembly", 1]])

# 6) Pooling 파트너사 정보
write_csv("pooling_partners.csv",
    ["partner", "contact", "email", "coverage_airports"],
    [["Lufthansa Technik", "+49-40-5070-5553", "pooling@lht.dlh.de", "FRA,CDG"],
     ["HAECO", "+852-2767-6111", "pooling@haeco.com", "HKG,SIN,BKK"],
     ["AAR Corp", "+1-630-227-2000", "pooling@aarcorp.com", "JFK,LAX"],
     ["ANA Base Maintenance", "+81-3-6735-1111", "pooling@ana.co.jp", "NRT,HND,ICN"],
     ["SIA Engineering", "+65-6541-2000", "pooling@siae.com.sg", "SIN,HKG,BKK,ICN"]])

# 7) 기종별 운영 타사 정보 (6단계 전체 문의 대상)
write_csv("fleet_operators.csv",
    ["aircraft_type", "airline", "contact", "email"],
    [["A330-300", "아시아나항공", "02-2669-8000", "fleet.a330@flyasiana.com"],
     ["A330-300", "Cathay Pacific", "+852-2747-1888", "fleet.a330@cathaypacific.com"],
     ["A330-300", "Thai Airways", "+66-2-356-1111", "fleet.a330@thaiairways.com"],
     ["B777-300ER", "Cathay Pacific", "+852-2747-1888", "fleet.b777@cathaypacific.com"],
     ["B777-300ER", "Emirates", "+971-600-555555", "fleet.b777@emirates.com"],
     ["B737-800", "제주항공", "02-2015-1000", "fleet.b737@jejuair.net"],
     ["B737-800", "티웨이항공", "1688-8686", "fleet.b737@twayair.com"],
     ["B737-800", "Ryanair", "+353-1-945-1212", "fleet.b737@ryanair.com"],
     ["A321neo", "에어부산", "1666-3060", "fleet.a321n@airbusan.com"],
     ["A321neo", "JAL", "+81-3-5460-3121", "fleet.a321n@jal.com"],
     ["B787-9", "ANA", "+81-3-6735-1000", "fleet.b787@ana.co.jp"],
     ["B787-9", "United Airlines", "+1-800-864-8331", "fleet.b787@united.com"],
     ["A350-900", "아시아나항공", "02-2669-8000", "fleet.a350@flyasiana.com"],
     ["A350-900", "Qatar Airways", "+974-4023-0000", "fleet.a350@qatarairways.com.qa"]])

# 8) 공항별 취항 항공사 (5단계 근거리 Main Station 문의)
write_csv("station_airlines.csv",
    ["airport_code", "airline", "contact", "email"],
    [["ICN", "아시아나항공", "02-2669-8000", "ops.icn@flyasiana.com"],
     ["GMP", "제주항공", "02-2015-1000", "ops.gmp@jejuair.net"],
     ["NRT", "ANA", "+81-3-6735-1000", "ops.nrt@ana.co.jp"],
     ["HKG", "Cathay Pacific", "+852-2747-1888", "ops.hkg@cathaypacific.com"],
     ["CDG", "Air France", "+33-1-4356-7890", "ops.cdg@airfrance.fr"],
     ["JFK", "Delta Air Lines", "+1-800-221-1212", "ops.jfk@delta.com"],
     ["FRA", "Lufthansa", "+49-69-86799799", "ops.fra@lufthansa.com"],
     ["SIN", "Singapore Airlines", "+65-6223-8888", "ops.sin@singaporeair.com"],
     ["BKK", "Thai Airways", "+66-2-356-1111", "ops.bkk@thaiairways.com"],
     ["LAX", "United Airlines", "+1-800-864-8331", "ops.lax@united.com"]])

# 9) 공항/조업사 정보 (7단계 인보이스 수취인 + 진에어 화물 인가)
write_csv("station_handlers.csv",
    ["airport_code", "handling_agent", "address", "jinair_cargo_auth"],
    [["ICN", "KAS (Korean Air Service)", "285, Jega-ro, Jung-gu, Incheon, Republic of Korea", "Y"],
     ["GMP", "KAS Gimpo", "Gimpo Int'l Airport Cargo Terminal, Seoul, Republic of Korea", "Y"],
     ["NRT", "ANA Cargo", "Narita International Airport, Chiba, Japan", "Y"],
     ["JFK", "Delta Cargo", "JFK Int'l Airport, Cargo Bldg 75, Jamaica, NY 11430, USA", "N"],
     ["CDG", "Air France Cargo", "Roissy CDG, Tremblay-en-France, France", "N"],
     ["FRA", "Fraport Cargo", "Frankfurt Airport CargoCity Sued, Germany", "N"],
     ["SIN", "SATS Cargo", "Singapore Changi Airport, Airfreight Terminal 1, Singapore", "Y"],
     ["HKG", "HACTL", "Hong Kong Int'l Airport, SuperTerminal 1, Hong Kong", "Y"],
     ["BKK", "BFS Cargo", "Suvarnabhumi Airport Free Zone, Thailand", "Y"],
     ["LAX", "Mercury Air Cargo", "Los Angeles Int'l Airport, CA 90045, USA", "Y"]])

# 10) 내부 부서 연락망 (공항별 Allocation)
write_csv("allocation_contacts.csv",
    ["airport_code", "department", "contact", "email"],
    [["ICN", "자재관리팀 Allocation 파트", "02-XXXX-1000", "allocation.icn@airline.example"],
     ["GMP", "자재관리팀 Allocation(김포)", "02-XXXX-1005", "allocation.gmp@airline.example"],
     ["NRT", "해외지점 Allocation(나리타)", "+81-3-XXXX-1010", "allocation.nrt@airline.example"],
     ["CDG", "해외지점 Allocation(파리)", "+33-1-XXXX-1015", "allocation.cdg@airline.example"],
     ["FRA", "해외지점 Allocation(프랑크푸르트)", "+49-69-XXXX-1030", "allocation.fra@airline.example"],
     ["SIN", "해외지점 Allocation(싱가포르)", "+65-XXXX-1025", "allocation.sin@airline.example"],
     ["JFK", "해외지점 Allocation(뉴욕)", "+1-718-XXXX-1040", "allocation.jfk@airline.example"]])

# 11) 내부 부서 연락망 (본사 팀: 통관/카고)
write_csv("hq_contacts.csv",
    ["team", "contact", "email"],
    [["통관팀", "02-XXXX-2000", "customs@airline.example"],
     ["카고 예약팀", "02-XXXX-3000", "cargo.booking@airline.example"]])

# 12) 과거 수배(대여) 이력
write_csv("sourcing_history.csv",
    ["date", "registration", "aircraft_type", "part_number", "airport", "source", "method", "lead_time_hours", "result"],
    [["2026-06-25", "HL7702", "A330-300", "OXY-GEN-A330-15", "CDG", "기체 탑재 FAK 키트", "자체재고(FAK)", 1, "성공"],
     ["2026-05-12", "HL7710", "A330-300", "IDG-A330-001", "FRA", "Lufthansa Technik (FRA)", "대여(Loan)", 6, "성공"],
     ["2026-02-20", "HL7702", "A330-300", "IDG-A330-001", "ICN", "ICN 본사 통합 자재창고", "자체재고(Allocation)", 2, "성공"],
     ["2026-06-01", "HL7710", "A330-300", "FUEL-NOZ-A330-07", "BKK", "ICN 자사창고→BKK 이송", "이송(자사)", 11, "성공"],
     ["2026-03-15", "HL8259", "B737-800", "HYD-PUMP-737-11", "SIN", "SIA Engineering 제휴창고(SIN)", "제휴(Non-Pool)", 4, "성공"],
     ["2026-01-09", "HL8260", "B737-800", "HYD-PUMP-737-11", "JFK", "Delta TechOps 제휴창고(JFK)", "제휴(Non-Pool)", 3, "성공"],
     ["2026-06-18", "HL8081", "B787-9", "APU-787-01", "LAX", "United Airlines (LAX)", "대여(Loan)", 6, "실패"],
     ["2026-06-19", "HL8081", "B787-9", "APU-787-01", "LAX", "본사 ICN→LAX KE011", "Hand-carry", 30, "성공"]])

# 13) 과거 결함 조치 이력
write_csv("defect_history.csv",
    ["date", "registration", "defect", "resolution", "parts_scope", "tools_required", "downtime_hours"],
    [["2026-05-12", "HL7710", "IDG low oil pressure warning", "부품 교환", "패키지(어셈블리)", "IDG 인출 지그 JIG-IDG-01, 토크렌치", 6],
     ["2026-02-20", "HL7702", "IDG disconnect fault (intermittent)", "리셋/재시동", "교환 없음(리셋)", "BITE 테스터", 1],
     ["2026-06-01", "HL7710", "Fuel nozzle coking", "부품 교환", "단일 부품", "노즐 풀러 PULLER-07", 3],
     ["2026-03-15", "HL8259", "Hydraulic pump low pressure", "부품 교환", "패키지(어셈블리)", "유압 실링 키트, 토크렌치", 8],
     ["2026-05-05", "HL8260", "Cargo smoke detector false warning", "리셋/재시동", "교환 없음(리셋)", "표준 공구", 1],
     ["2026-06-18", "HL8081", "APU start fault", "디퍼(MEL) 후 부품 교환", "패키지(어셈블리)", "APU 호이스트 HOIST-APU-01", 30]])


# 이메일/인보이스 공식 양식(뼈대) — 실제 사내 양식으로 교체 가능. {중괄호}는 자동 치환 필드.
with open(os.path.join(TPL, "aog_support_request_en.txt"), "w", encoding="utf-8") as f:
    f.write(
        "SUBJECT: [AOG - URGENT] Spare part support request - {aircraft_type} / {part_number} / {airport}\n\n"
        "Dear Operations / Material Support Team,\n\n"
        "We are currently experiencing an AOG (Aircraft on Ground) situation on our {aircraft_type} "
        "aircraft at {airport}. We urgently require the following part and would greatly appreciate your support:\n\n"
        "  - Part Number: {part_number}\n  - Aircraft Type: {aircraft_type}\n  - Station: {airport}\n\n"
        "If you have this part available, please advise on loan availability and the minimum lead time "
        "at your earliest convenience.\n\nThank you for your urgent assistance.\n\n"
        "Best regards,\nMaterial Control Department\n")

with open(os.path.join(TPL, "aog_invoice_template.txt"), "w", encoding="utf-8") as f:
    f.write(
        "AOG SPARE PART SHIPPING INVOICE / DECLARATION\n"
        "--------------------------------------------------------\n"
        "AOG Ref      : AOG-{date}-{registration}\n"
        "Aircraft     : {registration} ({aircraft_type})  |  Operator: {operator}\n"
        "Part Number  : {part_number}    Qty: 1\n"
        "Reason       : Aircraft On Ground (AOG) - urgent spare, nil commercial value\n"
        "Consignee    : {handling_agent}\n"
        "Address      : {address}\n"
        "Destination  : {airport}\n"
        "Shipper      : Korean Air Material Control, ICN\n"
        "Customs      : AOG duty exemption requested. DECLARATION REQUIRED before handover.\n"
        "--------------------------------------------------------\n"
        "** 신고 누락 시 파송 지연 - 반드시 통관 신고 완료 후 조업사 인계 **\n")

print("templates written")
print("\n완료: data/raw/*.csv 및 templates/*.txt 생성됨")
