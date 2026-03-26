import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import json
import re
import requests

# 🚨 [보안 방어막]
if "connected" not in st.session_state or not st.session_state.connected:
    st.switch_page("app.py")

st.set_page_config(page_title="계약 보고 시스템", page_icon="📝", layout="wide")

KOREA_REGION_DATA = {
    "서울특별시": {
        "강남구": ["개포동", "논현동", "대치동", "도곡동", "삼성동", "세곡동", "수서동", "신사동", "압구정동", "역삼동", "율현동", "일원동", "자곡동", "청담동"],
        "강동구": ["강일동", "고덕동", "길동", "둔촌동", "명일동", "상일동", "성내동", "암사동", "천호동"],
        "송파구": ["가락동", "거여동", "마천동", "문정동", "방이동", "삼전동", "석촌동", "송파동", "신천동", "오금동", "잠실동", "장지동", "풍납동"],
    },
    "경기도": {"하남시": ["감일동", "위례동", "학암동"], "성남시": ["위례동", "창곡동"]},
}

def is_valid_date_format(date_str): return bool(re.match(r'^\d{4}\.\d{2}\.\d{2}$', str(date_str).strip()))
def normalize_dong(d_str):
    clean_d = str(d_str).strip().replace("동", "")
    return "" if clean_d in ["", "0", "없음", "동없음"] else clean_d

try: token_dict = json.loads(st.secrets["google_token_json"])
except: st.error("❌ 금고 설정 확인!"); st.stop()

@st.cache_resource
def get_ss(): return gspread.authorize(Credentials.from_authorized_user_info(token_dict)).open_by_key('121-C5OIQpOnTtDbgSLgiq_Qdf5WoHhhIpNkRCWy5hKA')
ss = get_ss()
ws_data = ss.get_worksheet_by_id(1969836502) 

try:
    ws_staff = ss.worksheet("직원명단")
    staff_records = ws_staff.get_all_records()
    staff_dict = {str(row['이메일']).strip(): row['이름'] for row in staff_records}
except: staff_dict = {}

try: ws_history = ss.worksheet("토큰내역")
except: pass

ADMIN_EMAIL = "dldmdcks94@gmail.com"
user_email = st.session_state.user_info.get("email", "")
user_name = "이응찬 대표" if user_email == ADMIN_EMAIL else staff_dict.get(user_email, "알수없는 직원")

try: ws_contract = ss.worksheet("계약보고_DB")
except: pass

