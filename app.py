import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

# --- 設定頁面資訊 ---
st.set_page_config(page_title="Orbiloc 守護者外出燈保固註冊系統", page_icon="🛡️", layout="centered")

# --- 初始化 Session State ---
if 'cart' not in st.session_state:
    st.session_state['cart'] = []
if 'form_submitted' not in st.session_state:
    st.session_state['form_submitted'] = False

# 初始化搜尋狀態
if 'has_searched' not in st.session_state:
    st.session_state['has_searched'] = False
if 'search_phone_number' not in st.session_state:
    st.session_state['search_phone_number'] = ""

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
# 函式區：Google Sheet & Email
# ==========================================

@st.cache_resource
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

def send_email_background(to_email, customer_name, shop_name, product_details, purchase_date):
    gmail_user = os.environ.get("MAIL_USER")
    gmail_password = os.environ.get("MAIL_PASSWORD")
    bcc_email = os.environ.get("BCC_EMAIL")

    if not gmail_user or not gmail_password:
        print("❌ Email 設定缺失：請檢查 Render 環境變數")
        return

    msg = MIMEMultipart()
    msg['From'] = f"Orbiloc Taiwan <{gmail_user}>"
    msg['To'] = to_email
    msg['Subject'] = "【保固登錄成功】Orbiloc 守護者外出燈"

    recipients = [to_email]
    if bcc_email:
        recipients.append(bcc_email)

    body = f"""
    Dear {customer_name},

    感謝您購買 Orbiloc 守護者外出燈！
    您的保固資料已成功登錄，詳細資訊如下：

    --------------------------------------
    購買通路：{shop_name}
    登錄產品：{product_details}
    購買日期：{purchase_date}
    登錄日期：{datetime.now().strftime('%Y-%m-%d')}
    --------------------------------------

    【好禮兌換說明】
    在購買日起算一年內，攜帶您的 Orbiloc 外出燈親臨原購買通路 ({shop_name})，
    提供「保固登錄之電話號碼」供門市人員查詢確認後，
    即可現場享有「原廠電池＆防水圈維護服務」乙次。

    ※ 本服務採現場更換耗材制，恕不提供寄送服務。

    Orbiloc 台灣總代理
    Bluebulous 布魯樂斯
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        print("📨 嘗試連線到 Gmail SMTP (Port 465)...")
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
        
        print("🔐 登入中...")
        server.login(gmail_user, gmail_password)
        
        print("🚀 發送郵件中...")
        server.sendmail(gmail_user, recipients, msg.as_string())
        server.quit()
        print(f"✅ Email 成功發送給 {to_email}")
        
    except Exception as e:
        print(f"❌ Email 發送失敗 (詳細錯誤): {str(e)}")

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
    
    if st.session_state['form_submitted']:
        st.balloons()
        st.success("🎉 保固登錄成功！")
        
        st.info("系統正在背景發送確認信至您的信箱，請稍候查收（若未收到請檢查垃圾郵件夾）。")
        
        st.markdown(f"""
        ### 您的資料已成功建檔
        
        **【如何兌換免費維護？】** 請於方便的時間，攜帶您的外出燈前往 **{st.session_state.get('last_shop_name', '原購買通路')}**，
        告知店員您的 **電話號碼** 即可進行核銷與維護。
        
        感謝您選擇 Orbiloc 守護毛孩的安全！
        """)
        
        st.divider()
        if st.button("回首頁 (登錄下一筆)"):
            st.session_state['form_submitted'] = False
            st.session_state['cart'] = []
            st.rerun()
            
    else:
        st.title("守護者外出燈保固登錄")
        
        st.markdown("""
        ### 【三年原廠保固】
        凡購買 Orbiloc 守護者外出燈，在正常使用下（排除人為因素、寵物啃咬及不當拆解），我們提供長達三年的安心保固服務。

        ### 【登錄享好禮：免費電池維護】
        立即掃描 QR Code 完成線上保固登錄，即加贈 **「原廠電池＆防水圈維護服務」** 乙次。
        
        **兌換方式：** 在購買日起算一年內，請攜帶您的 Orbiloc 外出燈親臨原購買通路，提供「保固登錄之電話號碼」供門市人員查詢確認後，即可現場免費兌換維護。
        
        **貼心提醒：** 本服務採現場更換耗材制，恕不提供寄送服務，亦不可跨通路兌換*。  
        <small>*若原通路已停業或有其他特殊狀況，請洽總代理 LINE 客服 @bluebulous，我們將協助引導您至其他服務據點。</small>
        """, unsafe_allow_html=True)
        
        st.divider()

        st.subheader("1. 登錄產品清單")
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

        st.subheader("2. 填寫保固資訊")
        st.caption("請正確填寫資料，以免影響保固資格")
        
        with st.form("final_submission_form"):
            name = st.text_input("姓名")
            phone = st.text_input("電話 (數字請連號輸入，勿輸入任何符號)", placeholder="09xxxxxxxx")
            email = st.text_input("Email (將寄送確認信)", placeholder="example@email.com")
            invoice = st.text_input("發票/收據/訂單編號")
            shop_name = st.selectbox("購買通路名稱 (請務必正確選擇)", SHOP_LIST)
            purchase_date = st.date_input("購買日期")

            submitted = st.form_submit_button("送出保固登記", type="primary")

        if submitted:
            if not (name and phone and invoice and shop_name):
                st.error("❌ 請填寫所有必填欄位 (姓名、電話、發票、通路)！")
            elif not st.session_state['cart']:
                st.error("❌ 購買清單為空，請先在上方加入商品！")
            else:
                try:
                    product_detail_str_for_email = ", ".join(st.session_state['cart'])
                    
                    data = sheet.get_all_records()
                    is_duplicate = False
                    
                    # ===== 修改重點：嚴格檢查「發票/訂單號碼」 =====
                    if data:
                        df = pd.DataFrame(data)
                        df.columns = [c.strip() for c in df.columns]
                        if not df.empty and '發票' in df.columns:
                            input_invoice = str(invoice).strip()
                            
                            # 只要發票欄位裡有一模一樣的號碼，就視為重複！(不再管電話是不是同一個)
                            duplicate_check = df[df['發票'].astype(str).str.strip() == input_invoice]
                            
                            if not duplicate_check.empty:
                                is_duplicate = True
                    # ==========================================

                    if is_duplicate:
                        st.warning(f"⚠️ 發票/訂單號碼「{invoice}」已登記過，請勿重複送出！如有疑問請洽客服。")
                    else:
                        # 拆分購物車，多筆寫入 (支援單顆核銷)
                        rows_to_insert = []
                        for item in st.session_state['cart']:
                            prod_name, qty_str = item.rsplit(' x', 1)
                            qty = int(qty_str)
                            
                            for _ in range(qty):
                                new_row = [
                                    name, str(phone), email, invoice, shop_name, 
                                    f"{prod_name} x1", # 強制標示為 1 個
                                    str(purchase_date), 
                                    str(datetime.now().date()), "No", "", ""
                                ]
                                rows_to_insert.append(new_row)
                        
                        sheet.append_rows(rows_to_insert)

                        if email:
                            email_thread = threading.Thread(
                                target=send_email_background, 
                                args=(email, name, shop_name, product_detail_str_for_email, str(purchase_date))
                            )
                            email_thread.start()
                        
                        st.session_state['form_submitted'] = True
                        st.session_state['last_shop_name'] = shop_name 
                        st.rerun()

                except Exception as e:
                    st.error(f"系統寫入錯誤：{e}")

# ==========================================
# 功能二：店家核銷專區
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
        
        # === 分頁 1: 核銷功能 ===
        with tab1:
            st.subheader(f"📍 {login_shop} - 核銷作業")
            st.error("⚠️ 請詳細確認【發票／訂單號碼】以及【產品明細】是否吻合以進行核銷") 
            
            phone_input = st.text_input("輸入消費者電話", key="phone_input")
            
            if st.button("搜尋資料"):
                st.session_state['has_searched'] = True
                st.session_state['search_phone_number'] = phone_input
            
            if st.session_state['has_searched'] and st.session_state['search_phone_number']:
                
                data = sheet.get_all_records()
                if not data:
                    st.warning("目前資料庫為空。")
                else:
                    df = pd.DataFrame(data)
                    df.columns = [c.strip() for c in df.columns]
                    
                    if '電話' not in df.columns:
                        st.error("資料庫格式錯誤：缺少「電話」欄位。")
                    else:
                        df['clean_phone'] = df['電話'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace("'", "", regex=False).str.strip()
                        df['clean_phone'] = df['clean_phone'].apply(lambda x: "0" + x if len(x) == 9 and x.isdigit() else x)
                        
                        input_phone = str(st.session_state['search_phone_number']).strip()

                        customers = df[
                            (df['clean_phone'] == input_phone) & 
                            (df['購買通路名稱'] == login_shop)
                        ]
                        
                        if customers.empty:
                            check_all = df[df['clean_phone'] == input_phone]
                            if not check_all.empty:
                                 st.warning("⚠️ 查無此人於本店的購買紀錄（該客戶可能是在其他通路購買）。")
                            else:
                                 st.error("查無此電話號碼。")
                        else:
                            st.success(f"✅ 找到 {len(customers)} 筆可核銷商品 (已自動拆分顯示)")
                            
                            for index, record in customers.iterrows():
                                with st.container():
                                    st.markdown("---")
                                    c1, c2 = st.columns([3, 1])
                                    with c1:
                                        st.write(f"**產品：** {record['購買品項及數量']}")
                                        st.caption(f"姓名：{record['姓名']} | 購買日：{record['購買日期']} | 發票：{record.get('發票', '未填寫')}")
                                    with c2:
                                        status = record['是否已兌換']
                                        if status == "Yes":
                                            st.warning(f"已於 {record['兌換日']} 兌換")
                                        else:
                                            unique_key = f"btn_redeem_{index}"
                                            if st.button("🛠️ 執行核銷", key=unique_key):
                                                try:
                                                    row_idx = index + 2
                                                    sheet.update_cell(row_idx, 9, "Yes")
                                                    sheet.update_cell(row_idx, 10, login_shop)
                                                    sheet.update_cell(row_idx, 11, str(datetime.now().date()))
                                                    st.toast("✅ 核銷成功！資料已更新")
                                                    st.balloons()
                                                    st.rerun()
                                                except Exception as e:
                                                    st.error(f"核銷失敗：{e}")

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
                    
                    if '購買通路名稱' in df.columns and '電話' in df.columns:
                        
                        df['電話'] = df['電話'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace("'", "", regex=False).str.strip()
                        df['電話'] = df['電話'].apply(lambda x: "0" + x if len(x) == 9 and x.isdigit() else x)
                        
                        my_shop_data = df[df['購買通路名稱'] == login_shop]
                        
                        if my_shop_data.empty:
                            st.info("目前尚無消費者登記於貴店名下。")
                        else:
                            display_cols = ['姓名', '電話', '發票', '購買品項及數量', '購買日期', '是否已兌換', '兌換日']
                            final_cols = [c for c in display_cols if c in my_shop_data.columns]
                            st.dataframe(my_shop_data[final_cols])
                            st.caption(f"共 {len(my_shop_data)} 筆商品資料")
                    else:
                        st.error("資料庫讀取錯誤：缺少「電話」或「購買通路名稱」欄位。")
