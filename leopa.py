import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime
import io
import requests

# QRコード生成ライブラリ
try:
    import qrcode
    from PIL import Image, ImageDraw, ImageOps, ImageFont
    HAS_QR = True
except ImportError:
    HAS_QR = False

# --- 1. 定数・設定 ---
ADMIN_PASSWORD = "lucafk"  # 管理者用
VIEW_PASSWORD = "andgekko"  # 閲覧用
SPREADSHEET_NAME = "leopa_database"

# 保存する列の順番を固定する（ズレ防止）
COLUMNS = [
    "ID", "モルフ", "生年月日", "性別", "クオリティ", 
    "父親ID", "父親モルフ", "母親ID", "母親モルフ", 
    "画像1", "画像2", "備考", "非公開"
]

CLOUDINARY_URL = f"https://api.cloudinary.com/v1_1/{st.secrets.get('CLOUDINARY_CLOUD_NAME', '')}/image/upload"
UPLOAD_PRESET = st.secrets.get('CLOUDINARY_UPLOAD_PRESET', '')

st.set_page_config(page_title="&Gekko System", layout="wide", page_icon="🦎")

# --- 2. スタイル定義 ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .header-container { text-align: center; margin-bottom: 20px; border-bottom: 3px solid #81d1d1; padding-bottom: 10px; }
    .leopa-card { border: 1px solid #ddd; border-radius: 12px; background-color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.08); margin-bottom: 20px; overflow: hidden; position: relative; }
    .img-container { width: 100%; aspect-ratio: 1 / 1; overflow: hidden; position: relative; background-color: #f0f0f0; }
    .img-container img { width: 100%; height: 100%; object-fit: cover; }
    .badge-sex { position: absolute; top: 10px; right: 10px; padding: 5px 12px; border-radius: 20px; color: white; font-weight: bold; font-size: 0.85rem; z-index: 10; }
    .male { background-color: #5dade2; }
    .female { background-color: #ec7063; }
    .unknown { background-color: #aeb6bf; }
    .badge-quality { position: absolute; top: 10px; left: 10px; background-color: rgba(0,0,0,0.7); color: #f1c40f; padding: 3px 10px; border-radius: 5px; font-size: 0.8rem; font-weight: bold; border: 1px solid #f1c40f; z-index: 10; }
    .card-info { padding: 15px; }
    .card-id { font-size: 0.9rem; color: #7f8c8d; }
    .card-morph { font-size: 1.1rem; font-weight: bold; color: #2c3e50; }
    [data-testid="stSidebar"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 3. データベース関数 ---
def get_gspread_client():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
        creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google API接続エラー: {e}")
        return None

def load_data():
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    try:
        sheet = client.open(SPREADSHEET_NAME).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        # 必要な列が不足している場合の補完
        for col in COLUMNS:
            if col not in df.columns: df[col] = ""
        return df[COLUMNS] # 列順を固定
    except Exception as e:
        return pd.DataFrame(columns=COLUMNS)

def save_all_data(df):
    client = get_gspread_client()
    if not client: return
    try:
        sheet = client.open(SPREADSHEET_NAME).sheet1
        sheet.clear()
        # 列順を保証して保存
        df_save = df[COLUMNS].astype(str)
        data = [df_save.columns.values.tolist()] + df_save.values.tolist()
        sheet.update(range_name='A1', values=data)
        st.success("データベースを更新しました。")
    except Exception as e:
        st.error(f"データ保存エラー: {e}")

# --- 4. 画像処理関数 ---
def upload_to_cloudinary(file):
    if not file: return ""
    try:
        img = Image.open(file)
        img = ImageOps.exif_transpose(img)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        buf.seek(0)
        files = {"file": buf}
        data = {"upload_preset": UPLOAD_PRESET}
        res = requests.post(CLOUDINARY_URL, files=files, data=data)
        return res.json().get("secure_url") if res.status_code == 200 else ""
    except Exception as e:
        st.error(f"画像処理エラー: {e}")
        return ""

def create_label_image(id_val, morph, birth, quality):
    if not HAS_QR: return None
    width, height = 400, 220
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(f"ID:{id_val}\nMorph:{morph}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    img.paste(qr_img, (250, 25))
    draw.rectangle([(10, 10), (390, 210)], outline="#81d1d1", width=3)
    draw.text((30, 30), f"ID: {id_val}", fill="black")
    draw.text((30, 70), f"{morph}", fill="#2c3e50")
    draw.text((30, 110), f"Birth: {birth}", fill="#7f8c8d")
    draw.text((30, 150), f"Rank: {quality}", fill="#f1c40f")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- 5. メインUI ---
def main():
    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "is_admin": False})

    if not st.session_state["logged_in"]:
        st.write("### 🔐 MEMBER LOGIN")
        pwd = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": True}); st.rerun()
            elif pwd == VIEW_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": False}); st.rerun()
            else: st.error("パスワードが正しくありません")
        return

    df = load_data()
    if not df.empty and not st.session_state["is_admin"]:
        df = df[df["非公開"].astype(str).str.lower() != "true"]

    tabs = st.tabs(["📊 ダッシュボード", "🦎 検索・アルバム", "➕ 新規登録", "🖨️ ラベル生成"])

    # --- Tab 1: アルバム & 編集 ---
    with tabs[1]:
        s_query = st.text_input("🔍 検索 (ID/モルフ)")
        view_df = df.copy()
        if s_query:
            view_df = view_df[view_df['ID'].astype(str).str.contains(s_query, case=False) | view_df['モルフ'].astype(str).str.contains(s_query, case=False)]

        if view_df.empty:
            st.write("該当なし")
        else:
            cols = st.columns(2)
            for i, (idx, row) in enumerate(view_df.iterrows()):
                gender_class = "male" if row['性別'] == "オス" else "female" if row['性別'] == "メス" else "unknown"
                img_url = row.get("画像1", "")
                if img_url and not img_url.startswith("http"): img_url = f"data:image/jpeg;base64,{img_url}"

                with cols[i % 2]:
                    st.markdown(f"""
                        <div class="leopa-card">
                            <div class="img-container">
                                <span class="badge-quality">{row.get('クオリティ','-')}</span>
                                <span class="badge-sex {gender_class}">{row['性別']}</span>
                                <img src="{img_url}">
                            </div>
                            <div class="card-info">
                                <div class="card-id">ID: {row.get('ID','-')}</div>
                                <div class="card-morph">{row.get('モルフ','-')}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("詳細・管理"):
                        if st.session_state["is_admin"]:
                            edit_mode = st.toggle("編集モード", key=f"edit_mode_{idx}")
                        else: edit_mode = False
                        
                        if not edit_mode:
                            # 表示モード（レイアウト修正版）
                            st.write(f"**生年月日:** {row.get('生年月日','-')}")
                            st.write(f"**父親モルフ:** {row.get('父親モルフ','-')}")
                            st.write(f"**父親ID:** {row.get('父親ID','-')}")
                            st.write(f"**母親モルフ:** {row.get('母親モルフ','-')}")
                            st.write(f"**母親ID:** {row.get('母親ID','-')}")
                            st.write(f"**備考:** {row.get('備考','-')}")
                            
                            img2 = row.get("画像2")
                            if img2:
                                if not img2.startswith("http"): img2 = f"data:image/jpeg;base64,{img2}"
                                st.image(img2, caption="サブ画像", use_container_width=True)
                        else:
                            # 編集モード（全項目修正可能版）
                            with st.form(f"form_edit_{idx}"):
                                c1, c2 = st.columns(2)
                                with c1:
                                    e_id = st.text_input("個体ID", value=row['ID'])
                                    e_morph = st.text_input("モルフ", value=row['モルフ'])
                                    e_sex = st.selectbox("性別", ["不明", "オス", "メス"], index=["不明", "オス", "メス"].index(row['性別']))
                                with c2:
                                    e_birth = st.text_input("生年月日", value=row['生年月日'])
                                    e_qual = st.select_slider("クオリティ", options=["S", "A", "B", "C"], value=row['クオリティ'])
                                    e_pvt = st.checkbox("非公開", value=(str(row['非公開']).lower() == "true"))
                                
                                st.write("--- 家系情報の修正 ---")
                                col_f, col_m = st.columns(2)
                                with col_f:
                                    e_fid = st.text_input("父親ID", value=row.get('父親ID',''))
                                    e_fmo = st.text_input("父親モルフ", value=row.get('父親モルフ',''))
                                with col_m:
                                    e_mid = st.text_input("母親ID", value=row.get('母親ID',''))
                                    e_mmo = st.text_input("母親モルフ", value=row.get('母親モルフ',''))
                                
                                e_note = st.text_area("備考", value=row.get('備考',''))
                                e_img1 = st.file_uploader("メイン画像変更", type=["jpg","png"], key=f"fu1_{idx}")
                                e_img2 = st.file_uploader("サブ画像変更", type=["jpg","png"], key=f"fu2_{idx}")
                                
                                if st.form_submit_button("変更を保存"):
                                    df.at[idx, 'ID'] = e_id
                                    df.at[idx, 'モルフ'] = e_morph
                                    df.at[idx, '性別'] = e_sex
                                    df.at[idx, '生年月日'] = e_birth
                                    df.at[idx, 'クオリティ'] = e_qual
                                    df.at[idx, '父親ID'] = e_fid
                                    df.at[idx, '父親モルフ'] = e_fmo
                                    df.at[idx, '母親ID'] = e_mid
                                    df.at[idx, '母親モルフ'] = e_mmo
                                    df.at[idx, '備考'] = e_note
                                    df.at[idx, '非公開'] = str(e_pvt)
                                    if e_img1:
                                        url1 = upload_to_cloudinary(e_img1)
                                        if url1: df.at[idx, '画像1'] = url1
                                    if e_img2:
                                        url2 = upload_to_cloudinary(e_img2)
                                        if url2: df.at[idx, '画像2'] = url2
                                    save_all_data(df)
                                    st.rerun()

                            if st.button("🗑️ 削除", key=f"del_{idx}"):
                                save_all_data(df.drop(idx)); st.rerun()

    # --- Tab 2: 新規登録 ---
    with tabs[2]:
        if st.session_state["is_admin"]:
            st.subheader("📝 新規個体登録")
            this_year = datetime.now().year
            reg_year = st.selectbox("誕生年", [str(y) for y in range(this_year, this_year - 10, -1)])
            prefix = reg_year[2:]
            count = len(df[df["ID"].astype(str).str.startswith(prefix)]) if not df.empty else 0
            suggested_id = f"{prefix}{count+1:03d}"

            with st.form("new_registration", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    c_id = st.text_input("個体ID", value=suggested_id)
                    c_morph = st.text_input("モルフ名")
                    c_sex = st.selectbox("性別", ["不明", "オス", "メス"])
                with col2:
                    c_birth = st.text_input("生年月日 (YYYY/MM/DD)", value=f"{reg_year}/")
                    c_qual = st.select_slider("クオリティ", options=["S", "A", "B", "C"], value="A")
                    is_pvt = st.checkbox("非公開設定")
                
                st.write("--- 家系情報 ---")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    f_id = st.text_input("父親ID"); f_mo = st.text_input("父親モルフ")
                with col_p2:
                    m_id = st.text_input("母親ID"); m_mo = st.text_input("母親モルフ")
                
                new_img1 = st.file_uploader("メイン画像 (必須)", type=["jpg", "png"])
                new_img2 = st.file_uploader("サブ画像", type=["jpg", "png"])
                new_note = st.text_area("備考")
                
                if st.form_submit_button("登録"):
                    if not new_img1: st.error("画像1は必須です")
                    else:
                        url1 = upload_to_cloudinary(new_img1)
                        url2 = upload_to_cloudinary(new_img2) if new_img2 else ""
                        new_row = {
                            "ID": c_id, "モルフ": c_morph, "生年月日": c_birth, "性別": c_sex, 
                            "クオリティ": c_qual, "父親ID": f_id, "父親モルフ": f_mo,
                            "母親ID": m_id, "母親モルフ": m_mo, "画像1": url1, "画像2": url2, 
                            "備考": new_note, "非公開": str(is_pvt)
                        }
                        save_all_data(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                        st.rerun()

    # --- Tab 0: ダッシュボード ---
    with tabs[0]:
        if not df.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("総飼育数", f"{len(df)} 匹")
            c2.metric("♂", f"{len(df[df['性別'] == 'オス'])} 匹")
            c3.metric("♀", f"{len(df[df['性別'] == 'メス'])} 匹")
            c4.metric("不明", f"{len(df[df['性別'] == '不明'])} 匹")
            st.bar_chart(df['モルフ'].value_counts())

    # --- Tab 3: ラベル生成 ---
    with tabs[3]:
        if not df.empty:
            target = st.selectbox("対象選択", df['ID'].astype(str) + " : " + df['モルフ'])
            if st.button("生成"):
                tid = target.split(" : ")[0]
                row = df[df['ID'].astype(str) == tid].iloc[0]
                label = create_label_image(row['ID'], row['モルフ'], row.get('生年月日','-'), row.get('クオリティ','-'))
                st.image(label, width=400)
                st.download_button("保存", label, f"label_{tid}.png", "image/png")

if __name__ == "__main__":
    main()
