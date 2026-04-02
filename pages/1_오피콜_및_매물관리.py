import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
import json
import re
from datetime import datetime, timedelta
import requests

# 🚨 [보안 및 안전망] 정보가 하나라도 비면 뻗지 말고 즉시 메인으로 돌려보냄!
if not st.session_state.get("connected", False) or not st.session_state.get("user_info"):
    st.switch_page("app.py")
    st.stop()

# 💡 [핵심 방어막] 구글 시트 딜레이(시차)를 무시하고 즉시 반영시키는 로컬 기억장치
if 'status_overrides' not in st.session_state: st.session_state.status_overrides = {}
if 'memo_overrides' not in st.session_state: st.session_state.memo_overrides = {}

st.set_page_config(page_title="오피콜 및 매물관리", page_icon="🔍", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        html, body, [class*="css"]  { font-size: 14px !important; }
        .stButton>button { padding: 0.2rem 0.5rem; min-height: 2rem; }
        .block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
        [data-testid="stSidebarNav"] { display: none !important; }
        [data-testid="stSidebar"] { width: 280px !important; display: block !important; }
        div[role="radiogroup"] { flex-direction: row; gap: 15px; padding-bottom: 15px; border-bottom: 2px solid #f0f2f6; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

ADMIN_EMAILS = ["dldmdcks94@gmail.com", "ktg3582@gmail.com"]

KOREA_REGION_DATA = {
    "서울특별시": {"강남구": ["개포동", "논현동", "대치동", "도곡동", "삼성동", "세곡동", "수서동", "신사동", "압구정동", "역삼동", "율현동", "일원동", "자곡동", "청담동"], "강동구": ["강일동", "고덕동", "길동", "둔촌동", "명일동", "상일동", "성내동", "암사동", "천호동"], "송파구": ["가락동", "거여동", "마천동", "문정동", "방이동", "삼전동", "석촌동", "송파동", "신천동", "오금동", "잠실동", "장지동", "풍납동"], "서초구": ["내곡동", "반포동", "방배동", "서초동", "신원동", "양재동", "염곡동", "우면동", "원지동", "잠원동"], "강서구": ["가양동", "개화동", "공항동", "과해동", "내발산동", "등촌동", "마곡동", "방화동", "염창동", "오곡동", "오쇠동", "외발산동", "화곡동"], "관악구": ["남현동", "봉천동", "신림동"], "광진구": ["광장동", "구의동", "군자동", "능동", "자양동", "중곡동", "화양동"], "동대문구": ["답십리동", "신설동", "용두동", "이문동", "장안동", "전농동", "제기동", "청량리동", "회기동", "휘경동"], "마포구": ["공덕동", "구수동", "노고산동", "당인동", "대흥동", "도화동", "마포동", "망원동", "상수동", "상암동", "서교동", "성산동", "신공덕동", "신수동", "신정동", "아현동", "연남동", "염리동", "용강동", "중동", "창전동", "토정동", "하중동", "합정동", "현석동"], "성동구": ["금호동1가", "금호동2가", "금호동3가", "금호동4가", "도선동", "마장동", "사근동", "상왕십리동", "성수동1가", "성수동2가", "송정동", "옥수동", "용답동", "응봉동", "하왕십리동", "행당동", "홍익동"], "용산구": ["갈월동", "남영동", "도원동", "동빙고동", "동자동", "문배동", "보광동", "산천동", "서계동", "서빙고동", "신계동", "신창동", "용문동", "용산동1가", "용산동2가", "용산동3가", "용산동4가", "용산동5가", "용산동6가", "원효로1가", "원효로2가", "원효로3가", "원효로4가", "이촌동", "이태원동", "주성동", "청파동1가", "청파동2가", "청파동3가", "한강로1가", "한강로2가", "한강로3가", "한남동", "효창동", "후암동"], "영등포구": ["당산동", "당산동1가", "당산동2가", "당산동3가", "당산동4가", "당산동5가", "당산동6가", "대림동", "도림동", "문래동1가", "문래동2가", "문래동3가", "문래동4가", "문래동5가", "문래동6가", "신길동", "양평동", "양평동1가", "양평동2가", "양평동3가", "양평동4가", "양평동5가", "양평동6가", "양화동", "여의도동", "영등포동", "영등포동1가", "영등포동2가", "영등포동3가", "영등포동4가", "영등포동5가", "영등포동6가", "영등포동7가", "영등포동8가"], "종로구": ["가회동", "견지동", "경운동", "공평동", "관수동", "관철동", "관훈동", "교남동", "교북동", "구기동", "궁정동", "권농동", "낙원동", "내수동", "내자동", "누상동", "누하동", "당주동", "도렴동", "돈의동", "동숭동", "명륜1가", "명륜2가", "명륜3가", "명륜4가", "묘동", "무악동", "봉익동", "부암동", "사직동", "삼청동", "서린동", "세종로", "소격동", "송월동", "송현동", "수송동", "숭인동", "신교동", "신문로1가", "신문로2가", "신영동", "안국동", "연건동", "연지동", "예지동", "옥인동", "와룡동", "운니동", "원남동", "원서동", "이화동", "익선동", "인사동", "인의동", "장사동", "재동", "적선동", "종로1가", "종로2가", "종로3가", "종로4가", "종로5가", "종로6가", "중학동", "창성동", "창신동", "청운동", "청진동", "체부동", "충신동", "통의동", "통인동", "팔판동", "평동", "평창동", "필운동", "행촌동", "혜화동", "홍지동", "홍파동", "화동", "효자동", "효제동", "훈정동"], "중구": ["광희동1가", "광희동2가", "남대문로1가", "남대문로2가", "남대문로3가", "남대문로4가", "남대문로5가", "남산동1가", "남산동2가", "남산동3가", "남창동", "남학동", "다동", "만리동1가", "만리동2가", "명동1가", "명동2가", "무교동", "무학동", "묵정동", "방산동", "봉래동1가", "봉래동2가", "북창동", "산림동", "삼각동", "서소문동", "소공동", "수표동", "수하동", "순화동", "신당동", "쌍림동", "예관동", "예장동", "오장동", "을지로1가", "을지로2가", "을지로3가", "을지로4가", "을지로5가", "을지로6가", "을지로7가", "인현동1가", "인현동2가", "입정동", "장교동", "장충동1가", "장충동2가", "저동1가", "저동2가", "정동", "주교동", "주자동", "중림동", "초동", "충무로1가", "충무로2가", "충무로3가", "충무로4가", "충무로5가", "태평로1가", "태평로2가", "필동1가", "필동2가", "필동3가", "황학동", "회현동1가", "회현동2가", "회현동3가", "흥인동"]},
    "경기도": {"하남시": ["감북동", "감이동", "감일동", "광암동", "교산동", "덕풍동", "망월동", "미사동", "배알미동", "상사창동", "상산곡동", "선동", "신장동", "창우동", "천현동", "초이동", "초일동", "춘궁동", "풍산동", "하사창동", "하산곡동", "학암동", "항동"], "성남시 수정구": ["고등동", "금토동", "단대동", "둔전동", "복정동", "사송동", "산성동", "상적동", "수진동", "시흥동", "신촌동", "신흥동", "양지동", "오야동", "창곡동", "태평동"], "성남시 분당구": ["구미동", "궁내동", "금곡동", "대장동", "동원동", "백현동", "분당동", "삼평동", "서현동", "석운동", "수내동", "야탑동", "운중동", "율동", "이매동", "정자동", "판교동", "하산운동"], "수원시 팔달구": ["고등동", "교동", "구천동", "남수동", "남창동", "매교동", "매산로1가", "매산로2가", "매산로3가", "매향동", "북수동", "신풍동", "영동", "우만동", "인계동", "장안동", "중동", "지동", "팔달로1가", "팔달로2가", "팔달로3가", "화서동"]},
    "인천광역시": {"연수구": ["동춘동", "선학동", "송도동", "연수동", "옥련동", "청학동"], "부평구": ["갈산동", "구산동", "부개동", "부평동", "산곡동", "삼산동", "십정동", "일신동", "청천동"]},
    "부산광역시": {"강서구":[], "금정구":[], "기장군":[], "남구":[], "동구":[], "동래구":[], "부산진구":[], "북구":[], "사상구":[], "사하구":[], "서구":[], "수영구":[], "연제구":[], "영도구":[], "중구":[], "해운대구":[]},
    "대구광역시": {"남구":[], "달서구":[], "달성군":[], "동구":[], "북구":[], "서구":[], "수성구":[], "중구":[], "군위군":[]},
    "광주광역시": {"광산구":[], "남구":[], "동구":[], "북구":[], "서구":[]},
    "대전광역시": {"대덕구":[], "동구":[], "서구":[], "유성구":[], "중구":[]},
    "울산광역시": {"남구":[], "동구":[], "북구":[], "중구":[], "울주군":[]},
    "세종특별자치시": {"세종시":[]},
    "강원특별자치도": {"강릉시":[], "동해시":[], "삼척시":[], "속초시":[], "원주시":[], "춘천시":[], "태백시":[], "고성군":[], "양구군":[], "양양군":[], "영월군":[], "인제군":[], "정선군":[], "철원군":[], "평창군":[], "홍천군":[], "화천군":[], "횡성군":[]},
    "충청북도": {"제천시":[], "청주시":[], "충주시":[], "괴산군":[], "단양군":[], "보은군":[], "영동군":[], "옥천군":[], "음성군":[], "증평군":[], "진천군":[]},
    "충청남도": {"계룡시":[], "공주시":[], "논산시":[], "당진시":[], "보령시":[], "서산시":[], "아산시":[], "천안시":[], "금산군":[], "부여군":[], "서천군":[], "예산군":[], "청양군":[], "태안군":[], "홍성군":[]},
    "전북특별자치도": {"군산시":[], "김제시":[], "남원시":[], "익산시":[], "전주시":[], "정읍시":[], "고창군":[], "무주군":[], "부안군":[], "순창군":[], "완주군":[], "임실군":[], "장수군":[], "진안군":[]},
    "전라남도": {"광양시":[], "나주시":[], "목포시":[], "순천시":[], "여수시":[], "강진군":[], "고흥군":[], "곡성군":[], "구례군":[], "담양군":[], "무안군":[], "보성군":[], "신안군":[], "영광군":[], "영암군":[], "완도군":[], "장성군":[], "장흥군":[], "진도군":[], "함평군":[], "해남군":[], "화순군":[]},
    "경상북도": {"경산시":[], "경주시":[], "구미시":[], "김천시":[], "문경시":[], "상주시":[], "안동시":[], "영주시":[], "영천시":[], "포항시":[], "고령군":[], "봉화군":[], "성주군":[], "영덕군":[], "영양군":[], "예천군":[], "울릉군":[], "울진군":[], "의성군":[], "청도군":[], "청송군":[], "칠곡군":[]},
    "경상남도": {"거제시":[], "김해시":[], "밀양시":[], "사천시":[], "양산시":[], "진주시":[], "창원시":[], "통영시":[], "거창군":[], "고성군":[], "남해군":[], "산청군":[], "의령군":[], "창녕군":[], "하동군":[], "함안군":[], "함양군":[], "합천군":[]},
    "제주특별자치도": {"서귀포시":[], "제주시":[]}
}

token_dict = json.loads(st.secrets["google_token_json"])
@st.cache_resource
def get_ss(): return gspread.authorize(Credentials.from_authorized_user_info(token_dict)).open_by_key('121-C5OIQpOnTtDbgSLgiq_Qdf5WoHhhIpNkRCWy5hKA')
ss = get_ss()

@st.cache_data(ttl=30)
def fetch_all_data(): 
    ws_data = ss.get_worksheet_by_id(1969836502)
    try: ws_staff = ss.worksheet("직원명단")
    except: ws_staff = None
    try: ws_history = ss.worksheet("토큰내역")
    except: ws_history = None
    try: ws_settings = ss.worksheet("환경설정")
    except: ws_settings = None
    try: ws_b = ss.worksheet("건물정보")
    except: ws_b = None
    
    return (ws_data.get_all_values() if ws_data else [], 
            ws_staff.get_all_records() if ws_staff else [], 
            ws_history.get_all_values() if ws_history else [], 
            ws_settings.get_all_values() if ws_settings else [],
            ws_b.get_all_values() if ws_b else [])

all_data_raw, staff_records, history_all_values, settings_all_values, bldg_all_values = fetch_all_data()

staff_dict = {str(r['이메일']).strip(): r for r in staff_records}
user_email = st.session_state.get("user_info", {}).get("email", "")

now_kst = datetime.utcnow() + timedelta(hours=9)
today_shift = now_kst.strftime("%Y-%m-%d") if now_kst.hour >= 8 else (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")

if user_email in staff_dict:
    user_name = staff_dict[user_email]['이름']
    user_tokens = int(staff_dict[user_email].get('보유토큰', 0))
    staff_row_index = list(staff_dict.keys()).index(user_email) + 2 
    ws_staff = ss.worksheet("직원명단")
    
    last_shift = str(staff_dict[user_email].get('최근할당일', ''))
    if last_shift != today_shift:
        ws_staff.update_cell(staff_row_index, 7, today_shift); ws_staff.update_cell(staff_row_index, 8, 0)
        quota_done = 0; st.cache_data.clear()
    else: quota_done = int(staff_dict[user_email].get('할당진행도', 0)) if str(staff_dict[user_email].get('할당진행도', '')).isdigit() else 0
        
    has_vip = (str(staff_dict[user_email].get('VIP권한', 'X')) == 'O')
    is_locked = False if has_vip else (quota_done < 5) 
elif user_email in ADMIN_EMAILS:
    user_name = "이응찬 대표" if user_email == "dldmdcks94@gmail.com" else "곽태근 대표"
    user_tokens, is_locked, has_vip, quota_done = 9999, False, True, 5
else: 
    st.error("승인되지 않은 계정입니다."); st.stop()

# 💡 [핵심] 관리자 설정 개수 가져오기 (기본값 오피4, 아파트1)
try: office_limit = int(settings_all_values[6][1]) if len(settings_all_values)>6 else 4
except: office_limit = 4
try: apt_limit = int(settings_all_values[7][1]) if len(settings_all_values)>7 else 1
except: apt_limit = 1

def clean_numeric(t): return re.sub(r'[^0-9]', '', str(t))
def is_valid_date(d): return bool(re.match(r'^\d{4}\.\d{2}\.\d{2}$', str(d).strip()))
def update_token(t_name, amt, reason):
    if "대표" in t_name or "관리자" in t_name: return
    try: ws_h = ss.worksheet("토큰내역"); ws_s = ss.worksheet("직원명단")
    except: return
    for i, r in enumerate(staff_records):
        if r['이름'] == t_name:
            ws_s.update_cell(i + 2, 4, int(r.get('보유토큰', 0)) + amt)
            ws_h.append_row([(datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S'), t_name, amt, int(r.get('보유토큰', 0)) + amt, reason], value_input_option='USER_ENTERED')
            break

all_records = []
live_records = [] 
expired_records = [] 

if len(all_data_raw) > 1:
    for i, r in enumerate(all_data_raw[1:]):
        row_idx_sheet = i + 2
        status_val = st.session_state.status_overrides.get(row_idx_sheet, r[25].strip() if len(r)>25 else "정상")
        
        # 💡 실거주는 오피콜뿐만 아니라 리스트에서도 가림
        if not has_vip and status_val in ["비공개", "삭제", "잘못됨", "실거주"]: continue
        
        rp = (r + [""]*28)[:28] + [row_idx_sheet] 
        if row_idx_sheet in st.session_state.memo_overrides: rp[22] = st.session_state.memo_overrides[row_idx_sheet]
        
        d_day = -1
        try:
            reg_dt = datetime.strptime(str(rp[23]).replace("'", ""), '%Y-%m-%d %H:%M:%S')
            days_passed = (now_kst - reg_dt).days
            d_day = 7 - days_passed
        except: pass
        rp.append(d_day) 
        all_records.append(rp)

        if str(rp[26]).strip() in ["전세", "월세", "단기임대", "매매"] and status_val == "정상":
            live_records.append(rp)

def send_kakao_live_room(new_highlight_msg=""):
    try: requests.post("https://kakaowork.com/bots/hook/8fadfba4790e40b49281958fd256c431", json={"text": new_highlight_msg})
    except: pass

st.sidebar.markdown(f"### 👤 {user_name}")
st.sidebar.markdown(f"**보유 토큰:** `{user_tokens} 개`")
if st.sidebar.button("로그아웃"): 
    st.session_state.connected = False; st.session_state.user_info = {}; st.query_params.clear(); st.switch_page("app.py")
st.sidebar.write("---")

tab_names = ["🔥 실시간 매물방", "🔍 전체검색", "🏢 건물 정보", "👤 소유주검색", "📞 오늘의 오피콜", "📝 신규 등록"]
selected_tab = st.radio("메뉴", tab_names, horizontal=True, label_visibility="collapsed")

# (중략 - 실시간 매물방, 검색, 건물정보, 신규등록 탭 코드는 이전과 동일하므로 로직 집중을 위해 생략 표시함)
# ... [이전 코드와 동일한 탭 로직] ...

# ==========================================
# 💡 탭 5: 📞 오늘의 오피콜 (강화된 필터링)
# ==========================================
if selected_tab == "📞 오늘의 오피콜":
    if user_email in ADMIN_EMAILS:
        st.success("👑 대표님 계정입니다! 타겟을 점유하지 않도록 블라인드 처리되었습니다.")
    else:
        st.subheader(f"📞 오늘의 오피콜 (진행도: {quota_done}/5)")
        
        try: target_op_list = [a.strip().replace(" ", "") for a in settings_all_values[1][1].split(",") if a.strip()]
        except: target_op_list = []
        try: target_apt_list = [a.strip().replace(" ", "") for a in settings_all_values[4][1].split(",") if a.strip()]
        except: target_apt_list = []

        op_pool, apt_pool = [], []
        
        for r in all_records:
            status = r[25].strip()
            # 💡 [필터 1] 실거주, 비공개, 삭제는 무조건 제외
            if status in ["비공개", "삭제", "실거주"]: continue
            
            phone = str(r[11]).strip()
            if not phone or "연락처 없음" in phone: continue
            
            # 💡 [필터 2] 3일 쿨타임 (72시간 내 통화 이력 있으면 제외)
            try:
                last_call_dt = datetime.strptime(str(r[23]).replace("'", ""), '%Y-%m-%d %H:%M:%S')
                if (now_kst - last_call_dt).days < 3: continue
            except: pass

            # 💡 [필터 3] 만기일 파악 여부 및 3개월 레이더
            mangi = str(r[21]).strip()
            is_mangi_unknown = (not mangi or mangi == "0000.00.00" or "nan" in mangi)
            is_mangi_soon = False
            if not is_mangi_unknown:
                try:
                    m_dt = datetime.strptime(mangi, '%Y.%m.%d')
                    if (m_dt - now_kst).days <= 90: is_mangi_soon = True
                except: pass
            
            # 만기일 모르거나, 90일 이내인 경우만 타겟
            if not (is_mangi_unknown or is_mangi_soon): continue

            dong, bon, bu = str(r[2]).strip(), str(r[3]).strip(), str(r[4]).strip()
            addr_check = f"{dong}{bon}-{bu}" if bu and bu != "0" else f"{dong}{bon}"
            bldg = str(r[6]).replace(" ", "")
            yongdo = str(r[12]).strip()
            
            if yongdo == "아파트" and any(ta in addr_check or ta in bldg for ta in target_apt_list): apt_pool.append(r)
            elif yongdo != "아파트" and any(ta in addr_check or ta in bldg for ta in target_op_list): op_pool.append(r)

        # 💡 직원별 중복 없는 순환 배분
        eligible_staff = sorted([s['이름'] for s in staff_records if "대표" not in s['이름']])
        my_idx = eligible_staff.index(user_name) if user_name in eligible_staff else 0
        
        my_op = op_pool[my_idx::len(eligible_staff)][:office_limit] if op_pool else []
        my_apt = apt_pool[my_idx::len(eligible_staff)][:apt_limit] if apt_pool else []
        my_assigned = my_op + my_apt

        if not my_assigned:
            st.success("🎉 현재 조건에 맞는 오피콜 타겟이 없습니다!")
        else:
            ws_data = ss.get_worksheet_by_id(1969836502)
            for row in my_assigned:
                addr_str = f"{row[0]} {row[1]} {row[2]} {row[3]}" + (f"-{row[4]}" if row[4] and row[4] != "0" else "")
                room_str = f"{row[7]} {row[8]}" if row[7] and row[7] != "동없음" else f"{row[8]}"
                
                st.markdown(f"**🎯 {row[12]} | {addr_str} {room_str}**")
                st.info(f"**소유주:** {row[9]} | **연락처:** {row[11]}\n\n**기존 보/월:** {row[18]}/{row[19]} | **종료일:** {row[21]}\n\n**히스토리:**\n{row[22]}")
                
                with st.form(f"call_form_{row[28]}"):
                    c1, c2, c3 = st.columns([1.5, 2, 1])
                    new_m = c1.text_input("계약종료일*", placeholder="YYYY.MM.DD")
                    new_f = c2.text_input("피드*", placeholder="통화 결과 입력")
                    # 🌟 [대표님 아이디어] 실거주 체크박스
                    is_owner_living = c3.checkbox("실거주(제외)")
                    
                    if st.form_submit_button("✅ 저장(+1)"):
                        now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
                        updated_memo = f"{row[22]}\n👉 [{now_str[:10][2:].replace('-','.')}] {new_f}"
                        if is_owner_living: updated_memo += " (실거주 확인)"
                        
                        ws_data.update_cell(row[28], 22, new_m if not is_owner_living else today_shift.replace('-','.'))
                        ws_data.update_cell(row[28], 23, updated_memo)
                        ws_data.update_cell(row[28], 24, now_str)
                        ws_data.update_cell(row[28], 25, user_name)
                        if is_owner_living: ws_data.update_cell(row[28], 26, "실거주")
                        
                        if not has_vip: ws_staff.update_cell(staff_row_index, 8, quota_done + 1)
                        update_token(user_name, 1, f"오피콜 완료 ({addr_str})")
                        st.cache_data.clear(); st.rerun()

                if st.button("⏭️ 부재중 (3일 뒤 재노출)", key=f"skip_{row[28]}"):
                    ws_data.update_cell(row[28], 24, now_kst.strftime('%Y-%m-%d %H:%M:%S'))
                    ws_data.update_cell(row[28], 25, user_name)
                    st.cache_data.clear(); st.rerun()
                st.write("---")
