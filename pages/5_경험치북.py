import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
import json
from datetime import datetime, timedelta

# 🚨 [보안] 로그인 확인
if "connected" not in st.session_state or not st.session_state.connected:
    st.switch_page("app.py")

st.set_page_config(page_title="엘루이 경험치북", page_icon="📖", layout="wide")

st.markdown("""
    <style>
        html, body, [class*="css"]  { font-size: 14px !important; }
        .stButton>button { padding: 0.2rem 0.5rem; min-height: 2rem; }
        .block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
        [data-testid="stSidebarNav"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

ADMIN_EMAILS = ["dldmdcks94@gmail.com", "ktg3582@gmail.com"]

token_dict = json.loads(st.secrets["google_token_json"])
@st.cache_resource
def get_ss(): return gspread.authorize(Credentials.from_authorized_user_info(token_dict)).open_by_key('121-C5OIQpOnTtDbgSLgiq_Qdf5WoHhhIpNkRCWy5hKA')
ss = get_ss()

@st.cache_data(ttl=30)
def fetch_data():
    ws_staff = ss.worksheet("직원명단")
    try: ws_exp = ss.worksheet("경험치북")
    except: ws_exp = None
    return ws_staff.get_all_records(), ws_exp.get_all_values() if ws_exp else []

staff_records, exp_all_values = fetch_data()

staff_dict = {str(r['이메일']).strip(): r for r in staff_records}
user_email = st.session_state.user_info.get("email", "")

now_kst = datetime.utcnow() + timedelta(hours=9)
today_shift = now_kst.strftime("%Y-%m-%d") if now_kst.hour >= 8 else (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")

if user_email in staff_dict:
    user_name = staff_dict[user_email]['이름']
    user_tokens = int(staff_dict[user_email].get('보유토큰', 0))
elif user_email in ADMIN_EMAILS:
    user_name = "이응찬 대표" if user_email == "dldmdcks94@gmail.com" else "곽태근 대표"
    user_tokens = 9999
else: st.error("승인되지 않은 계정입니다."); st.stop()

# --- 🧭 사이드바 ---
st.sidebar.markdown(f"### 👤 {user_name}")
st.sidebar.markdown(f"**보유 토큰:** `{user_tokens} 개`")
if st.sidebar.button("로그아웃"): st.query_params.clear(); st.session_state.clear(); st.switch_page("app.py")
st.sidebar.write("---")

st.sidebar.markdown("### 🧭 메뉴 이동")
st.sidebar.page_link("app.py", label="홈", icon="🏠")
st.sidebar.page_link("pages/1_오피콜_및_매물관리.py", label="매물/DB", icon="🔍")
st.sidebar.page_link("pages/2_계약보고_시스템.py", label="계약정산", icon="💰")
st.sidebar.page_link("pages/3_팀장회의.py", label="회의록", icon="🤝")
st.sidebar.page_link("pages/5_경험치북.py", label="경험치북", icon="📖")
if user_email in ADMIN_EMAILS: st.sidebar.page_link("pages/4_관리자.py", label="관리자", icon="⚙️")
st.sidebar.write("---")

# ==========================================
# 📖 경험치북 (사내 지식인)
# ==========================================
st.title("📖 엘루이 경험치북 (사내 지식인)")
st.write("중개 사고 예방 및 꿀팁! 선배들의 노하우를 검색하고 댓글(피드)로 이력을 남기세요.")

try: ws_exp = ss.worksheet("경험치북")
except: ws_exp = None

if ws_exp is None:
    st.error("🚨 구글 마스터 시트에 **'경험치북'** 탭이 없습니다! 구글 시트 하단에서 [+] 버튼을 눌러 탭을 생성해주세요.")
else:
    with st.expander("✍️ 새로운 지식/판례 등록하기", expanded=False):
        with st.form("add_exp"):
            e_title = st.text_input("제목 (어떤 상황이었나요?)")
            e_body = st.text_area("상세 내용 및 해결 방법")
            if st.form_submit_button("등록하기"):
                if not e_title: st.error("제목을 입력하세요.")
                else:
                    new_id = len(exp_all_values) + 1
                    ws_exp.append_row([new_id, e_title, e_body, user_name, today_shift, "[]"], value_input_option='USER_ENTERED')
                    st.cache_data.clear(); st.success("등록 완료!"); st.rerun()
    
    st.write("---")
    search_exp = st.text_input("🔍 지식 검색 (키워드를 입력하면 제목, 내용, 피드에서 모두 찾아줍니다!)")
    st.write("---")
    
    has_data = False
    for i, r in enumerate(reversed(exp_all_values)):
        if not r or r[0] == "ID": continue # 헤더 또는 빈 줄 건너뛰기
        has_data = True
        
        idx = len(exp_all_values) - i # 원래 행 번호
        title, body = r[1] if len(r)>1 else "", r[2] if len(r)>2 else ""
        author, date = r[3] if len(r)>3 else "", r[4] if len(r)>4 else ""
        comments_str = r[5] if len(r)>5 else "[]"
        
        # 💡 [검색 로직] 제목, 본문, 댓글내용 중 하나라도 걸리면 띄워줌!
        if search_exp and search_exp not in title and search_exp not in body and search_exp not in comments_str: continue
        
        try: comments = json.loads(comments_str)
        except: comments = []
        
        with st.expander(f"📌 {title} (피드: {len(comments)}개) - 작성자: {author}"):
            st.write(body)
            st.caption(f"작성일: {date}")
            st.write("---")
            st.markdown("**💬 해결 과정 및 추가 피드백**")
            
            if comments:
                for c in comments:
                    st.info(f"**{c.get('author','')}** ({c.get('date','')}): {c.get('text','')}")
            else:
                st.caption("아직 등록된 피드가 없습니다.")
                
            with st.form(f"comment_form_{idx}"):
                c_text = st.text_input("피드 남기기")
                if st.form_submit_button("등록"):
                    if c_text:
                        comments.append({"author": user_name, "date": today_shift, "text": c_text})
                        ws_exp.update_cell(idx, 6, json.dumps(comments))
                        st.cache_data.clear(); st.rerun()
                        
    if not has_data:
        st.info("아직 등록된 지식이나 판례가 없습니다.")
