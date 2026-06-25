import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
import os

# --- 1. ระบบ Login หน้าบ้าน ---
st.set_page_config(page_title="Corporate AI Assistant", page_icon="🤖")

def check_password():
    """ระบบตรวจสอบรหัสผ่านแบบง่าย"""
    def password_entered():
        if st.session_state["password"] == st.secrets.get("APP_PASSWORD", "1234"):
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 เข้าสู่ระบบ AI องค์กร")
        st.text_input("กรุณาใส่รหัสผ่าน", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 เข้าสู่ระบบ AI องค์กร")
        st.text_input("รหัสผ่านผิด! กรุณาลองใหม่", type="password", on_change=password_entered, key="password")
        st.error("รหัสผ่านไม่ถูกต้อง")
        return False
    return True

if not check_password():
    st.stop() # หยุดการทำงานถ้ารหัสผิด

# --- 2. ระบบหลังบ้าน (RAG & Knowledge Base) ---
st.title("🤖 ผู้ช่วย AI สำหรับองค์กร")
st.caption("ถาม-ตอบ จากข้อมูลในไฟล์ knowledge.pdf เท่านั้น")

@st.cache_resource(show_spinner="กำลังเรียนรู้ข้อมูลองค์กร...")
def setup_knowledge_base():
    # 1. โหลดไฟล์ PDF
    loader = PyPDFLoader("knowledge.pdf")
    docs = loader.load()
    
    # 2. หั่นข้อความเป็นส่วนๆ
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    splits = text_splitter.split_documents(docs)
    
    # 3. สร้าง Embeddings ด้วยโมเดลฟรีที่รองรับภาษาไทย
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    # 4. เก็บลง Vector Database (FAISS)
    vectorstore = FAISS.from_documents(splits, embeddings)
    return vectorstore

# ดึงข้อมูลจากฐานข้อมูล
vectorstore = setup_knowledge_base()
retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) # ค้นหา 3 ส่วนที่เกี่ยวข้องที่สุด

# ตั้งค่า AI (LLM) ด้วย Groq Llama 3.1 (ฟรีและเร็วมาก)
llm = ChatGroq(
    model_name="llama-3.1-8b-instant",
    api_key=st.secrets["GROQ_API_KEY"],
    temperature=0.1
)

# สั่งสอน AI ให้ตอบเฉพาะเนื้อหาในไฟล์
system_prompt = (
    "คุณคือผู้ช่วย AI ขององค์กร จงตอบคำถามโดยใช้ข้อมูลจาก Context ด้านล่างนี้เท่านั้น "
    "ถ้าใน Context ไม่มีข้อมูลที่สามารถตอบคำถามได้ ให้ตอบอย่างสุภาพว่า 'ไม่พบข้อมูลในเอกสารขององค์กร' "
    "ไม่ต้องพยายามเดาหรือหาคำตอบจากแหล่งอื่น\n\n"
    "Context:\n{context}"
)
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

# --- 3. ส่วนของหน้าแชท (Chat UI) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# แสดงประวัติการแชท
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# รับข้อความจากผู้ใช้
if prompt := st.chat_input("พิมพ์คำถามเกี่ยวกับองค์กรที่นี่..."):
    # แสดงสิ่งที่พิมพ์
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ให้ AI คิดและตอบ
    with st.chat_message("assistant"):
        with st.spinner("AI กำลังค้นหาข้อมูล..."):
            response = rag_chain.invoke({"input": prompt})
            answer = response["answer"]
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})