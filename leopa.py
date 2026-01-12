import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# --- パスワード設定 ---
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"

# --- スプレッドシート設定 ---
SPREADSHEET_NAME = "leopa_database"

def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return gspread.authorize(creds)

def load_data_from_sheets():
    client = get_gspread_client()
    sheet = client.open(SPREADSHEET_NAME).sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def save_data_to_sheets(df):
    client = get_gspread_client()
    sheet = client.open(SPREADSHEET_NAME).sheet1
    sheet.clear()
    header = df.columns.values.tolist()
    values = df.astype(str).values.tolist()
    sheet.update(range_name='A1', values=[header] + values)

def main():
    st.title("レオパ管理システム")

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        password = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if password == ADMIN_PASSWORD:
                st.session_state["logged_in"] = True
                st.session_state["is_admin"] = True
                st.rerun()
            elif password == VIEW_PASSWORD:
                st.session_state["logged_in"] = True
                st.session_state["is_admin"] = False
                st.rerun()
            else:
                st.error("パスワードが違います")
    else:
        # メニュー設定
        menu = ["データ一覧"]
        if st.session_state["is_admin"]:
            menu.append("新規登録")
        
        choice = st.sidebar.selectbox("メニュー", menu)

        if choice == "データ一覧":
            st.subheader("登録されているレオパ")
            df = load_data_from_sheets()
            st.dataframe(df)

        elif choice == "新規登録":
            st.subheader("新しいレオパを登録")
            with st.form("add_form", clear_on_submit=True):
                id_val = st.text_input("ID")
                morph = st.text_input("モルフ")
                birth = st.date_input("生年月日")
                gender = st.selectbox("性別", ["不明", "オス", "メス"])
                quality = st.select_slider("クオリティ", options=["★1", "★2", "★3", "★4", "★5"])
                image_url = st.text_input("画像URL (Googleドライブ等)")
                notes = st.text_area("備考")
                
                submitted = st.form_submit_button("登録")
                if submitted:
                    df = load_data_from_sheets()
                    new_data = pd.DataFrame([{
                        "ID": id_val,
                        "モルフ": morph,
                        "生年月日": birth,
                        "性別": gender,
                        "クオリティ": quality,
                        "画像URL": image_url,
                        "備考": notes
                    }])
                    df = pd.concat([df, new_data], ignore_index=True)
                    save_data_to_sheets(df)
                    st.success(f"ID: {id_val} を保存しました！")

if __name__ == "__main__":
    main()
