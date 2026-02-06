import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime
import io
import requests

# QRコードライブラリ
try:
    import qrcode
    from PIL import Image, ImageDraw, ImageOps, ImageFont
    HAS_QR = True
except ImportError:
    HAS_QR = False

# --- 1. 設定 ---
# 運用に合わせて書き換えてください
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"
SPREADSHEET_NAME = "leopa_database"

# Cloudinary設定（Secretsから読み込み）
CLOUDINARY_URL = f"https://api.cloudinary.com/v1_1/{st.secrets.get('CLOUDINARY_CLOUD_NAME', '')}/image/upload"
UPLOAD_PRESET = st.secrets.get('CLOUDINARY_UPLOAD_PRESET', '')

st.set_page_config(page_title="&Gekko System Pro", layout="wide", page_icon="🦎")

# --- 2. デザイン (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .header-container { text-align: center; margin-bottom: 20px; border-bottom: 3px solid #81d1d1; padding-bottom: 10px; }
    .leopa-card { border: 1px solid #ddd; border-radius: 12px; background-color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.08); margin-bottom: 20px; overflow: hidden; position: relative; }
    .img-container { width: 100%; aspect-ratio: 1 / 1; overflow: hidden; position: relative; background-color: #f0f0f0; }
    .img-container img { width: 100%; height: 100%; object-fit: cover; }
    .badge-sex { position: absolute; top: 10px; right: 10px; padding: 5px 12px; border-radius: 20px; color: white; font-weight: bold; font-size: 0.8rem; z-index: 5; }
    .male { background-color: #5dade2; }
    .female { background-color: #ec7063; }
    .unknown { background-color: #aeb6bf; }
    .badge-quality { position: absolute; top: 10px; left: 10px; background-color: rgba(0,0,0,0.7); color: #f1c40f; padding: 3px 10px; border-radius: 5px; font-size: 0.8rem; font-weight: bold; border: 1px solid #f1c40f; z-index: 5; }
    [data-testid="stSidebar"] { display: none; }
    .care-log-entry { padding: 8px 10px; border-bottom: 1px solid #eee; font-size: 0.85rem; background-color: #fff; }
    .log-item-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 8px; font-size: 0.7rem; color: white; }
    /* 項目別カラー */
    .tag-feed { background-color: #27ae60; }
    .tag-clean { background-color: #3498db; }
    .tag-mate { background-color: #9b59b6; }
    .tag-ovul { background-color: #e67e22; }
    .tag-memo { background-color: #7f8c8d; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 共通関数 ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return gspread.authorize(creds)

def load_data(sheet_name=None):
    client = get_gspread_client()
    try:
        sh = client.open(SPREADSHEET_NAME)
        sheet = sh.worksheet(sheet_name) if sheet_name else sh.sheet1
        return pd.DataFrame(sheet.get_all_records())
    except:
        return pd.DataFrame()

def save_all_data(df, sheet_name=None):
    client = get_gspread_client()
    sh = client.open(SPREADSHEET_NAME)
    sheet = sh.worksheet(sheet_name) if sheet_name else sh.sheet1
    sheet.clear()
    data = [df.columns.values.tolist()] + df.astype(str).values.tolist()
    sheet.update(range_name='A1', values=data)

def upload_image(file):
    if not file: return ""
    try:
        files = {"file": file.getvalue()}
        data = {"upload_preset": UPLOAD_PRESET}
        res = requests.post(CLOUDINARY_URL, files=files, data=data)
        return res.json().get("secure_url") if res.status_code == 200 else ""
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
    draw.text((30, 150), f"Rank: {quality}", fill="#f1c40f")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- 4. メイン処理 ---
def main():
    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "is_admin": False})

    if not st.session_state["logged_in"]:
        st.write("### 🔐 MEMBER LOGIN")
        pwd = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": True}); st.rerun()
            elif pwd == VIEW_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": False}); st.rerun()
            else: st.error("パスワードが違います")
        return

    # データ一括読み込み
    df_leopa = load_data()
    df_logs = load_data("care_logs")

    if not df_leopa.empty and not st.session_state["is_admin"]:
        if "非公開" in df_leopa.columns:
            df_leopa = df_leopa[df_leopa["非公開"] != "True"]

    tabs = st.tabs(["📊 ダッシュボード", "🦎 検索・アルバム", "📝 お世話記録", "➕ 新規登録", "🖨️ ラベル生成"])

    # --- Tab 1: 検索・詳細 ---
    with tabs[1]:
        search_text = st.text_input("🔍 IDやモルフで検索")
        v_df = df_leopa.copy()
        if search_text:
            v_df = v_df[v_df['ID'].astype(str).str.contains(search_text) | v_df['モルフ'].str.contains(search_text)]

        if v_df.empty:
            st.info("個体が見つかりません")
        else:
            cols = st.columns(2)
            for i, (idx, row) in enumerate(v_df.iterrows()):
                s_cls = "male" if row['性別'] == "オス" else "female" if row['性別'] == "メス" else "unknown"
                img = row.get("画像1", "")
                if img and not img.startswith("http"): img = f"data:image/jpeg;base64,{img}"
                
                with cols[i % 2]:
                    st.markdown(f'<div class="leopa-card"><div class="img-container"><span class="badge-quality">{row.get("クオリティ","-")}</span><span class="badge-sex {s_cls}">{row["性別"]}</span><img src="{img}"></div><div style="padding:10px;"><b>ID: {row["ID"]}</b><br>{row["モルフ"]}</div></div>', unsafe_allow_html=True)
                    
                    with st.expander("詳細と履歴"):
                        # --- 指定の順番で情報を表示 ---
                        st.write(f"**生年月日:** {row.get('生年月日','-')}")
                        
                        # 間に家系情報を挿入
                        st.write(f"**父親モルフ:** {row.get('父親モルフ','-')}")
                        st.write(f"**父親ID:** {row.get('父親ID','-')}")
                        st.write(f"**母親モルフ:** {row.get('母親モルフ','-')}")
                        st.write(f"**母親ID:** {row.get('母親ID','-')}")
                        
                        st.write(f"**備考:** {row.get('備考','-')}")

                        # サブ画像があれば表示
                        img2 = row.get("画像2", "")
                        if img2:
                            if not img2.startswith("http"): img2 = f"data:image/jpeg;base64,{img2}"
                            st.image(img2, caption="サブ画像", use_container_width=True)
                        
                        st.markdown("---")
                        
                        # --- お世話履歴表示 ---
                        if not df_logs.empty:
                            my_full_logs = df_logs[df_logs['ID'].astype(str) == str(row['ID'])].sort_values('日付', ascending=False)
                            
                            # 給餌記録 (5回分)
                            st.write("**🍖 過去5回の給餌記録**")
                            my_feeds = my_full_logs[my_full_logs['項目'] == '給餌'].head(5)
                            if my_feeds.empty:
                                st.caption("給餌記録はありません")
                            else:
                                for _, l in my_feeds.iterrows():
                                    st.markdown(f'<div class="care-log-entry">📅 {l["日付"]} | {l["内容"]}</div>', unsafe_allow_html=True)
                            
                            # その他履歴
                            st.write("**📋 その他・全履歴**")
                            for _, l in my_full_logs.head(3).iterrows():
                                tag_map = {"給餌": "tag-feed", "掃除": "tag-clean", "交配": "tag-mate", "排卵(クラッチ)": "tag-ovul", "メモ": "tag-memo"}
                                tag_class = tag_map.get(l['項目'], "tag-memo")
                                st.markdown(f'<div class="care-log-entry">📅 {l["日付"]} <span class="log-item-tag {tag_class}">{l["項目"]}</span> {l["内容"]}</div>', unsafe_allow_html=True)
                        else:
                            st.caption("お世話記録がありません")

    # --- Tab 0: ダッシュボード ---
    with tabs[0]:
        if df_leopa.empty: st.info("データがありません")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("総飼育数", f"{len(df_leopa)}匹")
            m_count = len(df_leopa[df_leopa['性別'] == 'オス'])
            f_count = len(df_leopa[df_leopa['性別'] == 'メス'])
            c2.metric("♂/♀", f"{m_count} / {f_count}")
            today_str = datetime.now().strftime("%Y/%m/%d")
            recent_count = len(df_logs[df_logs['日付'] == today_str]) if not df_logs.empty else 0
            c3.metric("今日のお世話", f"{recent_count}件")
            st.subheader("モルフ分布")
            st.bar_chart(df_leopa['モルフ'].value_counts())

    # --- Tab 2: お世話記録 ---
    with tabs[2]:
        if not st.session_state["is_admin"]: st.warning("管理者のみ可能です")
        elif df_leopa.empty: st.info("個体を追加してください")
        else:
            st.subheader("📝 お世話の入力")
            with st.form("care_form_v7"):
                col1, col2 = st.columns(2)
                with col1:
                    selected_ids = st.multiselect("対象個体", options=df_leopa['ID'].tolist())
                    log_date = st.date_input("日付", datetime.now())
                
                is_all_female = False
                if selected_ids:
                    selected_gekkos = df_leopa[df_leopa['ID'].isin(selected_ids)]
                    if all(selected_gekkos['性別'] == 'メス'): is_all_female = True
                
                care_options = ["給餌", "掃除", "交配", "メモ"]
                if is_all_female: care_options.insert(3, "排卵(クラッチ)")
                
                with col2:
                    log_item = st.selectbox("項目", care_options)
                    log_note = st.text_input("内容")
                
                if st.form_submit_button("記録を保存"):
                    if not selected_ids: st.error("個体を選択してください")
                    else:
                        new_logs = []
                        for tid in selected_ids:
                            new_logs.append({"ID": tid, "日付": log_date.strftime("%Y/%m/%d"), "項目": log_item, "内容": log_note})
                        save_all_data(pd.concat([df_logs, pd.DataFrame(new_logs)], ignore_index=True), "care_logs")
                        st.success(f"{len(selected_ids)}件保存しました")
                        st.rerun()

            if not df_logs.empty:
                st.subheader("📋 履歴一覧")
                st.dataframe(df_logs.sort_values('日付', ascending=False), use_container_width=True, hide_index=True)

    # --- Tab 3: 新規登録 ---
    with tabs[3]:
        if st.session_state["is_admin"]:
            st.subheader("➕ 新規個体登録")
            this_y = datetime.now().year
            sel_y = st.selectbox("誕生年", [str(y) for y in range(this_y, this_y - 10, -1)])
            prefix = sel_y[2:]
            count = len(df_leopa[df_leopa["ID"].astype(str).str.startswith(prefix)]) if not df_leopa.empty else 0
            def_id = f"{prefix}{count+1:03d}"

            with st.form("reg_v7"):
                p_check = st.checkbox("非公開")
                c1, c2 = st.columns(2)
                with c1:
                    i_id = st.text_input("個体ID", value=def_id); i_mo = st.text_input("モルフ")
                with c2:
                    i_ge = st.selectbox("性別", ["不明", "オス", "メス"])
                    i_qu = st.select_slider("クオリティ", options=["S", "A", "B", "C"], value="A")
                i_bi = st.text_input("生年月日", value=f"{sel_y}/")
                st.write("家系情報入力")
                c3, c4 = st.columns(2)
                with c3:
                    f_mo_in = st.text_input("父親モルフ"); f_id_in = st.text_input("父親ID")
                with c4:
                    m_mo_in = st.text_input("母親モルフ"); m_id_in = st.text_input("母親ID")
                i_im1 = st.file_uploader("画像1 (必須)", type=["jpg","jpeg","png"])
                i_im2 = st.file_uploader("画像2 (任意)", type=["jpg","jpeg","png"])
                i_no = st.text_area("備考")
                if st.form_submit_button("登録"):
                    if not i_im1: st.error("画像が必要です")
                    else:
                        url1 = upload_image(i_im1)
                        url2 = upload_image(i_im2) if i_im2 else ""
                        new_row = {
                            "ID": i_id, "モルフ": i_mo, "生年月日": i_bi, "性別": i_ge, "クオリティ": i_qu,
                            "父親モルフ": f_mo_in, "父親ID": f_id_in, "母親モルフ": m_mo_in, "母親ID": m_id_in,
                            "画像1": url1, "画像2": url2, "備考": i_no, "非公開": str(p_check)
                        }
                        save_all_data(pd.concat([df_leopa, pd.DataFrame([new_row])], ignore_index=True))
                        st.rerun()
        else: st.warning("管理者のみ可能です")

    # --- Tab 4: ラベル生成 ---
    with tabs[4]:
        if not df_leopa.empty:
            target = st.selectbox("ラベル用個体選択", df_leopa['ID'].astype(str) + " : " + df_leopa['モルフ'])
            if st.button("ラベル生成"):
                tid = target.split(" : ")[0]
                row = df_leopa[df_leopa['ID'].astype(str) == tid].iloc[0]
                l_bytes = create_label_image(row['ID'], row['モルフ'], row.get('生年月日','-'), row.get('クオリティ','-'))
                if l_bytes:
                    st.image(l_bytes, width=400)
                    st.download_button("保存", l_bytes, f"label_{tid}.png", "image/png")

if __name__ == "__main__":
    main()
