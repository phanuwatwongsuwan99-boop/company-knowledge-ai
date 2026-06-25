import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import os
import glob # เพิ่มเครื่องมือค้นหาไฟล์
import time

st.set_page_config(page_title="Corporate AI Assistant", page_icon="🤖", layout="wide")

# =========================================================
# 🎨 THEME / DESIGN SYSTEM
# (ส่วนนี้เป็น UI/UX ทั้งหมด ไม่แตะ logic ของ RAG เดิมเลย)
# =========================================================

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def get_tokens(theme: str) -> dict:
    if theme == "dark":
        return {
            "bg": "#0E0F13",
            "panel": "#171922",
            "panel_alt": "#1E2029",
            "border": "#2A2D3A",
            "text": "#EDEEF2",
            "text_muted": "#9A9DAE",
            "accent": "#6E8BFF",
            "accent_soft": "rgba(110, 139, 255, 0.14)",
            "accent_text": "#FFFFFF",
            "user_bubble": "#262A3B",
            "bot_bubble": "#171922",
            "shadow": "0 8px 24px rgba(0,0,0,0.35)",
            "danger": "#FF6B6B",
        }
    return {
        "bg": "#FAFAF8",
        "panel": "#FFFFFF",
        "panel_alt": "#F2F2F0",
        "border": "#E6E6E2",
        "text": "#1B1C22",
        "text_muted": "#6B6E7E",
        "accent": "#4A63E0",
        "accent_soft": "rgba(74, 99, 224, 0.10)",
        "accent_text": "#FFFFFF",
        "user_bubble": "#EEF0FF",
        "bot_bubble": "#FFFFFF",
        "shadow": "0 8px 24px rgba(20,20,30,0.08)",
        "danger": "#D14343",
    }

T = get_tokens(st.session_state.theme)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;600;700&family=Inter:wght@500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Sarabun', 'Inter', sans-serif;
}}

.stApp {{
    background: {T['bg']};
    color: {T['text']};
}}

/* ซ่อน chrome เริ่มต้นของ Streamlit ที่ไม่จำเป็น */
#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ background: transparent; }}

/* ===== Sidebar ===== */
section[data-testid="stSidebar"] {{
    background: {T['panel']};
    border-right: 1px solid {T['border']};
}}
section[data-testid="stSidebar"] * {{
    color: {T['text']};
}}

