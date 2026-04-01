import streamlit as st
import requests
import re
from bs4 import BeautifulSoup

# --- 1. 網頁基礎設定 ---
st.set_page_config(page_title="APA 7 產生器 & 排序小幫手", page_icon="💉", layout="wide")

# 初始化文獻箱
if 'bib_list' not in st.session_state:
    st.session_state.bib_list = []

# 自訂 CSS：醫療綠風格
st.markdown("""
<style>
    .stApp {background-color: #f4f9f4;}
    .stButton>button {width: 100%; border-radius: 10px; background-color: #2e7d32; color: white; font-weight: bold;}
    .stButton>button:hover {background-color: #1b5e20; color: white;}
    h1, h2, h3 {color: #1b5e20;}
    .mascot-dialog {background-color: #e8f5e9; border-left: 5px solid #4caf50; padding: 15px; border-radius: 5px; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# --- 2. 核心邏輯 (API & 解析) ---
def parse_doi(text):
    match = re.search(r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', text, re.IGNORECASE)
    return match.group(1) if match else None

def parse_pubmed_id(text):
    # 抓取 PubMed 網址中的純數字 ID
    match = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', text)
    return match.group(1) if match else None

def fetch_crossref(doi):
    try:
        res = requests.get(f"https://api.crossref.org/works/{doi}", timeout=10)
        if res.status_code == 200:
            data = res.json()['message']
            year = str(data['issued']['date-parts'][0][0]) if 'issued' in data else "n.d."
            title = data.get('title', [''])[0]
            journal = data.get('container-title', [''])[0]
            vol = data.get('volume', '')
            issue = data.get('issue', '')
            page = data.get('page', '')
            
            authors = data.get('author', [])
            auth_list = [f"{a.get('family', '')}, {a.get('given', '')[0]}." for a in authors if a.get('family')]
            if not auth_list: auth_str = "Anonymous"
            elif len(auth_list) == 1: auth_str = auth_list[0]
            else: auth_str = ", ".join(auth_list[:-1]) + f", & {auth_list[-1]}"
            
            return auth_str, year, title, journal, vol, issue, page, f"https://doi.org/{doi}"
    except: return None

def fetch_pubmed(pmid):
    try:
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()['result'][pmid]
            year = data.get('pubdate', '').split(' ')[0] if data.get('pubdate') else "n.d."
            title = data.get('title', '')
            journal = data.get('fulljournalname', '')
            vol = data.get('volume', '')
            issue = data.get('issue', '')
            page = data.get('pages', '')
            doi = data.get('elocationid', '').replace('doi: ', '')
            link = f"https://doi.org/{doi}" if doi.startswith('10.') else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            
            authors = data.get('authors', [])
            auth_list = []
            for a in authors:
                name_parts = a['name'].split(' ')
                if len(name_parts) >= 2:
                    auth_list.append(f"{name_parts[0]}, {name_parts[1][0]}.")
                else:
                    auth_list.append(name_parts[0])
            
            if not auth_list: auth_str = "Anonymous"
            elif len(auth_list) == 1: auth_str = auth_list[0]
            else: auth_str = ", ".join(auth_list[:-1]) + f", & {auth_list[-1]}"
            
            return auth_str, year, title, journal, vol, issue, page, link
    except: return None

def build_apa7(auth, year, title, jou, vol, iss, page, link):
    ref = f"{auth} ({year}). {title}. "
    if jou: ref += f"*{jou}*"
    if vol: ref += f", *{vol}*"
    if iss: ref += f"({iss})"
    if page: ref += f", {page}."
    else: ref += "."
    if link: ref += f" {link}"
    return ref.replace("..", ".")

# --- 3. 側邊欄與導覽 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063205.png", width=120)
    st.markdown("### 👩‍⚕️ 主角來幫忙")
    page = st.radio("你要做什麼？", ["1. 產生成果 (自動/手動)", "2. 排序小幫手 (文獻箱)"])

# --- 4. 頁面 1：產生成果 ---
if page == "1. 產生成果 (自動/手動)":
    st.title("🔗 自動抓取文獻")
    st.markdown("<div class='mascot-dialog'><b>主角：</b>學長姐辛苦了！把 DOI、PubMed 網址，或是華藝網址丟進來，我來幫你想辦法！</div>", unsafe_allow_html=True)
    
    user_input = st.text_input("輸入網址或 DOI：", placeholder="例如: https://pubmed.ncbi.nlm.nih.gov/36669781/ 或 DOI碼")
    
    if st.button("🚀 呼叫主角抓資料"):
        if not user_input:
            st.warning("主角：學長姐，你還沒貼網址啦！")
        else:
            with st.spinner("主角正在翻箱倒櫃..."):
                doi_match = parse_doi(user_input)
                pmid_match = parse_pubmed_id(user_input)
                result_data = None
                
                if doi_match:
                    result_data = fetch_crossref(doi_match)
                elif pmid_match:
                    result_data = fetch_pubmed(pmid_match)
                elif "airiti" in user_input.lower():
                    st.error("主角：靠北，華藝的防護牆太厚了，我被擋在外面... 請學長姐直接把資料貼到下方『完整版手動區塊』！")
                else:
                    st.error("主角：這網址我看不太懂捏，裡面好像沒有 DOI 或 PMID，試試看手動輸入吧！")
                
                if result_data:
                    auth, year, title, jou, vol, iss, page_num, link = result_data
                    final_ref = build_apa7(auth, year, title, jou, vol, iss, page_num, link)
                    st.success("主角：搞定！幫您排好版了！")
                    st.markdown(f"**📝 預覽結果：**\n\n{final_ref}")
                    
                    if st.button("📥 加入我的文獻箱 (排序用)"):
                        st.session_state.bib_list.append({"ref": final_ref, "author": auth})
                        st.toast("主角：已經丟進文獻箱囉！")

    st.divider()
    
    st.title("✍️ 完整版手動輸入")
    st.markdown("<div class='mascot-dialog'><b>主角：</b>如果是沒有 DOI 的老文章，或是死都不讓我抓的華藝，就在這裡手動填吧！欄位我都準備好了！</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        m_auth = st.text_input("👥 作者群 (請用 '&' 或逗號分隔)", placeholder="例如: 王小明, & 李大華 或 Smith, J., & Doe, A.")
        m_year = st.text_input("📅 出版年份", placeholder="例如: 2026")
        m_title = st.text_area("📄 文章標題", placeholder="例如: 台灣護理師職場暴力之探討")
    with col2:
        m_jou = st.text_input("📖 期刊名稱", placeholder="例如: 護理雜誌")
        col2_1, col2_2, col2_3 = st.columns(3)
        with col2_1:
            m_vol = st.text_input("📚 卷號 (Volume)", placeholder="例如: 70")
        with col2_2:
            m_iss = st.text_input("🏷️ 期號 (Issue)", placeholder="例如: 2")
        with col2_3:
            m_page = st.text_input("📑 頁碼", placeholder="例如: 12-24")
        m_link = st.text_input("🔗 網址或 DOI (選填)", placeholder="例如: https://doi.org/10.xxxx")

    if st.button("✨ 手動組合並加入文獻箱"):
        if m_auth and m_title:
            manual_ref = build_apa7(m_auth, m_year, m_title, m_jou, m_vol, m_iss, m_page, m_link)
            st.session_state.bib_list.append({"ref": manual_ref, "author": m_auth})
            st.success("主角：手動排版完成！已經幫您丟進文獻箱了！")
            st.markdown(f"**📝 預覽：**\n\n{manual_ref}")
        else:
            st.warning("主角：至少要填寫『作者』跟『標題』我才能排版啦！")

# --- 5. 頁面 2：排序小幫手 ---
elif page == "2. 排序小幫手 (文獻箱)":
    st.title("🗂️ 文獻箱與排序")
    
    if not st.session_state.bib_list:
        st.markdown("<div class='mascot-dialog'><b>主角 (打瞌睡中...)：</b>嗯？文獻箱是空的啊... 學長姐快去前面抓幾篇回來！</div>", unsafe_allow_html=True)
    else:
        st.write(f"主角：目前收集了 **{len(st.session_state.bib_list)}** 篇文獻，請選擇排序方式！")
        sort_option = st.selectbox("選擇排序規則", ["按作者 A-Z (APA 預設)", "中文在前，英文在後", "英文在前，中文在後"])
        
        sorted_list = st.session_state.bib_list.copy()
        
        if sort_option == "按作者 A-Z (APA 預設)":
            sorted_list.sort(key=lambda x: x['author'].lower())
        elif "中文在前" in sort_option:
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

        st.markdown("### 📋 最終成果 (請直接複製貼上 Word)")
        final_text = "\n\n".join([item['ref'] for item in sorted_list])
        st.code(final_text, language="markdown")
        
        if st.button("🗑️ 寫完了，清空文獻箱！"):
            st.session_state.bib_list = []
            st.rerun()