# 💡 [업데이트] 토큰 부여 함수 추가
def update_token(t_name, amt, reason):
    if t_name in ["이응찬 대표", "곽태근 대표"]: return
    for i, r in enumerate(staff_records):
        if r['이름'] == t_name:
            ws_staff.update_cell(i + 2, 4, int(r.get('보유토큰', 0)) + amt)
            ws_history.append_row([(datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S'), t_name, amt, int(r.get('보유토큰', 0)) + amt, reason], value_input_option='USER_ENTERED')
            break

st.title("📝 엘루이 신규 계약 보고")
st.write("계약 내용을 입력하면 메인 DB와 정산 장부에 안전하게 저장됩니다.")

today_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y.%m.%d')

with st.form("contract_report_form", clear_on_submit=False):
    st.subheader("📌 계약 기본 정보")
    c_type1, c_type2 = st.columns([2, 1])
    deal_type = c_type1.radio("연결 구분 (양타 +5 / 단타 +3 토큰)", ["양타", "단타(임대측)", "단타(임차측)"], horizontal=True)
    # 💡 [업데이트] 매물 종류 선택 추가
    b_type_opts = ["오피스텔", "주택", "상가", "아파트", "다세대", "다가구", "빌라", "미분류"]
    b_type = c_type2.selectbox("매물 종류", b_type_opts, index=0)
    
    c_loc1, c_loc2, c_loc3 = st.columns(3)
    sido = c_loc1.selectbox("시/도", list(KOREA_REGION_DATA.keys()), index=0)
    gu_opts = list(KOREA_REGION_DATA[sido].keys()) if sido in KOREA_REGION_DATA else ["전체"]
    gu = c_loc2.selectbox("시/군/구", gu_opts, index=gu_opts.index("송파구") if "송파구" in gu_opts else 0)
    dong_opts = KOREA_REGION_DATA[sido][gu] if gu in KOREA_REGION_DATA[sido] else ["직접입력"]
    dong = c_loc3.selectbox("법정동", dong_opts + ["➕직접 입력"], index=dong_opts.index("방이동") if "방이동" in dong_opts else 0)
    if dong == "➕직접 입력": dong = st.text_input("법정동 직접 입력")

    c_loc4, c_loc5, c_loc6 = st.columns([2, 1, 2])
    bunji = c_loc4.text_input("번지 (예: 28-2)", placeholder="28-2")
    sub_dong = c_loc5.text_input("동 (없으면 빈칸)", placeholder="A동")
    room = c_loc6.text_input("호수 (숫자만)", placeholder="205")

    c_mon1, c_mon2 = st.columns(2)
    deposit = c_mon1.text_input("보증금 (원 단위 숫자만)", placeholder="10000000")
    rent = c_mon2.text_input("월세 (원 단위 숫자만, 없으면 0)", placeholder="1000000")
    
    c_date1, c_date2, c_date3 = st.columns(3)
    contract_date = c_date1.text_input("✍️ 계약일", value=today_str, disabled=True)
    move_in = c_date2.text_input("🗓️ 잔금일(입주일)", placeholder="2026.04.10")
    move_out = c_date3.text_input("🗓️ 만기일", placeholder="2028.04.09")
    
    c_info1, c_info2, c_info3 = st.columns(3)
    st.caption("※ 단타(임차측)을 선택하시면 임대인 연락처는 회사 번호(02-421-4988)로 자동 처리됩니다.")
    landlord_name = c_info1.text_input("임대인 성함", placeholder="이응찬")
    landlord_birth = c_info2.text_input("임대인 생년월일(6자리)", placeholder="941022")
    landlord_phone = c_info3.text_input("임대인 연락처(숫자만)", placeholder="01012345678")
    memo = st.text_area("📋 비고 및 특별사항", placeholder="임차측 단타 시 임대측 부동산 기재 (당사 공동중개 시 생략 무방)")
    
    submitted = st.form_submit_button("🚀 계약 결재 올리기", type="primary", use_container_width=True)
    
    if submitted:
        if not deposit.isdigit() or not rent.isdigit(): st.error("🚨 보증금과 월세는 숫자만!")
        elif deposit != "0" and not deposit.endswith("0000"): st.error("🚨 보증금 끝자리 0000 확인!")
        elif not is_valid_date_format(move_in) or not is_valid_date_format(move_out): st.error("🚨 날짜는 YYYY.MM.DD 포맷!")
        elif not bunji or not room: st.error("🚨 필수 항목 누락!")
        elif deal_type != "단타(임차측)" and (not landlord_name or any(char.isdigit() for char in landlord_name)): st.error("🚨 임대인 성함 누락 또는 숫자 포함!")
        else:
            bon, bu = bunji.split("-", 1) if "-" in bunji else (bunji, "0")
            d_dong = "동없음" if not sub_dong else (f"{sub_dong}동" if not sub_dong.endswith("동") else sub_dong)
            r_ho = f"{room}호" if not room.endswith("호") else room
            now_kst = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
            
            if deal_type == "단타(임차측)": final_name, final_birth, final_phone = "공동중개", "''", "'02-421-4988"
            else: final_name, final_birth, final_phone = landlord_name, f"'{landlord_birth}", f"'{landlord_phone}"
            
            # 💡 [업데이트] 매물종류(b_type)가 배열의 마지막(26번 인덱스, AA열)에 들어갑니다!
            def create_report_row(specific_type):
                return [now_kst, user_name, specific_type, sido, gu, dong, bon, bu, d_dong, r_ho, deposit, rent, move_in, move_out, contract_date, final_name, final_birth, final_phone, memo, "", "", "", "", "", "", "", b_type] 
            
            if deal_type == "양타":
                ws_contract.append_row(create_report_row("양타(임대측)"), value_input_option='USER_ENTERED')
                ws_contract.append_row(create_report_row("양타(임차측)"), value_input_option='USER_ENTERED')
            else: ws_contract.append_row(create_report_row(deal_type), value_input_option='USER_ENTERED')
            
            try:
                main_records = ws_data.get_all_values()
                updated = False
                in_dong, in_room, in_bunji = normalize_dong(d_dong), re.sub(r'[^0-9]', '', room), f"{bon}-{bu}" if bu and bu != "0" else bon
                
                for i, row in enumerate(main_records):
                    if i == 0: continue
                    r_dong, r_bon, r_bu, r_ddong, r_room = (str(row[2]).strip() if len(row)>2 else ""), (str(row[3]).strip() if len(row)>3 else ""), (str(row[4]).strip() if len(row)>4 else ""), (str(row[7]).strip() if len(row)>7 else ""), (str(row[8]).strip() if len(row)>8 else "")
                    r_full_bunji = f"{r_bon}-{r_bu}" if r_bu and r_bu != "0" else r_bon
                    
                    if r_dong == dong and r_full_bunji == in_bunji and normalize_dong(r_ddong) == in_dong and re.sub(r'[^0-9]', '', r_room) == in_room:
                        u_idx = i + 1
                        ws_data.update_cell(u_idx, 13, b_type); ws_data.update_cell(u_idx, 19, deposit); ws_data.update_cell(u_idx, 20, rent); ws_data.update_cell(u_idx, 22, move_out) 
                        old_m = str(row[22]) if len(row) > 22 else ""
                        ws_data.update_cell(u_idx, 23, f"{old_m}\n🏅[엘루이 자체계약] 👉 [{today_str}] 📝계약완료 (보/월 {deposit}/{rent}, 만기 {move_out})\n{memo}".strip())
                        ws_data.update_cell(u_idx, 24, now_kst); ws_data.update_cell(u_idx, 25, user_name)     
                        
                        if deal_type in ["양타", "단타(임대측)"]:
                            ws_data.update_cell(u_idx, 10, final_name)
                            ws_data.update_cell(u_idx, 11, final_birth)
                            ws_data.update_cell(u_idx, 12, final_phone)
                        updated = True; break 
                        
                if not updated:
                    t_row = len(ws_data.col_values(3)) + 1  
                    new_r = [""] * 26
                    new_r[0], new_r[1], new_r[2], new_r[3], new_r[4], new_r[7], new_r[8] = sido, gu, dong, bon, bu, d_dong, r_ho
                    new_r[9], new_r[10], new_r[11], new_r[12], new_r[14] = final_name, final_birth, final_phone, b_type, "위반 없음"
                    new_r[18], new_r[19], new_r[21], new_r[23], new_r[24], new_r[25] = deposit, rent, move_out, now_kst, user_name, "정상"
                    new_r[22] = f"🏅[엘루이 자체계약] 👉 [{today_str}] 📝신규계약 (보/월 {deposit}/{rent}, 만기 {move_out})\n{memo}"
                    c_list = ws_data.range(t_row, 1, t_row, 26)
                    for j, v in enumerate(new_r): c_list[j].value = v
                    ws_data.update_cells(c_list, value_input_option='USER_ENTERED')
            except: pass

            # 💡 [업데이트] 토큰 지급 및 심플한 성공 메시지
            reward = 5 if deal_type == "양타" else 3
            update_token(user_name, reward, f"계약 보고 ({deal_type})")
            st.success(f"✨ 데이터센터 저장 및 업데이트 완료 (토큰 +{reward}개 지급)")

            try:
                msg_text = f"""[📝 신규 계약보고] {deal_type}
담당자 : {user_name}
주소 : {sido} {gu} {dong} {bunji}번지{' '+sub_dong+'동' if sub_dong else ''} {r_ho}
종류 : {b_type}
보증금 : {int(deposit):,}원
월세 : {int(rent):,}원
잔금일 : {move_in}
만기일 : {move_out}
특이사항 : {memo}"""
                res = requests.post("https://kakaowork.com/bots/hook/4a5be71f2c424dfa8a6926ddfbd75ebe", json={"text": msg_text})
                if res.status_code == 200: st.balloons()
                else: st.error(f"⚠️ 앗! 카카오워크 전송에 실패했습니다. (코드: {res.status_code}) 내용: {res.text}")
            except Exception as e: st.error(f"⚠️ 카카오워크 서버와 통신 에러가 발생했습니다: {e}")
