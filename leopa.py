import streamlit as st
import csv
import os
from datetime import datetime
from PIL import Image

# 基本設定
FILE_NAME = 'leopa_manager_final.csv'
IMG_DIR = 'レオパ生体画像'
# 画像パス2を追加
FIELDS = ['ID', 'モルフ', '生年月日', '生後日数', '性別', '父親ID', '父親モルフ', '母親ID', '母親モルフ', 'クオリティ', '備考', '画像パス', '画像パス2']

if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

def calculate_age(birthday_str):
    if birthday_str == "不明": return "不明"
    try:
        birth = datetime.strptime(birthday_str, '%Y-%m-%d')
        return f"{(datetime.now() - birth).days}日"
    except: return "不明"

def get_all_data():
    if not os.path.exists(FILE_NAME): return []
    try:
        with open(FILE_NAME, 'r', encoding='utf-8-sig') as f:
            return list(csv.DictReader(f))
    except: return []

def save_all_data(data_list):
    with open(FILE_NAME, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(data_list)

st.set_page_config(page_title="レオパ管理Pro", layout="wide")
st.title("レオパ家系管理システム Pro")

if "edit_target" not in st.session_state:
    st.session_state.edit_target = None

menu = st.sidebar.selectbox("メニュー", ["個体登録", "データ一覧", "家系図表示", "兄弟検索"])
all_data = get_all_data()

current_view = "個体登録" if st.session_state.edit_target else menu

if current_view == "個体登録":
    is_edit = st.session_state.edit_target is not None
    st.header("個体情報の編集" if is_edit else "新規個体登録")
    edit_data = next((r for r in all_data if r['ID'] == st.session_state.edit_target), {}) if is_edit else {}

    with st.form("reg_form", clear_on_submit=not is_edit):
        is_unknown = st.checkbox("生年月日が正確には不明", value=(edit_data.get('生年月日') == "不明"))
        
        col_date, col_year = st.columns(2)
        with col_date:
            try:
                d_val = datetime.strptime(edit_data['生年月日'], '%Y-%m-%d') if edit_data.get('生年月日') and edit_data['生年月日'] != "不明" else datetime.now()
            except: d_val = datetime.now()
            birth_date = st.date_input("生年月日", value=d_val)
        with col_year:
            try:
                d_year = int("20" + edit_data['ID'][:2]) if is_edit else datetime.now().year
            except: d_year = datetime.now().year
            est_year = st.number_input("生まれ年(西暦)", min_value=2000, max_value=2099, value=d_year)

        if is_edit:
            custom_id = st.text_input("識別番号(ID) ※固定", value=edit_data['ID'], disabled=True)
        else:
            year_str = str(est_year)[2:] if is_unknown else birth_date.strftime('%y')
            count_in_year = sum(1 for r in all_data if r['ID'].startswith(year_str))
            suggested_id = year_str + str(count_in_year + 1).zfill(2)
            custom_id = st.text_input("識別番号(ID)", value=suggested_id)
        
        col1, col2 = st.columns(2)
        with col1:
            morph = st.text_input("モルフ", value=edit_data.get('モルフ', ""))
            g_list = ["不明", "オス", "メス"]
            g_idx = g_list.index(edit_data.get('性別')) if edit_data.get('性別') in g_list else 0
            gender = st.selectbox("性別", g_list, index=g_idx)
        with col2:
            q_list = ["A", "B", "C", "D"]
            q_idx = q_list.index(edit_data.get('クオリティ')) if edit_data.get('クオリティ') in q_list else 0
            quality = st.select_slider("クオリティ", options=q_list, value=q_list[q_idx])
            
        st.write("--- 両親の情報 ---")
        c_fa1, c_fa2 = st.columns(2)
        f_id = c_fa1.text_input("父親ID", value=edit_data.get('父親ID', "0000"))
        f_morph = c_fa2.text_input("父親モルフ", value=edit_data.get('父親モルフ', ""))
        c_mo1, c_mo2 = st.columns(2)
        m_id = c_mo1.text_input("母親ID", value=edit_data.get('母親ID', "0000"))
        m_morph = c_mo2.text_input("母親モルフ", value=edit_data.get('母親モルフ', ""))

        note = st.text_area("備考", value=edit_data.get('備考', ""))
        
        st.write("--- 写真（2枚まで登録可能） ---")
        col_img1, col_img2 = st.columns(2)
        uploaded_file1 = col_img1.file_uploader("写真1", type=['jpg', 'jpeg', 'png'])
        uploaded_file2 = col_img2.file_uploader("写真2", type=['jpg', 'jpeg', 'png'])
        
        if st.form_submit_button("保存する"):
            final_birth = "不明" if is_unknown else birth_date.strftime('%Y-%m-%d')
            img_path1 = edit_data.get('画像パス', "")
            img_path2 = edit_data.get('画像パス2', "")
            
            # 画像1の保存
            if uploaded_file1:
                img_path1 = os.path.join(IMG_DIR, f"{custom_id}_1.jpg")
                Image.open(uploaded_file1).save(img_path1)
            # 画像2の保存
            if uploaded_file2:
                img_path2 = os.path.join(IMG_DIR, f"{custom_id}_2.jpg")
                Image.open(uploaded_file2).save(img_path2)
            
            new_row = {
                'ID': custom_id, 'モルフ': morph, '生年月日': final_birth,
                '生後日数': calculate_age(final_birth), '性別': gender,
                '父親ID': f_id, '父親モルフ': f_morph,
                '母親ID': m_id, '母親モルフ': m_morph,
                'クオリティ': quality, '備考': note, 
                '画像パス': img_path1, '画像パス2': img_path2
            }

            if is_edit:
                all_data = [new_row if r['ID'] == custom_id else r for r in all_data]
                st.session_state.edit_target = None
            else:
                all_data.append(new_row)
            
            save_all_data(all_data)
            st.rerun()

    if is_edit:
        if st.button("編集をキャンセル"):
            st.session_state.edit_target = None
            st.rerun()

elif menu == "データ一覧":
    st.header("登録個体一覧")
    if all_data:
        morphs = sorted(list(set(r['モルフ'] for r in all_data if r.get('モルフ'))))
        sel_morph = st.selectbox("モルフで絞り込む", ["すべて"] + morphs)
        
        for row in all_data:
            if sel_morph != "すべて" and row.get('モルフ') != sel_morph: continue
            
            # 表示レイアウト
            st.subheader(f"ID: {row.get('ID')}　{row.get('モルフ')}")
            col_info, col_img_a, col_img_b, col_btn = st.columns([2, 1.5, 1.5, 1])
            
            with col_info:
                st.write(f"**性別**: {row.get('性別')} / **クオリティ**: {row.get('クオリティ')}")
                st.write(f"**誕生日**: {row.get('生年月日')} ({row.get('生後日数')})")
                st.write(f"**父**: {row.get('父親ID')}({row.get('父親モルフ')})")
                st.write(f"**母**: {row.get('母親ID')}({row.get('母親モルフ')})")
                st.info(f"備考: {row.get('備考')}")

            with col_img_a:
                if row.get('画像パス') and os.path.exists(row['画像パス']):
                    st.image(row['画像パス'], use_container_width=True, caption="写真1")
                else: st.write("No Image 1")
                
            with col_img_b:
                if row.get('画像パス2') and os.path.exists(row['画像パス2']):
                    st.image(row['画像パス2'], use_container_width=True, caption="写真2")
                else: st.write("No Image 2")

            with col_btn:
                if st.button("編集", key=f"e_{row['ID']}"):
                    st.session_state.edit_target = row['ID']
                    st.rerun()
                if st.button("削除", key=f"d_{row['ID']}"):
                    new_d = [r for r in all_data if r['ID'] != row['ID']]
                    save_all_data(new_d)
                    st.rerun()
            st.divider()
    else:
        st.write("データなし")

elif menu == "家系図表示":
    st.header("家系図検索")
    target_id = st.text_input("表示したい個体のIDを入力")
    if target_id:
        def display_tree(cid, level=0):
            row = next((r for r in all_data if r['ID'] == cid), None)
            if row:
                st.write("　" * level + f"└ **ID:{row['ID']}** [{row['モルフ']}]")
                if row.get('父親ID') and row['父親ID'] != "0000": display_tree(row['父親ID'], level + 1)
                elif row.get('父親モルフ'): st.write("　" * (level+1) + f"└ 父: [{row['父親モルフ']}]")
                if row.get('母親ID') and row['母親ID'] != "0000": display_tree(row['母親ID'], level + 1)
                elif row.get('母親モルフ'): st.write("　" * (level+1) + f"└ 母: [{row['母親モルフ']}]")
            else: st.warning(f"ID:{cid} は未登録です。")
        display_tree(target_id)

elif menu == "兄弟検索":
    st.header("兄弟検索")
    tid = st.text_input("個体IDを入力")
    if tid:
        me = next((r for r in all_data if r['ID'] == tid), None)
        if me and (me.get('父親ID', '0000') != '0000' or me.get('母親ID', '0000') != '0000'):
            st.subheader(f"ID:{tid} の兄弟一覧")
            for r in all_data:
                if r['ID'] != tid and r.get('父親ID') == me.get('父親ID') and r.get('母親ID') == me.get('母親ID'):
                    st.write(f"・ID:{r['ID']} ({r['モルフ']})")