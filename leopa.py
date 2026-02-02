import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime
import io
import requests

# QRコード生成ライブラリのインポート確認
try:
    import qrcode
    from PIL import Image, ImageDraw, ImageOps, ImageFont
    HAS_QR = True
except ImportError:
    HAS_QR = False

# --- 1. 定数・設定 ---
# セキュリティのため、本来は secrets.toml などで管理することを推奨します
ADMIN_PASSWORD = "lucafk"  # 管理者用
VIEW_PASSWORD = "andgekko"  # 閲覧用
SPREADSHEET_NAME = "leopa_database"

# Cloudinary APIエンドポイント（Secretsから取得）
CLOUDINARY_URL = f"https://api.cloudinary.com/v1_1/{st.secrets.get('CLOUDINARY_CLOUD_NAME', '')}/image/upload"
UPLOAD_PRESET = st.secrets.get('CLOUDINARY_UPLOAD_PRESET', '')

st.set_page_config(page_title="&Gekko System", layout="wide", page_icon="🦎")

# --- 2. スタイル（CSS）定義 ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .header-container { text-align: center; margin-bottom: 20px; border-bottom: 3px solid #81d1d1; padding-bottom: 10px; }
    .leopa-card { 
        border: 1px solid #ddd; 
        border-radius: 12px; 
        background-color: white; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.08); 
        margin-bottom: 20px; 
        overflow: hidden; 
        position: relative; 
        transition: transform 0.2s;
    }
    .leopa-card:hover { transform: translateY(-5px); }
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
    /* サイドバーを隠す設定 */
    [data-testid="stSidebar"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 3. データベース（Google Sheets）関数 ---
def get_gspread_client():
    """Google Sheets APIクライアントの初期化"""
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
        creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google API接続エラー: {e}")
        return None

def load_data():
    """スプレッドシートから全データを読み込む"""
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    try:
        sheet = client.open(SPREADSHEET_NAME).sheet1
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"データ読み込みエラー（シートが空の可能性があります）: {e}")
        return pd.DataFrame()

def save_all_data(df):
    """データフレーム全体をスプレッドシートに保存"""
    client = get_gspread_client()
    if not client: return
    try:
        sheet = client.open(SPREADSHEET_NAME).sheet1
        sheet.clear()
        # 列名を含めたデータリストの作成
        data = [df.columns.values.tolist()] + df.astype(str).values.tolist()
        sheet.update(range_name='A1', values=data)
        st.success("データベースを更新しました。")
    except Exception as e:
        st.error(f"データ保存エラー: {e}")

# --- 4. 画像処理・Cloudinary関数 ---
def upload_to_cloudinary(file):
    """画像を最適化してCloudinaryにアップロードし、URLを取得する"""
    if not file: return ""
    try:
        # 画像の読み込みとEXIFに基づく回転修正
        img = Image.open(file)
        img = ImageOps.exif_transpose(img)
        
        # メモリ内でJPEGに圧縮 (画質85)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        buf.seek(0)
        
        # Cloudinaryへ送信
        files = {"file": buf}
        data = {"upload_preset": UPLOAD_PRESET}
        res = requests.post(CLOUDINARY_URL, files=files, data=data)
        
        if res.status_code == 200:
            return res.json().get("secure_url")
        else:
            st.error(f"Cloudinaryアップロード失敗: {res.text}")
            return ""
    except Exception as e:
        st.error(f"画像処理エラー: {e}")
        return ""

