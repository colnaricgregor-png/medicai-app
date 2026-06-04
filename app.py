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

# --- 1. INICIALIZACIJA POSLOVNE LOGIKE (Spomin in Blagajna) ---
if "pozdrav_prikazan" not in st.session_state:
    st.toast("👋 **Dobrodošli v MedicAI!**\n\nNaložite izvid in preizkusite 3 brezplačna vprašanja.", icon="🩺")
    st.session_state.pozdrav_prikazan = True

if "api_history" not in st.session_state:
    st.session_state.api_history = []  
if "ui_history" not in st.session_state:
    st.session_state.ui_history = []   

# Spremenljivke za Paywall
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False
if "izvid_odklenjen" not in st.session_state:
    st.session_state.izvid_odklenjen = False
if "free_messages_used" not in st.session_state:
    st.session_state.free_messages_used = 0

if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("Missing API Key in Streamlit Secrets!")
    st.stop()

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
API_HEADERS = {"Content-Type": "application/json"}

# --- 2. PREMIUM CSS Z DODANIM PAYWALLOM ---
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
    
    .stApp {{ 
        background-color: {bg_app} !important; 
        font-family: -apple-system, sans-serif; 
        animation: fadeIn 0.8s ease-out;
    }}
    
    .block-container {{ max-width: 650px !important; padding-top: 3rem !important; padding-bottom: 100px !important; }}
    
    h1 {{ color: {text_main} !important; text-align: center; font-weight: 800; font-size: 2.6rem; margin-bottom: 0.2rem; }}
    .subtitle {{ text-align: center; color: {text_muted} !important; font-size: 1.1rem; margin-bottom: 3rem; }}
    
    div.stTextArea textarea {{
        color: {input_text} !important; background-color: {bg_card} !important; border: 1px solid {border_color} !important;
        border-radius: 16px !important; padding: 18px !important; transition: all 0.3s ease !important;
    }}
    
    .premium-disclaimer {{
        background-color: {bg_card}; padding: 18px 24px; border-radius: 16px; border: 1px solid {border_color}; 
        color: {text_muted}; font-size: 0.9rem; margin-bottom: 30px; border-left: 4px solid #3b82f6;
    }}
    
    /* ZAMEGLITEV (BLUR) */
    .blurred-content {{
        filter: blur(6px);
        opacity: 0.6;
        user-select: none;
        pointer-events: none;
        transition: all 0.5s ease;
    }}
    
    /* PAYWALL KARTICA */
    .paywall-box {{
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid #475569;
        border-radius: 16px;
        padding: 25px;
        text-align: center;
        margin-top: -60px;
        position: relative;
        z-index: 10;
        box-shadow: 0 -15px 30px rgba(15, 23, 42, 0.9);
    }}
    .paywall-box h3 {{ color: #f8fafc; font-size: 1.4rem; font-weight: 800; margin-bottom: 5px; }}
    .paywall-box p {{ color: #94a3b8; font-size: 1rem; margin-bottom: 20px; }}
    
    /* GUMBI ZA PLAČILO */
    div[data-testid="stButton"] button {{
        width: 100% !important; border-radius: 12px !important; padding: 16px !important; font-weight: 700 !important;
        transition: all 0.3s ease !important;
    }}
    
    /* Lebdeč Chat Input */
    .stChatFloatingInputContainer {{ background: transparent !important; }}
    div[data-testid="stChatInput"] {{
        background-color: rgba(30, 41, 59, 0.75) !important;
        backdrop-filter: blur(12px) !important; border: 1px solid {border_color} !important;
        border-radius: 24px !important; max-width: 650px !important; margin: 0 auto !important;
    }}
    
    [data-testid="stSidebar"], [data-testid="stHeader"] {{ display: none !important; }}
    footer {{ visibility: hidden; }}
    </style>
""", unsafe_allow_html=True)

# --- 3. PAMETNI HTML FORMATER Z ZAMEGLITVIJO ---
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
        
        # AKTIVACIJA BLURA KO PRIDEMO DO ODSTOPANJ
        if "POGLAVJE: POMEMBNA ODSTOPANJA" in vrstica.upper() and not is_unlocked:
            if znotraj_seznama: html_rezultat += "</ul>"; znotraj_seznama = False
            html_rezultat += "<div class='blurred-content'>"
            znotraj_blura = True
            potreben_paywall = True
            
        if "POGLAVJE:" in vrstica:
            if znotraj_seznama: html_rezultat += "</ul>"; znotraj_seznama = False
            naslov_tekst = vrstica.replace("POGLAVJE:", "").strip()
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
    if znotraj_blura: html_rezultat += "</div>" # Konec zamegljenega dela
    html_rezultat += "</div>"
    
    return html_rezultat, potreben_paywall

# --- 4. GLAVNI VMESNIK ---
st.markdown("<h1>MedicAI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Vaš osebni zdravstveni tolmač.<br>Hitro, preprosto in v laičnem jeziku.</p>", unsafe_allow_html=True)

izbira_nacina = st.radio("Način vnosa", ["📄 Datoteka / Slika", "💬 Besedilo / Vprašanje"], horizontal=True, label_visibility="collapsed")
uploaded_file = None
user_question = ""

if "📄" in izbira_nacina:
    uploaded_file = st.file_uploader("Naložite izvid", type=["png", "jpg", "jpeg", "pdf"], label_visibility="collapsed")
    if uploaded_file: st.success(f"📄 Dokument '{uploaded_file.name}' uspešno naložen!")
else:
    user_question = st.text_area("Vnesite tekst", placeholder="Sem prilepite besedilo izvida...", height=160, label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)
col_left, col_btn, col_right = st.columns([1, 2, 1])
with col_btn:
    analyze_button = st.button("Analiziraj in razloži")

SYSTEM_PROMPT = """
Si vrhunski, sočuten medicinski asistent. 
Če uporabnik naloži sliko, ki očitno NI povezana z medicino, odgovori SAMO IN IZKLJUČNO: "NAPAKA: Datoteka ni medicinske narave. Prosimo, naložite veljaven zdravstveni izvid."

STRIKTNA NAVODILA ZA STRUKTURO:
- NIKOLI ne postavljaj diagnoze in ne predpisuj zdravljenja.
- Odgovor razdeli v naslednja poglavja z VELIKIMI ČRKAMI:
  POGLAVJE: KRATEK POVZETEK
  POGLAVJE: STABILNE VREDNOSTI
  POGLAVJE: POMEMBNA ODSTOPANJA IN IZRAZI
  POGLAVJE: VPRAŠANJA ZA VAŠEGA ZDRAVNIKA
- Za alineje uporabljaj standardni znak minus (-).
"""

# KLIC ZA PRVO ANALIZO
if analyze_button:
    # Ob novi analizi resetiramo spomin, ampak ohranimo status naročnine
    st.session_state.api_history = []
    st.session_state.ui_history = []
    st.session_state.izvid_odklenjen = False # Zaklenemo nov izvid (razen če je premium)
    
    with st.spinner("⏳ MedicAI preučuje vaše podatke..."):
        try:
            full_prompt = f"NAVODILA:\n{SYSTEM_PROMPT}\n\nZAHTEVA:\n"
            parts_array = []
            
            if "📄" in izbira_nacina and uploaded_file:
                if uploaded_file.type == "application/pdf":
                    file_bytes = uploaded_file.read()
                    koncni_mime = "application/pdf"
                else:
                    slika = Image.open(uploaded_file)
                    if slika.mode != 'RGB': slika = slika.convert('RGB')
                    slika.thumbnail((2000, 2000))
                    b_io = io.BytesIO()
                    slika.save(b_io, format='JPEG', quality=85)
                    file_bytes = b_io.getvalue()
                    koncni_mime = "image/jpeg"

                base64_file = base64.b64encode(file_bytes).decode('utf-8')
                full_prompt += "Natančno preuči priložen dokument (ali sliko) in ga laično razloži v mojem jeziku."
                parts_array = [{"inlineData": {"mimeType": koncni_mime, "data": base64_file}}, {"text": full_prompt}]
            elif "💬" in izbira_nacina and user_question:
                full_prompt += user_question
                parts_array = [{"text": full_prompt}]
            else:
                st.warning("Prosim, vnesite tekst ali naložite dokument.")
                st.stop()
            
            st.session_state.api_history.append({"role": "user", "parts": parts_array})
            payload = {"contents": st.session_state.api_history, "generationConfig": {"temperature": 0.2}}
            response = requests.post(API_URL, headers=API_HEADERS, json=payload)
            response_json = response.json()
            
            if 'error' not in response_json:
                ai_odgovor = response_json['candidates'][0]['content']['parts'][0]['text']
                st.session_state.api_history.append({"role": "model", "parts": [{"text": ai_odgovor}]})
                st.session_state.ui_history.append({"role": "assistant", "content": ai_odgovor, "is_main_report": True})
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
                st.markdown(f"<h2 style='color: {text_main}; font-weight:800; font-size: 1.6rem; margin-top:30px;'>📋 Poročilo analize</h2>", unsafe_allow_html=True)
                st.markdown("<div class='premium-disclaimer'><b>Opozorilo:</b> Razlaga je informativne narave. Obvezno se posvetujte z zdravnikom.</div>", unsafe_allow_html=True)
                
                # Formatiranje in preverjanje pravic
                ima_pravice = st.session_state.is_premium or st.session_state.izvid_odklenjen
                oblikovan_html, rabi_paywall = formatiraj_izvid_v_html(msg["content"], is_unlocked=ima_pravice)
                st.markdown(oblikovan_html, unsafe_allow_html=True)
                
                # ČE UPORABNIK NIMA PRAVIC, SE PRIKAŽE GUMB ZA PLAČILO
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
        # Gumb v stilu "spletne strani", subtilen, a jasen
        if st.button("Odkleni to poročilo (1,90 €)", key="btn_onetime", type="secondary"):
            st.session_state.izvid_odklenjen = True
            st.rerun() # Osveži stran, da odstrani zameglitev!
    with pc2:
        # Premium gumb
        if st.button("⭐ Premium + AI Chat (4,90 €/mes)", key="btn_premium", type="primary"):
            st.session_state.is_premium = True
            st.session_state.izvid_odklenjen = True
            st.rerun() # Osveži stran, da odstrani zameglitev!

# --- 6. FREEMIUM KLEPET (LIMITIRANO NA 3 SPOROČILA) ---
if len(st.session_state.api_history) > 0 and not prikazan_paywall:
    
    # Preverimo limit za free chat
    preostala_sporocila = 3 - st.session_state.free_messages_used
    
    # Če ni Premium in je porabil sporočila, mu blokiramo polje
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
                        
                        # Zapišemo uporabo
                        if not st.session_state.is_premium:
                            st.session_state.free_messages_used += 1
                            st.rerun() # Osveži števec na gumbu
                    else:
                        st.error("Napaka pri klepetu.")
