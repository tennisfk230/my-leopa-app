import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
import os

# --- 1. 基本設定 ---
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"
SPREADSHEET_NAME = "leopa_database"

st.set_page_config(page_title="&Gekko Album", layout="wide")

# --- 2. デザイン（CSS） ---
st.markdown("""
    <style>
    /* 全体の背景 */
    .stApp { background-color: #ffffff; }
    
    /* ヘッダーロゴ部分 */
    .header-container {
        text-align: center;
        margin: -70px -50px 0px -50px;
        background-color: #000000;
        border-bottom: 4px solid #81d1d1;
    }

    /* メニューボタン（横並び）のデザイン */
    div.stRadio > div {
        flex-direction: row;
        justify-content: center;
        background-color: #f0fafa;
        padding: 10px 0;
        border-bottom: 1px solid #81d1d1;
        margin-bottom: 20px;
    }
    div.stRadio div[data-testid="stMarkdownContainer"] > p {
        font-size: 1.1rem !important;
        font-weight: bold;
    }

    /* インスタ風カード */
    .leopa-card {
        border: 1px solid #e0f2f2;
        border-radius: 12px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        overflow: hidden;
    }
    .img-container {
        width: 100%;
        aspect-ratio: 1 / 1;
        overflow: hidden;
    }
    .img-container img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .card-text { padding: 10px; text-align: center; }
    .card-id { font-weight: bold; color: #333; font-size: 1rem; }
    .card-morph { color: #81d1d1; font-size: 0.85rem; font-weight: bold; }

    /* サイドバーを完全に隠す（不要になったため） */
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 共通関数 ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return gspread.authorize(creds)

def load_data():
    try:
        client = get_gspread_client()
        sheet = client.open(SPREADSHEET_NAME).sheet1
        return pd.DataFrame(sheet.get_all_records())
    except:
        return pd.DataFrame()

def save_all_data(df):
    client = get_gspread_client()
    sheet = client.open(SPREADSHEET_NAME).sheet1
    sheet.clear()
    sheet.update(range_name='A1', values=[df.columns.values.tolist()] + df.astype(str).values.tolist())

def convert_image(file):
    return base64.b64encode(file.read()).decode() if file else ""

# --- 4. メイン処理 ---
def main():
    # ロゴ表示
    if os.path.exists("logo_gekko.png"):
        st.markdown('<div class="header-container">', unsafe_allow_html=True)
        st.image("logo_gekko.png", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "is_admin": False})

    if not st.session_state["logged_in"]:
        st.write("### ログイン")
        pwd = st.text_input("パスワードを入力", type="password")
        if st.button("ログイン"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": True}); st.rerun()
            elif pwd == VIEW_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": False}); st.rerun()
            else: st.error("パスワードが違います")
    else:
        # 【新案】画面上部にメニューを配置
        menu_options = ["🏠 アルバム一覧", "➕ 新規登録"] if st.session_state["is_admin"] else ["🏠 アルバム一覧"]
        choice = st.radio("", menu_options, horizontal=True)

        if "アルバム一覧" in choice:
            df = load_data()
            if df.empty:
                st.info("データがありません。")
            else:
                if not st.session_state["is_admin"]:
                    if "非公開" in df.columns:
                        df = df[df["非公開"] != "True"]

                cols = st.columns(2) # スマホで見やすいよう2列に
                for idx, row in df.iterrows():
                    with cols[idx % 2]:
                        st.markdown(f"""
                            <div class="leopa-card">
                                <div class="img-container">
                                    <img src="data:image/jpeg;base64,{row.get('画像1', '')}">
                                </div>
                                <div class="card-text">
                                    <div class="card-id">ID: {row.get('ID', '-')}</div>
                                    <div class="card-morph">{row.get('モルフ', '-')}</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        with st.expander("詳細"):
                            st.write(f"**性別:** {row.get('性別', '-')}")
                            st.write(f"**誕生日:** {row.get('生年月日', '-')}")
                            if row.get("画像2"):
                                st.image(f"data:image/jpeg;base64,{row['画像2']}", use_container_width=True)
                            if st.session_state["is_admin"]:
                                if st.button("削除", key=f"del_{idx}"):
                                    save_all_data(df.drop(idx)); st.rerun()

        elif "新規登録" in choice:
            st.subheader("新しいレオパを登録")
            with st.form("reg_form", clear_on_submit=True):
                is_p = st.checkbox("非公開にする")
                id_v = st.text_input("ID")
                mo = st.text_input("モルフ")
                bi = st.date_input("生年月日")
                ge = st.selectbox("性別", ["不明", "オス", "メス"])
                qu = st.select_slider("クオリティ", options=["S", "A", "B", "C", ])
                im1 = st.file_uploader("画像1枚目", type=["jpg", "jpeg", "png"])
                im2 = st.file_uploader("画像2枚目", type=["jpg", "jpeg", "png"])
                no = st.text_area("備考")
                if st.form_submit_button("保存する"):
                    df_new = load_data()
                    new_data = {
                        "ID":id_v, "モルフ":mo, "生年月日":str(bi), "性別":ge, "クオリティ":qu, 
                        "画像1":convert_image(im1), "画像2":convert_image(im2), "備考":no, "非公開": str(is_p)
                    }
                    df_all = pd.concat([df_new, pd.DataFrame([new_data])], ignore_index=True)
                    save_all_data(df_all)
                    st.success("保存完了しました！")

if __name__ == "__main__":
    main()
