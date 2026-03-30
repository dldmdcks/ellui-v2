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
    ws_data = ss.get_worksheet_by_id(1969836502) 
except Exception as e:
    st.error(f"구글 시트 연동 에러: {e}")
    st.stop()

st.title("🚚 잠실르엘 통합 명부 ➡️ 마스터 DB 이삿짐 센터")
st.info("엑셀에서 [다른 이름으로 저장] -> [CSV(쉼표로 분리)]로 저장한 파일을 올려주세요!")

# 2. 파일 업로드 (단일 파일)
uploaded_file = st.file_uploader("잠실르엘 통합 CSV 파일 업로드", type=['csv'])

if uploaded_file:
    if st.button("🚀 마스터 DB로 데이터 쏘기", type="primary"):
        rows_to_upload = []
        
        with st.spinner("통합 데이터를 정제하여 이사 준비 중입니다..."):
            try:
                # 💡 [핵심 패치] 한국어 엑셀(cp949) 호환 로직 장착!
                try:
                    df = pd.read_csv(uploaded_file, header=None, encoding='utf-8')
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, header=None, encoding='cp949')
                except Exception:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, header=None, encoding='euc-kr')
                
                for idx, row in df.iterrows():
                    if len(row) < 7: continue
                    
                    dong_raw = str(row.iloc[1]).strip()
                    ho_raw = str(row.iloc[2]).strip()
                    
                    if not re.search(r'\d', dong_raw) or not re.search(r'\d', ho_raw):
                        continue
                        
                    dong_num = re.sub(r'[^0-9]', '', dong_raw)
                    ho_num = re.sub(r'[^0-9]', '', ho_raw)
                    
                    if not dong_num or not ho_num: continue
                    
                    dong_str = f"{dong_num}동"
                    ho_str = f"{ho_num}호"
                    
                    owner = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else ""
                    if owner == 'nan': owner = ""
                    
                    phone = str(row.iloc[6]).strip() if pd.notna(row.iloc[6]) else ""
                    if phone == 'nan': phone = ""
                    
                    if phone and not phone.startswith("'"):
                        phone = f"'{phone}"
                        
                    new_row = [""] * 28
                    new_row[0], new_row[1], new_row[2], new_row[3], new_row[4] = "서울특별시", "송파구", "신천동", "17", "6"
                    new_row[6], new_row[7], new_row[8] = "잠실르엘", dong_str, ho_str
                    new_row[9], new_row[11], new_row[12], new_row[25] = owner, phone, "아파트", "정상"
                    
                    rows_to_upload.append(new_row)
            except Exception as e:
                st.error(f"파일 읽기 에러: {e}\n엑셀에서 '다른 이름으로 저장 -> CSV'로 올바르게 저장했는지 확인해주세요.")
                st.stop()

        if rows_to_upload:
            with st.spinner(f"총 {len(rows_to_upload)}개의 세대 데이터를 마스터 DB에 적재하는 중입니다... (약 10초 소요)"):
                ws_data.append_rows(rows_to_upload, value_input_option='USER_ENTERED')
            st.success(f"🎉 이사 완료! 총 {len(rows_to_upload)}건의 아파트 데이터가 등록되었습니다.")
            st.warning("데이터 이사가 완료되었으니, 이제 깃허브에서 `99_데이터이전.py` 파일을 삭제하셔도 됩니다.")
        else:
            st.warning("업로드할 유효한 데이터가 없습니다. 파일을 다시 확인해주세요.")
