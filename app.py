import streamlit as st
import google.generativeai as genai
import sqlite3
import time
from datetime import datetime
from google.api_core.exceptions import ResourceExhausted

st.set_page_config(page_title="Dual-Agent Chat & History", layout="wide", page_icon="💬")

# --- 1. ระบบฐานข้อมูล SQLite ---
DB_FILE = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT,
            updated_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            draft TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_all_sessions():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT session_id, title FROM sessions ORDER BY updated_at DESC")
    sessions = c.fetchall()
    conn.close()
    return sessions

def load_session_messages(session_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role, content, draft FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "draft": r[2]} for r in rows]

def save_message_to_db(session_id, role, content, draft=None, title=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO sessions (session_id, title, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET updated_at = excluded.updated_at
    """, (session_id, title or "บทสนทนาใหม่", now))
    if title:
        c.execute("UPDATE sessions SET title = ? WHERE session_id = ?", (title, session_id))
    c.execute("""
        INSERT INTO messages (session_id, role, content, draft, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, role, content, draft, now))
    conn.commit()
    conn.close()

def delete_session(session_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

init_db()

# --- 2. การตั้งค่า Gemini API พร้อมระบบ Retry ---
gemini_key = st.secrets.get("GEMINI_API_KEY")
if not gemini_key:
    st.error("ไม่พบคีย์ GEMINI_API_KEY ใน Secrets")
    st.stop()

genai.configure(api_key=gemini_key.strip())

@st.cache_resource
def get_working_model():
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    for m in models:
        if "flash" in m:
            return m
    return models[0] if models else "gemini-1.5-flash"

chosen_model_name = get_working_model()
model = genai.GenerativeModel(chosen_model_name)

# ฟังก์ชันยิงคำขอแบบกัน Rate Limit
def generate_safe(prompt, retries=3, delay=4):
    for attempt in range(retries):
        try:
            return model.generate_content(prompt).text
        except ResourceExhausted:
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise

# --- 3. Session State ---
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state.messages = []

# --- 4. Sidebar ---
with st.sidebar:
    st.title("📚 ประวัติการค้นคว้า")
    if st.button("➕ เปิดแชตใหม่ (New Chat)", use_container_width=True):
        st.session_state.current_session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        st.session_state.messages = []
        st.rerun()

    st.write("---")
    for s_id, s_title in get_all_sessions():
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(s_title[:20] + ("..." if len(s_title) > 20 else ""), key=f"btn_{s_id}", use_container_width=True):
                st.session_state.current_session_id = s_id
                st.session_state.messages = load_session_messages(s_id)
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{s_id}"):
                delete_session(s_id)
                if st.session_state.current_session_id == s_id:
                    st.session_state.current_session_id = datetime.now().strftime("%Y%m%d%H%M%S")
                    st.session_state.messages = []
                st.rerun()

# --- 5. Chat UI ---
st.title("💬 Dual-Agent Chat System")
st.caption(f"โมเดล: `{chosen_model_name}` | ระบบ 2 Agent ตรวจทานอัตโนมัติ")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("draft"):
            with st.expander("🔍 ดูร่างคำตอบแรกจาก Agent A (ก่อนตรวจทาน)"):
                st.markdown(msg["draft"])

if user_prompt := st.chat_input("พิมพ์คำถามได้เลย..."):
    is_first_message = len(st.session_state.messages) == 0
    chat_title = user_prompt[:30] if is_first_message else None

    st.chat_message("user").markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    save_message_to_db(st.session_state.current_session_id, "user", user_prompt, title=chat_title)

    history_context = "\n".join([
        f"{m['role'].capitalize()}: {m['content']}" 
        for m in st.session_state.messages[-4:]
    ])

    with st.chat_message("assistant"):
        with st.status("ทีม AI กำลังประมวลผล...", expanded=True) as status:
            try:
                # 1. Agent A ร่าง
                st.write("📝 Agent A กำลังร่างคำตอบ...")
                draft_prompt = f"บริบทก่อนหน้า:\n{history_context}\n\nคำถาม: {user_prompt}\n\nหน้าที่ (Agent A): ร่างข้อมูลอย่างละเอียด เป็นโครงสร้างชัดเจนเป็นภาษาไทย"
                draft_text = generate_safe(draft_prompt)

                # พักสั้นๆ 1 วินาทีไม่ให้ยิงคำขอติดกันเกินไป
                time.sleep(1)

                # 2. Agent B ตรวจทาน
                st.write("🔍 Agent B กำลังตรวจสอบและสังเคราะห์...")
                audit_prompt = f"บริบทก่อนหน้า:\n{history_context}\n\nคำถาม: {user_prompt}\n\nร่างคำตอบ Agent A:\n{draft_text}\n\nหน้าที่ (Agent B): ตรวจสอบความถูกต้อง กรองข้อมูลมั่ว แล้วสรุปเป็นคำตอบสุดท้ายที่ดีที่สุดเป็นภาษาไทย"
                final_text = generate_safe(audit_prompt)

                status.update(label="ประมวลผลเสร็จสิ้น!", state="complete")
            except ResourceExhausted:
                status.update(label="โควตาชั่วคราวเต็ม กรุณารอสักครู่", state="error")
                st.error("คุณส่งคำถามเร็วเกินไป กรุณารอประมาณ 30–60 วินาที แล้วลองใหม่อีกครั้งครับ")
                st.stop()

        st.markdown(final_text)
        with st.expander("🔍 ดูร่างคำตอบแรกจาก Agent A (ก่อนตรวจทาน)"):
            st.markdown(draft_text)

    st.session_state.messages.append({"role": "assistant", "content": final_text, "draft": draft_text})
    save_message_to_db(st.session_state.current_session_id, "assistant", final_text, draft=draft_text)
