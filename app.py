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
import glob
import time
import csv
import pandas as pd  # 👈 เพิ่ม pandas เพื่อใช้คำนวณและทำ Report
from collections import Counter
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="Corporate AI System", page_icon="🤖", layout="wide")

# --- ฟังก์ชันบันทึกประวัติการแชทลงไฟล์หลังบ้าน ---
def log_chat(username, question, answer, status):
    tz_th = timezone(timedelta(hours=7))
    now = datetime.now(tz_th).strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.isfile("chat_logs.csv")
    
    with open("chat_logs.csv", "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            # เพิ่มคอลัมน์ สถานะ เพื่อระบุว่า AI ตอบได้หรือตอบไม่ได้
            writer.writerow(["วัน-เวลา", "ชื่อพนักงาน", "คำถาม", "คำตอบจาก AI", "สถานะการตอบ"])
        writer.writerow([now, username, question, answer, status])

# --- ระบบ Login ---
def check_password():
    def login_attempt():
        user = st.session_state["username_input"]
        pw = st.session_state["password_input"]
        
        if "passwords" in st.secrets and user in st.secrets["passwords"]:
            if str(st.secrets["passwords"][user]) == str(pw):
                st.session_state["password_correct"] = True
                st.session_state["current_user"] = user 
                st.session_state["show_dino"] = True 
                del st.session_state["password_input"] 
                return
        st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 เข้าสู่ระบบ AI องค์กร")
        st.text_input("ชื่อผู้ใช้งาน (Username)", key="username_input")
        st.text_input("รหัสผ่าน (Password)", type="password", key="password_input")
        st.button("เข้าสู่ระบบ", on_click=login_attempt)
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 เข้าสู่ระบบ AI องค์กร")
        st.text_input("ชื่อผู้ใช้งาน (Username)", key="username_input")
        st.error("ชื่อผู้ใช้งาน หรือ รหัสผ่าน ไม่ถูกต้อง! กรุณาลองใหม่")
        st.text_input("รหัสผ่าน (Password)", type="password", key="password_input")
        st.button("เข้าสู่ระบบ", on_click=login_attempt)
        return False
    return True

if not check_password():
    st.stop()

# --- แอนิเมชันไดโนเสาร์ ---
if st.session_state.get("show_dino", False):
    st.title("🤖 กำลังเข้าสู่ระบบ...")
    dino_text = st.empty()
    progress_bar = st.progress(0)
    for percent in range(1, 101):
        spaces = "&nbsp;" * percent 
        dino_text.markdown(f"{spaces}🦖 **กำลังเตรียมข้อมูล... {percent}%**")
        progress_bar.progress(percent)
        time.sleep(0.01)
    dino_text.empty()
    progress_bar.empty()
    st.session_state["show_dino"] = False
    st.rerun()

# กองอำนวยการกำหนดสิทธิ์ Admin
ADMIN_USERS = ["boss", "admin"] 

# =========================================================
# 👑 หน้าจอสำหรับผู้ดูแลระบบ (ADMIN PANEL เท่านั้น - ไม่มีช่องแชท)
# =========================================================
if st.session_state["current_user"] in ADMIN_USERS:
    st.title("📊 ระบบรายงานข้อมูลสำหรับผู้ดูแลระบบ (Admin Dashboard)")
    st.caption(f"ยินดีต้อนรับผู้ดูแลระบบ: {st.session_state['current_user']}")
    st.write("---")

    # ส่วนดาวน์โหลดข้อมูล
    if os.path.exists("chat_logs.csv"):
        with open("chat_logs.csv", "rb") as f:
            st.download_button(
                label="📥 ดาวน์โหลดประวัติการแชททั้งหมด (CSV)",
                data=f,
                file_name=f"chat_logs_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        # --- ประมวลผลทำข้อมูลรายงาน (Report Analytics) ---
        df = pd.read_csv("chat_logs.csv")
        
        # สรุปตัวเลขเบื้องต้น (KPI Cards)
        total_questions = len(df)
        unanswered_questions = len(df[df["สถานะการตอบ"] == "ตอบไม่ได้"])
        answered_questions = total_questions - unanswered_questions
        
        col1, col2, col3 = st.columns(3)
        col1.metric("จำนวนการสอบถามทั้งหมด", f"{total_questions} ครั้ง")
        col2.metric("AI ตอบได้สำเร็จ", f"{answered_questions} ครั้ง")
        col3.metric("AI ไม่มีข้อมูลคำตอบ", f"{unanswered_questions} ครั้ง", delta_color="inverse")
        
        st.write("---")
        
        # ฟังก์ชันจัดกลุ่มคำถามแบบง่าย (Keyword Extraction)
        def get_top_keywords(text_series, top_n=5):
            words = []
            # คำที่เราต้องการคัดออกเพราะถามบ่อยแต่ไม่ใช่สาระสำคัญ
            stop_words = ["คะ", "ครับ", "อะไร", "ไหม", "มี", "ที่", "ได้", "การ", "ใน", "ของ", "อยาก", "สอบถาม"]
            for text in text_series.dropna():
                for word in str(text).split():
                    if len(word) > 2 and word not in stop_words:
                        words.append(word)
            return Counter(words).most_common(top_n)

        # 1. รายงานหัวข้อคำถามที่พนักงานถามบ่อยที่สุด
        st.subheader("🔥 5 อันดับหัวข้อ/คำถาม ที่พนักงานถามบ่อยที่สุด")
        top_keywords = get_top_keywords(df["คำถาม"])
        if top_keywords:
            for rank, (word, count) in enumerate(top_keywords, 1):
                st.write(f"**อันดับ {rank}:** หัวข้อเกี่ยวกับเกี่ยวกับ **'{word}'** (มีการถามถึง {count} ครั้ง)")
        else:
            st.info("ระบบยังเก็บสถิติตัวแปรคำถามไม่เพียงพอ")

        st.write("---")

        # 2. รายงานคำถามที่ AI ตอบไม่ได้ แต่ดันโดนถามบ่อย (ต้องเอาข้อมูลมาเพิ่มใน PDF)
        st.subheader("⚠️ 5 อันดับหัวข้อที่พนักงานสงสัย แต่ในเอกสารองค์กร 'ยังไม่มีคำตอบ'")
        unanswered_df = df[df["สถานะการตอบ"] == "ตอบไม่ได้"]
        top_unanswered_keywords = get_top_keywords(unanswered_df["คำถาม"])
        
        if top_unanswered_keywords:
            st.error("คำเตือน: หัวข้อเหล่านี้ถูกถามบ่อยแต่ AI ตอบไม่ได้ กรุณาอัปเดตไฟล์ PDF เพิ่มเติม")
            for rank, (word, count) in enumerate(top_unanswered_keywords, 1):
                st.write(f"❌ **อันดับ {rank}:** เรื่อง **'{word}'** (พนักงานพยายามถามแต่ไม่มีคำตอบ {count} ครั้ง)")
        else:
            st.success("ยอดเยี่ยมมาก! ปัจจุบันยังไม่มีคำถามที่เอกสารตอบไม่ได้ถูกถามซ้ำ")

        st.write("---")
        # แสดงตารางประวัติล่าสุดประกอบหน้าเว็บ Admin
        st.subheader("📋 ตารางประวัติการใช้งานล่าสุด 20 รายการ")
        st.dataframe(df.tail(20), use_container_width=True)

    else:
        st.info("ขณะนี้ยังไม่มีพนักงานเข้ามาใช้งานระบบ จึงยังไม่มีข้อมูลสถิติรายงานสำหรับคุณ")
    
    st.stop() # หยุดการทำงานตรงนี้ เพื่อไม่ให้ Admin เห็นหน้าจอแชทด้านล่าง

# =========================================================
# 💬 หน้าจอสำหรับพนักงานทั่วไป (CHAT INTERFACE เท่านั้น - ไม่มีเมนูและรายงาน)
# =========================================================
st.set_option('client.showSidebarNavigation', False) # ซ่อนแถบเมนูด้านซ้ายอย่างสิ้นเชิง
st.title("🤖 ผู้ช่วย AI สำหรับองค์กร")
st.caption(f"👤 บัญชีผู้ใช้พนักงาน: {st.session_state['current_user']}")

@st.cache_resource(show_spinner="กำลังเตรียมความพร้อม AI...")
def setup_knowledge_base():
    docs = []
    pdf_files = glob.glob("*.pdf")
    if not pdf_files:
        st.error("ไม่พบไฟล์เอกสาร PDF ใด ๆ ในระบบ")
        st.stop()
        
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

# ข้อความบังคับตอบไม่ได้ ถ้าไม่เจอในเอกสาร
NOT_FOUND_MSG = "ไม่พบข้อมูลในเอกสารขององค์กร"

system_prompt = (
    "คุณคือผู้ช่วย AI ขององค์กร จงตอบคำถามโดยใช้ข้อมูลจาก Context ด้านล่างนี้เท่านั้น\n"
    f"ถ้าไม่มีข้อมูลให้ตอบคำว่า '{NOT_FOUND_MSG}' เท่านั้น ห้ามเดาเอาเองเด็ดขาด\n\n"
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

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("พิมพ์คำถามเกี่ยวกับองค์กร..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("AI กำลังคิด..."):
            response = rag_chain.invoke(user_input)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # ตรวจสอบว่ารอบนี้ AI ตอบได้ หรือตอบไม่ได้
            status = "ตอบได้"
            if NOT_FOUND_MSG in response:
                status = "ตอบไม่ได้"
                
            # บันทึกประวัติลงไฟล์หลังบ้าน
            log_chat(st.session_state["current_user"], user_input, response, status)
