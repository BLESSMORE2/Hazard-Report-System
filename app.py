"""
HIRS – Hazard Identification & Reporting System (Prototype)
Full requirements coverage: reporting, risk/triage, CAPA, investigation, dashboards, exports, admin, reference.
Streamlit only – no backend.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from config import (
    WORKFLOW_STATUSES,
    CLASSIFICATION_TYPES,
    TAGS_OPTIONS,
    HAZARD_AREAS,
    SUBCATEGORIES,
    LIKELIHOOD_LABELS,
    SEVERITY_LABELS,
    risk_matrix_level,
    RISK_LEVELS_DISPLAY,
    ESCALATION_RULES,
    CAPA_ACTION_TYPES,
    CAPA_PRIORITIES,
    ROLES,
    ROLE_PERMISSIONS,
    REFERENCE_LINKS,
)

# ---------------------------------------------------------------------------
# Page config & session state
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="HIRS – Hazard Reporting",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def _init_session():
    if "hazards" not in st.session_state:
        st.session_state.hazards = []
    if "audit_log" not in st.session_state:
        st.session_state.audit_log = []
    if "selected_id" not in st.session_state:
        st.session_state.selected_id = None
    if "current_role" not in st.session_state:
        st.session_state.current_role = ROLES[0]
    if "admin_stations" not in st.session_state:
        st.session_state.admin_stations = "Station A\nStation B\nMain Ramp"
    if "admin_departments" not in st.session_state:
        st.session_state.admin_departments = "Ramp\nCargo\nGSE\nSafety"
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Report"

_init_session()

# All pages (single source of truth for nav)
PAGES = [
    "Report",
    "Hazards",
    "Risk & Triage",
    "CAPA",
    "Investigation",
    "Dashboard",
    "Exports",
    "Admin",
    "Reference",
]
PAGE_ICONS = ["📋", "📂", "⚖️", "📌", "🔍", "📊", "📤", "⚙️", "📎"]
PAGES_DISPLAY = [f"{icon} {name}" for icon, name in zip(PAGE_ICONS, PAGES)]

# ---------------------------------------------------------------------------
# Custom CSS (professional polish – cards, metrics, empty states, print)
# ---------------------------------------------------------------------------
def _inject_css():
    st.markdown("""
    <style>
    /* App background – light main area under purple header */
    [data-testid="stAppViewContainer"] > .main { background: #f5f7fa; padding-top: 0; }
    /* Main content spacing – push below fixed header so sidebar + top bar connect */
    .main .block-container { padding-top: 4rem; padding-bottom: 2rem; max-width: 1400px; background: #ffffff; border-radius: 12px 12px 0 0; box-shadow: 0 6px 20px rgba(0,0,0,0.12); }
    /* Card-style panels and expanders */
    .stExpander { border-radius: 10px; border: 1px solid #e0e0e0; box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 0.5rem; }
    [data-testid="stExpander"] summary { padding: 0.6rem 0.8rem; font-weight: 600; border-radius: 10px; }
    /* Risk/status badges */
    .hirs-badge { display: inline-block; padding: 3px 10px; border-radius: 14px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.02em; }
    .hirs-risk-low { background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
    .hirs-risk-medium { background: #fff8e1; color: #f57f17; border: 1px solid #ffecb3; }
    .hirs-risk-high { background: #ffebee; color: #c62828; border: 1px solid #ffcdd2; }
    .hirs-risk-extreme { background: #b71c1c; color: #fff; border: 1px solid #8b0000; }
    .hirs-status-open { background: #e3f2fd; color: #1565c0; border: 1px solid #bbdefb; }
    .hirs-status-closed { background: #e8e8e8; color: #424242; border: 1px solid #bdbdbd; }
    /* Metric cards */
    [data-testid="stMetric"] { background: linear-gradient(135deg, #fafbfc 0%, #f5f7fa 100%); padding: 1rem; border-radius: 10px; border: 1px solid #e8ecf0; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
    [data-testid="stMetric"] label { font-weight: 600; color: #37474f; }
    /* Document branding and footer */
    .hirs-doc-meta { font-size: 0.85rem; color: #546e7a; margin-top: 0.5rem; padding: 0.5rem 0; }
    .hirs-footer { font-size: 0.78rem; color: #78909c; text-align: center; margin-top: 2rem; padding: 1.2rem 1rem; border-top: 1px solid #eceff1; background: #fafafa; border-radius: 0 0 8px 8px; }
    /* Empty state block */
    .hirs-empty { text-align: center; padding: 2.5rem 1.5rem; background: linear-gradient(180deg, #f8f9fa 0%, #fff 100%); border: 1px dashed #dee2e6; border-radius: 12px; margin: 1rem 0; }
    .hirs-empty-icon { font-size: 2.5rem; margin-bottom: 0.5rem; opacity: 0.8; }
    /* Section container */
    .hirs-section { padding: 1rem 1.2rem; margin: 0.8rem 0; background: #fff; border-radius: 10px; border: 1px solid #e8ecf0; }
    /* Risk matrix grid (for visual) */
    .hirs-matrix { border-collapse: collapse; font-size: 0.8rem; margin: 0.5rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .hirs-matrix th, .hirs-matrix td { padding: 0.4rem 0.6rem; text-align: center; border: 1px solid #e0e0e0; }
    .hirs-matrix th { background: #37474f; color: #fff; font-weight: 600; }
    .hirs-matrix .cell-low { background: #e8f5e9; }
    .hirs-matrix .cell-medium { background: #fff8e1; }
    .hirs-matrix .cell-high { background: #ffebee; }
    .hirs-matrix .cell-extreme { background: #b71c1c; color: #fff; }
    .hirs-matrix .cell-active { box-shadow: inset 0 0 0 3px #5e4a7a; font-weight: 700; }
    /* Print: hide sidebar and footer */
    @media print { .css-1d391kg { display: none !important; } [data-testid="stSidebar"] { display: none !important; } .hirs-footer { display: none !important; } .block-container { max-width: 100% !important; } }
    /* ========== DC/OS-style: top header bar – fixed, full width, connects to sidebar ========== */
    .hirs-top-header {
        position: fixed !important; top: 0 !important; left: 0 !important; width: 100% !important;
        height: 52px !important; box-sizing: border-box !important; margin: 0 !important; z-index: 1000 !important;
        background: linear-gradient(90deg, #3f2b5f 0%, #5e4a7a 50%, #4a3d6a 100%); color: #fff;
        padding: 0 1.25rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25); font-family: inherit;
    }
    .hirs-top-header-left { display: flex; align-items: center; gap: 0.75rem; }
    .hirs-top-header-logo { font-size: 1.1rem; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; }
    .hirs-top-header-tagline { font-size: 0.75rem; opacity: 0.9; margin-left: 0.25rem; }
    .hirs-top-header-right { display: flex; align-items: center; gap: 1rem; }
    .hirs-top-header-divider { width: 1px; height: 1.25rem; background: rgba(255,255,255,0.4); }
    /* Page title row in main content */
    .hirs-page-title-row { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem; }
    .hirs-page-title { font-size: 1.6rem; font-weight: 700; color: #3f2b5f; margin: 0; }
    /* Sidebar: same purple as header for top 52px so they connect, then dark gray (L-shaped frame) */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #3f2b5f 0%, #5e4a7a 52px, #2d2d2d 52px, #1f1f1f 100%) !important;
        padding-top: 52px !important;
        min-height: 100vh;
    }
    [data-testid="stSidebar"] > div { padding-top: 0 !important; }
    [data-testid="stSidebar"] .stMarkdown { color: #e0e0e0 !important; }
    [data-testid="stSidebar"] .stMarkdown p { color: #e0e0e0 !important; }
    [data-testid="stSidebar"] label { color: #e0e0e0 !important; }
    [data-testid="stSidebar"] .stCaptionContainer { color: #b0b0b0 !important; }
    [data-testid="stSidebar"] .stRadio > div { flex-direction: column; gap: 0; }
    [data-testid="stSidebar"] .stRadio label { background: transparent !important; padding: 0.5rem 0.75rem !important; border-radius: 4px !important; margin-bottom: 2px !important; color: #e0e0e0 !important; font-weight: 500 !important; }
    [data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.08) !important; }
    [data-testid="stSidebar"] .stRadio label[data-checked="true"], [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) { background: #5e4a7a !important; color: #fff !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] [data-testid="stMetric"] { background: rgba(255,255,255,0.06) !important; border: 1px solid rgba(255,255,255,0.1); color: #e0e0e0 !important; }
    [data-testid="stSidebar"] [data-testid="stMetric"] label { color: #b0b0b0 !important; }
    [data-testid="stSidebar"] [data-testid="stMetric"] [data-testid="stMetricValue"] { color: #fff !important; }
    [data-testid="stSidebar"] select { background: #3d3d3d !important; color: #fff !important; border-color: #555 !important; }
    [data-testid="stSidebar"] .stButton button { background: #5e4a7a !important; color: #fff !important; border: none !important; }
    [data-testid="stSidebar"] .stButton button:hover { background: #6d5a8a !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }
    /* Primary buttons in main: purple accent */
    .stButton button[kind="primary"] { background: linear-gradient(90deg, #5e4a7a, #4a3d6a) !important; color: #fff !important; }
    </style>
    """, unsafe_allow_html=True)

def _risk_badge(level):
    if not level:
        return "—"
    c = "hirs-risk-low"
    if level in ("Medium", "Moderate"): c = "hirs-risk-medium"
    elif level == "High": c = "hirs-risk-high"
    elif level in ("Extreme", "Critical"): c = "hirs-risk-extreme"
    return f'<span class="hirs-badge {c}">{level}</span>'

def _status_badge(status):
    if not status:
        return "—"
    open_s = ["Draft", "Submitted", "Triage", "Assigned actions", "In progress", "Awaiting verification"]
    c = "hirs-status-open" if status in open_s else "hirs-status-closed"
    return f'<span class="hirs-badge {c}">{status}</span>'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _next_id():
    n = len(st.session_state.hazards) + 1
    return f"HZ-{n:04d}"

def _format_dt(value):
    if not value:
        return "—"
    try:
        s = str(value).replace("Z", "+00:00")[:19]
        d = datetime.fromisoformat(s)
        return d.strftime("%d %b %Y, %H:%M")
    except Exception:
        return str(value)

def _log_audit(action: str, entity_id: str = "", detail: str = ""):
    st.session_state.audit_log.append({
        "timestamp": datetime.now().isoformat(),
        "role": st.session_state.current_role,
        "action": action,
        "entity_id": entity_id,
        "detail": detail,
    })

def _get_hazard(hid):
    for h in st.session_state.hazards:
        if h.get("id") == hid:
            return h
    return None

def _empty_state(icon: str, title: str, message: str, action: str = ""):
    st.markdown(
        f'<div class="hirs-empty">'
        f'<div class="hirs-empty-icon">{icon}</div>'
        f'<p style="font-weight:600;color:#37474f;margin:0 0 0.25rem;">{title}</p>'
        f'<p style="color:#546e7a;margin:0;font-size:0.9rem;">{message}</p>'
        f'<p style="color:#0d47a1;margin:0.5rem 0 0;font-size:0.85rem;">{action}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

def _load_sample_data():
    base = datetime.now()
    samples = [
        {"id": "HZ-0001", "title": "FOD near stand 14", "category": "Airside / Ramp", "subcategory": "FOD (foreign object debris) and housekeeping",
         "severity_reporter": "High", "station": "Main Ramp", "area": "Stand 14", "gps_note": "", "datetime": (base - timedelta(days=2)).strftime("%Y-%m-%dT10:30:00"),
         "description": "Metal bolt and loose cable observed near stand 14 during pushback. Removed by ramp agent.", "people_exposed": "2 ramp agents", "potential_consequence": "FOD ingestion",
         "immediate_actions": "Bolt and cable removed; area swept", "witnesses": "Ramp lead", "attachment_names": [], "classification_type": "Hazard", "tags": ["Safety"],
         "status": "Awaiting verification", "rejection_reason": "", "reporter_summary": "J. Smith • Ramp", "likelihood": 3, "severity": 4, "risk_score": 12, "risk_level": "Medium",
         "capa_actions": [{"id": "HZ-0001-A1", "title": "Daily FOD walk", "type": "Preventive", "owner": "Ramp Lead", "department": "Ramp", "priority": "Medium",
                           "due_date": (base + timedelta(days=7)).isoformat()[:10], "required_evidence": "Checklist", "completion_date": None, "verification_result": "", "effectiveness_notes": "", "created_at": (base - timedelta(days=1)).isoformat()}],
         "investigation": {}, "created_at": (base - timedelta(days=2)).isoformat(), "updated_at": base.isoformat(), "submitted_at": (base - timedelta(days=2)).isoformat(),
         "triaged_at": (base - timedelta(days=1)).isoformat(), "closed_at": None},
        {"id": "HZ-0002", "title": "Fuel spill during refuel", "category": "Aircraft servicing", "subcategory": "Refueling/fueling safety",
         "severity_reporter": "Critical", "station": "Main Ramp", "area": "Stand 8", "gps_note": "", "datetime": (base - timedelta(days=1)).strftime("%Y-%m-%dT14:00:00"),
         "description": "Small fuel spill during disconnect; spill contained and reported.", "people_exposed": "Refueler", "potential_consequence": "Fire risk",
         "immediate_actions": "Spill kit used; supervisor notified", "witnesses": "", "attachment_names": [], "classification_type": "Incident", "tags": ["Safety", "Environment"],
         "status": "Triage", "rejection_reason": "", "reporter_summary": "Reported anonymously", "likelihood": 2, "severity": 5, "risk_score": 10, "risk_level": "Medium",
         "capa_actions": [], "investigation": {}, "created_at": (base - timedelta(days=1)).isoformat(), "updated_at": base.isoformat(),
         "submitted_at": (base - timedelta(days=1)).isoformat(), "triaged_at": None, "closed_at": None},
    ]
    for h in samples:
        if not any(ex.get("id") == h["id"] for ex in st.session_state.hazards):
            st.session_state.hazards.append(h)
    _log_audit("Sample data loaded", "", f"{len(samples)} sample reports")

# ---------------------------------------------------------------------------
# Module A – Hazard reporting (Draft, subcategory, attachments)
# ---------------------------------------------------------------------------
def render_report():
    st.subheader("New hazard report")
    st.caption("Submit in under 2 minutes. Mobile-first. Draft, named/confidential/anonymous, attachments.")
    st.success("⏱️ **Designed for speed:** Complete the required fields (*) and submit in under 2 minutes. Save as Draft to finish later.")
    st.markdown("---")

    with st.form("hazard_form", clear_on_submit=True):
        st.subheader("When & where")
        st.caption("Date/time observed; station/airport; specific area (stand, gate, cargo shed, GSE park); optional GPS.")
        c1, c2, c3 = st.columns(3)
        with c1:
            date_observed = st.date_input("Date observed", value=datetime.now().date(), help="When the hazard was observed")
            time_observed = st.time_input("Time observed", value=datetime.now().time())
        with c2:
            station = st.text_input("Station / airport", max_chars=120, value="", placeholder="e.g. Main Ramp, Terminal 2")
            area = st.text_input("Area (stand / gate / cargo shed / GSE park) *", max_chars=120, placeholder="e.g. Stand 14, Gate B12")
        with c3:
            gps_note = st.text_input("GPS / location note (optional)", max_chars=200, placeholder="Coordinates or landmark")

        st.markdown("---")
        st.subheader("Hazard details")
        st.caption("Category/subcategory; description; people exposed; potential consequence; immediate action; witnesses.")
        title = st.text_input("Short title *", max_chars=120, placeholder="Brief descriptive title (e.g. FOD near stand 7)")
        category = st.selectbox("Category *", [""] + HAZARD_AREAS, help="Primary hazard area per HIRS taxonomy")
        subcategory = ""
        if category and category in SUBCATEGORIES:
            subcategory = st.selectbox(
                "Subcategory",
                [""] + SUBCATEGORIES[category],
                key="subcat_report",
                help="Optional; refines the category",
            )
        description = st.text_area(
            "What happened or what could have happened? *",
            max_chars=1500,
            height=120,
            placeholder="Describe the hazard, near miss, or unsafe condition. Include what you saw and what could have happened.",
        )
        people_exposed = st.text_input("People exposed (who and how many?)", max_chars=200, placeholder="e.g. 2 ramp agents, pilot in cockpit")
        potential_consequence = st.text_area("Potential consequence", max_chars=600, height=60, placeholder="Worst credible outcome if not addressed")
        immediate_actions = st.text_area("Immediate action taken", max_chars=1000, height=80, placeholder="Steps already taken to reduce risk")
        witnesses = st.text_input("Witnesses (optional)", max_chars=300, placeholder="Names or teams who witnessed")

        st.markdown("---")
        st.subheader("Attachments (photos / video)")
        attachments_upload = st.file_uploader(
            "Upload photos or documents",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            help="In this prototype files are not stored; names only for demo.",
        )
        attachment_names = [f.name for f in (attachments_upload or [])]

        st.subheader("Classification")
        col_a, col_b = st.columns(2)
        with col_a:
            classification_type = st.selectbox("Type", [""] + CLASSIFICATION_TYPES, index=1, help="Hazard / Near miss / Incident / Unsafe act / Unsafe condition")
        with col_b:
            tags = st.multiselect("Tags (optional)", TAGS_OPTIONS, help="Safety, Security, Environment, Quality")

        st.markdown("---")
        st.subheader("Reporter")
        reporting_mode = st.radio(
            "Reporting mode",
            ["Named", "Confidential (limited access)", "Anonymous"],
            horizontal=True,
        )
        is_anonymous = "Anonymous" in reporting_mode
        reporter_name = ""
        employee_id = ""
        department = ""
        role = ""
        contact = ""
        if not is_anonymous:
            r1, r2 = st.columns(2)
            with r1:
                reporter_name = st.text_input("Name (optional)", max_chars=120)
                employee_id = st.text_input("Employee ID (optional)", max_chars=60)
                department = st.text_input("Department / team", max_chars=160)
            with r2:
                role = st.text_input("Role", max_chars=120)
                contact = st.text_input("Contact (optional)", max_chars=160, placeholder="Phone or email")

        st.subheader("Perceived risk (reporter)")
        severity_reporter = st.selectbox(
            "Perceived risk level *",
            [""] + ["Low", "Moderate", "High", "Critical"],
            help="Your initial assessment; Safety may reassess during triage",
        )

        col_submit, _ = st.columns(2)
        with col_submit:
            submit_as_draft = st.form_submit_button("💾 Save as Draft")
            submit_final = st.form_submit_button("✅ Submit report")
        if submit_as_draft or submit_final:
            missing = []
            if not title.strip(): missing.append("Short title")
            if not category: missing.append("Category")
            if not description.strip(): missing.append("Description (what happened)")
            if not area.strip(): missing.append("Area (stand / gate / bay)")
            if missing:
                st.error("**Please complete the required fields:** " + ", ".join(missing) + ".")
                return
            dt_str = f"{date_observed}T{time_observed.isoformat()}"
            reporter_summary = (
                "Reported anonymously"
                if is_anonymous
                else " • ".join(filter(None, [reporter_name, employee_id, department, role, contact])) or "Details not supplied"
            )
            status = "Draft" if submit_as_draft else "Submitted"
            hazard = {
                "id": _next_id(),
                "title": title,
                "category": category,
                "subcategory": subcategory,
                "severity_reporter": severity_reporter or "Not given",
                "station": station,
                "area": area,
                "gps_note": gps_note,
                "datetime": dt_str,
                "description": description,
                "people_exposed": people_exposed,
                "potential_consequence": potential_consequence,
                "immediate_actions": immediate_actions,
                "witnesses": witnesses,
                "attachment_names": attachment_names,
                "classification_type": classification_type or "Hazard",
                "tags": tags,
                "status": status,
                "rejection_reason": "",
                "reporter_summary": reporter_summary,
                "likelihood": None,
                "severity": None,
                "risk_score": None,
                "risk_level": None,
                "capa_actions": [],
                "investigation": {},
                "reporter_feedback": "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "submitted_at": None if submit_as_draft else datetime.now().isoformat(),
                "triaged_at": None,
                "closed_at": None,
            }
            st.session_state.hazards.append(hazard)
            st.session_state.selected_id = hazard["id"]
            _log_audit("Report created" if submit_as_draft else "Report submitted", hazard["id"], status)
            st.success(f"Report {hazard['id']} saved as {status}.")
            st.rerun()

# ---------------------------------------------------------------------------
# Hazards list + detail + status + rejection reason
# ---------------------------------------------------------------------------
def render_hazards():
    st.subheader("Hazards list")
    st.caption("Filter by station, risk, status. Update workflow status; reject with reason. Optionally add feedback to reporter.")
    hazards = st.session_state.hazards
    if not hazards:
        _empty_state("📋", "No hazards yet", "Create your first report from the **Report** page to see it here.", "👉 Use the sidebar to go to **Report**.")
        return

    # View toggle: Table or Cards
    view_mode = st.radio("View", ["Cards (expand for detail)", "Table"], horizontal=True, key="hazards_view")

    # Filters
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        risk_f = st.selectbox("Risk level", ["All"] + RISK_LEVELS_DISPLAY, key="f_risk")
    with f2:
        status_f = st.selectbox("Status", ["All"] + WORKFLOW_STATUSES, key="f_status")
    with f3:
        stations = sorted({h.get("station") or "—" for h in hazards})
        station_f = st.selectbox("Station", ["All"] + stations, key="f_station")
    with f4:
        search = st.text_input("Search (title, area, category, ID)", key="f_search", placeholder="Type to filter...")

    filtered = hazards
    if risk_f != "All":
        filtered = [h for h in filtered if h.get("risk_level") == risk_f]
    if status_f != "All":
        filtered = [h for h in filtered if h.get("status") == status_f]
    if station_f != "All":
        filtered = [h for h in filtered if (h.get("station") or "—") == station_f]
    if search:
        q = search.strip().lower()
        filtered = [h for h in filtered if q in ((h.get("title") or "") + (h.get("area") or "") + (h.get("category") or "") + (h.get("id") or "") + (h.get("description") or "")).lower()]

    if not filtered:
        _empty_state("🔍", "No matches", f"No reports match the current filters. Try changing risk, status, station or search.", f"Clear filters to see all {len(hazards)} reports.")
        return

    st.markdown(f"**Showing {len(filtered)} of {len(hazards)}** reports")
    st.markdown("---")

    if view_mode == "Table":
        table_data = []
        for h in sorted(filtered, key=lambda x: x.get("created_at", ""), reverse=True):
            table_data.append({
                "ID": h["id"],
                "Title": (h.get("title") or "—")[:40],
                "Risk": h.get("risk_level") or h.get("severity_reporter") or "—",
                "Status": h.get("status", "—"),
                "Station": h.get("station") or "—",
                "Area": h.get("area") or "—",
                "Created": _format_dt(h.get("created_at")),
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True)
        st.caption("Switch to **Cards** view to update status, add feedback, or see full detail.")
        return

    for h in sorted(filtered, key=lambda x: x.get("created_at", ""), reverse=True):
        risk_display = h.get("risk_level") or h.get("severity_reporter") or "—"
        expander_label = f"{h['id']} — {h.get('title', '—')[:45]} | Risk: {risk_display} | {h.get('status', '—')}"
        with st.expander(expander_label, expanded=(h["id"] == st.session_state.selected_id)):
            badge_risk = _risk_badge(risk_display)
            badge_status = _status_badge(h.get("status"))
            st.markdown(f"**Risk:** {badge_risk}  **Status:** {badge_status}", unsafe_allow_html=True)
            c_left, c_right = st.columns([3, 1])
            with c_left:
                st.markdown(f"**Category:** {h.get('category', '—')} · **Subcategory:** {h.get('subcategory', '—')} · **Area:** {h.get('area', '—')}")
                st.caption((h.get("description") or "")[:250] + ("..." if len(h.get("description") or "") > 250 else ""))
            with c_right:
                try:
                    idx = WORKFLOW_STATUSES.index(h["status"])
                except ValueError:
                    idx = 0
                new_status = st.selectbox("Status", WORKFLOW_STATUSES, index=idx, key=f"status_{h['id']}")
                if new_status == "Rejected":
                    reason = st.text_input("Rejection reason *", key=f"rej_{h['id']}", value=h.get("rejection_reason", ""), placeholder="Explain why this report is rejected")
                    confirm_reject = st.checkbox("I confirm I want to reject this report", key=f"confirm_rej_{h['id']}")
                    if st.button("Apply status", key=f"apply_{h['id']}"):
                        if not reason.strip():
                            st.error("Please provide a rejection reason.")
                        elif not confirm_reject:
                            st.warning("Please confirm rejection by checking the box.")
                        else:
                            h["status"] = new_status
                            h["rejection_reason"] = reason
                            h["updated_at"] = datetime.now().isoformat()
                            h["closed_at"] = datetime.now().isoformat()
                            _log_audit("Status updated to Rejected", h["id"], reason)
                            st.rerun()
                else:
                    if st.button("Apply status", key=f"apply_{h['id']}"):
                        h["status"] = new_status
                        h["rejection_reason"] = "" if new_status != "Rejected" else h.get("rejection_reason", "")
                        h["updated_at"] = datetime.now().isoformat()
                        if new_status == "Closed":
                            h["closed_at"] = datetime.now().isoformat()
                        if new_status == "Triage" and not h.get("triaged_at"):
                            h["triaged_at"] = datetime.now().isoformat()
                        _log_audit("Status updated", h["id"], new_status)
                        st.rerun()

            if h.get("rejection_reason"):
                st.warning(f"**Rejection reason:** {h['rejection_reason']}")
            st.markdown("---")
            st.markdown("**Description**"); st.write(h.get("description", "—"))
            st.markdown("**Immediate actions**"); st.write(h.get("immediate_actions") or "—")
            st.markdown("**People exposed / Consequence**"); st.write(h.get("people_exposed") or "—"); st.write(h.get("potential_consequence") or "—")
            st.markdown("**Classification**"); st.write(f"{h.get('classification_type', '—')} | Tags: {', '.join(h.get('tags', [])) or '—'}")
            st.markdown("**Attachments**"); st.caption(", ".join(h.get("attachment_names", [])) or "None")
            st.markdown("**Risk (triage)**"); st.write(f"L×S = {h.get('risk_score', '—')} → {h.get('risk_level', 'Not assessed')}")
            st.markdown("**Reporter**"); st.caption(h.get("reporter_summary", "—"))
            st.markdown("**Feedback to reporter**")
            st.caption("(Reporter receives this when implemented; supports higher reporting rate per requirements.)")
            if "reporter_feedback" not in h:
                h["reporter_feedback"] = ""
            new_feedback = st.text_area("Add or edit feedback for the reporter", value=h.get("reporter_feedback", ""), key=f"feedback_{h['id']}", height=60, placeholder="e.g. Thank you for reporting. We have assigned actions and will follow up.")
            if st.button("Save feedback", key=f"savefb_{h['id']}"):
                h["reporter_feedback"] = new_feedback
                h["updated_at"] = datetime.now().isoformat()
                _log_audit("Reporter feedback updated", h["id"], "")
                st.rerun()
            st.caption(f"Created: {_format_dt(h.get('created_at'))} · Submitted: {_format_dt(h.get('submitted_at'))} · Updated: {_format_dt(h.get('updated_at'))}")

# ---------------------------------------------------------------------------
# Module B – Risk assessment and triage (5×5 matrix, escalation, triage rules)
# ---------------------------------------------------------------------------
def render_risk_triage():
    st.subheader("Risk assessment and triage")
    st.caption("5×5 Likelihood × Severity matrix. Auto-calculated risk level and escalation rules.")
    hazards = [h for h in st.session_state.hazards if h.get("status") not in ("Draft", "Rejected")]
    if not hazards:
        _empty_state("⚖️", "No reports to triage", "Only submitted (non-draft, non-rejected) reports appear here.", "👉 Submit a report from **Report** or load **Sample data**.")
        return

    hid = st.selectbox(
        "Select report to assess",
        [h["id"] for h in hazards],
        format_func=lambda x: f"{x} – {_get_hazard(x).get('title', '')[:45]}",
        help="Only submitted (non-draft, non-rejected) reports appear",
    )
    h = _get_hazard(hid)
    if not h:
        return

    st.markdown("---")
    st.subheader(f"Report {h['id']}: {h.get('title', '')}")
    st.write("**Category:**", h.get("category"), "| **Subcategory:**", h.get("subcategory", "—"))
    st.caption(f"Observed: {_format_dt(h.get('datetime'))} at {h.get('area', '—')}")

    st.markdown("---")
    st.markdown("**Set likelihood and severity (1–5)**")
    c1, c2 = st.columns(2)
    with c1:
        likelihood = st.selectbox("Likelihood", list(LIKELIHOOD_LABELS.keys()), format_func=lambda k: LIKELIHOOD_LABELS[k], key="tri_like")
    with c2:
        severity = st.selectbox("Severity", list(SEVERITY_LABELS.keys()), format_func=lambda k: SEVERITY_LABELS[k], key="tri_sev")

    score, level = risk_matrix_level(likelihood, severity)
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("Risk score (L × S)", score, "")
    with col_m2:
        st.metric("Risk level", level, ESCALATION_RULES.get(level, "")[:50] + "...")
    st.markdown("**Escalation rule:**")
    st.info(ESCALATION_RULES.get(level, "—"))

    # Visual 5×5 matrix with current cell highlighted
    st.markdown("**Risk matrix (5×5)** — Selected cell: L{likelihood} × S{severity}")
    level_to_class = {"Low": "cell-low", "Medium": "cell-medium", "High": "cell-high", "Extreme": "cell-extreme"}
    rows_html = []
    for L in range(1, 6):
        cells = []
        for S in range(1, 6):
            s, lvl = risk_matrix_level(L, S)
            cls = level_to_class.get(lvl, "")
            if L == likelihood and S == severity:
                cls += " cell-active"
            cells.append(f'<td class="{cls}">{s}</td>')
        rows_html.append("<tr><th>L" + str(L) + "</th>" + "".join(cells) + "</tr>")
    header = "<tr><th></th>" + "".join(f'<th>S{j}</th>' for j in range(1, 6)) + "</tr>"
    st.markdown(f'<table class="hirs-matrix"><thead>{header}</thead><tbody>' + "".join(rows_html) + "</tbody></table>", unsafe_allow_html=True)

    # Triage decision rules (6.2)
    if level == "Extreme":
        st.error("**Stop/contain checklist** – Notify Safety and Operations Manager immediately. Investigation mandatory.")
        with st.expander("Stop/contain checklist (prototype)"):
            st.checkbox("Activity stopped/contained")
            st.checkbox("Safety notified")
            st.checkbox("Operations Manager notified")
    cat = (h.get("category") or "").lower()
    if "fod" in cat or (h.get("subcategory") or "").lower().startswith("fod"):
        st.warning("**FOD-related:** Prompt safe removal, record cleanup, require photo evidence when possible.")
    if "refuel" in cat or "fuel" in (h.get("subcategory") or "").lower():
        st.warning("**Fueling-related:** Spill/fire risk checklist – notify responsible supervisor immediately.")

    if st.button("💾 Save risk assessment"):
        h["likelihood"] = likelihood
        h["severity"] = severity
        h["risk_score"] = score
        h["risk_level"] = level
        h["updated_at"] = datetime.now().isoformat()
        if not h.get("triaged_at"):
            h["triaged_at"] = datetime.now().isoformat()
        if h["status"] == "Submitted":
            h["status"] = "Triage"
        _log_audit("Risk assessment saved", h["id"], f"{level} (L{likelihood}×S{severity})")
        st.success(f"Risk assessment saved for {h['id']}: **{level}** (score {score}).")
        st.rerun()

# ---------------------------------------------------------------------------
# Module C – CAPA (multiple actions, due dates, evidence, verification, overdue)
# ---------------------------------------------------------------------------
def render_capa():
    st.subheader("Corrective and preventive actions (CAPA)")
    st.caption("Multiple actions per report. Owner, due date, evidence, verification. Overdue escalation.")

    hazards = st.session_state.hazards
    if not hazards:
        _empty_state("📌", "No hazards", "Create a report first, then add CAPA actions here.", "👉 Go to **Report** or load **Sample data**.")
        return

    hid = st.selectbox("Select report", [h["id"] for h in hazards], key="capa_hid", format_func=lambda x: f"{x} – {_get_hazard(x).get('title', '')[:35]}")
    h = _get_hazard(hid)
    if not h:
        return

    if "capa_actions" not in h:
        h["capa_actions"] = []

    st.subheader(f"Actions for {h['id']}")
    actions = h["capa_actions"]

    # Add action form
    with st.expander("Add new action"):
        with st.form("capa_form"):
            title = st.text_input("Title / description *", max_chars=200)
            action_type = st.selectbox("Type", CAPA_ACTION_TYPES)
            owner = st.text_input("Owner", max_chars=120)
            department = st.text_input("Department", max_chars=120)
            priority = st.selectbox("Priority", CAPA_PRIORITIES)
            due_date = st.date_input("Due date", value=datetime.now().date() + timedelta(days=14))
            required_evidence = st.text_area("Required evidence", max_chars=500)
            if st.form_submit_button("Add action"):
                if title:
                    actions.append({
                        "id": f"{h['id']}-A{len(actions)+1}",
                        "title": title,
                        "type": action_type,
                        "owner": owner,
                        "department": department,
                        "priority": priority,
                        "due_date": due_date.isoformat(),
                        "required_evidence": required_evidence,
                        "completion_date": None,
                        "verification_result": "",
                        "effectiveness_notes": "",
                        "created_at": datetime.now().isoformat(),
                    })
                    h["updated_at"] = datetime.now().isoformat()
                    _log_audit("CAPA action added", h["id"], title)
                    st.rerun()

    # List actions
    today = datetime.now().date()
    overdue_list = []
    for a in actions:
        due = a.get("due_date")
        try:
            due_d = datetime.fromisoformat(due).date() if due else None
        except Exception:
            due_d = None
        if due_d and due_d < today and not a.get("completion_date"):
            overdue_list.append(a)

    if overdue_list:
        st.warning(f"**{len(overdue_list)} overdue action(s)** – Escalate to supervisor and operations management. Safety receives summary of overdue High/Extreme.")
        for a in overdue_list:
            st.caption(f"Overdue: {a.get('title')} (due {a.get('due_date')})")

    for a in actions:
        due_str = a.get("due_date")
        try:
            due_d = datetime.fromisoformat(due_str).date() if due_str else None
        except Exception:
            due_d = None
        today = datetime.now().date()
        if due_d:
            if due_d < today and not a.get("completion_date"):
                due_label = f"⚠️ Overdue by {(today - due_d).days} days"
            elif due_d >= today and not a.get("completion_date"):
                delta = (due_d - today).days
                due_label = f"Due in {delta} day{'s' if delta != 1 else ''}"
            else:
                due_label = f"Due: {due_str}"
        else:
            due_label = f"Due: {due_str}"
        with st.expander(f"**{a.get('title')}** | {a.get('type')} | {due_label} | Owner: {a.get('owner')}"):
            st.write("**Priority:**", a.get("priority"), "| **Department:**", a.get("department"))
            st.write("**Required evidence:**", a.get("required_evidence") or "—")
            comp_val = a.get("completion_date")
            try:
                comp_date = datetime.fromisoformat(comp_val).date() if comp_val else None
            except Exception:
                comp_date = None
            completion = st.date_input("Completion date", key=f"capacomp_{a.get('id')}", value=comp_date)
            verif = st.text_input("Verification result", key=f"capaver_{a.get('id')}", value=a.get("verification_result", ""))
            eff = st.text_area("Effectiveness notes", key=f"capaeff_{a.get('id')}", value=a.get("effectiveness_notes", ""))
            if st.button("Update action", key=f"capabtn_{a.get('id')}"):
                a["completion_date"] = completion.isoformat() if completion else None
                a["verification_result"] = verif
                a["effectiveness_notes"] = eff
                _log_audit("CAPA action updated", h["id"], a.get("title"))
                st.rerun()

# ---------------------------------------------------------------------------
# Module D – Investigation (serious events, REDA-style, lessons learned)
# ---------------------------------------------------------------------------
def render_investigation():
    st.subheader("Investigation (serious events)")
    st.caption("Structured investigation with contributing factors, corrective recommendations, lessons learned. Optional REDA-style.")

    hazards = st.session_state.hazards
    if not hazards:
        _empty_state("🔍", "No hazards", "Select a report to add or view its investigation.", "👉 Create a report from **Report** or load **Sample data**.")
        return

    hid = st.selectbox("Select report", [h["id"] for h in hazards], key="inv_hid", format_func=lambda x: f"{x} – {_get_hazard(x).get('title', '')[:35]}")
    h = _get_hazard(hid)
    if not h:
        return

    if "investigation" not in h:
        h["investigation"] = {}

    inv = h["investigation"]
    st.subheader(f"Investigation for {h['id']}")

    with st.form("investigation_form"):
        summary = st.text_area("Investigation summary", value=inv.get("summary", ""), max_chars=2000, height=100)
        contributing_factors = st.text_area("Contributing factors (REDA-style: system factors)", value=inv.get("contributing_factors", ""), max_chars=1500, height=80)
        recommendations = st.text_area("Corrective recommendations", value=inv.get("recommendations", ""), max_chars=1500, height=80)
        lessons_learned = st.text_area("Lessons learned (for publication)", value=inv.get("lessons_learned", ""), max_chars=1500, height=80)
        reda_style = st.checkbox("Aligned with REDA-style (ramp event decision aid) template", value=inv.get("reda_style", False))
        if st.form_submit_button("Save investigation"):
            h["investigation"] = {
                "summary": summary,
                "contributing_factors": contributing_factors,
                "recommendations": recommendations,
                "lessons_learned": lessons_learned,
                "reda_style": reda_style,
                "updated_at": datetime.now().isoformat(),
            }
            h["updated_at"] = datetime.now().isoformat()
            _log_audit("Investigation saved", h["id"], "")
            st.success("Investigation saved.")
            st.rerun()

    if inv:
        st.markdown("---")
        st.markdown("**Saved investigation**")
        st.write("Summary:", inv.get("summary", "—"))
        st.write("Contributing factors:", inv.get("contributing_factors", "—"))
        st.write("Recommendations:", inv.get("recommendations", "—"))
        st.write("Lessons learned:", inv.get("lessons_learned", "—"))
        st.caption(f"REDA-style: {inv.get('reda_style', False)}")

# ---------------------------------------------------------------------------
# Module E – Dashboards (open by station/area/department/risk, overdue, KPIs, trends, heat map)
# ---------------------------------------------------------------------------
def render_dashboard():
    st.subheader("Dashboards")
    st.caption("Open hazards by station/risk; overdue actions; time-to-triage and time-to-close; trends; risk heat map.")
    hazards = st.session_state.hazards
    if not hazards:
        _empty_state("📊", "No data yet", "Submit reports from **Report** to see metrics and charts.", "👉 Go to **Report** or load **Sample data** from the sidebar.")
        return

    open_statuses = ["Submitted", "Triage", "Assigned actions", "In progress", "Awaiting verification"]
    open_h = [h for h in hazards if h.get("status") in open_statuses]

    # KPI row
    st.subheader("Key metrics")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total reports", len(hazards), help="All reports in this session")
    m2.metric("Open", len(open_h), help="Not yet closed or rejected")
    m3.metric("Closed", sum(1 for h in hazards if h.get("status") == "Closed"), "")
    m4.metric("Rejected", sum(1 for h in hazards if h.get("status") == "Rejected"), "")

    triaged = [h for h in hazards if h.get("triaged_at")]
    if triaged:
        def days_between(sub, tri):
            try:
                s = datetime.fromisoformat(sub.replace("Z", ""))
                t = datetime.fromisoformat(tri.replace("Z", ""))
                return (t - s).days
            except Exception:
                return None
        days_list = [days_between(h.get("submitted_at"), h.get("triaged_at")) for h in triaged]
        days_list = [d for d in days_list if d is not None]
        avg_triage = sum(days_list) / len(days_list) if days_list else 0
    else:
        avg_triage = None
    m5.metric("Avg days to triage", f"{avg_triage:.1f}" if avg_triage is not None else "—", "Submitted → triaged")

    closed = [h for h in hazards if h.get("closed_at")]
    if closed:
        def days_to_close(h):
            try:
                s = datetime.fromisoformat((h.get("submitted_at") or h.get("created_at") or "").replace("Z", ""))
                c = datetime.fromisoformat((h.get("closed_at") or "").replace("Z", ""))
                return (c - s).days
            except Exception:
                return None
        days_close = [d for d in [days_to_close(h) for h in closed] if d is not None]
        avg_close = sum(days_close) / len(days_close) if days_close else 0
    else:
        avg_close = None
    st.metric("Avg days to close", f"{avg_close:.1f}" if avg_close is not None else "—", "Submitted → closed")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["Open by station / risk", "Overdue & trends", "Heat map & hotspots"])

    with tab1:
        st.subheader("Open hazards by station")
        by_station = pd.DataFrame([{"Station": h.get("station") or "—", "Count": 1} for h in open_h])
        if not by_station.empty:
            by_station = by_station.groupby("Station", as_index=False).sum()
            st.bar_chart(by_station.set_index("Station"))
        st.subheader("Open hazards by risk level")
        by_risk = {}
        for r in RISK_LEVELS_DISPLAY:
            by_risk[r] = sum(1 for h in open_h if h.get("risk_level") == r)
        st.bar_chart(by_risk)

    with tab2:
        st.subheader("Overdue actions (by owner/department)")
        overdue_rows = []
        for h in hazards:
            for a in h.get("capa_actions", []):
                if a.get("completion_date"):
                    continue
                due = a.get("due_date")
                try:
                    due_d = datetime.fromisoformat(due).date() if due else None
                except Exception:
                    due_d = None
                if due_d and due_d < datetime.now().date():
                    overdue_rows.append({"Report": h["id"], "Action": a.get("title"), "Owner": a.get("owner"), "Department": a.get("department"), "Due": due})
        if overdue_rows:
            st.dataframe(pd.DataFrame(overdue_rows), use_container_width=True)
        else:
            st.success("No overdue actions.")
        st.subheader("Trend (reports by week)")
        created_dates = []
        for h in hazards:
            try:
                created_dates.append(datetime.fromisoformat((h.get("created_at") or "").replace("Z", "")).date())
            except Exception:
                pass
        if created_dates:
            df = pd.DataFrame({"date": created_dates})
            df["week"] = pd.to_datetime(df["date"]).dt.to_period("W").astype(str)
            weekly = df.groupby("week").size()
            st.bar_chart(weekly)
        else:
            st.caption("No date data.")

    with tab3:
        st.subheader("Recurring hazard hotspots (by category)")
        cat_counts = {}
        for h in hazards:
            c = h.get("category") or "Other"
            cat_counts[c] = cat_counts.get(c, 0) + 1
        st.bar_chart(cat_counts)
        st.subheader("Risk heat map (5×5 L×S)")
        st.caption("Rows = Likelihood 1–5, Columns = Severity 1–5. Cell = number of reports at that L×S.")
        heat = [[0]*5 for _ in range(5)]
        for h in hazards:
            L, S = h.get("likelihood"), h.get("severity")
            if L and S and 1 <= L <= 5 and 1 <= S <= 5:
                heat[L-1][S-1] = heat[L-1][S-1] + 1
        df_heat = pd.DataFrame(heat, index=[f"L{i}" for i in range(1,6)], columns=[f"S{j}" for j in range(1,6)])
        st.dataframe(df_heat.astype(int), use_container_width=True)

# ---------------------------------------------------------------------------
# Exports (CSV/Excel, printable investigation, audit log)
# ---------------------------------------------------------------------------
def render_exports():
    st.subheader("Exports")
    st.caption("Export to CSV for audits; printable investigation summary; audit trail.")
    hazards = st.session_state.hazards
    if not hazards:
        _empty_state("📤", "No data to export", "Create reports first, then return here to download CSV or print investigations.", "👉 Go to **Report** or load **Sample data**.")
        return

    st.subheader("Download data")
    rows = []
    for h in hazards:
        rows.append({
            "ID": h.get("id"),
            "Title": h.get("title"),
            "Category": h.get("category"),
            "Subcategory": h.get("subcategory"),
            "Status": h.get("status"),
            "Risk level": h.get("risk_level"),
            "Station": h.get("station"),
            "Area": h.get("area"),
            "Reporter feedback": h.get("reporter_feedback", ""),
            "Created": h.get("created_at"),
            "Submitted": h.get("submitted_at"),
            "Closed": h.get("closed_at"),
        })
    df = pd.DataFrame(rows)

    e1, e2, e3 = st.columns(3)
    with e1:
        st.download_button(
            "📥 Download hazards CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"hirs_hazards_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key="dl_hazards",
        )
    capa_rows = []
    for h in hazards:
        for a in h.get("capa_actions", []):
            capa_rows.append({
                "Report ID": h["id"],
                "Action": a.get("title"),
                "Type": a.get("type"),
                "Owner": a.get("owner"),
                "Department": a.get("department"),
                "Due date": a.get("due_date"),
                "Completion": a.get("completion_date"),
            })
    with e2:
        if capa_rows:
            df_capa = pd.DataFrame(capa_rows)
            st.download_button(
                "📥 Download CAPA CSV",
                data=df_capa.to_csv(index=False).encode("utf-8"),
                file_name=f"hirs_capa_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                key="dl_capa",
            )
        else:
            st.caption("No CAPA data to export.")
    with e3:
        if st.session_state.audit_log:
            df_audit = pd.DataFrame(st.session_state.audit_log)
            st.download_button(
                "📥 Download audit log CSV",
                data=df_audit.to_csv(index=False).encode("utf-8"),
                file_name=f"hirs_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                key="dl_audit",
            )
        else:
            st.caption("No audit entries yet.")

    st.markdown("---")
    st.subheader("Printable investigation summary")
    st.caption("Select a report with an investigation to print or save as PDF (browser Print).")
    hid = st.selectbox("Report", [h["id"] for h in hazards], key="exp_hid", format_func=lambda x: f"{x} – {_get_hazard(x).get('title', '')[:40]}")
    h = _get_hazard(hid)
    if h and h.get("investigation"):
        inv = h["investigation"]
        printable = f"""
# Investigation summary – {h['id']}
**Report:** {h.get('title')}
**Category:** {h.get('category')} | **Area:** {h.get('area')}

## Summary
{inv.get('summary', '—')}

## Contributing factors
{inv.get('contributing_factors', '—')}

## Recommendations
{inv.get('recommendations', '—')}

## Lessons learned
{inv.get('lessons_learned', '—')}

*Generated by HIRS prototype. Print this page for audit.*
"""
        st.markdown(printable)
        st.caption("Use browser **Print (Ctrl+P)** to save as PDF. Sidebar and footer are hidden when printing.")

# ---------------------------------------------------------------------------
# Admin (stations, areas, categories, risk matrix, users/roles)
# ---------------------------------------------------------------------------
def render_admin():
    st.subheader("Admin configuration")
    st.caption("Manage stations, departments, risk matrix, taxonomy, roles. Prototype: mock config.")
    tab_a, tab_b, tab_c = st.tabs(["Stations & departments", "Risk matrix", "Taxonomy & roles"])
    with tab_a:
        st.subheader("Stations / airports")
        st.session_state.admin_stations = st.text_area("Stations (one per line)", value=st.session_state.admin_stations, height=80)
        st.subheader("Departments")
        st.session_state.admin_departments = st.text_area("Departments (one per line)", value=st.session_state.admin_departments, height=80)
    with tab_b:
        st.subheader("Risk matrix (5×5)")
        st.markdown("Likelihood × Severity → Score → Level: **Low** (1–6), **Medium** (7–12), **High** (13–20), **Extreme** (21–25).")
        st.dataframe(pd.DataFrame({
            "Severity": list(SEVERITY_LABELS.values()),
            "L=1": ["Low"]*5,
            "L=2": ["Low"]*2 + ["Medium"]*3,
            "L=3": ["Low", "Medium", "Medium", "High", "High"],
            "L=4": ["Medium", "Medium", "High", "High", "Extreme"],
            "L=5": ["Medium", "High", "High", "Extreme", "Extreme"],
        }), use_container_width=True)
    with tab_c:
        st.subheader("Hazard categories (taxonomy)")
        for cat, sublist in SUBCATEGORIES.items():
            with st.expander(cat):
                st.write(", ".join(sublist))
        st.subheader("Users / roles")
        for r in ROLES:
            st.markdown(f"**{r}** — {ROLE_PERMISSIONS.get(r, '')}")

# ---------------------------------------------------------------------------
# Reference (full taxonomy, links, requirements, document metadata)
# ---------------------------------------------------------------------------
def render_reference():
    st.subheader("HIRS overview & reference")
    st.caption("Requirements document summary and reference reading.")
    st.markdown(
        '<p class="hirs-doc-meta">'
        "Prepared for: <strong>YESAYA YESAYA</strong> | Organization: Yesaya Yesaya | Date: 25 Feb 2026 | Version 1.0 | Document status: Draft for design & development"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    with st.expander("1. Executive summary", expanded=True):
        st.write("HIRS provides a fast, structured way for frontline staff to report hazards, near misses, and safety concerns; for supervisors and Safety (SMS/QHSE) teams to assess risk consistently; and for management to track actions to closure and learn from trends.")
        st.write("Designed for high-tempo ramp environments: FOD, vehicle-pedestrian conflict, aircraft servicing, cargo/baggage, GSE.")
        st.markdown("- Higher reporting rate (mobile, anonymous, feedback)  \n- Consistent prioritization (likelihood × severity matrix, escalation)  \n- Closed-loop CAPA with evidence and verification  \n- Dashboards: trends, hotspots, overdue actions, risk heat maps")

    with st.expander("2. Scope"):
        st.markdown("**In scope:** Hazard/near miss/incident reporting (mobile-first); risk assessment & triage; CAPA; investigation; dashboards & exports; audit trail; admin config.  \n**Out of scope (Phase 1):** Full HR/directory; sensor/IoT; AI auto-classification.")

    with st.expander("3. Users, roles and permissions"):
        for r in ROLES:
            st.markdown(f"**{r}** — {ROLE_PERMISSIONS.get(r, '')}")

    with st.expander("4. Functional requirements (Modules A–E)"):
        st.markdown("**A Hazard reporting** – Under 2 min, attachments, named/confidential/anonymous.  \n**B Risk & triage** – 5×5 matrix, escalation rules.  \n**C CAPA** – Multiple actions, owner, due date, evidence, verification, overdue escalation.  \n**D Investigation** – Contributing factors, REDA-style, lessons learned.  \n**E Dashboards & exports** – Open by station/area/department/risk; overdue; KPIs; trends; heat map; CSV/PDF export.")

    with st.expander("5. Hazard taxonomy (full)"):
        for cat, sublist in SUBCATEGORIES.items():
            st.markdown(f"**{cat}**")
            for s in sublist:
                st.markdown(f"- {s}")

    with st.expander("6. Workflow and statuses"):
        st.markdown("Draft → Submitted → Triage → Assigned actions → In progress → Awaiting verification → Closed | Rejected (with reason).  \nTriage rules: Extreme → stop/contain; FOD → safe removal, photo; fueling → spill/fire checklist.")

    with st.expander("7. Non-functional requirements"):
        st.markdown("Mobile-first; low bandwidth; security (RBAC, MFA); privacy (confidential/anonymous); auditability; reliability; performance; retention.")

    with st.expander("8. Delivery phases"):
        st.markdown("Phase 1 MVP: Capture, risk, CAPA, dashboards, exports, audit.  \nPhase 2: Investigations, lessons learned, QR, offline.  \nPhase 3: HR integration, messaging, analytics.")

    with st.expander("9. Reference reading"):
        for label, url in REFERENCE_LINKS:
            st.markdown(f"- [{label}]({url})")

    with st.expander("Audit trail (prototype)"):
        for e in reversed(st.session_state.audit_log[-50:]):
            st.caption(f"{_format_dt(e.get('timestamp'))} | {e.get('role')} | {e.get('action')} | {e.get('entity_id')} | {e.get('detail')}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    _inject_css()

    # Sync role from widget value (if already selected)
    if "role_sel" in st.session_state:
        st.session_state.current_role = st.session_state.role_sel

    hazards = st.session_state.hazards
    open_statuses = ["Submitted", "Triage", "Assigned actions", "In progress", "Awaiting verification"]
    open_count = sum(1 for h in hazards if h.get("status") in open_statuses)

    # ----- Top header: dark purple band with logo + role/region/plus -----
    st.markdown(
        '<div class="hirs-top-header">'
        '<div class="hirs-top-header-left">'
        '<span class="hirs-top-header-logo">☰</span>'
        '<span class="hirs-top-header-logo">⚠️ HIRS</span>'
        '<span class="hirs-top-header-tagline">Hazard Identification & Reporting System</span>'
        '</div>'
        '<div class="hirs-top-header-right">'
        f'<span class="hirs-top-header-tagline">{st.session_state.current_role} ▾</span>'
        '<span class="hirs-top-header-divider"></span>'
        '<span class="hirs-top-header-tagline">Station / Region ▾</span>'
        '<span class="hirs-top-header-divider"></span>'
        '<span class="hirs-top-header-tagline" style="font-size:1.1rem; cursor:pointer;" title="New report">➕</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ----- Sidebar navigation (Mesosphere-style: icons + labels) -----
    with st.sidebar:
        st.markdown("**Navigation**")
        try:
            nav_idx = PAGES.index(st.session_state.current_page)
        except ValueError:
            nav_idx = 0
        page_display = st.radio(
            "Select page",
            PAGES_DISPLAY,
            index=nav_idx,
            key="sidebar_nav",
            label_visibility="collapsed",
        )
        st.session_state.current_page = PAGES[PAGES_DISPLAY.index(page_display)]

    # Page title row: large purple title + primary action
    col_title, col_action = st.columns([3, 1])
    with col_title:
        st.markdown(
            f'<h1 class="hirs-page-title">{st.session_state.current_page}</h1>',
            unsafe_allow_html=True,
        )
    with col_action:
        if st.session_state.current_page == "Report":
            st.button(
                "➕ New report",
                type="primary",
                key="header_primary",
                disabled=True,
                help="You are on the report form",
            )
        elif st.session_state.current_page == "Hazards":
            if st.button("➕ New hazard", type="primary", key="header_primary"):
                st.session_state.current_page = "Report"
                st.rerun()
        elif st.session_state.current_page == "CAPA":
            st.button(
                "➕ Add action",
                type="primary",
                key="header_primary",
                help="Add CAPA from a hazard’s detail",
            )
        elif st.session_state.current_page == "Admin":
            st.button(
                "➕ Add",
                type="primary",
                key="header_primary",
                help="Manage stations, departments, roles",
            )
        else:
            st.button("➕ New", type="primary", key="header_primary", disabled=True)

    # Top controls row: role selector, sample data, headline metrics
    ctrl_role, ctrl_sample, ctrl_total, ctrl_open = st.columns([2, 1, 1, 1])
    with ctrl_role:
        st.session_state.current_role = st.selectbox(
            "View as role",
            ROLES,
            key="role_sel",
        )
    with ctrl_sample:
        if st.button(
            "📥 Load sample data",
            help="Add 2 sample reports for demo (won't duplicate if already loaded)",
            key="btn_sample",
        ):
            _load_sample_data()
            st.success("Sample data loaded.")
            st.rerun()
    with ctrl_total:
        st.metric("Total reports", len(hazards))
    with ctrl_open:
        st.metric("Open", open_count)

    st.markdown("---")

    if st.session_state.current_page == "Report":
        render_report()
    elif st.session_state.current_page == "Hazards":
        render_hazards()
    elif st.session_state.current_page == "Risk & Triage":
        render_risk_triage()
    elif st.session_state.current_page == "CAPA":
        render_capa()
    elif st.session_state.current_page == "Investigation":
        render_investigation()
    elif st.session_state.current_page == "Dashboard":
        render_dashboard()
    elif st.session_state.current_page == "Exports":
        render_exports()
    elif st.session_state.current_page == "Admin":
        render_admin()
    else:
        render_reference()

    st.markdown("---")
    st.markdown(
        '<p class="hirs-footer">HIRS Prototype v1.0 · Hazard Identification & Reporting System · '
        'Prepared for YESAYA YESAYA · 25 Feb 2026 · Front-end only · No backend · Data in session only</p>',
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
