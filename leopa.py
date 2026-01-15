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

# --- デザイン設定（&Gekkoカラー） ---
st.set_page_config(page_title="&Gekko Leopa Log", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #81d1d1; }
    h1, h2, h3 { color: #000000 !important; font-family: 'Serif'; }
    .stButton>button {
        background-color: #81d1d1;
        color: white;
        border-radius: 20px;
        border: none;
        width: 100%;
    }
    .stTextInput>div>div>input { border-color: #81d1d1; }
    .edit-box {
        padding: 20px;
        border: 2px solid #81d1d1;
        border-radius: 10px;
        background-color: #f9fefed;
        margin-bottom: 20px;
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
    st.title("🦎 &Gekko Leopa Log")

    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "is_admin": False})

    if not st.session_state["logged_in"]:
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": True})
                st.rerun()
            elif pwd == VIEW_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": False})
                st.rerun()
            else: st.error("Incorrect password")
    else:
        menu = ["Data List"]
        if st.session_state["is_admin"]: menu.append("Register")
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Data List":
            df = load_data()
            if df.empty:
                st.info("データがありません。")
            else:
                # --- ここがポイント：管理者以外には「非公開」を隠す ---
                if not st.session_state["is_admin"]:
                    # 「非公開」列が TRUE または "True" のものを除外
                    df = df[df["非公開"] != "True"]
                
                for idx, row in df.iterrows():
                    with st.container():
                        st.markdown("---")
                        # 管理者には非公開バッジを表示
                        if st.session_state["is_admin"] and str(row.get("非公開")) == "True":
                            st.warning("🔒 このデータは自分専用（非公開）です")

                        if row.get("画像1"): st.image(f"data:image/jpeg;base64,{row['画像1']}", use_container_width=True)
                        st.markdown(f"### ID: {row['ID']} / {row['モルフ']}")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**生年月日:** {row['生年月日']}\n\n**性別:** {row['性別']}\n\n**クオリティ:** {row['クオリティ']}")
                        with c2:
                            st.write(f"**父:** {row['父親のモルフ']}({row['父親のID']})\n\n**母:** {row['母親のモルフ']}({row['母親のID']})")
                        
                        if row["備考"]: st.info(f"Memo: {row['備考']}")
                        if row.get("画像2"):
                            with st.expander("Show Photo 2"): st.image(f"data:image/jpeg;base64,{row['画像2']}", use_container_width=True)
                        
                        if st.session_state["is_admin"]:
                            ec1, ec2 = st.columns(2)
                            if ec1.button("Edit (編集)", key=f"edit_btn_{idx}"):
                                st.session_state["edit_idx"] = idx
                            if ec2.button("Delete (削除)", key=f"del_btn_{idx}"):
                                df = df.drop(idx)
                                save_all_data(df)
                                st.success("Deleted.")
                                st.rerun()
                            
                            if st.session_state.get("edit_idx") == idx:
                                st.markdown('<div class="edit-box">', unsafe_allow_html=True)
                                with st.form(f"form_{idx}"):
                                    st.write("### データの編集")
                                    # --- 非公開設定（編集） ---
                                    u_private = st.checkbox("このレオパを自分以外には見せない（非公開）", value=(str(row.get("非公開")) == "True"))
                                    u_id = st.text_input("ID", value=row["ID"])
                                    u_mo = st.text_input("モルフ", value=row["モルフ"])
                                    u_bi = st.text_input("生年月日 (YYYY-MM-DD)", value=row["生年月日"])
                                    u_ge = st.selectbox("性別", ["不明", "オス", "メス"], index=["不明", "オス", "メス"].index(row["性別"]))
                                    u_qu = st.select_slider("クオリティ", options=["★1", "★2", "★3", "★4", "★5"], value=row["クオリティ"])
                                    u_fm = st.text_input("父モルフ", value=row["父親のモルフ"])
                                    u_fi = st.text_input("父ID", value=row["父親のID"])
                                    u_mm = st.text_input("母モルフ", value=row["母親のモルフ"])
                                    u_mi = st.text_input("母ID", value=row["母親のID"])
                                    u_no = st.text_area("備考", value=row["備考"])
                                    u_im1 = st.file_uploader("画像1を差し替える", type=["jpg", "jpeg", "png"])
                                    u_im2 = st.file_uploader("画像2を差し替える", type=["jpg", "jpeg", "png"])
                                    
                                    if st.form_submit_button("Update (更新)"):
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
                                        st.success("Updated!")
                                        st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)

        elif choice == "Register":
            st.subheader("New Registration")
            with st.form("reg_form", clear_on_submit=True):
                # --- 非公開設定（新規） ---
                is_private = st.checkbox("このレオパを自分以外には見せない（非公開）")
                id_v = st.text_input("ID")
                mo = st.text_input("モルフ")
                bi = st.date_input("生年月日")
                ge = st.selectbox("性別", ["不明", "オス", "メス"])
                qu = st.select_slider("クオリティ", options=["★1", "★2", "★3", "★4", "★5"])
                f_m = st.text_input("父モルフ"); f_i = st.text_input("父ID")
                m_m = st.text_input("母モルフ"); m_i = st.text_input("母ID")
                im1 = st.file_uploader("Photo 1"); im2 = st.file_uploader("Photo 2")
                no = st.text_area("備考")
                
                if st.form_submit_button("Save"):
                    df = load_data()
                    new_row = {
                        "ID":id_v, "モルフ":mo, "生年月日":bi, "性別":ge, "クオリティ":qu, 
                        "父親のモルフ":f_m, "父親のID":f_i, "母親のモルフ":m_m, "母親のID":m_i, 
                        "画像1":convert_image(im1), "画像2":convert_image(im2), "備考":no,
                        "非公開": str(is_private) # 保存
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_all_data(df)
                    st.success("Saved!")

if __name__ == "__main__":
    main()
