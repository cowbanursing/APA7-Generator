import streamlit as st
import requests
import re

# --- 1. 網頁基礎設定 ---
st.set_page_config(page_title="APA 7 產生器 & 排序小幫手", page_icon="📋", layout="wide")

# 初始化文獻箱 (如果不存在就建立一個空的清單)
if 'bib_list' not in st.session_state:
    st.session_state.bib_list = []

# 自訂 CSS：醫療綠風格
st.markdown("""
<style>
    .stApp {background-color: #f0f7f4;}
    .stButton>button {width: 100%; border-radius: 20px; background-color: #2e7d32; color: white;}
    .css-10trblm {color: #2e7d32;}
    .st-emotion-cache-1kyx603 {border: 1px solid #c8e6c9; background-color: white; padding: 20px; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# --- 2. 工具函數 ---
def extract_doi(text):
    match = re.search(r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', text, re.IGNORECASE)
    return match.group(1) if match else None

def fetch_metadata(doi):
    url = f"https://api.crossref.org/works/{doi}"
    try:
        res = requests.get(url, timeout=10)
        return res.json()['message'] if res.status_code == 200 else None
    except: return None

def generate_apa7_parts(data):
    # 此處邏輯與前版本相同，提取作者、年份、標題、期刊
    try: year = str(data['issued']['date-parts'][0][0])
    except: year = "n.d."
    title = data.get('title', ['無標題'])[0]
    journal = data.get('container-title', [''])[0]
    authors = data.get('author', [])
    
    auth_list = [f"{a.get('family', '')}, {a.get('given', '')[0]}." for a in authors if a.get('family')]
    if not auth_list: auth_str = "Anonymous"
    elif len(auth_list) == 1: auth_str = auth_list[0]
    else: auth_str = ", ".join(auth_list[:-1]) + f", & {auth_list[-1]}"
    
    full_ref = f"{auth_str} ({year}). {title}. *{journal}*. https://doi.org/{data.get('DOI')}"
    return {"ref": full_ref, "author": auth_str, "year": year}

# --- 3. 側邊欄導覽 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063205.png", width=100)
    st.title("主角助手")
    page = st.radio("功能選單", ["1. 產生成果", "2. 排序小幫手"])
    st.info("提示：抓取的文獻會暫存在『排序小幫手』中，網頁重整後會清空喔！")

# --- 4. 頁面邏輯 ---

if page == "1. 產生成果":
    st.title("📝 APA 7 文獻抓取")
    user_input = st.text_input("貼上 DOI 或 網址：", placeholder="例如: 10.1016/j.iccn.2023.103399")
    
    if st.button("開始抓取"):
        doi = extract_doi(user_input)
        if doi:
            with st.spinner("主角翻找中..."):
                data = fetch_metadata(doi)
                if data:
                    result = generate_apa7_parts(data)
                    st.success("成功抓取！")
                    st.markdown(f"**預覽：** \n\n {result['ref']}")
                    
                    # 加入收藏箱按鈕
                    if st.button("📥 加入我的文獻箱"):
                        st.session_state.bib_list.append(result)
                        st.toast("已加入！可以去左側『排序小幫手』查看")
                else: st.error("找不到該 DOI 資料。")
        else: st.error("請提供正確的 DOI 格式。")

    st.divider()
    with st.expander("無法抓取？手動輸入並加入清單"):
        m_auth = st.text_input("作者 (例: 王小明)")
        m_year = st.text_input("年份")
        m_title = st.text_input("標題")
        m_jou = st.text_input("期刊")
        if st.button("手動加入清單"):
            manual_ref = f"{m_auth} ({m_year}). {m_title}. *{m_jou}*."
            st.session_state.bib_list.append({"ref": manual_ref, "author": m_auth, "year": m_year})
            st.toast("手動文獻已加入！")

elif page == "2. 排序小幫手":
    st.title("🗂️ 文獻排序整理")
    
    if not st.session_state.bib_list:
        st.write("😱 文獻箱還是空的！主角在打瞌睡...快去抓點東西回來。")
    else:
        st.write(f"目前文獻箱內共有 {len(st.session_state.bib_list)} 篇資料。")
        
        sort_option = st.selectbox("選擇排序規則", 
            ["按作者 A-Z (APA 標準)", "中文在前，英文在後", "英文在前，中文在後"])
        
        # 排序邏輯
        sorted_list = st.session_state.bib_list.copy()
        
        if sort_option == "按作者 A-Z (APA 標準)":
            sorted_list.sort(key=lambda x: x['author'].lower())
        elif "中文在前" in sort_option:
            # 區分中英文
            cn = [i for i in sorted_list if re.search(r'[\u4e00-\u9fff]', i['author'])]
            en = [i for i in sorted_list if not re.search(r'[\u4e00-\u9fff]', i['author'])]
            cn.sort(key=lambda x: x['author'])
            en.sort(key=lambda x: x['author'].lower())
            sorted_list = cn + en
        elif "英文在前" in sort_option:
            cn = [i for i in sorted_list if re.search(r'[\u4e00-\u9fff]', i['author'])]
            en = [i for i in sorted_list if not re.search(r'[\u4e00-\u9fff]', i['author'])]
            cn.sort(key=lambda x: x['author'])
            en.sort(key=lambda x: x['author'].lower())
            sorted_list = en + cn

        # 顯示結果
        st.markdown("### 📋 排序後的文獻 (直接複製貼上 Word)")
        final_text = "\n\n".join([item['ref'] for item in sorted_list])
        st.code(final_text, language="markdown")
        
        if st.button("🗑️ 清空文獻箱"):
            st.session_state.bib_list = []
            st.rerun()