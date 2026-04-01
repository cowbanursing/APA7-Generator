import streamlit as st
import requests
import re
from bs4 import BeautifulSoup

# --- 1. 網頁基礎設定 ---
st.set_page_config(page_title="APA 7 產生器 & 排序小幫手", page_icon="💉", layout="wide")

# 初始化所有的暫存區
if 'bib_list' not in st.session_state:
    st.session_state.bib_list = []
if 'temp_fetch' not in st.session_state:
    st.session_state.temp_fetch = None
if 'temp_manual' not in st.session_state:
    st.session_state.temp_manual = None

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

# --- 2. 核心邏輯 (格式化與 API) ---
def format_authors(raw_auths):
    if not raw_auths: return "Anonymous", []
    ref_auths = []
    last_names = []
    for last, init in raw_auths:
        last_names.append(last)
        if init: ref_auths.append(f"{last}, {init}.")
        else: ref_auths.append(last)
            
    if len(ref_auths) == 1:
        return ref_auths[0], last_names
    elif len(ref_auths) == 2:
        return f"{ref_auths[0]}, & {ref_auths[1]}", last_names
    else:
        return ", ".join(ref_auths[:-1]) + f", & {ref_auths[-1]}", last_names

def build_in_text(last_names, year):
    if not last_names:
        return f"(Anonymous, {year})", f"Anonymous ({year})"
    if len(last_names) == 1:
        return f"({last_names[0]}, {year})", f"{last_names[0]} ({year})"
    elif len(last_names) == 2:
        return f"({last_names[0]} & {last_names[1]}, {year})", f"{last_names[0]} and {last_names[1]} ({year})"
    else:
        return f"({last_names[0]} et al., {year})", f"{last_names[0]} et al. ({year})"

def build_apa7(auth, year, title, jou, vol, iss, page, link):
    ref = f"{auth} ({year}). {title}. "
    if jou: ref += f"*{jou}*"
    if vol: ref += f", *{vol}*"
    if iss: ref += f"({iss})"
    if page: ref += f", {page}."
    else: ref += "."
    if link: ref += f" {link}"
    return ref.replace("..", ".")

