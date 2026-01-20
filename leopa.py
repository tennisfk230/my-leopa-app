import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
import os
from datetime import datetime
import io
from PIL import Image

# --- 1. 基本設定 ---
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"
SPREADSHEET_NAME = "leopa_database"

st.set_page_config(page_title="&Gekko System", layout="wide", page_icon="🦎")

# --- 2. プロ仕様デザイン ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .header-container { text-align: center; margin-bottom: 20px; border-bottom: 3px solid #81d1d1; }
    .leopa-card { border: 1px solid #eee; border-radius: 12px; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; overflow: hidden; }
    .img-container { width: 100%; aspect-ratio: 1 / 1; overflow: hidden; position: relative; }
    .img-container img { width: 100%; height: 100%; object-fit: cover; }
    .badge-sex { position: absolute; top: 10px; right: 10px; padding: 5px 10px; border-radius: 20px; color: white; font-weight: bold; font-size: 0.8rem; }
    .male { background-color: #5dade2; }
    .female { background-color: #ec7063; }
    .unknown { background-color: #aeb6bf; }
    .badge-quality { position: absolute; top: 10px; left: 10px; background-color: rgba(0,0,0,0.6); color: #f1c40f; padding: 2px 8px; border-radius: 5px; font-size: 0.8rem; font-weight: bold; border: 1px solid #f1c40f; }
    [data-testid="stSidebar"] { display: none; }
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
    data = [df.columns.values.tolist()] + df.astype(str).values.tolist()
    sheet.update(data, 'A1') # 最新のgspread用書き方

# 📸 画像をリサイズして軽量化する関数 (最重要)
def convert_image(file):
    if file:
        img = Image.open(file)
        img = img.convert("RGB") # PNG対策
        # 最大800pxに縮小（スプレッドシートの文字数制限対策）
        img.thumbnail((800, 800))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70) # 画質70%で圧縮
        return base64.b64encode(buf.getvalue()).decode()
    return ""

# --- 4. メイン処理 ---
def main():
    if os.path.exists("logo_gekko.png"):
        st.markdown('<div class="header-container">', unsafe_allow_html=True)
        st.image("logo_gekko.png", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "is_admin": False})

    if not st.session_state["logged_in"]:
        st.write("### 🔐 MEMBER LOGIN")
        pwd = st.text_input("パスワードを入力", type="password")
        if st.button("ログイン"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": True}); st.rerun()
            elif pwd == VIEW_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": False}); st.rerun()
            else: st.error("パスワードが違います")
    else:
        df = load_data()
        tabs = st.tabs(["📊 ダッシュボード", "🦎 アルバム・検索", "➕ 新規登録"])

        with tabs[0]: # ダッシュボード
            if not df.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric("総数", f"{len(df)}匹")
                c2.metric("♂", f"{len(df[df['性別']=='オス'])}匹")
                c3.metric("♀", f"{len(df[df['性別']=='メス'])}匹")
                st.bar_chart(df['モルフ'].value_counts())

        with tabs[1]: # アルバム
            if df.empty: st.info("データがありません")
            else:
                search = st.text_input("検索 (モルフ名など)")
                v_df = df[df['モルフ'].str.contains(search, case=False)] if search else df
                cols = st.columns(2)
                for i, (idx, row) in enumerate(v_df.iterrows()):
                    with cols[i % 2]:
                        sex_c = "male" if row['性別']=="オス" else "female" if row['性別']=="メス" else "unknown"
                        st.markdown(f'<div class="leopa-card"><div class="img-container"><span class="badge-quality">{row["クオリティ"]}</span><span class="badge-sex {sex_c}">{row["性別"]}</span><img src="data:image/jpeg;base64,{row["画像1"]}"></div><div style="padding:10px;"><b>{row["ID"]}</b><br><small>{row["モルフ"]}</small></div></div>', unsafe_allow_html=True)
                        with st.expander("詳細"):
                            st.write(f"誕生日: {row['生年月日']}")
                            st.write(f"備考: {row['備考']}")
                            if st.button("削除", key=f"del_{idx}"):
                                save_all_data(df.drop(idx)); st.rerun()

        with tabs[2]: # 登録
            this_year = datetime.now().year
            years = [str(y) for y in range(this_year, this_year - 10, -1)]
            sel_year = st.selectbox("誕生年", years)
            prefix = sel_year[2:]
            count = len(df[df['ID'].astype(str).str.startswith(prefix)]) if not df.empty else 0
            
            with st.form("reg"):
                id_v = st.text_input("ID", value=f"{prefix}{count+1:03d}")
                mo = st.text_input("モルフ")
                bi = st.text_input("生年月日", value=f"{sel_year}/")
                ge = st.selectbox("性別", ["不明", "オス", "メス"])
                qu = st.select_slider("クオリティ", options=["S", "A", "B", "C"])
                im1 = st.file_uploader("画像")
                if st.form_submit_button("保存"):
                    new = {"ID":id_v, "モルフ":mo, "生年月日":bi, "性別":ge, "クオリティ":qu, "画像1":convert_image(im1), "備考":""}
                    save_all_data(pd.concat([df, pd.DataFrame([new])], ignore_index=True))
                    st.success("保存完了"); st.rerun()

if __name__ == "__main__":
    main()
