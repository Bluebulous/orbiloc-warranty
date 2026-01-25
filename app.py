import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

# --- 設定頁面資訊 ---
st.set_page_config(page_title="Orbiloc 保固服務系統", page_icon="🛡️", layout="centered")

# --- 1. 顯示 Logo (請確保 GitHub 上有 logo.png) ---
# 如果您還沒上傳圖片，這一行會報錯，請先上傳或暫時註解掉
try:
    st.image("logo.png", width=250)
except:
    st.warning("請在 GitHub 上傳 logo.png 以顯示圖片")

# ==========================================
# 資料設定區 (您可以在這裡修改選單內容)
# ==========================================

# 購買通路清單 (請根據實際情況增減)
SHOP_LIST = [
    "Bluebulous 布魯樂斯毛孩專業用品",
    "Caldo Pets 卡朵毛孩生活",
    "Fluffy Pet|犬貓生活選品",
    "好多毛寵物美容",
    "Kodomou 毛孩選物所",
    "趴趴狗寵物精品",
    "Buster & Beans 選物",
    "阿貴養了一隻牛",
]

# 產品清單
PRODUCT_LIST = [
    "Orbiloc 守護者外出燈 (香檳金)",
    "Orbiloc 守護者外出燈 (白光)",
    "Orbiloc 守護者外出燈 (湖水綠)",
    "Orbiloc 守護者外出燈 (琥珀)",
    "Orbiloc 守護者外出燈 (紫色)",
    "Orbiloc 守護者外出燈 (粉紅)",
    "Orbiloc 守護者外出燈 (藍色)",
    "Orbiloc 守護者外出燈 (綠色)",
    "Orbiloc 守護者外出燈 (黃色)",
    "Orbiloc 守護者外出燈 (闇光)",
    "Orbiloc 守護者外出燈 (紅色)"
]

# ==========================================

