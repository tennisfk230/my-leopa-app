import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
import os
from datetime import datetime
import io

# QRコードと画像処理ライブラリ
try:
    import qrcode
    from PIL import Image, ImageDraw
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

# --- 1. 基本設定 ---
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"
SPREADSHEET_NAME = "leopa_database"

st.set_page_config(page_title="&Gekko System", layout="wide", page_icon="🦎")

# --- 2. デザイン (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .header-container { text-align: center; margin-bottom: 20px; border-bottom: 3px solid #81d1d1; }
    .leopa-card { border: 1px solid #eee; border-radius: 12px; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; overflow: hidden; position: relative; }
    .img-container { width: 100%; aspect-ratio: 1 / 1; overflow: hidden; position: relative; }
    .img-container img { width: 100%; height: 100%; object-fit: cover; }
    .badge-sex { position: absolute; top: 10px; right: 10px; padding: 5px 10px; border-radius: 20px; color: white; font-weight: bold; font-size: 0.8rem; z-index: 10; }
    .male { background-color: #5dade2; }
    .female { background-color: #ec7063; }
    .unknown { background-color: #aeb6bf; }
    .badge-quality { position: absolute; top: 10px; left: 10px; background-color: rgba(0,0,0,0.6); color: #f1c40f; padding: 2px 8px; border-radius: 5px; font-size: 0.8rem; font-weight: bold; border: 1px solid #f1c40f; z-index: 10; }
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
    sheet.update(data, 'A1')

# 📸 画像をリサイズ・圧縮する関数 (APIエラー対策)
def convert_image(file):
    if file:
        img = Image.open(file)
        img = img.convert("RGB")
        img.thumbnail((800, 800)) # 最大幅800pxに縮小
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70) # 圧縮して軽量化
        return base64.b64encode(buf.getvalue()).decode()
    return ""

# 🖨️ ラベル画像生成関数
def create_label_image(id_val, morph, birth, quality):
    if not HAS_LIBS: return None
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
        # 4つのタブを実装
        tabs = st.tabs(["📊 ダッシュボード", "🦎 アルバム・検索", "➕ 新規登録", "🖨️ ラベル生成"])

        # --- TAB 1: ダッシュボード ---
        with tabs[0]:
            if not df.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric("総飼育数", f"{len(df)}匹")
                c2.metric("♂ オス", f"{len(df[df['性別']=='オス'])}匹")
                c3.metric("♀ メス", f"{len(df[df['性別']=='メス'])}匹")
                st.bar_chart(df['モルフ'].value_counts())

        # --- TAB 2: アルバム ---
        with tabs[1]:
            if df.empty: st.info("データがありません")
            else:
                search = st.text_input("キーワード検索 (IDやモルフ名)")
                v_df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)] if search else df
                cols = st.columns(2)
                for i, (idx, row) in enumerate(v_df.iterrows()):
                    with cols[i % 2]:
                        s_cls = "male" if row['性別']=="オス" else "female" if row['性別']=="メス" else "unknown"
                        st.markdown(f"""
                            <div class="leopa-card">
                                <div class="img-container">
                                    <span class="badge-quality">{row['クオリティ']}</span>
                                    <span class="badge-sex {s_cls}">{row['性別']}</span>
                                    <img src="data:image/jpeg;base64,{row['画像1']}">
                                </div>
                                <div style="padding:10px;"><b>ID: {row['ID']}</b><br>{row['モルフ']}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        with st.expander("詳細を見る"):
                            st.write(f"生年月日: {row['生年月日']}")
                            st.write(f"親情報: {row.get('父親ID','-')} × {row.get('母親ID','-')}")
                            st.write(f"備考: {row['備考']}")
                            if st.session_state["is_admin"] and st.button("削除", key=f"del_{idx}"):
                                save_all_data(df.drop(idx)); st.rerun()

        # --- TAB 3: 新規登録 ---
        with tabs[2]:
            st.subheader("新しい個体を登録")
            this_year = datetime.now().year
            sel_year = st.selectbox("誕生年", [str(y) for y in range(this_year, this_year-15, -1)])
            prefix = sel_year[2:]
            count = len(df[df['ID'].astype(str).str.startswith(prefix)]) if not df.empty else 0
            
            with st.form("reg_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    id_v = st.text_input("個体ID", value=f"{prefix}{count+1:03d}")
                    bi_str = st.text_input("生年月日", value=f"{sel_year}/")
                with col2:
                    mo = st.text_input("モルフ")
                    ge = st.selectbox("性別", ["不明", "オス", "メス"])
                qu = st.select_slider("クオリティ", options=["S", "A", "B", "C"])
                
                st.write("---")
                f_id = st.text_input("父親ID")
                m_id = st.text_input("母親ID")
                im1 = st.file_uploader("画像1 (必須)", type=["jpg", "jpeg", "png"])
                im2 = st.file_uploader("画像2 (詳細用)", type=["jpg", "jpeg", "png"])
                no = st.text_area("備考")
                
                if st.form_submit_button("保存"):
                    if not im1: st.error("画像をアップロードしてください")
                    else:
                        new = {
                            "ID":id_v, "モルフ":mo, "生年月日":bi_str, "性別":ge, "クオリティ":qu,
                            "父親ID":f_id, "母親ID":m_id, "画像1":convert_image(im1), "画像2":convert_image(im2),
                            "備考":no, "非公開": "False"
                        }
                        save_all_data(pd.concat([df, pd.DataFrame([new])], ignore_index=True))
                        st.success("保存しました！"); st.rerun()

        # --- TAB 4: ラベル生成 ---
        with tabs[3]:
            st.subheader("🖨️ ラベル作成")
            if df.empty: st.warning("データがありません")
            else:
                target = st.selectbox("個体を選択", df['ID'].astype(str) + " : " + df['モルフ'])
                if st.button("ラベル生成"):
                    tid = target.split(" : ")[0]
                    r = df[df['ID'].astype(str) == tid].iloc[0]
                    label = create_label_image(r['ID'], r['モルフ'], r['生年月日'], r['クオリティ'])
                    st.image(label, width=400)
                    st.download_button("画像をダウンロード", label, f"label_{tid}.png", "image/png")

if __name__ == "__main__":
    main()
