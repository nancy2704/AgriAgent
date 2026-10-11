"""
AgriAgent — Agentic AI-Powered Smart Farming Assistant
Main Streamlit Application
SDG 2: Zero Hunger
"""
from __future__ import annotations

import base64
import os
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

# Initialize DB on first run
from database import db as _db
_db.initialize_db()

from services.workflow_service import run_workflow
from services.report_service import (
    get_all_reports_summary,
    get_report_detail,
    get_followup_dashboard,
)
from agents.followup_agent import (
    get_all_tasks,
    update_task_status,
    save_followup_task,
)
from agents.intake_agent import get_missing_field_prompts
from models.schemas import FollowUpTask, FollowUpTaskUpdate

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AgriAgent — Smart Farming Assistant",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Logo helper — load SVG as base64 data URI for offline-safe embedding
# ---------------------------------------------------------------------------
def _logo_data_uri() -> str:
    logo_path = Path(__file__).parent / "assets" / "agriagent_logo.svg"
    svg_bytes = logo_path.read_bytes()
    b64 = base64.b64encode(svg_bytes).decode()
    return f"data:image/svg+xml;base64,{b64}"

_LOGO_URI = _logo_data_uri()

st.markdown(
    """
    <style>
    /* ══════════════════════════════════════════════════════════
       MAIN CONTENT — explicit dark text on all custom cards
       (these must come before sidebar rules so specificity wins)
       ══════════════════════════════════════════════════════════ */

    .main-header {font-size: 2.2rem; font-weight: 700; color: #1a4731; margin-bottom: 0;}
    .sub-header  {font-size: 1rem; color: #52796f; margin-top: 0; margin-bottom: 1.5rem;}

    .sdg-badge {
        display: inline-block; background: #e9c46a; color: #264653 !important;
        border-radius: 6px; padding: 2px 10px; font-size: 0.85rem; font-weight: 600;
    }

    /* ── Warning / demo boxes ──────────────────────────────── */
    .warning-box,
    .warning-box * {
        background: #fff8e1;
        border-left: 4px solid #f59e0b;
        padding: 0.75rem 1rem;
        border-radius: 6px;
        margin: 0.6rem 0;
        color: #1c1c1c !important;
        font-size: 0.9rem;
        line-height: 1.55;
    }
    .demo-box,
    .demo-box * {
        background: #e8f4fd;
        border-left: 4px solid #2563eb;
        padding: 0.75rem 1rem;
        border-radius: 6px;
        margin: 0.6rem 0;
        color: #1c1c1c !important;
        font-size: 0.9rem;
    }

    /* ── Step cards ────────────────────────────────────────── */
    .step-card {
        background: #f0faf4;
        border: 1px solid #b7e4c7;
        border-left: 5px solid #2d6a4f;
        border-radius: 8px;
        padding: 0.85rem 1.1rem;
        margin: 0.55rem 0;
    }
    .step-card * { color: #1a1a1a !important; }
    .step-card .step-title {
        font-size: 1rem;
        font-weight: 700;
        color: #1a4731 !important;
        margin-bottom: 0.25rem;
        display: block;
    }
    .step-card .step-action {
        font-size: 0.95rem;
        color: #1c1c1c !important;
        font-weight: 500;
        margin-bottom: 0.3rem;
        display: block;
    }
    .step-card .step-rationale {
        font-size: 0.85rem;
        color: #3a3a3a !important;
        font-style: italic;
        display: block;
        margin-top: 0.2rem;
    }
    .step-card .step-urgency {
        display: inline-block;
        border-radius: 4px;
        padding: 1px 8px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-left: 0.4rem;
        vertical-align: middle;
    }
    .urgency-urgent { background:#fde8e8; color:#b91c1c !important; }
    .urgency-high   { background:#fef3c7; color:#92400e !important; }
    .urgency-normal { background:#d1fae5; color:#065f46 !important; }
    .urgency-low    { background:#f3f4f6; color:#374151 !important; }

    /* ── Source cards ──────────────────────────────────────── */
    .source-card {
        background: #ffffff;
        border: 1px solid #c6e8d3;
        border-left: 4px solid #40916c;
        border-radius: 8px;
        padding: 0.85rem 1.1rem;
        margin: 0.55rem 0;
    }
    .source-card * { color: #1a1a1a !important; }
    .source-card .src-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #1a4731 !important;
        display: block;
        margin-bottom: 0.2rem;
    }
    .source-card .src-org {
        font-size: 0.82rem;
        color: #52796f !important;
        display: block;
        margin-bottom: 0.2rem;
    }
    .source-card .src-relevance {
        font-size: 0.82rem;
        color: #374151 !important;
        font-style: italic;
        display: block;
        margin-top: 0.15rem;
    }
    .source-card a,
    .source-card a:visited {
        color: #1d6fa4 !important;
        text-decoration: underline;
        font-size: 0.82rem;
    }

    /* ── Plan summary box ──────────────────────────────────── */
    .plan-summary-box {
        background: #f0faf4;
        border: 1px solid #b7e4c7;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    .plan-summary-box * { color: #1a1a1a !important; }
    .plan-summary-box .psb-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: #40916c !important;
        font-weight: 700;
        margin-bottom: 0.3rem;
        display: block;
    }
    .plan-summary-box .psb-text {
        font-size: 0.95rem;
        color: #1a1a1a !important;
        line-height: 1.6;
    }

    /* ── Likely-issues pill list ───────────────────────────── */
    .issue-pill {
        display: inline-block;
        background: #fff8e1;
        border: 1px solid #f59e0b;
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #78350f !important;
        margin: 3px 4px 3px 0;
    }

    /* ── Section headings inside results ──────────────────── */
    .results-section-heading {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1a4731 !important;
        margin: 1.1rem 0 0.5rem;
        padding-bottom: 0.25rem;
        border-bottom: 2px solid #b7e4c7;
    }

    /* ── Observations list ─────────────────────────────────── */
    .obs-item {
        background: #f8fffe;
        border-left: 3px solid #74c69d;
        border-radius: 0 6px 6px 0;
        padding: 0.45rem 0.8rem;
        margin: 0.3rem 0;
        font-size: 0.88rem;
        color: #1a1a1a !important;
    }

    /* ══════════════════════════════════════════════════════════
       SIDEBAR — keep all sidebar text light (scoped tightly)
       ══════════════════════════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a4731 0%, #1f5c3a 60%, #245c3a 100%);
    }
    /* Scope the light-text rule to sidebar only — NOT main content */
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] > div * { color: #d8f3dc; }

    .sidebar-brand {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 1.4rem 0.6rem 0.8rem;
        text-align: center;
    }
    .sidebar-logo {
        width: 82px;
        height: 82px;
        border-radius: 50%;
        box-shadow: 0 4px 18px rgba(0,0,0,0.45), 0 0 0 3px #40916c;
        margin-bottom: 0.7rem;
        background: #1a4731;
    }
    .sidebar-app-name {
        font-size: 1.55rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        color: #d8f3dc !important;
        line-height: 1.15;
        margin: 0;
    }
    .sidebar-tagline {
        font-size: 0.78rem;
        font-weight: 600;
        color: #95d5b2 !important;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin: 0.18rem 0 0;
    }
    .sidebar-subtitle {
        font-size: 0.72rem;
        color: #74c69d !important;
        margin-top: 0.22rem;
        font-style: italic;
    }
    .sidebar-sdg {
        display: inline-block;
        background: rgba(233,196,106,0.18);
        border: 1px solid rgba(233,196,106,0.45);
        color: #e9c46a !important;
        border-radius: 20px;
        padding: 2px 11px;
        font-size: 0.72rem;
        font-weight: 600;
        margin-top: 0.55rem;
        letter-spacing: 0.03em;
    }
    .sidebar-divider {
        border: none;
        border-top: 1px solid rgba(82,183,136,0.25);
        margin: 0.9rem 0 0.5rem;
    }

    /* Nav radio — remove default Streamlit label spacing */
    [data-testid="stSidebar"] .stRadio > label {
        display: none;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
        gap: 0.15rem;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        display: flex !important;
        align-items: center;
        padding: 0.52rem 0.85rem;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 500;
        transition: background 0.15s;
        cursor: pointer;
        color: #b7e4c7 !important;
        background: transparent;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background: rgba(64,145,108,0.28) !important;
        color: #d8f3dc !important;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {
        background: rgba(82,183,136,0.22) !important;
        border-left: 3px solid #52b788;
        color: #d8f3dc !important;
        font-weight: 700;
        padding-left: 0.7rem;
    }
    /* Hide the radio circle dot itself */
    [data-testid="stSidebar"] .stRadio input[type="radio"] {
        display: none;
    }

    /* Config status section */
    .sidebar-config-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #74c69d !important;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    .sidebar-config-item {
        font-size: 0.78rem;
        color: #95d5b2 !important;
        padding: 0.18rem 0;
        display: flex;
        align-items: center;
        gap: 0.3rem;
    }
    .sidebar-footer {
        font-size: 0.66rem;
        color: #52b788 !important;
        text-align: center;
        padding: 0.6rem 0.4rem 0.2rem;
        line-height: 1.5;
        opacity: 0.75;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — branding + navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    # ── Brand block ────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="sidebar-brand">
          <img src="{_LOGO_URI}" class="sidebar-logo" alt="AgriAgent logo"/>
          <p class="sidebar-app-name">AgriAgent</p>
          <p class="sidebar-tagline">Smart Farming. Smarter Decisions.</p>
          <p class="sidebar-subtitle">Your AI Agriculture Assistant</p>
          <span class="sidebar-sdg">🌱 SDG 2 — Zero Hunger</span>
        </div>
        <hr class="sidebar-divider"/>
        """,
        unsafe_allow_html=True,
    )

    # ── Navigation ─────────────────────────────────────────────────────────
    page = st.radio(
        "Navigate",
        options=["🏠 Home", "🔍 Analyze Problem", "📋 Follow-Up Tasks", "📁 Previous Reports"],
        label_visibility="collapsed",
    )

    st.markdown('<hr class="sidebar-divider"/>', unsafe_allow_html=True)

    # ── Configuration status ────────────────────────────────────────────────
    api_key_set = bool(os.environ.get("OPENAI_API_KEY", ""))
    print("OpenAI key loaded:", api_key_set)
    print(
    "OpenAI key length:",
    len(os.environ.get("OPENAI_API_KEY", "").strip())
)
    weather_key_set = bool(os.environ.get("OPENWEATHER_API_KEY", ""))

    st.markdown('<p class="sidebar-config-label">Configuration</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="sidebar-config-item">{"✅" if api_key_set else "⚠️"} '
        f'OpenAI: {"connected" if api_key_set else "demo mode"}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="sidebar-config-item">{"✅" if weather_key_set else "⚠️"} '
        f'Weather: {"live data" if weather_key_set else "demo data"}</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="sidebar-divider"/>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sidebar-footer">AgriAgent v1.0<br>'
        'AI-assisted only — always consult<br>a qualified agronomist.</p>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------------------------
if page == "🏠 Home":
    st.markdown('<h1 class="main-header">🌾 AgriAgent</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Agentic AI-Powered Smart Farming Assistant</p>', unsafe_allow_html=True)
    st.markdown('<span class="sdg-badge">SDG 2 — Zero Hunger</span>', unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(
            """
            ## What is AgriAgent?

            AgriAgent is an agentic AI application that helps **smallholder farmers** understand
            crop problems, retrieve reliable agricultural information, analyze local weather
            conditions, and prepare **personalized, evidence-based farming action plans**.

            ### How it works
            1. **Describe your crop problem** — tell us the crop, your location, and what you observe.
            2. **AgriAgent researches** — searches a curated agricultural knowledge base from FAO, IRRI, CGIAR, and Cornell.
            3. **Weather context** — retrieves real-time weather for your location (if API key is configured).
            4. **AI-powered planning** — combines all evidence into a structured, uncertainty-aware action plan.
            5. **Follow-up** — save the plan, schedule observations, and track your progress.

            ### Supported Crops (Knowledge Base)
            Wheat · Rice · Maize · Tomato · Potato · Cotton · Banana · General Agriculture

            ### Important Disclaimer
            > AgriAgent is an **AI assistant** designed to support — not replace — qualified
            > agricultural expertise. Always consult a local agronomist before applying
            > chemical treatments or making high-stakes farming decisions.
            """
        )

    with col2:
        st.markdown("### 🤖 Agents")
        agents_info = [
            ("🧑‍🌾", "Intake Agent", "Validates your input and identifies missing information"),
            ("📚", "Research Agent", "Searches the curated knowledge base"),
            ("🌤️", "Weather Agent", "Retrieves real-time weather data"),
            ("🗺️", "Planning Agent", "Creates your personalized action plan"),
            ("📅", "Follow-Up Agent", "Tracks your progress and reminders"),
        ]
        for icon, name, desc in agents_info:
            st.markdown(f"**{icon} {name}**  \n{desc}")
            st.markdown("")


# ---------------------------------------------------------------------------
# ANALYZE PROBLEM PAGE
# ---------------------------------------------------------------------------
elif page == "🔍 Analyze Problem":
    st.markdown("## 🔍 Analyze Crop Problem")
    st.markdown("Fill in the details below and click **Analyze Problem** to start the agentic workflow.")

    with st.form("farmer_form"):
        col1, col2 = st.columns(2)
        with col1:
            crop_name = st.text_input(
                "Crop Name *",
                placeholder="e.g., wheat, rice, tomato",
                help="Enter the name of the affected crop",
            )
            location = st.text_input(
                "Farm Location *",
                placeholder="e.g., Punjab, India",
                help="City, region, or country where your farm is located",
            )
        with col2:
            symptom_duration = st.text_input(
                "Symptom Duration",
                placeholder="e.g., 3 days, 2 weeks",
                help="How long have you observed these symptoms?",
            )
            additional_notes = st.text_area(
                "Additional Notes",
                placeholder="Any recent spraying, fertilization, unusual weather events…",
                height=80,
            )

        symptoms = st.text_area(
            "Observed Symptoms *",
            placeholder="Describe what you see on the plants (e.g., yellow spots on leaves, wilting, brown lesions…)",
            height=120,
            help="Be as specific as possible — colour, shape, location on plant, affected parts",
        )

        uploaded_image = st.file_uploader(
            "Crop Image (optional)",
            type=["jpg", "jpeg", "png", "webp"],
            help="Upload a photo of the affected crop for reference. Note: automated image diagnosis is not available in this version.",
        )

        submitted = st.form_submit_button("🔬 Analyze Problem", use_container_width=True, type="primary")

    # Show uploaded image if provided
    if uploaded_image is not None:
        st.image(uploaded_image, caption="Uploaded crop image (reference only)", width=300)
        st.info(
            "📷 **Image Analysis Notice:** Automated crop disease image diagnosis is not available "
            "in this version. The image is stored for reference. Please describe all symptoms in the "
            "text field above for analysis.",
            icon="ℹ️",
        )

    # Show follow-up prompts for missing fields (real-time hint before submit)
    if crop_name or location or symptoms:
        prompts = get_missing_field_prompts(crop_name, location, symptoms)
        if prompts:
            st.markdown('<div class="warning-box">⚠️ <strong>Missing information:</strong><br>' + "<br>".join(f"• {p}" for p in prompts) + "</div>", unsafe_allow_html=True)

    if submitted:
        with st.spinner("🌾 AgriAgent is analyzing your crop problem…"):
            result, errors = run_workflow(
                crop_name=crop_name,
                location=location,
                symptoms=symptoms,
                symptom_duration=symptom_duration or None,
                additional_notes=additional_notes or None,
                save_to_db=True,
            )

        if errors:
            st.error("**Please fix the following issues before continuing:**")
            for e in errors:
                st.error(f"• {e}")
        else:
            st.success("✅ Analysis complete!")
            st.session_state["last_result"] = result

    # Display results
    result = st.session_state.get("last_result")
    if result is not None:
        # Demo / status banners
        if result.is_demo:
            st.markdown(
                '<div class="demo-box">🔵 <strong>Demo Mode</strong> — One or more data sources '
                'are using sample/demo data (see individual sections below). '
                'Configure API keys in your <code>.env</code> file for live data.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # Layout: Research | Weather
        col_r, col_w = st.columns([3, 2])

        with col_r:
            st.markdown("### 📚 Agricultural Research Results")
            if result.research.entries:
                for entry in result.research.entries:
                    severity_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(entry.severity, "⚪")
                    with st.expander(f"{severity_color} {entry.topic.title()} — {entry.crop.title()} (score: {entry.relevance_score:.2f})"):
                        st.markdown(f"**Knowledge Base Entry** — *{entry.source_title}*")
                        st.markdown(entry.content)
                        if entry.source_url:
                            st.markdown(f"🔗 [View Source]({entry.source_url})")
            else:
                st.info(
                    "No matching entries found in the knowledge base for the reported symptoms. "
                    "The plan below is based on general agricultural principles."
                )
                if result.research.note:
                    st.caption(result.research.note)

        with col_w:
            st.markdown("### 🌤️ Weather Information")
            weather = result.weather
            if weather.error:
                st.warning(f"⚠️ {weather.error}")
            else:
                if weather.is_demo:
                    st.markdown('<div class="demo-box">🔵 Demo weather data — not a real observation.</div>', unsafe_allow_html=True)
                cols = st.columns(2)
                cols[0].metric("📍 Location", weather.location)
                if weather.temperature_c is not None:
                    cols[1].metric("🌡️ Temperature", f"{weather.temperature_c:.1f} °C")
                if weather.humidity_pct is not None:
                    cols[0].metric("💧 Humidity", f"{weather.humidity_pct:.0f}%")
                if weather.wind_speed_ms is not None:
                    cols[1].metric("💨 Wind Speed", f"{weather.wind_speed_ms:.1f} m/s")
                if weather.description:
                    st.markdown(f"**Conditions:** {weather.description}")
                if weather.rainfall_mm is not None:
                    st.markdown(f"**Rainfall (last hour):** {weather.rainfall_mm:.1f} mm")
                if weather.forecast_summary:
                    st.caption(weather.forecast_summary)

        st.markdown("---")

        # ── Farming Action Plan ─────────────────────────────────────────────
        st.markdown("### 🗺️ Farming Action Plan")
        plan = result.action_plan

        # Summary box
        st.markdown(
            f'<div class="plan-summary-box">'
            f'<span class="psb-label">Plan Summary</span>'
            f'<span class="psb-text">{plan.summary}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Likely issues as pills
        if plan.likely_issues:
            st.markdown(
                '<p class="results-section-heading">🔎 Likely Issues Identified</p>',
                unsafe_allow_html=True,
            )
            pills_html = "".join(
                f'<span class="issue-pill">⚠ {issue}</span>' for issue in plan.likely_issues
            )
            st.markdown(f'<div style="margin:0.4rem 0 0.8rem">{pills_html}</div>', unsafe_allow_html=True)

        # Recommended steps — structured cards
        if plan.steps:
            st.markdown(
                '<p class="results-section-heading">✅ Recommended Steps</p>',
                unsafe_allow_html=True,
            )
            for step in plan.steps:
                urgency_class = f"urgency-{step.urgency}"
                urgency_label = step.urgency.capitalize()
                st.markdown(
                    f'<div class="step-card">'
                    f'  <span class="step-title">Step {step.step_number}: {step.action}'
                    f'    <span class="step-urgency {urgency_class}">{urgency_label}</span>'
                    f'  </span>'
                    f'  <span class="step-rationale">💡 {step.rationale}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Observations needed
        if plan.observations_needed:
            st.markdown(
                '<p class="results-section-heading">👁️ What to Observe Next</p>',
                unsafe_allow_html=True,
            )
            obs_html = "".join(
                f'<div class="obs-item">• {obs}</div>' for obs in plan.observations_needed
            )
            st.markdown(obs_html, unsafe_allow_html=True)

        # Uncertainty notice
        if plan.uncertainty_notes:
            st.markdown(
                f'<div class="warning-box">⚠️ <strong>Uncertainty Notice:</strong> {plan.uncertainty_notes}</div>',
                unsafe_allow_html=True,
            )

        # Expert recommendation
        if plan.expert_consultation_recommended:
            st.warning(
                "👨‍🔬 **Expert Consultation Recommended:** The findings suggest consulting a "
                "qualified agricultural expert or local extension service for accurate diagnosis "
                "and region-specific treatment guidance.",
                icon="⚠️",
            )

        st.info(f"ℹ️ {plan.disclaimer}", icon="ℹ️")

        # ── Sources and References ──────────────────────────────────────────
        if result.sources:
            st.markdown("---")
            st.markdown("### 📚 Sources and References")
            st.caption(
                "The following sources informed this analysis. "
                "All content is retrieved directly from the curated knowledge base — not AI-generated."
            )
            for src in result.sources:
                # Extract a short organisation name from the title (text before " — ")
                org_name = src.source_title.split(" — ")[0] if " — " in src.source_title else ""
                display_title = src.source_title.split(" — ", 1)[-1] if " — " in src.source_title else src.source_title

                link_html = (
                    f'<a href="{src.source_url}" target="_blank" rel="noopener">🔗 View source</a>'
                    if src.source_url else
                    '<span style="color:#6b7280;font-size:0.8rem">No URL available</span>'
                )
                relevance_note = (
                    f"Matched for: <em>{src.topic.title()}</em> on <em>{src.crop.title()}</em>"
                    f" — relevance score {src.relevance_score:.0%}"
                )
                st.markdown(
                    f'<div class="source-card">'
                    f'  <span class="src-title">📄 {display_title}</span>'
                    + (f'  <span class="src-org">🏛 {org_name}</span>' if org_name else "")
                    + f'  <span class="src-relevance">{relevance_note}</span>'
                    f'  <div style="margin-top:0.4rem">{link_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        elif not result.sources:
            st.markdown("---")
            st.info(
                "No source references are available for this analysis. "
                "The knowledge base did not find closely matching entries for the reported crop and symptoms.",
                icon="📚",
            )

        # Save action plan / follow-up
        st.markdown("---")
        st.markdown("### 💾 Save & Follow-Up")
        if result.report_id:
            st.success(f"✅ Action plan saved (Report ID: {result.report_id}). Follow-up tasks were automatically created.")
            st.info("Navigate to **📋 Follow-Up Tasks** to view and manage your follow-up schedule.")

            with st.expander("➕ Add Custom Follow-Up Task"):
                custom_task = st.text_input("Task description", placeholder="e.g., Apply fungicide to affected rows")
                custom_due = st.date_input("Due date", value=date.today())
                if st.button("Save Follow-Up Task"):
                    if custom_task.strip():
                        task = FollowUpTask(
                            task_description=custom_task.strip(),
                            due_date=custom_due,
                            report_id=result.report_id,
                        )
                        tid = save_followup_task(task)
                        st.success(f"Follow-up task saved (ID: {tid}).")
                    else:
                        st.error("Please enter a task description.")
        else:
            st.info("Run an analysis first to save an action plan.")


# ---------------------------------------------------------------------------
# FOLLOW-UP TASKS PAGE
# ---------------------------------------------------------------------------
elif page == "📋 Follow-Up Tasks":
    st.markdown("## 📋 Follow-Up Tasks Dashboard")

    try:
        dashboard = get_followup_dashboard()
    except Exception as exc:
        st.error(f"Could not load follow-up tasks: {exc}")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("🕐 Pending", len(dashboard["pending"]))
    col2.metric("✅ Completed", len(dashboard["completed"]))
    col3.metric("⏭️ Skipped", len(dashboard["skipped"]))

    st.markdown("---")

    if not dashboard["total"]:
        st.info("No follow-up tasks yet. Run an analysis to automatically create follow-up tasks.")
    else:
        # Pending tasks
        if dashboard["pending"]:
            st.markdown("### 🕐 Pending Tasks")
            for task in dashboard["pending"]:
                due = task.get("due_date", "No due date")
                # Check if overdue
                try:
                    due_obj = date.fromisoformat(due)
                    overdue = due_obj < date.today()
                except (TypeError, ValueError):
                    overdue = False

                with st.expander(f"{'🔴 OVERDUE' if overdue else '🟡'} {task['task_description']} (Due: {due})"):
                    st.markdown(f"**Report ID:** {task['report_id']}")
                    st.markdown(f"**Created:** {task['created_at']}")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        notes = st.text_area(
                            "Observation notes",
                            key=f"notes_{task['id']}",
                            placeholder="What did you observe?",
                            height=80,
                        )
                    with col_b:
                        st.markdown("")
                        if st.button("✅ Mark Complete", key=f"complete_{task['id']}"):
                            update_task_status(FollowUpTaskUpdate(
                                task_id=task["id"],
                                status="completed",
                                observation_notes=notes or None,
                            ))
                            st.success("Task marked complete!")
                            st.rerun()
                        if st.button("⏭️ Skip Task", key=f"skip_{task['id']}"):
                            update_task_status(FollowUpTaskUpdate(
                                task_id=task["id"],
                                status="skipped",
                                observation_notes=notes or None,
                            ))
                            st.info("Task skipped.")
                            st.rerun()

        # Completed tasks
        if dashboard["completed"]:
            st.markdown("### ✅ Completed Tasks")
            for task in dashboard["completed"]:
                with st.expander(f"✅ {task['task_description']}"):
                    st.markdown(f"**Updated:** {task.get('updated_at', 'N/A')}")
                    if task.get("observation_notes"):
                        st.markdown(f"**Notes:** {task['observation_notes']}")

        # Skipped tasks
        if dashboard["skipped"]:
            st.markdown("### ⏭️ Skipped Tasks")
            for task in dashboard["skipped"]:
                st.markdown(f"- {task['task_description']}")


# ---------------------------------------------------------------------------
# PREVIOUS REPORTS PAGE
# ---------------------------------------------------------------------------
elif page == "📁 Previous Reports":
    st.markdown("## 📁 Previous Analysis Reports")

    try:
        reports = get_all_reports_summary()
    except Exception as exc:
        st.error(f"Could not load reports: {exc}")
        st.stop()

    if not reports:
        st.info("No reports saved yet. Run an analysis to create your first report.")
    else:
        st.markdown(f"**{len(reports)} report(s) found.**")
        for report in reports:
            crop = report.get("crop_name", "Unknown")
            loc = report.get("location", "Unknown")
            created = report.get("created_at", "")[:16]
            with st.expander(f"🌾 {crop.title()} — {loc} ({created})"):
                st.markdown(f"**Report ID:** {report['id']}  **Query ID:** {report['query_id']}")
                st.markdown(f"**Symptoms:** {report.get('symptoms', 'N/A')}")
                st.markdown("**Action Plan Summary:**")
                st.markdown(report.get("action_plan", "N/A"))
                if report.get("research_summary"):
                    st.markdown(f"**Research:** {report['research_summary']}")
                if report.get("weather_summary"):
                    st.markdown(f"**Weather:** {report['weather_summary']}")
                if report.get("uncertainty_notes"):
                    st.markdown(
                        f'<div class="warning-box">⚠️ {report["uncertainty_notes"]}</div>',
                        unsafe_allow_html=True,
                    )

                # Sources
                detail = get_report_detail(report["id"])
                if detail and detail.get("sources"):
                    st.markdown("**Sources:**")
                    for src in detail["sources"]:
                        title = src.get("source_title", "Unknown source")
                        url = src.get("source_url", "")
                        link_html = (
                            f'<a href="{url}" target="_blank" rel="noopener">🔗 View source</a>'
                            if url else '<span style="color:#6b7280;font-size:0.8rem">No URL available</span>'
                        )
                        st.markdown(
                            f'<div class="source-card">'
                            f'  <span class="src-title">📄 {title}</span>'
                            f'  <div style="margin-top:0.35rem">{link_html}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                # Follow-up tasks for this report
                tasks = get_all_tasks(report_id=report["id"])
                if tasks:
                    st.markdown(f"**Follow-up tasks:** {len(tasks)} ({sum(1 for t in tasks if t['status']=='pending')} pending)")