.sidebar-brand {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 18px 0;
    border-bottom: 1px solid {T['border']};
    margin-bottom: 16px;
}}
.sidebar-brand .logo {{
    width: 38px; height: 38px;
    border-radius: 11px;
    background: linear-gradient(135deg, {T['accent']}, #9AA9FF);
    display: flex; align-items: center; justify-content: center;
    font-size: 19px;
    box-shadow: {T['shadow']};
}}
.sidebar-brand .title {{
    font-weight: 700;
    font-size: 16px;
    line-height: 1.2;
}}
.sidebar-brand .subtitle {{
    font-size: 12px;
    color: {T['text_muted']};
}}

.sidebar-section-label {{
    font-size: 11px;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: {T['text_muted']};
    font-weight: 600;
    margin: 18px 0 8px 2px;
}}

.history-item {{
    background: {T['panel_alt']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: 9px 12px;
    margin-bottom: 6px;
    font-size: 13px;
    color: {T['text']};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    cursor: default;
}}

.empty-history {{
    font-size: 12.5px;
    color: {T['text_muted']};
    padding: 10px 2px;
    line-height: 1.5;
}}

/* ===== Chat header ===== */
.chat-header {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 4px 18px 4px;
    border-bottom: 1px solid {T['border']};
    margin-bottom: 18px;
}}
.chat-header .avatar {{
    width: 44px; height: 44px;
    border-radius: 13px;
    background: linear-gradient(135deg, {T['accent']}, #9AA9FF);
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
    flex-shrink: 0;
}}
.chat-header .h-title {{
    font-weight: 700;
    font-size: 18px;
    margin: 0;
}}
.chat-header .h-status {{
    font-size: 12.5px;
    color: #3DD68C;
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 2px 0 0 0;
}}
.dot-online {{
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #3DD68C;
    box-shadow: 0 0 0 0 rgba(61,214,140,0.5);
    animation: pulse-online 2s infinite;
}}
@keyframes pulse-online {{
    0% {{ box-shadow: 0 0 0 0 rgba(61,214,140,0.45); }}
    70% {{ box-shadow: 0 0 0 6px rgba(61,214,140,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(61,214,140,0); }}
}}

/* ===== Chat bubbles ===== */
div[data-testid="stChatMessage"] {{
    background: transparent;
    padding: 4px 0;
}}

div[data-testid="stChatMessageContent"] {{
    border-radius: 16px;
    padding: 12px 16px;
    box-shadow: {T['shadow']};
    font-size: 14.5px;
    line-height: 1.6;
}}

div[data-testid="stChatMessage"][data-testid*="user"] {{
    flex-direction: row-reverse;
}}

/* user bubble */
.stChatMessage:has(div[data-testid="stChatMessageAvatarUser"]) div[data-testid="stChatMessageContent"] {{
    background: {T['user_bubble']};
    border: 1px solid {T['border']};
}}

/* assistant bubble */
.stChatMessage:has(div[data-testid="stChatMessageAvatarAssistant"]) div[data-testid="stChatMessageContent"] {{
    background: {T['bot_bubble']};
    border: 1px solid {T['border']};
}}

/* ===== Typing indicator (กำลังคิดอยู่) ===== */
.thinking-row {{
    display: flex;
    align-items: center;
    gap: 10px;
    background: {T['bot_bubble']};
    border: 1px solid {T['border']};
    border-radius: 16px;
    padding: 13px 18px;
    width: fit-content;
    box-shadow: {T['shadow']};
}}
.thinking-label {{
    font-size: 13px;
    color: {T['text_muted']};
}}
.typing-dots {{
    display: flex;
    gap: 4px;
}}
.typing-dots span {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: {T['accent']};
    animation: bounce-dot 1.2s infinite ease-in-out;
}}
.typing-dots span:nth-child(2) {{ animation-delay: 0.15s; }}
.typing-dots span:nth-child(3) {{ animation-delay: 0.3s; }}
@keyframes bounce-dot {{
    0%, 80%, 100% {{ transform: translateY(0); opacity: 0.5; }}
    40% {{ transform: translateY(-5px); opacity: 1; }}
}}

/* ===== Chat input ===== */
div[data-testid="stChatInput"] textarea {{
    background: {T['panel']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 14px !important;
    color: {T['text']} !important;
}}
div[data-testid="stChatInput"] {{
    background: transparent !important;
}}

/* ===== Buttons ===== */
.stButton button {{
    border-radius: 10px !important;
    border: 1px solid {T['border']} !important;
    background: {T['panel_alt']} !important;
    color: {T['text']} !important;
    font-weight: 500 !important;
    transition: all .15s ease;
}}
.stButton button:hover {{
    border-color: {T['accent']} !important;
    color: {T['accent']} !important;
}}

/* ===== Login screen ===== */
.login-wrap {{
    max-width: 380px;
    margin: 10vh auto 0 auto;
    text-align: center;
}}
.login-card {{
    background: {T['panel']};
    border: 1px solid {T['border']};
    border-radius: 18px;
    padding: 34px 30px;
    box-shadow: {T['shadow']};
}}
.login-icon {{
    width: 56px; height: 56px;
    border-radius: 16px;
    background: linear-gradient(135deg, {T['accent']}, #9AA9FF);
    display: flex; align-items: center; justify-content: center;
    font-size: 26px;
    margin: 0 auto 16px auto;
}}
.login-title {{
    font-weight: 700;
    font-size: 19px;
    margin-bottom: 4px;
}}
.login-subtitle {{
    font-size: 13px;
    color: {T['text_muted']};
    margin-bottom: 20px;
}}

::placeholder {{ color: {T['text_muted']} !important; opacity: .8; }}
</style>
""", unsafe_allow_html=True)


# =========================================================
# 🔐 AUTH (logic เดิมทั้งหมด ปรับแค่หน้าตา)
# =========================================================

def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
        st.markdown("""
            <div class="login-card">
                <div class="login-icon">🤖</div>
                <div class="login-title">เข้าสู่ระบบ AI องค์กร</div>
                <div class="login-subtitle">กรอกรหัสผ่านเพื่อเข้าใช้งานผู้ช่วย AI</div>
            </div>
        """, unsafe_allow_html=True)
        st.text_input("รหัสผ่าน", type="password", on_change=password_entered, key="password", label_visibility="collapsed", placeholder="กรุณาใส่รหัสผ่าน")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    elif not st.session_state["password_correct"]:
        st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
        st.markdown("""
            <div class="login-card">
                <div class="login-icon">🔒</div>
                <div class="login-title">รหัสผ่านไม่ถูกต้อง</div>
                <div class="login-subtitle">กรุณาลองใหม่อีกครั้ง</div>
            </div>
        """, unsafe_allow_html=True)
        st.text_input("รหัสผ่าน", type="password", on_change=password_entered, key="password", label_visibility="collapsed", placeholder="กรุณาใส่รหัสผ่าน")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

if not check_password():
    st.stop()


# =========================================================
# 📚 SIDEBAR — ประวัติแชท + ตั้งค่าธีม (UI เพิ่มเติม)
# =========================================================

with st.sidebar:
    st.markdown(f"""
        <div class="sidebar-brand">
            <div class="logo">🤖</div>
            <div>
                <div class="title">Corporate AI</div>
                <div class="subtitle">ผู้ช่วย AI สำหรับองค์กร</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-label">ลักษณะหน้าจอ</div>', unsafe_allow_html=True)
    is_dark = st.toggle("โหมดมืด (Dark mode)", value=(st.session_state.theme == "dark"))
    new_theme = "dark" if is_dark else "light"
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    st.markdown('<div class="sidebar-section-label">ประวัติคำถาม</div>', unsafe_allow_html=True)

    if "messages" in st.session_state and st.session_state.messages:
        user_questions = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
        if user_questions:
            for q in reversed(user_questions[-15:]):
                label = q if len(q) <= 42 else q[:42] + "…"
                st.markdown(f'<div class="history-item">💬 {label}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty-history">ยังไม่มีประวัติคำถาม<br>เริ่มพิมพ์คำถามได้ที่ช่องแชทเลย</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-history">ยังไม่มีประวัติคำถาม<br>เริ่มพิมพ์คำถามได้ที่ช่องแชทเลย</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ ล้างประวัติการสนทนา", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# =========================================================
# 🧠 RAG SETUP (logic เดิมทั้งหมด ไม่แก้ไขแม้แต่บรรทัดเดียว)
# =========================================================

@st.cache_resource(show_spinner="กำลังเรียนรู้ข้อมูลองค์กรทั้งหมด...")
def setup_knowledge_base():
    docs = []
    # ค้นหาไฟล์ทั้งหมดที่ลงท้ายด้วย .pdf ในโฟลเดอร์นี้
    pdf_files = glob.glob("*.pdf")

    if not pdf_files:
        st.error("ไม่พบไฟล์เอกสาร PDF ใด ๆ ในระบบ กรุณาอัปโหลดไฟล์ขึ้น GitHub")
        st.stop()

    # ลูปอ่านข้อมูลจากทุกไฟล์ PDF ที่เจอ
    for file_path in pdf_files:
        loader = PyPDFLoader(file_path)
        docs.extend(loader.load())

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    vectorstore = FAISS.from_documents(splits, embeddings)
    return vectorstore

vectorstore = setup_knowledge_base()
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

llm = ChatGroq(model_name="llama-3.1-8b-instant", api_key=st.secrets["GROQ_API_KEY"], temperature=0.1)

system_prompt = (
    "คุณคือผู้ช่วย AI ขององค์กร จงตอบคำถามโดยใช้ข้อมูลจาก Context ด้านล่างนี้เท่านั้น "
    "ถ้าไม่มีข้อมูลให้ตอบว่า 'ไม่พบข้อมูลในเอกสารขององค์กร' ห้ามเดาเอาเอง\n\n"
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


# =========================================================
# 💬 CHAT UI
# =========================================================

st.markdown(f"""
    <div class="chat-header">
        <div class="avatar">🤖</div>
        <div>
            <p class="h-title">ผู้ช่วย AI สำหรับองค์กร</p>
            <p class="h-status"><span class="dot-online"></span>พร้อมตอบคำถามจากเอกสารองค์กร</p>
        </div>
    </div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.markdown(f"""
        <div style="text-align:center; padding: 40px 20px; color:{T['text_muted']};">
            <div style="font-size:34px; margin-bottom:8px;">💡</div>
            <div style="font-size:14.5px;">ลองถามคำถามเกี่ยวกับเอกสารขององค์กรได้เลย เช่น<br>
            <span style="color:{T['accent']};">"นโยบายการลาพักร้อนเป็นอย่างไร"</span></div>
        </div>
    """, unsafe_allow_html=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("พิมพ์คำถาม..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        thinking_placeholder = st.empty()
        thinking_placeholder.markdown(f"""
            <div class="thinking-row">
                <div class="typing-dots"><span></span><span></span><span></span></div>
                <div class="thinking-label">AI กำลังคิด...</div>
            </div>
        """, unsafe_allow_html=True)

        response = rag_chain.invoke(user_input)

        thinking_placeholder.empty()
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
