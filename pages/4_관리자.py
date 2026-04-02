import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
import json
import pandas as pd
from datetime import datetime, timedelta

# 🚨 [보안] 로그인 확인
if "connected" not in st.session_state or not st.session_state.connected:
    st.switch_page("app.py")

st.set_page_config(page_title="최고 관리자 사령실", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")

ADMIN_EMAILS = ["dldmdcks94@gmail.com", "ktg3582@gmail.com"]
user_email = st.session_state.get("user_info", {}).get("email", "")

if user_email not in ADMIN_EMAILS:
    st.error("🔒 접근 권한이 없습니다."); st.stop()

token_dict = json.loads(st.secrets["google_token_json"])
@st.cache_resource
def get_ss(): return gspread.authorize(Credentials.from_authorized_user_info(token_dict)).open_by_key('121-C5OIQpOnTtDbgSLgiq_Qdf5WoHhhIpNkRCWy5hKA')
ss = get_ss()
ws_settings = ss.worksheet("환경설정")
settings_all = ws_settings.get_all_values()

# 현재 설정값 읽기
try: off_count = int(settings_all[6][1]) if len(settings_all)>6 else 4
except: off_count = 4
try: apt_count = int(settings_all[7][1]) if len(settings_all)>7 else 1
except: apt_count = 1

st.title("⚙️ 최고 관리자 사령실")
st.write("---")

# 💡 [신규] 오피콜 배정 개수 설정 섹션
st.subheader("📞 직원별 오피콜 배정 개수 설정")
c_oc1, c_oc2 = st.columns(2)
with c_oc1:
    new_off = st.select_slider("오피스텔/빌라 오피콜 개수", options=list(range(1, 11)), value=off_count)
with c_oc2:
    new_apt = st.select_slider("아파트 오피콜 개수", options=list(range(1, 11)), value=apt_count)

if st.button("💾 배정 개수 저장", type="primary"):
    ws_settings.update_cell(7, 2, new_off)
    ws_settings.update_cell(8, 2, new_apt)
    st.cache_data.clear()
    st.success(f"저장 완료! (오피스텔: {new_off}개 / 아파트: {new_apt}개)")
    st.rerun()

st.write("---")
# (이후 직원 관리 및 기타 설정 코드는 기존과 동일)
