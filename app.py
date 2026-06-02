import streamlit as st
import requests
import base64
from PIL import Image
import io

st.set_page_config(
    page_title="MedicAI",
    page_icon="🩺",
    layout="centered"
)

# Prevzem varnostnega ključa
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("Missing API Key in Streamlit Secrets!")
    st.stop()

# 1. INTERAKTIVNA IZBIRA JEZIKA (Brez izbire teme - zacementiran Dark Mode)
jezik_razlage = st.selectbox(
    "Jezik razlage",
    ["Preprosta Slovenščina (Prevod izvidov)", "Simple English", "Einfaches Deutsch"],
    label_visibility="collapsed"
)

# Fiksna paleta za luksuzen Temen način (Premium Dark Mode)
bg_app = "#0f172a"
bg_card = "#1e293b"
text_main = "#f8fafc"
text_muted = "#94a3b8"
border_color = "#334155"
input_text = "#ffffff"
btn_bg = "#ffffff"
btn_text = "#0f172a"
txt_barva = "#ffffff"

# 2. PREMIUM LUKSUZNI CSS
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_app} !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    .block-container {{ max-width: 600px !important; padding-top: 2rem !important; }}
    
    h1 {{ color: {text_main} !important; text-align: center; font-weight: 800; font-size: 2.4rem; letter-spacing: -0.03em; margin-bottom: 0.5rem; }}
    .subtitle {{ text-align: center; color: {text_muted} !important; font-size: 1.1rem; margin-bottom: 2.5rem; font-weight: 400; }}
    
    div.stTextArea textarea {{
        color: {input_text} !important; background-color: {bg_card} !important; border: 1px solid {border_color} !important;
        border-radius: 14px !important; padding: 15px !important;
    }}
    
    .stButton>button {{
        background-color: {btn_bg} !important; color: {btn_text} !important; width: 100% !important; border-radius: 14px !important; 
        padding: 14px 24px !important; font-weight: 600 !important; font-size: 1.05rem !important; border: none !important; 
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1) !important; transition: all 0.25s ease !important;
    }}
    .stButton>button:hover {{ transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15) !important; }}
    .stButton>button p {{ color: {btn_text} !important; font-weight: 600 !important; margin: 0 !important; }}
    
    .premium-disclaimer {{
        background-color: {bg_card}; padding: 16px 20px; border-radius: 14px; border: 1px solid {border_color}; 
        color: {text_muted}; font-size: 0.85rem; margin-bottom: 25px; line-height: 1.5;
    }}
    
    [data-testid="stSidebar"], [data-testid="stSidebarCollapseButton"], [data-testid="stHeader"] {{ display: none !important; }}
    footer {{ visibility: hidden; }}
    </style>
