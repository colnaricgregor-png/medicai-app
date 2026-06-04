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

if "pozdrav_prikazan" not in st.session_state:
    st.toast("👋 **Dobrodošli v MedicAI!**\n\nNaložite sliko ali PDF izvida ali preprosto vprašajte, kaj vas zanima.", icon="🩺")
    st.session_state.pozdrav_prikazan = True

if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("Missing API Key in Streamlit Secrets!")
    st.stop()

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
API_HEADERS = {"Content-Type": "application/json"}

bg_app = "#0f172a"
bg_card = "#1e293b"
text_main = "#f8fafc"
text_muted = "#94a3b8"
border_color = "#334155"
input_text = "#ffffff"
btn_bg = "#ffffff"
btn_text = "#0f172a"
txt_barva = "#ffffff"

st.markdown(f"""
    <style>
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(15px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .stApp {{ 
        background-color: {bg_app} !important; 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
        animation: fadeIn 0.8s ease-out;
    }}
    
    .block-container {{ max-width: 650px !important; padding-top: 3rem !important; padding-bottom: 100px !important; }}
    
    h1 {{ color: {text_main} !important; text-align: center; font-weight: 800; font-size: 2.6rem; letter-spacing: -0.03em; margin-bottom: 0.2rem; }}
    .subtitle {{ text-align: center; color: {text_muted} !important; font-size: 1.1rem; margin-bottom: 3rem; font-weight: 400; line-height: 1.5; }}
    
    div.stTextArea textarea {{
        color: {input_text} !important; background-color: {bg_card} !important; border: 1px solid {border_color} !important;
        border-radius: 16px !important; padding: 18px !important; font-size: 1.05rem !important;
        transition: all 0.3s ease !important;
    }}
    div.stTextArea textarea:focus {{
        border-color: #64748b !important;
        box-shadow: 0 0 0 2px rgba(100, 116, 139, 0.2) !important;
    }}
    
    .stButton>button {{
        background-color: {btn_bg} !important; color: {btn_text} !important; width: 100% !important; border-radius: 16px !important; 
        padding: 16px 24px !important; font-weight: 700 !important; font-size: 1.1rem !important; border: none !important; 
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1) !important; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    .stButton>button:hover {{ 
        transform: translateY(-3px) !important; 
        box-shadow: 0 10px 25px rgba(255, 255, 255, 0.15) !important; 
        background-color: #f1f5f9 !important;
    }}
    .stButton>button p {{ color: {btn_text} !important; font-weight: 700 !important; margin: 0 !important; }}
    
    .premium-disclaimer {{
        background-color: {bg_card}; padding: 18px 24px; border-radius: 16px; border: 1px solid {border_color}; 
        color: {text_muted}; font-size: 0.9rem; margin-bottom: 30px; line-height: 1.6;
        border-left: 4px solid #3b82f6;
    }}
    
    /* 3. PROSOJEN IN CENTRIRAN CHAT INPUT */
    .stChatFloatingInputContainer {{
        background: transparent !important;
    }}
    div[data-testid="stChatInput"] {{
        background-color: rgba(30, 41, 59, 0.75) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid {border_color} !important;
        border-radius: 24px !important;
        max-width: 650px !important;
        margin: 0 auto !important;
        padding: 5px !important;
    }}
    
    [data-testid="stSidebar"], [data-testid="stSidebarCollapseButton"], [data-testid="stHeader"] {{ display: none !important; }}
    footer {{ visibility: hidden; }}
    </style>
""", unsafe_allow_html=True)

