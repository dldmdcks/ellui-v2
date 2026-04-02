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
        .live-card { background-color: #f8f9fa; border-left: 4px solid #00c853; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .stNumberInput input { padding: 0.2rem 0.5rem; }
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
    st.error("승인되지 않은 계정입니다.")
    st.stop()

history_records = history_all_values[1:] if len(history_all_values) > 1 else []
MANAGER_BUILDINGS = {b.strip(): r['이름'] for r in staff_records for b in str(r.get('관리건물', '')).split(',') if b.strip()}

try: target_op_list = [a.strip().replace(" ", "") for a in (settings_all_values[1][1] if len(settings_all_values)>1 and len(settings_all_values[1])>1 else "").split(",") if a.strip()]
except: target_op_list = []

try: target_apt_list = [a.strip().replace(" ", "") for a in (settings_all_values[4][1] if len(settings_all_values)>4 and len(settings_all_values[4])>1 else "").split(",") if a.strip()]
except: target_apt_list = []

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
        
        if not has_vip and status_val in ["비공개", "삭제", "잘못됨"]: continue
        
        rp = (r + [""]*28)[:28] + [row_idx_sheet] 
        
        if row_idx_sheet in st.session_state.memo_overrides:
            rp[22] = st.session_state.memo_overrides[row_idx_sheet]
        
        d_day = -1
        try:
            reg_dt = datetime.strptime(str(rp[23]).replace("'", ""), '%Y-%m-%d %H:%M:%S')
            days_passed = (now_kst - reg_dt).days
            d_day = 7 - days_passed
        except: pass
        rp.append(d_day) 

        tr_type = str(rp[26]).strip()
        yongdo = str(rp[12]).strip()
        is_live_format = tr_type in ["전세", "월세", "단기임대", "매매"]
        
        full_addr_check = f"{str(rp[2])} {str(rp[3])}-{str(rp[4])} {str(rp[6])}"
        is_managed = False
        for b_name in MANAGER_BUILDINGS.keys():
            if b_name.replace(" ","") in full_addr_check.replace(" ",""): is_managed = True; break

        if is_live_format and status_val not in ["비공개", "삭제", "잘못됨"]:
            if is_managed or yongdo in ["빌라", "상가", "다세대", "다가구"]: 
                live_records.append(rp)
            else:
                if d_day >= 0: live_records.append(rp)
                elif d_day < 0 and str(rp[24]).strip(): expired_records.append(rp)
                
        all_records.append(rp)

all_records.reverse()
live_records.sort(key=lambda x: f"{str(x[2]).strip()} {str(x[3]).strip()}-{str(x[4]).strip()}") 

op_live, apt_live, etc_live = [], [], []
for r in live_records:
    yd = str(r[12]).strip()
    if yd == "오피스텔": op_live.append(r)
    elif yd == "아파트": apt_live.append(r)
    else: etc_live.append(r)

def build_kakao_msg_for_group(group_list, group_title):
    if not group_list: return ""
    msg = f"━━━━━━━━━━━━━━\n🌟 [{group_title} 매물]\n━━━━━━━━━━━━━━\n\n"
    grouped = {}
    for r in group_list:
        d_str, b_str, bu_str = str(r[2]).strip(), str(r[3]).strip(), str(r[4]).strip()
        bldg_name = str(r[6]).strip()
        addr_key = f"[{d_str} {b_str}" + (f"-{bu_str}" if bu_str and bu_str != "0" else "") + "]"
        display_group_name = f"{addr_key} {bldg_name}".strip() if bldg_name else addr_key
        if display_group_name not in grouped: grouped[display_group_name] = []
        grouped[display_group_name].append(r)
        
    for g_name in sorted(grouped.keys()):
        msg += f"<{g_name}>\n"
        for r in grouped[g_name]:
            ho = f"{r[7]} {r[8]}".strip().replace("동없음 ", "")
            tr_type = str(r[26]); biz_type = str(r[27])
            
            dep = int(clean_numeric(r[18])) if clean_numeric(r[18]) else 0
            rent = int(clean_numeric(r[19])) if clean_numeric(r[19]) else 0
            price_str = f"{dep:,}/{rent:,}" if rent > 0 else f"{dep:,}"
            
            end_date = str(r[21]).strip()
            if end_date == "0000.00.00" or not end_date:
                end_date_short = "미정"
            else:
                end_date_short = end_date[2:] if end_date.startswith("20") else end_date
                
            # 💡 [핵심 패치] 가장 마지막(최신) 피드만 깔끔하게 추출해서 40자까지 넉넉하게 카톡으로 보냅니다!
            last_memo = str(r[22]).split('\n')[-1] if str(r[22]) else ""
            clean_memo = re.sub(r'👉 \[\d{2}\.\d{2}\.\d{2}\]\s*(매물방\s*등록:?|신규등록:?)?\s*', '', last_memo).strip()
            memo_short = clean_memo[:40]
            
            d_val = r[29]
            d_str = f"D-{d_val}" if d_val >= 0 else f"D+{-d_val} 🚨"
            
            memo_part = f"/{memo_short}" if memo_short else ""
            msg += f"{ho}/{tr_type} {price_str}/만기 {end_date_short}{memo_part}/{biz_type}/{r[24]}/{d_str}\n"
        msg += "\n"
    return msg

def send_kakao_live_room(new_highlight_msg=""):
    full_msg = "🔥 [실시간 엘루이 매물방 업데이트]\n\n"
    full_msg += build_kakao_msg_for_group(op_live, "오피스텔")
    full_msg += build_kakao_msg_for_group(apt_live, "아파트")
    full_msg += build_kakao_msg_for_group(etc_live, "빌라/상가/기타건물")
    
    if new_highlight_msg:
        full_msg += f"\n👇 [🔔 실시간 알림]\n{new_highlight_msg}"
        
    try: requests.post("https://kakaowork.com/bots/hook/8fadfba4790e40b49281958fd256c431", json={"text": full_msg})
    except: pass

st.sidebar.markdown(f"### 👤 {user_name}")
st.sidebar.markdown(f"**보유 토큰:** `{user_tokens} 개`")
if st.sidebar.button("로그아웃"): 
    st.session_state.connected = False
    st.session_state.user_info = {}
    st.query_params.clear()
    st.switch_page("app.py")
st.sidebar.write("---")

st.sidebar.markdown("### 🧭 메뉴 이동")
st.sidebar.page_link("app.py", label="홈", icon="🏠")
st.sidebar.page_link("pages/1_오피콜_및_매물관리.py", label="매물/DB", icon="🔍")
st.sidebar.page_link("pages/2_계약보고_시스템.py", label="계약정산", icon="💰")
st.sidebar.page_link("pages/3_팀장회의.py", label="회의록", icon="🤝")
st.sidebar.page_link("pages/5_경험치북.py", label="경험치북", icon="📖") 
if user_email in ADMIN_EMAILS: st.sidebar.page_link("pages/4_관리자.py", label="관리자", icon="⚙️")
st.sidebar.write("---")

tab_names = ["🔥 실시간 매물방", "🔍 전체검색", "🏢 건물 정보", "👤 소유주검색", "📞 오늘의 오피콜", "📝 신규 등록"]
if has_vip: tab_names.insert(5, "⏰ VIP만기")
selected_tab = st.radio("메뉴", tab_names, horizontal=True, label_visibility="collapsed")

# ==========================================
# 탭 1: 🔥 실시간 매물방
# ==========================================
if selected_tab == "🔥 실시간 매물방":
    st.title("🔥 실시간 매물방 (Live)")
    st.write("새로 등록한 매물만 표시되며, 카톡 워크로 연동됩니다.")
    ws_data = ss.get_worksheet_by_id(1969836502)
    
    with st.expander("➕ [신규 매물 등록] 매물방에 띄우기 (기존 DB 연동)", expanded=False):
        reg_type = st.radio("어떤 매물인가요?", ["🏢 일반 오피스텔/아파트", "🏘️ 빌라/상가/기타(관리건물)"], horizontal=True)
        
        with st.form("new_data_form", clear_on_submit=True):
            c_reg1, c_reg2, c_reg3 = st.columns(3)
            n_city = c_reg1.selectbox("시/도", list(KOREA_REGION_DATA.keys()), index=list(KOREA_REGION_DATA.keys()).index("서울특별시") if "서울특별시" in KOREA_REGION_DATA else 0)
            
            gu_opts = list(KOREA_REGION_DATA[n_city].keys())
            if "➕직접 입력" not in gu_opts: gu_opts.append("➕직접 입력")
            n_gu_sel = c_reg2.selectbox("시/군/구", gu_opts, index=gu_opts.index("송파구") if "송파구" in gu_opts else 0)
            
            if n_gu_sel == "➕직접 입력": n_gu = st.text_input("시/군/구 직접 입력 (예: 해운대구)")
            else: n_gu = n_gu_sel
            
            dong_opts = KOREA_REGION_DATA[n_city].get(n_gu, []) + ["➕직접 입력"]
            n_dong_sel = c_reg3.selectbox("법정동", dong_opts, index=dong_opts.index("방이동") if "방이동" in dong_opts else 0)
            
            if n_dong_sel == "➕직접 입력": n_dong = st.text_input("법정동 직접 입력 (예: 방이동)")
            else: n_dong = n_dong_sel
            
            c_n1, c_n2, c_n3 = st.columns(3)
            n_bon = c_n1.text_input("본번", placeholder="28")
            n_bu = c_n2.text_input("부번", placeholder="2")
            n_room = c_n3.text_input("호실", placeholder="101")
            n_bldg = st.text_input("🏢 건물명 (선택사항, 입력 시 가시성 극대화)", placeholder="예: 엘루이시티")
            
            c_t1, c_t2, c_t3 = st.columns(3)
            if "일반" in reg_type: yongdo_opts = ["오피스텔", "아파트"]
            else: yongdo_opts = ["빌라", "상가", "다세대", "다가구", "기타"]
            n_btype = c_t1.selectbox("용도", yongdo_opts)
            n_tr_type = c_t2.selectbox("거래 종류", ["전세", "월세", "단기임대", "매매"])
            n_biz_type = c_t3.selectbox("사업자 유형", ["무사업자", "주임사", "일임사", "확인불가"])
            
            c_d1, c_d2, c_d3 = st.columns(3)
            n_dep = c_d1.text_input("보증금", placeholder="10000000")
            n_rent = c_d2.text_input("월세 (없으면 0)", placeholder="1000000")
            n_end = c_d3.text_input("계약 종료일 (YYYY.MM.DD 또는 0000.00.00)", placeholder="0000.00.00")
            
            n_memo = st.text_area("피드 (특이사항)")
            
            if st.form_submit_button("🚀 매물방에 등록하기", type="primary"):
                is_duplicate = False
                dup_manager = ""
                for lr in live_records:
                    if str(lr[2]).strip() == str(n_dong).strip() and str(lr[3]).strip() == str(n_bon).strip() and str(lr[4]).strip() == str(n_bu).strip() and re.sub(r'[^0-9]', '', str(lr[8])) == re.sub(r'[^0-9]', '', str(n_room)):
                        is_duplicate = True; dup_manager = lr[24]; break
                        
                if is_duplicate: st.error(f"🚨 이미 매물방에 등록되어 살아있는 매물입니다! (담당자: {dup_manager})")
                elif not n_dong or not n_bon or not n_room: st.error("필수 항목(동, 본번, 호수)을 입력하세요.")
                else:
                    in_dong, in_bon, in_bu, in_room = str(n_dong).strip(), str(n_bon).strip(), str(n_bu).strip() if str(n_bu).strip() else "0", re.sub(r'[^0-9]', '', str(n_room))
                    old_history = ""
                    
                    for idx_db, r_row in enumerate(all_data_raw):
                        if idx_db == 0: continue
                        r_dong, r_bon, r_bu = str(r_row[2]).strip(), str(r_row[3]).strip(), str(r_row[4]).strip()
                        r_room = re.sub(r'[^0-9]', '', str(r_row[8])) if len(r_row)>8 else ""
                        if r_dong == in_dong and r_bon == in_bon and r_bu == in_bu and r_room == in_room:
                            curr_hist = str(r_row[22]).strip() if len(r_row)>22 else ""
                            if len(curr_hist) > len(old_history): old_history = curr_hist
                            if len(r_row) <= 25 or str(r_row[25]).strip() != "비공개":
                                ws_data.update_cell(idx_db+1, 26, "비공개")
                                st.session_state.status_overrides[idx_db+1] = "비공개" 
                    
                    now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
                    final_memo = f"{old_history}\n👉 [{now_str[:10][2:].replace('-','.')}] 매물방 등록: {n_memo}".strip() if old_history else f"👉 [{now_str[:10][2:].replace('-','.')}] 매물방 등록: {n_memo}"
                    
                    new_row = [""] * 28
                    new_row[0], new_row[1], new_row[2], new_row[3], new_row[4], new_row[6], new_row[7], new_row[8] = n_city, n_gu, n_dong, n_bon, n_bu, n_bldg, "동없음", n_room
                    new_row[9], new_row[11], new_row[12], new_row[14], new_row[18], new_row[19] = "", "", n_btype, "위반 없음", n_dep, n_rent
                    new_row[21], new_row[22], new_row[23], new_row[24], new_row[25] = n_end, final_memo, now_str, user_name, "정상"
                    new_row[26], new_row[27] = n_tr_type, n_biz_type
                    
                    ws_data.append_row(new_row, value_input_option='USER_ENTERED')
                    
                    price_s = f"{int(clean_numeric(n_dep)):,}/{int(clean_numeric(n_rent)):,}" if clean_numeric(n_rent) and n_rent != "0" else f"{int(clean_numeric(n_dep)):,}"
                    n_bu_str = f"-{n_bu}" if n_bu and n_bu != "0" else ""
                    b_s = f"[{n_dong} {n_bon}{n_bu_str}] {n_bldg}".strip() if n_bldg else f"[{n_dong} {n_bon}{n_bu_str}]"
                    
                    temp_live_row = new_row.copy(); temp_live_row.append(0); temp_live_row.append(7) 
                    
                    if n_btype == "오피스텔": op_live.append(temp_live_row)
                    elif n_btype == "아파트": apt_live.append(temp_live_row)
                    else: etc_live.append(temp_live_row)
                    
                    send_kakao_live_room(f"{b_s}/{n_room}/{n_tr_type} {price_s}/{n_memo[:40]}/{n_biz_type}/{user_name}")
                    st.cache_data.clear(); st.success("🎉 매물방 등록 완료!"); st.rerun()

    if user_email in ADMIN_EMAILS:
        if st.button("🚀 단톡방에 현재 3단 매물 리스트 쏘기 (관리자)"):
            send_kakao_live_room("수동 브리핑 발송 완료")
            st.success("카카오워크 발송 완료!")
        
    st.write("---")
    
    def render_live_group(group_list, title, icon):
        if not group_list: return
        st.markdown(f"### {icon} {title} 매물")
        for r in group_list:
            city, gu, dong, bon, bu, road, bldg, d_dong, room, name, birth, phone, b_type, appr_date, viol, land_area, room_area, curr_biz, deposit, rent, fee, end_date, memo, reg_date, registrar, status, tr_type, biz_type, row_idx, d_day = r
            addr_key = f"[{dong} {bon}" + (f"-{bu}" if bu and bu != "0" else "") + "]"
            b_name = f"{addr_key} {bldg}".strip() if bldg else addr_key
            ho_str = f"{d_dong} {room}".strip().replace("동없음 ", "")
            
            dep_val = int(clean_numeric(deposit)) if clean_numeric(deposit) else 0
            rent_val = int(clean_numeric(rent)) if clean_numeric(rent) else 0
            price_str = f"{dep_val:,} / {rent_val:,}" if rent_val > 0 else f"{dep_val:,}"
            
            d_color = "🟢" if d_day >= 4 else "🔴"
            d_str = f"D-{d_day}" if d_day >= 0 else f"D+{-d_day}🚨"
            
            st.markdown(f"**{b_name} {ho_str}** ({tr_type} {price_str}) {d_color} {d_str}")
            st.write(f"입주: {end_date} | 유형: {biz_type} | 담당: {registrar}")
            
            # 💡 웹 화면에서 메모 히스토리가 줄바꿈되어 예쁘게 보이도록 디자인 패치
            st.markdown(f"<div style='color:gray; font-size:0.85em;'>📝 {str(memo).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            st.write("")
            
            if registrar == user_name or has_vip:
                c_exp1, c_exp2 = st.columns(2)
                with c_exp1:
                    with st.expander("🔄 최신화(연장)"):
                        with st.form(f"ex_{row_idx}"):
                            new_memo = st.text_input("추가 피드", placeholder="통화 완료")
                            if st.form_submit_button("최신화(+1)"):
                                now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
                                up_memo = f"{memo}\n👉 [{now_str[:10][2:].replace('-','.')}] {new_memo}".strip() if memo else f"👉 [{now_str[:10][2:].replace('-','.')}] {new_memo}"
                                ws_data = ss.get_worksheet_by_id(1969836502)
                                ws_data.update_cell(row_idx, 23, up_memo); ws_data.update_cell(row_idx, 24, now_str) 
                                
                                st.session_state.memo_overrides[row_idx] = up_memo
                                
                                # 💡 [핵심] 카톡 발송 전에 시스템 내부 리스트의 메모를 방금 쓴 걸로 갈아 끼움!
                                for lst in (op_live, apt_live, etc_live):
                                    for item in lst:
                                        if item[28] == row_idx:
                                            item[22] = up_memo
                                
                                update_token(user_name, 1, f"매물 최신화 ({b_name} {ho_str})")
                                send_kakao_live_room(f"{b_name}/{ho_str}/[갱신] {new_memo}/{user_name}")
                                st.cache_data.clear(); st.rerun()
                with c_exp2:
                    with st.expander("❌ 내리기(계약/보류)"):
                        with st.form(f"dr_{row_idx}"):
                            drop_reason = st.selectbox("사유", ["타부동산 계약", "보류", "당사계약", "기타"])
                            if st.form_submit_button("내리기"):
                                now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
                                up_memo = f"{memo}\n👉 [{now_str[:10][2:].replace('-','.')}] 내림: {drop_reason}".strip() if memo else f"👉 [{now_str[:10][2:].replace('-','.')}] 내림: {drop_reason}"
                                ws_data = ss.get_worksheet_by_id(1969836502)
                                ws_data.update_cell(row_idx, 23, up_memo); ws_data.update_cell(row_idx, 26, "비공개") 
                                
                                st.session_state.status_overrides[row_idx] = "비공개"
                                
                                op_live[:] = [x for x in op_live if x[28] != row_idx]
                                apt_live[:] = [x for x in apt_live if x[28] != row_idx]
                                etc_live[:] = [x for x in etc_live if x[28] != row_idx]
                                
                                send_kakao_live_room(f"{b_name}/{ho_str} ❌ 내림({drop_reason})/{user_name}")
                                st.cache_data.clear(); st.rerun()
            st.write("---")

    render_live_group(op_live, "오피스텔", "🏢")
    render_live_group(apt_live, "아파트", "🏘️")
    render_live_group(etc_live, "빌라/상가/기타건물", "🏡")
    if not (op_live or apt_live or etc_live): st.info("현재 확인된 살아있는 매물이 없습니다.")

# ==========================================
# 탭 2: 🔍 전체검색
# ==========================================
elif selected_tab == "🔍 전체검색":
    if is_locked: st.markdown(f"<div class='locked-tab'><h2>🔒 오늘 할당량을 먼저 완수해주세요!</h2><p>할당량({quota_done}/5건) 완료 시 해제</p></div>", unsafe_allow_html=True)
    else:
        st.subheader("🔍 엘루이 통합 디테일 검색")
        
        with st.form("search_addr_form"):
            c_s1, c_s2, c_s3 = st.columns(3)
            sel_sido = c_s1.selectbox("시/도", ["전체"] + list(KOREA_REGION_DATA.keys()), index=list(KOREA_REGION_DATA.keys()).index("서울특별시")+1 if "서울특별시" in KOREA_REGION_DATA else 1)
            
            gu_opts = ["전체"] + list(KOREA_REGION_DATA[sel_sido].keys()) if sel_sido != "전체" else ["전체"]
            sel_sigungu = c_s2.selectbox("시/군/구", gu_opts, index=gu_opts.index("송파구") if "송파구" in gu_opts else 0)
            
            dong_opts = ["전체"] + (KOREA_REGION_DATA[sel_sido][sel_sigungu] if sel_sigungu != "전체" and sel_sido != "전체" else [])
            sel_dong = c_s3.selectbox("법정동", dong_opts, index=dong_opts.index("방이동") if "방이동" in dong_opts else 0)
            
            c_f1, c_f2 = st.columns([2, 1])
            b_search = c_f1.text_input("번지/건물명", placeholder="28-2 또는 엘루이")
            r_search = c_f2.text_input("호실", placeholder="101")
            
            st.write("**💰 금액 필터 (단위: 만원)**")
            c_p1, c_p2, c_p3, c_p4 = st.columns(4)
            min_dep = c_p1.number_input("최소 보증금", value=0, step=1000)
            max_dep = c_p2.number_input("최대 보증금", value=999999, step=1000)
            min_rent = c_p3.number_input("최소 월세", value=0, step=10)
            max_rent = c_p4.number_input("최대 월세", value=9999, step=10)
            
            st.write("**✨ 특수 조건**")
            c_k1, c_k2 = st.columns([1, 2])
            pet_ok = c_k1.checkbox("🐶 애완(반려동물) 가능만 보기")
            kw_search = c_k2.text_input("특이사항 포함 키워드", placeholder="예: 전입, 풀옵션, 주차")
            
            if st.form_submit_button("🔍 검색하기", type="primary", use_container_width=True):
                res = []
                for r in all_records:
                    if sel_sido != "전체" and sel_sido != str(r[0]).strip(): continue
                    if sel_sigungu != "전체" and sel_sigungu != str(r[1]).strip(): continue
                    if sel_dong != "전체" and sel_dong != str(r[2]).strip(): continue
                    
                    addr_combined = ((f"{r[3]}-{r[4]}" if str(r[4])!="0" else str(r[3]))+str(r[6])).replace(" ","")
                    if b_search and b_search.replace(" ","") not in addr_combined: continue
                    if r_search and r_search.replace(" ","") not in (str(r[7])+str(r[8])).replace(" ",""): continue
                    
                    dep_val = int(clean_numeric(r[18])) // 10000 if clean_numeric(r[18]) else 0
                    rent_val = int(clean_numeric(r[19])) // 10000 if clean_numeric(r[19]) else 0
                    if not (min_dep <= dep_val <= max_dep): continue
                    if not (min_rent <= rent_val <= max_rent): continue
                    
                    memo_text = str(r[22]).replace(" ", "")
                    if pet_ok:
                        has_pet_kw = any(k in memo_text for k in ["애완", "반려", "동물", "강아지", "고양이", "펫"])
                        has_no_kw = any(k in memo_text for k in ["불가", "안됨", "x", "금지"])
                        if not (has_pet_kw and not has_no_kw) and "애완가능" not in memo_text and "반려동물가능" not in memo_text:
                            continue
                            
                    if kw_search and kw_search.replace(" ", "") not in memo_text: continue
                    res.append(r)
                    
                st.session_state.addr_search_res = sorted(res, key=lambda x: int(clean_numeric(x[8])) if clean_numeric(x[8]) else 9999)
        
        if st.session_state.get("addr_search_res"):
            st.caption(f"검색 결과: {len(st.session_state.addr_search_res)}건")
            for idx, row in enumerate(st.session_state.addr_search_res):
                addr_str = f"{row[0]} {row[1]} {row[2]} {row[3]}" + (f"-{row[4]}" if row[4] and row[4] != "0" else "") + (f" {row[6]}" if row[6] else "")
                room_str = f"{row[7]} {row[8]}" if row[7] and row[7] != "동없음" else f"{row[8]}"
                m_name = next((m for b, m in MANAGER_BUILDINGS.items() if f" {b} " in f" {addr_str} "), None)
                st.markdown(f"**📍 {addr_str} | {room_str}**" + (f" | 👑 {m_name} 관리" if m_name else ""))
                
                if m_name and m_name != user_name and not has_vip: st.error(f"🔒 전담 매물"); st.write("---"); continue

                uk, tk = f"unlock_addr_{addr_str}_{room_str}", f"toggle_addr_{idx}"
                if has_vip or user_email in ADMIN_EMAILS or st.session_state.get(uk, False):
                    if st.button("🔓 닫기/열기", key=f"btn_re_{idx}"): st.session_state[tk] = not st.session_state.get(tk, False)
                    if st.session_state.get(tk, False) or has_vip or user_email in ADMIN_EMAILS:
                        d_val = int(clean_numeric(row[18])) if clean_numeric(row[18]) else 0
                        r_val = int(clean_numeric(row[19])) if clean_numeric(row[19]) else 0
                        p_str = f"{d_val:,} / {r_val:,}" if r_val > 0 else f"{d_val:,}"
                        st.info(f"**소유주:** {row[9]}({row[10]}) | **연락처:** {row[11]}\n\n**보/월:** {p_str} | **만기:** {row[21]}\n\n**히스토리:**\n{row[22]}")
                else:
                    if st.button("🔓 열람 (-1토큰)", key=f"btn_addr_{idx}"):
                        if user_tokens >= 1: update_token(user_name, -1, f"매물 열람 ({addr_str})"); st.session_state[uk] = True; st.session_state[tk] = True; st.cache_data.clear(); st.rerun()
                        else: st.error("토큰 부족")
                st.write("---")

# ==========================================
# 탭 3: 🏢 건물 정보
# ==========================================
elif selected_tab == "🏢 건물 정보":
    st.title("🏢 건물 비밀수첩")
    st.write("각 건물의 주소, 관리실 번호, 공동현관 및 화장실 비밀번호를 모아두는 곳입니다.")
    
    try: ws_building = ss.worksheet("건물정보")
    except: ws_building = None
    
    if ws_building is None:
        st.error("🚨 구글 마스터 시트에 **'건물정보'** 탭이 없습니다! 구글 시트 하단에서 [+] 버튼을 눌러 탭을 생성해주세요.")
    else:
        with st.expander("➕ 새로운 건물 정보 등록", expanded=False):
            with st.form("add_bldg"):
                c_b1, c_b2 = st.columns(2)
                b_name = c_b1.text_input("건물명* (예: 엘루이시티)")
                b_addr = c_b2.text_input("주소 (예: 방이동 28-2)")
                
                c_b3, c_b4, c_b5 = st.columns(3)
                b_mgmt = c_b3.text_input("관리실 번호")
                b_pw1 = c_b4.text_input("1층 현관 비밀번호")
                b_pw2 = c_b5.text_input("화장실 비밀번호")
                
                b_note = st.text_area("기타 참고사항")
                
                if st.form_submit_button("등록"):
                    if not b_name: st.error("건물명은 필수입니다.")
                    else:
                        now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
                        history_str = f"👉 [{now_str[:16]}] {user_name} 최초 등록"
                        
                        new_row = [b_name, b_mgmt, b_pw1, b_pw2, user_name, now_str, b_note, b_addr, history_str]
                        ws_building.append_row(new_row, value_input_option='USER_ENTERED')
                        st.cache_data.clear(); st.success("저장 완료!"); st.rerun()
                        
        st.write("---")
        search_bldg = st.text_input("🔍 건물명 또는 주소 검색 (비워두면 전체 표시)")
        
        has_data = False
        
        for i, r in reversed(list(enumerate(bldg_all_values))):
            if i == 0 or not r or r[0] == "건물명": continue 
            if len(r) < 1: continue
            
            sheet_row_idx = i + 1 
            
            name_val = str(r[0]).strip()
            mgmt_val = str(r[1]).strip() if len(r) > 1 else ""
            pw1_val = str(r[2]).strip() if len(r) > 2 else ""
            pw2_val = str(r[3]).strip() if len(r) > 3 else ""
            updater_val = str(r[4]).strip() if len(r) > 4 else ""
            date_val = str(r[5]).strip() if len(r) > 5 else ""
            note_val = str(r[6]).strip() if len(r) > 6 else ""
            addr_val = str(r[7]).strip() if len(r) > 7 else ""
            hist_val = str(r[8]).strip() if len(r) > 8 else ""
            
            if search_bldg and search_bldg not in name_val and search_bldg not in addr_val: continue
            
            has_data = True
            
            st.markdown(f"### 📍 {name_val} <span style='font-size:0.6em; color:gray;'>{addr_val}</span>", unsafe_allow_html=True)
            st.info(f"**📞 관리실:** {mgmt_val} | **🔑 1층 비번:** {pw1_val} | **🚽 화장실:** {pw2_val}\n\n**📝 비고:** {note_val} \n\n*(최근 업데이트: {date_val} by {updater_val})*")
            
            with st.expander("✏️ 정보 수정 및 히스토리 보기"):
                if hist_val:
                    st.caption("📜 **수정 히스토리**")
                    st.code(hist_val)
                
                with st.form(f"edit_bldg_{sheet_row_idx}"):
                    c_e1, c_e2 = st.columns(2)
                    e_name = c_e1.text_input("건물명*", value=name_val)
                    e_addr = c_e2.text_input("주소", value=addr_val)
                    
                    c_e3, c_e4, c_e5 = st.columns(3)
                    e_mgmt = c_e3.text_input("관리실 번호", value=mgmt_val)
                    e_pw1 = c_e4.text_input("1층 현관 비밀번호", value=pw1_val)
                    e_pw2 = c_e5.text_input("화장실 비밀번호", value=pw2_val)
                    
                    e_note = st.text_area("기타 참고사항", value=note_val)
                    
                    if st.form_submit_button("💾 수정 내용 저장하기", type="primary"):
                        if not e_name: st.error("건물명은 필수입니다.")
                        else:
                            now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
                            new_hist = f"👉 [{now_str[:16]}] {user_name} 정보 수정\n{hist_val}"
                            
                            ws_building.update_cell(sheet_row_idx, 1, e_name)
                            ws_building.update_cell(sheet_row_idx, 2, e_mgmt)
                            ws_building.update_cell(sheet_row_idx, 3, e_pw1)
                            ws_building.update_cell(sheet_row_idx, 4, e_pw2)
                            ws_building.update_cell(sheet_row_idx, 5, user_name)
                            ws_building.update_cell(sheet_row_idx, 6, now_str)
                            ws_building.update_cell(sheet_row_idx, 7, e_note)
                            ws_building.update_cell(sheet_row_idx, 8, e_addr)
                            ws_building.update_cell(sheet_row_idx, 9, new_hist)
                            
                            st.cache_data.clear()
                            st.rerun()
            st.write("---")
            
        if not has_data:
            st.info("아직 등록된 건물 정보가 없거나, 검색 결과가 없습니다.")

# ==========================================
# 탭 4: 👤 소유주검색 
# ==========================================
elif selected_tab == "👤 소유주검색":
    if is_locked: 
        st.markdown(f"<div class='locked-tab'><h2>🔒 오늘 할당량을 먼저 완수해주세요!</h2><p>할당량({quota_done}/5건) 완료 시 해제</p></div>", unsafe_allow_html=True)
    else:
        st.subheader("👤 소유주 통합 검색")
        st.write("소유주 이름이나 연락처(전체 또는 뒷자리)를 입력하여 관련된 모든 매물과 히스토리를 확인하세요.")
        
        with st.form("owner_search_form"):
            search_keyword = st.text_input("이름 또는 연락처 입력", placeholder="예: 홍길동 또는 1234")
            if st.form_submit_button("🔍 검색", type="primary", use_container_width=True):
                res = []
                for r in all_records:
                    owner_name = str(r[9]).strip().replace(" ", "")
                    owner_phone = str(r[11]).strip().replace("-", "")
                    kw = search_keyword.replace(" ", "").replace("-", "")
                    if kw and (kw in owner_name or kw in owner_phone):
                        res.append(r)
                st.session_state.owner_search_res = res
        
        if st.session_state.get("owner_search_res"):
            st.caption(f"검색 결과: {len(st.session_state.owner_search_res)}건")
            for idx, row in enumerate(st.session_state.owner_search_res):
                addr_str = f"{row[0]} {row[1]} {row[2]} {row[3]}" + (f"-{row[4]}" if row[4] and row[4] != "0" else "") + (f" {row[6]}" if row[6] else "")
                room_str = f"{row[7]} {row[8]}" if row[7] and row[7] != "동없음" else f"{row[8]}"
                
                d_val = int(clean_numeric(row[18])) if clean_numeric(row[18]) else 0
                r_val = int(clean_numeric(row[19])) if clean_numeric(row[19]) else 0
                p_str = f"{d_val:,} / {r_val:,}" if r_val > 0 else f"{d_val:,}"
                
                st.markdown(f"### 👤 {row[9]} ({row[10]}) | 📞 {row[11]}")
                st.markdown(f"**📍 {addr_str} | {room_str}**")
                st.info(f"**보/월:** {p_str} | **만기:** {row[21]}\n\n**히스토리:**\n{row[22]}")
                st.write("---")

# ==========================================
# 탭 5: 📞 오늘의 오피콜
# ==========================================
elif selected_tab == "📞 오늘의 오피콜":
    if user_email in ADMIN_EMAILS:
        st.success("👑 대표님 계정입니다! 타겟을 점유하지 않도록 블라인드 처리되었습니다.")
    else:
        if has_vip: 
            st.success("🎉 VIP 계정은 오피콜 의무 할당량이 면제됩니다!")
            quota_done = 5 
        else: st.subheader(f"📞 오늘의 오피콜 (진행도: {quota_done}/5)")

        if quota_done >= 5 and not has_vip: st.success("🎉 오늘의 오피콜을 모두 완료했습니다!")
        
        op_candidates, apt_candidates = [], []
        
        for r in expired_records + all_records:
            if today_shift in str(r[23]): continue 
            if "연락처 없음" in str(r[11]) or not str(r[11]).strip(): continue
            
            dong = str(r[2]).strip()
            bon = str(r[3]).strip()
            bu = str(r[4]).strip()
            addr_no_space = f"{dong}{bon}-{bu}" if bu and bu != "0" else f"{dong}{bon}"
            bldg = str(r[6]).replace(" ", "")
            yongdo = str(r[12]).strip()
            
            is_apt = any((ta in addr_no_space or ta in bldg or addr_no_space in ta) for ta in target_apt_list if ta)
            is_op = any((ta in addr_no_space or ta in bldg or addr_no_space in ta) for ta in target_op_list if ta)
            
            if yongdo == "아파트" and is_apt: apt_candidates.append(r)
            elif yongdo != "아파트" and is_op: op_candidates.append(r)
                
        def deduplicate_pool(pool):
            seen = set(); res = []
            for x in pool:
                if x[28] not in seen: seen.add(x[28]); res.append(x)
            return res
            
        unique_op = deduplicate_pool(op_candidates)
        unique_apt = deduplicate_pool(apt_candidates)
                
        eligible_staff = sorted([r['이름'] for r in staff_records if r['이름'] not in ["이응찬 대표", "곽태근 대표"]])
        my_idx = eligible_staff.index(user_name) if user_name in eligible_staff else 0
        
        items_to_show = 5 if has_vip else (5 - quota_done)
        
        my_op = unique_op[my_idx * 4 : (my_idx * 4) + 4]
        my_apt = unique_apt[my_idx * 1 : (my_idx * 1) + 1]
        
        my_assigned_pool = my_op + my_apt
        
        if len(my_assigned_pool) < items_to_show:
            shortage = items_to_show - len(my_assigned_pool)
            extra_op = unique_op[(my_idx * 4) + 4 : (my_idx * 4) + 4 + shortage]
            my_assigned_pool += extra_op
            
        my_assigned_pool = my_assigned_pool[:items_to_show]
        
        ws_data = ss.get_worksheet_by_id(1969836502)
        
        if not my_assigned_pool: st.success("🎉 배정된 타겟 명단이 모두 소진되었습니다!")
        else:
            for idx, row in enumerate(my_assigned_pool):
                addr_str = f"{row[0]} {row[1]} {row[2]} {row[3]}" + (f"-{row[4]}" if row[4] and row[4] != "0" else "")
                room_str = f"{row[7]} {row[8]}" if row[7] and row[7] != "동없음" else f"{row[8]}"
                is_expired_target = row in expired_records
                yongdo_badge = f"🏢[{row[12]}]" if str(row[12]) else "🏢[미상]"
                
                tag = "🔥 [폭파 매물 줍기!]" if is_expired_target else "🎯 타겟"
                st.markdown(f"**{tag} {yongdo_badge} {addr_str} {room_str}**")
                
                d_val = int(clean_numeric(row[18])) if clean_numeric(row[18]) else 0
                r_val = int(clean_numeric(row[19])) if clean_numeric(row[19]) else 0
                p_str = f"{d_val:,} / {r_val:,}" if r_val > 0 else f"{d_val:,}"
                
                st.info(f"**소유주:** {row[9]}({row[10]}) | **연락처:** {row[11]}\n\n**기존 보/월:** {p_str} | **종료일:** {row[21]}\n\n**히스토리:**\n{row[22]}")
                
                with st.form(f"call_update_{row[28]}"):
                    st.markdown("**📝 통화 결과 입력** (* 표시 항목은 필수입니다)")
                    c_in1, c_in2, c_in3, c_in4, c_in5 = st.columns([1.5, 1, 1, 2.5, 1.3])
                    new_mangi = c_in1.text_input("계약종료일*", key=f"m_{row[28]}", placeholder="0000.00.00", label_visibility="collapsed")
                    new_dep = c_in2.text_input("보증금", key=f"d_{row[28]}", placeholder="보증금", label_visibility="collapsed")
                    new_rent = c_in3.text_input("월세", key=f"r_{row[28]}", placeholder="월세", label_visibility="collapsed")
                    new_memo = c_in4.text_input("피드*", key=f"f_{row[28]}", placeholder="피드(통화결과) 입력", label_visibility="collapsed")
                    
                    if c_in5.form_submit_button("✅ 내용저장(+1)", use_container_width=True):
                        if not new_mangi or not new_memo:
                            st.error("🚨 계약종료일과 피드는 필수 입력입니다!")
                        elif not is_valid_date(new_mangi):
                            st.error("🚨 계약종료일은 'YYYY.MM.DD' 또는 '0000.00.00' 양식으로 정확히 적어주세요!")
                        else:
                            now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
                            old_memo = str(row[22]).strip()
                            updated_memo = f"{old_memo}\n👉 [{now_str[:10][2:].replace('-','.')}] {new_memo}".strip() if old_memo else f"👉 [{now_str[:10][2:].replace('-','.')}] {new_memo}"
                            
                            ws_data.update_cell(row[28], 22, new_mangi)
                            ws_data.update_cell(row[28], 23, updated_memo) 
                            ws_data.update_cell(row[28], 24, now_str) 
                            ws_data.update_cell(row[28], 25, user_name) 
                            
                            if new_dep: ws_data.update_cell(row[28], 18, new_dep)
                            if new_rent: ws_data.update_cell(row[28], 19, new_rent)
                            
                            if not has_vip: ws_staff.update_cell(staff_row_index, 8, quota_done + 1)
                            update_token(user_name, 1, f"오피콜 완료 ({addr_str})")
                            st.cache_data.clear(); st.rerun()

                if st.button("⏭️ 부재중 / 다음기회에", key=f"pass_{row[28]}"):
                    ws_data.update_cell(row[28], 24, (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S'))
                    ws_data.update_cell(row[28], 25, user_name) 
                    if not has_vip: ws_staff.update_cell(staff_row_index, 8, quota_done + 1)
                    st.cache_data.clear(); st.rerun()
                st.write("---")

# ==========================================
# 탭 6: 📝 신규 등록
# ==========================================
elif selected_tab == "📝 신규 등록":
    ws_data = ss.get_worksheet_by_id(1969836502)
    st.title("📝 신규 등록 (완료 시 +3 토큰 / +5점)")
    st.write("새로운 소유주 및 매물 DB를 등록하는 공간입니다. (매물방 노출과는 별개입니다)")
    
    with st.form("add_new_db_form", clear_on_submit=True):
        c_r1, c_r2, c_r3 = st.columns(3)
        n_city = c_r1.selectbox("시/도", list(KOREA_REGION_DATA.keys()), index=list(KOREA_REGION_DATA.keys()).index("서울특별시") if "서울특별시" in KOREA_REGION_DATA else 0)
        
        gu_opts = list(KOREA_REGION_DATA[n_city].keys())
        if "➕직접 입력" not in gu_opts: gu_opts.append("➕직접 입력")
        n_gu_sel = c_r2.selectbox("시/군/구", gu_opts, index=gu_opts.index("송파구") if "송파구" in gu_opts else 0)
        n_gu = st.text_input("시/군/구 직접 입력") if n_gu_sel == "➕직접 입력" else n_gu_sel
        
        dong_opts = KOREA_REGION_DATA[n_city].get(n_gu, []) + ["➕직접 입력"]
        n_dong_sel = c_r3.selectbox("법정동", dong_opts, index=dong_opts.index("방이동") if "방이동" in dong_opts else 0)
        n_dong = st.text_input("법정동 직접 입력") if n_dong_sel == "➕직접 입력" else n_dong_sel
        
        st.write("---")
        c_n1, c_n2, c_n3, c_n4 = st.columns(4)
        n_bon = c_n1.text_input("본번 (필수)", placeholder="28")
        n_bu = c_n2.text_input("부번 (없으면 0)", value="0")
        n_room = c_n3.text_input("호실 (숫자만)", placeholder="101")
        n_btype = c_n4.selectbox("용도 (필수)", ["아파트", "오피스텔", "빌라", "상가", "다세대", "다가구", "기타"])
        
        c_o1, c_o2, c_o3 = st.columns(3)
        o_name = c_o1.text_input("임대인 성함 (필수)")
        o_birth = c_o2.text_input("생년월일 (숫자만)", placeholder="940101")
        o_phone = c_o3.text_input("연락처 (숫자만)", placeholder="01012345678")
        
        c_p1, c_p2, c_p3 = st.columns(3)
        n_dep = c_p1.text_input("보증금 (0원 단위. 예: 10000000)")
        n_rent = c_p2.text_input("월세 (0원 단위)")
        n_mangi = c_p3.text_input("만기일 (필수 YYYY.MM.DD)", placeholder="2026.04.00")
        
        n_memo = st.text_area("특이사항", placeholder="예: 애완가능, 주차가능 등")
        
        if st.form_submit_button("💾 데이터 등록", type="primary"):
            if not n_bon or not o_name or not n_mangi:
                st.error("🚨 필수 항목(본번, 임대인 성함, 만기일)을 모두 입력해주세요!")
            else:
                now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
                final_memo = f"👉 [{now_str[:10][2:].replace('-','.')}] 신규등록: {n_memo}".strip() if n_memo else f"👉 [{now_str[:10][2:].replace('-','.')}] 신규등록"
                
                new_row = [""] * 28
                new_row[0], new_row[1], new_row[2], new_row[3], new_row[4] = n_city, n_gu, n_dong, n_bon, n_bu
                new_row[6], new_row[7], new_row[8] = "", "동없음", n_room
                
                new_row[9] = o_name
                new_row[10] = f"'{o_birth}" if o_birth else ""
                new_row[11] = f"'{o_phone}" if o_phone else ""
                
                new_row[12], new_row[18], new_row[19] = n_btype, n_dep, n_rent
                new_row[21], new_row[22], new_row[23], new_row[24], new_row[25] = n_mangi, final_memo, now_str, user_name, "정상"
                
                ws_data.append_row(new_row, value_input_option='USER_ENTERED')
                
                update_token(user_name, 3, f"신규 매물 등록 ({n_btype})")
                
                st.cache_data.clear()
                st.success("🎉 신규 DB 등록이 완료되었습니다! (+3 토큰)")
                st.rerun()
