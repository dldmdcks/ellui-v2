import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
import json
import requests
import re
import pandas as pd
import math
from datetime import datetime, timedelta

if "connected" not in st.session_state or not st.session_state.connected:
    st.switch_page("app.py")

st.set_page_config(page_title="계약보고 및 정산", page_icon="💰", layout="wide")
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-size: 14px !important; }
        .stButton>button { padding: 0.2rem 0.5rem; min-height: 2rem; }
        .block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
        div[role="radiogroup"] { flex-direction: row; gap: 15px; padding-bottom: 15px; border-bottom: 2px solid #f0f2f6; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

ADMIN_EMAILS = ["dldmdcks94@gmail.com", "ktg3582@gmail.com"]

token_dict = json.loads(st.secrets["google_token_json"])
@st.cache_resource
def get_ss(): return gspread.authorize(Credentials.from_authorized_user_info(token_dict)).open_by_key('121-C5OIQpOnTtDbgSLgiq_Qdf5WoHhhIpNkRCWy5hKA')
ss = get_ss()

ws_data = ss.get_worksheet_by_id(1969836502)
try: ws_staff = ss.worksheet("직원명단")
except: pass
try: ws_contract = ss.worksheet("계약보고_DB")
except: pass

@st.cache_data(ttl=30)
def fetch_contract_data(): return ws_staff.get_all_records(), ws_contract.get_all_values()
staff_records, contract_all_values = fetch_contract_data()

staff_dict = {str(r['이메일']).strip(): r for r in staff_records}
user_email = st.session_state.user_info.get("email", "")

if user_email in staff_dict:
    user_name = staff_dict[user_email]['이름'] 
    my_ratio = int(staff_dict[user_email].get('수수료비율', 60)) if str(staff_dict[user_email].get('수수료비율', '')).isdigit() else 60
elif user_email in ADMIN_EMAILS:
    user_name = "관리자 (대표)"
    my_ratio = 100
else: st.error("승인되지 않은 계정입니다."); st.stop()

contract_records = contract_all_values[1:]

st.sidebar.markdown(f"### 👤 {user_name}")

tab_names = ["✍️ 계약보고 올리기", "💰 내 정산"]
if user_email in ADMIN_EMAILS: tab_names.append("👑 전사 대시보드")
selected_tab = st.radio("메뉴", tab_names, horizontal=True, label_visibility="collapsed")

if selected_tab == "✍️ 계약보고 올리기":
    st.subheader("📌 계약 정보 입력 (이후 정산 장부로 자동 이동)")
    st.info("준비 중인 화면입니다. 1번 탭의 기능을 먼저 완벽히 테스트해 주십시오!") # 우선 1번 탭에 집중하기 위해 비워둡니다.

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

    if st.toggle("👁️ 이번 달 예상 급여"): st.success(f"이번 달 예상 실수령액: **{expected_salary:,}원**")
    hide_completed_my = st.checkbox("☑️ 지급 완료된 내역 숨기기", value=True)
    
    if not my_contracts: st.info("아직 보고하신 계약건이 없습니다.")
    else:
        for idx, row in enumerate(my_contracts):
            rp = (row + [""]*27)[:27] 
            if hide_completed_my and str(rp[23]) == "O": continue
            c_date, d_type = str(rp[0])[:10], str(rp[2])
            c_addr = f"{rp[5]} {rp[6]}-{rp[7]} {rp[9]}"
            fee_val = int(re.sub(r'[^0-9]', '', str(rp[19]))) if re.sub(r'[^0-9]', '', str(rp[19])) else 0
            comp_in, emp_out = "🟡 입금완료" if str(rp[22]) == "O" else "⚪ 미입금", "🔴 급여완료" if str(rp[23]) == "O" else "⚪ 미정산"
            is_locked_data = (str(rp[22]) == "O") 
            exp_key = f"exp_mycalc_{idx}"
            
            with st.expander(f"{c_date} 📍 {c_addr} [{d_type}] | 입금액: {fee_val:,}원 | {comp_in}/{emp_out}", expanded=st.session_state.get(exp_key, False)):
                if is_locked_data: st.warning("🔒 대표님 입금 확인 완료 (금액 수정 불가)")
                with st.form(f"fee_form_{idx}"):
                    c_f1, c_f2, c_f3 = st.columns(3)
                    new_fee = c_f1.text_input("총 수수료", value=str(rp[19]), disabled=is_locked_data)
                    new_method = c_f2.selectbox("결제 수단", ["계좌이체", "현금"], index=0 if str(rp[20])!="현금" else 1, disabled=is_locked_data)
                    new_depositor = c_f3.text_input("입금자명", value=str(rp[25]), disabled=is_locked_data)
                    if st.form_submit_button("💾 정보 저장", disabled=is_locked_data):
                        t_idx = len(contract_all_values) - idx 
                        ws_contract.update_cell(t_idx, 20, new_fee); ws_contract.update_cell(t_idx, 21, new_method); ws_contract.update_cell(t_idx, 26, new_depositor)
                        st.session_state[exp_key] = True; st.cache_data.clear(); st.rerun()
                
                if "요청완료" in str(rp[21]): st.success(f"✅ {rp[21]}")
                else:
                    st.write("---")
                    st.markdown("#### 🧾 증빙 자동 요청 (카카오워크 전송)")
                    with st.form(f"req_form_{idx}", clear_on_submit=True):
                        req_type = st.radio("발급 종류", ["세금계산서", "지출증빙", "현금영수증"], horizontal=True)
                        r_c1, r_c2 = st.columns(2)
                        biz_name = r_c1.text_input("상호/이름")
                        biz_num = r_c2.text_input("사업자/폰번호")
                        if st.form_submit_button("🚀 대표님께 카톡 요청 쏘기"):
                            msg = f"💌 [{req_type} 요청]\n담당자 : {user_name}\n주소 : {c_addr}\n금액 : {new_fee}원\n정보 : {biz_name} / {biz_num}"
                            try:
                                requests.post("https://kakaowork.com/bots/hook/4a5be71f2c424dfa8a6926ddfbd75ebe", json={"text": msg})
                                ws_contract.update_cell(len(contract_all_values) - idx, 22, f"{req_type} 요청완료") 
                                st.session_state[exp_key] = True; st.cache_data.clear(); st.rerun()
                            except: st.error("⚠️ 카톡 전송 에러")

elif selected_tab == "👑 전사 대시보드":
    st.subheader("👑 전사 정산 및 매출 대시보드")
    hide_completed = st.checkbox("☑️ 급여 지급 완료(🔴)된 내역 숨기기", value=True)
    
    calc_data = []
    for i, row in enumerate(contract_records):
        if len(row) < 19: continue
        rp = (row + [""]*27)[:27] 
        if hide_completed and str(rp[23]) == "O": continue
        
        fee = int(re.sub(r'[^0-9]', '', str(rp[19]))) if re.sub(r'[^0-9]', '', str(rp[19])) else 0
        pmethod = str(rp[20])
        s_ratio = int(staff_dict[str(rp[1])].get('수수료비율', 60)) if str(rp[1]) in staff_dict else 60
        
        if fee > 0:
            if pmethod == "현금" and fee < 100000:
                net_fee, vat, tax_33 = fee, 0, 0
                final_pay = int(fee * (s_ratio/100))
                comp_profit = fee - final_pay
            else:
                net_fee = int(round(fee/1.1)); vat = fee - net_fee; share = int(net_fee * (s_ratio/100)); tax_33 = math.ceil(share * 0.033) 
                final_pay = share - tax_33; comp_profit = net_fee - share
        else: final_pay, comp_profit, vat, tax_33 = 0, 0, 0, 0
        
        calc_data.append([i + 2, str(rp[0])[:10], str(rp[1]), str(rp[2]), f"{fee:,}원", str(rp[25]), pmethod, f"{final_pay:,}원", f"{comp_profit:,}원", str(rp[22]) == "O", str(rp[23]) == "O"])
        
    # 💡 [UI 깨짐 복구] 
    edited_df = st.data_editor(
        pd.DataFrame(calc_data, columns=["줄번호", "계약일", "담당직원", "구분", "총입금액", "입금자명", "수단", "직원급여", "회사수익", "회사입금(체크)", "직원지급(체크)"]), 
        column_config={"줄번호": None, "회사입금(체크)": st.column_config.CheckboxColumn("🟡회사입금"), "직원지급(체크)": st.column_config.CheckboxColumn("🔴급여지급")}, 
        disabled=["계약일", "담당직원", "구분", "총입금액", "입금자명", "수단", "직원급여", "회사수익"], 
        use_container_width=True, hide_index=True
    )
    
    if st.button("💾 정산 상태 저장"):
        for idx, r in edited_df.iterrows():
            row_num = r["줄번호"]
            ws_contract.update_cell(row_num, 23, "O" if r["회사입금(체크)"] else "") 
            ws_contract.update_cell(row_num, 24, "O" if r["직원지급(체크)"] else "") 
        st.cache_data.clear(); st.success("정산 저장 완료!"); st.rerun()
