import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
import json
import requests
import pandas as pd
from datetime import datetime, timedelta

# 🚨 [보안] 로그인 확인
if "connected" not in st.session_state or not st.session_state.connected:
    st.switch_page("app.py")

st.set_page_config(page_title="최고 관리자 사령실", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")

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
try: ws_settings = ss.worksheet("환경설정")
except: pass
try: ws_history = ss.worksheet("토큰내역")
except: pass

@st.cache_data(ttl=30)
def fetch_basic_data(): return ws_staff.get_all_records(), ws_settings.get_all_values(), ws_history.get_all_values()
staff_records, settings_all_values, history_all_values = fetch_basic_data()

staff_dict = {str(r['이메일']).strip(): r for r in staff_records}
user_email = st.session_state.get("user_info", {}).get("email", "")

if user_email not in ADMIN_EMAILS:
    st.error("🔒 접근 권한이 없습니다. 최고 관리자 전용 페이지입니다.")
    st.stop()

user_name = "이응찬 대표" if user_email == "dldmdcks94@gmail.com" else "곽태근 대표"
user_tokens = 9999

now_kst = datetime.utcnow() + timedelta(hours=9)
today_shift = now_kst.strftime("%Y-%m-%d") if now_kst.hour >= 8 else (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")
current_month_str = now_kst.strftime("%Y-%m")
start_of_week = (now_kst - timedelta(days=now_kst.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

try: target_op = settings_all_values[1][1] if len(settings_all_values) > 1 and len(settings_all_values[1]) > 1 else ""
except: target_op = ""
try: notice_text = settings_all_values[2][1] if len(settings_all_values) > 2 and len(settings_all_values[2]) > 1 else ""
except: notice_text = ""
try: idpw_text = settings_all_values[3][1] if len(settings_all_values) > 3 and len(settings_all_values[3]) > 1 else ""
except: idpw_text = ""
try: target_apt = settings_all_values[4][1] if len(settings_all_values) > 4 and len(settings_all_values[4]) > 1 else ""
except: target_apt = ""

# 💡 [신규] 은행 상담사 데이터
try: bank_data_str = settings_all_values[5][1] if len(settings_all_values) > 5 and len(settings_all_values[5]) > 1 else "[]"
except: bank_data_str = "[]"
try: bank_data = json.loads(bank_data_str)
except: bank_data = [{"은행명": "", "성함": "", "직책": "", "연락처": ""}]
if not bank_data: bank_data = [{"은행명": "", "성함": "", "직책": "", "연락처": ""}]

# --- 🧭 사이드바 ---
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
st.sidebar.page_link("pages/4_관리자.py", label="관리자", icon="⚙️")
st.sidebar.write("---")

# ==========================================
# 👑 최고 관리자 전용 대시보드
# ==========================================
st.title("⚙️ 최고 관리자 사령실")
st.write("엘루이 전사 시스템 설정 및 직원 통제 보드입니다.")
st.write("---")

c_set1, c_set2 = st.columns(2)
with c_set1:
    st.subheader("📢 공지사항 설정")
    with st.form("notice_form", clear_on_submit=False):
        new_notice = st.text_area("홈 화면 공지사항 입력", value=notice_text, height=120)
        if st.form_submit_button("💾 저장"):
            ws_settings.update_cell(3, 2, new_notice); st.cache_data.clear(); st.success("저장 완료!"); st.rerun()

    st.subheader("🎯 오피스텔 타겟 (4건 배정)")
    with st.form("target_op_form", clear_on_submit=False):
        new_target_op = st.text_area("오피스텔 주소 (쉼표 구분)", value=target_op, height=120)
        if st.form_submit_button("💾 저장"):
            ws_settings.update_cell(2, 2, new_target_op); st.cache_data.clear(); st.success("저장 완료!"); st.rerun()

with c_set2:
    st.subheader("🔑 공용 계정(ID/PW)")
    with st.form("idpw_form", clear_on_submit=False):
        new_idpw = st.text_area("계정 정보 입력", value=idpw_text, height=120)
        if st.form_submit_button("💾 저장"):
            ws_settings.update_cell(4, 2, new_idpw); st.cache_data.clear(); st.success("저장 완료!"); st.rerun()

    st.subheader("🎯 아파트 타겟 (1건 배정)")
    with st.form("target_apt_form", clear_on_submit=False):
        new_target_apt = st.text_area("아파트 주소 (쉼표 구분)", value=target_apt, height=120, placeholder="예: 신천동 17-6")
        if st.form_submit_button("💾 저장"):
            ws_settings.update_cell(5, 2, new_target_apt); st.cache_data.clear(); st.success("저장 완료!"); st.rerun()

# 💡 [신규] 대출/은행 상담사 관리 UI
st.write("---")
st.subheader("🏦 대출/은행 상담사 연락처 관리")
st.write("홈 화면에 노출될 은행 상담사 명단을 추가/수정/삭제할 수 있습니다. 칸을 선택해서 엑셀처럼 바로 적으시면 됩니다.")
df_bank = pd.DataFrame(bank_data)
edited_bank = st.data_editor(df_bank, num_rows="dynamic", use_container_width=True)

if st.button("💾 상담사 연락처 저장", type="primary"):
    new_bank_str = edited_bank.to_json(orient="records", force_ascii=False)
    ws_settings.update_cell(6, 2, new_bank_str)
    st.cache_data.clear()
    st.success("저장 완료! 홈 화면에 즉시 반영됩니다.")
    st.rerun()

st.write("---")
st.subheader("📊 타겟 건물별 만기일(오피콜) 파악 진척도")

target_op_list = [a.strip() for a in target_op.split(",") if a.strip()]
target_apt_list = [a.strip() for a in target_apt.split(",") if a.strip()]

ws_data = ss.get_worksheet_by_id(1969836502)
all_data_raw = ws_data.get_all_values()

target_progress = []
for ta_raw in target_op_list + target_apt_list:
    ta = ta_raw.replace(" ", "")
    if not ta: continue
    total, checked = 0, 0
    for r in all_data_raw[1:]:
        d_str = str(r[2]).strip()
        b_str = str(r[3]).strip()
        bu_str = str(r[4]).strip()
        dong_bon_bu = (f"{d_str}{b_str}" + (f"-{bu_str}" if bu_str and bu_str != "0" else "")).replace(" ", "")
        
        if dong_bon_bu == ta:
            phone = str(r[11]).strip()
            if "연락처 없음" in phone or not phone: continue 
            total += 1
            
            mangi = str(r[21]).strip()
            if mangi and mangi != "0000.00.00" and mangi != "nan":
                checked += 1
    
    if total > 0:
        pct = int((checked / total) * 100)
        target_progress.append({"주소": ta_raw, "전체": total, "완료": checked, "비율": pct})

if not target_progress:
    st.info("현재 분석된 타겟 진행 데이터가 없습니다.")
else:
    for tp in target_progress:
        st.markdown(f"**📍 {tp['주소']}** : 총 {tp['전체']}개 중 **{tp['완료']}개 파악 완료 ({tp['비율']}%)**")
        st.progress(tp['비율'] / 100.0)

st.write("---")

# --- 직원 스탯 및 통제 보드 ---
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
    elif "갱신" in reason or "연장" in reason or "최신화" in reason:
        if "아파트" in reason or "오피스텔" in reason: pts = 3
        else: pts = 1
        
    stats_dict[t_name]["total_score"] += pts
    if is_this_month: stats_dict[t_name]["month_score"] += pts
    if "오피콜" in reason and is_this_week: stats_dict[t_name]["week_call"] += 1
    if "갱신" in reason or "최신화" in reason:
        if "오피스텔" in reason: stats_dict[t_name]["op_update"] += 1
    if "신규" in reason and "빌라" in reason: stats_dict[t_name]["villa_new"] += 1

st.subheader("🏆 직원 통합 통제 보드 & 기여도 현황")

admin_staff_data = []
for r in staff_records:
    name = r['이름']
    if name in ["이응찬 대표", "곽태근 대표"]: continue
    last_shift = str(r.get('최근할당일', ''))
    q_done = 0 if last_shift != today_shift else (int(r.get('할당진행도', 0)) if str(r.get('할당진행도','')).isdigit() else 0)
    st_info = stats_dict.get(name, {})
    
    admin_staff_data.append({
        "직원명": name, 
        "VIP권한": str(r.get('VIP권한', 'X')) == 'O', 
        "오늘진행도(0~5)": q_done, 
        "잔여토큰(수정)": int(r.get('보유토큰', 0)), 
        "이번주 오피콜(건)": st_info["week_call"], 
        "오피스텔 갱신(누적)": st_info["op_update"], 
        "빌라 신규(누적)": st_info["villa_new"], 
        "이번달 기여도(점)": st_info["month_score"],
        "총 누적 기여도(점)": st_info["total_score"]
    })

df_admin = pd.DataFrame(admin_staff_data)
edited_staff = st.data_editor(
    df_admin, 
    column_config={
        "VIP권한": st.column_config.CheckboxColumn("VIP권한 허용"), 
        "오늘진행도(0~5)": st.column_config.NumberColumn("오늘 진행도 (0~5건)", min_value=0, max_value=5),
        "잔여토큰(수정)": st.column_config.NumberColumn("잔여토큰(수정가능)")
    }, 
    disabled=["직원명", "이번주 오피콜(건)", "오피스텔 갱신(누적)", "빌라 신규(누적)", "이번달 기여도(점)", "총 누적 기여도(점)"], 
    hide_index=True, 
    use_container_width=True
)

if st.button("💾 데이터 저장 (토큰/VIP/진행도 적용)", type="primary"):
    for idx, row in edited_staff.iterrows():
        staff_name = row['직원명']
        vip_val = "O" if row['VIP권한'] else "X"
        token_val = row['잔여토큰(수정)']
        prog_val = row['오늘진행도(0~5)']
        
        for i, sr in enumerate(staff_records):
            if sr['이름'] == staff_name:
                s_idx = i + 2
                ws_staff.update_cell(s_idx, 4, token_val) 
                ws_staff.update_cell(s_idx, 6, vip_val)    
                ws_staff.update_cell(s_idx, 8, prog_val)   
                break
    st.cache_data.clear(); st.success("저장 완료! 전사 시스템에 반영되었습니다."); st.rerun()
