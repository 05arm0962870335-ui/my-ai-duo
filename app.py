import streamlit as st
from openai import OpenAI
from google import genai

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="AI Research Duo", layout="centered", page_icon="🤖")

# ดึง Key จากระบบหลังบ้าน
openai_api_key = st.secrets.get("OPENAI_API_KEY")
gemini_api_key = st.secrets.get("GEMINI_API_KEY")

st.title("🤖 AI Duo: Research & Debate")
st.caption("ส่งคำถามครั้งเดียว ให้ ChatGPT ร่างข้อมูล และ Gemini ช่วยตรวจทานเพื่อคำตอบที่ดีที่สุด")

query = st.text_area("พิมพ์คำถามหรือหัวข้อที่ต้องการค้นหา:", placeholder="เช่น เปรียบเทียบข้อดีข้อเสียของ...", height=120)

if st.button("🚀 เริ่มค้นหาและวิเคราะห์", type="primary"):
    if not query.strip():
        st.warning("กรุณาใส่คำถามก่อนครับ")
    elif not openai_api_key or not gemini_api_key:
        st.error("ยังไม่ได้ใส่ API Key ในระบบหลังบ้าน กรุณาตรวจสอบการตั้งค่า Secrets")
    else:
        with st.status("กำลังดำเนินการวิเคราะห์ร่วมกัน...", expanded=True) as status:
            # 1. ChatGPT เริ่มค้นคว้าและร่างคำตอบแรก
            st.write("🤖 1. ChatGPT กำลังร่างข้อมูลชุดแรก...")
            client_openai = OpenAI(api_key=openai_api_key)
            gpt_response = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "คุณคือผู้ช่วยค้นคว้า ให้ข้อมูลที่ละเอียด ชัดเจน และมีโครงสร้างที่ดี"},
                    {"role": "user", "content": query}
                ]
            )
            gpt_draft = gpt_response.choices[0].message.content

            # 2. ส่งให้ Gemini ตรวจสอบและสังเคราะห์คำตอบที่ดีที่สุด
            st.write("🔍 2. Gemini กำลังตรวจสอบความถูกต้องและข้อเท็จจริง...")
            client_gemini = genai.Client(api_key=gemini_api_key)
            
            synthesis_prompt = f"""
            หัวข้อ/คำถาม: {query}
            
            ข้อมูลที่ร่างโดย AI อีกตัวหนึ่ง:
            {gpt_draft}
            
            หน้าที่ของคุณ:
            1. ตรวจสอบข้อเท็จจริงว่ามีจุดใดคลาดเคลื่อนหรือล้าสมัยหรือไม่
            2. รวมมุมมองที่ขาดตกบกพร่อง
            3. สรุปเป็น "คำตอบสุดท้ายที่ดีที่สุด" ที่ถูกต้อง ครบถ้วน และอ่านเข้าใจง่ายที่สุด
            """
            
            gemini_res = client_gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=synthesis_prompt
            )
            final_answer = gemini_res.text
            status.update(label="ประมวลผลเสร็จสิ้น!", state="complete")

        # แสดงผลลัพธ์
        st.subheader("📌 คำตอบที่ดีและสมบูรณ์ที่สุด:")
        st.markdown(final_answer)

        # เมนูพับเก็บดูการโต้แย้ง
        with st.expander("ดูร่างคำตอบแรกจาก ChatGPT"):
            st.markdown(gpt_draft)