""", unsafe_allow_html=True)

# 3. STRUKTURA VMESNIKA
st.markdown("<h1>MedicAI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Vaš osebni zdravstveni tolmač. Hitro, preprosto in v laičnem jeziku.</p>", unsafe_allow_html=True)

izbira_nacina = st.radio("Način vnosa", ["📸 Slika / Kamera", "💬 Kopiranje teksta / Vprašanje"], horizontal=True, label_visibility="collapsed")

uploaded_file = None
user_question = ""

if "📸" in izbira_nacina:
    uploaded_file = st.file_uploader("Naložite sliko", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    if uploaded_file:
        st.image(Image.open(uploaded_file), caption="Dokument uspešno naložen", use_container_width=True)
else:
    user_question = st.text_area("Vnesite tekst", placeholder="Sem prilepite besedilo izvida ali vpisite zdravstveno težavo (npr. Kaj je angina pektoris?)...", height=160, label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

col_left, col_btn, col_right = st.columns([1, 2, 1])
with col_btn:
    analyze_button = st.button("Analiziraj in razloži")

if "Slovenščina" in jezik_razlage:
    target_lang = "Slovenian"
elif "Deutsch" in jezik_razlage:
    target_lang = "German"
else:
    target_lang = "English"

SYSTEM_PROMPT = f"""
Si vrhunski, sočuten medicinski asistent. 
Tvoja naloga je, da pacientu (laiku) prevedeš medicinski izvid ali odgovoriš na zdravstveno vprašanje. Vse natančno RAZLOŽI V JEZIKU: {target_lang}.
NIKOLI ne postavljaj diagnoze in ne predpisuj zdravljenja.
Ne uporabljaj nobenih uvodnih fraz. Začni neposredno z vsebino.
PREPOVEDANO: Nikoli ne uporabljaj lojtric (#) na začetku vrstic.
Odgovor razdeli v naslednja poglavja z VELIKIMI ČRKAMI:
POGLAVJE: KRATEK POVZETEK
POGLAVJE: STABILNE VREDNOSTI
POGLAVJE: POMEMBNA ODSTOPANJA IN IZRAZI
POGLAVJE: VPRAŠANJA ZA VAŠEGA ZDRAVNIKA
Za alineje uporabljaj standardni znak minus (-).
"""

# 4. NEPREBOJNI ZDRUŽENI HTTP KLIC Z MODELOM GEMINI-2.5-FLASH
if analyze_button:
    with st.spinner("⏳ MedicAI natančno preučuje dokument..."):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
            headers = {"Content-Type": "application/json"}
            
            full_prompt = f"NAVODILA ZA UMETNO INTELIGENCO:\n{SYSTEM_PROMPT}\n\nVPRAŠANJE/ZAHTEVA UPORABNIKA:\n"
            
            contents_payload = []
            
            if "📸" in izbira_nacina and uploaded_file:
                img_bytes = uploaded_file.read()
                base64_image = base64.b64encode(img_bytes).decode('utf-8')
                full_prompt += "Natančno preuči to sliko in jo laično razloži."
                contents_payload = [
                    {
                        "parts": [
                            {"inlineData": {"mimeType": uploaded_file.type, "data": base64_image}},
                            {"text": full_prompt}
                        ]
                    }
                ]
            elif "💬" in izbira_nacina and user_question:
                full_prompt += user_question
                contents_payload = [{"parts": [{"text": full_prompt}]}]
            else:
                st.warning("Prosim, vnesite tekst ali naložite sliko.")
                st.stop()
                
            payload = {
                "contents": contents_payload,
                "generationConfig": {"temperature": 0.2}
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response_json = response.json()
            
            if 'error' in response_json:
                st.error(f"Googlova napaka: {response_json['error'].get('message', 'Neznano obvestilo')}")
                st.stop()
                
            if 'candidates' not in response_json or not response_json['candidates']:
                st.error("Strežnik ni vrnil odgovora. Prosimo, poskusite znova.")
                st.stop()
                
            ai_odgovor = response_json['candidates'][0]['content']['parts'][0]['text']
            
            st.markdown(f"<h2 style='color: {text_main}; font-weight:700; font-size: 1.5rem; margin-top:20px;'>📋 Poročilo analize</h2>", unsafe_allow_html=True)
            st.markdown(f"""
                <div class='premium-disclaimer'>
                    <b>Opozorilo:</b> Razlaga je informativne narave, generirana z napredno umetno inteligenco MedicAI. Za kakršne koli zdravstvene odločitve se obvezno posvetujte s svojim zdravnikom.
                </div>
            """, unsafe_allow_html=True)
            
            html_rezultat = "<div style='margin-top: 15px; padding: 5px;'>"
            znotraj_seznama = False
            
            for line in ai_odgovor.split('\n'):
                vrstica = line.replace('#', '').strip()
                if not vrstica:
                    if znotraj_seznama:
                        html_rezultat += "</ul>"
                        znotraj_seznama = False
                    continue
                
                if "POGLAVJE:" in vrstica:
                    if znotraj_seznama:
                        html_rezultat += "</ul>"
                        znotraj_seznama = False
                    naslov_tekst = vrstica.replace("POGLAVJE:", "").strip()
                    html_rezultat += f"<p style='color: {txt_barva} !important; font-weight: 700 !important; font-size: 1.35rem !important; margin-top: 1.8rem !important; margin-bottom: 0.6rem !important; font-family: -apple-system, sans-serif;'>{naslov_tekst}</p>"
                    
                elif vrstica.endswith('?') and len(vrstica) < 80:
                    if znotraj_seznama:
                        html_rezultat += "</ul>"
                        znotraj_seznama = False
                    html_rezultat += f"<p style='color: {txt_barva} !important; font-weight: 700 !important; font-size: 1.25rem !important; margin-top: 1.5rem !important; margin-bottom: 0.5rem !important; font-family: -apple-system, sans-serif;'>{vrstica}</p>"
                    
                elif vrstica.startswith("-") or vrstica.startswith("*"):
                    if not znotraj_seznama:
                        html_rezultat += f"<ul style='padding-left: 20px !important; margin-top: 0 !important; margin-bottom: 1rem !important; color: {txt_barva} !important;'>"
                        znotraj_seznama = True
                    item_tekst = vrstica.lstrip("-* ").strip()
                    
                    if "**" in item_tekst:
                        d = item_tekst.split("**")
                        for i in range(1, len(d), 2):
                            d[i] = f"<strong style='color: {txt_barva} !important; font-weight: 700;'>{d[i]}</strong>"
                        item_tekst = "".join(d)
                        
                    html_rezultat += f"<li style='color: {txt_barva} !important; font-size: 1.05rem !important; margin-bottom: 0.5rem !important; font-family: -apple-system, sans-serif;'>{item_tekst}</li>"
                    
                else:
                    if znotraj_seznama:
                        html_rezultat += "</ul>"
                        znotraj_seznama = False
                    p_tekst = vrstica
                    if "**" in p_tekst:
                        d = p_tekst.split("**")
                        for i in range(1, len(d), 2):
                            d[i] = f"<strong style='color: {txt_barva} !important; font-weight: 700;'>{d[i]}</strong>"
                        p_tekst = "".join(d)
                    html_rezultat += f"<p style='color: {txt_barva} !important; font-size: 1.05rem !important; line-height: 1.7 !important; margin-bottom: 1rem !important; font-family: -apple-system, sans-serif;'>{p_tekst}</p>"
                    
            if znotraj_seznama:
                html_rezultat += "</ul>"
                
            html_rezultat += "</div>"
            st.markdown(html_rezultat, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Prišlo je do napake znotraj aplikacije: {e}")
