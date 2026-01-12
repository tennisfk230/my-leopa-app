import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
from io import BytesIO

# --- パスワード設定（ご自身で決めたものに書き換えてください） ---
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"

# --- スプレッドシート設定 ---
SPREADSHEET_NAME = "leopa_database"

# --- 関数：画像を文字列に変換（スプレッドシート保存用） ---
def convert_image_to_base64(image_file):
    if image_file is not None:
        return base64.b64encode(image_file.read()).decode()
    return ""

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
        menu = ["データ一覧"]
        if st.session_state["is_admin"]:
            menu.append("新規登録")
        choice = st.sidebar.selectbox("メニュー", menu)

        if choice == "データ一覧":
            st.subheader("登録されているレオパ")
            df = load_data_from_sheets()
            # 画像データが入っている場合、縮小して表示する設定
            st.dataframe(df)

        elif choice == "新規登録":
            st.subheader("新しいレオパを登録")
            with st.form("add_form", clear_on_submit=True):
                id_val = st.text_input("ID")
                morph = st.text_input("モルフ")
                birth = st.date_input("生年月日")
                gender = st.selectbox("性別", ["不明", "オス", "メス"])
                quality = st.select_slider("クオリティ", options=["★1", "★2", "★3", "★4", "★5"])
                
                # 画像選択ボタン（カメラ起動・フォルダ選択が可能になります）
                img_file1 = st.file_uploader("画像1枚目を選択", type=["jpg", "jpeg", "png"])
                img_file2 = st.file_uploader("画像2枚目を選択", type=["jpg", "jpeg", "png"])
                
                notes = st.text_area("備考")
                submitted = st.form_submit_button("登録")
                
                if submitted:
                    # 画像をデータに変換
                    img_str1 = convert_image_to_base64(img_file1)
                    img_str2 = convert_image_to_base64(img_file2)
                    
                    df = load_data_from_sheets()
                    new_data = pd.DataFrame([{
                        "ID": id_val, "モルフ": morph, "生年月日": birth,
                        "性別": gender, "クオリティ": quality,
                        "画像1": img_str1, "画像2": img_str2, "備考": notes
                    }])
                    df = pd.concat([df, new_data], ignore_index=True)
                    save_data_to_sheets(df)
                    st.success(f"ID: {id_val} を保存しました！")

if __name__ == "__main__":
    main()
