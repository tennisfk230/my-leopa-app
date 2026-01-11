import streamlit as st
import pandas as pd
from datetime import datetime
import os
import json
from google.oauth2.service_account import Credentials
import gspread

# --- 設定 ---
# スプレッドシートの名前（あなたが作った名前に合わせてください）
SPREADSHEET_NAME = "leopa_database"
# パスワード（以前決めたもの）
CORRECT_PASSWORD = "lucafk" 

# --- Googleスプレッドシートへの接続 ---
@st.cache_resource
def get_gspread_client():
    # GitHub Secretsに保存したJSONを取得
    service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(credentials)

def load_data_from_sheets():
    client = get_gspread_client()
    sheet = client.open(SPREADSHEET_NAME).sheet1
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=['ID', 'モルフ', '生年月日', '生後日数', '性別', '父親ID', '父親モルフ', '母親ID', '母親モルフ', 'クオリティ', '備考', '画像パス', '画像パス2'])
    return pd.DataFrame(data)

def save_data_to_sheets(df):
    client = get_gspread_client()
    sheet = client.open(SPREADSHEET_NAME).sheet1
    sheet.clear()
    
    # 列の名前（ヘッダー）をリストにする
    header = df.columns.values.tolist()
    # 全データを文字列に変換し、リストのリスト形式にする
    values = df.astype(str).values.tolist()
    
    # まとめて更新（この書き方が最新の安定版です）
    sheet.update(range_name='A1', values=[header] + values)
# パスワード認証
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if password == CORRECT_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います")
else:
    # データ読み込み
    df = load_data_from_sheets()

    # サイドバーメニュー
    menu = st.sidebar.selectbox("メニュー", ["データ一覧", "新規登録"])

    if menu == "データ一覧":
        st.header("レオパデータ一覧")
        if df.empty:
            st.write("データがありません。")
        else:
            st.dataframe(df)
            
    elif menu == "新規登録":
        st.header("新しいレオパを登録")
        with st.form("registration_form"):
            leopa_id = st.text_input("ID")
            morph = st.text_input("モルフ")
            birth_date = st.date_input("生年月日", value=datetime.today())
            gender = st.selectbox("性別", ["不明", "オス", "メス"])
            memo = st.text_area("備考")
            
            submitted = st.form_submit_button("登録")
            if submitted:
                new_data = {
                    'ID': leopa_id, 'モルフ': morph, '生年月日': str(birth_date),
                    '生後日数': (datetime.today().date() - birth_date).days,
                    '性別': gender, '備考': memo
                }
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                save_data_to_sheets(df)
                st.success(f"ID: {leopa_id} をスプレッドシートに保存しました！")

    if st.sidebar.button("ログアウト"):
        st.session_state.authenticated = False
        st.rerun()


