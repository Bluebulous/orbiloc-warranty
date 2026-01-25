import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

# --- 設定頁面資訊 ---
st.set_page_config(page_title="Orbiloc 守護者外出燈保固註冊系統", page_icon="🛡️", layout="centered")

# --- 初始化 Session State ---
if 'cart' not in st.session_state:
    st.session_state['cart'] = []

# --- 1. 顯示 Logo ---
try:
    st.image("logo.png", width=250)
except:
    pass

# ==========================================
# 資料設定區
# ==========================================

SHOP_LIST = [
    "Bluebulous 布魯樂斯毛孩專業用品",
    "Caldo Pets 卡朵毛孩生活",
    "Fluffy Pet | 犬貓生活選品",
    "好多毛寵物美容",
    "Kodomou 毛孩選物所",
    "趴趴狗寵物精品",
    "Buster & Beans 選物",
    "阿貴養了一隻牛",
    "汪喵精選"
]

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
# Google Sheets 連線函式
# ==========================================
def get_google_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    if "gcp_service_account" in os.environ:
        creds_dict = json.loads(os.environ["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        st.error("系統設定錯誤：找不到金鑰 (Render Environment Variable)。")
        st.stop()

    client = gspread.authorize(creds)
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
    st.title("守護者外出燈保固登錄")
    
    st.markdown("""
    ### 【三年原廠保固】
    凡購買 Orbiloc 守護者外出燈，在正常使用下（排除人為因素、寵物啃咬及不當拆解），我們提供長達三年的安心保固服務。

    ### 【登錄享好禮：免費電池維護】
    立即掃描 QR Code 完成線上保固登錄，即加贈 **「原廠電池＆防水圈維護服務」** 乙次。
    
    **兌換方式：** 請攜帶您的 Orbiloc 外出燈親臨原購買通路，提供「保固登錄之電話號碼」供門市人員查詢確認後，即可現場免費兌換維護。
    
    **貼心提醒：** 本服務採現場更換耗材制，恕不提供寄送服務，亦不可跨通路兌換*。  
    <small>*若原通路已停業或有其他特殊狀況，請洽總代理 LINE 客服 @bluebulous，我們將協助引導您至其他服務據點。</small>
    """, unsafe_allow_html=True)
    
    st.divider()

    # --- 步驟 1: 建立購買清單 ---
    st.subheader("1. 建立購買清單")
    st.caption("若購買多樣商品，請選取後點擊「加入清單」。")
    
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        selected_prod = st.selectbox("選擇產品", PRODUCT_LIST)
    with c2:
        selected_qty = st.number_input("數量", min_value=1, value=1, step=1)
    with c3:
        st.write("") 
        st.write("")
        add_btn = st.button("➕ 加入清單")

    if add_btn:
        st.session_state['cart'].append(f"{selected_prod} x{selected_qty}")
        st.success(f"已加入：{selected_prod} x{selected_qty}")

    if st.session_state['cart']:
        st.markdown("**🛒 目前已登錄商品：**")
        for i, item in enumerate(st.session_state['cart']):
            st.text(f"{i+1}. {item}")
        
        if st.button("🗑️ 清空重選"):
            st.session_state['cart'] = []
            st.rerun()
    else:
        st.info("尚未加入任何商品")

    st.divider()

    # --- 步驟 2: 填寫保固資訊 ---
    st.subheader("2. 填寫保固資訊")
    
    name = st.text_input("姓名")
    phone = st.text_input("電話 (作為查詢依據)", placeholder="09xxxxxxxx")
    email = st.text_input("Email")
    invoice = st.text_input("發票/收據/訂單編號")
    shop_name = st.selectbox("購買通路名稱 (請務必正確選擇)", SHOP_LIST)
    purchase_date = st.date_input("購買日期")

    if st.button("送出保固登記", type="primary"):
        if not (name and phone and invoice and shop_name):
            st.error("❌ 請填寫所有必填欄位！")
        elif not st.session_state['cart']:
            st.error("❌ 購買清單為空！")
        else:
            try:
                product_detail_str = ", ".join(st.session_state['cart'])
                data = sheet.get_all_records()
                
                # --- 修改重點：防止重複登記的邏輯 ---
                is_duplicate = False
                if data:
                    df = pd.DataFrame(data)
                    df.columns = [c.strip() for c in df.columns]
                    # 只有當「電話」和「發票號碼」都完全一樣時，才視為重複
                    # 這樣同一人(同電話)買不同張訂單(不同發票)就可以成功登記
                    if not df.empty and '電話' in df.columns and '發票' in df.columns:
                        # 檢查是否有一行同時符合這兩個條件
                        duplicate_check = df[
                            (df['電話'].astype(str) == str(phone)) & 
                            (df['發票'].astype(str) == str(invoice))
                        ]
                        if not duplicate_check.empty:
                            is_duplicate = True

                if is_duplicate:
                    st.warning("⚠️ 此發票號碼與電話已登記過，請勿重複送出。")
                else:
                    new_row = [
                        name, "'" + str(phone), email, invoice, shop_name, 
                        product_detail_str, str(purchase_date), 
                        str(datetime.now().date()), "No", "", ""
                    ]
                    sheet.append_row(new_row)
                    st.session_state['cart'] = []
                    st.balloons()
                    st.success(f"✅ 登記成功！資料已歸檔至【{shop_name}】。")

            except Exception as e:
                st.error(f"系統寫入錯誤：{e}")

# ==========================================
# 功能二：店家核銷專區 (支援多筆資料版)
# ==========================================
elif menu == "店家核銷專區":
    st.title("經銷商核銷登入")
    
    login_shop = st.selectbox("請選擇您的店家名稱", SHOP_LIST)
    password = st.text_input("請輸入店家通行碼", type="password")
    
    shop_credentials_json = os.environ.get("SHOP_CREDENTIALS", "{}")
    try:
        shop_credentials = json.loads(shop_credentials_json)
    except:
        shop_credentials = {}

    if st.button("登入系統"):
        if login_shop in shop_credentials and str(password) == str(shop_credentials[login_shop]):
            st.session_state['logged_in'] = True
            st.session_state['current_shop'] = login_shop
            st.success(f"歡迎 {login_shop}，登入成功！")
        else:
            st.error("密碼錯誤，或該店家尚未開通權限。")

    if st.session_state.get('logged_in') and st.session_state.get('current_shop') == login_shop:
        
        tab1, tab2 = st.tabs(["🔍 消費者核銷", "📋 本店銷售/登錄紀錄"])
        
        # === 分頁 1: 核銷功能 (重大更新：支援迴圈顯示多筆資料) ===
        with tab1:
            st.subheader(f"📍 {login_shop} - 核銷作業")
            st.error("⚠️ 請詳細確認【發票／訂單號碼】以及【產品明細】是否吻合以進行核銷") 
            
            search_phone = st.text_input("輸入消費者電話", key="search_phone")
            
            if st.button("搜尋資料"):
                data = sheet.get_all_records()
                if not data:
                    st.warning("目前資料庫為空。")
                else:
                    df = pd.DataFrame(data)
                    df.columns = [c.strip() for c in df.columns]
                    
                    if '電話' not in df.columns:
                        st.error("資料庫格式錯誤：缺少「電話」欄位。")
                    else:
                        df['電話'] = df['電話'].astype(str)
                        # 篩選出該店家的該客戶資料 (可能有多筆)
                        customers = df[
                            (df['電話'] == search_phone) & 
                            (df['購買通路名稱'] == login_shop)
                        ]
                        
                        if customers.empty:
                            check_all = df[df['電話'] == search_phone]
                            if not check_all.empty:
                                 st.warning("⚠️ 查無此人於本店的購買紀錄（該客戶可能是在其他通路購買）。")
                            else:
                                 st.error("查無此電話號碼。")
                        else:
                            st.success(f"✅ 找到 {len(customers)} 筆資料")
                            
                            # --- 迴圈顯示每一筆購買紀錄 ---
                            # iterrows 會回傳 index (在原始df的行數) 和 row (該行資料)
                            for index, record in customers.iterrows():
                                with st.container():
                                    st.markdown("---")
                                    # 使用 columns 排版讓資訊更清楚
                                    c1, c2 = st.columns([3, 1])
                                    
                                    with c1:
                                        st.write(f"**購買品項：** {record['購買品項及數量']}")
                                        st.caption(f"姓名：{record['姓名']} | 購買日：{record['購買日期']} | 發票：{record.get('發票', '未填寫')}")
                                    
                                    with c2:
                                        # 根據狀態顯示不同內容
                                        status = record['是否已兌換']
                                        if status == "Yes":
                                            st.warning(f"已於 {record['兌換日']} 兌換")
                                        else:
                                            # 為每個按鈕建立唯一的 key，避免衝突
                                            # row_index 需要 +2 才是 Google Sheet 真正的行數 (Header+1, 0-based+1)
                                            unique_key = f"btn_redeem_{index}"
                                            if st.button("🛠️ 執行核銷", key=unique_key):
                                                row_idx = index + 2
                                                sheet.update_cell(row_idx, 9, "Yes")
                                                sheet.update_cell(row_idx, 10, login_shop)
                                                sheet.update_cell(row_idx, 11, str(datetime.now().date()))
                                                st.balloons()
                                                st.success("核銷成功！")
                                                # 強制重新執行以更新畫面狀態
                                                st.rerun()

        # === 分頁 2: 本店歷史紀錄 ===
        with tab2:
            st.subheader(f"📋 {login_shop} - 歷史登錄名單")
            if st.button("載入/更新名單"):
                data = sheet.get_all_records()
                if not data:
                    st.info("尚無任何資料。")
                else:
                    df = pd.DataFrame(data)
                    df.columns = [c.strip() for c in df.columns]
                    if '購買通路名稱' in df.columns:
                        my_shop_data = df[df['購買通路名稱'] == login_shop]
                        if my_shop_data.empty:
                            st.info("目前尚無消費者登記於貴店名下。")
                        else:
                            display_cols = ['姓名', '電話', '發票', '購買品項及數量', '購買日期', '是否已兌換', '兌換日']
                            final_cols = [c for c in display_cols if c in my_shop_data.columns]
                            st.dataframe(my_shop_data[final_cols])
                            st.caption(f"共 {len(my_shop_data)} 筆資料")
                    else:
                        st.error("資料庫讀取錯誤。")
