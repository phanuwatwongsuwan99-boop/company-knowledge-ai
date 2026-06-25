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

st.set_page_config(page_title="Corporate AI Assistant", page_icon="🤖")

def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
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
        return False
    return True

if not check_password():
    st.stop()

st.title("🤖 ผู้ช่วย AI สำหรับองค์กร")

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
