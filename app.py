import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import json
import requests
import re
import pandas as pd
import os
import math

st.set_page_config(page_title="엘루이 업무포털", page_icon="🏢", layout="wide")
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-size: 14px !important; }
        .stButton>button { padding: 0.2rem 0.5rem; min-height: 2rem; }
        .block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
        [data-testid="stSidebar"] { width: 280px !important; }
        div[role="radiogroup"] {
            flex-direction: row; gap: 15px; padding-bottom: 15px; border-bottom: 2px solid #f0f2f6; margin-bottom: 20px;
        }
        .locked-tab { text-align: center; padding: 50px; background-color: #f8f9fa; border-radius: 10px; border: 2px dashed #ff4b4b; margin-top: 20px;}
    </style>
""", unsafe_allow_html=True)

ADMIN_EMAILS = ["dldmdcks94@gmail.com", "ktg3582@gmail.com"]

KOREA_REGION_DATA = {
    "서울특별시": {
        "강남구": ["개포동", "논현동", "대치동", "도곡동", "삼성동", "세곡동", "수서동", "신사동", "압구정동", "역삼동", "율현동", "일원동", "자곡동", "청담동"],
        "강동구": ["강일동", "고덕동", "길동", "둔촌동", "명일동", "상일동", "성내동", "암사동", "천호동"],
        "송파구": ["가락동", "거여동", "마천동", "문정동", "방이동", "삼전동", "석촌동", "송파동", "신천동", "오금동", "잠실동", "장지동", "풍납동"],
    },
    "경기도": {"하남시": ["감일동", "위례동", "학암동"], "성남시": ["위례동", "창곡동"]},
}

try:
    creds_dict = json.loads(st.secrets["credentials_json"])
    token_dict = json.loads(st.secrets["google_token_json"])
    CLIENT_ID = creds_dict["web"]["client_id"]
    CLIENT_SECRET = creds_dict["web"]["client_secret"]
    REDIRECT_URI = creds_dict["web"]["redirect_uris"][0]
except: st.error("❌ 금고 설정(Secrets) 확인 요망!"); st.stop()

if not os.getenv("RENDER"):
    st.session_state.connected = True
    st.session_state.user_info = {"email": "dldmdcks94@gmail.com"}

if 'connected' not in st.session_state: st.session_state.connected = False

query_params = st.query_params
if "session_token" in query_params and not st.session_state.connected:
    access_token = query_params["session_token"]
    user_info = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"}).json()
    if "email" in user_info: st.session_state.connected, st.session_state.user_info = True, user_info

if "code" in query_params and not st.session_state.connected:
    res = requests.post("https://oauth2.googleapis.com/token", data={"code": query_params["code"], "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code"}).json()
    if "access_token" in res:
        st.session_state.connected = True
        st.session_state.user_info = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {res['access_token']}"}).json()
        st.query_params["session_token"] = res['access_token']
        st.rerun()

if not st.session_state.connected:
    st.warning("🔒 엘루이 매물관리 시스템입니다. 본인인증 후 이용해주세요.")
    st.link_button("🔵 Google 계정으로 로그인", f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=openid%20email%20profile&access_type=offline&prompt=select_account", type="primary", use_container_width=True)
    st.stop()

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
try: ws_contract = ss.worksheet("계약보고_DB")
except: pass

@st.cache_data(ttl=30)
def fetch_all_data(): return ws_data.get_all_values(), ws_staff.get_all_records(), ws_history.get_all_values(), ws_settings.get_all_values(), ws_contract.get_all_values()
all_data_raw, staff_records, history_all_values, settings_all_values, contract_all_values = fetch_all_data()

staff_dict = {str(r['이메일']).strip(): r for r in staff_records}
if st.session_state.user_info.get("email", "") not in ADMIN_EMAILS + list(staff_dict.keys()): st.error("⚠️ 승인되지 않은 계정입니다."); st.stop()

now_kst = datetime.utcnow() + timedelta(hours=9)
today_shift = now_kst.strftime("%Y-%m-%d") if now_kst.hour >= 8 else (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")
user_email = st.session_state.user_info.get("email", "")

if user_email in ADMIN_EMAILS:
    user_name, user_tokens, is_locked, has_vip, quota_done, my_ratio = "이응찬 대표" if user_email == "dldmdcks94@gmail.com" else "곽태근 대표", 9999, False, True, 5, 100
else:
    user_name = staff_dict[user_email]['이름']
    user_tokens, my_ratio = int(staff_dict[user_email].get('보유토큰', 0)), int(staff_dict[user_email].get('수수료비율', 60)) if str(staff_dict[user_email].get('수수료비율', '')).isdigit() else 60
    staff_row_index = list(staff_dict.keys()).index(user_email) + 2 
    quota_done = int(staff_dict[user_email].get('할당진행도', 0)) if str(staff_dict[user_email].get('할당진행도', '')).isdigit() else 0
    if str(staff_dict[user_email].get('최근할당일', '')) != today_shift:
        ws_staff.update_cell(staff_row_index, 7, today_shift); ws_staff.update_cell(staff_row_index, 8, 0)
        quota_done = 0; st.cache_data.clear()
    has_vip, is_locked = (str(staff_dict[user_email].get('VIP권한', 'X')) == 'O'), (quota_done < 5)

history_records, contract_records = history_all_values[1:], contract_all_values[1:] 
MANAGER_BUILDINGS = {b.strip(): r['이름'] for r in staff_records for b in str(r.get('관리건물', '')).split(',') if b.strip()}

def clean_numeric(text): return re.sub(r'[^0-9]', '', str(text))
def extract_room_number(room_str): return int(clean_numeric(room_str)) if clean_numeric(room_str) else 99999
def is_valid_date_format(date_str): return bool(re.match(r'^\d{4}\.\d{2}\.\d{2}$', str(date_str).strip()))
def update_token(t_name, amt, reason):
    if t_name in ["이응찬 대표", "곽태근 대표"]: return
    for i, r in enumerate(staff_records):
        if r['이름'] == t_name:
            ws_staff.update_cell(i + 2, 4, int(r.get('보유토큰', 0)) + amt)
            ws_history.append_row([(datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S'), t_name, amt, int(r.get('보유토큰', 0)) + amt, reason], value_input_option='USER_ENTERED')
            break
def is_unlocked_recently(addr, room):
    if user_email in ADMIN_EMAILS: return True
    search_str = f"({addr} {room})"
    for r in reversed(history_records):
        if len(r) > 4 and r[1] == user_name and search_str in r[4] and str(r[2]) == "-1":
            try:
                if (datetime.now() - datetime.strptime(r[0].replace("'", ""), '%Y-%m-%d %H:%M:%S')).total_seconds() <= 86400: return True
            except: continue
    return False

temp_dict = {}
for i, r in enumerate(all_data_raw[1:]):
    if user_email not in ADMIN_EMAILS and (r[25].strip() if len(r)>25 else "정상") in ["비공개", "삭제", "잘못됨"]: continue
    rp = (r + [""]*26)[:26] + [i + 2]
    temp_dict[(str(rp[2]).replace(" ",""), str(rp[3]), str(rp[4]), str(rp[7]), str(rp[8]), str(rp[9]), str(rp[10]))] = rp 
all_records = list(temp_dict.values()); all_records.reverse()

st.sidebar.markdown(f"### 👤 {user_name}")
st.sidebar.markdown(f"**보유 토큰:** `{user_tokens} 개`")
st.sidebar.markdown("<div style='font-size: 13px; color: #4a4a4a; margin-top: -5px;'><b style='color:#1E90FF'>[🪙 보유 토큰 안내]</b><br>👉 양타 결재 <b>+5</b><br>👉 단타/신규 <b>+3</b><br>👉 검색 갱신 <b>+2</b><br>👉 오피콜 갱신 <b>+1</b><br>👉 매물 열람 <b>-1</b></div>", unsafe_allow_html=True)
if st.sidebar.button("로그아웃"): st.query_params.clear(); st.session_state.clear(); st.rerun()

try: target_addresses = [a.strip().replace(" ", "") for a in (settings_all_values[1][1] if len(settings_all_values)>1 else "").split(",") if a.strip()]
except: target_addresses = []
try: notice_text = settings_all_values[2][1] if len(settings_all_values) > 2 else ""
except: notice_text = ""

tab_names = ["🏠 홈", "🔍 검색", "👤 소유주", "📞 오피콜", "📝 신규", "💰 내 정산"]
if has_vip or user_email in ADMIN_EMAILS: tab_names.append("⏰ VIP만기")
if user_email in ADMIN_EMAILS: tab_names.extend(["👑 대시보드", "⚙️ 설정"])

selected_tab = st.radio("메뉴", tab_names, horizontal=True, label_visibility="collapsed")

def render_edit_form(row_idx, city, gu, dong, bon, bu, road, bldg, d_dong, room, name, birth, phone, b_type, appr_date, viol, land_area, room_area, curr_biz, deposit, rent, fee, end_date, memo, addr_str, room_str, form_key, reward_reason, reward_amount):
    with st.form(f"edit_{form_key}", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        new_btype = c1.selectbox("용도", ["아파트", "오피스텔", "다세대", "다가구", "빌라", "상가", "미분류"], index=["아파트", "오피스텔", "다세대", "다가구", "빌라", "상가", "미분류"].index(b_type) if b_type in ["아파트", "오피스텔", "다세대", "다가구", "빌라", "상가", "미분류"] else 0)
        new_deposit, new_rent, new_end = c2.text_input("보증금", value=str(deposit)), c3.text_input("월세", value=str(rent)), c4.text_input("만기일", value=str(end_date), placeholder="2026.04.00")
        new_memo_add = st.text_input("추가 특이사항")
        if st.form_submit_button(f"🛠️ 데이터 갱신 (+{reward_amount} 토큰)"):
            if not new_end or not is_valid_date_format(new_end): st.error("🚨 만기일 YYYY.MM.DD 확인!"); return False
            now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
            ws_data.update_cell(row_idx, 26, "비공개")
            added_log = f"[{now_str[:10][2:].replace('-','.')}] "
            if str(deposit) != new_deposit or str(rent) != new_rent: added_log += f"보/월 {new_deposit}/{new_rent} 변경. "
            if str(end_date) != new_end: added_log += f"만기 {new_end}. "
            new_full_memo = f"{memo}\n👉 {added_log}{new_memo_add}".strip() if memo else f"👉 {added_log}{new_memo_add}"
            ws_data.append_row([city, gu, dong, bon, bu, road, bldg, d_dong, room, name, birth, phone, new_btype, appr_date, viol, land_area, room_area, curr_biz, new_deposit, new_rent, fee, new_end, new_full_memo, now_str, user_name, "정상"], value_input_option='USER_ENTERED')
            update_token(user_name, reward_amount, f"{reward_reason} ({addr_str} {room_str})")
            st.cache_data.clear(); st.success(f"✅ 반영 완료! (+{reward_amount})"); return True
    return False

if selected_tab == "🏠 홈":
    st.subheader("🏠 엘루이 업무 포털")
    if notice_text: st.info(f"📢 **[전체 공지사항]**\n\n{notice_text}")
    st.columns(3)[0].link_button("📊 오피콜 시트 (마스터)", "https://docs.google.com/spreadsheets/d/11WZhFnPPIduKVSy3UG0-L1BrXRdddCBhzQLZGMVBSXc/", use_container_width=True)

elif selected_tab == "🔍 검색":
    if is_locked: st.markdown(f"<div class='locked-tab'><h2>🔒 오늘 할당량을 먼저 완수해주세요!</h2><p>할당량({quota_done}/5건) 완료 시 해제</p></div>", unsafe_allow_html=True)
    else:
        c_s1, c_s2, c_s3 = st.columns(3)
        sel_sido = c_s1.selectbox("시/도", ["전체"] + list(KOREA_REGION_DATA.keys()), index=1)
        gu_opts = ["전체"] + list(KOREA_REGION_DATA[sel_sido].keys()) if sel_sido != "전체" else ["전체"]
        sel_sigungu = c_s2.selectbox("시/군/구", gu_opts, index=gu_opts.index("송파구") if "송파구" in gu_opts else 0)
        sel_dong = c_s3.selectbox("법정동", ["전체"] + KOREA_REGION_DATA[sel_sido][sel_sigungu] if sel_sigungu != "전체" and sel_sido != "전체" else ["전체"], index=(["전체"] + KOREA_REGION_DATA[sel_sido][sel_sigungu]).index("방이동") if sel_sigungu != "전체" and "방이동" in KOREA_REGION_DATA[sel_sido][sel_sigungu] else 0)
        
        with st.form("search_addr_form"):
            b_search, r_search = st.columns([2, 1])[0].text_input("번지/건물명", placeholder="28-2"), st.columns([2, 1])[1].text_input("호실", placeholder="101")
            if st.form_submit_button("🔍 검색", type="primary", use_container_width=True):
                st.session_state.addr_search_res = sorted([r for r in all_records if (sel_sido=="전체" or sel_sido==str(r[0]).strip()) and (sel_sigungu=="전체" or sel_sigungu==str(r[1]).strip()) and (sel_dong=="전체" or sel_dong==str(r[2]).strip()) and (not b_search or b_search.replace(" ","") in ((f"{r[3]}-{r[4]}" if str(r[4])!="0" else str(r[3]))+str(r[6])).replace(" ","")) and (not r_search or r_search.replace(" ","") in (str(r[7])+str(r[8])).replace(" ",""))], key=lambda x: extract_room_number(x[8]))
        if st.session_state.get("addr_search_res"):
            st.caption(f"검색 결과: {len(st.session_state.addr_search_res)}건")
            for idx, row in enumerate(st.session_state.addr_search_res):
                addr_str = f"{row[0]} {row[1]} {row[2]} {row[3]}" + (f"-{row[4]}" if row[4] and row[4] != "0" else "") + (f" {row[6]}" if row[6] else "")
                room_str = f"{row[7]} {row[8]}" if row[7] and row[7] != "동없음" else f"{row[8]}"
                m_name = next((m for b, m in MANAGER_BUILDINGS.items() if f" {b} " in f" {addr_str} "), None)
                st.markdown(f"**📍 {addr_str} | {room_str}**" + (f" | 👑 {m_name} 관리" if m_name else ""))
                if m_name and m_name != user_name and user_email not in ADMIN_EMAILS: st.error(f"🔒 전담 매물"); st.write("---"); continue

                uk, tk = f"unlock_addr_{addr_str}_{room_str}", f"toggle_addr_{idx}"
                if is_unlocked_recently(addr_str, room_str) or st.session_state.get(uk, False):
                    if st.button("🔓 닫기/열기", key=f"btn_re_{idx}"): st.session_state[tk] = not st.session_state.get(tk, False)
                    if st.session_state.get(tk, False):
                        if "🏅[엘루이 자체계약]" in str(row[22]): st.markdown("#### 🏅 엘루이 자체계약 매물 (협의 수월)")
                        st.info(f"**소유주:** {row[9]}({row[10]}) | **연락처:** {row[11]}\n\n**보/월:** {row[18]}/{row[19]} | **만기:** {row[21]}\n\n**히스토리:**\n{row[22]}")
                        if render_edit_form(row[26], row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20], row[21], row[22], addr_str, room_str, f"addr_upd_{idx}", "검색 갱신", 2): st.rerun()
                else:
                    if st.button("🔓 열람 (-1토큰)", key=f"btn_addr_{idx}"):
                        if user_tokens >= 1 or user_email in ADMIN_EMAILS: update_token(user_name, -1, f"매물 열람 ({addr_str} {room_str})"); st.session_state[uk] = True; st.session_state[tk] = True; st.cache_data.clear(); st.rerun()
                        else: st.error("토큰 부족")
                st.write("---")

elif selected_tab == "👤 소유주":
    if is_locked: st.markdown(f"<div class='locked-tab'><h2>🔒 오늘 할당량을 먼저 완수해주세요!</h2></div>", unsafe_allow_html=True)
    else:
        with st.form("search_owner_form"):
            sn, sb = st.columns(2)[0].text_input("성함"), st.columns(2)[1].text_input("생년월일(6자리)")
            if st.form_submit_button("소유주 검색", type="primary", use_container_width=True):
                st.session_state.owner_search_res = sorted([r for r in all_records if (sn in str(r[9])) and (not sb or sb == str(r[10]))], key=lambda x: extract_room_number(x[8]))
        if st.session_state.get("owner_search_res"):
            for idx, row in enumerate(st.session_state.owner_search_res):
                addr_str = f"{row[0]} {row[1]} {row[2]} {row[3]}" + (f"-{row[4]}" if row[4] and row[4] != "0" else "") + (f" {row[6]}" if row[6] else "")
                room_str = f"{row[7]} {row[8]}" if row[7] and row[7] != "동없음" else f"{row[8]}"
                st.markdown(f"**👤 {row[9]}({row[10]}) | 📍 {addr_str} {room_str}**")
                uk, tk = f"unlock_own_{addr_str}_{room_str}", f"toggle_own_{idx}"
                if is_unlocked_recently(addr_str, room_str) or st.session_state.get(uk, False):
                    if st.button("🔓 닫기/열기", key=f"btn_re_own_{idx}"): st.session_state[tk] = not st.session_state.get(tk, False)
                    if st.session_state.get(tk, False):
                        if "🏅[엘루이 자체계약]" in str(row[22]): st.markdown("#### 🏅 엘루이 자체계약 매물 (협의 수월)")
                        st.info(f"**연락처:** {row[11]} | **만기/보/월:** {row[21]} / {row[18]} / {row[19]}\n\n**히스토리:**\n{row[22]}")
                        if render_edit_form(row[26], row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20], row[21], row[22], addr_str, room_str, f"own_upd_{idx}", "소유주 갱신", 2): st.rerun()
                else:
                    if st.button("🔓 열람 (-1토큰)", key=f"btn_own_{idx}"):
                        if user_tokens >= 1 or user_email in ADMIN_EMAILS: update_token(user_name, -1, f"소유주 열람 ({addr_str} {room_str})"); st.session_state[uk] = True; st.session_state[tk] = True; st.cache_data.clear(); st.rerun()
                        else: st.error("토큰 부족")
                st.write("---")

elif selected_tab == "📞 오피콜":
    st.subheader(f"📞 오늘의 오피콜 (진행도: {quota_done}/5)")
    if quota_done >= 5: st.success("🎉 오늘의 오피콜을 모두 완료했습니다!")
    else:
        target_pool = [r for r in all_records if today_shift not in str(r[23]) and "연락처 없음" not in str(r[11]) and str(r[11]).strip() and next((True for ta in target_addresses if ta == (f"{r[2]}{r[3]}" + (f"-{r[4]}" if r[4] and r[4] != "0" else "")).replace(" ", "")), False)]
        target_pool.sort(key=lambda x: str(x[23])) 
        my_idx = sorted([r['이름'] for r in staff_records]).index(user_name) if user_name in [r['이름'] for r in staff_records] else 0
        my_assigned_pool = target_pool[(my_idx * 5) : (my_idx * 5) + (5 - quota_done)]
        if not my_assigned_pool: st.success("🎉 타겟 명단이 소진되었습니다!")
        else:
            for idx, row in enumerate(my_assigned_pool):
                addr_str = f"{row[0]} {row[1]} {row[2]} {row[3]}" + (f"-{row[4]}" if row[4] and row[4] != "0" else "")
                room_str = f"{row[7]} {row[8]}" if row[7] and row[7] != "동없음" else f"{row[8]}"
                st.markdown(f"**🎯 타겟: {addr_str} {room_str}**")
                st.info(f"**소유주:** {row[9]}({row[10]}) | **연락처:** {row[11]}\n\n**기존 보증/월세:** {row[18]}/{row[19]} | **만기:** {row[21]}\n\n**히스토리:**\n{row[22]}")
                if st.button("⏭️ 부재중/패스", key=f"pass_{row[26]}"):
                    ws_data.update_cell(row[26], 24, (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')); ws_data.update_cell(row[26], 25, user_name) 
                    if user_email not in ADMIN_EMAILS: ws_staff.update_cell(staff_row_index, 8, quota_done + 1)
                    st.cache_data.clear(); st.rerun()
                if render_edit_form(row[26], row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20], row[21], row[22], addr_str, room_str, f"task_upd_{idx}", "오피콜 갱신", 1):
                    if user_email not in ADMIN_EMAILS: ws_staff.update_cell(staff_row_index, 8, quota_done + 1)
                    st.cache_data.clear(); st.rerun()
                st.write("---")

elif selected_tab == "📝 신규":
    st.subheader("📝 외부 매물(공실클럽/네이버 등) 신규 등록 (+3 토큰)")
    with st.form("new_data_form", clear_on_submit=True):
        n_city, n_gu, n_dong = st.columns(3)[0].text_input("시/도", value="서울특별시"), st.columns(3)[1].text_input("시/군/구", value="송파구"), st.columns(3)[2].text_input("법정동", placeholder="방이동")
        n_bon, n_bu, n_room = st.columns(3)[0].text_input("본번", placeholder="28"), st.columns(3)[1].text_input("부번", placeholder="2"), st.columns(3)[2].text_input("호실", placeholder="101")
        n_dep, n_rent, n_end = st.columns(3)[0].text_input("보증금", placeholder="10000000"), st.columns(3)[1].text_input("월세", placeholder="1000000"), st.columns(3)[2].text_input("만기일", placeholder="2026.04.00")
        n_name, n_phone, n_memo = st.columns(2)[0].text_input("임대인 성함"), st.columns(2)[1].text_input("임대인 연락처"), st.text_area("특이사항")
        if st.form_submit_button("🚀 매물 등록하기 (+3 토큰)", type="primary"):
            if not n_dong or not n_bon or not n_room: st.error("필수 항목(동, 번지, 호수)을 입력하세요.")
            else:
                ws_data.append_row([n_city, n_gu, n_dong, n_bon, n_bu, "", "", "동없음", n_room, n_name, "", f"'{n_phone}", "미분류", "", "위반 없음", "", "", "", n_dep, n_rent, "", n_end, n_memo, (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S'), user_name, "정상"], value_input_option='USER_ENTERED')
                update_token(user_name, 3, f"신규 매물 등록 ({n_dong} {n_bon}-{n_bu})"); st.cache_data.clear(); st.success("🎉 매물 등록 완료! (+3 토큰)"); st.rerun()

# 💰 [탭 5] 내 정산 💰
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
            
            # 💡 [업데이트] 심플한 제목 (시뮬레이션 UI 삭제)
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
                
                # 💡 [업데이트] 증빙 타입 정확히 기록!
                if "요청완료" in str(rp[21]) or "발급완료" in str(rp[21]): st.success(f"✅ {rp[21]} 건입니다.")
                else:
                    st.write("---")
                    st.markdown("#### 🧾 증빙 자동 요청 (카카오워크 전송)")
                    with st.form(f"req_form_{idx}", clear_on_submit=True):
                        req_type = st.radio("발급 종류", ["세금계산서", "지출증빙", "현금영수증"], horizontal=True)
                        st.caption("※ 알맞게 빈칸을 채워주시면 단톡방에 예쁘게 전송됩니다.")
                        
                        r_c1, r_c2 = st.columns(2)
                        biz_name = r_c1.text_input("상호명 (현금영수증은 '이름' 입력)")
                        biz_ceo = r_c2.text_input("대표자 성함 (현금영수증은 비워두세요)")
                        biz_num = r_c1.text_input("사업자번호 (현금영수증은 '폰번호' 입력)")
                        biz_email = r_c2.text_input("이메일 (예: 필요없음)")
                        
                        if st.form_submit_button("🚀 대표님께 카톡 요청 쏘기"):
                            url = "https://kakaowork.com/bots/hook/4a5be71f2c424dfa8a6926ddfbd75ebe"
                            if req_type in ["세금계산서", "지출증빙"]:
                                msg = f"💌 [{req_type} 발행 요청]\n담당자 : {user_name}\n주소 : {c_addr} [{d_type}]\n금액 : {int(new_fee):,}원\n\n[🏢 사업자 정보]\n- 상호명 : {biz_name}\n- 대표자 : {biz_ceo}\n- 등록번호 : {biz_num}\n- 이메일 : {biz_email}"
                            else:
                                msg = f"💌 [현금영수증 발행 요청]\n담당자 : {user_name}\n주소 : {c_addr} [{d_type}]\n금액 : {int(new_fee):,}원\n\n[👤 발급 정보]\n- 이름 : {biz_name}\n- 번호 : {biz_num}"
                            try:
                                res = requests.post(url, json={"text": msg})
                                if res.status_code == 200:
                                    ws_contract.update_cell(len(contract_all_values) - idx, 22, f"{req_type} 요청완료") # 정확한 타입 명시!
                                    st.session_state[exp_key] = True
                                    st.cache_data.clear(); st.rerun()
                                else: st.error(f"⚠️ 앗! 카카오워크 전송에 실패했습니다. (코드: {res.status_code}) 내용: {res.text}")
                            except Exception as e: st.error(f"⚠️ 카카오워크 서버와 통신 에러가 발생했습니다: {e}")

# --- VIP 만기 ---
elif selected_tab == "⏰ VIP만기":
    st.subheader("⏰ VIP 만기일 임박 매물 조회")
    months_ahead = st.columns([1, 3])[0].number_input("조회 개월 수", min_value=1, max_value=24, value=3)
    if st.button("조회 시작"):
        t_date = datetime.now() + timedelta(days=30 * months_ahead)
        v_res = [r for r in all_records if str(r[21]).strip() and is_valid_date_format(str(r[21])) and datetime.now() <= datetime.strptime(str(r[21]).strip(), '%Y.%m.%d') <= t_date]
        if v_res:
            st.success(f"총 {len(v_res)}건의 만기 임박 매물이 있습니다.")
            for r in sorted(v_res, key=lambda x: str(x[21])): st.write(f"**만기:** {r[21]} | 📍 {r[5]} {r[6]}-{r[7]} {r[9]} | {r[9]}({r[10]}) {r[11]}")
        else: st.info("조건에 맞는 매물이 없습니다.")

# 👑 [탭 7] 통합 정산 대시보드 👑
elif selected_tab == "👑 대시보드":
    st.subheader("👑 엘루이 전사 정산 및 매출 대시보드")
    hide_completed = st.checkbox("☑️ 급여 지급 완료(🔴)된 내역 숨기기", value=True)
    
    calc_data = []
    for i, row in enumerate(contract_records):
        if len(row) < 19: continue
        rp = (row + [""]*27)[:27] # 💡 매물종류(AA열)까지 읽기 위해 27로 확장!
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
            
        # 💡 [업데이트] 줄번호 데이터는 있지만 화면에는 안 보이게 처리 (column_config 이용)
        b_type_str = str(rp[26]) if str(rp[26]) else "미입력"
        deposit_str = f"{int(re.sub(r'[^0-9]', '', str(rp[10]))):,}원" if re.sub(r'[^0-9]', '', str(rp[10])) else "0원"
        rent_str = f"{int(re.sub(r'[^0-9]', '', str(rp[11]))):,}원" if re.sub(r'[^0-9]', '', str(rp[11])) else "0원"
        
        calc_data.append([i + 2, str(rp[0])[:10], str(rp[1]), str(rp[2]), deposit_str, rent_str, b_type_str, f"{fee:,}원", str(rp[25]), pmethod, f"{final_pay:,}원", f"{comp_profit:,}원", f"{vat:,}원", f"{tax_33:,}원", str(rp[22]) == "O", str(rp[23]) == "O"])
        
    edited_df = st.data_editor(
        pd.DataFrame(calc_data, columns=["줄번호", "계약일", "담당직원", "구분", "보증금", "월세", "매물종류", "총입금액", "입금자명", "수단", "직원급여", "회사수익", "부가세", "소득세", "회사입금(체크)", "직원지급(체크)"]), 
        column_config={
            "줄번호": None, # 💡 줄번호 숨기기 마법!
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

elif selected_tab == "⚙️ 설정":
    st.subheader("⚙️ 관리자 환경설정")
    st.info("시트에서 직접 수정하셔도 됩니다.")