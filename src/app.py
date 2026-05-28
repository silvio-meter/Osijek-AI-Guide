import streamlit as st

st.set_page_config(page_title="Osijek AI Guide", page_icon="🏙️")
st.title("🏙️ Osijek AI Guide")
st.markdown("**Pomoćnik za turiste i stanovnike Osijeka**")

st.write("Aplikacija je u izradi...")

prompt = st.text_input("Postavi pitanje o Osijeku:")

if prompt:
    st.write(f"Još uvijek radim na ovoj aplikaciji. Uskoro će raditi!")