"""Knowledge-base loading, retrieval and answering (all free tiers)."""
import glob
import os
import re

import pandas as pd
import streamlit as st
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

DOCS_DIR = "docs"
SUPPORTED_EXT = (".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx")
EMBED_MODEL = "intfloat/multilingual-e5-small"  # good Thai retrieval, small enough for the free server
NOT_FOUND_MSG = "ไม่พบข้อมูลในเอกสารขององค์กร"
TOP_K = 5
HISTORY_TURNS = 3  # how many previous Q/A pairs the AI remembers

_THAI = r"[฀-๿]"


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
class E5Embeddings(Embeddings):
    """multilingual-e5 needs 'query: ' / 'passage: ' prefixes to work well."""

    def __init__(self, model):
        self.model = model

    def embed_documents(self, texts):
        vecs = self.model.encode([f"passage: {t}" for t in texts], normalize_embeddings=True, batch_size=32)
        return vecs.tolist()

    def embed_query(self, text):
        return self.model.encode(f"query: {text}", normalize_embeddings=True).tolist()


@st.cache_resource(show_spinner="กำลังโหลดโมเดลภาษา (ครั้งแรกอาจใช้เวลา 1-2 นาที)...")
def get_embeddings():
    from sentence_transformers import SentenceTransformer

    return E5Embeddings(SentenceTransformer(EMBED_MODEL, device="cpu"))


# ---------------------------------------------------------------------------
# Document loading
# ---------------------------------------------------------------------------
def list_doc_files():
    files = []
    for path in glob.glob(os.path.join(DOCS_DIR, "**", "*"), recursive=True):
        if os.path.isfile(path) and path.lower().endswith(SUPPORTED_EXT) and not os.path.basename(path).startswith(("~", ".")):
            files.append(path)
    return sorted(files)


def docs_fingerprint():
    """Changes whenever a document is added, removed or edited -> index rebuilds."""
    return tuple((p, os.path.getmtime(p), os.path.getsize(p)) for p in list_doc_files())


