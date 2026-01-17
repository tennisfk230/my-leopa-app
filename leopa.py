import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
import os
from datetime import datetime
import io

# QRコードライブラリのインポート（なければエラー回避）
try:
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
    HAS_QR = True
except ImportError:
    HAS_QR = False

# --- 1. 基本設定 ---
ADMIN_PASSWORD = "lucafk"
VIEW_PASSWORD = "andgekko"
SPREADSHEET_NAME = "leopa_database"

st.set_page_config(page_title="&Gekko System", layout="wide", page_icon="🦎")

# --- 2. プロ仕様デザイン（CSS） ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    
    /* ヘッダー */
    .header-container {
        text-align: center;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 3px solid #81d1d1;
    }
    
    /* タブのデザイン */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #ffffff;
        border-radius: 10px 10px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e0f2f2;
        border-bottom: 2px solid #81d1d1;
        font-weight: bold;
        color: #000;
    }

    /* 検索フィルターエリア */
    .filter-box {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }

    /* インスタ風カード（リッチ版） */
    .leopa-card {
        border: 1px solid #eee;
        border-radius: 12px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        overflow: hidden;
        position: relative;
        transition: transform 0.2s;
    }
    .leopa-card:hover { transform: translateY(-3px); }
    
    .img-container {
        width: 100%;
        aspect-ratio: 1 / 1;
        overflow: hidden;
        position: relative;
    }
    .img-container img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    /* 性別バッジ */
    .badge-sex {
        position: absolute;
        top: 10px;
        right: 10px;
        padding: 5px 10px;
        border-radius: 20px;
        font-weight: bold;
        color: white;
        font-size: 0.8rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .male { background-color: #5dade2; }
    .female { background-color: #ec7063; }
    .unknown { background-color: #aeb6bf; }

    /* クオリティタグ */
    .badge-quality {
        position: absolute;
        top: 10px;
        left: 10px;
        background-color: rgba(0,0,0,0.6);
        color: #f1c40f;
        padding: 2px 8px;
        border-radius: 5px;
        font-size: 0.8rem;
        font-weight: bold;
        border: 1px solid #f1c40f;
    }

    .card-text { padding: 12px; text-align: left; }
    .card-id { font-weight: bold; color: #333; font-size: 1.1rem; }
    .card-morph { color: #555; font-size: 0.9rem; margin-top: 4px;}
    .card-date { color: #999; font-size: 0.8rem; margin-top: 4px; }

    /* サイドバー隠し */
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
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
    sheet.update(range_name='A1', values=[df.columns.values.tolist()] + df.astype(str).values.tolist())

def convert_image(file):
    return base64.b64encode(file.read()).decode() if file else ""

# QRコード付きラベル生成関数
def create_label_image(id_val, morph, birth, quality):
    if not HAS_QR:
        return None
    
    # 1. 土台の白いカードを作る
    width, height = 400, 200
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # 2. QRコード生成（中身はIDとモルフのテキスト情報）
    qr_data = f"ID:{id_val}\nMorph:{morph}\nBirth:{birth}"
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # 3. 画像に配置
    img.paste(qr_img, (260, 20)) # 右側に配置
    
    # 4. 文字を描画（フォントがない場合はデフォルト）
    # 黒い枠線
    draw.rectangle([(10, 10), (390, 190)], outline="#81d1d1", width=5)
    
    draw.text((30, 30), f"ID: {id_val}", fill="black", font_size=20)
    draw.text((30, 70), f"{morph}", fill="black")
    draw.text((30, 110), f"Birth: {birth}", fill="gray")
    draw.text((30, 150), f"Rank: {quality}", fill="#f1c40f")
    draw.text((340, 160), "&Gekko", fill="#81d1d1")

    # ストリームに変換して返す
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
        # === アプリケーション本編 ===
        
        # データをロード
        df = load_data()
        if not df.empty and not st.session_state["is_admin"]:
            if "非公開" in df.columns:
                df = df[df["非公開"] != "True"]

        # タブメニュー（これが新しいナビゲーションです）
        tabs = st.tabs(["📊 ダッシュボード", "🦎 アルバム・検索", "➕ 新規登録", "🖨️ ラベル生成"])

        # --- TAB 1: ダッシュボード ---
        with tabs[0]:
            st.markdown("### 📈 Breeding Dashboard")
            if df.empty:
                st.info("データがありません")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("総飼育数", f"{len(df)}匹")
                
                male_cnt = len(df[df['性別'] == 'オス'])
                female_cnt = len(df[df['性別'] == 'メス'])
                c2.metric("♂ オス", f"{male_cnt}匹")
                c3.metric("♀ メス", f"{female_cnt}匹")
                
                st.markdown("---")
                # 簡易的なグラフ
                st.caption("モルフ別内訳")
                st.bar_chart(df['モルフ'].value_counts())

        # --- TAB 2: アルバム & 検索 ---
        with tabs[1]:
            # 🔍 検索フィルター機能
            with st.expander("🔍 検索・絞り込み条件を開く", expanded=False):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filter_sex = st.multiselect("性別", options=["オス", "メス", "不明"])
                    filter_quality = st.multiselect("クオリティ", options=["S", "A", "B", "C"])
                with col_f2:
                    search_text = st.text_input("キーワード検索 (ID, モルフ名など)")
            
            # フィルタリング実行
            view_df = df.copy()
            if not view_df.empty:
                if filter_sex:
                    view_df = view_df[view_df['性別'].isin(filter_sex)]
                if filter_quality:
                    view_df = view_df[view_df['クオリティ'].isin(filter_quality)]
                if search_text:
                    view_df = view_df[
                        view_df['ID'].astype(str).str.contains(search_text, case=False) |
                        view_df['モルフ'].astype(str).str.contains(search_text, case=False)
                    ]

            st.markdown(f"**検索結果: {len(view_df)} 匹**")

            # グリッド表示
            cols = st.columns(2) # 2列表示
            for i, (idx, row) in enumerate(view_df.iterrows()):
                # 性別による色の決定
                sex_class = "male" if row['性別'] == "オス" else "female" if row['性別'] == "メス" else "unknown"
                sex_icon = "♂" if row['性別'] == "オス" else "♀" if row['性別'] == "メス" else "?"
                
                with cols[i % 2]:
                    # HTML/CSSによるリッチカード描画
                    st.markdown(f"""
                        <div class="leopa-card">
                            <div class="img-container">
                                <span class="badge-quality">{row.get('クオリティ', '-')}</span>
                                <span class="badge-sex {sex_class}">{sex_icon}</span>
                                <img src="data:image/jpeg;base64,{row.get('画像1', '')}">
                            </div>
                            <div class="card-text">
                                <div class="card-id">{row.get('ID', '-')}</div>
                                <div class="card-morph">{row.get('モルフ', '-')}</div>
                                <div class="card-date">🎂 {row.get('生年月日', '-')}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 詳細ボタン
                    with st.expander("詳細 & 血統"):
                        t1, t2 = st.tabs(["基本情報", "🧬 血統・親情報"])
                        
                        with t1:
                            st.write(f"**性別:** {row.get('性別', '-')}")
                            st.write(f"**誕生日:** {row.get('生年月日', '-')}")
                            st.write(f"**備考:** {row.get('備考', '-')}")
                            if row.get("画像2"):
                                st.image(f"data:image/jpeg;base64,{row['画像2']}", use_container_width=True)

                        with t2:
                            # 親情報の表示と検索（簡易ペディグリー機能）
                            col_p1, col_p2 = st.columns(2)
                            
                            # 父親検索
                            father_id = str(row.get('父親ID', ''))
                            with col_p1:
                                st.markdown("#### 🟦 Father")
                                st.write(f"ID: {father_id}")
                                st.write(f"モルフ: {row.get('父親モルフ', '-')}")
                                # データベース内に親がいるか探す
                                if father_id and not df.empty:
                                    father_row = df[df['ID'].astype(str) == father_id]
                                    if not father_row.empty:
                                        st.success("親個体をDBで発見")
                                        st.image(f"data:image/jpeg;base64,{father_row.iloc[0]['画像1']}", use_container_width=True)

                            # 母親検索
                            mother_id = str(row.get('母親ID', ''))
                            with col_p2:
                                st.markdown("#### 🟥 Mother")
                                st.write(f"ID: {mother_id}")
                                st.write(f"モルフ: {row.get('母親モルフ', '-')}")
                                if mother_id and not df.empty:
                                    mother_row = df[df['ID'].astype(str) == mother_id]
                                    if not mother_row.empty:
                                        st.success("親個体をDBで発見")
                                        st.image(f"data:image/jpeg;base64,{mother_row.iloc[0]['画像1']}", use_container_width=True)

                        if st.session_state["is_admin"]:
                            if st.button("データを削除", key=f"del_{idx}"):
                                save_all_data(df.drop(idx)); st.rerun()

        # --- TAB 3: 新規登録 ---
        with tabs[2]:
            st.markdown("### 📝 新規個体登録")
            # 1. 誕生年選択
            this_year = datetime.now().year
            years = [str(y) for y in range(this_year, this_year - 15, -1)]
            selected_year = st.selectbox("誕生年を選択（ID自動生成用）", years)
            
            # IDプレフィックス計算
            year_prefix = selected_year[2:]
            count_in_year = 0
            if not df.empty:
                ids = df["ID"].astype(str)
                count_in_year = len(ids[ids.str.startswith(year_prefix)])
            auto_id_val = f"{year_prefix}{count_in_year + 1:03d}"

            with st.form("reg_form", clear_on_submit=True):
                is_p = st.checkbox("非公開にする")
                col1, col2 = st.columns(2)
                with col1:
                    id_v = st.text_input("個体ID", value=auto_id_val)
                    bi_str = st.text_input("生年月日 (例: 2026/05/10, 2026/不明)", value=f"{selected_year}/")
                with col2:
                    mo = st.text_input("モルフ")
                    ge = st.selectbox("性別", ["不明", "オス", "メス"])
                qu = st.select_slider("クオリティ", options=["S", "A", "B", "C"])
                
                st.markdown("---")
                st.caption("🧬 血統情報")
                col_k1, col_k2 = st.columns(2)
                with col_k1:
                    f_id = st.text_input("父親ID")
                    f_mo = st.text_input("父親モルフ")
                with col_k2:
                    m_id = st.text_input("母親ID")
                    m_mo = st.text_input("母親モルフ")
                st.markdown("---")
                
                im1 = st.file_uploader("画像1枚目 (メイン)", type=["jpg", "jpeg", "png"])
                im2 = st.file_uploader("画像2枚目 (詳細用)", type=["jpg", "jpeg", "png"])
                no = st.text_area("備考")
                
                if st.form_submit_button("登録する"):
                    new_data = {
                        "ID":id_v, "モルフ":mo, "生年月日":bi_str, "性別":ge, "クオリティ":qu,
                        "父親ID":f_id, "父親モルフ":f_mo, "母親ID":m_id, "母親モルフ":m_mo,
                        "画像1":convert_image(im1), "画像2":convert_image(im2), "備考":no, "非公開": str(is_p)
                    }
                    df_all = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                    save_all_data(df_all)
                    st.success(f"ID {id_v} を登録しました！")
                    st.balloons()

        # --- TAB 4: ラベル生成 ---
        with tabs[3]:
            st.markdown("### 🖨️ ケージ用ラベル作成")
            if not HAS_QR:
                st.error("⚠️ QRコード機能を使うには、requirements.txt に 'qrcode' を追加してください。")
            else:
                if df.empty:
                    st.warning("データがありません")
                else:
                    # ラベルを作りたい個体を選択
                    label_target = st.selectbox("個体を選択してください", df['ID'].astype(str) + " : " + df['モルフ'])
                    
                    if st.button("ラベルを生成する"):
                        target_id = label_target.split(" : ")[0]
                        row = df[df['ID'].astype(str) == target_id].iloc[0]
                        
                        # 画像生成実行
                        label_img_bytes = create_label_image(
                            row['ID'], row['モルフ'], row['生年月日'], row['クオリティ']
                        )
                        
                        st.image(label_img_bytes, caption=f"ID: {target_id} のラベル", width=400)
                        
                        # ダウンロードボタン
                        st.download_button(
                            label="画像をダウンロード",
                            data=label_img_bytes,
                            file_name=f"label_{target_id}.png",
                            mime="image/png"
                        )

if __name__ == "__main__":
    main()