def formatiraj_izvid_v_html(tekst_odgovora):
    html_rezultat = "<div style='margin-top: 15px; padding: 5px; animation: fadeIn 0.6s ease-out;'>"
    znotraj_seznama = False
    
    for line in tekst_odgovora.split('\n'):
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
            html_rezultat += f"<p style='color: {txt_barva} !important; font-weight: 700 !important; font-size: 1.35rem !important; margin-top: 2rem !important; margin-bottom: 0.8rem !important; font-family: -apple-system, sans-serif; letter-spacing: 0.02em;'>{naslov_tekst}</p>"
            
        elif vrstica.endswith('?') and len(vrstica) < 80:
            if znotraj_seznama:
                html_rezultat += "</ul>"
                znotraj_seznama = False
            html_rezultat += f"<p style='color: {txt_barva} !important; font-weight: 700 !important; font-size: 1.25rem !important; margin-top: 1.5rem !important; margin-bottom: 0.5rem !important; font-family: -apple-system, sans-serif;'>{vrstica}</p>"
            
        elif vrstica.startswith("-") or vrstica.startswith("*"):
            if not znotraj_seznama:
                html_rezultat += f"<ul style='padding-left: 20px !important; margin-top: 0 !important; margin-bottom: 1.2rem !important; color: {text_muted} !important;'>"
                znotraj_seznama = True
            item_tekst = vrstica.lstrip("-* ").strip()
            
            if "**" in item_tekst:
                d = item_tekst.split("**")
                for i in range(1, len(d), 2):
                    d[i] = f"<strong style='color: {txt_barva} !important; font-weight: 600;'>{d[i]}</strong>"
                item_tekst = "".join(d)
                
            html_rezultat += f"<li style='color: {text_main} !important; font-size: 1.05rem !important; margin-bottom: 0.6rem !important; font-family: -apple-system, sans-serif; line-height: 1.6;'>{item_tekst}</li>"
            
        else:
            if znotraj_seznama:
                html_rezultat += "</ul>"
                znotraj_seznama = False
            p_tekst = vrstica
            if "**" in p_tekst:
                d = p_tekst.split("**")
                for i in range(1, len(d), 2):
                    d[i] = f"<strong style='color: {txt_barva} !important; font-weight: 600;'>{d[i]}</strong>"
                p_tekst = "".join(d)
            html_rezultat += f"<p style='color: {text_muted} !important; font-size: 1.05rem !important; line-height: 1.7 !important; margin-bottom: 1.2rem !important; font-family: -apple-system, sans-serif;'>{p_tekst}</p>"
            
    if znotraj_seznama:
        html_rezultat += "</ul>"
        
    html_rezultat += "</div>"
    return html_rezultat

if "api_history" not in st.session_state:
    st.session_state.api_history = []  
if "ui_history" not in st.session_state:
    st.session_state.ui_history = []   

st.markdown("<h1>MedicAI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Vaš osebni zdravstveni tolmač.<br>Hitro, preprosto in v laičnem jeziku.</p>", unsafe_allow_html=True)

izbira_nacina = st.radio("Način vnosa", ["📄 Datoteka / Slika", "💬 Besedilo / Vprašanje"], horizontal=True, label_visibility="collapsed")

uploaded_file = None
user_question = ""

if "📄" in izbira_nacina:
    uploaded_file = st.file_uploader("Naložite izvid", type=["png", "jpg", "jpeg", "pdf"], label_visibility="collapsed")
    if uploaded_file:
        # 1. ODSTRANJENA ST.IMAGE LOGIKA - Izpiše samo uspeh
        st.success(f"📄 Dokument '{uploaded_file.name}' uspešno naložen!")
