"""
Osijek AI Guide - Lega (Optimizirana verzija)
"""

import streamlit as st
from prompts import get_system_prompt
from retrieval import get_relevant_documents
from langchain_xai import ChatXAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(
    page_title="Osijek AI Guide - Lega",
    page_icon="🏛️",
    layout="wide"
)

# =============================================
# CSS - Optimizirani dizajn Osijeka
# =============================================
st.markdown("""
<style>
    :root {
        --osijek-blue: #003087;
        --osijek-light-blue: #0055A5;
    }
    
    /* Glavno zaglavlje */
    .main-header {
        background: linear-gradient(135deg, #003087 0%, #0055A5 100%);
        color: white;
        padding: 20px 30px;
        border-radius: 16px;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0, 48, 135, 0.3);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.4rem;
        font-weight: 700;
    }
    
    .main-header p {
        margin: 5px 0 0 0;
        font-size: 1.1rem;
        opacity: 0.95;
    }
    
    /* Chat poruke */
    .stChatMessage {
        border-radius: 18px;
        padding: 14px 18px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .stChatMessage[data-testid="chat-message-user"] {
        background-color: #E8F4FD;
        border-left: 5px solid #003087;
    }
    
    .stChatMessage[data-testid="chat-message-assistant"] {
        background-color: #F0F7FF;
        border-left: 5px solid #0055A5;
    }
    
    /* Gumbi */
    .stButton > button {
        background-color: #003087;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #0055A5;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 85, 165, 0.4);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    
    /* Izvori */
    .stExpander {
        border: 1px solid #E2E8F0;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_llm():
    return ChatXAI(
        model="grok-3-mini",
        temperature=0.7,
        max_tokens=800,
        xai_api_key=os.getenv("XAI_API_KEY")
    )

llm = get_llm()

# =============================================
# ZAGLAVLJE SA GRBOM (optimizirano)
# =============================================
col1, col2 = st.columns([1.2, 7])

with col1:
    grb_path = os.path.join(os.path.dirname(__file__), "grb_osijeka.jpg")
    if os.path.exists(grb_path):
        st.image(grb_path, width=85)
    else:
        st.write("🏛️")

with col2:
    st.markdown("""
    <div style="padding-top: 8px;">
        <h1 style="margin: 0; color: #003087; font-size: 2.6rem; font-weight: 700;">Osijek AI Guide</h1>
        <p style="margin: 4px 0 0 0; color: #555; font-size: 1.15rem;">Lega - tvoj prijateljski lokalni vodič kroz Osijek</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Sidebar
with st.sidebar:
    st.header("O Legi")
    st.write("""
    **Lega** je AI agent koji poznaje Osijek bolje od većine ljudi.
    
    Pitaš ga što god želiš - o hrani, smještaju, događajima, slengu, povijesti...
    
    Odgovara na osiječki način - opušteno, iskreno i s malo humora.
    """)
    
    st.divider()
    
    language = st.selectbox(
        "🌐 Jezik / Language / Sprache",
        options=["Hrvatski", "English", "Deutsch"],
        index=0
    )
    
    lang_code = {
        "Hrvatski": "hr",
        "English": "en",
        "Deutsch": "de"
    }[language]
    
    st.divider()
    
    if st.button("🔄 Resetiraj razgovor"):
        st.session_state.messages = []
        st.rerun()
    
    st.caption("🏛️ Grb grada Osijeka")

SYSTEM_PROMPT = get_system_prompt(lang_code)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt_input := st.chat_input("Pitaj Legu nešto o Osijeku..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt_input})
    with st.chat_message("user"):
        st.markdown(prompt_input)
    
    with st.spinner("Lega razmišlja..." if lang_code == "hr" else "Lega is thinking..." if lang_code == "en" else "Lega denkt nach..."):
        relevant_docs = get_relevant_documents(prompt_input)
        
        context_text = "\n\n".join([
            f"[{doc['source']}]\n{doc['content']}" 
            for doc in relevant_docs
        ]) if relevant_docs else ("Nema relevantnog konteksta u bazi." if lang_code == "hr" else "No relevant context in the database." if lang_code == "en" else "Kein relevanter Kontext in der Datenbank.")
        
        full_prompt = prompt.format(
            input=prompt_input,
            chat_history=st.session_state.messages,
            context=context_text
        )
        
        response = llm.invoke(full_prompt)
        answer = response.content
    
    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)
        
        if relevant_docs:
            with st.expander("📚 Izvori" if lang_code == "hr" else "📚 Sources" if lang_code == "en" else "📚 Quellen"):
                for doc in relevant_docs[:3]:
                    st.write(f"**{doc['source']}** (score: {doc['score']:.2f})")