import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

# --- 設定頁面資訊 ---
st.set_page_config(page_title="Orbiloc 保固服務系統", layout="centered")

# --- 連接 Google Sheets (Render 專用版) ---
def get_google_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 這裡是最關鍵的修改：讀取 Render 的環境變數
    # 我們會在 Render 後台設定一個叫做 "gcp_service_account" 的變數
    if "gcp_service_account" in os.environ:
        creds_dict = json.loads(os.environ["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # 本機測試用 (如果您有把 json 檔放在專案資料夾才會用到，上線後不需要)
        # st.secrets 是 Streamlit Cloud 用的，Render 用不到，這裡僅作備用
        st.error("找不到金鑰，請確認 Render 環境變數設定正確。")
        st.stop()

    client = gspread.authorize(creds)
    sheet = client.open("Orbiloc_Warranty_Data").sheet1
    return sheet

try:
    sheet = get_google_sheet()
except Exception as e:
    st.error(f"資料庫連線失敗：{e}")
    st.stop()

# --- 介面邏輯 (與之前相同) ---
menu = st.sidebar.selectbox("選擇功能", ["消費者保固登錄", "店家核銷專區"])

if menu == "消費者保固登錄":
    st.title("🛡️ Orbiloc 守護者外出燈 - 線上保固登錄")
    st.info("購買一年內，享免費換電池及維護一次（需回原購買店家使用）。")

    with st.form("register_form"):
        name = st.text_input("姓名")
        phone = st.text_input("電話 (作為查詢依據)", placeholder="09xxxxxxxx")
        email = st.text_input("Email")
        invoice = st.text_input("發票/收據/訂單編號")
        shop_name = st.text_input("購買通路名稱")
        product_detail = st.text_input("購買品項及數量")
        purchase_date = st.date_input("購買日期")

        submitted = st.form_submit_button("送出登記")

        if submitted:
            if not (name and phone and invoice and shop_name):
                st.error("請填寫所有必填欄位！")
            else:
                try:
                    data = sheet.get_all_records()
                    df = pd.DataFrame(data)
                    # 檢查電話是否重複
                    if not df.empty and str(phone) in df['電話'].astype(str).values:
                        st.warning("此電話號碼已登記過保固。")
                    else:
                        new_row = [
                            name, "'" + str(phone), email, invoice, shop_name, 
                            product_detail, str(purchase_date), 
                            str(datetime.now().date()), "No", "", ""
                        ]
                        sheet.append_row(new_row)
                        st.success("✅ 登記成功！")
                except Exception as e:
                    st.error(f"寫入錯誤：{e}")

elif menu == "店家核銷專區":
    st.title("🔧 經銷商核銷後台")
    password = st.sidebar.text_input("請輸入店家通行碼", type="password")
    
    # 這裡也要用環境變數來保護密碼
    correct_password = os.environ.get("shop_password", "1234") # 預設1234，請在Render設定

    if password == correct_password:
        st.success("登入成功")
        search_phone = st.text_input("輸入消費者電話查詢資格")
        
        if st.button("查詢"):
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            df['電話'] = df['電話'].astype(str)
            customer = df[df['電話'] == search_phone]
            
            if customer.empty:
                st.error("查無此電話號碼。")
            else:
                st.write("---")
                st.write(f"**姓名：** {customer.iloc[0]['姓名']}")
                st.write(f"**品項：** {customer.iloc[0]['購買品項及數量']}")
                st.write(f"**購買日：** {customer.iloc[0]['購買日期']}")
                
                status = customer.iloc[0]['是否已兌換']
                if status == "Yes":
                    st.warning(f"⚠️ 已於 {customer.iloc[0]['兌換日']} 使用過。")
                else:
                    st.success("✅ 符合資格，尚未兌換。")
                    with st.form("redeem_form"):
                        shop_verify = st.text_input("輸入您的店名")
                        confirm = st.form_submit_button("確認換電池")
                        
                        if confirm and shop_verify:
                            row_idx = customer.index[0] + 2 
                            sheet.update_cell(row_idx, 9, "Yes")
                            sheet.update_cell(row_idx, 10, shop_verify)
                            sheet.update_cell(row_idx, 11, str(datetime.now().date()))
                            st.balloons()
                            st.success("核銷完成！")
    elif password:
        st.error("通行碼錯誤")
