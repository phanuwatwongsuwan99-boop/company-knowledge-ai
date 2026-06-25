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
import time  # 👈 เพิ่มเครื่องมือควบคุมเวลาสำหรับแอนิเมชันไดโนเสาร์

st.set_page_config(page_title="Corporate AI Assistant", page_icon="🤖")

# --- ระบบ Login ---
def check_password():
    def login_attempt():
        user = st.session_state["username_input"]
        pw = st.session_state["password_input"]
        
        if "passwords" in st.secrets and user in st.secrets["passwords"]:
            if str(st.secrets["passwords"][user]) == str(pw):
                st.session_state["password_correct"] = True
                st.session_state["current_user"] = user 
                st.session_state["show_dino"] = True  # 👈 สั่งให้เปิดหน้าไดโนเสาร์วิ่งตอนเข้าสู่ระบบสำเร็จ
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

# --- แอนิเมชันไดโนเสาร์โหลดดิ้ง 🦖 ---
if st.session_state.get("show_dino", False):
    st.title("🤖 กำลังเข้าสู่ระบบ...")
    
    # สร้างพื้นที่ว่างสำหรับโชว์ข้อความและแถบโหลด
    dino_text = st.empty()
    progress_bar = st.progress(0)
    
    # ให้ไดโนเสาร์วิ่งจาก 1 ถึง 100
    for percent in range(1, 101):
        # เคาะ spacebar ดันไดโนเสาร์ไปทางขวาตามเปอร์เซ็นต์
        spaces = "&nbsp;" * percent 
        dino_text.markdown(f"{spaces}🦖 **กำลังดึงข้อมูลองค์กร... {percent}%**")
        progress_bar.progress(percent)
        time.sleep(0.02)  # ความเร็วในการวิ่ง (ยิ่งค่าน้อยยิ่งวิ่งเร็ว)
        
    # ลบแถบโหลดทิ้งเมื่อวิ่งเสร็จ
    dino_text.empty()
    progress_bar.empty()
    
    # ปิดสวิตช์ไดโนเสาร์เพื่อไม่ให้มันโชว์อีก และโหลดหน้าหลัก
    st.session_state["show_dino"] = False
    st.rerun()
# ------------------------------------

# --- หน้าแชทหลัก ---
st.caption(f"👤 เข้าสู่ระบบโดย: {st.session_state['current_user']}")
st.title("🤖 ผู้ช่วย AI สำหรับองค์กร")

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

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("พิมพ์คำถาม..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("AI กำลังคิด..."):
            response = rag_chain.invoke(user_input)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
