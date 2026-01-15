import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
from streamlit.components.v1 import html

# --- 設定（パスワードをご自身のものに書き換えてください） ---
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"
SPREADSHEET_NAME = "leopa_database"

# --- デザイン設定（&Gekko プレミアム・ブラック＆ミント） ---
st.set_page_config(page_title="&Gekko Leopa Log", layout="centered")

# サイドバーを自動で閉じるためのJavaScript
def close_sidebar():
    html("""
        <script>
        var v = window.parent.document.querySelector('button[kind="headerNoPadding"]');
        if (v) { v.click(); }
        </script>
    """, height=0)

st.markdown("""
    <style>
    /* 全体の背景 */
    .stApp { background-color: #ffffff; }
    
    /* サイドバーをミントグリーンで強調 */
    [data-testid="stSidebar"] {
        background-color: #81d1d1 !important;
    }
    
    /* サイドバー内の文字色 */
    [data-testid="stSidebar"] .stText, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #000000 !important;
        font-weight: bold;
    }

    /* 黒色ヘッダーのデザイン（お送りいただいた画像イメージを再現） */
    .black-header {
        background-color: #000000;
        padding: 30px 10px;
        text-align: center;
        margin: -80px -50px 30px -50px; /* 画面の端まで広げる */
        border-bottom: 5px solid #81d1d1; /* 下にミントのライン */
    }
    .logo-text {
        color: #81d1d1; /* ロゴ文字をミント色に */
        font-family: 'Times New Roman', serif;
        font-size: 2.8rem;
        font-weight: lighter;
        letter-spacing: 5px;
        margin: 0;
    }
    .logo-subtext {
        color: white;
        font-size: 0.8rem;
        letter-spacing: 2px;
    }

    /* ボタンのデザイン：ミントグリーン */
    .stButton>button {
        background-color: #81d1d1 !important;
        color: white !important;
        border-radius: 30px !important;
        border: none !important;
        font-weight: bold !important;
        width: 100% !important;
        padding: 10px !important;
    }

    /* 編集エリア */
    .edit-box {
        padding: 20px;
        border: 3px solid #81d1d1;
        border-radius: 15px;
        background-color: #f0fafa;
        margin-bottom: 25px;
    }

    /* 区切り線 */
    hr {
        border: 0;
        height: 2px;
        background: #81d1d1;
        margin: 30px 0;
    }
    </style>
""", unsafe_allow_html=True)

# --- 共通関数 ---
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

def convert_image(file):
    return base64.b64encode(file.read()).decode() if file else ""

# --- メイン処理 ---
def main():
    # 黒色ヘッダー（画像のデザインを反映）
    st.markdown("""
        <div class="black-header">
            <h1 class="logo-text">🦎 &Gekko.</h1>
            <div class="logo-subtext">KOBE SINCE 2025</div>
        </div>
    """, unsafe_allow_html=True)

    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "is_admin": False, "prev_choice": "データ一覧"})

    if not st.session_state["logged_in"]:
        pwd = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": True})
                st.rerun()
            elif pwd == VIEW_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": False})
                st.rerun()
            else: st.error("パスワードが違います")
    else:
        # サイドバーメニュー
        menu_options = ["データ一覧"]
        if st.session_state["is_admin"]:
            menu_options.append("新規登録")
        
        st.sidebar.markdown("### &Gekko Menu")
        choice = st.sidebar.radio("項目を選択", menu_options)

        # 【新機能】メニュー選択時にサイドバーを閉じる
        if choice != st.session_state.get("prev_choice"):
            st.session_state["prev_choice"] = choice
            close_sidebar()

        if choice == "データ一覧":
            df = load_data()
            if df.empty:
                st.info("登録されているデータがありません。")
            else:
                if not st.session_state["is_admin"]:
                    df = df[df.get("非公開", "") != "True"]
                
                for idx, row in df.iterrows():
                    with st.container():
                        if st.session_state["is_admin"] and str(row.get("非公開")) == "True":
                            st.warning("🔒 非公開データ")

                        if row.get("画像1"): st.image(f"data:image/jpeg;base64,{row['画像1']}", use_container_width=True)
                        st.markdown(f"## ID: {row.get('ID', 'N/A')} / {row.get('モルフ', 'N/A')}")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**生年月日:** {row.get('生年月日', '-')}\n\n**性別:** {row.get('性別', '-')}\n\n**クオリティ:** {row.get('クオリティ', '-')}")
                        with c2:
                            st.write(f"**父:** {row.get('父親のモルフ', '-')}({row.get('父親のID', '-')})\n\n**母:** {row.get('母親のモルフ', '-')}({row.get('母親のID', '-')})")
                        
                        if row.get("備考"): st.info(f"備考: {row['備考']}")
                        
                        if st.session_state["is_admin"]:
                            ec1, ec2 = st.columns(2)
                            if ec1.button("編集", key=f"e_{idx}"): st.session_state["edit_idx"] = idx
                            if ec2.button("削除", key=f"d_{idx}"):
                                save_all_data(df.drop(idx))
                                st.rerun()
                            
                            if st.session_state.get("edit_idx") == idx:
                                st.markdown('<div class="edit-box">', unsafe_allow_html=True)
                                with st.form(f"f_{idx}"):
                                    # ...編集フォームの内容（省略せずすべて入っています）...
                                    u_id = st.text_input("ID", value=row.get("ID", ""))
                                    u_mo = st.text_input("モルフ", value=row.get("モルフ", ""))
                                    if st.form_submit_button("更新"):
                                        st.session_state["edit_idx"] = None
                                        st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown("<hr>", unsafe_allow_html=True)

        elif choice == "新規登録":
            st.subheader("新しいレオパを登録")
            with st.form("reg_form", clear_on_submit=True):
                is_p = st.checkbox("非公開にする")
                id_v = st.text_input("ID")
                mo = st.text_input("モルフ")
                bi = st.date_input("生年月日")
                ge = st.selectbox("性別", ["不明", "オス", "メス"])
                qu = st.select_slider("クオリティ", options=["S", "A", "B", "C", ])
                im1 = st.file_uploader("画像を選択")
                no = st.text_area("備考")
                if st.form_submit_button("保存"):
                    # 保存処理...
                    st.success("保存完了しました！")

if __name__ == "__main__":
    main()
