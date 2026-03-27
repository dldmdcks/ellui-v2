import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
import json
import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. 페이지 설정 및 디자인 (못생긴 기본 메뉴판 삭제!)
st.set_page_config(page_title="엘루이 업무포털", page_icon="🏢", layout="wide")
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-size: 14px !important; }
        .stButton>button { padding: 0.2rem 0.5rem; min-height: 2rem; }
        .block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
        /* 👇 스트림릿 기본 회색 메뉴판(pages 내비게이션) 숨기기 */
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

@st.cache_data(ttl=30)
def fetch_basic_data(): return ws_staff.get_all_records(), ws_settings.get_all_values()
staff_records, settings_all_values = fetch_basic_data()

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

# --- 사이드바 ---
st.sidebar.markdown(f"### 👤 {user_name}")
st.sidebar.markdown(f"**보유 토큰:** `{user_tokens} 개`")
if st.sidebar.button("로그아웃"): st.query_params.clear(); st.session_state.clear(); st.rerun()

try: notice_text = settings_all_values[2][1] if len(settings_all_values) > 2 else ""
except: notice_text = ""

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
c3.link_button("🛡️ HUG 보증보험 확인", "https://www.khug.or.kr", use_container_width=True)

c1.link_button("🏗️ 세움터", "https://cloud.eais.go.kr", use_container_width=True)

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
# 👑 최고 관리자 전용 대시보드 (대표님/곽대표님 전용)
# ==========================================
if user_email in ADMIN_EMAILS:
    st.write("---")
    st.header("👑 최고 관리자 대시보드")
    
    # 1. 공지사항 설정
    st.subheader("📢 전체 공지사항 설정")
    with st.form("notice_form"):
        new_notice = st.text_area("공지사항 내용 입력", value=notice_text)
        if st.form_submit_button("공지사항 저장"):
            ws_settings.update_cell(3, 2, new_notice)
            st.cache_data.clear(); st.success("공지사항이 업데이트되었습니다."); st.rerun()

    # 2. 오피콜 타겟 설정
    st.subheader("🎯 오피콜 타겟 설정")
    current_target = settings_all_values[1][1] if len(settings_all_values)>1 else ""
    with st.form("target_form"):
        new_target = st.text_input("이번 주 집중 타겟 주소 (쉼표로 구분)", value=current_target)
        if st.form_submit_button("타겟 주소 저장"):
            ws_settings.update_cell(2, 2, new_target)
            st.cache_data.clear(); st.success("타겟이 업데이트되었습니다."); st.rerun()

    # 3. 직원 권한 및 토큰 통제 보드
    st.subheader("🏆 직원 통합 통제 보드")
    admin_staff_data = []
    for r in staff_records:
        if r['이름'] in ["이응찬 대표", "곽태근 대표"]: continue
        q_done = int(r.get('할당진행도', 0)) if str(r.get('할당진행도','')).isdigit() else 0
        admin_staff_data.append({
            "직원명": r['이름'],
            "VIP권한": str(r.get('VIP권한', 'X')) == 'O',
            "할당진행도": f"{q_done}/5",
            "잔여토큰": int(r.get('보유토큰', 0)),
            "수수료비율": int(r.get('수수료비율', 60)) if str(r.get('수수료비율','')).isdigit() else 60
        })

    df_admin = pd.DataFrame(admin_staff_data)
    edited_staff = st.data_editor(
        df_admin,
        column_config={
            "VIP권한": st.column_config.CheckboxColumn("VIP권한 허용"),
            "잔여토큰": st.column_config.NumberColumn("잔여토큰(수정가능)"),
            "수수료비율": st.column_config.NumberColumn("수수료비율(%)")
        },
        disabled=["직원명", "할당진행도"],
        hide_index=True,
        use_container_width=True
    )

    if st.button("💾 직원 권한/토큰 변경사항 일괄 저장"):
        for idx, row in edited_staff.iterrows():
            staff_name = row['직원명']
            vip_val = "O" if row['VIP권한'] else "X"
            token_val = row['잔여토큰']
            ratio_val = row['수수료비율']

            for i, sr in enumerate(staff_records):
                if sr['이름'] == staff_name:
                    s_idx = i + 2
                    ws_staff.update_cell(s_idx, 4, token_val)  # 토큰 열 (D)
                    ws_staff.update_cell(s_idx, 6, vip_val)    # VIP 열 (F)
                    try: ws_staff.update_cell(s_idx, 10, ratio_val) # 수수료 열 (J)
                    except: pass
                    break
        st.cache_data.clear(); st.success("직원 설정이 완벽하게 저장되었습니다!"); st.rerun()
