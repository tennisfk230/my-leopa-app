import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
import os
from datetime import datetime
import io

# QRコードライブラリ
try:
    import qrcode
    from PIL import Image, ImageDraw, ImageOps
    HAS_QR = True
except ImportError:
    HAS_QR = False

# --- 1. 設定 ---
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"
SPREADSHEET_NAME = "leopa_database"

st.set_page_config(page_title="&Gekko System", layout="wide", page_icon="🦎")

# --- 2. デザイン ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .header-container { text-align: center; margin-bottom: 20px; border-bottom: 3px solid #81d1d1; }
    .leopa-card { border: 1px solid #eee; border-radius: 12px; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; overflow: hidden; position: relative; }
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
    sheet.update(range_name='A1', values=data)

# ✅ ここに二段階の圧縮機能を追加しました
def convert_image(file):
    if file:
        try:
            img = Image.open(file)
            if hasattr(img, '_getexif'): img = ImageOps.exif_transpose(img)
            if img.mode != 'RGB': img = img.convert('RGB')
            
            # 1段目：400px, 画質40
            img.thumbnail((400, 400))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=40, optimize=True)
            b_str = base64.b64encode(buf.getvalue()).decode()
            
            # 2段目：40,000文字を超えた場合、200px, 画質30まで落とす
            if len(b_str) > 40000:
                img.thumbnail((200, 200))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=30)
                b_str = base64.b64encode(buf.getvalue()).decode()
            
            return b_str
        except: return ""
    return ""

