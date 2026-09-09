import streamlit as st
from openai import OpenAI
from google import genai

st.set_page_config(page_title="AI Research Duo (Free)", layout="centered", page_icon="🤖")

openrouter_key = st.secrets.get("OPENROUTER_API_KEY")
gemini_key = st.secrets.get("GEMINI_API_KEY")

st.title("🤖 AI Duo: Multi-Agent Research")
st.caption("ระบบผสานสองโมเดล: ค้นคว้า ร่างข้อมูล และตรวจสอบความถูกต้อง")

query = st.text_area("พิมพ์คำถามหรือหัวข้อที่ต้องการค้นหา:", placeholder="เช่น เปรียบเทียบข้อดีข้อเสียของ...", height=120)

if st.button("🚀 เริ่มค้นหาและวิเคราะห์", type="primary"):
    if not query.strip():
        st.warning("กรุณาใส่คำถามก่อนครับ")
    elif not openrouter_key or not gemini_key:
        st.error("ยังไม่ได้ตั้งค่า API Key ใน Secrets ให้ครบถ้วน")
    else:
        with st.status("กำลังดำเนินการวิเคราะห์ร่วมกัน...", expanded=True) as status:
            # 1. ร่างข้อมูลผ่าน OpenRouter
            st.write("🧠 1. กำลังคิดวิเคราะห์และร่างข้อมูลชุดแรก...")
            client_openrouter = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
                default_headers={
                    "HTTP-Referer": "https://streamlit.app",
                    "X-Title": "AI Research Duo",
                }
            )
            response_draft = client_openrouter.chat.completions.create(
                model="deepseek/deepseek-r1:free",
                messages=[
                    {"role": "system", "content": "คุณคือผู้เชี่ยวชาญด้านการค้นคว้า ให้ข้อมูลที่ละเอียด ชัดเจน และมีโครงสร้างที่ดีเป็นภาษาไทย"},
                    {"role": "user", "content": query}
                ]
            )
            initial_draft = response_draft.choices[0].message.content

            # 2. ให้ Gemini สังเคราะห์และตรวจทาน
            st.write("🔍 2. Gemini กำลังตรวจสอบข้อเท็จจริงและสรุปคำตอบที่ดีที่สุด...")
            client_gemini = genai.Client(api_key=gemini_key)
            
            synthesis_prompt = f"""
            หัวข้อ/คำถาม: {query}
            
            ข้อมูลที่ร่างโดย AI ตัวแรก:
            {initial_draft}
            
            หน้าที่ของคุณ:
            1. ตรวจสอบข้อเท็จจริงว่ามีจุดใดคลาดเคลื่อน ลำเอียง หรือล้าสมัยหรือไม่
            2. เพิ่มมุมมองหรือข้อมูลเชิงลึกที่ตกหล่น
            3. สรุปเป็น "คำตอบสุดท้ายที่ดีที่สุด" ที่ถูกต้อง ครบถ้วน และอ่านเข้าใจง่ายที่สุดเป็นภาษาไทย
            """
            
            gemini_res = client_gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=synthesis_prompt
            )
            final_answer = gemini_res.text
            status.update(label="ประมวลผลเสร็จสิ้น!", state="complete")

        st.subheader("📌 คำตอบที่ดีและสมบูรณ์ที่สุด:")
        st.markdown(final_answer)

        with st.expander("ดูร่างคำตอบแรก"):
            st.markdown(initial_draft)
