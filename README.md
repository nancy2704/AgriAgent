# AgriAgent — Agentic AI-Powered Smart Farming Assistant

> **SDG 2 — Zero Hunger** | AI/ML Internship Demonstration Project

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/built%20with-Streamlit-ff4b4b.svg)](https://streamlit.io/)

---

## 📌 Project Overview

AgriAgent is an **agentic AI application** that helps smallholder farmers understand crop problems,
retrieve reliable agricultural information, analyze local weather conditions, and prepare
**personalized, evidence-based farming action plans**.

It addresses **UN SDG 2 (Zero Hunger)** by bringing AI-powered agricultural decision support
directly to farmers — regardless of their access to extension services or specialists.

---

## 🌾 Problem Statement

Smallholder farmers — who produce over 70% of the world's food — often lack timely access
to agricultural expertise when crops are affected by diseases, pests, or environmental stress.
Delayed or incorrect responses lead to yield losses, unnecessary chemical applications, and
economic hardship. AgriAgent bridges this gap using a multi-agent AI workflow that retrieves
trusted agricultural knowledge, incorporates real-time weather data, and synthesizes
structured, uncertainty-aware action plans that farmers can act on immediately.

---

## 🎯 SDG Mapping

| SDG | Target | How AgriAgent Contributes |
|-----|--------|--------------------------|
| SDG 2 — Zero Hunger | 2.3, 2.4 | Supports smallholder productivity and sustainable farming practices |
| SDG 2 — Zero Hunger | 2.4 | Promotes integrated pest management over blanket pesticide use |
| SDG 17 — Partnerships | 17.8 | Leverages AI/ML technology for agricultural development |

---

## 🏗️ System Architecture

```
User (Streamlit UI)
        │
        ▼
┌─────────────────────────────────────────────┐
│              Workflow Service               │
│  1. Intake Agent  → validate input          │
│  2. Research Agent → knowledge base search  │
│  3. Weather Agent → weather API / demo      │
│  4. Planning Agent → LLM / template plan    │
│  5. Follow-up Agent → tasks & reminders     │
│  6. Report Service → SQLite persistence     │
└─────────────────────────────────────────────┘
        │
        ▼
    SQLite DB (agriagent.db)
```

---

## 🤖 Agent Responsibilities

### 1. Farmer Intake Agent (`agents/intake_agent.py`)
- Validates all required fields (crop name, location, symptoms)
- Provides follow-up prompts for missing information
- Strips whitespace and normalises input via Pydantic

### 2. Agricultural Research Agent (`agents/research_agent.py`)
- Searches the local curated knowledge base (`data/agricultural_knowledge.json`)
- Uses keyword-based relevance scoring
- Returns source titles and URLs from FAO, IRRI, CGIAR, Cornell
- **Never invents citations** — all content comes from stored entries

### 3. Weather Agent (`agents/weather_agent.py`)
- Retrieves current weather via OpenWeatherMap API
- Falls back to clearly labelled demo data when no key is configured
- Handles all API failures gracefully without fabricating data

### 4. Farming Planning Agent (`agents/planning_agent.py`)
- Combines research evidence, weather, and farmer symptoms
- Uses OpenAI GPT-4o-mini when API key is configured
- Falls back to a template-based demo plan (clearly labelled) otherwise
- All plans include uncertainty notes and expert consultation warnings

### 5. Follow-Up Agent (`agents/followup_agent.py`)
- Saves action plans and auto-generates follow-up tasks
- Allows farmers to track progress and add observations
- Never claims notifications were sent — all tracking is in-app only

---

## 📁 Project Structure

```
AgriAgent/
├── app.py                      # Streamlit main application
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .env.example                # Environment variable template
├── gitignore.txt               # Rename to .gitignore before use
│
├── agents/
│   ├── __init__.py
│   ├── intake_agent.py         # Input validation agent
│   ├── research_agent.py       # Knowledge base retrieval
│   ├── weather_agent.py        # Weather data retrieval
│   ├── planning_agent.py       # LLM-based action planning
│   └── followup_agent.py       # Follow-up task management
│
├── tools/
│   ├── __init__.py
│   ├── agricultural_knowledge.py  # KB search tool
│   └── weather_tool.py            # OpenWeatherMap tool
│
├── services/
│   ├── __init__.py
│   ├── workflow_service.py     # Agentic workflow orchestrator
│   └── report_service.py       # Report retrieval helpers
│
├── database/
│   ├── __init__.py
│   ├── db.py                   # SQLite CRUD operations
│   └── schema.sql              # Database schema
│
├── models/
│   ├── __init__.py
│   └── schemas.py              # Pydantic validation models
│
├── tests/
│   ├── test_database.py        # Database layer tests
│   ├── test_tools.py           # Tools tests (KB, weather)
│   └── test_workflow.py        # Workflow and agents tests
│
└── data/
    └── agricultural_knowledge.json  # Curated KB (FAO, IRRI, CGIAR, Cornell)
```

---

## 🚀 Installation

### Prerequisites
- Python 3.11 or higher
- pip

### Steps

```bash
# 1. Clone or navigate to the project directory
cd AgriAgent

# 2. (Recommended) Create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ Environment Configuration

```bash
# Copy the example file
cp .env.example .env      # macOS/Linux
# or on Windows:
copy .env.example .env
```

Edit `.env` and fill in your credentials:

```env
# Required for AI-generated action plans
OPENAI_API_KEY=sk-...

# Required for live weather data (free tier at openweathermap.org)
OPENWEATHER_API_KEY=...
```

> **Without API keys**, AgriAgent runs fully in **demo mode**:
> - Action plans use a template-based system (clearly labelled)
> - Weather shows sample data (clearly labelled as demo)
> - The knowledge base always works — no API required

---

## ▶️ Running the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## 🧪 Running the Tests

```bash
# Install pytest if not already installed
pip install pytest pytest-mock

# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_database.py -v
pytest tests/test_tools.py -v
pytest tests/test_workflow.py -v
```

---

## 🌐 Knowledge Base Coverage

The local knowledge base (`data/agricultural_knowledge.json`) includes entries for:

| Crop | Topics Covered |
|------|---------------|
| Wheat | Rust diseases (stripe, stem, leaf), powdery mildew, nitrogen deficiency |
| Rice | Blast disease, bacterial leaf blight, brown planthopper |
| Maize | Fall armyworm, maize streak virus, northern corn leaf blight |
| Tomato | Late blight, early blight, blossom end rot |
| Potato | Late blight |
| Cotton | Bollworm |
| Banana | Panama disease (Fusarium wilt, TR4) |
| General | Drought stress, soil health, integrated pest management |

*Sources: FAO, IRRI, CGIAR, Cornell Plant Disease Diagnostic Clinic, University Extensions*

---

## ⚠️ Image Analysis

**Automated crop disease image diagnosis is NOT available** in this version.

- Uploaded images are displayed for reference only.
- The application clearly labels image analysis as unavailable.
- Farmers are prompted to describe symptoms in text for accurate analysis.

A future version could integrate a pretrained CNN model (e.g., PlantVillage dataset)
for supported crop classes with documented confidence reporting.

---

## 🔒 Safety and Reliability

- **No fabricated diagnoses** — all crop information comes from the verified knowledge base
- **No invented weather data** — failures and demo data are clearly labelled
- **No specific pesticide dosages** — farmers are referred to local extension services
- **Uncertainty communication** — all plans include confidence caveats
- **Expert referral** — severe or ambiguous cases always recommend professional consultation
- **No secrets in logs or UI** — API keys are read from environment variables only
- **Input validation** — all farmer inputs validated via Pydantic before processing

---

## 📊 Data Storage

SQLite (`agriagent.db`) stores:
- Farmer queries (crop, location, symptoms)
- Analysis reports (plan summaries, research summaries, weather summaries)
- Source references (titles and URLs)
- Follow-up tasks (with status tracking)

API keys are **never** stored in the database.

---

## ⚡ Limitations and Future Improvements

### Current Limitations
- Knowledge base is static JSON — limited to ~18 crop/issue entries
- Image-based disease diagnosis not implemented
- No push notifications — follow-up is in-app only
- Weather forecast (multi-day) not implemented (only current conditions)
- English language only

### Future Improvements
- Integrate PlantVillage CNN model for image-based diagnosis
- Expand knowledge base with more crops and regions
- Add multi-day weather forecasts
- Support multiple languages
- Integrate SMS/email reminders via Twilio/SendGrid
- Add a REST API for mobile app integration
- Implement RAG (Retrieval-Augmented Generation) with a vector database

---

## 📄 License

This project is developed for educational and demonstration purposes as part of an AI/ML internship.

---

*AgriAgent — Helping farmers grow more, waste less, and feed the world. 🌾*
