import streamlit as st
import pandas as pd
import gspread
from google.oauth2.credentials import Credentials
import json
import re

st.set_page_config(page_title="DB 자동 업로드기", layout="wide")

# 1. 구글 시트 연동
try:
    token_dict = json.loads(st.secrets["google_token_json"])
    gc = gspread.authorize(Credentials.from_authorized_user_info(token_dict))
    ss = gc.open_by_key('121-C5OIQpOnTtDbgSLgiq_Qdf5WoHhhIpNkRCWy5hKA')
    ws_data = ss.get_worksheet_by_id(1969836502) # 마스터 DB
except Exception as e:
    st.error(f"구글 시트 연동 에러: {e}")
    st.stop()

st.title("🚚 아파트 명부 ➡️ 마스터 DB 자동 이삿짐 센터")
st.info("올려주신 잠실르엘 동별 CSV 파일들을 한 번에 선택해서 올려주세요.")

# 2. 파일 업로드
uploaded_files = st.file_uploader("동별 CSV 파일 업로드 (여러 개 동시 선택 가능)", type=['csv'], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 마스터 DB로 데이터 쏘기", type="primary"):
        rows_to_upload = []
        
        with st.spinner("데이터를 정제하여 이사 준비 중입니다..."):
            for file in uploaded_files:
                # 파일명에서 '동' 추출 (예: 101동.csv -> 101동)
                dong_match = re.search(r'(\d+동)', file.name)
                dong_str = dong_match.group(1) if dong_match else "동미상"
                
                # CSV 읽기
                df = pd.read_csv(file)
                
                for _, row in df.iterrows():
                    # 호실 추출 (첫 번째 열)
                    ho_raw = str(row.iloc[0]).strip()
                    if not ho_raw or ho_raw == '비고' or ho_raw == 'nan': 
                        continue # 빈칸이나 '비고' 행은 건너뜀
                        
                    ho_num = re.sub(r'[^0-9]', '', ho_raw)
                    if not ho_num: continue
                    
                    # 소유주 (두 번째 열), 연락처 (네 번째 열)
                    owner = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                    phone = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
                    if phone == 'nan': phone = ""
                    
                    # 엑셀에서 0이 날아가지 않게 작은따옴표 붙이기
                    if phone and not phone.startswith("'"):
                        phone = f"'{phone}"
                        
                    # 마스터 DB (28칸) 양식에 맞게 데이터 조립
                    new_row = [""] * 28
                    new_row[0] = "서울특별시"
                    new_row[1] = "송파구"
                    new_row[2] = "신천동"
                    new_row[3] = "17"
                    new_row[4] = "6"
                    new_row[6] = "잠실르엘"
                    new_row[7] = dong_str
                    new_row[8] = f"{ho_num}호"
                    new_row[9] = owner
                    new_row[11] = phone
                    new_row[12] = "아파트" # 💡 핵심: 용도에 아파트로 세팅
                    new_row[25] = "정상" # 상태값
                    
                    rows_to_upload.append(new_row)

        if rows_to_upload:
            with st.spinner(f"총 {len(rows_to_upload)}개의 세대 데이터를 마스터 DB에 적재하는 중입니다... (약 10~20초 소요)"):
                ws_data.append_rows(rows_to_upload, value_input_option='USER_ENTERED')
            st.success(f"🎉 이사 완료! 총 {len(rows_to_upload)}건의 아파트 데이터가 마스터 DB에 성공적으로 등록되었습니다.")
            st.warning("데이터 이사가 완료되었으니, 이제 깃허브에서 `99_데이터이전.py` 파일을 삭제하셔도 됩니다.")
        else:
            st.warning("업로드할 유효한 데이터가 없습니다.")
