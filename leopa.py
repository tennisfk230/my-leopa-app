import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
import os
from streamlit.components.v1 import html

# --- 設定 ---
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"
SPREADSHEET_NAME = "leopa_database"

# --- デザイン設定（&Gekko アルバムスタイル） ---
st.set_page_config(page_title="&Gekko Album", layout="wide") # 広く使うためにwideに設定

def close_sidebar():
    html("""<script>var v = window.parent.document.querySelector('button[kind="headerNoPadding"]'); if (v) { v.click(); }</script>""", height=0)

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #81d1d1 !important; }
    
    /* ヘッダー */
    .header-container {
        text-align: center;
        margin: -70px -50px 30px -50px;
        background-color: #000000;
        border-bottom: 4px solid #81d1d1;
    }

    /* インスタ風カードデザイン */
    .leopa-card {
        border: 1px solid #e0f2f2;
        border-radius: 10px;
        padding: 0px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        transition: 0.3s;
    }
    .leopa-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px rgba(129, 209, 209, 0.3);
    }

    /* 画像を正方形に整える */
    .img-container {
        width: 100%;
        aspect-ratio: 1 / 1;
        overflow: hidden;
        border-radius: 10px 10px 0 0;
    }
    .img-container img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    /* テキスト部分 */
    .card-text {
        padding: 10px;
        text-align: center;
    }
    .card-id { font-weight: bold; color: #333; font-size: 0.9rem; }
    .card-morph { color: #81d1d1; font-size: 0.8rem; font-weight: bold; }

    /* ボタン類 */
    .stButton>button {
        background-color: #81d1d1 !important;
        color: white !important;
        border-radius: 20px !important;
        border: none !important;
        font-size: 0.8rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 共通関数（省略なしでそのままお使いください） ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return gspread.authorize(creds)

def load_data():
    client = get_gspread_client()
    sheet = client.open(SPREADSHEET_NAME).sheet1
    return pd.DataFrame(sheet.get_all_records())

def save_all_data(df):
    client = get_gspread_client()
    sheet = client.open(SPREADSHEET_NAME).sheet1
    sheet.clear()
    sheet.update(range_name='A1', values=[df.columns.values.tolist()] + df.astype(str).values.tolist())

# --- メイン処理 ---
def main():
    # ヘッダー表示
    if os.path.exists("logo_gekko.png"):
        st.markdown('<div class="header-container">', unsafe_allow_html=True)
        st.image("logo_gekko.png", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "is_admin": False, "prev_choice": "データ一覧"})

    if not st.session_state["logged_in"]:
        pwd = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pwd == ADMIN_PASSWORD: st.session_state.update({"logged_in": True, "is_admin": True}); st.rerun()
            elif pwd == VIEW_PASSWORD: st.session_state.update({"logged_in": True, "is_admin": False}); st.rerun()
            else: st.error("パスワードが違います")
    else:
        menu_options = ["アルバム一覧", "新規登録"] if st.session_state["is_admin"] else ["アルバム一覧"]
        choice = st.sidebar.radio("メニュー", menu_options)
        if choice != st.session_state.get("prev_choice"):
            st.session_state["prev_choice"] = choice
            close_sidebar()

        if choice == "アルバム一覧":
            df = load_data()
            if df.empty:
                st.info("データがありません。")
            else:
                if not st.session_state["is_admin"]:
                    df = df[df.get("非公開", "") != "True"]

                # ★ インスタ風グリッドの作成 ★
                # PCは3列、スマホは自動で2列程度に調整されます
                cols = st.columns(3) 
                
                for idx, row in df.iterrows():
                    with cols[idx % 3]: # 順番に列に振り分け
                        # カード全体の枠
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
                        
                        # 詳細確認用のボタン（アコーディオン）
                        with st.expander("詳細を見る"):
                            st.write(f"**性別:** {row.get('性別', '-')}")
                            st.write(f"**誕生日:** {row.get('生年月日', '-')}")
                            st.write(f"**クオリティ:** {row.get('クオリティ', '-')}")
                            if row.get("画像2"):
                                st.image(f"data:image/jpeg;base64,{row['画像2']}", use_container_width=True)
                            
                            if st.session_state["is_admin"]:
                                if st.button("削除", key=f"del_{idx}"):
                                    save_all_data(df.drop(idx))
                                    st.rerun()

        elif choice == "新規登録":
            # 新規登録のフォーム（前回の内容を維持）
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
                    # 保存処理（前回のロジックと同じ）
                    def convert_image(file):
                        return base64.b64encode(file.read()).decode() if file else ""
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
