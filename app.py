import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="MedicAI", page_icon="🩺", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing API Key in Streamlit Secrets!")
    st.stop()

# 1. PREMIUM NATIVE CSS (Popolna prilagoditev sistemski temi uporabnika)
st.markdown("""
    <style>
    .block-container { max-width: 600px !important; padding-top: 3rem !important; }
    
    h1 { text-align: center; font-weight: 800; font-size: 2.4rem; letter-spacing: -0.03em; margin-bottom: 0.5rem; }
    .subtitle { text-align: center; opacity: 0.7; font-size: 1.1rem; margin-bottom: 2.5rem; font-weight: 400; }
    
    div.stTextArea textarea { border-radius: 12px !important; }
    
    /* Premium gumb, ki dinamično spreminja kontrast glede na svetel/temen način */
    .stButton>button {
        background-color: var(--text-color) !important;
        color: var(--background-color) !important;
        width: 100% !important; 
        border-radius: 12px !important; 
        padding: 14px 24px !important; 
        font-weight: 600 !important; 
        font-size: 1.05rem !important;
        border: none !important; 
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        transition: all 0.2s ease;
    }
    
    /* Pametno opozorilo z mehkimi robovi */
    .premium-disclaimer {
        background-color: var(--secondary-background-color); 
        padding: 16px 20px; 
        border-radius: 14px; 
        font-size: 0.9rem; 
        margin-bottom: 25px; 
        border-left: 4px solid var(--text-color);
        opacity: 0.9;
    }
    
    /* Zagotovitev, da Streamlitov Markdown ne bo posilil barv v sivo ali belo */
    [data-testid="stMarkdownContainer"] p, 
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {
        color: var(--text-color) !important;
    }
    
    [data-testid="stSidebar"], [data-testid="stHeader"] { display: none !important; }
    footer { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# 2. STRUKTURA GLOBALNEGA VMESNIKA
st.markdown("<h1>MedicAI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Your global medical interpreter. Fast, simple, and jargon-free.</p>", unsafe_allow_html=True)

# Izbira jezika za razlago (Globalna osnova z možnostjo preklopa)
jezik_razlage = st.selectbox(
    "Output Language / Jezik razlage", 
    ["Preprosta Slovenščina (Prevod izvidov)", "Simple English", "Einfaches Deutsch"], 
    label_visibility="visible"
)

izbira_nacina = st.radio("Input Method", ["📸 Image / Camera", "💬 Text / Question"], horizontal=True, label_visibility="collapsed")

uploaded_file = None
user_question = ""

if "📸" in izbira_nacina:
    uploaded_file = st.file_uploader("Upload report", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    if uploaded_file:
        st.image(Image.open(uploaded_file), caption="Document uploaded successfully", use_container_width=True)
else:
    user_question = st.text_area("Enter text", placeholder="Paste report text or type a question (e.g., Kaj je angina pektoris?)...", height=160, label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

col_left, col_btn, col_right = st.columns([1, 2, 1])
with col_btn:
    analyze_button = st.button("Analyze & Explain")

# Določitev ciljnega jezika za AI prompt
if "Slovenščina" in jezik_razlage:
    target_lang = "Slovenian"
elif "Deutsch" in jezik_razlage:
    target_lang = "German"
else:
    target_lang = "English"

# SISTEMSKI PROMPT Z REGIONALNO INTELIGENCO (Brez lojtric v rezultatu)
SYSTEM_PROMPT = f"""
You are an expert, compassionate global medical assistant. 
Your task is to translate medical reports or answer health questions for a layperson. 
Explain everything very simply, as if explaining to a 12-year-old. 

EXPLAIN EVERYTHING IN THE FOLLOWING LANGUAGE: {target_lang}.

CRITICAL INSTRUCTIONS:
- NEVER provide a diagnosis or prescribe treatment.
- Do NOT use any introductory or concluding remarks. Start directly with the content.
- CRITICAL: Never use hash signs (#) or bold headers that might mess up the rendering theme. Just use plain text for section titles.
- Automatically adapt and explain any regional measurement units (e.g., converting or contextualizing US metric systems if compared to European standards).
- Structure the response into distinct, clear paragraphs with these titles in uppercase:
  SUMMARY
  STABLE VALUES
  IMPORTANT DEVIATIONS & TERMS
  QUESTIONS FOR YOUR DOCTOR
- Use standard hyphens (-) for bullet points.
"""

# 3. AI LOGIKA IN STREMLIT REAL-TIME PRIKAZ
if analyze_button:
    with st.spinner("⏳ MedicAI analyzing document..."):
        try:
            model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)
            
            if "📸" in izbira_nacina and uploaded_file:
                response = model.generate_content([{"mime_type": uploaded_file.type, "data": uploaded_file.read()}, "Analyze and interpret this document thoroughly."])
            elif "💬" in izbira_nacina and user_question:
                response = model.generate_content(user_question)
            else:
                st.warning("Please provide an image or text input.")
                st.stop()
                
            st.markdown("<h2 style='font-weight:700; font-size: 1.5rem; margin-top:20px;'>📋 Report Analysis</h2>", unsafe_allow_html=True)
            st.markdown("""
                <div class='premium-disclaimer'>
                    Disclaimer: This interpretation is for informational purposes only, generated by AI. Always consult your doctor for any medical decisions.
                </div>
            """, unsafe_allow_html=True)
            
            # Čisti izpis - s pomočjo native spremenljivk bo barva 100% pravilna (črna v svetlem, bela v temnem)
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
