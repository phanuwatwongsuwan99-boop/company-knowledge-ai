import streamlit as st
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import os
import glob
import time
import csv
import base64
import pandas as pd
from collections import Counter
from datetime import datetime, timezone, timedelta
import uuid

st.set_page_config(page_title="Oran AI | Corporate Assistant", page_icon="🟠", layout="wide")

# =========================================================
# 🎨 LOGO ASSET — embedded as base64 so it works anywhere
# =========================================================
LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")

@st.cache_data
def get_logo_b64():
    try:
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

LOGO_B64 = get_logo_b64()
LOGO_IMG = f"data:image/png;base64,{LOGO_B64}" if LOGO_B64 else ""

# =========================================================
# 🎨 DESIGN TOKENS + GLOBAL CSS (Dark mode, warm-orange accent)
# Consistent with the Login screen theme
# =========================================================
st.markdown(
    f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800&family=IBM+Plex+Sans+Thai:wght@300;400;500;600&display=swap');

        :root {{
            --bg: #0E0F12;
            --bg-soft: #14151A;
            --surface: #17181C;
            --surface-2: #1D1E24;
            --surface-hover: #24252C;
            --border: #2A2B30;
            --text: #F2F1ED;
            --text-dim: #9A9A9F;
            --text-faint: #6B6B70;
            --accent-yellow: #FFD748;
            --accent-orange: #FF9A3C;
            --accent-green: #1FBE6B;
            --radius-lg: 20px;
            --radius-md: 14px;
            --radius-sm: 10px;
        }}

        html, body, [class*="css"] {{
            font-family: 'IBM Plex Sans Thai', 'Outfit', sans-serif;
        }}

        .stApp {{
            background: var(--bg);
            color: var(--text);
        }}

        h1, h2, h3, h4 {{
            font-family: 'Outfit', 'IBM Plex Sans Thai', sans-serif !important;
            letter-spacing: -0.01em;
        }}

        /* Hide default Streamlit chrome (menu + footer only — keep header so the sidebar toggle still works) */
        #MainMenu, footer {{visibility: hidden;}}
        [data-testid="stHeader"] {{
            background: transparent;
        }}

        /* ---------- SIDEBAR (Claude-style: dark, collapsible) ---------- */
        [data-testid="stSidebar"] {{
            background: var(--bg-soft);
            border-right: 1px solid var(--border);
        }}
        [data-testid="stSidebarContent"]::-webkit-scrollbar {{ display: none; }}
        [data-testid="stSidebarContent"] {{
            scrollbar-width: none;
            height: 100vh;
            max-height: 100vh;
            overflow: hidden !important;
        }}
        /* Style Streamlit's native collapse control to match the dark theme */
        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="stBaseButton-headerNoPadding"] {{
            color: var(--text-dim) !important;
        }}
        [data-testid="collapsedControl"] {{
            background: var(--bg-soft);
        }}

        /* ---------- BRAND HEADER (sidebar, top-left) ---------- */
        .brand-row {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 4px 2px 18px 2px;
        }}
        .brand-row img {{
            width: 30px;
            height: 30px;
            object-fit: contain;
            border-radius: 8px;
        }}
        .brand-row .brand-name {{
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 16px;
            color: var(--text);
            letter-spacing: -0.01em;
        }}

        /* ---------- BUTTONS ---------- */
        .stButton > button {{
            background: var(--surface-2);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            font-weight: 500;
            transition: all 0.12s ease;
        }}
        .stButton > button:hover {{
            background: var(--surface-hover);
            color: var(--text);
            border-color: var(--accent-orange);
        }}
        /* Primary buttons (New chat) get the brand gradient */
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, var(--accent-yellow), var(--accent-orange));
            color: #1A1300;
            border: none;
            font-weight: 600;
            box-shadow: 0 4px 16px rgba(255, 154, 60, 0.2);
        }}
        .stButton > button[kind="primary"]:hover {{
            color: #1A1300;
            filter: brightness(1.08);
            box-shadow: 0 6px 22px rgba(255, 154, 60, 0.35);
        }}

        /* ---------- TEXT INPUTS ---------- */
        .stTextInput > div > div > input {{
            background: var(--surface-2);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
        }}
        .stTextInput > div > div > input:focus {{
            border-color: var(--accent-green);
            box-shadow: 0 0 0 1px var(--accent-green);
        }}

        /* ---------- CHAT AREA (ChatGPT-style centered column) ---------- */
        .block-container {{
            max-width: 820px;
            padding-top: 2.5rem;
        }}
        [data-testid="stChatMessage"] {{
            background: transparent;
            border: none;
            padding: 18px 0;
            border-bottom: 1px solid var(--border);
        }}
        [data-testid="stChatMessage"]:last-child {{
            border-bottom: none;
        }}
        [data-testid="stChatMessageAvatarUser"] {{
            background: var(--surface-2) !important;
        }}
        [data-testid="stChatMessageAvatarAssistant"] {{
            background: linear-gradient(135deg, var(--accent-yellow), var(--accent-orange)) !important;
        }}
        [data-testid="stChatInput"] {{
            background: transparent;
        }}
        [data-testid="stChatInput"] textarea {{
            background: var(--surface-2) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-lg) !important;
        }}
        [data-testid="stChatInput"] textarea::placeholder {{
            color: var(--text-faint) !important;
        }}

        /* ---------- METRICS / DATAFRAME (admin) ---------- */
        [data-testid="stMetric"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 14px 16px;
        }}

        /* =========================================================
           LOGIN SCREEN — signature element (unchanged from before)
           ========================================================= */
        .login-wrap {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 6vh;
        }}
        .login-orb-bloom {{
            position: relative;
            width: 132px;
            height: 132px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .login-orb-bloom::before {{
            content: "";
            position: absolute;
            width: 220px;
            height: 220px;
            background: radial-gradient(circle, rgba(255,154,60,0.35) 0%, rgba(255,154,60,0.0) 70%);
            border-radius: 50%;
            z-index: 0;
            animation: pulse-bloom 3.5s ease-in-out infinite;
        }}
        @keyframes pulse-bloom {{
            0%, 100% {{ opacity: 0.7; transform: scale(1); }}
            50% {{ opacity: 1; transform: scale(1.08); }}
        }}
        .login-orb-bloom img {{
            position: relative;
            z-index: 1;
            width: 112px;
            height: 112px;
            object-fit: contain;
            filter: drop-shadow(0 8px 24px rgba(255, 154, 60, 0.35));
        }}
        .login-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: var(--text);
            margin: 4px 0 2px 0;
            text-align: center;
        }}
        .login-subtitle {{
            color: var(--text-dim);
            font-size: 14px;
            margin-bottom: 28px;
            text-align: center;
        }}

        /* Admin badge accent */
        .admin-pill {{
            display: inline-block;
            background: linear-gradient(135deg, var(--accent-yellow), var(--accent-orange));
            color: #1A1300;
            font-weight: 600;
            font-size: 12px;
            padding: 3px 10px;
            border-radius: 999px;
        }}

        /* Empty-chat hero (shown before the first message) */
        .empty-hero {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding-top: 14vh;
            text-align: center;
        }}
        .empty-hero img {{
            width: 64px;
            height: 64px;
            object-fit: contain;
            margin-bottom: 14px;
            filter: drop-shadow(0 6px 18px rgba(255, 154, 60, 0.3));
        }}
        .empty-hero h2 {{
            font-size: 22px;
            margin: 0 0 4px 0;
        }}
        .empty-hero p {{
            color: var(--text-dim);
            font-size: 14px;
            margin: 0;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- ฟังก์ชันบันทึกประวัติการแชทลงไฟล์หลังบ้าน ---
def log_chat(chat_id, username, question, answer, status):
    tz_th = timezone(timedelta(hours=7))
    now = datetime.now(tz_th).strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.isfile("chat_logs.csv")

    with open("chat_logs.csv", "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Chat ID", "วัน-เวลา", "ชื่อพนักงาน", "คำถาม", "คำตอบจาก AI", "สถานะการตอบ"])
        writer.writerow([chat_id, now, username, question, answer, status])

# --- ฟังก์ชันออกจากระบบ (Logout) ---
def logout():
    st.session_state.clear()
    st.rerun()

# --- ระบบสร้างและสลับห้องแชท ---
def new_chat():
    st.session_state["current_chat_id"] = str(uuid.uuid4().hex[:8])
    st.session_state.messages = []

def switch_chat(selected_chat_id):
    st.session_state["current_chat_id"] = selected_chat_id
    st.session_state.messages = []

# --- ระบบ Login แบบจัดกึ่งกลาง ---
def check_password():
    def login_attempt():
        user = st.session_state.get("username_input", "")
        pw = st.session_state.get("password_input", "")

        if "passwords" in st.secrets and user in st.secrets["passwords"]:
            if str(st.secrets["passwords"][user]) == str(pw):
                st.session_state["password_correct"] = True
                st.session_state["current_user"] = user
                st.session_state["show_dino"] = True
                if "password_input" in st.session_state:
                    del st.session_state["password_input"]
                return
        st.session_state["password_correct"] = False

    def render_login_header():
        st.markdown(
            f"""
            <div class="login-wrap">
                <div class="login-orb-bloom">
                    <img src="{LOGO_IMG}" alt="Oran AI" />
                </div>
                <div class="login-title">Oran AI</div>
                <div class="login-subtitle">ผู้ช่วย AI สำหรับองค์กรของคุณ</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if "password_correct" not in st.session_state:
        st.markdown(
            """
            <style>
                [data-testid='stSidebar']{display:none;}
                [data-testid='stAppViewContainer'] > .main {margin-left:0;}
            </style>
            """,
            unsafe_allow_html=True
        )
        col1, col2, col3 = st.columns([1, 1.3, 1])
        with col2:
            render_login_header()
            st.text_input("ชื่อผู้ใช้งาน", key="username_input", placeholder="Username")
            st.text_input("รหัสผ่าน", type="password", key="password_input", placeholder="Password")
            st.write("")
            st.button("เข้าสู่ระบบ", on_click=login_attempt, use_container_width=True, type="primary")
        return False

    elif not st.session_state["password_correct"]:
        st.markdown(
            """
            <style>
                [data-testid='stSidebar']{display:none;}
                [data-testid='stAppViewContainer'] > .main {margin-left:0;}
            </style>
            """,
            unsafe_allow_html=True
        )
        col1, col2, col3 = st.columns([1, 1.3, 1])
        with col2:
            render_login_header()
            st.error("ชื่อผู้ใช้งาน หรือ รหัสผ่าน ไม่ถูกต้อง! กรุณาลองใหม่")
            st.text_input("ชื่อผู้ใช้งาน", key="username_input", placeholder="Username")
            st.text_input("รหัสผ่าน", type="password", key="password_input", placeholder="Password")
            st.write("")
            st.button("เข้าสู่ระบบ", on_click=login_attempt, use_container_width=True, type="primary")
        return False
    return True

if not check_password():
    st.stop()

# --- แอนิเมชันไดโนเสาร์ ---
if st.session_state.get("show_dino", False):
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown(
            f"""
            <div class="login-wrap" style="padding-top: 10vh;">
                <div class="login-orb-bloom">
                    <img src="{LOGO_IMG}" alt="Oran AI" />
                </div>
                <div class="login-title">กำลังเข้าสู่ระบบ</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        dino_text = st.empty()
        progress_bar = st.progress(0)
        for percent in range(1, 101):
            dino_text.markdown(
                f"<p style='text-align:center; color:#9A9A9F;'>🦖 กำลังเตรียมข้อมูล... {percent}%</p>",
                unsafe_allow_html=True
            )
            progress_bar.progress(percent)
            time.sleep(0.01)
        dino_text.empty()
        progress_bar.empty()
    st.session_state["show_dino"] = False

    if "current_chat_id" not in st.session_state:
        st.session_state["current_chat_id"] = str(uuid.uuid4().hex[:8])

    st.rerun()

ADMIN_USERS = ["boss", "admin"]

# =========================================================
# 👑 หน้าจอสำหรับผู้ดูแลระบบ (ADMIN PANEL)
# =========================================================
if st.session_state["current_user"] in ADMIN_USERS:
    with st.sidebar:
        st.markdown(
            f"""
            <div class="brand-row">
                <img src="{LOGO_IMG}" alt="Oran AI" />
                <div class="brand-name">Oran AI</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(f"<span class='admin-pill'>ผู้ดูแลระบบ · {st.session_state['current_user']}</span>", unsafe_allow_html=True)
        st.write("---")
        st.button("🚪 ออกจากระบบ", on_click=logout, use_container_width=True)

    st.title("📊 ระบบรายงานข้อมูลสำหรับผู้ดูแลระบบ (Admin Dashboard)")
    st.write("---")

    if os.path.exists("chat_logs.csv"):
        try:
            df = pd.read_csv("chat_logs.csv", on_bad_lines='skip')
        except:
            df = pd.DataFrame()

        if not df.empty:
            try:
                first_log_time_str = df.iloc[0]["วัน-เวลา"]
                first_log_time = datetime.strptime(first_log_time_str, "%Y-%m-%d %H:%M:%S")
                tz_th = timezone(timedelta(hours=7))
                current_time = datetime.now(tz_th).replace(tzinfo=None)
                file_age_days = (current_time - first_log_time).days

                if file_age_days >= 5:
                    st.warning(
                        f"⚠️ **แจ้งเตือนผู้ดูแลระบบ:** ไฟล์ประวัติถูกบันทึกมา **{file_age_days} วัน** แล้ว "
                        f"ระบบฟรีอาจเคลียร์ข้อมูลทิ้ง **กรุณาดาวน์โหลดสำรองข้อมูลทันที!**"
                    )
                    st.write("")
            except:
                pass

            with open("chat_logs.csv", "rb") as f:
                st.download_button(
                    label="📥 ดาวน์โหลดประวัติการแชททั้งหมด (CSV)",
                    data=f,
                    file_name=f"chat_logs_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

            if "สถานะการตอบ" in df.columns:
                total_questions = len(df)
                unanswered_questions = len(df[df["สถานะการตอบ"] == "ตอบไม่ได้"])
                answered_questions = total_questions - unanswered_questions
                col1, col2, col3 = st.columns(3)
                col1.metric("จำนวนการสอบถามทั้งหมด", f"{total_questions} ครั้ง")
                col2.metric("AI ตอบได้สำเร็จ", f"{answered_questions} ครั้ง")
                col3.metric("AI ไม่มีข้อมูลคำตอบ", f"{unanswered_questions} ครั้ง", delta_color="inverse")
                st.write("---")

            def get_top_keywords(text_series, top_n=5):
                words = []
                stop_words = ["คะ", "ครับ", "อะไร", "ไหม", "มี", "ที่", "ได้", "การ", "ใน", "ของ", "อยาก", "สอบถาม", "ขอ"]
                for text in text_series.dropna():
                    for word in str(text).split():
                        if len(word) > 2 and word not in stop_words:
                            words.append(word)
                return Counter(words).most_common(top_n)

            if "คำถาม" in df.columns:
                st.subheader("🔥 5 อันดับหัวข้อ/คำถาม ที่พนักงานถามบ่อยที่สุด")
                top_keywords = get_top_keywords(df["คำถาม"])
                if top_keywords:
                    for rank, (word, count) in enumerate(top_keywords, 1):
                        st.write(f"**อันดับ {rank}:** หัวข้อเกี่ยวกับ **'{word}'** (ถาม {count} ครั้ง)")
                else:
                    st.info("ระบบยังเก็บสถิติตัวแปรคำถามไม่เพียงพอ")
                st.write("---")

            if "สถานะการตอบ" in df.columns and "คำถาม" in df.columns:
                st.subheader("⚠️ 5 อันดับหัวข้อที่พนักงานสงสัย แต่ 'ยังไม่มีคำตอบ'")
                unanswered_df = df[df["สถานะการตอบ"] == "ตอบไม่ได้"]
                top_unanswered_keywords = get_top_keywords(unanswered_df["คำถาม"])

                if top_unanswered_keywords:
                    st.error("คำเตือน: หัวข้อเหล่านี้ถูกถามบ่อยแต่ AI ตอบไม่ได้ กรุณาอัปเดตไฟล์ข้อมูลเพิ่มเติม")
                    for rank, (word, count) in enumerate(top_unanswered_keywords, 1):
                        st.write(f"❌ **อันดับ {rank}:** เรื่อง **'{word}'** (พยายามถามแต่ไม่มีคำตอบ {count} ครั้ง)")
                else:
                    st.success("ยอดเยี่ยมมาก! ปัจจุบันยังไม่มีคำถามที่เอกสารตอบไม่ได้ถูกถามซ้ำ")
                st.write("---")

            st.subheader("📋 ตารางประวัติการใช้งานล่าสุด 20 รายการ")
            st.dataframe(df.tail(20), use_container_width=True)
    else:
        st.info("ขณะนี้ยังไม่มีพนักงานเข้ามาใช้งานระบบ จึงยังไม่มีข้อมูลสถิติรายงานสำหรับคุณ")
    st.stop()

# =========================================================
# 💬 หน้าจอสำหรับพนักงานทั่วไป (CHAT INTERFACE)
# =========================================================
st.set_option('client.showSidebarNavigation', False)

my_history_df = pd.DataFrame()
if os.path.exists("chat_logs.csv"):
    try:
        df_history = pd.read_csv("chat_logs.csv", on_bad_lines='skip')
        if "ชื่อพนักงาน" in df_history.columns and "Chat ID" in df_history.columns:
            my_history_df = df_history[df_history["ชื่อพนักงาน"] == st.session_state["current_user"]]
    except:
        pass

# 📌 แถบเมนูด้านซ้ายสำหรับพนักงาน (โลโก้มุมบนซ้าย + ปุ่มย่อ/ขยายของ Streamlit เอง)
with st.sidebar:
    st.markdown(
        f"""
        <div class="brand-row">
            <img src="{LOGO_IMG}" alt="Oran AI" />
            <div class="brand-name">Oran AI</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.caption(f"👤 {st.session_state['current_user']}")
    st.button("➕ New chat", on_click=new_chat, use_container_width=True, type="primary")
    st.write("---")

    st.write("**History**")

    if not my_history_df.empty:
        chat_groups = my_history_df.groupby("Chat ID", sort=False)
        for chat_id, group in reversed(list(chat_groups)):
            first_question = str(group.iloc[0]["คำถาม"])
            short_name = first_question[:25] + "..." if len(first_question) > 25 else first_question

            is_active = (chat_id == st.session_state.get("current_chat_id"))
            btn_label = f"💬 {short_name}" if not is_active else f"📍 {short_name}"

            st.button(btn_label, key=f"btn_{chat_id}", on_click=switch_chat, args=(chat_id,), use_container_width=True)
    else:
        st.caption("ยังไม่มีประวัติการแชท")

    st.button("🚪 Logout", on_click=logout, use_container_width=True)

@st.cache_resource(show_spinner="กำลังเตรียมความพร้อม AI...")
def setup_knowledge_base():
    docs = []
    def load_document(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == '.pdf':
                return PyPDFLoader(file_path).load()
            elif ext == '.txt':
                return TextLoader(file_path, encoding='utf-8').load()
            elif ext == '.csv':
                return CSVLoader(file_path, encoding='utf-8-sig').load()
            elif ext == '.docx':
                return Docx2txtLoader(file_path).load()
            elif ext == '.xlsx':
                df = pd.read_excel(file_path)
                temp_csv = f"temp_{os.path.basename(file_path)}.csv"
                df.to_csv(temp_csv, index=False, encoding='utf-8-sig')
                data = CSVLoader(temp_csv, encoding='utf-8-sig').load()
                os.remove(temp_csv)
                return data
            else:
                return []
        except Exception as e:
            st.warning(f"ไม่สามารถอ่านไฟล์ {file_path} ได้: {str(e)}")
            return []

    supported_extensions = ['*.pdf', '*.txt', '*.csv', '*.docx', '*.xlsx']
    all_files = []
    for ext in supported_extensions:
        all_files.extend(glob.glob(ext))

    if not all_files:
        st.error("ไม่พบไฟล์เอกสารใด ๆ (PDF, TXT, CSV, DOCX, XLSX) ในระบบ")
        st.stop()

    for file_path in all_files:
        docs.extend(load_document(file_path))

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    vectorstore = FAISS.from_documents(splits, embeddings)
    return vectorstore

vectorstore = setup_knowledge_base()
retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

llm = ChatGroq(model_name="llama-3.1-8b-instant", api_key=st.secrets["GROQ_API_KEY"], temperature=0.1)

NOT_FOUND_MSG = "ไม่พบข้อมูลในเอกสารขององค์กร"

system_prompt = (
    "คุณคือผู้ช่วย AI อัจฉริยะขององค์กร จงใช้ข้อมูลจาก Context ด้านล่างเพื่อตอบคำถาม\n\n"
    "คำแนะนำเพิ่มเติมเพื่อให้คุณฉลาดขึ้น:\n"
    "1. หากผู้ใช้พิมพ์คำถามมาสั้นๆ หรือพิมพ์แค่คีย์เวิร์ด (เช่น 'วันลากิจ', 'เบิกเงิน') ให้คุณตีความว่าผู้ใช้อยากรู้รายละเอียดทั้งหมดเกี่ยวกับเรื่องนั้น และช่วยสรุปข้อมูลทั้งหมดที่คุณเจอใน Context มาอธิบายให้ครบถ้วนในรูปแบบที่อ่านง่าย\n"
    "2. พยายามตอบให้ตรงประเด็น เป็นมิตร และใช้การจัดหน้า (เช่น Bullet points) ถ้าข้อมูลมีหลายข้อ\n"
    f"3. ถ้าข้อมูลใน Context ไม่มีเรื่องที่ถามเลยจริงๆ ให้ตอบคำว่า '{NOT_FOUND_MSG}' เท่านั้น ห้ามเดาเอาเองเด็ดขาด\n\n"
    "Context:\n{context}"
)
prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "input": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

if "messages" not in st.session_state or not st.session_state.messages:
    st.session_state.messages = []

    if not my_history_df.empty and "current_chat_id" in st.session_state:
        current_chat_history = my_history_df[my_history_df["Chat ID"] == st.session_state["current_chat_id"]]

        for index, row in current_chat_history.iterrows():
            st.session_state.messages.append({"role": "user", "content": str(row["คำถาม"])})
            st.session_state.messages.append({"role": "assistant", "content": str(row["คำตอบจาก AI"])})

# หน้าจอเปล่าก่อนเริ่มแชท (เหมือน ChatGPT/Claude ตอนเปิดแชทใหม่)
if not st.session_state.messages:
    st.markdown(
        f"""
        <div class="empty-hero">
            <img src="{LOGO_IMG}" alt="Oran AI" />
            <h2>มีอะไรให้ช่วยไหม</h2>
            <p>พิมพ์คำถามเกี่ยวกับองค์กรของคุณด้านล่างนี้ได้เลย</p>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if user_input := st.chat_input("พิมพ์คำถามเกี่ยวกับองค์กร... (พิมพ์คำสั้นๆ ก็ได้นะ)"):
    if "current_chat_id" not in st.session_state:
        st.session_state["current_chat_id"] = str(uuid.uuid4().hex[:8])

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("AI กำลังวิเคราะห์และสรุปข้อมูลให้คุณ..."):
            response = rag_chain.invoke(user_input)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

            status = "ตอบได้"
            if NOT_FOUND_MSG in response:
                status = "ตอบไม่ได้"

            log_chat(st.session_state["current_chat_id"], st.session_state["current_user"], user_input, response, status)

            st.rerun()
