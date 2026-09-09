import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="Gemini Multi-Agent Research", layout="centered", page_icon="🧠")

gemini_key = st.secrets.get("GEMINI_API_KEY")

st.title("🧠 Gemini Dual-Agent System")
st.caption("ระบบ 2 Agent ตรวจสอบกันเอง: Agent 1 ร่างข้อมูลเชิงลึก และ Agent 2 ทำหน้าที่วิจารณ์/ตรวจจับข้อผิดพลาด")

query = st.text_area("พิมพ์คำถามหรือหัวข้อที่ต้องการค้นหา:", placeholder="เช่น ข้อดีข้อเสียของรถยนต์ไฟฟ้าเทียบกับรถสันดาป...", height=120)

if st.button("🚀 เริ่มค้นหาและวิเคราะห์", type="primary"):
    if not query.strip():
        st.warning("กรุณาใส่คำถามก่อนครับ")
    elif not gemini_key:
        st.error("ไม่พบ GEMINI_API_KEY ใน Secrets กรุณาตรวจสอบการตั้งค่า")
    else:
        client = genai.Client(api_key=gemini_key)

        with st.status("กำลังดำเนินการวิเคราะห์ร่วมกัน...", expanded=True) as status:
            # Agent 1: Researcher & Drafter
            st.write("📝 1. Agent A (Researcher) กำลังรวบรวมและร่างข้อมูลชุดแรก...")
            draft_prompt = f"คำถาม/หัวข้อ: {query}\n\nหน้าที่ของคุณ: ร่างข้อมูล คำอธิบาย และข้อเท็จจริงอย่างละเอียด เป็นขั้นตอน และครอบคลุมทุกประเด็นสำคัญเป็นภาษาไทย"
            res_draft = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=draft_prompt,
                config=types.GenerateContentConfig(
                    system_instruction="คุณคือนักวิจัยข้อมูลเชิงลึก ค้นหาและเรียบเรียงเนื้อหาอย่างรอบด้าน"
                )
            )
            draft_text = res_draft.text

            # Agent 2: Critique & Synthesizer
            st.write("🔍 2. Agent B (Fact-Checker & Auditor) กำลังตรวจสอบข้อผิดพลาดและสังเคราะห์ข้อมูล...")
            synthesis_prompt = f"""
            หัวข้อคำถามของผู้ใช้: {query}

            ร่างคำตอบที่ Agent A จัดทำขึ้น:
            {draft_text}

            หน้าที่ของคุณ:
            1. ตรวจสอบความถูกต้อง ชี้จุดที่ข้อมูลอาจคลาดเคลื่อน ลำเอียง หรือตกหล่น
            2. กรองข้อมูลที่ไม่สมเหตุสมผลออก
            3. สรุปเป็น "คำตอบสุดท้ายที่ดีที่สุด" ที่ถูกต้อง แม่นยำ และอ่านง่ายที่สุดเป็นภาษาไทย
            """
            res_final = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=synthesis_prompt,
                config=types.GenerateContentConfig(
                    system_instruction="คุณคือผู้ตรวจสอบข้อเท็จจริง (Fact-Checker) และบรรณาธิการ มีหน้าที่คัดกรองความผิดพลาดและเรียบเรียงคำตอบที่เชื่อถือได้สูงสุด"
                )
            )
            final_text = res_final.text
            status.update(label="ประมวลผลเสร็จสิ้น!", state="complete")

        # แสดงผลลัพธ์
        st.subheader("📌 คำตอบที่ดีและสมบูรณ์ที่สุด (ผ่านการตรวจสอบแล้ว):")
        st.markdown(final_text)

        with st.expander("ดูร่างคำตอบแรกจาก Agent A (ก่อนตรวจทาน)"):
            st.markdown(draft_text)