def create_label_image(id_val, morph, birth, quality):
    """個体識別用のQRコード付きラベル画像を生成"""
    if not HAS_QR: return None
    
    width, height = 400, 220
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # QRコードの作成
    qr = qrcode.QRCode(box_size=4, border=1)
    # 本来は個体詳細URLなどを入れると便利
    qr.add_data(f"ID:{id_val}\nMorph:{morph}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    img.paste(qr_img, (250, 25))
    
    # デザイン枠とテキスト
    draw.rectangle([(10, 10), (390, 210)], outline="#81d1d1", width=3)
    
    # テキスト描画（フォントがない場合はデフォルト）
    try:
        f_main = ImageFont.load_default()
    except:
        f_main = None

    draw.text((30, 30), f"ID: {id_val}", fill="black", font=f_main)
    draw.text((30, 70), f"{morph}", fill="#2c3e50", font=f_main)
    draw.text((30, 110), f"Birth: {birth}", fill="#7f8c8d", font=f_main)
    draw.text((30, 150), f"Rank: {quality}", fill="#f1c40f", font=f_main)
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- 5. メインアプリケーションUI ---
def main():
    # ロゴ表示
    if os.path.exists("logo_gekko.png"):
        st.markdown('<div class="header-container">', unsafe_allow_html=True)
        st.image("logo_gekko.png", width=300)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<h1 style="text-align:center; color:#81d1d1;">&Gekko System</h1>', unsafe_allow_html=True)

    # ログイン管理
    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "is_admin": False})

    if not st.session_state["logged_in"]:
        st.write("### 🔐 MEMBER LOGIN")
        pwd = st.text_input("パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": True})
                st.rerun()
            elif pwd == VIEW_PASSWORD:
                st.session_state.update({"logged_in": True, "is_admin": False})
                st.rerun()
            else:
                st.error("パスワードが正しくありません")
        return

    # データ読み込み
    df = load_data()
    
    # 非公開データのフィルタリング（一般ユーザーの場合）
    if not df.empty and not st.session_state["is_admin"]:
        if "非公開" in df.columns:
            df = df[df["非公開"].astype(str).str.lower() != "true"]

    tabs = st.tabs(["📊 ダッシュボード", "🦎 検索・アルバム", "➕ 新規登録", "🖨️ ラベル生成"])

    # --- Tab 0: ダッシュボード ---
    with tabs[0]:
        if df.empty:
            st.info("データが登録されていません")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("総飼育数", f"{len(df)} 匹")
            c2.metric("オス (♂)", f"{len(df[df['性別'] == 'オス'])} 匹")
            c3.metric("メス (♀)", f"{len(df[df['性別'] == 'メス'])} 匹")
            c4.metric("不明", f"{len(df[df['性別'] == '不明'])} 匹")
            
            st.subheader("モルフ分布")
            st.bar_chart(df['モルフ'].value_counts())

    # --- Tab 1: アルバム & 編集 ---
    with tabs[1]:
        with st.expander("🔍 検索・フィルタ"):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                f_sex = st.multiselect("性別", options=["オス", "メス", "不明"])
            with col_f2:
                f_qual = st.multiselect("クオリティ", options=["S", "A", "B", "C"])
            with col_f3:
                s_query = st.text_input("キーワード (ID/モルフ)")

        view_df = df.copy()
        if not view_df.empty:
            if f_sex: view_df = view_df[view_df['性別'].isin(f_sex)]
            if f_qual: view_df = view_df[view_df['クオリティ'].isin(f_qual)]
            if s_query:
                view_df = view_df[
                    view_df['ID'].astype(str).str.contains(s_query, case=False) | 
                    view_df['モルフ'].astype(str).str.contains(s_query, case=False)
                ]

        if view_df.empty:
            st.write("該当する個体がいません")
        else:
            # 2列グリッドで表示
            cols = st.columns(2)
            for i, (idx, row) in enumerate(view_df.iterrows()):
                gender_class = "male" if row['性別'] == "オス" else "female" if row['性別'] == "メス" else "unknown"
                gender_icon = "♂" if row['性別'] == "オス" else "♀" if row['性別'] == "メス" else "?"
                
                img_url = row.get("画像1", "")
                # Base64互換性維持
                if img_url and not img_url.startswith("http"):
                    img_url = f"data:image/jpeg;base64,{img_url}"

                with cols[i % 2]:
                    # カード型UIの構築
                    st.markdown(f"""
                        <div class="leopa-card">
                            <div class="img-container">
                                <span class="badge-quality">{row.get('クオリティ','-')}</span>
                                <span class="badge-sex {gender_class}">{gender_icon}</span>
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
                        else:
                            edit_mode = False
                        
                        if not edit_mode:
                            # 表示モード
                            t1, t2 = st.tabs(["基本データ", "🧬 家系図"])
                            with t1:
                                st.write(f"**生年月日:** {row.get('生年月日','-')}")
                                st.write(f"**備考:** {row.get('備考','-')}")
                                if row.get("画像2"):
                                    img2 = row.get("画像2")
                                    if not img2.startswith("http"): img2 = f"data:image/jpeg;base64,{img2}"
                                    st.image(img2, caption="サブ画像", use_container_width=True)
                            with t2:
                                st.write(f"**父:** {row.get('父親ID','-')} ({row.get('父親モルフ','-')})")
                                st.write(f"**母:** {row.get('母親ID','-')} ({row.get('母親モルフ','-')})")
                        else:
                            # 編集モード（フォーム）
                            with st.form(f"form_edit_{idx}"):
                                e_morph = st.text_input("モルフ", value=row['モルフ'])
                                e_sex = st.selectbox("性別", ["不明", "オス", "メス"], index=["不明", "オス", "メス"].index(row['性別']))
                                e_qual = st.select_slider("クオリティ", options=["S", "A", "B", "C"], value=row['クオリティ'])
                                e_note = st.text_area("備考", value=row.get('備考',''))
                                e_img1 = st.file_uploader("画像1更新", type=["jpg","png"], key=f"fu1_{idx}")
                                
                                if st.form_submit_button("更新を保存"):
                                    df.at[idx, 'モルフ'] = e_morph
                                    df.at[idx, '性別'] = e_sex
                                    df.at[idx, 'クオリティ'] = e_qual
                                    df.at[idx, '備考'] = e_note
                                    if e_img1:
                                        new_url = upload_to_cloudinary(e_img1)
                                        if new_url: df.at[idx, '画像1'] = new_url
                                    save_all_data(df)
                                    st.rerun()
                            
                            if st.button("🗑️ この個体を削除", key=f"del_btn_{idx}", type="secondary"):
                                save_all_data(df.drop(idx))
                                st.rerun()

    # --- Tab 2: 新規登録 ---
    with tabs[2]:
        if not st.session_state["is_admin"]:
            st.warning("登録権限がありません")
        else:
            st.subheader("📝 新規個体登録")
            this_year = datetime.now().year
            reg_year = st.selectbox("誕生年", [str(y) for y in range(this_year, this_year - 10, -1)])
            
            prefix = reg_year[2:] # 年の下2桁
            count = len(df[df["ID"].astype(str).str.startswith(prefix)]) if not df.empty else 0
            suggested_id = f"{prefix}{count+1:03d}"

            with st.form("new_registration", clear_on_submit=True):
                is_private = st.checkbox("非公開（自分のみ閲覧）")
                c_id = st.text_input("個体ID", value=suggested_id)
                c_morph = st.text_input("モルフ名")
                c_sex = st.selectbox("性別", ["不明", "オス", "メス"])
                c_qual = st.select_slider("クオリティ", options=["S", "A", "B", "C"], value="A")
                c_birth = st.text_input("生年月日 (YYYY/MM/DD)", value=f"{reg_year}/")
                
                st.markdown("---")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    f_id = st.text_input("父親ID"); f_mo = st.text_input("父親モルフ")
                with col_p2:
                    m_id = st.text_input("母親ID"); m_mo = st.text_input("母親モルフ")
                
                new_img1 = st.file_uploader("メイン画像 (必須)", type=["jpg", "jpeg", "png"])
                new_img2 = st.file_uploader("サブ画像", type=["jpg", "jpeg", "png"])
                new_note = st.text_area("備考")
                
                if st.form_submit_button("データベースに登録"):
                    if not new_img1:
                        st.error("メイン画像は必須です")
                    else:
                        with st.spinner("画像をアップロード中..."):
                            url1 = upload_to_cloudinary(new_img1)
                            url2 = upload_to_cloudinary(new_img2) if new_img2 else ""
                            
                            new_data = {
                                "ID": c_id, "モルフ": c_morph, "生年月日": c_birth, "性別": c_sex, 
                                "クオリティ": c_qual, "父親ID": f_id, "父親モルフ": f_mo,
                                "母親ID": m_id, "母親モルフ": m_mo, "画像1": url1, "画像2": url2, 
                                "備考": new_note, "非公開": str(is_private)
                            }
                            updated_df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                            save_all_data(updated_df)
                            st.rerun()

    # --- Tab 3: ラベル生成 ---
    with tabs[3]:
        st.subheader("🖨️ 管理用ラベルの作成")
        if df.empty:
            st.info("データがありません")
        else:
            target_label = st.selectbox("個体を選択", df['ID'].astype(str) + " : " + df['モルフ'])
            if st.button("ラベルを生成"):
                target_id = target_label.split(" : ")[0]
                target_row = df[df['ID'].astype(str) == target_id].iloc[0]
                
                label_bytes = create_label_image(
                    target_row['ID'], target_row['モルフ'], 
                    target_row.get('生年月日','-'), target_row.get('クオリティ','-')
                )
                
                if label_bytes:
                    st.image(label_bytes, width=400)
                    st.download_button(
                        label=f"ラベル(ID:{target_id})を保存",
                        data=label_bytes,
                        file_name=f"label_{target_id}.png",
                        mime="image/png"
                    )

if __name__ == "__main__":
    main()
