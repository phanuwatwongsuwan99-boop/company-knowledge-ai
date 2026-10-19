import hmac
import html
import time
import uuid
from collections import Counter
from datetime import datetime

import pandas as pd
import streamlit as st

import storage
from assets import (
    LOGO_B64_RAW,
    TOMATO_1_B64_RAW,
    TOMATO_2_B64_RAW,
    TOMATO_3_B64_RAW,
    TOMATO_4_B64_RAW,
    TOMATO_5_B64_RAW,
)
from rag import NOT_FOUND_MSG, Assistant, build_index, docs_fingerprint
from styles import global_css

st.set_page_config(page_title="Oran AI | Corporate Assistant", page_icon="🟠", layout="wide")

LOGO_IMG = f"data:image/png;base64,{LOGO_B64_RAW}"
TOMATO_FRAMES = [
    f"data:image/png;base64,{f}"
    for f in [TOMATO_1_B64_RAW, TOMATO_2_B64_RAW, TOMATO_3_B64_RAW, TOMATO_4_B64_RAW, TOMATO_5_B64_RAW]
]
st.markdown(global_css(TOMATO_FRAMES), unsafe_allow_html=True)

HIDE_SIDEBAR = """
<style>
    [data-testid='stSidebar']{display:none;}
    [data-testid='stAppViewContainer'] > .main {margin-left:0;}
</style>
"""


def secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


ADMIN_USERS = list(secret("ADMIN_USERS", ["boss", "admin"]))


# =========================================================
# 🔐 LOGIN
# =========================================================
def logout():
    st.session_state.clear()


def new_chat():
    st.session_state["current_chat_id"] = uuid.uuid4().hex[:8]
    st.session_state.messages = []


def switch_chat(chat_id):
    st.session_state["current_chat_id"] = chat_id
    st.session_state.messages = []


def login_attempt():
    user = st.session_state.get("username_input", "").strip()
    pw = st.session_state.get("password_input", "")
    users = secret("passwords", {}) or {}
    ok = user in users and hmac.compare_digest(str(users[user]).encode(), str(pw).encode())
    st.session_state["password_correct"] = ok
    st.session_state.pop("password_input", None)
    if ok:
        st.session_state["current_user"] = user
        st.session_state["show_loader"] = True


