import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
import json
import requests
from datetime import datetime, timedelta

# 🚨 [보안] 로그인 확인
if "connected" not in st.session_state or not st.session_state.connected:
    st.switch_page("app.py")

st.set_page_config(page_title="팀장 회의록", page_icon="🤝", layout="wide")

st.markdown("""
    <style>
        html, body, [class*="css"]  { font-size: 14px !important; }
        .stButton>button { padding: 0.2rem 0.5rem; min-height: 2rem; }
        .block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
        [data-testid="stSidebarNav"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

ADMIN_EMAILS = ["dldmdcks94@gmail.com", "ktg3582@gmail.com"]

# 구글 시트 연동
token_dict = json.loads(st.secrets["google_token_json"])
@st.cache_resource
def get_ss(): return gspread.authorize(Credentials.from_authorized_user_info(token_dict)).open_by_key('121-C5OIQpOnTtDbgSLgiq_Qdf5WoHhhIpNkRCWy5hKA')
ss = get_ss()

try: ws_staff = ss.worksheet("직원명단")
except: pass
try: ws_meeting = ss.worksheet("팀장회의록")
except: st.error("🚨 구글 시트에 '팀장회의록' 탭을 먼저 만들어주세요!"); st.stop()

@st.cache_data(ttl=30)
def fetch_meeting_data(): return ws_staff.get_all_records(), ws_meeting.get_all_values()
staff_records, meeting_data = fetch_meeting_data()

staff_dict = {str(r['이메일']).strip(): r for r in staff_records}
user_email = st.session_state.user_info.get("email", "")

if user_email in staff_dict:
    user_name = staff_dict[user_email]['이름']
    user_tokens = int(staff_dict[user_email].get('보유토큰', 0))
elif user_email in ADMIN_EMAILS:
    user_name = "이응찬 대표" if user_email == "dldmdcks94@gmail.com" else "곽태근 대표"
    user_tokens = 9999
else: st.error("승인되지 않은 계정입니다."); st.stop()

# 💡 [핵심 보안] 팀장 또는 대표 직급이 아니면 강제 차단!
is_leader = "팀장" in user_name or "대표" in user_name or user_email in ADMIN_EMAILS
if not is_leader:
    st.error("🔒 접근 권한이 없습니다. 팀장 이상 직급만 열람 및 작성이 가능한 공간입니다.")
    st.stop()

# --- 🧭 사이드바 ---
st.sidebar.markdown(f"### 👤 {user_name}")
st.sidebar.markdown(f"**보유 토큰:** `{user_tokens} 개`")
if st.sidebar.button("로그아웃"): st.query_params.clear(); st.session_state.clear(); st.switch_page("app.py")
st.sidebar.write("---")
st.sidebar.markdown("### 🧭 메뉴 이동")
st.sidebar.page_link("app.py", label="홈", icon="🏠")
st.sidebar.page_link("pages/1_오피콜_및_매물관리.py", label="매물관리", icon="🔍")
st.sidebar.page_link("pages/2_계약보고_시스템.py", label="계약", icon="💰")
st.sidebar.page_link("pages/3_팀장회의.py", label="회의록", icon="🤝")

if user_email in ADMIN_EMAILS:
    st.sidebar.page_link("pages/4_관리자.py", label="관리자", icon="⚙️")
st.sidebar.write("---")

# ==========================================
# 🤝 팀장 안건 및 회의록 메인 화면
# ==========================================
st.title("🤝 엘루이 팀장 안건 및 회의록")
st.write("주간 회의 안건을 올리고, 도출된 결과물과 피드백을 영구적으로 기록하는 공간입니다.")

# 1. 신규 안건 등록 폼
with st.expander("➕ [신규 안건 등록] 이번 주 회의 안건 올리기", expanded=False):
    with st.form("new_agenda_form", clear_on_submit=True):
        agenda_title = st.text_input("📌 안건 제목", placeholder="예: 3월 넷째 주 신규 입사자 교육 방안")
        agenda_detail = st.text_area("📝 안건 상세 내용", placeholder="어떤 주제로 논의가 필요한지 상세히 적어주세요.")
        
        if st.form_submit_button("🚀 안건 등록하기", type="primary"):
            if not agenda_title or not agenda_detail:
                st.error("제목과 상세 내용을 모두 입력해주세요.")
            else:
                now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
                ws_meeting.append_row([now_str, user_name, agenda_title, agenda_detail, ""], value_input_option='USER_ENTERED')
                st.cache_data.clear(); st.success("안건이 성공적으로 등록되었습니다!"); st.rerun()

st.write("---")

# 2. 안건 검색 및 리스트
c_search1, c_search2 = st.columns([3, 1])
search_keyword = c_search1.text_input("🔍 과거 안건/회의록 검색 (제목 또는 내용)", placeholder="검색어를 입력하세요...")

records = meeting_data[1:] # 첫 번째 줄(제목) 제외
if not records:
    st.info("등록된 안건이 없습니다. 첫 번째 안건을 등록해보세요!")
else:
    # 최신 글이 위로 오도록 뒤집기 (인덱스 유지를 위해 tuple로 묶음)
    records_with_idx = [(i+2, r) for i, r in enumerate(records)]
    records_with_idx.reverse()
    
    for row_idx, r in records_with_idx:
        # 데이터 길이 맞추기 (빈칸 에러 방지)
        rp = (r + [""]*5)[:5]
        reg_dt, author, title, detail, comments = rp[0], rp[1], rp[2], rp[3], rp[4]
        
        # 검색 필터링
        if search_keyword and search_keyword.lower() not in title.lower() and search_keyword.lower() not in detail.lower():
            continue
            
        date_short = reg_dt[:10] if len(reg_dt) >= 10 else reg_dt
        comment_count = len([c for c in comments.split('\n') if "👉" in c])
        badge = f"💬({comment_count})" if comment_count > 0 else "🆕"
        
        with st.expander(f"[{date_short}] {title} (작성: {author}) {badge}"):
            st.markdown(f"**📝 안건 상세:**\n{detail}")
            st.write("---")
            
            st.markdown("**💡 회의 결과 및 피드백:**")
            if comments.strip():
                st.info(comments)
            else:
                st.caption("아직 등록된 결과나 코멘트가 없습니다.")
                
            # 코멘트(결과) 추가 폼
            with st.form(f"comment_form_{row_idx}", clear_on_submit=True):
                new_comment = st.text_area("회의 결과 또는 피드백 추가", placeholder="회의에서 결정된 사항이나 추가 의견을 적어주세요.")
                if st.form_submit_button("답변/결과 기록하기"):
                    if new_comment.strip():
                        now_str = (datetime.utcnow() + timedelta(hours=9)).strftime('%m.%d %H:%M')
                        updated_comments = f"{comments}\n👉 [{now_str}] {user_name}: {new_comment}".strip() if comments else f"👉 [{now_str}] {user_name}: {new_comment}"
                        
                        ws_meeting.update_cell(row_idx, 5, updated_comments)
                        st.cache_data.clear(); st.rerun()
