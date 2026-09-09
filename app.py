import streamlit as st
import google.generativeai as genai
import sqlite3
import json
from datetime import datetime

st.set_page_config(page_title="Dual-Agent Chat & History", layout="wide", page_icon="💬")

# --- 1. ระบบฐานข้อมูลบันทึกประวัติการคุย (SQLite) ---
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
    
    # บันทึกหรืออัปเดตหัวข้อแชต
    c.execute("""
        INSERT INTO sessions (session_id, title, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET updated_at = excluded.updated_at
    """, (session_id, title or "บทสนทนาใหม่", now))
    
    if title:
        c.execute("UPDATE sessions SET title = ? WHERE session_id = ?", (title, session_id))

    # บันทึกข้อความ
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

# --- 2. การตั้งค่าโมเดล Gemini ---
gemini_key = st.secrets.get("GEMINI_API_KEY")
if not gemini_key:
    st.error("ไม่พบคีย์ GEMINI_API_KEY ใน Secrets กรุณาตรวจสอบการตั้งค่า")
    st.stop()

genai.configure(api_key=gemini_key.strip())

@st.cache_resource
def get_working_model():
    models = [
        m.name for m in genai.list_models() 
        if 'generateContent' in m.supported_generation_methods
    ]
    for m in models:
        if "flash" in m:
            return m
    return models[0] if models else "gemini-1.5-flash"

chosen_model_name = get_working_model()
model = genai.GenerativeModel(chosen_model_name)

# --- 3. จัดการ Session State ปัจจุบัน ---
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state.messages = []

# --- 4. แถบเมนูด้านข้าง (Sidebar) แสดงประวัติแชตย้อนหลัง ---
with st.sidebar:
    st.title("📚 ประวัติการค้นคว้า")
    
    # ปุ่มเริ่มเรื่องใหม่
    if st.button("➕ เปิดแชตใหม่ (New Chat)", use_container_width=True):
        st.session_state.current_session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        st.session_state.messages = []
        st.rerun()

    st.write("---")
    st.write("🗂️ **รายการแชตที่ผ่านมา:**")
    
    past_sessions = get_all_sessions()
    for s_id, s_title in past_sessions:
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            # คลิกเพื่อดึงแชตเก่ากลับมาดู/คุยต่อ
            if st.button(s_title[:22] + ("..." if len(s_title) > 22 else ""), key=f"btn_{s_id}", use_container_width=True):
                st.session_state.current_session_id = s_id
                st.session_state.messages = load_session_messages(s_id)
                st.rerun()
        with col2:
            # ปุ่มลบแชตเก่า
            if st.button("🗑️", key=f"del_{s_id}"):
                delete_session(s_id)
                if st.session_state.current_session_id == s_id:
                    st.session_state.current_session_id = datetime.now().strftime("%Y%m%d%H%M%S")
                    st.session_state.messages = []
                st.rerun()

# --- 5. พื้นที่แชตหลัก ---
st.title("💬 Dual-Agent Chat System")
st.caption(f"โมเดลที่ใช้งาน: `{chosen_model_name}` | Agent A ร่างประเด็น + Agent B ตรวจสอบข้อเท็จจริง")

# แสดงข้อความที่เคยคุยกัน
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("draft"):
            with st.expander("🔍 ดูร่างคำตอบแรกจาก Agent A (ก่อนตรวจทาน)"):
                st.markdown(msg["draft"])

# กล่องรับข้อความ
if user_prompt := st.chat_input("พิมพ์คำถามหรือถามต่อเนื่องได้เลย..."):
    # บันทึกข้อความผู้ใช้
    is_first_message = len(st.session_state.messages) == 0
    chat_title = user_prompt[:30] if is_first_message else None
    
    st.chat_message("user").markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    save_message_to_db(st.session_state.current_session_id, "user", user_prompt, title=chat_title)

    # บริบทการคุยก่อนหน้า
    history_context = "\n".join([
        f"{m['role'].capitalize()}: {m['content']}" 
        for m in st.session_state.messages[-6:]
    ])

    # การประมวลผล Dual-Agent
    with st.chat_message("assistant"):
        with st.status("ทีม AI กำลังวิเคราะห์และตรวจสอบ...", expanded=True) as status:
            # Agent A ร่างคำตอบ
            st.write("📝 Agent A กำลังร่างคำตอบ...")
            draft_prompt = f"""
            ประวัติการสนทนา:
            {history_context}

            คำถามล่าสุด: {user_prompt}

            หน้าที่ของคุณ (Agent A):
            ร่างข้อมูลและข้อเท็จจริงอย่างละเอียด เป็นโครงสร้างชัดเจน และตอบให้ตรงประเด็นเป็นภาษาไทย
            """
            res_draft = model.generate_content(draft_prompt)
            draft_text = res_draft.text

            # Agent B ตรวจสอบและสังเคราะห์
            st.write("🔍 Agent B กำลังตรวจสอบข้อผิดพลาดและเรียบเรียง...")
            audit_prompt = f"""
            ประวัติการสนทนา:
            {history_context}

            คำถามล่าสุด: {user_prompt}

            ข้อมูลที่ Agent A ร่างไว้:
            {draft_text}

            หน้าที่ของคุณ (Agent B):
            1. ตรวจสอบความถูกต้องว่าข้อมูลสอดคล้องกับบริบทเดิมและคำถามล่าสุดหรือไม่
            2. กรองจุดที่ผิดพลาด คลาดเคลื่อน หรือเวิ่นเว้อออก
            3. สรุปเป็น "คำตอบสุดท้ายที่ดีที่สุด" ที่ถูกต้อง แม่นยำ และอ่านง่ายเป็นภาษาไทย
            """
            res_final = model.generate_content(audit_prompt)
            final_text = res_final.text

            status.update(label="ประมวลผลเสร็จสิ้น!", state="complete")

        st.markdown(final_text)
        with st.expander("🔍 ดูร่างคำตอบแรกจาก Agent A (ก่อนตรวจทาน)"):
            st.markdown(draft_text)

    # บันทึกคำตอบ AI ลงฐานข้อมูล
    st.session_state.messages.append({
        "role": "assistant",
        "content": final_text,
        "draft": draft_text
    })
    save_message_to_db(st.session_state.current_session_id, "assistant", final_text, draft=draft_text)
