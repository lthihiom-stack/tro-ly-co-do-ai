import os
import re
import io
import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
import speech_recognition as sr

# 1. Cấu hình trang Web tương thích tốt với cả Điện thoại và Máy tính
st.set_page_config(
    page_title="Trợ Lý Cố Đô AI Pro",
    page_icon="🏯",
    layout="centered"
)

CHI_DAN_HE_THONG = """
Bạn là Trợ lý Cố Đô AI (Phiên bản Web App Chuyên nghiệp), chuyên gia thông thái về lịch sử, văn hóa, du lịch, tâm linh và ẩm thực vùng Hà Nam – Ninh Bình – Nam Định (Cố đô Hoa Lư, Tràng An, Tam Chúc, Phủ Thiên Trường...).
Nhiệm vụ: Tư vấn lịch trình chi tiết, thuyết minh di tích lịch sử, gợi ý đặc sản địa phương và hỗ trợ thông tin du lịch thực tế.
Phong cách: Chuyên nghiệp, mến khách, trình bày rõ ràng, tự nhiên.
"""

# 2. Tự động lấy mã kích hoạt từ hệ thống bảo mật Streamlit Secrets
default_key = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("⚙️ Cài đặt Hệ thống")
    api_key = st.text_input(
        "🔑 Mã Kích Hoạt (Tùy chọn):",
        type="password",
        value=default_key,
        help="Hệ thống đã kích hoạt sẵn cho Ban Giám Khảo."
    )
    bat_loa = st.toggle("🔊 Tự động đọc câu trả lời", value=True)
    if st.button("🔄 Cuộc trò chuyện mới", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 3. Giao diện tiêu đề chính
st.title("🏯 Trợ Lý Cố Đô AI Pro")
st.caption("Khám phá Văn hóa • Lịch sử • Du lịch • Ẩm thực vùng Hà Nam – Ninh Bình – Nam Định")

if not api_key:
    st.warning("⚠️ Hệ thống chưa có Mã Kích Hoạt. Vui lòng mở menu bên trái (>) để nhập mã.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Mình là **Trợ lý Cố Đô AI**. Bạn có thể gõ câu hỏi bên dưới hoặc bấm vào biểu tượng **Micro** để nói chuyện trực tiếp với mình nhé!"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🏯" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# Hàm tạo âm thanh giọng đọc tiếng Việt
def tao_am_thanh(van_ban):
    try:
        van_ban_sach = re.sub(r'[*#_`>-]', ' ', van_ban)
        van_ban_sach = re.sub(r'\s+', ' ', van_ban_sach).strip()
        if not van_ban_sach:
            return None
        mp3_fp = io.BytesIO()
        tts = gTTS(text=van_ban_sach, lang='vi')
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp
    except Exception:
        return None

# Hàm tự động lấy danh sách mô hình Gemini đang hoạt động thực tế từ API Key
@st.cache_data(ttl=3600)
def lay_danh_sach_model_kha_dung(key):
    try:
        c = genai.Client(api_key=key)
        ds = []
        for m in c.models.list():
            ten = m.name.replace("models/", "")
            if "gemini" in ten and "embedding" not in ten and "imagen" not in ten and "veo" not in ten and "aqa" not in ten:
                ds.append(ten)
        # Ưu tiên các dòng flash lên đầu để phản hồi nhanh nhất
        ds.sort(key=lambda x: (0 if "flash" in x else 1, x), reverse=False)
        return ds if ds else ["gemini-2.5-flash", "gemini-2.0-flash"]
    except Exception:
        return ["gemini-2.5-flash", "gemini-2.0-flash"]

# 4. Khu vực nhập liệu 2 chiều (Gõ chữ hoặc Ghi âm trên Điện thoại & Máy tính)
cau_hoi = st.chat_input("Nhập câu hỏi về du lịch, di tích, đặc sản Cố Đô...")
audio_value = st.audio_input("🎤 Hoặc bấm vào biểu tượng Micro để nói câu hỏi:")

if audio_value is not None:
    audio_bytes = audio_value.getvalue()
    if st.session_state.get("last_audio") != audio_bytes:
        st.session_state.last_audio = audio_bytes
        with st.spinner("⏳ Đang nhận diện giọng nói của bạn..."):
            try:
                recognizer = sr.Recognizer()
                with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                    audio_data = recognizer.record(source)
                cau_hoi = recognizer.recognize_google(audio_data, language="vi-VN")
            except Exception:
                st.error("⚠️ Chưa nghe rõ giọng nói, bạn vui lòng bấm ghi âm lại nhé.")

# 5. Xử lý câu hỏi bằng mô hình tự động phát hiện
if cau_hoi:
    st.session_state.messages.append({"role": "user", "content": cau_hoi})
    with st.chat_message("user", avatar="👤"):
        st.markdown(cau_hoi)

    with st.chat_message("assistant", avatar="🏯"):
        with st.spinner("Trợ lý Cố Đô AI đang suy nghĩ..."):
            try:
                client = genai.Client(api_key=api_key)
                noi_dung_gui = [
                    types.Content(
                        role="user" if m["role"] == "user" else "model",
                        parts=[types.Part.from_text(text=m["content"])]
                    )
                    for m in st.session_state.messages
                ]
                
                cac_mo_hinh = lay_danh_sach_model_kha_dung(api_key)
                response = None
                loi_cuoi = ""
                
                for ten_model in cac_mo_hinh:
                    try:
                        response = client.models.generate_content(
                            model=ten_model,
                            contents=noi_dung_gui,
                            config=types.GenerateContentConfig(
                                system_instruction=CHI_DAN_HE_THONG,
                                temperature=0.7
                            )
                        )
                        if response and response.text:
                            break
                    except Exception as e_model:
                        loi_cuoi = str(e_model)
                        continue
                
                if not response or not response.text:
                    raise Exception(loi_cuoi)

                tra_loi = response.text
                st.markdown(tra_loi)
                st.session_state.messages.append({"role": "assistant", "content": tra_loi})

                if bat_loa:
                    audio_stream = tao_am_thanh(tra_loi)
                    if audio_stream:
                        st.audio(audio_stream, format="audio/mp3", autoplay=True)
            except Exception as e:
                st.error(f"❌ Lỗi kết nối máy chủ AI: {e}")
