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

# --- 1. INICIALIZACIJA POSLOVNE LOGIKE ---
if "pozdrav_prikazan" not in st.session_state:
    st.toast("👋 **Dobrodošli v MedicAI!**\n\nNaložite izvid ali vpišite vprašanje.", icon="🩺")
    st.session_state.pozdrav_prikazan = True

if "api_history" not in st.session_state: st.session_state.api_history = []  
if "ui_history" not in st.session_state: st.session_state.ui_history = []   
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "izvid_odklenjen" not in st.session_state: st.session_state.izvid_odklenjen = False
if "free_messages_used" not in st.session_state: st.session_state.free_messages_used = 0

if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("Missing API Key in Streamlit Secrets!")
    st.stop()

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
API_HEADERS = {"Content-Type": "application/json"}

# --- 2. PREMIUM CSS ---
bg_app = "#0f172a"
bg_card = "#1e293b"
text_main = "#f8fafc"
text_muted = "#94a3b8"
border_color = "#334155"
input_text = "#ffffff"
txt_barva = "#ffffff"

st.markdown(f"""
    <style>
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(15px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    .stApp {{ background-color: {bg_app} !important; font-family: -apple-system, sans-serif; animation: fadeIn 0.8s ease-out; }}
    .block-container {{ max-width: 650px !important; padding-top: 3rem !important; padding-bottom: 100px !important; }}
    h1 {{ color: {text_main} !important; text-align: center; font-weight: 800; font-size: 2.6rem; margin-bottom: 0.2rem; }}
    .subtitle {{ text-align: center; color: {text_muted} !important; font-size: 1.1rem; margin-bottom: 3rem; }}
    
    /* Input polja */
    div.stTextArea textarea {{
        color: {input_text} !important; background-color: {bg_card} !important; border: 1px solid {border_color} !important;
        border-radius: 16px !important; padding: 18px !important; transition: all 0.3s ease !important;
    }}
    
    /* File uploader dizajn */
    [data-testid="stFileUploader"] {{
        background-color: {bg_card}; padding: 15px; border-radius: 16px; border: 1px dashed {border_color}; margin-bottom: 10px;
    }}
    
    .premium-disclaimer {{
        background-color: {bg_card}; padding: 18px 24px; border-radius: 16px; border: 1px solid {border_color}; 
        color: {text_muted}; font-size: 0.9rem; margin-bottom: 30px; border-left: 4px solid #3b82f6;
    }}
    
    /* Zameglitev */
    .blurred-content {{ filter: blur(6px); opacity: 0.6; user-select: none; pointer-events: none; transition: all 0.5s ease; }}
    
    /* Paywall kartica */
    .paywall-box {{
        background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #475569; border-radius: 16px;
        padding: 25px; text-align: center; margin-top: -60px; position: relative; z-index: 10; box-shadow: 0 -15px 30px rgba(15, 23, 42, 0.9);
    }}
    .paywall-box h3 {{ color: #f8fafc; font-size: 1.4rem; font-weight: 800; margin-bottom: 5px; }}
    .paywall-box p {{ color: #94a3b8; font-size: 1rem; margin-bottom: 20px; }}
    
    /* Gumbi */
    div[data-testid="stButton"] button {{
        width: 100% !important; border-radius: 12px !important; padding: 16px !important; font-weight: 700 !important; transition: all 0.3s ease !important;
    }}
    
    /* Lebdeč Chat */
    .stChatFloatingInputContainer {{ background: transparent !important; }}
    div[data-testid="stChatInput"] {{
        background-color: rgba(30, 41, 59, 0.75) !important; backdrop-filter: blur(12px) !important; border: 1px solid {border_color} !important;
        border-radius: 24px !important; max-width: 650px !important; margin: 0 auto !important;
    }}
    
    [data-testid="stSidebar"], [data-testid="stHeader"] {{ display: none !important; }}
    footer {{ visibility: hidden; }}
    </style>
""", unsafe_allow_html=True)