def render_login():
    st.markdown(HIDE_SIDEBAR, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.3, 1])
    with col:
        st.markdown(
            f"""
            <div class="login-wrap">
                <div class="login-orb-bloom"><img src="{LOGO_IMG}" alt="Oran AI" /></div>
                <div class="login-title">Oran AI</div>
                <div class="login-subtitle">ผู้ช่วย AI สำหรับองค์กรของคุณ</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not secret("passwords"):
            st.error("ยังไม่ได้ตั้งค่าบัญชีผู้ใช้ใน Secrets (หัวข้อ [passwords]) — ดูวิธีใน README")
        elif st.session_state.get("password_correct") is False:
            st.error("ชื่อผู้ใช้งาน หรือ รหัสผ่าน ไม่ถูกต้อง! กรุณาลองใหม่")
        with st.form("login", border=False):
            st.text_input("ชื่อผู้ใช้งาน", key="username_input", placeholder="Username")
            st.text_input("รหัสผ่าน", type="password", key="password_input", placeholder="Password")
            st.form_submit_button("เข้าสู่ระบบ", on_click=login_attempt, width="stretch", type="primary")


if not st.session_state.get("password_correct"):
    render_login()
    st.stop()

# --- แอนิเมชันมะเขือเทศกลิ้ง (ตอนกำลังเข้าสู่ระบบ) ---
if st.session_state.get("show_loader"):
    st.markdown(HIDE_SIDEBAR, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.3, 1])
    with col:
        st.markdown(
            f"""
            <div class="login-wrap" style="padding-top: 10vh;">
                <div class="login-orb-bloom"><img src="{LOGO_IMG}" alt="Oran AI" /></div>
                <div class="login-title">กำลังเข้าสู่ระบบ</div>
                <div class="tomato-roll-track"><div class="tomato-roll-sprite"></div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Warm up the heavy parts while the animation plays
        build_index(docs_fingerprint())
        time.sleep(0.8)
    st.session_state["show_loader"] = False
    st.session_state.setdefault("current_chat_id", uuid.uuid4().hex[:8])
    st.rerun()

USER = st.session_state["current_user"]


def brand_header():
    st.markdown(
        f"""
        <div class="brand-row">
            <img src="{LOGO_IMG}" alt="Oran AI" />
            <div class="brand-name">Oran AI</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 👑 ADMIN PANEL
# =========================================================
def top_keywords(texts, top_n=5):
    try:
        from pythainlp.corpus import thai_stopwords
        from pythainlp.tokenize import word_tokenize

        stop = set(thai_stopwords()) | {"ครับ", "คะ", "ค่ะ", "สอบถาม", "อยาก", "ขอ", "ทราบ", "บ้าง", "ยังไง", "อย่างไร"}
        tokenize = lambda t: word_tokenize(t, engine="newmm", keep_whitespace=False)
    except Exception:
        stop, tokenize = set(), str.split
    words = []
    for text in texts.dropna():
        for w in tokenize(str(text).lower()):
            w = w.strip(" ?.,!:()\"'")
            if len(w) > 1 and w not in stop and not w.isdigit():
                words.append(w)
    return Counter(words).most_common(top_n)


def admin_page():
    with st.sidebar:
        brand_header()
        st.markdown(f"<span class='admin-pill'>ผู้ดูแลระบบ · {html.escape(USER)}</span>", unsafe_allow_html=True)
        st.write("---")
        st.button("🚪 ออกจากระบบ", on_click=logout, width="stretch")

    st.title("📊 Admin Dashboard")

    if storage.using_sheets():
        st.success(f"💾 ที่เก็บประวัติแชท: **{storage.backend_name()}** (ข้อมูลถาวร)")
    else:
        st.warning(
            "💾 ที่เก็บประวัติแชทตอนนี้เป็น **ไฟล์ชั่วคราว** — ข้อมูลจะหายเมื่อแอปรีสตาร์ท "
            "แนะนำให้เชื่อม Google Sheets (ฟรี) ตามขั้นตอนใน README และดาวน์โหลดสำรองข้อมูลเป็นระยะ"
        )

    tab_stats, tab_logs, tab_docs = st.tabs(["📈 สถิติ", "📋 ประวัติการใช้งาน", "📚 เอกสาร"])
    df = storage.load_logs()

    with tab_stats:
        if df.empty:
            st.info("ยังไม่มีพนักงานเข้ามาใช้งานระบบ")
        else:
            total = len(df)
            unanswered_df = df[df["สถานะการตอบ"] == "ตอบไม่ได้"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("คำถามทั้งหมด", f"{total}")
            c2.metric("AI ตอบได้", f"{total - len(unanswered_df)}")
            c3.metric("AI ไม่มีคำตอบ", f"{len(unanswered_df)}")
            c4.metric("ผู้ใช้งาน", f"{df['ชื่อพนักงาน'].nunique()}")

            st.subheader("🔥 หัวข้อที่ถามบ่อยที่สุด")
            kws = top_keywords(df["คำถาม"])
            if kws:
                st.bar_chart(pd.DataFrame(kws, columns=["คำ", "จำนวนครั้ง"]).set_index("คำ"), horizontal=True)
            else:
                st.info("ข้อมูลยังไม่เพียงพอ")

            st.subheader("⚠️ คำถามที่ AI ยังตอบไม่ได้ (ควรเพิ่มเอกสาร)")
            if unanswered_df.empty:
                st.success("ยอดเยี่ยม! ยังไม่มีคำถามที่เอกสารตอบไม่ได้")
            else:
                st.dataframe(
                    unanswered_df[["วัน-เวลา", "ชื่อพนักงาน", "คำถาม"]].iloc[::-1],
                    width="stretch",
                    hide_index=True,
                )

    with tab_logs:
        if df.empty:
            st.info("ยังไม่มีประวัติ")
        else:
            st.download_button(
                "📥 ดาวน์โหลดประวัติทั้งหมด (CSV)",
                data=storage.logs_csv_bytes(df),
                file_name=f"chat_logs_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
            users = ["ทั้งหมด"] + sorted(df["ชื่อพนักงาน"].unique().tolist())
            pick = st.selectbox("กรองตามพนักงาน", users)
            view = df if pick == "ทั้งหมด" else df[df["ชื่อพนักงาน"] == pick]
            st.dataframe(view.iloc[::-1], width="stretch", hide_index=True)

    with tab_docs:
        st.caption(
            "เพิ่ม/แก้ไขเอกสารได้โดยอัปโหลดไฟล์ลงโฟลเดอร์ `docs/` ใน GitHub (รองรับ PDF, DOCX, TXT, MD, CSV, XLSX) "
            "แอปจะอัปเดตฐานความรู้ให้อัตโนมัติ ⚠️ ห้ามใส่ไฟล์ที่มีรหัสผ่านหรือข้อมูลลับ"
        )
        _, report = build_index(docs_fingerprint())
        if report:
            st.dataframe(pd.DataFrame(report), width="stretch", hide_index=True)
        else:
            st.error("ไม่พบเอกสารในโฟลเดอร์ docs/")
        if st.button("🔄 สร้างฐานความรู้ใหม่"):
            build_index.clear()
            st.rerun()


if USER in ADMIN_USERS:
    admin_page()
    st.stop()

# =========================================================
# 💬 CHAT
# =========================================================
api_key = secret("GROQ_API_KEY")
if not api_key:
    st.error("ยังไม่ได้ตั้งค่า GROQ_API_KEY ใน Secrets — ดูวิธีใน README")
    st.stop()

vectorstore, _ = build_index(docs_fingerprint())
if vectorstore is None:
    st.error("ยังไม่มีเอกสารในฐานความรู้ (โฟลเดอร์ docs/) กรุณาติดต่อผู้ดูแลระบบ")
    st.stop()

assistant = Assistant(
    vectorstore,
    api_key=api_key,
    model=secret("GROQ_MODEL", "llama-3.3-70b-versatile"),
    fallback_model=secret("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant"),
)

all_logs = storage.load_logs()
my_logs = all_logs[all_logs["ชื่อพนักงาน"] == USER]

with st.sidebar:
    brand_header()
    st.caption(f"👤 {USER}")
    st.button("➕ New chat", on_click=new_chat, width="stretch", type="primary")
    st.write("---")
    st.write("**History**")
    if my_logs.empty:
        st.caption("ยังไม่มีประวัติการแชท")
    else:
        for chat_id, group in reversed(list(my_logs.groupby("Chat ID", sort=False))):
            first_q = str(group.iloc[0]["คำถาม"])
            short = first_q[:25] + "..." if len(first_q) > 25 else first_q
            icon = "📍" if chat_id == st.session_state.get("current_chat_id") else "💬"
            st.button(f"{icon} {short}", key=f"btn_{chat_id}", on_click=switch_chat, args=(chat_id,), width="stretch")
    st.write("---")
    st.button("🚪 Logout", on_click=logout, width="stretch")

st.session_state.setdefault("current_chat_id", uuid.uuid4().hex[:8])
if not st.session_state.get("messages"):
    st.session_state.messages = []
    for _, row in my_logs[my_logs["Chat ID"] == st.session_state["current_chat_id"]].iterrows():
        st.session_state.messages.append({"role": "user", "content": str(row["คำถาม"])})
        st.session_state.messages.append(
            {"role": "assistant", "content": str(row["คำตอบจาก AI"]), "sources": str(row["แหล่งข้อมูล"])}
        )


def show_user(text):
    st.markdown(f'<span class="chat-user-marker" style="display:none"></span>{html.escape(text)}', unsafe_allow_html=True)


def show_sources(sources):
    if sources:
        st.caption(f"📄 อ้างอิง: {sources}")


if not st.session_state.messages:
    st.markdown(
        f"""
        <div class="empty-hero">
            <img src="{LOGO_IMG}" alt="Oran AI" />
            <h2>มีอะไรให้ช่วยไหม</h2>
            <p>พิมพ์คำถามเกี่ยวกับองค์กรของคุณด้านล่างนี้ได้เลย</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            if m["role"] == "user":
                show_user(m["content"])
            else:
                st.markdown(m["content"])
                show_sources(m.get("sources"))

if user_input := st.chat_input("พิมพ์คำถามเกี่ยวกับองค์กร... (พิมพ์คำสั้นๆ ก็ได้นะ)"):
    history = list(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        show_user(user_input)

    with st.chat_message("assistant"):
        with st.spinner("กำลังค้นหาข้อมูลจากเอกสาร..."):
            query = assistant.search_query(user_input, history)
            docs = assistant.retrieve(query)
        response = st.write_stream(assistant.stream_answer(user_input, history, docs))
        response = response if isinstance(response, str) else "".join(map(str, response))

        answered = NOT_FOUND_MSG not in response and not response.startswith("⚠️")
        sources = assistant.sources_text(docs) if answered else ""
        show_sources(sources)

    st.session_state.messages.append({"role": "assistant", "content": response, "sources": sources})
    try:
        storage.append_log(
            st.session_state["current_chat_id"], USER, user_input, response,
            "ตอบได้" if answered else "ตอบไม่ได้", sources,
        )
    except Exception as e:
        st.toast(f"บันทึกประวัติไม่สำเร็จ: {e}", icon="⚠️")
    st.rerun()

# =========================================================
# 🛠️ JS FIX: vertically centre the chat input contents
# =========================================================
st.html(
    """
    <script>
    function centerChatInputVertically() {
        const doc = document;
        doc.querySelectorAll('[data-testid="stChatInput"] textarea').forEach(function(ta) {
            let node = ta.parentElement;
            for (let i = 0; i < 5 && node; i++) {
                if (window.getComputedStyle(node).display === 'flex') {
                    node.style.setProperty('align-items', 'center', 'important');
                }
                node = node.parentElement;
            }
            ta.style.setProperty('margin-top', 'auto', 'important');
            ta.style.setProperty('margin-bottom', 'auto', 'important');
        });
        doc.querySelectorAll('[data-testid="stChatInput"] button').forEach(function(btn) {
            btn.style.setProperty('margin-top', 'auto', 'important');
            btn.style.setProperty('margin-bottom', 'auto', 'important');
            btn.style.setProperty('align-self', 'center', 'important');
        });
    }
    centerChatInputVertically();
    let throttled = false;
    new MutationObserver(function() {
        if (throttled) return;
        throttled = true;
        setTimeout(function() { centerChatInputVertically(); throttled = false; }, 200);
    }).observe(document.body, {childList: true, subtree: true});
    </script>
    """,
    unsafe_allow_javascript=True,
)
