import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Gemini Multi-Agent Research", layout="centered", page_icon="🧠")

gemini_key = st.secrets.get("GEMINI_API_KEY")

st.title("🧠 Gemini Dual-Agent System")
st.caption("ระบบ 2 Agent วิเคราะห์ร่วมกัน: Agent A ร่างประเด็น และ Agent B ตรวจสอบความถูกต้อง")

query = st.text_area("พิมพ์คำถามหรือหัวข้อที่ต้องการค้นหา:", placeholder="เช่น เปรียบเทียบข้อดีข้อเสียของ...", height=120)

if st.button("🚀 เริ่มค้นหาและวิเคราะห์", type="primary"):
    if not query.strip():
        st.warning("กรุณาใส่คำถามก่อนครับ")
    elif not gemini_key:
        st.error("ไม่พบคีย์ GEMINI_API_KEY ใน Secrets")
    else:
        # กำหนด API Key
        genai.configure(api_key=gemini_key.strip())
        
        # เลือกโมเดลที่เสถียรที่สุด
        model = genai.GenerativeModel("gemini-1.5-flash-latest")

        with st.status("กำลังดำเนินการวิเคราะห์ร่วมกัน...", expanded=True) as status:
            # 1. Agent A: ร่างข้อมูล
            st.write("📝 1. Agent A กำลังรวบรวมและร่างข้อมูลชุดแรก...")
            draft_prompt = f"""
            คุณคือผู้เชี่ยวชาญด้านการค้นคว้า (Agent A)
            หัวข้อ/คำถาม: {query}
            
            คำสั่ง: ร่างคำตอบที่ละเอียด มีโครงสร้างชัดเจน และครอบคลุมประเด็นสำคัญเป็นภาษาไทย
            """
            res_draft = model.generate_content(draft_prompt)
            draft_text = res_draft.text

            # 2. Agent B: ตรวจทานและสังเคราะห์
            st.write("🔍 2. Agent B กำลังตรวจสอบข้อเท็จจริงและสรุปคำตอบที่ดีที่สุด...")
            audit_prompt = f"""
            คุณคือผู้ตรวจสอบข้อเท็จจริงและบรรณาธิการ (Agent B)
            หัวข้อคำถามเดิม: {query}

            ข้อมูลที่ Agent A ร่างไว้:
            {draft_text}

            คำสั่ง:
            1. ตรวจสอบความถูกต้อง ชี้จุดที่ข้อมูลอาจคลาดเคลื่อน ลำเอียง หรือตกหล่น
            2. กรองข้อมูลที่ไม่สมเหตุสมผลออก
            3. สรุปเป็น "คำตอบสุดท้ายที่ดีที่สุด" ที่ถูกต้อง แม่นยำ และอ่านง่ายที่สุดเป็นภาษาไทย
            """
            res_final = model.generate_content(audit_prompt)
            final_text = res_final.text
            
            status.update(label="ประมวลผลเสร็จสิ้น!", state="complete")

        st.subheader("📌 คำตอบที่ดีและสมบูรณ์ที่สุด:")
        st.markdown(final_text)

        with st.expander("ดูร่างคำตอบแรกจาก Agent A (ก่อนตรวจทาน)"):
            st.markdown(draft_text)
