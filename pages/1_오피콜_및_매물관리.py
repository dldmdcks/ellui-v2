import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
import json
import re
from datetime import datetime, timedelta

if "connected" not in st.session_state or not st.session_state.connected:
    st.switch_page("app.py")

st.set_page_config(page_title="오피콜 및 매물관리", page_icon="🔍", layout="wide")
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-size: 14px !important; }
        .stButton>button { padding: 0.2rem 0.5rem; min-height: 2rem; }
        .block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
        div[role="radiogroup"] { flex-direction: row; gap: 15px; padding-bottom: 15px; border-bottom: 2px solid #f0f2f6; margin-bottom: 20px; }
        .locked-tab { text-align: center; padding: 50px; background-color: #f8f9fa; border-radius: 10px; border: 2px dashed #ff4b4b; margin-top: 20px;}
    </style>
""", unsafe_allow_html=True)

ADMIN_EMAILS = ["dldmdcks94@gmail.com", "ktg3582@gmail.com"]

# (전국 주소 데이터가 깁니다. 지우지 말고 그대로 쓰세요!)
KOREA_REGION_DATA = {
    "서울특별시": {
        "강남구": ["개포동", "논현동", "대치동", "도곡동", "삼성동", "세곡동", "수서동", "신사동", "압구정동", "역삼동", "율현동", "일원동", "자곡동", "청담동"],
        "강동구": ["강일동", "고덕동", "길동", "둔촌동", "명일동", "상일동", "성내동", "암사동", "천호동"],
        "송파구": ["가락동", "거여동", "마천동", "문정동", "방이동", "삼전동", "석촌동", "송파동", "신천동", "오금동", "잠실동", "장지동", "풍납동"],
        "서초구": ["내곡동", "반포동", "방배동", "서초동", "신원동", "양재동", "염곡동", "우면동", "원지동", "잠원동"],
        "강서구": ["가양동", "개화동", "공항동", "과해동", "내발산동", "등촌동", "마곡동", "방화동", "염창동", "오곡동", "오쇠동", "외발산동", "화곡동"],
        "관악구": ["남현동", "봉천동", "신림동"],
        "광진구": ["광장동", "구의동", "군자동", "능동", "자양동", "중곡동", "화양동"],
        "동대문구": ["답십리동", "신설동", "용두동", "이문동", "장안동", "전농동", "제기동", "청량리동", "회기동", "휘경동"],
        "마포구": ["공덕동", "구수동", "노고산동", "당인동", "대흥동", "도화동", "마포동", "망원동", "상수동", "상암동", "서교동", "성산동", "신공덕동", "신수동", "신정동", "아현동", "연남동", "염리동", "용강동", "중동", "창전동", "토정동", "하중동", "합정동", "현석동"],
        "성동구": ["금호동1가", "금호동2가", "금호동3가", "금호동4가", "도선동", "마장동", "사근동", "상왕십리동", "성수동1가", "성수동2가", "송정동", "옥수동", "용답동", "응봉동", "하왕십리동", "행당동", "홍익동"],
        "용산구": ["갈월동", "남영동", "도원동", "동빙고동", "동자동", "문배동", "보광동", "산천동", "서계동", "서빙고동", "신계동", "신창동", "용문동", "용산동1가", "용산동2가", "용산동3가", "용산동4가", "용산동5가", "용산동6가", "원효로1가", "원효로2가", "원효로3가", "원효로4가", "이촌동", "이태원동", "주성동", "청파동1가", "청파동2가", "청파동3가", "한강로1가", "한강로2가", "한강로3가", "한남동", "효창동", "후암동"],
        "영등포구": ["당산동", "당산동1가", "당산동2가", "당산동3가", "당산동4가", "당산동5가", "당산동6가", "대림동", "도림동", "문래동1가", "문래동2가", "문래동3가", "문래동4가", "문래동5가", "문래동6가", "신길동", "양평동", "양평동1가", "양평동2가", "양평동3가", "양평동4가", "양평동5가", "양평동6가", "양화동", "여의도동", "영등포동", "영등포동1가", "영등포동2가", "영등포동3가", "영등포동4가", "영등포동5가", "영등포동6가", "영등포동7가", "영등포동8가"],
        "종로구": ["가회동", "견지동", "경운동", "공평동", "관수동", "관철동", "관훈동", "교남동", "교북동", "구기동", "궁정동", "권농동", "낙원동", "내수동", "내자동", "누상동", "누하동", "당주동", "도렴동", "돈의동", "동숭동", "명륜1가", "명륜2가", "명륜3가", "명륜4가", "묘동", "무악동", "봉익동", "부암동", "사직동", "삼청동", "서린동", "세종로", "소격동", "송월동", "송현동", "수송동", "숭인동", "신교동", "신문로1가", "신문로2가", "신영동", "안국동", "연건동", "연지동", "예지동", "옥인동", "와룡동", "운니동", "원남동", "원서동", "이화동", "익선동", "인사동", "인의동", "장사동", "재동", "적선동", "종로1가", "종로2가", "종로3가", "종로4가", "종로5가", "종로6가", "중학동", "창성동", "창신동", "청운동", "청진동", "체부동", "충신동", "통의동", "통인동", "팔판동", "평동", "평창동", "필운동", "행촌동", "혜화동", "홍지동", "홍파동", "화동", "효자동", "효제동", "훈정동"],
        "중구": ["광희동1가", "광희동2가", "남대문로1가", "남대문로2가", "남대문로3가", "남대문로4가", "남대문로5가", "남산동1가", "남산동2가", "남산동3가", "남창동", "남학동", "다동", "만리동1가", "만리동2가", "명동1가", "명동2가", "무교동", "무학동", "묵정동", "방산동", "봉래동1가", "봉래동2가", "북창동", "산림동", "삼각동", "서소문동", "소공동", "수표동", "수하동", "순화동", "신당동", "쌍림동", "예관동", "예장동", "오장동", "을지로1가", "을지로2가", "을지로3가", "을지로4가", "을지로5가", "을지로6가", "을지로7가", "인현동1가", "인현동2가", "입정동", "장교동", "장충동1가", "장충동2가", "저동1가", "저동2가", "정동", "주교동", "주자동", "중림동", "초동", "충무로1가", "충무로2가", "충무로3가", "충무로4가", "충무로5가", "태평로1가", "태평로2가", "필동1가", "필동2가", "필동3가", "황학동", "회현동1가", "회현동2가", "회현동3가", "흥인동"],
    },
    "경기도": {
        "하남시": ["감북동", "감이동", "감일동", "광암동", "교산동", "덕풍동", "망월동", "미사동", "배알미동", "상사창동", "상산곡동", "선동", "신장동", "창우동", "천현동", "초이동", "초일동", "춘궁동", "풍산동", "하사창동", "하산곡동", "학암동", "항동"],
        "성남시 수정구": ["고등동", "금토동", "단대동", "둔전동", "복정동", "사송동", "산성동", "상적동", "수진동", "시흥동", "신촌동", "신흥동", "양지동", "오야동", "창곡동", "태평동"],
        "성남시 분당구": ["구미동", "궁내동", "금곡동", "대장동", "동원동", "백현동", "분당동", "삼평동", "서현동", "석운동", "수내동", "야탑동", "운중동", "율동", "이매동", "정자동", "판교동", "하산운동"],
        "수원시 팔달구": ["고등동", "교동", "구천동", "남수동", "남창동", "매교동", "매산로1가", "매산로2가", "매산로3가", "매향동", "북수동", "신풍동", "영동", "우만동", "인계동", "장안동", "중동", "지동", "팔달로1가", "팔달로2가", "팔달로3가", "화서동"],
    },
    "인천광역시": {
        "연수구": ["동춘동", "선학동", "송도동", "연수동", "옥련동", "청학동"],
        "부평구": ["갈산동", "구산동", "부개동", "부평동", "산곡동", "삼산동", "십정동", "일신동", "청천동"],
    }
}

token_dict = json.loads(st.secrets["google_token_json"])
@st.cache_resource
def get_ss(): return gspread.authorize(Credentials.from_authorized_user_info(token_dict)).open_by_key('121-C5OIQpOnTtDbgSLgiq_Qdf5WoHhhIpNkRCWy5hKA')
ss = get_ss()
ws_data = ss.get_worksheet_by_id(1969836502)
try: ws_staff = ss.worksheet("직원명단")
except: pass
try: ws_history = ss.worksheet("토큰내역")
except: pass
try: ws_settings = ss.worksheet("환경설정")
except: pass

@st.cache_data(ttl=30)
def fetch_all_data(): return ws_data.get_all_values(), ws_staff.get_all_records(), ws_history.get_all_values(), ws_settings.get_all_values()
all_data_raw, staff_records, history_all_values, settings_all_values = fetch_all_data()

staff_dict = {str(r['이메일']).strip(): r for r in staff_records}
user_email = st.session_state.user_info.get("email", "")

now_kst = datetime.utcnow() + timedelta(hours=9)
today_shift = now_kst.strftime("%Y-%m-%d") if now_kst.hour >= 8 else (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")

# 권한 및 할당량 로직
if user_email in staff_dict:
    user_name = staff_dict[user_email]['이름']
    user_tokens = int(staff_dict[user_email].get('보유토큰', 0))
    staff_row_index = list(staff_dict.keys()).index(user_email) + 2 
    quota_done = int(staff_dict[user_email].get('할당진행도', 0)) if str(staff_dict[user_email].get('할당진행도', '')).isdigit() else 0
    if str(staff_dict[user_email].get('최근할당일', '')) != today_shift:
        ws_staff.update_cell(staff_row_index, 7, today_shift); ws_staff.update_cell(staff_row_index, 8, 0)
        quota_done = 0; st.cache_data.clear()
    has_vip = (str(staff_dict[user_email].get('VIP권한', 'X')) == 'O')
    is_locked = False if has_vip else (quota_done < 5) # VIP는 락 해제
elif user_email in ADMIN_EMAILS:
    user_name = "관리자 (대표)"
    user_tokens, is_locked, has_vip, quota_done = 9999, False, True, 5
else:
    st.error("승인되지 않은 계정입니다."); st.stop()

history_records = history_all_values[1:]
MANAGER_BUILDINGS = {b.strip(): r['이름'] for r in staff_records for b in str(r.get('관리건물', '')).split(',') if b.strip()}
try: target_addresses = [a.strip().replace(" ", "") for a in (settings_all_values[1][1] if len(settings_all_values)>1 else "").split(",") if a.strip()]
except: target_addresses = []

def clean_numeric(t): return re.sub(r'[^0-9]', '', str(t))
def is_valid_date(d): return bool(re.match(r'^\d{4}\.\d{2}\.\d{2}$', str(d).strip()))
def update_token(t_name, amt, reason):
    if "대표" in t_name or "관리자" in t_name: return
    for i, r in enumerate(staff_records):
        if r['이름'] == t_name:
            ws_staff.update_cell(i + 2, 4, int(r.get('보유토큰', 0)) + amt)
            ws_history.append_row([(datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S'), t_name, amt, int(r.get('보유토큰', 0)) + amt, reason], value_input_option='USER_ENTERED')
            break

def is_unlocked_recently(addr, room):
    if has_vip or user_email in ADMIN_EMAILS: return True
    search_str = f"({addr} {room})"
    for r in reversed(history_records):
        if len(r) > 4 and r[1] == user_name and search_str in r[4] and str(r[2]) == "-1":
            try:
                if (datetime.now() - datetime.strptime(r[0].replace("'", ""), '%Y-%m-%d %H:%M:%S')).total_seconds() <= 86400: return True
            except: continue
    return False

# 데이터 전처리
temp_dict = {}
for i, r in enumerate(all_data_raw[1:]):
    if not has_vip and (r[25].strip() if len(r)>25 else "정상") in ["비공개", "삭제", "잘못됨"]: continue
    rp = (r + [""]*26)[:26] + [i + 2]
    temp_dict[(str(rp[2]).replace(" ",""), str(rp[3]), str(rp[4]), str(rp[7]), str(rp[8]), str(rp[9]), str(rp[10]))] = rp 
all_records = list(temp_dict.values()); all_records.reverse()

st.sidebar.markdown(f"### 👤 {user_name}")
st.sidebar.markdown(f"**보유 토큰:** `{user_tokens} 개`")

tab_names = ["🔍 매물검색", "👤 소유주검색", "📞 오늘의 오피콜", "📝 신규등록"]
if has_vip: tab_names.append("⏰ VIP만기")
selected_tab = st.radio("메뉴", tab_names, horizontal=True, label_visibility="collapsed")

def render_edit_form(row_idx, city, gu, dong, bon, bu, road, bldg, d_dong, room, name, birth, phone, b_type, appr_date, viol, land_area, room_area, curr_biz, deposit, rent, fee, end_date, memo, addr_str, room_str, form_key, reward_reason, reward_amount):
    with st.form(f"edit_{form_key}", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        new_btype = c1.selectbox("용도", ["아파트", "오피스텔", "다세대", "다가구", "빌라", "상가", "미분류"], index=["아파트", "오피스텔", "다세대", "다가구", "빌라", "상가", "미분류"].index(b_type) if b_type in ["아파트", "오피스텔", "다세대", "다가구", "빌라", "상가", "미분류"] else 0)
        new_deposit, new_rent, new_end = c2.text_input("보증금", value=str(deposit)), c3.text_input("월세", value=str(rent)), c4.text_input("만기일", value=str(end_date), placeholder="2026.04.00")
        new_memo_add = st.text_input("추가 특이사항")
        if st.form_submit_button(f"🛠️ 데이터 갱신 (+{reward_amount} 토큰)"):
            if not new_end or not is_valid_date(new_end): st.error("🚨 만기일 YYYY.MM.DD 확인!"); return False
            now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
            ws_data.update_cell(row_idx, 26, "비공개")
            added_log = f"[{now_str[:10][2:].replace('-','.')}] 보/월 {new_deposit}/{new_rent} 만기 {new_end}"
            new_full_memo = f"{memo}\n👉 {added_log} {new_memo_add}".strip() if memo else f"👉 {added_log} {new_memo_add}"
            ws_data.append_row([city, gu, dong, bon, bu, road, bldg, d_dong, room, name, birth, phone, new_btype, appr_date, viol, land_area, room_area, curr_biz, new_deposit, new_rent, fee, new_end, new_full_memo, now_str, user_name, "정상"], value_input_option='USER_ENTERED')
            update_token(user_name, reward_amount, f"{reward_reason} ({addr_str} {room_str})")
            st.cache_data.clear(); st.success("✅ 갱신 완료!"); st.rerun()

if selected_tab == "🔍 매물검색":
    if is_locked: st.markdown(f"<div class='locked-tab'><h2>🔒 오늘 할당량을 먼저 완수해주세요!</h2><p>할당량({quota_done}/5건) 완료 시 해제</p></div>", unsafe_allow_html=True)
    else:
        c_s1, c_s2, c_s3 = st.columns(3)
        sel_sido = c_s1.selectbox("시/도", ["전체"] + list(KOREA_REGION_DATA.keys()), index=1)
        gu_opts = ["전체"] + list(KOREA_REGION_DATA[sel_sido].keys()) if sel_sido != "전체" else ["전체"]
        sel_sigungu = c_s2.selectbox("시/군/구", gu_opts, index=gu_opts.index("송파구") if "송파구" in gu_opts else 0)
        sel_dong = c_s3.selectbox("법정동", ["전체"] + (KOREA_REGION_DATA[sel_sido][sel_sigungu] if sel_sigungu != "전체" and sel_sido != "전체" else []), index=0)
        
        with st.form("search_addr_form"):
            c_f1, c_f2 = st.columns([2, 1])
            b_search = c_f1.text_input("번지/건물명", placeholder="28-2")
            r_search = c_f2.text_input("호실", placeholder="101")
            if st.form_submit_button("🔍 검색", type="primary", use_container_width=True):
                st.session_state.addr_search_res = sorted([r for r in all_records if (sel_sido=="전체" or sel_sido==str(r[0]).strip()) and (sel_sigungu=="전체" or sel_sigungu==str(r[1]).strip()) and (sel_dong=="전체" or sel_dong==str(r[2]).strip()) and (not b_search or b_search.replace(" ","") in ((f"{r[3]}-{r[4]}" if str(r[4])!="0" else str(r[3]))+str(r[6])).replace(" ","")) and (not r_search or r_search.replace(" ","") in (str(r[7])+str(r[8])).replace(" ",""))], key=lambda x: int(clean_numeric(x[8])) if clean_numeric(x[8]) else 9999)
        
        if st.session_state.get("addr_search_res"):
            st.caption(f"검색 결과: {len(st.session_state.addr_search_res)}건")
            for idx, row in enumerate(st.session_state.addr_search_res):
                addr_str = f"{row[0]} {row[1]} {row[2]} {row[3]}" + (f"-{row[4]}" if row[4] and row[4] != "0" else "") + (f" {row[6]}" if row[6] else "")
                room_str = f"{row[7]} {row[8]}" if row[7] and row[7] != "동없음" else f"{row[8]}"
                m_name = next((m for b, m in MANAGER_BUILDINGS.items() if f" {b} " in f" {addr_str} "), None)
                st.markdown(f"**📍 {addr_str} | {room_str}**" + (f" | 👑 {m_name} 관리" if m_name else ""))
                if m_name and m_name != user_name and not has_vip: st.error(f"🔒 전담 매물"); st.write("---"); continue

                uk, tk = f"unlock_addr_{addr_str}_{room_str}", f"toggle_addr_{idx}"
                if is_unlocked_recently(addr_str, room_str) or st.session_state.get(uk, False):
                    if st.button("🔓 닫기/열기", key=f"btn_re_{idx}"): st.session_state[tk] = not st.session_state.get(tk, False)
                    if st.session_state.get(tk, False):
                        st.info(f"**소유주:** {row[9]}({row[10]}) | **연락처:** {row[11]}\n\n**보/월:** {row[18]}/{row[19]} | **만기:** {row[21]}\n\n**히스토리:**\n{row[22]}")
                        render_edit_form(row[26], row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20], row[21], row[22], addr_str, room_str, f"addr_upd_{idx}", "검색 갱신", 2)
                else:
                    if st.button("🔓 열람 (-1토큰)", key=f"btn_addr_{idx}"):
                        if user_tokens >= 1 or has_vip: update_token(user_name, -1, f"매물 열람 ({addr_str})"); st.session_state[uk] = True; st.session_state[tk] = True; st.cache_data.clear(); st.rerun()
                        else: st.error("토큰 부족")
                st.write("---")

elif selected_tab == "👤 소유주검색":
    if is_locked: st.markdown(f"<div class='locked-tab'><h2>🔒 오늘 할당량을 먼저 완수해주세요!</h2></div>", unsafe_allow_html=True)
    else:
        with st.form("search_owner_form"):
            c_o1, c_o2 = st.columns(2)
            sn, sb = c_o1.text_input("성함"), c_o2.text_input("생년월일(6자리)")
            if st.form_submit_button("소유주 검색", type="primary", use_container_width=True):
                st.session_state.owner_search_res = sorted([r for r in all_records if (sn in str(r[9])) and (not sb or sb == str(r[10]))], key=lambda x: int(clean_numeric(x[8])) if clean_numeric(x[8]) else 9999)
        if st.session_state.get("owner_search_res"):
            for idx, row in enumerate(st.session_state.owner_search_res):
                addr_str = f"{row[0]} {row[1]} {row[2]} {row[3]}" + (f"-{row[4]}" if row[4] and row[4] != "0" else "")
                room_str = f"{row[7]} {row[8]}" if row[7] and row[7] != "동없음" else f"{row[8]}"
                st.markdown(f"**👤 {row[9]}({row[10]}) | 📍 {addr_str} {room_str}**")
                uk, tk = f"unlock_own_{addr_str}_{room_str}", f"toggle_own_{idx}"
                if is_unlocked_recently(addr_str, room_str) or st.session_state.get(uk, False):
                    if st.button("🔓 닫기/열기", key=f"btn_re_own_{idx}"): st.session_state[tk] = not st.session_state.get(tk, False)
                    if st.session_state.get(tk, False):
                        st.info(f"**연락처:** {row[11]} | **만기/보/월:** {row[21]} / {row[18]} / {row[19]}\n\n**히스토리:**\n{row[22]}")
                        render_edit_form(row[26], row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20], row[21], row[22], addr_str, room_str, f"own_upd_{idx}", "소유주 갱신", 2)
                else:
                    if st.button("🔓 열람 (-1토큰)", key=f"btn_own_{idx}"):
                        if user_tokens >= 1 or has_vip: update_token(user_name, -1, f"소유주 열람 ({addr_str})"); st.session_state[uk] = True; st.session_state[tk] = True; st.cache_data.clear(); st.rerun()
                        else: st.error("토큰 부족")
                st.write("---")

elif selected_tab == "📞 오늘의 오피콜":
    # 💡 [무한루프 버그 & VIP 면제 해결]
    if has_vip: 
        st.success("🎉 대표님/VIP 계정은 오피콜 의무 할당량이 면제됩니다! (매물 갱신용으로 자유롭게 이용 가능합니다)")
        quota_done = 5 
    else:
        st.subheader(f"📞 오늘의 오피콜 (진행도: {quota_done}/5)")

    if quota_done >= 5 and not has_vip: st.success("🎉 오늘의 오피콜을 모두 완료했습니다!")
    
    target_pool = [r for r in all_records if today_shift not in str(r[23]) and "연락처 없음" not in str(r[11]) and str(r[11]).strip() and next((True for ta in target_addresses if ta == (f"{r[2]}{r[3]}" + (f"-{r[4]}" if r[4] and r[4] != "0" else "")).replace(" ", "")), False)]
    target_pool.sort(key=lambda x: str(x[23])) 
    my_idx = sorted([r['이름'] for r in staff_records]).index(user_name) if user_name in [r['이름'] for r in staff_records] else 0
    
    # 여기서 정확히 5개만 고정으로 자름 (무한 리필 방지)
    items_to_show = 5 if has_vip else (5 - quota_done)
    my_assigned_pool = target_pool[(my_idx * 5) : (my_idx * 5) + items_to_show] 
    
    if not my_assigned_pool: st.success("🎉 배정된 타겟 명단이 모두 소진되었습니다!")
    else:
        for idx, row in enumerate(my_assigned_pool):
            addr_str = f"{row[0]} {row[1]} {row[2]} {row[3]}" + (f"-{row[4]}" if row[4] and row[4] != "0" else "")
            room_str = f"{row[7]} {row[8]}" if row[7] and row[7] != "동없음" else f"{row[8]}"
            st.markdown(f"**🎯 타겟: {addr_str} {room_str}**")
            st.info(f"**소유주:** {row[9]}({row[10]}) | **연락처:** {row[11]}\n\n**기존 보/월:** {row[18]}/{row[19]} | **만기:** {row[21]}\n\n**히스토리:**\n{row[22]}")
            if st.button("⏭️ 부재중/패스", key=f"pass_{row[26]}"):
                ws_data.update_cell(row[26], 24, (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')); ws_data.update_cell(row[26], 25, user_name) 
                if not has_vip: ws_staff.update_cell(staff_row_index, 8, quota_done + 1)
                st.cache_data.clear(); st.rerun()
            if render_edit_form(row[26], row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20], row[21], row[22], addr_str, room_str, f"task_upd_{idx}", "오피콜 갱신", 1):
                if not has_vip: ws_staff.update_cell(staff_row_index, 8, quota_done + 1)
                st.cache_data.clear(); st.rerun()
            st.write("---")

elif selected_tab == "📝 신규등록":
    st.subheader("📝 신규 등록 (+3 토큰)")
    with st.form("new_data_form", clear_on_submit=True):
        c_reg1, c_reg2, c_reg3 = st.columns(3)
        n_city = c_reg1.selectbox("시/도", list(KOREA_REGION_DATA.keys()), index=list(KOREA_REGION_DATA.keys()).index("서울특별시") if "서울특별시" in KOREA_REGION_DATA else 0)
        n_gu = c_reg2.selectbox("시/군/구", list(KOREA_REGION_DATA[n_city].keys()))
        n_dong = c_reg3.text_input("법정동 (필수)", placeholder="방이동")
        
        c_n1, c_n2, c_n3 = st.columns(3)
        n_bon, n_bu, n_room = c_n1.text_input("본번", placeholder="28"), c_n2.text_input("부번", placeholder="2"), c_n3.text_input("호실", placeholder="101")
        n_btype = c_n1.selectbox("용도", ["아파트", "오피스텔", "다세대", "다가구", "빌라", "상가"])
        n_dep, n_rent, n_end = c_n1.text_input("보증금", placeholder="10000000"), c_n2.text_input("월세", placeholder="1000000"), c_n3.text_input("만기일", placeholder="2026.04.00")
        c_n4, c_n5 = st.columns(2)
        n_name, n_phone = c_n4.text_input("임대인 성함"), c_n5.text_input("임대인 연락처")
        n_memo = st.text_area("특이사항")
        
        if st.form_submit_button("🚀 매물 등록하기 (+3 토큰)", type="primary"):
            if not n_dong or not n_bon or not n_room: st.error("필수 항목(동, 번지, 호수)을 입력하세요.")
            else:
                ws_data.append_row([n_city, n_gu, n_dong, n_bon, n_bu, "", "", "동없음", n_room, n_name, "", f"'{n_phone}", n_btype, "", "위반 없음", "", "", "", n_dep, n_rent, "", n_end, n_memo, (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S'), user_name, "정상"], value_input_option='USER_ENTERED')
                update_token(user_name, 3, f"신규 매물 등록 ({n_dong} {n_bon})"); st.cache_data.clear(); st.success("🎉 매물 등록 완료!"); st.rerun()

elif selected_tab == "⏰ VIP만기":
    st.subheader("⏰ VIP 만기일 임박 매물 조회")
    months_ahead = st.columns([1, 3])[0].number_input("조회 개월 수", min_value=1, max_value=24, value=3)
    if st.button("조회 시작"):
        t_date = datetime.now() + timedelta(days=30 * months_ahead)
        v_res = [r for r in all_records if str(r[21]).strip() and is_valid_date(str(r[21])) and datetime.now() <= datetime.strptime(str(r[21]).strip(), '%Y.%m.%d') <= t_date]
        if v_res:
            st.success(f"총 {len(v_res)}건의 만기 임박 매물이 있습니다.")
            for r in sorted(v_res, key=lambda x: str(x[21])): st.write(f"**만기:** {r[21]} | 📍 {r[5]} {r[6]}-{r[7]} {r[9]} | {r[9]}({r[10]}) {r[11]}")
        else: st.info("조건에 맞는 매물이 없습니다.")