# --- 3. HTML FORMATER ---
def formatiraj_izvid_v_html(tekst_odgovora, is_unlocked):
    html_rezultat = "<div style='margin-top: 15px; padding: 5px;'>"
    znotraj_seznama = False
    znotraj_blura = False
    potreben_paywall = False
    
    for line in tekst_odgovora.split('\n'):
        vrstica = line.replace('#', '').strip()
        if not vrstica:
            if znotraj_seznama: html_rezultat += "</ul>"; znotraj_seznama = False
            continue
        
        if "[NASLOV] POMEMBNA ODSTOPANJA" in vrstica.upper() and not is_unlocked:
            if znotraj_seznama: html_rezultat += "</ul>"; znotraj_seznama = False
            html_rezultat += "<div class='blurred-content'>"
            znotraj_blura = True
            potreben_paywall = True
            
        if "[NASLOV]" in vrstica.upper():
            if znotraj_seznama: html_rezultat += "</ul>"; znotraj_seznama = False
            naslov_tekst = vrstica.upper().replace("[NASLOV]", "").strip()
            html_rezultat += f"<p style='color: {txt_barva}; font-weight: 700; font-size: 1.35rem; margin-top: 2rem; margin-bottom: 0.8rem;'>{naslov_tekst}</p>"
        elif vrstica.startswith("-") or vrstica.startswith("*"):
            if not znotraj_seznama:
                html_rezultat += f"<ul style='padding-left: 20px; color: {text_muted};'>"
                znotraj_seznama = True
            item_tekst = vrstica.lstrip("-* ").strip()
            if "**" in item_tekst:
                d = item_tekst.split("**")
                for i in range(1, len(d), 2): d[i] = f"<strong style='color: {txt_barva}; font-weight: 600;'>{d[i]}</strong>"
                item_tekst = "".join(d)
            html_rezultat += f"<li style='color: {text_main}; font-size: 1.05rem; margin-bottom: 0.6rem;'>{item_tekst}</li>"
        else:
            if znotraj_seznama: html_rezultat += "</ul>"; znotraj_seznama = False
            p_tekst = vrstica
            if "**" in p_tekst:
                d = p_tekst.split("**")
                for i in range(1, len(d), 2): d[i] = f"<strong style='color: {txt_barva}; font-weight: 600;'>{d[i]}</strong>"
                p_tekst = "".join(d)
            html_rezultat += f"<p style='color: {text_muted}; font-size: 1.05rem; margin-bottom: 1.2rem;'>{p_tekst}</p>"
            
    if znotraj_seznama: html_rezultat += "</ul>"
    if znotraj_blura: html_rezultat += "</div>"
    html_rezultat += "</div>"
    
    return html_rezultat, potreben_paywall

# --- 4. ZDRUŽEN VMESNIK (SKRIVANJE PO ANALIZI) ---
st.markdown("<h1>MedicAI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Vaš osebni zdravstveni tolmač.<br>Hitro, preprosto in v laičnem jeziku.</p>", unsafe_allow_html=True)

uploaded_file = None
user_question = ""
analyze_button = False

# Prikažemo vnosna polja SAMO, če uporabnik še ni začel z analizo (zgodovina je prazna)
if len(st.session_state.api_history) == 0:
    with st.container():
        uploaded_file = st.file_uploader("📁 Naložite izvid (Slika s kamere ali PDF)", type=["png", "jpg", "jpeg", "pdf"])
        user_question = st.text_area("💬 Ali pa vpišite svoje vprašanje:", placeholder="Npr. Kaj pomeni visok holesterol? ali sem prilepite besedilo izvida...", height=110)

    st.markdown("<br>", unsafe_allow_html=True)
    col_left, col_btn, col_right = st.columns([1, 1.5, 1])
    with col_btn:
        analyze_button = st.button("Analiziraj podatke", use_container_width=True)
else:
    # Če je analiza že narejena, prvotni blok skrijemo in ponudimo gumb za "Začni znova"
    col_left, col_btn, col_right = st.columns([1, 1.5, 1])
    with col_btn:
        if st.button("🔄 Začni znova / Naloži nov izvid", use_container_width=True):
            st.session_state.api_history = []
            st.session_state.ui_history = []
            st.session_state.izvid_odklenjen = False
            st.rerun()

