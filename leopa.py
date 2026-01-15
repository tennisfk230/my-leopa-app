import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import base64

# --- 設定（パスワードをご自身のものに書き換えてください） ---
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"
SPREADSHEET_NAME = "leopa_database"

# --- デザイン設定（&Gekkoカラー強化版） ---
st.set_page_config(page_title="&Gekko レオパログ", layout="centered")

st.markdown("""
    <style>
    /* 全体の背景 */
    .stApp { background-color: #ffffff; }
    
    /* サイドバー（メニュー）をミントグリーンで塗りつぶし */
    [data-testid="stSidebar"] {
        background-color: #81d1d1 !important;
    }
    
    /* サイドバー内の文字色を黒で読みやすく */
    [data-testid="stSidebar"] .stText, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stSelectbox div {
        color: #000000 !important;
        font-weight: bold;
    }

    /* タイトルエリアをミントグリーンの背景に（割合を増やす工夫） */
    .main-header {
        background-color: #81d1d1;
        padding: 20px;
        border-radius: 0px 0px 20px 20px;
        margin-bottom: 30px;
        text-align: center;
        color: white;
    }

    /* ボタンのデザインを強化 */
    .stButton>button {
        background-color: #81d1d1;
        color: white;
        border-radius: 25px;
        border: 2px solid #81d1d1;
        font-weight: bold;
        padding: 0.5rem 1rem;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: white;
        color: #81d1d1;
        border: 2px solid #81d1d1;
    }

    /* 入力欄の枠線 */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-color: #81d1d1;
    }

    /* 編集ボックスの背景を薄いミントに */
    .edit-box {
        padding: 20px;
        border: 2px solid #81d1d1;
        border-radius: 15px;
        background-color: #f0fafa;
        margin-bottom: 25px;
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
    # ヘッダーデザイン（ミントグリーンの割合を増やす）
    st.markdown('<div class="main-header"><h1>🦎 &Gekko レオパログ</h1></div>', unsafe_allow_html=True)

    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "is_admin": False})

    if not st.session_state["logged_in"]:
        pwd = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": True})
                st.rerun()
            elif pwd == VIEW_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": False})
                st.rerun()
            else: st.error("パスワードが違います")
    else:
        # メニュー設定
        menu_options = ["データ一覧"]
        if st.session_state["is_admin"]:
            menu_options.append("新規登録")
        
        # サイドバーのデザイン変更
        st.sidebar.markdown("### &Gekko メニュー")
        choice = st.sidebar.radio("項目を選択してください", menu_options)

        if choice == "データ一覧":
            df = load_data()
            if df.empty:
                st.info("登録されているデータがありません。")
            else:
                if not st.session_state["is_admin"]:
                    df = df[df["非公開"] != "True"]
                
                for idx, row in df.iterrows():
                    with st.container():
                        st.markdown("---")
                        if st.session_state["is_admin"] and str(row.get("非公開")) == "True":
                            st.warning("🔒 非公開データ")

                        if row.get("画像1"): st.image(f"data:image/jpeg;base64,{row['画像1']}", use_container_width=True)
                        st.markdown(f"## ID: {row['ID']} / {row['モルフ']}")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**生年月日:** {row['生年月日']}\n\n**性別:** {row['性別']}\n\n**クオリティ:** {row['クオリティ']}")
                        with c2:
                            st.write(f"**父:** {row['父親のモルフ']}({row['父親のID']})\n\n**母:** {row['母親のモルフ']}({row['母親のID']})")
                        
                        if row["備考"]: st.info(f"備考: {row['備考']}")
                        if row.get("画像2"):
                            with st.expander("2枚目の写真を見る"): st.image(f"data:image/jpeg;base64,{row['画像2']}", use_container_width=True)
                        
                        if st.session_state["is_admin"]:
                            ec1, ec2 = st.columns(2)
                            if ec1.button("編集", key=f"edit_btn_{idx}"):
                                st.session_state["edit_idx"] = idx
                            if ec2.button("削除", key=f"del_btn_{idx}"):
                                df = df.drop(idx)
                                save_all_data(df)
                                st.success("削除完了")
                                st.rerun()
                            
                            if st.session_state.get("edit_idx") == idx:
                                st.markdown('<div class="edit-box">', unsafe_allow_html=True)
                                with st.form(f"form_{idx}"):
                                    st.write("### 修正フォーム")
                                    u_private = st.checkbox("非公開にする", value=(str(row.get("非公開")) == "True"))
                                    u_id = st.text_input("ID", value=row["ID"])
                                    u_mo = st.text_input("モルフ", value=row["モルフ"])
                                    u_bi = st.text_input("生年月日", value=row["生年月日"])
                                    u_ge = st.selectbox("性別", ["不明", "オス", "メス"], index=["不明", "オス", "メス"].index(row["性別"]))
                                    u_qu = st.select_slider("クオリティ", options=["★1", "★2", "★3", "★4", "★5"], value=row["クオリティ"])
                                    u_fm = st.text_input("父モルフ", value=row["父親のモルフ"])
                                    u_fi = st.text_input("父ID", value=row["父親のID"])
                                    u_mm = st.text_input("母モルフ", value=row["母親のモルフ"])
                                    u_mi = st.text_input("母ID", value=row["母親のID"])
                                    u_no = st.text_area("備考", value=row["備考"])
                                    u_im1 = st.file_uploader("画像1差し替え", type=["jpg", "jpeg", "png"])
                                    u_im2 = st.file_uploader("画像2差し替え", type=["jpg", "jpeg", "png"])
                                    
                                    if st.form_submit_button("この内容で更新"):
                                        df.at[idx, "ID"] = u_id
                                        df.at[idx, "モルフ"] = u_mo
                                        df.at[idx, "生年月日"] = u_bi
                                        df.at[idx, "性別"] = u_ge
                                        df.at[idx, "クオリティ"] = u_qu
                                        df.at[idx, "父親のモルフ"] = u_fm
                                        df.at[idx, "父親のID"] = u_fi
                                        df.at[idx, "母親のモルフ"] = u_mm
                                        df.at[idx, "母親のID"] = u_mi
                                        df.at[idx, "備考"] = u_no
                                        df.at[idx, "非公開"] = str(u_private)
                                        if u_im1: df.at[idx, "画像1"] = convert_image(u_im1)
                                        if u_im2: df.at[idx, "画像2"] = convert_image(u_im2)
                                        save_all_data(df)
                                        st.session_state["edit_idx"] = None
                                        st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)

        elif choice == "新規登録":
            st.subheader("新しいレオパを登録")
            with st.form("reg_form", clear_on_submit=True):
                is_private = st.checkbox("非公開にする")
                id_v = st.text_input("ID")
                mo = st.text_input("モルフ")
                bi = st.date_input("生年月日")
                ge = st.selectbox("性別", ["不明", "オス", "メス"])
                qu = st.select_slider("クオリティ", options=["★1", "★2", "★3", "★4", "★5"])
                f_m = st.text_input("父モルフ"); f_i = st.text_input("父ID")
                m_m = st.text_input("母モルフ"); m_i = st.text_input("母ID")
                im1 = st.file_uploader("画像1を選択"); im2 = st.file_uploader("画像2を選択")
                no = st.text_area("備考")
                
                if st.form_submit_button("新しく保存する"):
                    df = load_data()
                    new_row = {
                        "ID":id_v, "モルフ":mo, "生年月日":bi, "性別":ge, "クオリティ":qu, 
                        "父親のモルフ":f_m, "父親のID":f_i, "母親のモルフ":m_m, "母親のID":m_i, 
                        "画像1":convert_image(im1), "画像2":convert_image(im2), "備考":no,
                        "非公開": str(is_private)
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_all_data(df)
                    st.success("保存完了！")

if __name__ == "__main__":
    main()
