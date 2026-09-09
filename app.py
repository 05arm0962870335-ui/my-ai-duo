import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Gemini Multi-Agent Research", layout="centered", page_icon="🧠")

gemini_key = st.secrets.get("GEMINI_API_KEY")

st.title("🧠 Gemini Dual-Agent System")
st.caption("ระบบ 2 Agent ค้นคว้าและตรวจสอบข้อเท็จจริงอัตโนมัติ")

query = st.text_area("พิมพ์คำถามหรือหัวข้อที่ต้องการค้นหา:", placeholder="เช่น ข้อดีข้อเสียของรถยนต์ไฟฟ้า...", height=120)

if st.button("🚀 เริ่มค้นหาและวิเคราะห์", type="primary"):
    if not query.strip():
        st.warning("กรุณากรอกข้อความก่อนกดค้นหาครับ")
    elif not gemini_key:
        st.error("ไม่พบคีย์ GEMINI_API_KEY ใน Secrets")
    else:
        genai.configure(api_key=gemini_key.strip())

        with st.status("กำลังดำเนินการ...", expanded=True) as status:
            # 1. ค้นหาโมเดลที่คีย์นี้มีสิทธิ์ใช้งานได้จริงโดยอัตโนมัติ
            st.write("🔍 ตรวจสอบโมเดลที่พร้อมใช้งานในบัญชีของคุณ...")
            available_models = [
                m.name for m in genai.list_models() 
                if 'generateContent' in m.supported_generation_methods
            ]
            
            if not available_models:
                st.error("ไม่พบโมเดลที่รองรับข้อความใน API Key นี้")
                st.stop()

            # เลือกโมเดลตัวแรกที่พร้อมใช้งาน
            chosen_model_name = available_models[0]
            for m in available_models:
                if "flash" in m:
                    chosen_model_name = m
                    break
            
            st.write(f"✅ เลือกใช้โมเดล: `{chosen_model_name}`")
            model = genai.GenerativeModel(chosen_model_name)

            # 2. Agent A: ร่างข้อมูล
            st.write("📝 Agent A กำลังรวบรวมและร่างข้อมูลชุดแรก...")
            draft_prompt = f"คำถาม/หัวข้อ: {query}\n\nหน้าที่ของคุณ: ร่างข้อมูลและข้อเท็จจริงอย่างละเอียด เป็นโครงสร้างชัดเจนเป็นภาษาไทย"
            res_draft = model.generate_content(draft_prompt)
            draft_text = res_draft.text

            # 3. Agent B: ตรวจสอบและสรุป
            st.write("🔍 Agent B กำลังตรวจสอบความถูกต้องและสังเคราะห์คำตอบ...")
            audit_prompt = f"""
            หัวข้อ: {query}
            
            ข้อมูลที่ร่างไว้:
            {draft_text}
            
            หน้าที่ของคุณ:
            1. ตรวจสอบความถูกต้อง ชี้จุดที่ข้อมูลอาจคลาดเคลื่อนหรือตกหล่น
            2. เรียบเรียงเป็นคำตอบสุดท้ายที่ดีที่สุด ถูกต้อง และอ่านง่ายที่สุดเป็นภาษาไทย
            """
            res_final = model.generate_content(audit_prompt)
            final_text = res_final.text

            status.update(label="ประมวลผลเสร็จสิ้น!", state="complete")

        st.subheader("📌 คำตอบที่ดีและสมบูรณ์ที่สุด:")
        st.markdown(final_text)

        with st.expander("ดูร่างคำตอบแรกจาก Agent A (ก่อนตรวจทาน)"):
            st.markdown(draft_text)