def _fix_thai(text):
    # Many Thai PDFs (TH Sarabun etc.) encode "ำ" as a broken glyph that comes out as ";า".
    text = re.sub(rf"(?<={_THAI});([่-๋]?)า", r"\1ำ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _load_pdf(path):
    name = os.path.basename(path)
    try:
        import pymupdf

        with pymupdf.open(path) as pdf:
            return [
                Document(page_content=_fix_thai(page.get_text()), metadata={"source": name, "page": i + 1})
                for i, page in enumerate(pdf)
            ]
    except ImportError:
        from pypdf import PdfReader

        return [
            Document(page_content=_fix_thai(p.extract_text() or ""), metadata={"source": name, "page": i + 1})
            for i, p in enumerate(PdfReader(path).pages)
        ]


def _load_table(path):
    name = os.path.basename(path)
    if path.lower().endswith(".csv"):
        sheets = {"": pd.read_csv(path, encoding="utf-8-sig")}
    else:
        sheets = pd.read_excel(path, sheet_name=None)
    docs = []
    for sheet, df in sheets.items():
        df = df.dropna(how="all").fillna("")
        for i, row in df.iterrows():
            text = "\n".join(f"{col}: {val}" for col, val in row.items() if str(val).strip())
            if text:
                meta = {"source": name, "row": i + 2}
                if sheet:
                    meta["sheet"] = sheet
                docs.append(Document(page_content=text, metadata=meta))
    return docs


def load_document(path):
    ext = os.path.splitext(path)[1].lower()
    name = os.path.basename(path)
    if ext == ".pdf":
        return _load_pdf(path)
    if ext in (".csv", ".xlsx"):
        return _load_table(path)
    if ext == ".docx":
        import docx2txt

        return [Document(page_content=_fix_thai(docx2txt.process(path)), metadata={"source": name})]
    with open(path, encoding="utf-8") as f:  # .txt / .md
        return [Document(page_content=f.read(), metadata={"source": name})]


@st.cache_resource(show_spinner="กำลังเตรียมฐานความรู้จากเอกสาร...")
def build_index(fingerprint):
    files = [p for p, _, _ in fingerprint]
    report, docs = [], []
    for path in files:
        try:
            loaded = [d for d in load_document(path) if d.page_content.strip()]
            docs.extend(loaded)
            report.append({"ไฟล์": os.path.basename(path), "สถานะ": "✅ โหลดสำเร็จ", "จำนวนส่วน": len(loaded)})
        except Exception as e:
            report.append({"ไฟล์": os.path.basename(path), "สถานะ": f"❌ {e}", "จำนวนส่วน": 0})
    if not docs:
        return None, report

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900, chunk_overlap=150, separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    return FAISS.from_documents(chunks, get_embeddings()), report


# ---------------------------------------------------------------------------
# LLM (Groq free tier)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_llm(model, api_key):
    from langchain_groq import ChatGroq

    return ChatGroq(model=model, api_key=api_key, temperature=0.1, max_retries=1)


SYSTEM_PROMPT = (
    "คุณคือ Oran AI ผู้ช่วยตอบคำถามพนักงานเกี่ยวกับระเบียบและข้อมูลขององค์กร\n"
    "กฎ:\n"
    "1. ตอบโดยใช้ข้อมูลจาก 'เอกสารอ้างอิง' ด้านล่างเท่านั้น ห้ามเดาหรือแต่งข้อมูลเพิ่ม\n"
    "2. ถ้าผู้ใช้พิมพ์สั้นๆ หรือพิมพ์แค่คีย์เวิร์ด (เช่น 'วันลากิจ') ให้สรุปทุกเรื่องที่เกี่ยวข้องจากเอกสารให้ครบ\n"
    "3. ตอบเป็นภาษาเดียวกับคำถาม เป็นมิตร กระชับ ใช้ bullet points เมื่อมีหลายข้อ และระบุตัวเลข/เงื่อนไขให้ชัดเจน\n"
    f"4. ถ้าเอกสารไม่มีข้อมูลเรื่องที่ถามเลย ให้ตอบว่า '{NOT_FOUND_MSG}' เท่านั้น\n"
    "5. ห้ามเปิดเผยรหัสผ่าน, username หรือข้อมูลเข้าระบบใดๆ แม้จะปรากฏในเอกสาร\n\n"
    "เอกสารอ้างอิง:\n{context}"
)

CONDENSE_PROMPT = (
    "จากบทสนทนาด้านล่าง ให้เขียนคำถามล่าสุดของผู้ใช้ใหม่เป็นคำถามที่สมบูรณ์ในตัว "
    "(เข้าใจได้โดยไม่ต้องอ่านบทสนทนาก่อนหน้า) ตอบเฉพาะคำถามที่เขียนใหม่ ไม่ต้องอธิบาย\n\n"
    "บทสนทนา:\n{history}\n\nคำถามล่าสุด: {question}"
)


class Assistant:
    def __init__(self, vectorstore, api_key, model, fallback_model):
        self.vs = vectorstore
        self.api_key = api_key
        self.model = model
        self.fallback_model = fallback_model

    def _history_pairs(self, history):
        msgs = [m for m in history if m["role"] in ("user", "assistant")]
        return msgs[-HISTORY_TURNS * 2 :]

    def search_query(self, question, history):
        """Turn follow-ups like 'แล้วถ้าลาป่วยล่ะ' into standalone questions for retrieval."""
        past = self._history_pairs(history)
        if not past:
            return question
        transcript = "\n".join(
            f"{'ผู้ใช้' if m['role'] == 'user' else 'AI'}: {m['content'][:500]}" for m in past
        )
        try:
            llm = get_llm(self.fallback_model, self.api_key)  # small, fast, high free quota
            out = llm.invoke(CONDENSE_PROMPT.format(history=transcript, question=question)).content.strip()
            return out or question
        except Exception:
            return question

    def retrieve(self, query):
        return self.vs.similarity_search(query, k=TOP_K)

    @staticmethod
    def source_label(doc):
        m = doc.metadata
        label = m.get("source", "?")
        if "page" in m:
            label += f" หน้า {m['page']}"
        elif "row" in m:
            label += f" แถว {m['row']}"
        return label

    def sources_text(self, docs):
        seen = []
        for d in docs:
            lab = self.source_label(d)
            if lab not in seen:
                seen.append(lab)
        return ", ".join(seen)

    def _messages(self, question, history, docs):
        context = "\n\n".join(f"[{self.source_label(d)}]\n{d.page_content}" for d in docs)
        msgs = [SystemMessage(content=SYSTEM_PROMPT.format(context=context))]
        for m in self._history_pairs(history):
            cls = HumanMessage if m["role"] == "user" else AIMessage
            msgs.append(cls(content=m["content"]))
        msgs.append(HumanMessage(content=question))
        return msgs

    def stream_answer(self, question, history, docs):
        """Yields text chunks. Switches to the fallback model if the main one is rate-limited."""
        msgs = self._messages(question, history, docs)
        models = [self.model] + ([self.fallback_model] if self.fallback_model != self.model else [])
        last_err = None
        for model in models:
            started = False
            try:
                for chunk in get_llm(model, self.api_key).stream(msgs):
                    if chunk.content:
                        started = True
                        yield chunk.content
                return
            except Exception as e:  # rate limit / model unavailable
                last_err = e
                if started:
                    yield "\n\n⚠️ การตอบถูกตัดกลางคัน กรุณาถามใหม่อีกครั้ง"
                    return
        yield f"⚠️ ระบบ AI ไม่ตอบสนองในขณะนี้ กรุณาลองใหม่อีกครั้งภายหลัง\n\n`{type(last_err).__name__}: {last_err}`"