def create_label_image(id_val, morph, birth, quality):
    if not HAS_QR: return None
    width, height = 400, 200
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(f"ID:{id_val}\nMorph:{morph}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    img.paste(qr_img, (260, 20))
    draw.rectangle([(10, 10), (390, 190)], outline="#81d1d1", width=5)
    draw.text((30, 30), f"ID: {id_val}", fill="black")
    draw.text((30, 70), f"{morph}", fill="black")
    draw.text((30, 110), f"Birth: {birth}", fill="gray")
    draw.text((30, 150), f"Rank: {quality}", fill="#f1c40f")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

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
        if not df.empty and not st.session_state["is_admin"]:
            if "非公開" in df.columns:
                df = df[df["非公開"] != "True"]

        tabs = st.tabs(["📊 ダッシュボード", "🦎 アルバム・検索", "➕ 新規登録", "🖨️ ラベル生成"])

        with tabs[0]: # ダッシュボード
            if df.empty: st.info("データがありません")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("総数", f"{len(df)}匹")
                c2.metric("♂", f"{len(df[df['性別'] == 'オス'])}匹")
                c3.metric("♀", f"{len(df[df['性別'] == 'メス'])}匹")
                st.bar_chart(df['モルフ'].value_counts())

        with tabs[1]: # アルバム & 編集
            with st.expander("🔍 検索・絞り込み"):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filter_sex = st.multiselect("性別", options=["オス", "メス", "不明"])
                    filter_quality = st.multiselect("クオリティ", options=["S", "A", "B", "C"])
                with col_f2:
                    search_text = st.text_input("キーワード検索 (ID, モルフなど)")
            
            view_df = df.copy()
            if not view_df.empty:
                if filter_sex: view_df = view_df[view_df['性別'].isin(filter_sex)]
                if filter_quality: view_df = view_df[view_df['クオリティ'].isin(filter_quality)]
                if search_text:
                    view_df = view_df[view_df['ID'].astype(str).str.contains(search_text, case=False) | view_df['モルフ'].astype(str).str.contains(search_text, case=False)]

            cols = st.columns(2)
            for i, (idx, row) in enumerate(view_df.iterrows()):
                s_cls = "male" if row['性別'] == "オス" else "female" if row['性別'] == "メス" else "unknown"
                s_icon = "♂" if row['性別'] == "オス" else "♀" if row['性別'] == "メス" else "?"
                with cols[i % 2]:
                    st.markdown(f'<div class="leopa-card"><div class="img-container"><span class="badge-quality">{row.get("クオリティ","-")}</span><span class="badge-sex {s_cls}">{s_icon}</span><img src="data:image/jpeg;base64,{row.get("画像1","")}"></div><div style="padding:10px;"><b>ID: {row.get("ID","-")}</b><br>{row.get("モルフ","-")}</div></div>', unsafe_allow_html=True)
                    
                    with st.expander("詳細 / 編集"):
                        if st.session_state["is_admin"]:
                            mode = st.radio("操作を選択", ["表示", "編集"], key=f"m_{idx}", horizontal=True)
                        else: mode = "表示"
                        
                        if mode == "表示":
                            t1, t2 = st.tabs(["基本情報", "🧬 血統"])
                            with t1:
                                st.write(f"誕生日: {row.get('生年月日','-')}")
                                st.write(f"備考: {row.get('備考','-')}")
                                if row.get("画像2"): st.image(f"data:image/jpeg;base64,{row['画像2']}", use_container_width=True)
                            with t2:
                                st.write(f"父親: {row.get('父親ID','-')} ({row.get('父親モルフ','-')})")
                                st.write(f"母親: {row.get('母親ID','-')} ({row.get('母親モルフ','-')})")
                            if st.session_state["is_admin"]:
                                if st.button("🗑️ 削除", key=f"del_{idx}"):
                                    save_all_data(df.drop(idx)); st.rerun()
                        else:
                            with st.form(f"edit_{idx}"):
                                n_id = st.text_input("個体ID", value=row['ID'])
                                n_mo = st.text_input("モルフ", value=row['モルフ'])
                                n_ge = st.selectbox("性別", ["不明", "オス", "メス"], index=["不明", "オス", "メス"].index(row['性別']))
                                n_qu = st.select_slider("クオリティ", options=["S", "A", "B", "C"], value=row['クオリティ'])
                                n_bi = st.text_input("生年月日", value=row['生年月日'])
                                n_fi = st.text_input("父親ID", value=row.get('父親ID',''))
                                n_fm = st.text_input("父親モルフ", value=row.get('父親モルフ',''))
                                n_mi = st.text_input("母親ID", value=row.get('母親ID',''))
                                n_mm = st.text_input("母親モルフ", value=row.get('母親モルフ',''))
                                n_no = st.text_area("備考", value=row.get('備考',''))
                                n_im1 = st.file_uploader("画像1差替", type=["jpg", "jpeg", "png"], key=f"u1_{idx}")
                                n_im2 = st.file_uploader("画像2追加/差替", type=["jpg", "jpeg", "png"], key=f"u2_{idx}")
                                if st.form_submit_button("更新を保存"):
                                    df.at[idx, 'ID'] = n_id
                                    df.at[idx, 'モルフ'] = n_mo
                                    df.at[idx, '性別'] = n_ge
                                    df.at[idx, 'クオリティ'] = n_qu
                                    df.at[idx, '生年月日'] = n_bi
                                    df.at[idx, '父親ID'] = n_fi
                                    df.at[idx, '父親モルフ'] = n_fm
                                    df.at[idx, '母親ID'] = n_mi
                                    df.at[idx, '母親モルフ'] = n_mm
                                    df.at[idx, '備考'] = n_no
                                    if n_im1: df.at[idx, '画像1'] = convert_image(n_im1)
                                    if n_im2: df.at[idx, '画像2'] = convert_image(n_im2)
                                    save_all_data(df); st.success("保存完了！"); st.rerun()

        with tabs[2]: # ➕ 新規登録
            st.markdown("### 📝 新規個体登録")
            this_year = datetime.now().year
            sel_y = st.selectbox("誕生年を選択", [str(y) for y in range(this_year, this_year - 15, -1)], key="reg_year")
            
            prefix = sel_y[2:]
            count = len(df[df["ID"].astype(str).str.startswith(prefix)]) if not df.empty else 0
            default_id = f"{prefix}{count+1:03d}"
            
            with st.form("reg_form", clear_on_submit=True):
                is_p = st.checkbox("非公開にする")
                col1, col2 = st.columns(2)
                with col1:
                    id_v = st.text_input("個体ID", value=default_id)
                    bi_s = st.text_input("生年月日 (例: 2026/05/10)", value=f"{sel_y}/")
                with col2:
                    mo = st.text_input("モルフ")
                    ge = st.selectbox("性別", ["不明", "オス", "メス"])
                qu = st.select_slider("クオリティ", options=["S", "A", "B", "C"])
                st.markdown("---")
                ck1, ck2 = st.columns(2)
                with ck1:
                    f_id = st.text_input("父親ID"); f_mo = st.text_input("父親モルフ")
                with ck2:
                    m_id = st.text_input("母親ID"); m_mo = st.text_input("母親モルフ")
                im1 = st.file_uploader("画像1 (必須)", type=["jpg", "jpeg", "png"])
                im2 = st.file_uploader("画像2", type=["jpg", "jpeg", "png"])
                no = st.text_area("備考")
                if st.form_submit_button("登録する"):
                    if not im1: st.error("画像1は必須です")
                    else:
                        new_row = {
                            "ID":id_v, "モルフ":mo, "生年月日":bi_s, "性別":ge, "クオリティ":qu,
                            "父親ID":f_id, "父親モルフ":f_mo, "母親ID":m_id, "母親モルフ":m_mo,
                            "画像1":convert_image(im1), "画像2":convert_image(im2), "備考":no, "非公開": str(is_p)
                        }
                        save_all_data(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                        st.success(f"ID {id_v} 保存完了！"); st.rerun()

        with tabs[3]: # 🖨️ ラベル生成
            if not df.empty:
                target = st.selectbox("個体を選択", df['ID'].astype(str) + " : " + df['モルフ'])
                if st.button("生成"):
                    tid = target.split(" : ")[0]
                    row = df[df['ID'].astype(str) == tid].iloc[0]
                    label = create_label_image(row['ID'], row['モルフ'], row['生年月日'], row['クオリティ'])
                    st.image(label, width=400)
                    st.download_button("ダウンロード", label, f"label_{tid}.png", "image/png")

if __name__ == "__main__":
    main()
