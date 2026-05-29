# 🏛️ Osijek AI Guide - Lega

**Lega** is an advanced AI agent specialized in Osijek, Croatia. It answers in an authentic Osijek style — relaxed, honest, with a touch of local humor and deep knowledge of the city. It is not just another chatbot, but a real local guide that speaks in real Osijek slang (essekerizmi) when using Croatian, remembers the entire conversation, and uses a RAG system with a knowledge base of over 50 detailed PDFs.

---

## ✨ Key Features

- **Multilingual**: Croatian (with authentic Osijek slang), English, German
- **Chat Memory**: Remembers the full conversation history
- **RAG System**: Retrieves information from a curated knowledge base
- **Source Citation**: Shows which PDF the answer came from
- **Osijek Design**: Blue and white theme with the city coat of arms
- **Interactive**: Asks follow-up questions and keeps the conversation going

---

## 🛠️ How It Was Built

This project was developed in one intensive day (approximately 10 hours of work) with the following phases:

### Phase 1: Architecture & Setup
Created a clean modular structure (`src/` folder) and separated concerns into `prompts.py`, `retrieval.py`, `config.py`, and `app.py`.

### Phase 2: Core System
Wrote a detailed System Prompt with authentic Osijek personality and examples. Implemented RAG using Chroma vector database + HuggingFace embeddings and connected to xAI Grok API.

### Phase 3: Advanced Logic
Added Chat Memory (full conversation history), implemented smart fallback logic, and added source citation for transparency.

### Phase 4: User Experience & Design
Added language selection (HR/EN/DE), integrated the official coat of arms of Osijek, designed a clean modern UI using Osijek's blue and white colors, and fixed multiple technical issues.

---

## 📁 Project Structure

```
Osijek-AI-Guide-v2/
├── src/
│   ├── app.py                 # Main Streamlit application
│   ├── prompts.py             # System prompts (HR, EN, DE)
│   ├── retrieval.py           # RAG logic + citation
│   ├── config.py              # Configuration
│   └── grb_osijeka.jpg        # Coat of arms of Osijek
├── data/                      # Knowledge base (50+ PDFs)
├── vectorstore/               # Chroma vector database
├── create_knowledge_base.py   # Script to rebuild the vector store
├── requirements.txt
├── .env                       # Contains XAI_API_KEY
└── README.md
```

---

## 🚀 Installation & Running

### 1. Install dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Set up your API key

Create a `.env` file in the root folder and add:

```env
XAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### 3. Run the application

```bash
python3 -m streamlit run src/app.py
```

---

## 🔧 How to Customize

| File              | What you can change                     |
|-------------------|-----------------------------------------|
| `src/app.py`      | UI design, layout, logic                |
| `src/prompts.py`  | Personality, examples, slang            |
| `src/retrieval.py`| Retrieval parameters and citation       |
| `src/config.py`   | Model, temperature, similarity threshold|

---

## 📚 Knowledge Base

The agent uses a carefully curated knowledge base of over 50 detailed PDFs covering:
- History of Osijek (from Roman times to present)
- Tourism, landmarks, and practical information
- Gastronomy and traditional food
- Accommodation, events, nature, and more

---

## 🧠 Technical Stack

- **Frontend**: Streamlit
- **LLM**: Grok-3-mini (via xAI API)
- **Vector Database**: Chroma
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Framework**: LangChain

---

## 🚀 Future Improvements (Planned)

- [ ] Export conversation to text/PDF
- [ ] Better fallback mechanism
- [ ] More examples in the System Prompt
- [ ] Streaming responses
- [ ] Deployment to Streamlit Cloud or Hugging Face
- [ ] Voice input support

---

## 👤 Author

Developed by **Silvio Meter** in one focused day (May 28, 2026).

---

## 📄 License

This project is open for personal and educational use.

---

**Enjoy talking to Lega!** 🏛️