import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import io
import requests

# QRコード生成ライブラリ
try:
    import qrcode
    from PIL import Image, ImageDraw, ImageOps
    HAS_QR = True
except ImportError:
    HAS_QR = False

# --- 1. 定数・設定 ---
SPREADSHEET_NAME = "leopa_database"
LOGO_URL = "logo_gekko.png" # GitHubにあるロゴのファイル名
PLACEHOLDER_IMAGE = "https://via.placeholder.com/400x400?text=No+Image"

# 列の並び順を固定（データのズレを防止）
COLUMNS = [
    "ID", "モルフ", "生年月日", "性別", "クオリティ",
    "父親ID", "父親モルフ", "母親ID", "母親モルフ",
    "画像1", "画像2", "備考", "非公開"
]

# Secretsから設定を読み込み
CLOUDINARY_URL = f"https://api.cloudinary.com/v1_1/{st.secrets.get('CLOUDINARY_CLOUD_NAME', '')}/image/upload"
UPLOAD_PRESET = st.secrets.get('CLOUDINARY_UPLOAD_PRESET', '')

st.set_page_config(page_title="&Gekko System", layout="wide", page_icon="🦎")

# --- 2. デザイン定義 ---
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
    [data-testid="stSidebar"] { display: none; }
    .care-log-entry { padding: 8px 10px; border-bottom: 1px solid #eee; font-size: 0.85rem; background-color: #fff; }
    .log-item-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 8px; font-size: 0.7rem; color: white; }
    .tag-feed { background-color: #27ae60; }
    .tag-clean { background-color: #3498db; }
    .tag-mate { background-color: #9b59b6; }
    .tag-ovul { background-color: #e67e22; }
    .tag-memo { background-color: #7f8c8d; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 共通関数 ---

def get_gspread_client():
    try:
        service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
        creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google APIエラー: {e}")
        return None

def load_data(sheet_name=None):
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open(SPREADSHEET_NAME)
        sheet = sh.worksheet(sheet_name) if sheet_name else sh.sheet1
        df = pd.DataFrame(sheet.get_all_records())
        if not sheet_name:
            for col in COLUMNS:
                if col not in df.columns: df[col] = ""
            return df[COLUMNS]
        return df
    except:
        return pd.DataFrame()

def save_all_data(df, sheet_name=None):
    client = get_gspread_client()
    if not client: return False
    try:
        sh = client.open(SPREADSHEET_NAME)
        try:
            sheet = sh.worksheet(sheet_name) if sheet_name else sh.sheet1
        except:
            sheet = sh.add_worksheet(title=sheet_name, rows=1000, cols=20)
        sheet.clear()
        df_save = df.fillna("").astype(str)
        data = [df_save.columns.values.tolist()] + df_save.values.tolist()
        sheet.update(range_name='A1', values=data)
        return True
    except Exception as e:
        st.error(f"保存エラー: {e}")
        return False

def upload_to_cloudinary(file):
    if not file: return ""
    try:
        img = Image.open(file)
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((800, 800), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        buf.seek(0)
        files = {"file": buf.getvalue()}
        data = {"upload_preset": UPLOAD_PRESET}
        res = requests.post(CLOUDINARY_URL, files=files, data=data, timeout=30)
        return res.json().get("secure_url", "")
    except:
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
    draw.text((30, 150), f"Rank: {quality}", fill="#e67e22")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- 4. メイン処理 ---
def main():
    # ロゴを表示（ログイン画面でも表示されるように配置）
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    try:
        st.image(LOGO_URL, width=300)
    except:
        st.markdown('<h1 style="color:#81d1d1;">&Gekko System</h1>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "is_admin": False})

    # --- ログインチェック ---
    if not st.session_state["logged_in"]:
        st.write("### 🔐 MEMBER LOGIN")
        pwd = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if pwd == st.secrets.get("ADMIN_PASSWORD"):
                st.session_state.update({"logged_in": True, "is_admin": True}); st.rerun()
            elif pwd == st.secrets.get("VIEW_PASSWORD"):
                st.session_state.update({"logged_in": True, "is_admin": False}); st.rerun()
            else: st.error("パスワードが正しくありません")
        return

    # データロード
    df = load_data()
    df_logs = load_data("care_logs")
    is_admin = st.session_state["is_admin"]

    if not df.empty and not is_admin:
        df = df[df["非公開"].astype(str).str.lower() != "true"]

    tabs = st.tabs(["📊 ダッシュボード", "🦎 検索・アルバム", "📝 お世話記録", "➕ 新規登録", "🖨️ ラベル生成"])

    # --- Tab 1: アルバム & 詳細 ---
    with tabs[1]:
        s_query = st.text_input("🔍 検索 (ID / モルフ)")
        view_df = df.copy()
        if s_query:
            view_df = view_df[view_df['ID'].astype(str).str.contains(s_query, case=False) | view_df['モルフ'].astype(str).str.contains(s_query, case=False)]

        if view_df.empty:
            st.info("該当なし")
        else:
            cols = st.columns(2)
            for i, (idx, row) in enumerate(view_df.iterrows()):
                g_cls = "male" if row['性別'] == "オス" else "female" if row['性別'] == "メス" else "unknown"
                img_url = row.get("画像1", PLACEHOLDER_IMAGE)
                if img_url and not str(img1_url).startswith("http"): img1_url = f"data:image/jpeg;base64,{img1_url}"
                
                with cols[i % 2]:
                    st.markdown(f'<div class="leopa-card"><div class="img-container"><span class="badge-quality">{row.get("クオリティ","-")}</span><span class="badge-sex {g_cls}">{row["性別"]}</span><img src="{img_url}"></div><div style="padding:10px;"><b>ID: {row["ID"]}</b><br>{row["モルフ"]}</div></div>', unsafe_allow_html=True)
                    
                    with st.expander("詳細と履歴"):
                        # 指定の順番：生年月日 -> 家系(父・母) -> 備考
                        st.write(f"**生年月日:** {row.get('生年月日','-')}")
                        st.write(f"**父親モルフ:** {row.get('父親モルフ','-')}")
                        st.write(f"**父親ID:** {row.get('父親ID','-')}")
                        st.write(f"**母親モルフ:** {row.get('母親モルフ','-')}")
                        st.write(f"**母親ID:** {row.get('母親ID','-')}")
                        st.write(f"**備考:** {row.get('備考','-')}")
                        
                        if row.get("画像2"):
                            i2 = row["画像2"]
                            if not str(i2).startswith("http"): i2 = f"data:image/jpeg;base64,{i2}"
                            st.image(i2, use_container_width=True)

                        st.markdown("---")
                        if not df_logs.empty:
                            my_logs = df_logs[df_logs['ID'].astype(str) == str(row['ID'])].sort_values('日付', ascending=False)
                            st.write("**🍖 過去5回の給餌記録**")
                            feeds = my_logs[my_logs['項目'] == '給餌'].head(5)
                            if feeds.empty: st.caption("記録なし")
                            else:
                                for _, l in feeds.iterrows():
                                    st.markdown(f'<div class="care-log-entry">📅 {l["日付"]} | {l["内容"]}</div>', unsafe_allow_html=True)
                            
                            st.write("**📋 その他履歴**")
                            for _, l in my_logs.head(3).iterrows():
                                tag_map = {"給餌": "tag-feed", "掃除": "tag-clean", "交配": "tag-mate", "排卵(クラッチ)": "tag-ovul", "メモ": "tag-memo"}
                                tag_class = tag_map.get(l['項目'], "tag-memo")
                                st.markdown(f'<div class="care-log-entry">📅 {l["日付"]} <span class="log-item-tag {tag_class}">{l["項目"]}</span> {l["内容"]}</div>', unsafe_allow_html=True)

                        if is_admin:
                            if st.toggle("✏️ 編集モード", key=f"ed_{idx}"):
                                with st.form(f"f_{idx}"):
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        e_id = st.text_input("ID", value=row['ID'])
                                        e_mo = st.text_input("モルフ", value=row['モルフ'])
                                        e_se = st.selectbox("性別", ["不明", "オス", "メス"], index=["不明", "オス", "メス"].index(row['性別']))
                                    with c2:
                                        e_bi = st.text_input("生年月日", value=row['生年月日'])
                                        e_qu = st.select_slider("ランク", options=["S", "A", "B", "C"], value=row['クオリティ'])
                                        e_pv = st.checkbox("非公開", value=(str(row['非公開']).lower() == "true"))
                                    st.write("家系情報")
                                    ef, em = st.columns(2)
                                    with ef:
                                        e_fid = st.text_input("父ID", value=row['父親ID'])
                                        e_fmo = st.text_input("父モルフ", value=row['父親モルフ'])
                                    with em:
                                        e_mid = st.text_input("母ID", value=row['母親ID'])
                                        e_mmo = st.text_input("母モルフ", value=row['母親モルフ'])
                                    e_no = st.text_area("備考", value=row['備考'])
                                    if st.form_submit_button("保存"):
                                        df.loc[idx, COLUMNS] = [e_id, e_mo, e_bi, e_se, e_qu, e_fid, e_fmo, e_mid, e_mmo, row['画像1'], row['画像2'], e_no, str(e_pv)]
                                        save_all_data(df); st.rerun()

    # --- 他のタブ ---
    with tabs[0]: # Dashboard
        if not df.empty:
            st.metric("総飼育数", f"{len(df)}匹")
            st.bar_chart(df['モルフ'].value_counts())
            
    with tabs[2]: # Care Record
        if is_admin:
            with st.form("care"):
                s_ids = st.multiselect("対象個体", options=df['ID'].tolist())
                l_date = st.date_input("日付", datetime.now())
                is_f = all(df[df['ID'].isin(s_ids)]['性別'] == 'メス') if s_ids else False
                opts = ["給餌", "掃除", "交配", "メモ"]
                if is_f: opts.insert(3, "排卵(クラッチ)")
                l_item = st.selectbox("項目", opts); l_note = st.text_input("内容")
                if st.form_submit_button("記録"):
                    new_l = [{"ID":i, "日付":l_date.strftime("%Y/%m/%d"), "項目":l_item, "内容":l_note} for i in s_ids]
                    save_all_data(pd.concat([df_logs, pd.DataFrame(new_l)]), "care_logs"); st.rerun()

    with tabs[3]: # New Entry
        if is_admin:
            with st.form("reg"):
                c1, c2 = st.columns(2)
                with c1: rid = st.text_input("ID"); rmo = st.text_input("モルフ"); rse = st.selectbox("性別", ["不明", "オス", "メス"])
                with c2: rbi = st.text_input("生年月日"); rqu = st.select_slider("ランク", options=["S", "A", "B", "C"], value="A"); rpv = st.checkbox("非公開")
                st.write("家系情報")
                cf, cm = st.columns(2)
                with cf: rfmo = st.text_input("父モルフ"); rfid = st.text_input("父ID")
                with cm: rmmo = st.text_input("母モルフ"); rmid = st.text_input("母ID")
                rim1 = st.file_uploader("画像1", type=["jpg","png"]); rim2 = st.file_uploader("画像2", type=["jpg","png"]); rno = st.text_area("備考")
                if st.form_submit_button("登録"):
                    u1 = upload_to_cloudinary(rim1); u2 = upload_to_cloudinary(rim2) if rim2 else ""
                    new_r = {"ID":rid,"モルフ":rmo,"生年月日":rbi,"性別":rse,"クオリティ":rqu,"父親ID":rfid,"父親モルフ":rfmo,"母親ID":rmid,"母親モルフ":rmmo,"画像1":u1,"画像2":u2,"備考":rno,"非公開":str(rpv)}
                    save_all_data(pd.concat([df, pd.DataFrame([new_r])], ignore_index=True)); st.rerun()

    with tabs[4]: # QR Label
        if not df.empty:
            target = st.selectbox("ラベル作成個体", df['ID'].astype(str))
            if st.button("生成"):
                r = df[df['ID'].astype(str) == target].iloc[0]
                lbl = create_label_image(r['ID'], r['モルフ'], r.get('生年月日','-'), r.get('クオリティ','A'))
                st.image(lbl, width=400)

if __name__ == "__main__":
    main()