else:
    user_question = st.text_area("Vnesite tekst", placeholder="Sem prilepite besedilo izvida ali vpisite zdravstveno težavo...", height=160, label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

col_left, col_btn, col_right = st.columns([1, 2, 1])
with col_btn:
    analyze_button = st.button("Analiziraj in razloži")

# 4. DODAN STROGI FILTER ZA NE-MEDICINSKE SLIKE (Pse, avte itd.)
SYSTEM_PROMPT = """
Si vrhunski, sočuten medicinski asistent. 
TVOJA GLAVNA NALOGA: Samodejno zaznaj jezik, v katerem te uporabnik nagovarja ali sprašuje. 

POMEMBNO VARNOSTNO PRAVILO:
Če uporabnik naloži sliko ali tekst, ki očitno NI povezan z medicino (npr. slike živali, narave, računov iz trgovine, naključnih predmetov), 
odgovori SAMO IN IZKLJUČNO s tem natančnim stavkom: "NAPAKA: Datoteka ni medicinske narave. Prosimo, naložite veljaven zdravstveni izvid."
V tem primeru NE UPORABLJAJ nobenih poglavij ali dodatnih razlag! Zapiši samo ta en stavek.

STRIKTNA NAVODILA ZA STRUKTURO (Samo za prave izvide):
- NIKOLI ne postavljaj diagnoze in ne predpisuj zdravljenja.
- Vse razloži v zelo preprostem, laičnem jeziku.
- Ne uporabljaj nobenih uvodnih fraz. Začni neposredno z vsebino.
- PREPOVEDANO: Nikoli ne uporabljaj lojtric (#) na začetku vrstic.
- Odgovor razdeli v naslednja poglavja z VELIKIMI ČRKAMI:
  POGLAVJE: KRATEK POVZETEK
  POGLAVJE: STABILNE VREDNOSTI
  POGLAVJE: POMEMBNA ODSTOPANJA IN IZRAZI
  POGLAVJE: VPRAŠANJA ZA VAŠEGA ZDRAVNIKA
- Za alineje uporabljaj standardni znak minus (-).
"""

if analyze_button:
    st.session_state.api_history = []
    st.session_state.ui_history = []
    
    with st.spinner("⏳ MedicAI preučuje vaše podatke..."):
        try:
            full_prompt = f"NAVODILA ZA UMETNO INTELIGENCO:\n{SYSTEM_PROMPT}\n\nVPRAŠANJE/ZAHTEVA UPORABNIKA:\n"
            
            parts_array = []
            if "📄" in izbira_nacina and uploaded_file:
                if uploaded_file.type == "application/pdf":
                    file_bytes = uploaded_file.read()
                    koncni_mime = "application/pdf"
                else:
                    slika = Image.open(uploaded_file)
                    if slika.mode != 'RGB':
                        slika = slika.convert('RGB')
                    slika.thumbnail((2000, 2000))
                    b_io = io.BytesIO()
                    slika.save(b_io, format='JPEG', quality=85)
                    file_bytes = b_io.getvalue()
                    koncni_mime = "image/jpeg"

                base64_file = base64.b64encode(file_bytes).decode('utf-8')
                full_prompt += "Natančno preuči priložen dokument (ali sliko) in ga laično razloži v mojem jeziku."
                
                parts_array = [
                    {"inlineData": {"mimeType": koncni_mime, "data": base64_file}},
                    {"text": full_prompt}
                ]
            elif "💬" in izbira_nacina and user_question:
                full_prompt += user_question
                parts_array = [{"text": full_prompt}]
            else:
                st.warning("Prosim, vnesite tekst ali naložite dokument.")
                st.stop()
            
            st.session_state.api_history.append({"role": "user", "parts": parts_array})
            
            payload = {
                "contents": st.session_state.api_history,
                "generationConfig": {"temperature": 0.2}
            }
            response = requests.post(API_URL, headers=API_HEADERS, json=payload)
            response_json = response.json()
            
            if 'error' in response_json:
                st.error(f"Googlova napaka: {response_json['error'].get('message', 'Neznano obvestilo')}")
                st.stop()
            
            ai_odgovor = response_json['candidates'][0]['content']['parts'][0]['text']
            
            st.session_state.api_history.append({"role": "model", "parts": [{"text": ai_odgovor}]})
            st.session_state.ui_history.append({"role": "assistant", "content": ai_odgovor, "is_main_report": True})
            
        except Exception as e:
            st.error(f"Prišlo je do napake znotraj aplikacije: {e}")

for msg in st.session_state.ui_history:
    # 2. DODELITEV PREMIUM AVATARJEV
    trenutni_avatar = "👤" if msg["role"] == "user" else "🩺"
    
    with st.chat_message(msg["role"], avatar=trenutni_avatar):
        if msg.get("is_main_report", False):
            # Preverimo, če je AI vrnil napako za sliko psa/neumnosti
            if "NAPAKA: Datoteka ni medicinske narave" in msg["content"]:
                st.warning("Datoteka ni medicinske narave. Prosimo, naložite veljaven zdravstveni izvid.")
            else:
                st.markdown(f"<h2 style='color: {text_main}; font-weight:800; font-size: 1.6rem; margin-top:30px; letter-spacing:-0.02em;'>📋 Poročilo analize</h2>", unsafe_allow_html=True)
                st.markdown(f"""
                    <div class='premium-disclaimer'>
                        <b>Opozorilo:</b> Razlaga je informativne narave, generirana z napredno umetno inteligenco MedicAI. Za kakršne koli zdravstvene odločitve se obvezno posvetujte s svojim zdravnikom.
                    </div>
                """, unsafe_allow_html=True)
                oblikovan_html = formatiraj_izvid_v_html(msg["content"])
                st.markdown(oblikovan_html, unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

if len(st.session_state.api_history) > 0:
    if prompt := st.chat_input("Vnesite vprašanje glede vašega izvida..."):
        
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
            
        st.session_state.ui_history.append({"role": "user", "content": prompt})
        st.session_state.api_history.append({"role": "user", "parts": [{"text": prompt}]})
        
        with st.chat_message("assistant", avatar="🩺"):
            with st.spinner("⏳ Pripravljam odgovor..."):
                payload = {
                    "contents": st.session_state.api_history,
                    "generationConfig": {"temperature": 0.2}
                }
                response = requests.post(API_URL, headers=API_HEADERS, json=payload)
                response_json = response.json()
                
                if 'error' not in response_json:
                    ai_odgovor = response_json['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(ai_odgovor)
                    
                    st.session_state.api_history.append({"role": "model", "parts": [{"text": ai_odgovor}]})
                    st.session_state.ui_history.append({"role": "assistant", "content": ai_odgovor, "is_main_report": False})
                else:
                    st.error("Napaka pri klepetu. Poskusite znova.")