def parse_doi(text):
    match = re.search(r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', text, re.IGNORECASE)
    return match.group(1) if match else None

def parse_pubmed_id(text):
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
            
            raw_auths = []
            for a in data.get('author', []):
                family = a.get('family', '')
                given = a.get('given', '')
                if family: raw_auths.append((family, given[0] if given else ""))
            
            auth_str, last_names = format_authors(raw_auths)
            paren, narr = build_in_text(last_names, year)
            ref = build_apa7(auth_str, year, title, journal, vol, issue, page, f"https://doi.org/{doi}")
            return ref, paren, narr, auth_str
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
            
            raw_auths = []
            for a in data.get('authors', []):
                name = a.get('name', '')
                parts = name.split(' ')
                if len(parts) >= 2: raw_auths.append((parts[0], parts[1][0]))
                elif name: raw_auths.append((name, ""))
            
            auth_str, last_names = format_authors(raw_auths)
            paren, narr = build_in_text(last_names, year)
            ref = build_apa7(auth_str, year, title, journal, vol, issue, page, link)
            return ref, paren, narr, auth_str
    except: return None

# --- 解決按鈕消失的 Callback 函數 ---
def add_fetch_to_box():
    # 修復 BUG：temp_fetch 是一個 Tuple (ref, paren, narr, auth_str)，所以用數字索引
    st.session_state.bib_list.append({
        "ref": st.session_state.temp_fetch[0], 
        "author": st.session_state.temp_fetch[3]
    })
    st.session_state.temp_fetch = None # 清除暫存畫面

def add_manual_to_box():
    # temp_manual 是一個 Dictionary，所以用字串索引
    st.session_state.bib_list.append({
        "ref": st.session_state.temp_manual['ref'], 
        "author": st.session_state.temp_manual['author']
    })
    st.session_state.temp_manual = None

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
                
                if doi_match:
                    st.session_state.temp_fetch = fetch_crossref(doi_match)
                elif pmid_match:
                    st.session_state.temp_fetch = fetch_pubmed(pmid_match)
                elif "airiti" in user_input.lower():
                    st.error("主角：靠北，華藝的防護牆太厚了... 請學長姐直接把資料貼到下方『完整版手動區塊』！")
                    st.session_state.temp_fetch = None
                else:
                    st.error("主角：這網址我看不太懂捏，試試看手動輸入吧！")
                    st.session_state.temp_fetch = None

    # 展示自動抓取的「三合一」結果
    if st.session_state.temp_fetch:
        ref, paren, narr, auth_for_sort = st.session_state.temp_fetch
        st.success("主角：搞定！幫您排好版了！")
        
        st.markdown("### ✨ 三合一結果展示")
        st.markdown("**📝 文末參考文獻 (Reference List)**")
        st.code(ref, language="markdown")
        st.markdown("**💬 括號式引用 (Parenthetical Citation)**")
        st.code(paren, language="markdown")
        st.markdown("**🗣️ 敘述式引用 (Narrative Citation)**")
        st.code(narr, language="markdown")
        
        # 使用 callback 避免畫面重整資料消失
        st.button("📥 加入我的文獻箱 (排序用)", on_click=add_fetch_to_box, type="primary")

    st.divider()
    
    st.title("✍️ 完整版手動輸入")
    st.markdown("<div class='mascot-dialog'><b>主角：</b>如果是死都不讓我抓的文章，就在這裡手動填吧！欄位我都準備好了！</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        m_auth = st.text_input("👥 作者群 (請用 '&' 或逗號分隔)", placeholder="例如: 王小明, & 李大華 或 Smith, J., & Doe, A.")
        m_year = st.text_input("📅 出版年份", placeholder="例如: 2026")
        m_title = st.text_area("📄 文章標題", placeholder="例如: 台灣護理師職場暴力之探討")
    with col2:
        m_jou = st.text_input("📖 期刊名稱", placeholder="例如: 護理雜誌")
        col2_1, col2_2, col2_3 = st.columns(3)
        with col2_1: m_vol = st.text_input("📚 卷號 (Volume)", placeholder="例如: 70")
        with col2_2: m_iss = st.text_input("🏷️ 期號 (Issue)", placeholder="例如: 2")
        with col2_3: m_page = st.text_input("📑 頁碼", placeholder="例如: 12-24")
        m_link = st.text_input("🔗 網址或 DOI (選填)", placeholder="例如: https://doi.org/10.xxxx")

    if st.button("✨ 手動組合三合一格式"):
        if m_auth and m_title:
            m_ref = build_apa7(m_auth, m_year, m_title, m_jou, m_vol, m_iss, m_page, m_link)
            # 簡易判定文中引用姓氏
            last_names = [n for n in re.split(r'[,&和]+', m_auth) if n.strip()]
            m_paren, m_narr = build_in_text(last_names, m_year)
            
            st.session_state.temp_manual = {"ref": m_ref, "paren": m_paren, "narr": m_narr, "author": m_auth}
        else:
            st.warning("主角：至少要填寫『作者』跟『標題』我才能排版啦！")

    # 展示手動輸入的「三合一」結果
    if st.session_state.temp_manual:
        st.markdown("### ✨ 手動三合一結果")
        st.markdown("**📝 文末參考文獻**")
        st.code(st.session_state.temp_manual['ref'], language="markdown")
        st.markdown("**💬 括號式引用**")
        st.code(st.session_state.temp_manual['paren'], language="markdown")
        st.markdown("**🗣️ 敘述式引用**")
        st.code(st.session_state.temp_manual['narr'], language="markdown")
        
        st.button("📥 將手動文獻加入文獻箱", on_click=add_manual_to_box, type="primary")

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

        st.markdown("### 📋 最終文末參考文獻 (請直接複製貼上 Word)")
        final_text = "\n\n".join([item['ref'] for item in sorted_list])
        st.code(final_text, language="markdown")
        
        if st.button("🗑️ 寫完了，清空文獻箱！"):
            st.session_state.bib_list = []
            st.rerun()
