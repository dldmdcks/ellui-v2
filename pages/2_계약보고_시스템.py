import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
import json
import requests
import re
import pandas as pd
import math
from datetime import datetime, timedelta

# 🚨 [보안] 로그인 확인
if "connected" not in st.session_state or not st.session_state.connected:
    st.switch_page("app.py")

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="계약보고 및 정산", page_icon="💰", layout="wide")
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-size: 14px !important; }
        .stButton>button { padding: 0.2rem 0.5rem; min-height: 2rem; }
        .block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
        [data-testid="stSidebarNav"] { display: none !important; } /* 회색 메뉴판 강제 숨김 */
        div[role="radiogroup"] { flex-direction: row; gap: 15px; padding-bottom: 15px; border-bottom: 2px solid #f0f2f6; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

ADMIN_EMAILS = ["dldmdcks94@gmail.com", "ktg3582@gmail.com"]

KOREA_REGION_DATA = {
    "서울특별시": {"강남구": ["개포동", "논현동", "대치동", "도곡동", "삼성동", "세곡동", "수서동", "신사동", "압구정동", "역삼동", "율현동", "일원동", "자곡동", "청담동"], "강동구": ["강일동", "고덕동", "길동", "둔촌동", "명일동", "상일동", "성내동", "암사동", "천호동"], "송파구": ["가락동", "거여동", "마천동", "문정동", "방이동", "삼전동", "석촌동", "송파동", "신천동", "오금동", "잠실동", "장지동", "풍납동"], "서초구": ["내곡동", "반포동", "방배동", "서초동", "신원동", "양재동", "염곡동", "우면동", "원지동", "잠원동"], "강서구": ["가양동", "개화동", "공항동", "과해동", "내발산동", "등촌동", "마곡동", "방화동", "염창동", "오곡동", "오쇠동", "외발산동", "화곡동"], "관악구": ["남현동", "봉천동", "신림동"], "광진구": ["광장동", "구의동", "군자동", "능동", "자양동", "중곡동", "화양동"], "동대문구": ["답십리동", "신설동", "용두동", "이문동", "장안동", "전농동", "제기동", "청량리동", "회기동", "휘경동"], "마포구": ["공덕동", "구수동", "노고산동", "당인동", "대흥동", "도화동", "마포동", "망원동", "상수동", "상암동", "서교동", "성산동", "신공덕동", "신수동", "신정동", "아현동", "연남동", "염리동", "용강동", "중동", "창전동", "토정동", "하중동", "합정동", "현석동"], "성동구": ["금호동1가", "금호동2가", "금호동3가", "금호동4가", "도선동", "마장동", "사근동", "상왕십리동", "성수동1가", "성수동2가", "송정동", "옥수동", "용답동", "응봉동", "하왕십리동", "행당동", "홍익동"], "용산구": ["갈월동", "남영동", "도원동", "동빙고동", "동자동", "문배동", "보광동", "산천동", "서계동", "서빙고동", "신계동", "신창동", "용문동", "용산동1가", "용산동2가", "용산동3가", "용산동4가", "용산동5가", "용산동6가", "원효로1가", "원효로2가", "원효로3가", "원효로4가", "이촌동", "이태원동", "주성동", "청파동1가", "청파동2가", "청파동3가", "한강로1가", "한강로2가", "한강로3가", "한남동", "효창동", "후암동"], "영등포구": ["당산동", "당산동1가", "당산동2가", "당산동3가", "당산동4가", "당산동5가", "당산동6가", "대림동", "도림동", "문래동1가", "문래동2가", "문래동3가", "문래동4가", "문래동5가", "문래동6가", "신길동", "양평동", "양평동1가", "양평동2가", "양평동3가", "양평동4가", "양평동5가", "양평동6가", "양화동", "여의도동", "영등포동", "영등포동1가", "영등포동2가", "영등포동3가", "영등포동4가", "영등포동5가", "영등포동6가", "영등포동7가", "영등포동8가"], "종로구": ["가회동", "견지동", "경운동", "공평동", "관수동", "관철동", "관훈동", "교남동", "교북동", "구기동", "궁정동", "권농동", "낙원동", "내수동", "내자동", "누상동", "누하동", "당주동", "도렴동", "돈의동", "동숭동", "명륜1가", "명륜2가", "명륜3가", "명륜4가", "묘동", "무악동", "봉익동", "부암동", "사직동", "삼청동", "서린동", "세종로", "소격동", "송월동", "송현동", "수송동", "숭인동", "신교동", "신문로1가", "신문로2가", "신영동", "안국동", "연건동", "연지동", "예지동", "옥인동", "와룡동", "운니동", "원남동", "원서동", "이화동", "익선동", "인사동", "인의동", "장사동", "재동", "적선동", "종로1가", "종로2가", "종로3가", "종로4가", "종로5가", "종로6가", "중학동", "창성동", "창신동", "청운동", "청진동", "체부동", "충신동", "통의동", "통인동", "팔판동", "평동", "평창동", "필운동", "행촌동", "혜화동", "홍지동", "홍파동", "화동", "효자동", "효제동", "훈정동"], "중구": ["광희동1가", "광희동2가", "남대문로1가", "남대문로2가", "남대문로3가", "남대문로4가", "남대문로5가", "남산동1가", "남산동2가", "남산동3가", "남창동", "남학동", "다동", "만리동1가", "만리동2가", "명동1가", "명동2가", "무교동", "무학동", "묵정동", "방산동", "봉래동1가", "봉래동2가", "북창동", "산림동", "삼각동", "서소문동", "소공동", "수표동", "수하동", "순화동", "신당동", "쌍림동", "예관동", "예장동", "오장동", "을지로1가", "을지로2가", "을지로3가", "을지로4가", "을지로5가", "을지로6가", "을지로7가", "인현동1가", "인현동2가", "입정동", "장교동", "장충동1가", "장충동2가", "저동1가", "저동2가", "정동", "주교동", "주자동", "중림동", "초동", "충무로1가", "충무로2가", "충무로3가", "충무로4가", "충무로5가", "태평로1가", "태평로2가", "필동1가", "필동2가", "필동3가", "황학동", "회현동1가", "회현동2가", "회현동3가", "흥인동"]},
    "경기도": {"하남시": ["감북동", "감이동", "감일동", "광암동", "교산동", "덕풍동", "망월동", "미사동", "배알미동", "상사창동", "상산곡동", "선동", "신장동", "창우동", "천현동", "초이동", "초일동", "춘궁동", "풍산동", "하사창동", "하산곡동", "학암동", "항동"], "성남시 수정구": ["고등동", "금토동", "단대동", "둔전동", "복정동", "사송동", "산성동", "상적동", "수진동", "시흥동", "신촌동", "신흥동", "양지동", "오야동", "창곡동", "태평동"], "성남시 분당구": ["구미동", "궁내동", "금곡동", "대장동", "동원동", "백현동", "분당동", "삼평동", "서현동", "석운동", "수내동", "야탑동", "운중동", "율동", "이매동", "정자동", "판교동", "하산운동"], "수원시 팔달구": ["고등동", "교동", "구천동", "남수동", "남창동", "매교동", "매산로1가", "매산로2가", "매산로3가", "매향동", "북수동", "신풍동", "영동", "우만동", "인계동", "장안동", "중동", "지동", "팔달로1가", "팔달로2가", "팔달로3가", "화서동"]},
    "인천광역시": {"연수구": ["동춘동", "선학동", "송도동", "연수동", "옥련동", "청학동"], "부평구": ["갈산동", "구산동", "부개동", "부평동", "산곡동", "삼산동", "십정동", "일신동", "청천동"]}
}

# 2. 구글 시트 연동
token_dict = json.loads(st.secrets["google_token_json"])
@st.cache_resource
def get_ss(): return gspread.authorize(Credentials.from_authorized_user_info(token_dict)).open_by_key('121-C5OIQpOnTtDbgSLgiq_Qdf5WoHhhIpNkRCWy5hKA')
ss = get_ss()

ws_data = ss.get_worksheet_by_id(1969836502)
try: ws_staff = ss.worksheet("직원명단")
except: pass
try: ws_contract = ss.worksheet("계약보고_DB")
except: pass
try: ws_history = ss.worksheet("토큰내역")
except: pass

@st.cache_data(ttl=30)
def fetch_contract_data(): return ws_data.get_all_values(), ws_staff.get_all_records(), ws_contract.get_all_values()
all_data_raw, staff_records, contract_all_values = fetch_contract_data()

staff_dict = {str(r['이메일']).strip(): r for r in staff_records}
user_email = st.session_state.user_info.get("email", "")

now_kst = datetime.utcnow() + timedelta(hours=9)
today_shift = now_kst.strftime("%Y-%m-%d") if now_kst.hour >= 8 else (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")

if user_email in staff_dict:
    user_name = staff_dict[user_email]['이름'] 
    user_tokens = int(staff_dict[user_email].get('보유토큰', 0))
    my_ratio = int(staff_dict[user_email].get('수수료비율', 60)) if str(staff_dict[user_email].get('수수료비율', '')).isdigit() else 60
elif user_email in ADMIN_EMAILS:
    user_name = "이응찬 대표" if user_email == "dldmdcks94@gmail.com" else "곽태근 대표"
    user_tokens, my_ratio = 9999, 100
else: st.error("승인되지 않은 계정입니다."); st.stop()

contract_records = contract_all_values[1:]

def is_valid_date_format(date_str): return bool(re.match(r'^\d{4}\.\d{2}\.\d{2}$', str(date_str).strip()))
def update_token(t_name, amt, reason):
    if "대표" in t_name or "관리자" in t_name: return
    for i, r in enumerate(staff_records):
        if r['이름'] == t_name:
            ws_staff.update_cell(i + 2, 4, int(r.get('보유토큰', 0)) + amt)
            ws_history.append_row([(datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S'), t_name, amt, int(r.get('보유토큰', 0)) + amt, reason], value_input_option='USER_ENTERED')
            break

# --- 🧭 사이드바 ---
st.sidebar.markdown(f"### 👤 {user_name}")
st.sidebar.markdown(f"**보유 토큰:** `{user_tokens} 개`")
if st.sidebar.button("로그아웃"): st.query_params.clear(); st.session_state.clear(); st.switch_page("app.py")
st.sidebar.write("---")

st.sidebar.markdown("### 🧭 메뉴 이동")
st.sidebar.page_link("app.py", label="홈", icon="🏠")
st.sidebar.page_link("pages/1_오피콜_및_매물관리.py", label="매물관리", icon="🔍")
st.sidebar.page_link("pages/2_계약보고_시스템.py", label="계약", icon="💰")
st.sidebar.page_link("pages/3_팀장회의.py", label="회의록", icon="🤝") # 👈 이거 추가!
st.sidebar.write("---")

# --- 상단 라디오 탭 ---
tab_names = ["✅ 계약 컨펌 요청", "✍️ 신규 계약 보고", "💰 내 정산"]
if user_email in ADMIN_EMAILS: tab_names.append("👑 전사 대시보드")
selected_tab = st.radio("메뉴", tab_names, horizontal=True, label_visibility="collapsed")

# ==========================================
# 탭 1: 계약 컨펌 요청 (입금 전 승인)
# ==========================================
if selected_tab == "✅ 계약 컨펌 요청":
    st.title("✅ 계약 컨펌 요청 (입금 전 사전 승인)")
    st.write("아래 양식을 채워 컨펌을 요청하면 카카오워크 단톡방으로 즉시 전송됩니다.")
    
    # 💡 [업데이트] 직관적인 2지선다 라디오 버튼으로 용도 선택
    registry_type = st.radio("📌 매물 등기 종류 선택", ["구분등기 (다세대/오피스텔/아파트 등)", "다가구/단독주택"], horizontal=True)

    with st.form("confirm_request_form", clear_on_submit=False):
        st.subheader("🏠 매물 정보")
        c_loc1, c_loc2, c_loc3 = st.columns(3)
        cr_sido = c_loc1.selectbox("시/도", list(KOREA_REGION_DATA.keys()), index=list(KOREA_REGION_DATA.keys()).index("서울특별시") if "서울특별시" in KOREA_REGION_DATA else 0)
        cr_gu_opts = list(KOREA_REGION_DATA[cr_sido].keys())
        cr_gu = c_loc2.selectbox("시/군/구", cr_gu_opts, index=cr_gu_opts.index("송파구") if "송파구" in cr_gu_opts else 0)
        cr_dong_opts = KOREA_REGION_DATA[cr_sido][cr_gu] + ["➕직접 입력"]
        cr_dong_sel = c_loc3.selectbox("법정동", cr_dong_opts, index=cr_dong_opts.index("방이동") if "방이동" in cr_dong_opts else 0)
        if cr_dong_sel == "➕직접 입력": dong = st.text_input("법정동 직접 입력")
        else: dong = cr_dong_sel

        c_loc4, c_loc5, c_loc6 = st.columns([2, 1, 2])
        bunji = c_loc4.text_input("번지 (예: 28-2)", placeholder="28-2")
        sub_dong = c_loc5.text_input("동 (없으면 빈칸)", placeholder="A동")
        room = c_loc6.text_input("호수 (숫자만)", placeholder="205")

        c_m1, c_m2 = st.columns(2)
        deposit = c_m1.text_input("보증금 (0000 끝나는 원단위)", placeholder="10000000")
        rent = c_m2.text_input("월세 (원단위, 없으면 0)", placeholder="1000000")
        
        st.subheader("⚖️ 권리 분석 정보")
        c_r1, c_r2 = st.columns(2)
        priority_amount = c_r1.text_input("해당연도 최우선변제금액 (0000 원단위)", placeholder="55000000")
        loan_exist = c_r2.selectbox("대출 유무", ["무", "유"])
        
        # 💡 [업데이트] 다가구일 때만 나타나는 선순위 정보 입력칸
        senior_deposit = ""
        total_rooms = ""
        if registry_type == "다가구/단독주택":
            st.markdown("**🚨 [다가구 전용] 선순위 정보 입력**")
            c_d1, c_d2 = st.columns(2)
            senior_deposit = c_d1.text_input("선순위 총 보증금 (원단위)", placeholder="500000000")
            total_rooms = c_d2.text_input("총 호실 수 (숫자만)", placeholder="10")
            
        special_notes = st.text_area("📋 특이사항", placeholder="예: 미등기, 전입불가, 근저당 말소조건 등")
        
        submit_btn = st.form_submit_button("🚀 워크로 컨펌 요청 쏘기", type="primary", use_container_width=True)
        
        if submit_btn:
            if not deposit.isdigit() or not deposit.endswith("0000"): st.error("🚨 보증금은 숫자로, 끝자리가 0000이어야 합니다.")
            elif not priority_amount.isdigit() or not priority_amount.endswith("0000"): st.error("🚨 최우선변제금액은 숫자로, 끝자리가 0000이어야 합니다.")
            elif not bunji: st.error("🚨 필수 항목(번지)을 입력해주세요.")
            elif registry_type == "다가구/단독주택" and (not senior_deposit.isdigit() or not total_rooms.isdigit()): st.error("🚨 다가구 주택은 선순위 총 보증금과 총 호실 수를 숫자로 정확히 입력해야 합니다.")
            else:
                addr_full = f"{cr_sido} {cr_gu} {dong} {bunji}{'-'+sub_dong if sub_dong else ''} {room}호".strip()
                
                # 워크 메시지 포맷 (임대인/임차인 이름 제외)
                msg = f"[🔴 계약 컨펌 요청]\n"
                msg += f"담당자 : {user_name}\n"
                msg += f"주소 : {addr_full} [{registry_type.split(' ')[0]}]\n"
                msg += f"보/월 : {int(deposit):,}원 / {int(rent) if rent.isdigit() else 0:,}원\n"
                msg += f"최우선변제금 : {int(priority_amount):,}원\n"
                msg += f"대출유무 : {loan_exist}\n"
                
                if registry_type == "다가구/단독주택":
                    msg += f"선순위 총보증금 : {int(senior_deposit):,}원 (총 {total_rooms}호실)\n"
                    
                msg += f"특이사항 : {special_notes}\n"
                msg += f"\n📢 (확인 후 등기/건축물대장을 톡방에 첨부해주세요!)"
                
                try:
                    res = requests.post("https://kakaowork.com/bots/hook/4a5be71f2c424dfa8a6926ddfbd75ebe", json={"text": msg})
                    if res.status_code == 200:
                        st.success("✅ 카카오워크 단톡방으로 컨펌 요청이 전송되었습니다! 아래에 등기부등본을 톡방에 첨부해주세요.")
                        st.balloons()
                    else: st.error(f"⚠️ 전송 실패: {res.text}")
                except Exception as e: st.error(f"⚠️ 카카오워크 서버 통신 에러: {e}")
                    
    st.write("---")
    st.subheader("📖 참고: 지역별 최우선변제금액")
    try: st.image("최우선변제.jpg", use_container_width=True)
    except: st.warning("최우선변제.jpg 이미지를 깃허브(ellui-v2)에 업로드해주시면 여기에 표시됩니다.")

# ==========================================
# 탭 2: 신규 계약 보고
# ==========================================
elif selected_tab == "✍️ 신규 계약 보고":
    st.title("📝 엘루이 신규 계약 보고")
    st.write("계약 내용을 입력하시면 메인 DB와 정산 장부에 안전하게 자동 저장됩니다.")
    
    with st.form("contract_report_form", clear_on_submit=False):
        st.subheader("📌 계약 기본 정보")
        c_type1, c_type2 = st.columns([2, 1])
        deal_type = c_type1.radio("연결 구분 (양타 +5 / 단타 +3 토큰)", ["양타", "단타(임대측)", "단타(임차측)"], horizontal=True)
        b_type = c_type2.selectbox("매물 종류", ["오피스텔", "주택", "상가", "아파트", "다세대", "다가구", "빌라", "미분류"], index=0)
        
        c_loc1, c_loc2, c_loc3 = st.columns(3)
        cr_sido = c_loc1.selectbox("시/도", list(KOREA_REGION_DATA.keys()), index=list(KOREA_REGION_DATA.keys()).index("서울특별시") if "서울특별시" in KOREA_REGION_DATA else 0)
        cr_gu_opts = list(KOREA_REGION_DATA[cr_sido].keys())
        cr_gu = c_loc2.selectbox("시/군/구", cr_gu_opts, index=cr_gu_opts.index("송파구") if "송파구" in cr_gu_opts else 0)
        cr_dong_opts = KOREA_REGION_DATA[cr_sido][cr_gu] + ["➕직접 입력"]
        cr_dong_sel = c_loc3.selectbox("법정동", cr_dong_opts, index=cr_dong_opts.index("방이동") if "방이동" in cr_dong_opts else 0)
        if cr_dong_sel == "➕직접 입력": dong = st.text_input("법정동 직접 입력")
        else: dong = cr_dong_sel

        c_loc4, c_loc5, c_loc6 = st.columns([2, 1, 2])
        bunji = c_loc4.text_input("번지 (예: 28-2)", placeholder="28-2")
        sub_dong = c_loc5.text_input("동 (없으면 빈칸)", placeholder="A동")
        room = c_loc6.text_input("호수 (숫자만)", placeholder="205")

        c_mon1, c_mon2 = st.columns(2)
        deposit = c_mon1.text_input("보증금 (원 단위 숫자만)", placeholder="10000000")
        rent = c_mon2.text_input("월세 (원 단위 숫자만, 없으면 0)", placeholder="1000000")
        
        c_date1, c_date2, c_date3 = st.columns(3)
        contract_date = c_date1.text_input("✍️ 계약일", value=today_shift, disabled=True)
        move_in = c_date2.text_input("🗓️ 잔금일(입주일)", placeholder="2026.04.10")
        move_out = c_date3.text_input("🗓️ 만기일", placeholder="2028.04.09")
        
        c_info1, c_info2, c_info3 = st.columns(3)
        st.caption("※ 단타(임차측)을 선택하시면 임대인 연락처는 회사 번호(02-421-4988)로 자동 처리됩니다.")
        landlord_name = c_info1.text_input("임대인 성함", placeholder="이응찬")
        landlord_birth = c_info2.text_input("임대인 생년월일(6자리)", placeholder="941022")
        landlord_phone = c_info3.text_input("임대인 연락처(숫자만)", placeholder="01012345678")
        memo = st.text_area("📋 비고 및 특별사항", placeholder="임차측 단타 시 임대측 부동산 기재 (당사 공동중개 시 생략 무방)")
        
        if st.form_submit_button("🚀 계약 결재 올리기", type="primary", use_container_width=True):
            if not deposit.isdigit() or not rent.isdigit(): st.error("🚨 보증금과 월세는 숫자만 입력해주세요!")
            elif deposit != "0" and not deposit.endswith("0000"): st.error("🚨 보증금 끝자리를 확인해주세요! (예: 1000만 원 -> 10000000)")
            elif not is_valid_date_format(move_in) or not is_valid_date_format(move_out): st.error("🚨 날짜는 YYYY.MM.DD 포맷으로 입력해주세요!")
            elif not bunji or not room: st.error("🚨 필수 항목(번지, 호수)을 입력해주세요!")
            elif deal_type != "단타(임차측)" and (not landlord_name or any(char.isdigit() for char in landlord_name)): st.error("🚨 임대인 성함을 정확히 입력해주세요!")
            else:
                bon, bu = bunji.split("-", 1) if "-" in bunji else (bunji, "0")
                d_dong = "동없음" if not sub_dong else (f"{sub_dong}동" if not sub_dong.endswith("동") else sub_dong)
                r_ho = f"{room}호" if not room.endswith("호") else room
                now_kst_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
                
                if deal_type == "단타(임차측)": final_name, final_birth, final_phone = "공동중개", "''", "'02-421-4988"
                else: final_name, final_birth, final_phone = landlord_name, f"'{landlord_birth}", f"'{landlord_phone}"
                
                def create_report_row(specific_type): return [now_kst_str, user_name, specific_type, cr_sido, cr_gu, dong, bon, bu, d_dong, r_ho, deposit, rent, move_in, move_out, contract_date, final_name, final_birth, final_phone, memo, "", "", "", "", "", "", "", b_type] 
                
                if deal_type == "양타":
                    ws_contract.append_row(create_report_row("양타(임대측)"), value_input_option='USER_ENTERED')
                    ws_contract.append_row(create_report_row("양타(임차측)"), value_input_option='USER_ENTERED')
                else: ws_contract.append_row(create_report_row(deal_type), value_input_option='USER_ENTERED')
                
                try:
                    updated = False
                    in_dong, in_room, in_bunji = str(dong).strip(), re.sub(r'[^0-9]', '', room), f"{bon}-{bu}" if bu and bu != "0" else bon
                    for i, r_row in enumerate(all_data_raw):
                        if i == 0: continue
                        r_dong, r_bon, r_bu, r_ddong, r_room = (str(r_row[2]).strip() if len(r_row)>2 else ""), (str(r_row[3]).strip() if len(r_row)>3 else ""), (str(r_row[4]).strip() if len(r_row)>4 else ""), (str(r_row[7]).strip() if len(r_row)>7 else ""), (str(r_row[8]).strip() if len(r_row)>8 else "")
                        r_full_bunji = f"{r_bon}-{r_bu}" if r_bu and r_bu != "0" else r_bon
                        
                        if r_dong == in_dong and r_full_bunji == in_bunji and str(r_ddong).replace("동","") == str(d_dong).replace("동","") and re.sub(r'[^0-9]', '', r_room) == in_room:
                            u_idx = i + 1
                            ws_data.update_cell(u_idx, 13, b_type); ws_data.update_cell(u_idx, 19, deposit); ws_data.update_cell(u_idx, 20, rent); ws_data.update_cell(u_idx, 22, move_out) 
                            old_m = str(r_row[22]) if len(r_row) > 22 else ""
                            ws_data.update_cell(u_idx, 23, f"{old_m}\n🏅[엘루이 자체계약] 👉 [{today_shift}] 📝계약완료 (보/월 {deposit}/{rent}, 만기 {move_out})\n{memo}".strip())
                            ws_data.update_cell(u_idx, 24, now_kst_str); ws_data.update_cell(u_idx, 25, user_name)     
                            if deal_type in ["양타", "단타(임대측)"]:
                                ws_data.update_cell(u_idx, 10, final_name); ws_data.update_cell(u_idx, 11, final_birth); ws_data.update_cell(u_idx, 12, final_phone)
                            updated = True; break 
                            
                    if not updated:
                        new_r = [""] * 26
                        new_r[0], new_r[1], new_r[2], new_r[3], new_r[4], new_r[7], new_r[8] = cr_sido, cr_gu, dong, bon, bu, d_dong, r_ho
                        new_r[9], new_r[10], new_r[11], new_r[12], new_r[14] = final_name, final_birth, final_phone, b_type, "위반 없음"
                        new_r[18], new_r[19], new_r[21], new_r[23], new_r[24], new_r[25] = deposit, rent, move_out, now_kst_str, user_name, "정상"
                        new_r[22] = f"🏅[엘루이 자체계약] 👉 [{today_shift}] 📝신규계약 (보/월 {deposit}/{rent}, 만기 {move_out})\n{memo}"
                        ws_data.append_row(new_r, value_input_option='USER_ENTERED')
                except: pass

                reward = 5 if deal_type == "양타" else 3
                update_token(user_name, reward, f"계약 보고 ({deal_type})")
                st.success(f"✨ 데이터센터 저장 및 업데이트 완료 (토큰 +{reward}개 지급)")

                try:
                    msg_text = f"[📝 신규 계약보고] {deal_type}\n담당자 : {user_name}\n주소 : {cr_sido} {cr_gu} {dong} {bunji}번지{' '+sub_dong+'동' if sub_dong else ''} {r_ho}\n종류 : {b_type}\n보증금 : {int(deposit):,}원\n월세 : {int(rent):,}원\n잔금일 : {move_in}\n만기일 : {move_out}\n특이사항 : {memo}"
                    res = requests.post("https://kakaowork.com/bots/hook/4a5be71f2c424dfa8a6926ddfbd75ebe", json={"text": msg_text})
                    if res.status_code == 200: st.balloons()
                except Exception as e: st.error(f"⚠️ 카카오워크 전송 에러: {e}")

# ==========================================
# 탭 3: 내 정산
# ==========================================
elif selected_tab == "💰 내 정산":
    st.subheader(f"💰 {user_name}님의 계약 및 정산 관리")
    my_contracts = [r for r in contract_records if len(r) > 1 and r[1] == user_name]
    my_contracts.reverse() 
    
    expected_salary = 0
    for row in my_contracts:
        rp = (row + [""]*27)[:27]
        if rp[23] != "O":
            fee_val = int(re.sub(r'[^0-9]', '', str(rp[19]))) if re.sub(r'[^0-9]', '', str(rp[19])) else 0
            pmethod = str(rp[20]).strip()
            if fee_val > 0:
                if pmethod == "현금" and fee_val < 100000: expected_salary += int(fee_val * (my_ratio / 100))
                else: expected_salary += (int(round(fee_val / 1.1) * (my_ratio / 100)) - math.ceil(int(round(fee_val / 1.1) * (my_ratio / 100)) * 0.033))

    if st.toggle("👁️ 이번 달 예상 급여"): st.success(f"이번 달 예상 실수령액: **{expected_salary:,}원** (현재 정산 대기 중인 금액의 총합입니다)")
    hide_completed_my = st.checkbox("☑️ 내 급여 지급 완료(🔴)된 내역 숨기기", value=True)
    st.write("---")
    
    if not my_contracts: st.info("아직 보고하신 계약건이 없습니다.")
    else:
        for idx, row in enumerate(my_contracts):
            rp = (row + [""]*27)[:27] 
            c_date, d_type = str(rp[0])[:10], str(rp[2])
            c_dong, c_bon, c_bu, c_room = str(rp[5]), str(rp[6]), str(rp[7]), str(rp[9])
            c_addr = f"{c_dong} {c_bon}-{c_bu} {c_room}"
            
            fee_str = str(rp[19]).replace(",","").replace("원","").strip()
            fee_val = int(fee_str) if fee_str.isdigit() else 0
            pay_method, depositor_name = str(rp[20]).strip(), str(rp[25]).strip()
            
            comp_in, emp_out = "🟡 입금완료" if str(rp[22]) == "O" else "⚪ 미입금", "🔴 급여완료" if str(rp[23]) == "O" else "⚪ 미정산"
            is_locked_data = (str(rp[22]) == "O") 
            
            if hide_completed_my and str(rp[23]) == "O": continue
            contact_tag = " 🚨[수배중]" if str(rp[17]) == "'02-421-4988" else ""
            fee_display = f"{fee_val:,}원" if fee_val > 0 else "미입력"
            exp_key = f"exp_mycalc_{idx}"
            
            with st.expander(f"{c_date} 📍 {c_addr} [{d_type}]{contact_tag} | 💰 보: {rp[10]} / 월: {rp[11]} / 입금액: {fee_display} | {comp_in}/{emp_out}", expanded=st.session_state.get(exp_key, False)):
                if is_locked_data: st.warning("🔒 대표님 입금 확인 완료 (금액 및 입금자 수정 불가)")
                
                with st.form(f"fee_form_{idx}"):
                    c_f1, c_f2, c_f3 = st.columns(3)
                    new_fee = c_f1.text_input("총 수수료 입력(숫자만)", value=fee_str, disabled=is_locked_data)
                    new_method = c_f2.selectbox("결제 수단", ["계좌이체", "현금"], index=0 if pay_method!="현금" else 1, disabled=is_locked_data)
                    new_depositor = c_f3.text_input("입금자명", value=depositor_name, disabled=is_locked_data)
                    
                    new_real_phone = st.text_input("🚨 임대인 실제 연락처 (공동중개 확인 후 업데이트)") if str(rp[17]) == "'02-421-4988" else ""
                    new_note = st.text_input("정산 특이사항", value=str(rp[24]))
                    
                    if st.form_submit_button("💾 금액/수단 저장", disabled=is_locked_data):
                        t_idx = len(contract_all_values) - idx 
                        ws_contract.update_cell(t_idx, 20, new_fee); ws_contract.update_cell(t_idx, 21, new_method); ws_contract.update_cell(t_idx, 25, new_note); ws_contract.update_cell(t_idx, 26, new_depositor)
                        if new_real_phone: ws_contract.update_cell(t_idx, 18, f"'{new_real_phone}")
                        st.session_state[exp_key] = True 
                        st.cache_data.clear(); st.rerun()
                
                if "요청완료" in str(rp[21]) or "발급완료" in str(rp[21]): st.success(f"✅ {rp[21]} 건입니다.")
                else:
                    st.write("---")
                    st.markdown("#### 🧾 증빙 자동 요청 (카카오워크 전송)")
                    with st.form(f"req_form_{idx}", clear_on_submit=True):
                        req_type = st.radio("발급 종류", ["세금계산서", "지출증빙", "현금영수증"], horizontal=True)
                        r_c1, r_c2 = st.columns(2)
                        biz_name = r_c1.text_input("상호명 (현금영수증은 '이름' 입력)")
                        biz_ceo = r_c2.text_input("대표자 성함 (현금영수증은 비워두세요)")
                        biz_num = r_c1.text_input("사업자번호 (현금영수증은 '폰번호' 입력)")
                        biz_email = r_c2.text_input("이메일 (예: 필요없음)")
                        
                        if st.form_submit_button("🚀 대표님께 카톡 요청 쏘기"):
                            if req_type in ["세금계산서", "지출증빙"]:
                                msg = f"💌 [{req_type} 발행 요청]\n담당자 : {user_name}\n주소 : {c_addr} [{d_type}]\n금액 : {int(new_fee):,}원\n\n[🏢 사업자 정보]\n- 상호명 : {biz_name}\n- 대표자 : {biz_ceo}\n- 등록번호 : {biz_num}\n- 이메일 : {biz_email}"
                            else:
                                msg = f"💌 [현금영수증 발행 요청]\n담당자 : {user_name}\n주소 : {c_addr} [{d_type}]\n금액 : {int(new_fee):,}원\n\n[👤 발급 정보]\n- 이름 : {biz_name}\n- 번호 : {biz_num}"
                            try:
                                res = requests.post("https://kakaowork.com/bots/hook/4a5be71f2c424dfa8a6926ddfbd75ebe", json={"text": msg})
                                if res.status_code == 200:
                                    ws_contract.update_cell(len(contract_all_values) - idx, 22, f"{req_type} 요청완료") 
                                    st.session_state[exp_key] = True
                                    st.cache_data.clear(); st.rerun()
                            except Exception as e: st.error(f"⚠️ 카카오워크 전송 에러: {e}")

# ==========================================
# 탭 4: 전사 대시보드 (관리자용)
# ==========================================
elif selected_tab == "👑 전사 대시보드":
    st.subheader("👑 엘루이 전사 정산 및 매출 대시보드")
    hide_completed = st.checkbox("☑️ 급여 지급 완료(🔴)된 내역 숨기기", value=True)
    
    calc_data = []
    for i, row in enumerate(contract_records):
        if len(row) < 19: continue
        rp = (row + [""]*27)[:27] 
        if hide_completed and str(rp[23]) == "O": continue
        
        fee = int(str(rp[19]).replace(",","").replace("원","").strip()) if str(rp[19]).replace(",","").replace("원","").strip().isdigit() else 0
        pmethod = str(rp[20])
        s_ratio = int(staff_dict[str(rp[1])].get('수수료비율', 60)) if str(rp[1]) in staff_dict else 60
        
        if fee > 0:
            if pmethod == "현금" and fee < 100000:
                net_fee, vat, tax_33 = fee, 0, 0
                final_pay = int(fee * (s_ratio/100))
                comp_profit = fee - final_pay
            else:
                net_fee = int(round(fee/1.1))
                vat = fee - net_fee
                share = int(net_fee * (s_ratio/100))
                tax_33 = math.ceil(share * 0.033) 
                final_pay = share - tax_33
                comp_profit = net_fee - share
        else: final_pay, comp_profit, vat, tax_33 = 0, 0, 0, 0
            
        b_type_str = str(rp[26]) if str(rp[26]) else "미입력"
        deposit_str = f"{int(re.sub(r'[^0-9]', '', str(rp[10]))):,}원" if re.sub(r'[^0-9]', '', str(rp[10])) else "0원"
        rent_str = f"{int(re.sub(r'[^0-9]', '', str(rp[11]))):,}원" if re.sub(r'[^0-9]', '', str(rp[11])) else "0원"
        
        calc_data.append([i + 2, str(rp[0])[:10], str(rp[1]), str(rp[2]), deposit_str, rent_str, b_type_str, f"{fee:,}원", str(rp[25]), pmethod, f"{final_pay:,}원", f"{comp_profit:,}원", f"{vat:,}원", f"{tax_33:,}원", str(rp[22]) == "O", str(rp[23]) == "O"])
        
    edited_df = st.data_editor(
        pd.DataFrame(calc_data, columns=["줄번호", "계약일", "담당직원", "구분", "보증금", "월세", "매물종류", "총입금액", "입금자명", "수단", "직원급여", "회사수익", "부가세", "소득세", "회사입금(체크)", "직원지급(체크)"]), 
        column_config={
            "줄번호": None, 
            "회사입금(체크)": st.column_config.CheckboxColumn("🟡회사입금완료"),
            "직원지급(체크)": st.column_config.CheckboxColumn("🔴급여지급완료")
        }, 
        disabled=["계약일", "담당직원", "구분", "보증금", "월세", "매물종류", "총입금액", "입금자명", "수단", "직원급여", "회사수익", "부가세", "소득세"], 
        use_container_width=True, hide_index=True, height=600
    )
    
    if st.button("💾 정산 체크 상태 저장"):
        for idx, r in edited_df.iterrows():
            row_num = r["줄번호"]
            if str(contract_records[row_num-2][22] if len(contract_records[row_num-2])>22 else "") != ("O" if r["회사입금(체크)"] else ""):
                ws_contract.update_cell(row_num, 23, "O" if r["회사입금(체크)"] else "") 
            if str(contract_records[row_num-2][23] if len(contract_records[row_num-2])>23 else "") != ("O" if r["직원지급(체크)"] else ""):
                ws_contract.update_cell(row_num, 24, "O" if r["직원지급(체크)"] else "") 
        st.cache_data.clear(); st.success("정산 상태가 완벽하게 저장되었습니다!"); st.rerun()