SYSTEM_PROMPT = """
Si vrhunski, sočuten medicinski asistent. 
Če uporabnik naloži sliko, ki očitno NI povezana z medicino, odgovori SAMO IN IZKLJUČNO: "NAPAKA: Datoteka ni medicinske narave. Prosimo, naložite veljaven zdravstveni izvid."

PRAVILA GLEDE NA VRSTO VPRAŠANJA:
SCENARIJ A (Uporabnik preda konkreten zdravstveni izvid v analizo):
Odgovor obvezno razdeli v naslednja poglavja z natančno oznako [NASLOV]:
  [NASLOV] KRATEK POVZETEK
  [NASLOV] STABILNE VREDNOSTI
  [NASLOV] POMEMBNA ODSTOPANJA IN IZRAZI
  [NASLOV] VPRAŠANJA ZA VAŠEGA ZDRAVNIKA

SCENARIJ B (Uporabnik postavi samo splošno vprašanje, npr. 'Kaj je angina?' brez priloženega izvida):
Odgovori neposredno, laično in prijazno v nekaj odstavkih. V tem primeru NE UPORABI zgornjih poglavij in oznak.

Splošna pravila: NIKOLI ne postavljaj diagnoze. Za alineje uporabljaj znak minus (-).
"""

# KLIC ZA PRVO ANALIZO
if analyze_button:
    if not uploaded_file and not user_question.strip():
        st.warning("Prosim, naložite dokument ali vpišite vprašanje.")
        st.stop()
        
    st.session_state.api_history = []
    st.session_state.ui_history = []
    st.session_state.izvid_odklenjen = False 
    
    with st.spinner("⏳ MedicAI preučuje podatke..."):
        try:
            full_prompt = f"NAVODILA:\n{SYSTEM_PROMPT}\n\nZAHTEVA UPORABNIKA:\n"
            parts_array = []
            
            if uploaded_file and user_question:
                if uploaded_file.type == "application/pdf": file_bytes = uploaded_file.read(); koncni_mime = "application/pdf"
                else:
                    slika = Image.open(uploaded_file); slika = slika.convert('RGB') if slika.mode != 'RGB' else slika
                    slika.thumbnail((2000, 2000)); b_io = io.BytesIO(); slika.save(b_io, format='JPEG', quality=85)
                    file_bytes = b_io.getvalue(); koncni_mime = "image/jpeg"
                base64_file = base64.b64encode(file_bytes).decode('utf-8')
                full_prompt += f"Preuči priložen dokument. Uporabnik je zraven dodal še tole vprašanje/opombo: {user_question}"
                parts_array = [{"inlineData": {"mimeType": koncni_mime, "data": base64_file}}, {"text": full_prompt}]
                
            elif uploaded_file:
                if uploaded_file.type == "application/pdf": file_bytes = uploaded_file.read(); koncni_mime = "application/pdf"
                else:
                    slika = Image.open(uploaded_file); slika = slika.convert('RGB') if slika.mode != 'RGB' else slika
                    slika.thumbnail((2000, 2000)); b_io = io.BytesIO(); slika.save(b_io, format='JPEG', quality=85)
                    file_bytes = b_io.getvalue(); koncni_mime = "image/jpeg"
                base64_file = base64.b64encode(file_bytes).decode('utf-8')
                full_prompt += "Natančno preuči priložen dokument (ali sliko) in ga laično razloži v mojem jeziku."
                parts_array = [{"inlineData": {"mimeType": koncni_mime, "data": base64_file}}, {"text": full_prompt}]
                
            elif user_question:
                full_prompt += user_question
                parts_array = [{"text": full_prompt}]
            
            st.session_state.api_history.append({"role": "user", "parts": parts_array})
            payload = {"contents": st.session_state.api_history, "generationConfig": {"temperature": 0.2}}
            response = requests.post(API_URL, headers=API_HEADERS, json=payload)
            response_json = response.json()
            
            if 'error' not in response_json:
                ai_odgovor = response_json['candidates'][0]['content']['parts'][0]['text']
                st.session_state.api_history.append({"role": "model", "parts": [{"text": ai_odgovor}]})
                st.session_state.ui_history.append({"role": "assistant", "content": ai_odgovor, "is_main_report": True})
                st.rerun() # Prisilno osvežimo stran, da skrijemo vnosni obrazec!
        except Exception as e:
            st.error(f"Napaka: {e}")

