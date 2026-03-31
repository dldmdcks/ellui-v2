import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
import json
import requests
from datetime import datetime, timedelta
import extra_streamlit_components as stx

# 1. 페이지 설정 및 디자인 (사이드바 고정)
st.set_page_config(page_title="엘루이 업무포털", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")
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

# 쿠키 매니저 로딩
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()
cookie_manager = get_cookie_manager()

# 2. 구글 로그인 및 보안
try:
    creds_dict = json.loads(st.secrets["credentials_json"])
    token_dict = json.loads(st.secrets["google_token_json"])
    CLIENT_ID = creds_dict["web"]["client_id"]
    CLIENT_SECRET = creds_dict["web"]["client_secret"]
    REDIRECT_URI = creds_dict["web"]["redirect_uris"][0]
except: 
    st.error("❌ 금고 설정(Secrets) 확인 요망!")
    st.stop()

if 'connected' not in st.session_state: 
    st.session_state.connected = False

query_params = st.query_params

# 💡 쿠키 확인
cached_email = cookie_manager.get(cookie="ellui_user_email")
if cached_email and not st.session_state.connected:
    st.session_state.connected = True
    st.session_state.user_info = {"email": cached_email}

if "session_token" in query_params and not st.session_state.connected:
    access_token = query_params["session_token"]
    user_info = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"}).json()
    if "email" in user_info: 
        st.session_state.connected = True
        st.session_state.user_info = user_info
        cookie_manager.set("ellui_user_email", user_info["email"], expires_at=datetime.now() + timedelta(days=30))

if "code" in query_params and not st.session_state.connected:
    res = requests.post("https://oauth2.googleapis.com/token", data={"code": query_params["code"], "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code"}).json()
    if "access_token" in res:
        user_info = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {res['access_token']}"}).json()
        if "email" in user_info:
            st.session_state.connected = True
            st.session_state.user_info = user_info
            cookie_manager.set("ellui_user_email", user_info["email"], expires_at=datetime.now() + timedelta(days=30))
            st.query_params.clear()
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

# 💡 [안전망 패치] 이메일 정보가 없어도 에러 안 나게 방어!
user_email = st.session_state.get("user_info", {}).get("email", "")

if user_email in staff_dict:
    user_name = staff_dict[user_email]['이름'] 
    user_tokens = int(staff_dict[user_email].get('보유토큰', 0))
elif user_email in ADMIN_EMAILS:
    user_name = "이응찬 대표" if user_email == "dldmdcks94@gmail.com" else "곽태근 대표"
    user_tokens = 9999
else:
    st.error("⚠️ 승인되지 않은 계정입니다. 로그인 상태를 다시 확인해주세요.")
    st.stop()

# --- 사이드바 ---
st.sidebar.markdown(f"### 👤 {user_name}")
st.sidebar.markdown(f"**보유 토큰:** `{user_tokens} 개`")
if st.sidebar.button("로그아웃"): 
    cookie_manager.delete("ellui_user_email")
    st.query_params.clear()
    st.session_state.clear()
    st.rerun()
st.sidebar.write("---")

st.sidebar.markdown("### 🧭 메뉴 이동")
st.sidebar.page_link("app.py", label="홈", icon="🏠")
st.sidebar.page_link("pages/1_오피콜_및_매물관리.py", label="매물/DB", icon="🔍")
st.sidebar.page_link("pages/2_계약보고_시스템.py", label="계약정산", icon="💰")
st.sidebar.page_link("pages/3_팀장회의.py", label="회의록", icon="🤝")
st.sidebar.page_link("pages/5_경험치북.py", label="경험치북", icon="📖")

if user_email in ADMIN_EMAILS:
    st.sidebar.page_link("pages/4_관리자.py", label="관리자", icon="⚙️")
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
