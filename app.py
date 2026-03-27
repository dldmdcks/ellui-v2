import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
import json
import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="엘루이 업무포털", page_icon="🏢", layout="wide")
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-size: 14px !important; }
        .stButton>button { padding: 0.2rem 0.5rem; min-height: 2rem; }
        .block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
        [data-testid="stSidebarNav"] { display: none !important; }
        [data-testid="stSidebar"] { width: 280px !important; display: block !important; }
    </style>
""", unsafe_allow_html=True)

ADMIN_EMAILS = ["dldmdcks94@gmail.com", "ktg3582@gmail.com"]

# 2. 구글 로그인 및 보안
try:
    creds_dict = json.loads(st.secrets["credentials_json"])
    token_dict = json.loads(st.secrets["google_token_json"])
    CLIENT_ID = creds_dict["web"]["client_id"]
    CLIENT_SECRET = creds_dict["web"]["client_secret"]
    REDIRECT_URI = creds_dict["web"]["redirect_uris"][0]
except: st.error("❌ 금고 설정(Secrets) 확인 요망!"); st.stop()

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
    st.warning("🔒 엘루이 매물관리 시스템입니다. 구글 계정으로 본인인증 후 이용해주세요.")
    st.link_button("🔵 Google 계정으로 로그인", f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=openid%20email%20profile&access_type=offline&prompt=select_account", type="primary", use_container_width=True)
    st.stop()

# 3. 시트 데이터 연동
@st.cache_resource
def get_ss(): return gspread.authorize(Credentials.from_authorized_user_info(token_dict)).open_by_key('121-C5OIQpOnTtDbgSLgiq_Qdf5WoHhhIpNkRCWy5hKA')
ss = get_ss()

try: ws_staff = ss.worksheet("직원명단")
except: pass
try: ws_settings = ss.worksheet("환경설정")
except: pass
try: ws_history = ss.worksheet("토큰내역")
except: pass

@st.cache_data(ttl=30)
def fetch_basic_data(): return ws_staff.get_all_records(), ws_settings.get_all_values(), ws_history.get_all_values()
staff_records, settings_all_values, history_all_values = fetch_basic_data()

staff_dict = {str(r['이메일']).strip(): r for r in staff_records}
user_email = st.session_state.user_info.get("email", "")

if user_email in staff_dict:
    user_name = staff_dict[user_email]['이름'] 
    user_tokens = int(staff_dict[user_email].get('보유토큰', 0))
elif user_email in ADMIN_EMAILS:
    user_name = "이응찬 대표" if user_email == "dldmdcks94@gmail.com" else "곽태근 대표"
    user_tokens = 9999
else:
    st.error("⚠️ 승인되지 않은 계정입니다."); st.stop()

now_kst = datetime.utcnow() + timedelta(hours=9)
today_shift = now_kst.strftime("%Y-%m-%d") if now_kst.hour >= 8 else (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")
current_month_str = now_kst.strftime("%Y-%m")
start_of_week = (now_kst - timedelta(days=now_kst.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

# --- 사이드바 ---
st.sidebar.markdown(f"### 👤 {user_name}")
st.sidebar.markdown(f"**보유 토큰:** `{user_tokens} 개`")
if st.sidebar.button("로그아웃"): st.query_params.clear(); st.session_state.clear(); st.rerun()
st.sidebar.write("---")

st.sidebar.markdown("### 🧭 메뉴 이동")
st.sidebar.page_link("app.py", label="홈", icon="🏠")
st.sidebar.page_link("pages/1_오피콜_및_매물관리.py", label="매물관리", icon="🔍")
st.sidebar.page_link("pages/2_계약보고_시스템.py", label="계약", icon="💰")
st.sidebar.write("---")

try: notice_text = settings_all_values[2][1] if len(settings_all_values) > 2 else ""
except: notice_text = ""
try: idpw_text = settings_all_values[3][1] if len(settings_all_values) > 3 else ""
except: idpw_text = ""

# ==========================================
# 🏠 메인 로비 렌더링
# ==========================================
st.title("🏠 엘루이 업무 포털")

if notice_text: 
    st.info(f"📢 **[전체 공지사항]**\n\n{notice_text}")
st.write("---")

st.subheader("🔗 내부 업무망 & 🌐 부동산 필수 사이트")
st.columns(3)[0].link_button("📊 오피콜 시트 (마스터)", "https://docs.google.com/spreadsheets/d/11WZhFnPPIduKVSy3UG0-L1BrXRdddCBhzQLZGMVBSXc/", use_container_width=True)

c1, c2, c3 = st.columns(3)
c1.link_button("🟢 네이버 부동산", "https://land.naver.com", use_container_width=True) 
c2.link_button("🏛️ 정부24 (건축물대장)", "https://www.gov.kr", use_container_width=True)
c3.link_button("📄 인터넷 등기소", "http://www.iros.go.kr", use_container_width=True)

c1.link_button("🏢 공실클럽", "https://www.gongsilclub.com", use_container_width=True)
c2.link_button("🗺️ 씨리얼 (부동산정보)", "https://seereal.lh.or.kr", use_container_width=True)
c3.link_button("🔥 도시가스 (코원에너지)", "https://www.coone.co.kr", use_container_width=True)

c1.link_button("⚖️ 법제처 (국가법령)", "https://www.law.go.kr", use_container_width=True)
c2.link_button("📍 밸류맵", "https://www.valueupmap.com", use_container_width=True)
c3.link_button("🏦 KB부동산", "https://kbland.kr", use_container_width=True)

c1.link_button("📈 부동산테크", "https://www.rtech.or.kr", use_container_width=True)
c2.link_button("🏘️ 렌트홈", "https://www.renthome.go.kr", use_container_width=True)
c3.link_button("🧮 부동산 계산기", "https://xn--989a00af8jnslv3dba.com/", use_container_width=True)

c1.link_button("💰 홈택스 (기준시가)", "https://www.hometax.go.kr", use_container_width=True)
c2.link_button("🔔 공시가격 알리미", "https://www.realtyprice.kr", use_container_width=True)
c3.link_button("🛡️ HUG 보증보험 확인", "https://khig.khug.or.kr/websquare/popup.html?w2xPath=/cg/ae/CGAE034P02.xml&popupID=help&idx=idx10_16146745922339600.17851819347&w2xHome=/login/&w2xDocumentRoot=", use_container_width=True)

st.write("---")

# 💡 [업데이트] 공용 계정 정보 섹션 추가
st.subheader("🔑 회사 공용 계정 (ID/PW)")
if idpw_text: st.info(idpw_text)
else: st.info("등록된 공용 계정 정보가 없습니다. 관리자가 대시보드에서 등록할 수 있습니다.")
st.write("---")

st.subheader("🤝 엘루이 제휴 및 협력 업체")
hc1, hc2 = st.columns(2)
with hc1:
    st.markdown("**🧹 청소 전문업체 [하루하침]**")
    try: st.image("clean.jpg", use_container_width=True)
    except: st.warning("clean.jpg 이미지를 업로드해주세요.")
with hc2:
    st.markdown("**🔧 전속 수리업체 [집고 송파동점]**")
    try: st.image("zipgo.jpg", use_container_width=True)
    except: st.warning("zipgo.jpg 이미지를 업로드해주세요.")

# ==========================================
# 👑 최고 관리자 전용 대시보드
# ==========================================
if user_email in ADMIN_EMAILS:
    st.write("---")
    st.header("👑 최고 관리자 대시보드")
    
    col_admin1, col_admin2, col_admin3 = st.columns(3)
    with col_admin1:
        st.subheader("📢 공지사항 설정")
        with st.form("notice_form", clear_on_submit=False):
            new_notice = st.text_area("공지사항 입력", value=notice_text)
            if st.form_submit_button("💾 공지사항 저장"):
                ws_settings.update_cell(3, 2, new_notice)
                st.cache_data.clear(); st.success("저장 완료!"); st.rerun()

    with col_admin2:
        st.subheader("🎯 오피콜 타겟 설정")
        current_target = settings_all_values[1][1] if len(settings_all_values)>1 else ""
        with st.form("target_form", clear_on_submit=False):
            new_target = st.text_input("타겟 주소 (쉼표 구분)", value=current_target)
            if st.form_submit_button("💾 타겟 주소 저장"):
                ws_settings.update_cell(2, 2, new_target)
                st.cache_data.clear(); st.success("저장 완료!"); st.rerun()
                
    with col_admin3:
        st.subheader("🔑 공용 계정(ID/PW) 설정")
        with st.form("idpw_form", clear_on_submit=False):
            new_idpw = st.text_area("계정 정보 입력", value=idpw_text, height=100)
            if st.form_submit_button("💾 계정 정보 저장"):
                ws_settings.update_cell(4, 2, new_idpw)
                st.cache_data.clear(); st.success("저장 완료!"); st.rerun()

    stats_dict = {r['이름']: {"week_call": 0, "op_update": 0, "villa_new": 0, "month_score": 0, "total_score": 0} for r in staff_records if r['이름'] not in ["이응찬 대표", "곽태근 대표"]}
    
    for row in history_all_values[1:]:
        if len(row) < 5: continue
        dt_str, t_name, reason = str(row[0]), str(row[1]), str(row[4])
        if t_name not in stats_dict: continue
        try: r_dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        except: continue
        is_this_week = r_dt >= start_of_week
        is_this_month = r_dt.strftime("%Y-%m") == current_month_str
        
        pts = 0
        if "신규" in reason: pts = 5
        elif "갱신" in reason or "연장" in reason:
            if "아파트" in reason or "오피스텔" in reason: pts = 3
            else: pts = 1
            
        stats_dict[t_name]["total_score"] += pts
        if is_this_month: stats_dict[t_name]["month_score"] += pts
        if "오피콜" in reason and is_this_week: stats_dict[t_name]["week_call"] += 1
        if "갱신" in reason and "오피스텔" in reason: stats_dict[t_name]["op_update"] += 1
        if "신규" in reason and "빌라" in reason: stats_dict[t_name]["villa_new"] += 1

    st.subheader("🏆 직원 통합 통제 보드 & 기여도 현황")
    admin_staff_data = []
    for r in staff_records:
        name = r['이름']
        if name in ["이응찬 대표", "곽태근 대표"]: continue
        last_shift = str(r.get('최근할당일', ''))
        q_done = 0 if last_shift != today_shift else (int(r.get('할당진행도', 0)) if str(r.get('할당진행도','')).isdigit() else 0)
        st_info = stats_dict.get(name, {})
        admin_staff_data.append({"직원명": name, "VIP권한": str(r.get('VIP권한', 'X')) == 'O', "할당진행도": f"{q_done}/5", "잔여토큰": int(r.get('보유토큰', 0)), "이번주 오피콜(건)": st_info["week_call"], "오피스텔 갱신(누적)": st_info["op_update"], "빌라 신규(누적)": st_info["villa_new"], "이번달 기여도(점)": st_info["month_score"]})

    df_admin = pd.DataFrame(admin_staff_data)
    edited_staff = st.data_editor(df_admin, column_config={"VIP권한": st.column_config.CheckboxColumn("VIP권한 허용"), "잔여토큰": st.column_config.NumberColumn("잔여토큰(수정가능)")}, disabled=["직원명", "할당진행도", "이번주 오피콜(건)", "오피스텔 갱신(누적)", "빌라 신규(누적)", "이번달 기여도(점)"], hide_index=True, use_container_width=True)

    if st.columns([1, 4])[0].button("💾 토큰/VIP 저장", type="primary"):
        for idx, row in edited_staff.iterrows():
            staff_name, vip_val, token_val = row['직원명'], "O" if row['VIP권한'] else "X", row['잔여토큰']
            for i, sr in enumerate(staff_records):
                if sr['이름'] == staff_name:
                    s_idx = i + 2
                    ws_staff.update_cell(s_idx, 4, token_val); ws_staff.update_cell(s_idx, 6, vip_val)
                    break
        st.cache_data.clear(); st.success("저장 완료!"); st.rerun()
