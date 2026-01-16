import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
import os
from datetime import datetime

# --- 基本設定 ---
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"
SPREADSHEET_NAME = "leopa_database"

st.set_page_config(page_title="&Gekko Album", layout="wide")

# --- デザイン（CSS） ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .header-container {
        text-align: center;
        margin: -70px -50px 0px -50px;
        background-color: #000000;
        border-bottom: 4px solid #81d1d1;
    }
    div.stRadio > div {
        flex-direction: row;
        justify-content: center;
        background-color: #f0fafa;
        padding: 10px 0;
        border-bottom: 1px solid #81d1d1;
        margin-bottom: 20px;
    }
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
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 共通関数 ---
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

# --- メイン処理 ---
def main():
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

                cols = st.columns(2)
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
                        with st.expander("詳細データを見る"):
                            st.write(f"**性別:** {row.get('性別', '-')}")
                            st.write(f"**誕生日:** {row.get('生年月日', '-')}")
                            st.write(f"**クオリティ:** {row.get('クオリティ', '-')}")
                            st.markdown("---")
                            st.write(f"**父親ID:** {row.get('父親ID', '-')}")
                            st.write(f"**父親モルフ:** {row.get('父親モルフ', '-')}")
                            st.write(f"**母親ID:** {row.get('母親ID', '-')}")
                            st.write(f"**母親モルフ:** {row.get('母親モルフ', '-')}")
                            st.markdown("---")
                            st.write(f"**備考:** {row.get('備考', '-')}")
                            if row.get("画像2"):
                                st.image(f"data:image/jpeg;base64,{row['画像2']}", use_container_width=True)
                            if st.session_state["is_admin"]:
                                if st.button("削除", key=f"del_{idx}"):
                                    save_all_data(df.drop(idx)); st.rerun()

        elif "新規登録" in choice:
            df_current = load_data()
            st.subheader("新しいレオパを登録")
            
            # 1. 誕生年だけをまず選ぶ
            this_year = datetime.now().year
            years = [str(y) for y in range(this_year, this_year - 15, -1)]
            selected_year = st.selectbox("誕生年を選択", years)
            
            # 2. IDのプレフィックス（26など）を自動作成
            year_prefix = selected_year[2:]
            count_in_year = 0
            if not df_current.empty:
                ids = df_current["ID"].astype(str)
                count_in_year = len(ids[ids.str.startswith(year_prefix)])
            auto_id_val = f"{year_prefix}{count_in_year + 1:03d}"

            with st.form("reg_form", clear_on_submit=True):
                is_p = st.checkbox("非公開にする")
                
                col1, col2 = st.columns(2)
                with col1:
                    # IDは自動で頭2文字が入るが、手入力も可能
                    id_v = st.text_input("個体ID", value=auto_id_val)
                    # 生年月日はテキスト入力に。月日が不明なら「不明」と書けます。
                    bi_str = st.text_input("生年月日 (例: 2026/05/10, 2026/不明)", value=f"{selected_year}/")
                
                with col2:
                    mo = st.text_input("モルフ")
                    ge = st.selectbox("性別", ["不明", "オス", "メス"])
                
                qu = st.select_slider("クオリティ", options=["S", "A", "B", "C"])
                
                st.markdown("---")
                st.write("🧬 **血統情報**")
                f_id = st.text_input("父親のID")
                f_mo = st.text_input("父親のモルフ")
                m_id = st.text_input("母親のID")
                m_mo = st.text_input("母親のモルフ")
                st.markdown("---")
                
                im1 = st.file_uploader("画像1枚目 (メイン)", type=["jpg", "jpeg", "png"])
                im2 = st.file_uploader("画像2枚目 (詳細用)", type=["jpg", "jpeg", "png"])
                no = st.text_area("備考")
                
                if st.form_submit_button("保存する"):
                    new_data = {
                        "ID":id_v, "モルフ":mo, "生年月日":bi_str, "性別":ge, "クオリティ":qu,
                        "父親ID":f_id, "父親モルフ":f_mo, "母親ID":m_id, "母親モルフ":m_mo,
                        "画像1":convert_image(im1), "画像2":convert_image(im2), "備考":no, "非公開": str(is_p)
                    }
                    df_all = pd.concat([df_current, pd.DataFrame([new_data])], ignore_index=True)
                    save_all_data(df_all)
                    st.success(f"ID {id_v} で保存しました！")
                    st.balloons()

if __name__ == "__main__":
    main()