# --- 5. PRIKAZ REZULTATOV IN PAYWALL ---
prikazan_paywall = False

for msg in st.session_state.ui_history:
    avatar_ikona = "👤" if msg["role"] == "user" else "🩺"
    with st.chat_message(msg["role"], avatar=avatar_ikona):
        if msg.get("is_main_report", False):
            if "NAPAKA: Datoteka ni medicinske narave" in msg["content"]:
                st.warning("Datoteka ni medicinske narave. Prosimo, naložite veljaven zdravstveni izvid.")
            else:
                if "[NASLOV]" in msg["content"]:
                    st.markdown(f"<h2 style='color: {text_main}; font-weight:800; font-size: 1.6rem; margin-top:30px;'>📋 Poročilo analize</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='premium-disclaimer'><b>Opozorilo:</b> Razlaga je informativne narave. Obvezno se posvetujte z zdravnikom.</div>", unsafe_allow_html=True)
                
                ima_pravice = st.session_state.is_premium or st.session_state.izvid_odklenjen
                oblikovan_html, rabi_paywall = formatiraj_izvid_v_html(msg["content"], is_unlocked=ima_pravice)
                st.markdown(oblikovan_html, unsafe_allow_html=True)
                
                if rabi_paywall and not ima_pravice:
                    prikazan_paywall = True
        else:
            st.markdown(msg["content"])

# IZRIS PAYWALL KARTICE
if prikazan_paywall:
    st.markdown("""
        <div class='paywall-box'>
            <h3>🔒 Odklenite celotno analizo</h3>
            <p>Vaš izvid vsebuje pomembna odstopanja. Odkrijte vse podrobnosti in postavite vprašanja.</p>
        </div>
    """, unsafe_allow_html=True)
    
    pc1, pc2 = st.columns(2)
    with pc1:
        if st.button("Odkleni to poročilo (1,90 €)", key="btn_onetime", type="secondary"):
            st.session_state.izvid_odklenjen = True
            st.rerun() 
    with pc2:
        if st.button("⭐ Premium + AI Chat (4,90 €/mes)", key="btn_premium", type="primary"):
            st.session_state.is_premium = True
            st.session_state.izvid_odklenjen = True
            st.rerun() 

# --- 6. FREEMIUM KLEPET (LIMITIRANO NA 3 SPOROČILA) ---
if len(st.session_state.api_history) > 0 and not prikazan_paywall:
    
    preostala_sporocila = 3 - st.session_state.free_messages_used
    
    if not st.session_state.is_premium and preostala_sporocila <= 0:
        st.info("⚠️ **Vaš brezplačni paket je porabljen.** Za neomejen klepet z AI zdravnikom odklenite Premium.")
        if st.button("⭐ Odkleni Premium (4,90 €/mes)", key="btn_chat_premium", type="primary"):
            st.session_state.is_premium = True
            st.rerun()
            
    else:
        placeholder = "Vprašajte o izvidu..." if st.session_state.is_premium else f"Vnesite vprašanje... (Še {preostala_sporocila} brezplačna)"
        if prompt := st.chat_input(placeholder):
            
            with st.chat_message("user", avatar="👤"): st.markdown(prompt)
            st.session_state.ui_history.append({"role": "user", "content": prompt})
            st.session_state.api_history.append({"role": "user", "parts": [{"text": prompt}]})
            
            with st.chat_message("assistant", avatar="🩺"):
                with st.spinner("⏳ Pripravljam odgovor..."):
                    payload = {"contents": st.session_state.api_history, "generationConfig": {"temperature": 0.2}}
                    response = requests.post(API_URL, headers=API_HEADERS, json=payload)
                    response_json = response.json()
                    
                    if 'error' not in response_json:
                        ai_odgovor = response_json['candidates'][0]['content']['parts'][0]['text']
                        st.markdown(ai_odgovor)
                        st.session_state.api_history.append({"role": "model", "parts": [{"text": ai_odgovor}]})
                        st.session_state.ui_history.append({"role": "assistant", "content": ai_odgovor, "is_main_report": False})
                        
                        if not st.session_state.is_premium:
                            st.session_state.free_messages_used += 1
                            st.rerun() 
                    else:
                        st.error("Napaka pri klepetu.")