# --- 連接 Google Sheets ---
def get_google_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    if "gcp_service_account" in os.environ:
        creds_dict = json.loads(os.environ["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        st.error("找不到金鑰，請確認 Render 環境變數設定正確。")
        st.stop()

    client = gspread.authorize(creds)
    # 請確認您的 Google Sheet 名稱正確
    sheet = client.open("Orbiloc_Warranty_Data").sheet1
    return sheet

try:
    sheet = get_google_sheet()
except Exception as e:
    st.error(f"資料庫連線失敗：{e}")
    st.stop()

# --- 側邊欄導航 ---
menu = st.sidebar.selectbox("選擇功能", ["消費者保固登錄", "店家核銷專區"])

# ==========================================
# 功能一：消費者保固登錄
# ==========================================
if menu == "消費者保固登錄":
    st.title("🛡️ 保固登錄")
    st.info("購買一年內，享免費換電池及維護一次。")

    with st.form("register_form"):
        name = st.text_input("姓名")
        phone = st.text_input("電話 (作為查詢依據)", placeholder="09xxxxxxxx")
        email = st.text_input("Email")
        invoice = st.text_input("發票/收據/訂單編號")
        
        # 變動 2: 通路改成下拉選單
        shop_name = st.selectbox("購買通路名稱 (請務必選擇正確，以免影響保固權益)", SHOP_LIST)
        
        # 變動 3: 品項選單 + 數量填寫
        st.write("購買明細")
        c1, c2 = st.columns([3, 1])
        with c1:
            product_item = st.selectbox("購買品項", PRODUCT_LIST)
        with c2:
            quantity = st.number_input("數量", min_value=1, value=1, step=1)
        
        product_detail = f"{product_item} x{quantity}"
        
        purchase_date = st.date_input("購買日期")

        submitted = st.form_submit_button("送出登記")

        if submitted:
            if not (name and phone and invoice):
                st.error("請填寫所有必填欄位！")
            else:
                try:
                    data = sheet.get_all_records()
                    df = pd.DataFrame(data)
                    # 檢查重複
                    if not df.empty and str(phone) in df['電話'].astype(str).values:
                        st.warning("此電話號碼已登記過保固。")
                    else:
                        new_row = [
                            name, "'" + str(phone), email, invoice, shop_name, 
                            product_detail, str(purchase_date), 
                            str(datetime.now().date()), "No", "", ""
                        ]
                        sheet.append_row(new_row)
                        st.success(f"✅ 登記成功！您的資料已歸檔至【{shop_name}】。")
                except Exception as e:
                    st.error(f"寫入錯誤：{e}")

# ==========================================
# 功能二：店家核銷專區 (權限隔離版)
# ==========================================
elif menu == "店家核銷專區":
    st.title("🔧 經銷商核銷登入")
    
    # 讓店家選擇自己是誰
    login_shop = st.selectbox("請選擇您的店家名稱", SHOP_LIST)
    password = st.text_input("請輸入店家通行碼", type="password")
    
    # --- 讀取 Render 環境變數中的店家密碼表 ---
    # 我們會儲存一個 JSON 字串，格式如：{"店名A": "密碼A", "店名B": "密碼B"}
    shop_credentials_json = os.environ.get("SHOP_CREDENTIALS", "{}")
    try:
        shop_credentials = json.loads(shop_credentials_json)
    except:
        shop_credentials = {}

    # 驗證按鈕
    if st.button("登入查詢"):
        # 1. 驗證密碼是否正確
        if login_shop in shop_credentials and str(password) == str(shop_credentials[login_shop]):
            st.session_state['logged_in'] = True
            st.session_state['current_shop'] = login_shop
            st.success(f"歡迎 {login_shop}，登入成功！")
        else:
            st.error("密碼錯誤，或該店家尚未開通權限。")

    # --- 登入成功後的畫面 ---
    if st.session_state.get('logged_in') and st.session_state.get('current_shop') == login_shop:
        st.divider()
        st.subheader(f"📍 {login_shop} - 客戶查詢系統")
        
        search_phone = st.text_input("輸入消費者電話", key="search_phone")
        
        if st.button("搜尋資料"):
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            df['電話'] = df['電話'].astype(str)
            
            # 變動 4: 雙重過濾 (電話吻合 + 通路吻合)
            # 只有當消費者填寫的通路 = 目前登入的通路，才看得到
            customer = df[
                (df['電話'] == search_phone) & 
                (df['購買通路名稱'] == login_shop)
            ]
            
            if customer.empty:
                # 為了隱私，即使別家店有這個人，我們也顯示查無資料，或提示非本店客戶
                # 這裡我們檢查一下是否在別家買的，給予不同提示
                check_all = df[df['電話'] == search_phone]
                if not check_all.empty:
                     st.warning("⚠️ 查無此人於本店的購買紀錄（該客戶可能是在其他通路購買）。")
                else:
                     st.error("查無此電話號碼。")
            else:
                record = customer.iloc[0]
                st.info("✅ 找到資料 (僅顯示本店售出之產品)")
                st.write(f"**姓名：** {record['姓名']}")
                st.write(f"**品項：** {record['購買品項及數量']}")
                st.write(f"**購買日：** {record['購買日期']}")
                
                status = record['是否已兌換']
                if status == "Yes":
                    st.warning(f"⚠️ 此服務已於 {record['兌換日']} 在 {record['兌換店家']} 使用過。")
                else:
                    st.success("✅ 符合資格，尚未兌換。")
                    
                    with st.form("redeem_update"):
                        st.write(f"執行店家：{login_shop}")
                        confirm = st.form_submit_button("確認執行換電池服務")
                        
                        if confirm:
                            row_idx = customer.index[0] + 2 
                            sheet.update_cell(row_idx, 9, "Yes")
                            sheet.update_cell(row_idx, 10, login_shop)
                            sheet.update_cell(row_idx, 11, str(datetime.now().date()))
                            st.balloons()
                            st.success("核銷完成！")
