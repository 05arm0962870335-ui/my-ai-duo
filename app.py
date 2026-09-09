import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Dual-Agent Chat", layout="centered", page_icon="💬")

gemini_key = st.secrets.get("GEMINI_API_KEY")

st.title("💬 Dual-Agent Chat System")
st.caption("ระบบแชตโต้ตอบต่อเนื่อง: ทุกข้อความจะถูกร่างโดย Agent A และตรวจทานความถูกต้องโดย Agent B")

# ตรวจสอบ API Key
if not gemini_key:
    st.error("ไม่พบคีย์ GEMINI_API_KEY ใน Secrets กรุณาตรวจสอบการตั้งค่า")
    st.stop()

genai.configure(api_key=gemini_key.strip())

# ฟังก์ชันเลือกโมเดลอัตโนมัติที่บัญชีใช้งานได้จริง
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

# สร้างที่เก็บประวัติการคุยใน session
if "messages" not in st.session_state:
    st.session_state.messages = []

# ปุ่มล้างประวัติการคุย เพื่อเริ่มเรื่องใหม่
if st.sidebar.button("🗑️ ล้างบทสนทนา (เริ่มหัวข้อใหม่)"):
    st.session_state.messages = []
    st.rerun()

# แสดงประวัติการสนทนาที่ผ่านมาบนหน้าจอ
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "draft" in msg:
            with st.expander("🔍 ดูร่างคำตอบแรกจาก Agent A (ก่อนตรวจทาน)"):
                st.markdown(msg["draft"])

# กล่องรับข้อความแชตด้านล่าง
if user_prompt := st.chat_input("พิมพ์คำถามหรือถามต่อเนื่องได้เลย..."):
    # แสดงคำถามของผู้ใช้ทันที
    st.chat_message("user").markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # เตรียมประวัติการคุยย่อๆ เพื่อส่งให้ AI จำบริบทเดิมได้
    history_context = "\n".join([
        f"{m['role'].capitalize()}: {m['content']}" 
        for m in st.session_state.messages[-6:] # ดึง 6 ข้อความล่าสุด
    ])

    with st.chat_message("assistant"):
        with st.status("ทีม AI กำลังร่วมกันวิเคราะห์และตรวจทาน...", expanded=True) as status:
            # 1. Agent A ร่างคำตอบโดยอิงบริบทเก่า
            st.write("📝 Agent A (ผู้ค้นคว้า) กำลังร่างคำตอบ...")
            draft_prompt = f"""
            ประวัติการสนทนาที่ผ่านมา:
            {history_context}

            ข้อความล่าสุดจากผู้ใช้: {user_prompt}

            หน้าที่ของคุณ (Agent A):
            ร่างคำตอบหรือข้อมูลที่ตอบตรงประเด็น ละเอียด และเชื่อมโยงกับสิ่งที่คุยกันมาก่อนหน้านี้เป็นภาษาไทย
            """
            res_draft = model.generate_content(draft_prompt)
            draft_text = res_draft.text

            # 2. Agent B ตรวจสอบและเกลาคำตอบ
            st.write("🔍 Agent B (ผู้ตรวจทาน) กำลังตรวจสอบความถูกต้องและสังเคราะห์...")
            audit_prompt = f"""
            ประวัติการสนทนาที่ผ่านมา:
            {history_context}

            ข้อความล่าสุดจากผู้ใช้: {user_prompt}

            ร่างคำตอบที่ Agent A เขียนขึ้น:
            {draft_text}

            หน้าที่ของคุณ (Agent B):
            1. ตรวจสอบความถูกต้องว่าข้อมูลสอดคล้องกับบริบทเดิมและคำถามล่าสุดหรือไม่
            2. กรองจุดที่ผิดพลาด คลาดเคลื่อน หรือเวิ่นเว้อออก
            3. เรียบเรียงเป็นคำตอบสุดท้ายที่ดีที่สุด สุภาพ ชัดเจน และอ่านง่ายเป็นภาษาไทย
            """
            res_final = model.generate_content(audit_prompt)
            final_text = res_final.text

            status.update(label="เรียบร้อย!", state="complete")

        # แสดงผลลัพธ์สุดท้าย
        st.markdown(final_text)
        with st.expander("🔍 ดูร่างคำตอบแรกจาก Agent A (ก่อนตรวจทาน)"):
            st.markdown(draft_text)

    # บันทึกคำตอบลง session
    st.session_state.messages.append({
        "role": "assistant", 
        "content": final_text,
        "draft": draft_text
    })
