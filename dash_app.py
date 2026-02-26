import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from dash import callback_context
import json
import plotly.graph_objects as go

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


external_stylesheets = [
    {
        "href": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
        "rel": "stylesheet",
    }
]

# ---------------------------------------------------------------------------
# App + in-memory data (simple prototype store)
# ---------------------------------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "HIRS – Hazard Reporting"
server = app.server  # Flask app for production WSGI (gunicorn, etc.)

# Simple in-memory store – good enough for a single-user prototype
HAZARDS = []  # list[dict]

# Dummy reports for the Report page – professional prototype with realistic data
SAMPLE_REPORTS = [
    {"id": "HZ-0001", "title": "FOD near stand 7", "category": "Airside / Ramp", "area": "Stand 7", "station": "Main Ramp", "status": "Submitted"},
    {"id": "HZ-0002", "title": "Vehicle-pedestrian conflict at gate B12", "category": "Airside / Ramp", "area": "Gate B12", "station": "Terminal B", "status": "Triage"},
    {"id": "HZ-0003", "title": "Spill at refuelling point", "category": "Aircraft servicing", "area": "Stand 14", "station": "North Ramp", "status": "Closed"},
    {"id": "HZ-0004", "title": "Damaged GPU cable left on stand", "category": "Ground Support Equipment (GSE)", "area": "Stand 22", "station": "Main Ramp", "status": "Assigned actions"},
    {"id": "HZ-0005", "title": "Insufficient lighting at cargo bay entrance", "category": "Cargo, baggage & loading", "area": "Cargo Bay A", "station": "Freight Terminal", "status": "In progress"},
]

# Hardcoded sample data so the Hazards page looks exactly like the reference (always visible)
SAMPLE_HAZARDS = [
    {"id": "HZ-0001", "title": "FOD near stand 7", "category": "Airside / Ramp", "area": "Stand 7", "station": "Main Ramp", "perceived_risk": "High", "status": "Submitted"},
    {"id": "HZ-0002", "title": "Vehicle-pedestrian conflict at gate B12", "category": "Airside / Ramp", "area": "Gate B12", "station": "Terminal B", "perceived_risk": "Moderate", "status": "Triage"},
    {"id": "HZ-0003", "title": "Spill at refuelling point", "category": "Aircraft servicing", "area": "Stand 14", "station": "North Ramp", "perceived_risk": "Critical", "status": "Closed"},
]

# Hardcoded sample CAPA actions (same structure as Hazards page)
SAMPLE_CAPA = [
    {"id": "CA-0001", "action": "Inspect stand 7 for FOD; reinforce briefing", "type": "Corrective", "priority": "High", "hazard_id": "HZ-0001", "due_date": "2026-03-05", "status": "In progress"},
    {"id": "CA-0002", "action": "Install additional signage at gate B12", "type": "Preventive", "priority": "Medium", "hazard_id": "HZ-0002", "due_date": "2026-03-12", "status": "Open"},
    {"id": "CA-0003", "action": "Spill kit replenishment and training", "type": "Immediate", "priority": "Critical", "hazard_id": "HZ-0003", "due_date": "2026-02-28", "status": "Closed"},
]

# Hardcoded sample investigations (serious events / REDA-style)
SAMPLE_INVESTIGATIONS = [
    {"id": "INV-0001", "title": "FOD incident stand 7 – root cause", "hazard_id": "HZ-0001", "status": "In progress", "lead": "J. Smith", "started": "2026-02-20"},
    {"id": "INV-0002", "title": "Gate B12 vehicle-pedestrian near miss", "hazard_id": "HZ-0002", "status": "Open", "lead": "—", "started": "2026-02-24"},
    {"id": "INV-0003", "title": "Refuelling spill stand 14", "hazard_id": "HZ-0003", "status": "Closed", "lead": "A. Jones", "started": "2026-02-18"},
]


SIDEBAR_ITEMS = [
    ("dashboard", "📊", "Dashboard"),
    ("report", "📋", "Report"),
    ("hazards", "📂", "Hazards"),
    ("risk", "⚖️", "Risk & Triage"),
    ("capa", "📌", "CAPA"),
    ("investigation", "🔍", "Investigation"),
    ("exports", "📤", "Exports"),
    ("admin", "⚙️", "Admin"),
    ("requirements", "📄", "Requirements"),
    ("reference", "📎", "Reference"),
]


def sidebar():
    return html.Div(
        [
            html.Nav(
                [
                    dcc.Link(
                        html.Div(
                            [
                                html.Span(icon, className="nav-icon"),
                                html.Span(label, className="nav-label"),
                            ],
                            className="sidebar-item-inner",
                        ),
                        href=f"/{name}",
                        className="sidebar-item",
                        id=f"nav-{name}",
                    )
                    for name, icon, label in SIDEBAR_ITEMS
                ],
                className="sidebar-nav",
            ),
        ],
        className="sidebar",
    )


def top_header():
    return html.Div(
        [
            html.Div(
                [
                    html.Img(
                        src=app.get_asset_url("images/nhs.png"),
                        alt="NHS",
                        className="top-header-logo-img",
                    ),
                    html.Div(
                        "Hazard Identification & Reporting System",
                        className="top-tagline",
                    ),
                ],
                className="top-left",
            ),
            html.Div(
                id="top-right-content",
                children=[
                    html.Span("Jane Smith", className="top-user"),
                    html.Span("AMER–EMEA ▾", className="top-region"),
                    html.Div("+", className="top-plus", id="top-add-btn"),
                    dcc.Link("Log out", href="/logout", className="top-logout-link"),
                ],
                className="top-right",
            ),
        ],
        className="top-header",
    )


# ---------------------------------------------------------------------------
# Login page – professional sign-in form
# ---------------------------------------------------------------------------
def login_page():
    """Centered login form: email, password, remember me, sign in."""
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Img(
                                src=app.get_asset_url("images/nhs.png"),
                                alt="HIRS",
                                className="login-logo",
                            ),
                            html.H1("Sign in to HIRS", className="login-title"),
                            html.P("Hazard Identification & Reporting System. Enter your credentials to continue.", className="login-subtitle"),
                        ],
                        className="login-header",
                    ),
                    html.Form(
                        [
                            html.Div(
                                [
                                    html.Label("Email or username", htmlFor="login-email", className="login-label"),
                                    dcc.Input(
                                        id="login-email",
                                        type="text",
                                        placeholder="you@example.com",
                                        autoComplete="username",
                                        className="login-input",
                                    ),
                                ],
                                className="login-field",
                            ),
                            html.Div(
                                [
                                    html.Label("Password", htmlFor="login-password", className="login-label"),
                                    dcc.Input(
                                        id="login-password",
                                        type="password",
                                        placeholder="••••••••",
                                        autoComplete="current-password",
                                        className="login-input",
                                    ),
                                ],
                                className="login-field",
                            ),
                            html.Div(
                                [
                                    dcc.Checklist(
                                        id="login-remember",
                                        options=[{"label": " Remember me", "value": "remember"}],
                                        value=[],
                                        className="login-remember",
                                    ),
                                    dcc.Link("Forgot password?", href="#", className="login-forgot"),
                                ],
                                className="login-options",
                            ),
                            html.Div(
                                html.Button("Sign in", type="button", id="login-submit", className="login-submit"),
                                className="login-submit-wrap",
                            ),
                            html.Div(id="login-message", className="login-message"),
                        ],
                        className="login-form",
                    ),
                    html.P("Demo: any email and password will sign you in as Jane Smith.", className="login-demo-hint"),
                ],
                className="login-card",
            ),
        ],
        className="login-page",
    )


def logout_placeholder():
    """Shown briefly when user navigates to /logout before redirect to login."""
    return html.Div(
        [
            html.Div("Logging out…", className="login-logging-out-text"),
            html.Div("Redirecting to sign in…", className="login-logging-out-sub"),
        ],
        className="login-logging-out",
    )


def page_shell(page_title: str, body_placeholder: str = None):
    """Generic page shell – still used for simple pages (e.g. Admin stub)."""
    if body_placeholder is None:
        body_placeholder = f"Content for {page_title} will be implemented here."
    return html.Div(
        [
            html.Div(
                [
                    html.H2(page_title, className="page-title"),
                    html.Button("+ New", className="primary-btn"),
                ],
                className="page-header",
            ),
            html.Div(body_placeholder, className="page-body-placeholder"),
        ]
    )


# ---------------------------------------------------------------------------
# Report page – real hazard entry form (Module A)
# ---------------------------------------------------------------------------
def _next_hazard_id() -> str:
    """Generate a simple incremental hazard ID (after SAMPLE_REPORTS)."""
    return f"HZ-{len(SAMPLE_REPORTS) + len(HAZARDS) + 1:04d}"


def report_page():
    """Report dashboard with KPIs, charts, generated reports list, and form (shown on New report)."""
    # Dummy data for Report dashboard (from SAMPLE_REPORTS + HAZARDS)
    all_r = list(SAMPLE_REPORTS) + list(HAZARDS)
    n_total = len(all_r)
    status_counts = {}
    for r in all_r:
        s = r.get("status") or "Unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
    n_open = status_counts.get("Submitted", 0) + status_counts.get("Triage", 0) + status_counts.get("Assigned actions", 0) + status_counts.get("In progress", 0)
    n_closed = status_counts.get("Closed", 0)
    n_pending = status_counts.get("Submitted", 0) + status_counts.get("Triage", 0)
    category_counts = {}
    for r in all_r:
        c = r.get("category") or "Other"
        category_counts[c] = category_counts.get(c, 0) + 1
    # Chart: Reports by status
    status_labels = list(status_counts.keys()) or ["No data"]
    status_values = list(status_counts.values()) or [0]
    colors_status = ["#5e4a7a", "#10b981", "#3b82f6", "#f59e0b", "#94a3b8", "#ef4444"]
    report_status_fig = go.Figure(
        data=[
            go.Pie(
                labels=status_labels,
                values=status_values,
                hole=0.55,
                marker_colors=colors_status[: len(status_labels)],
                textinfo="label+percent",
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="Reports by status",
            margin=dict(l=10, r=10, t=36, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            showlegend=False,
        ),
    )
    # Chart: Reports by category
    cat_labels = list(category_counts.keys()) or ["No data"]
    cat_values = list(category_counts.values()) or [0]
    report_cat_fig = go.Figure(
        data=[
            go.Bar(
                x=cat_labels,
                y=cat_values,
                marker_color="#5e4a7a",
                text=cat_values,
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="Reports by category",
            margin=dict(l=20, r=20, t=36, b=80),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            xaxis=dict(tickangle=-35),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        ),
    )
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Report", className="page-title"),
                    html.P("Overview of hazard reports, then browse the list or add a new one.", className="page-lead"),
                ],
                className="page-header report-page-header",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("Total reports", className="report-kpi-title"),
                                            html.Div("📋", className="report-kpi-icon"),
                                            html.Div(str(n_total), className="report-kpi-value"),
                                            html.Div("All time", className="report-kpi-sub"),
                                        ],
                                        className="report-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Open / in progress", className="report-kpi-title"),
                                            html.Div("🔓", className="report-kpi-icon"),
                                            html.Div(str(n_open), className="report-kpi-value"),
                                            html.Div("Active", className="report-kpi-sub"),
                                        ],
                                        className="report-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Closed", className="report-kpi-title"),
                                            html.Div("✅", className="report-kpi-icon"),
                                            html.Div(str(n_closed), className="report-kpi-value"),
                                            html.Div("Resolved", className="report-kpi-sub"),
                                        ],
                                        className="report-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Pending triage", className="report-kpi-title"),
                                            html.Div("⏳", className="report-kpi-icon"),
                                            html.Div(str(n_pending), className="report-kpi-value"),
                                            html.Div("Awaiting review", className="report-kpi-sub"),
                                        ],
                                        className="report-kpi-card",
                                    ),
                                ],
                                className="report-kpi-row",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [dcc.Graph(figure=report_status_fig, config={"displayModeBar": False})],
                                        className="report-chart-card",
                                    ),
                                    html.Div(
                                        [dcc.Graph(figure=report_cat_fig, config={"displayModeBar": False})],
                                        className="report-chart-card",
                                    ),
                                ],
                                className="report-charts-row",
                            ),
                        ],
                        className="report-dashboard-section",
                    ),
                    html.Div(
                        [
                            html.H3("Generated reports", className="report-section-title"),
                            html.Div(id="report-list-container", className="report-list-container"),
                        ],
                        className="report-section report-list-section",
                    ),
                    dcc.Store(id="report-scroll-sentinel", data=0),
                    dcc.Store(id="report-form-visible", data=False),
                    html.Div(
                        [
                            html.H3("Submit a new report", className="report-section-title"),
                            html.P("Click 'New report' to add a new hazard, near miss, or safety concern.", className="report-form-intro"),
                            html.Div(
                                html.Button("New report", id="report-new-btn", className="primary-btn", title="Open form to create a new report"),
                                className="report-header-actions",
                            ),
                        ],
                        className="report-section report-form-actions-section",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Button("Submit report", id="report-submit", className="primary-btn report-submit-btn"),
                                    html.Button("Cancel", id="report-cancel-btn", className="report-cancel-btn"),
                                ],
                                className="report-header-actions report-form-buttons",
                            ),
                            html.Div(
                        [
                            html.Div(
                                [
                                    html.H3("When & where", className="report-section-title"),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Label("Date observed"),
                                                    dcc.DatePickerSingle(id="report-date"),
                                                ],
                                                className="form-field",
                                            ),
                                            html.Div(
                                                [
                                                    html.Label("Station / airport"),
                                                    dcc.Input(
                                                        id="report-station",
                                                        type="text",
                                                        placeholder="e.g. Main Ramp, Station A",
                                                        className="form-input",
                                                    ),
                                                ],
                                                className="form-field",
                                            ),
                                            html.Div(
                                                [
                                                    html.Label("Area (stand/gate/cargo shed/GSE park)"),
                                                    dcc.Input(
                                                        id="report-area",
                                                        type="text",
                                                        placeholder="e.g. Stand 14, Gate B12",
                                                        className="form-input",
                                                    ),
                                                ],
                                                className="form-field",
                                            ),
                                        ],
                                        className="form-grid form-grid-2",
                                    ),
                                ],
                                className="report-section",
                            ),
                            html.Div(
                                [
                                    html.H3("Hazard details", className="report-section-title"),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Label("Short title"),
                                                    dcc.Input(
                                                        id="report-title",
                                                        type="text",
                                                        placeholder="Brief descriptive title (e.g. FOD near stand 7)",
                                                        className="form-input",
                                                    ),
                                                ],
                                                className="form-field form-field-full",
                                            ),
                                            html.Div(
                                                [
                                                    html.Label("Category"),
                                                    dcc.Dropdown(
                                                        id="report-category",
                                                        options=[{"label": c, "value": c} for c in HAZARD_AREAS],
                                                        placeholder="Select category",
                                                        className="form-input",
                                                    ),
                                                ],
                                                className="form-field",
                                            ),
                                            html.Div(
                                                [
                                                    html.Label("Subcategory"),
                                                    dcc.Dropdown(id="report-subcategory", placeholder="Select subcategory"),
                                                ],
                                                className="form-field",
                                            ),
                                        ],
                                        className="form-grid form-grid-2",
                                    ),
                            html.Label("What happened or what could have happened?"),
                            dcc.Textarea(
                                id="report-description",
                                className="form-textarea",
                                placeholder="Describe the hazard, near miss, or unsafe condition.",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Label("People exposed"),
                                            dcc.Input(
                                                id="report-people",
                                                type="text",
                                                className="form-input",
                                                placeholder="e.g. 2 ramp agents, 1 engineer",
                                            ),
                                        ],
                                        className="form-field",
                                    ),
                                    html.Div(
                                        [
                                            html.Label("Perceived risk level"),
                                            dcc.Dropdown(
                                                id="report-severity-reporter",
                                                options=[
                                                    {"label": l, "value": l}
                                                    for l in ["Low", "Moderate", "High", "Critical"]
                                                ],
                                                placeholder="Select",
                                            ),
                                        ],
                                        className="form-field",
                                    ),
                                ],
                                className="form-grid form-grid-2",
                            ),
                        ],
                        className="report-section",
                    ),
                    html.Div(
                        [
                            html.H3("Classification", className="report-section-title"),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Label("Type"),
                                            dcc.Dropdown(
                                                id="report-classification",
                                                options=[{"label": t, "value": t} for t in CLASSIFICATION_TYPES],
                                                placeholder="Hazard / Near miss / Incident / ...",
                                            ),
                                        ],
                                        className="form-field",
                                    ),
                                    html.Div(
                                        [
                                            html.Label("Tags"),
                                            dcc.Dropdown(
                                                id="report-tags",
                                                options=[{"label": t, "value": t} for t in TAGS_OPTIONS],
                                                placeholder="Safety, Security, Environment, Quality",
                                                multi=True,
                                            ),
                                        ],
                                        className="form-field",
                                    ),
                                ],
                                className="form-grid form-grid-2",
                            ),
                        ],
                        className="report-section",
                    ),
                    html.Div(
                        [
                            html.H3("Reporter", className="report-section-title"),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Label("Reporting mode"),
                                            dcc.RadioItems(
                                                id="report-mode",
                                                options=[
                                                    {"label": "Named", "value": "Named"},
                                                    {"label": "Confidential", "value": "Confidential"},
                                                    {"label": "Anonymous", "value": "Anonymous"},
                                                ],
                                                value="Named",
                                                className="form-radio report-radio",
                                            ),
                                        ],
                                        className="form-field",
                                    ),
                                ],
                                className="form-grid",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Label("Name"),
                                            dcc.Input(id="reporter-name", type="text", placeholder="Your name", className="form-input"),
                                        ],
                                        className="form-field",
                                    ),
                                    html.Div(
                                        [
                                            html.Label("Department / team"),
                                            dcc.Input(id="reporter-dept", type="text", placeholder="e.g. Ramp, Cargo", className="form-input"),
                                        ],
                                        className="form-field",
                                    ),
                                    html.Div(
                                        [
                                            html.Label("Role"),
                                            dcc.Input(id="reporter-role", type="text", placeholder="e.g. Ground handler", className="form-input"),
                                        ],
                                        className="form-field",
                                    ),
                                ],
                                className="form-grid form-grid-3",
                            ),
                        ],
                        className="report-section",
                    ),
                    html.Div(id="report-status", className="form-status report-status"),
                ],
                id="report-form-card",
                className="page-body-card report-form-card",
            ),
        ],
        id="report-form-block",
    ),
        ],
        className="report-page-body",
    ),
        ],
        className="report-page",
    )


# ---------- HIRS Requirements Document (full professional layout) ----------
def requirements_document():
    return html.Div(
        [
            # Cover & metadata
            html.Div(
                [
                    html.H1(
                        "Hazard Identification & Reporting System (HIRS)",
                        className="doc-title",
                    ),
                    html.P(
                        "Professional Requirements & Content Specification for Airport Ground Handling and Ramp Operations",
                        className="doc-subtitle",
                    ),
                    html.Div(
                        [
                            html.Div([html.Strong("Document status"), html.Span("Draft for design & development")], className="doc-meta-row"),
                            html.Div([html.Strong("Prepared by"), html.Span("YESAYA YESAYA")], className="doc-meta-row"),
                            html.Div([html.Strong("Organization"), html.Span("Yesaya Yesaya")], className="doc-meta-row"),
                            html.Div([html.Strong("Date"), html.Span("25 Feb 2026")], className="doc-meta-row"),
                            html.Div([html.Strong("Version"), html.Span("1.0")], className="doc-meta-row"),
                        ],
                        className="doc-meta",
                    ),
                    html.P(
                        "This document defines the modules, workflows, data fields, dashboards, and non-functional requirements for a mobile-first hazard reporting system supporting airside ramp and ground handling safety management.",
                        className="doc-lead",
                    ),
                ],
                className="doc-cover",
            ),
            # TOC
            html.Nav(
                [
                    html.H3("Contents", className="doc-toc-title"),
                    html.A("1. Executive summary", href="#sec1", className="doc-toc-link"),
                    html.A("2. Scope", href="#sec2", className="doc-toc-link"),
                    html.A("3. Users, roles, and permissions", href="#sec3", className="doc-toc-link"),
                    html.A("4. Functional requirements", href="#sec4", className="doc-toc-link"),
                    html.A("5. Hazard taxonomy", href="#sec5", className="doc-toc-link"),
                    html.A("6. Workflow and statuses", href="#sec6", className="doc-toc-link"),
                    html.A("7. Non-functional requirements", href="#sec7", className="doc-toc-link"),
                    html.A("8. Recommended delivery phases", href="#sec8", className="doc-toc-link"),
                    html.A("9. Reference reading", href="#sec9", className="doc-toc-link"),
                ],
                className="doc-toc",
            ),
            # Section 1
            html.Section(
                [
                    html.H2("1. Executive summary", id="sec1", className="doc-section-title"),
                    html.P(
                        "HIRS provides a fast, structured way for frontline staff to report hazards, near misses, and safety concerns; for supervisors and Safety (SMS/QHSE) teams to assess risk consistently; and for management to track actions to closure and learn from trends."
                    ),
                    html.P(
                        "The system is designed for high-tempo ramp environments where risks include FOD, vehicle-pedestrian conflict, aircraft servicing (fueling, pushback/towing, docking), cargo/baggage handling, and ground support equipment (GSE)."
                    ),
                    html.H4("Key outcomes", className="doc-h4"),
                    html.Ul(
                        [
                            html.Li("Higher reporting rate through simple mobile capture, optional anonymous reporting, and feedback to reporters."),
                            html.Li("Consistent prioritization using an embedded likelihood × severity risk matrix with escalation rules."),
                            html.Li("Closed-loop corrective/preventive action (CAPA) tracking with evidence and verification."),
                            html.Li("Dashboards for trends, hotspots, overdue actions, and risk heat maps to drive prevention."),
                        ],
                        className="doc-list",
                    ),
                ],
                className="doc-section",
            ),
            # Section 2
            html.Section(
                [
                    html.H2("2. Scope", id="sec2", className="doc-section-title"),
                    html.H4("2.1 In scope", className="doc-h4"),
                    html.Ul(
                        [
                            html.Li("Hazard, near miss, incident, and unsafe condition reporting (mobile-first)."),
                            html.Li("Risk assessment (likelihood/severity), triage, and escalation."),
                            html.Li("CAPA assignment, reminders, evidence upload, verification, and closure."),
                            html.Li("Investigation workflow for serious events (option to align with REDA-style contributing factor capture)."),
                            html.Li("Dashboards, analytics, exports, and audit trail."),
                            html.Li("Admin configuration: stations, areas, categories, risk matrix, users/roles."),
                        ],
                        className="doc-list",
                    ),
                    html.H4("2.2 Out of scope (Phase 1)", className="doc-h4"),
                    html.Ul(
                        [
                            html.Li("Full integration with HR / directory services (planned for Phase 3)."),
                            html.Li("Automated sensor/IoT ingestion (e.g., vehicle telematics) (future)."),
                            html.Li("Advanced AI auto-classification (future)."),
                        ],
                        className="doc-list",
                    ),
                ],
                className="doc-section",
            ),
            # Section 3 - Roles table
            html.Section(
                [
                    html.H2("3. Users, roles, and permissions", id="sec3", className="doc-section-title"),
                    html.P(
                        "HIRS supports role-based access to protect confidentiality while enabling operational ownership and Safety oversight."
                    ),
                    html.Div(
                        html.Table(
                            [html.Thead(html.Tr([html.Th("Role"), html.Th("Key permissions")]))]
                            + [
                                html.Tr([html.Td(role), html.Td(ROLE_PERMISSIONS.get(role, "—"))])
                                for role in ROLES
                            ],
                            className="doc-table",
                        ),
                        className="doc-table-wrap",
                    ),
                ],
                className="doc-section",
            ),
            # Section 4 - Functional requirements
            html.Section(
                [
                    html.H2("4. Functional requirements", id="sec4", className="doc-section-title"),
                    html.H4("4.1 Module A – Hazard reporting", className="doc-h4"),
                    html.P(
                        "A reporter must be able to submit a hazard report in under 2 minutes using a guided form optimized for mobile devices. The form must support attachments (photos/video) and allow named, confidential, or anonymous submissions depending on policy."
                    ),
                    html.P(html.Strong("Minimum data fields (Hazard Report)"), className="doc-strong-p"),
                    html.Div(
                        html.Table(
                            [
                                html.Thead(html.Tr([html.Th("Section"), html.Th("Fields")])),
                                html.Tr([html.Td("Reporter"), html.Td("Name (optional), employee ID (optional), department/team, role, contact (optional), reporting mode (named/confidential/anonymous).")]),
                                html.Tr([html.Td("When & where"), html.Td("Date/time observed; station/airport; specific area (stand/gate/cargo shed/GSE park etc.); optional GPS pin.")]),
                                html.Tr([html.Td("Hazard details"), html.Td("Category/subcategory; description; people exposed; potential consequence; immediate action taken; attachments; witnesses (optional).")]),
                                html.Tr([html.Td("Classification"), html.Td("Hazard / Near miss / Incident / Unsafe act / Unsafe condition; safety/security/environment/quality tag (optional).")]),
                            ],
                            className="doc-table",
                        ),
                        className="doc-table-wrap",
                    ),
                    html.H4("4.2 Module B – Risk assessment and triage", className="doc-h4"),
                    html.P(
                        "HIRS must embed a configurable risk matrix (recommended 5×5) using Likelihood (1–5) and Severity (1–5). The system auto-calculates risk score and level, and enforces escalation and response rules by risk level."
                    ),
                    html.Div(
                        html.Table(
                            [
                                html.Thead(html.Tr([html.Th("Risk level"), html.Th("Rule (minimum)")])),
                                html.Tr([html.Td("Extreme"), html.Td("Immediate stop/contain checklist; notify Safety and Operations Manager immediately; investigation mandatory.")]),
                                html.Tr([html.Td("High"), html.Td("Same-shift review required; actions assigned with short due dates; Safety notified.")]),
                                html.Tr([html.Td("Medium"), html.Td("Action plan required; due date set; periodic review.")]),
                                html.Tr([html.Td("Low"), html.Td("Record and monitor; housekeeping/awareness actions as needed.")]),
                            ],
                            className="doc-table",
                        ),
                        className="doc-table-wrap",
                    ),
                    html.H4("4.3 Module C – Corrective and preventive actions (CAPA)", className="doc-h4"),
                    html.P(
                        "The system must support multiple actions per report, with ownership, due dates, reminders, evidence, verification, and closure. Overdue actions must automatically escalate."
                    ),
                    html.Ul(
                        [
                            html.Li("Action fields: title/description; type (Immediate/Corrective/Preventive); owner; department; priority; due date; required evidence; completion date; verification result; effectiveness notes."),
                            html.Li("Escalation: notify owner at T-3 and T-1 days; escalate overdue to supervisor and operations management; Safety receives summary of overdue High/Extreme actions."),
                        ],
                        className="doc-list",
                    ),
                    html.H4("4.4 Module D – Investigation (serious events)", className="doc-h4"),
                    html.P(
                        "For incidents and serious near misses, HIRS must enable a structured investigation with contributing factor capture, corrective recommendations, and lessons learned publication. An optional template may follow a REDA-style approach (ramp event decision aid) to focus on system factors."
                    ),
                    html.H4("4.5 Module E – Dashboards and exports", className="doc-h4"),
                    html.Ul(
                        [
                            html.Li("Open hazards by station/area/department and risk level."),
                            html.Li("Overdue actions by owner/department; time-to-triage and time-to-close KPIs."),
                            html.Li("Trend lines (weekly/monthly), recurring hazard hotspots, and risk heat map."),
                            html.Li("Export to PDF and CSV/Excel for audits; printable investigation summary."),
                        ],
                        className="doc-list",
                    ),
                ],
                className="doc-section",
            ),
            # Section 5 - Taxonomy (from config)
            html.Section(
                [
                    html.H2("5. Hazard taxonomy (dropdown configuration)", id="sec5", className="doc-section-title"),
                    html.P(
                        "The following taxonomy is recommended for airport ramp and ground handling contexts. It should be configurable by Admin (not hardcoded) so categories can match local operations and regulatory requirements."
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H4(cat, className="doc-taxonomy-cat"),
                                    html.Ul([html.Li(sub) for sub in subs], className="doc-list doc-list-compact"),
                                ],
                                className="doc-taxonomy-block",
                            )
                            for cat, subs in SUBCATEGORIES.items()
                        ],
                        className="doc-taxonomy",
                    ),
                ],
                className="doc-section",
            ),
            # Section 6
            html.Section(
                [
                    html.H2("6. Workflow and statuses", id="sec6", className="doc-section-title"),
                    html.H4("6.1 Standard status flow", className="doc-h4"),
                    html.P(
                        "Draft → Submitted → Triage (Safety/Supervisor) → Assigned actions → In progress → Awaiting verification → Closed | Rejected (with reason).",
                        className="doc-flow",
                    ),
                    html.H4("6.2 Triage decision rules (examples)", className="doc-h4"),
                    html.Ul(
                        [
                            html.Li("If risk level = Extreme: show stop/contain checklist and trigger immediate notifications."),
                            html.Li("If category = FOD: prompt safe removal, record cleanup, require photo evidence when possible."),
                            html.Li("If fueling-related: prompt spill/fire risk checklist and notify responsible supervisor immediately."),
                        ],
                        className="doc-list",
                    ),
                ],
                className="doc-section",
            ),
            # Section 7
            html.Section(
                [
                    html.H2("7. Non-functional requirements", id="sec7", className="doc-section-title"),
                    html.Ul(
                        [
                            html.Li([html.Strong("Mobile-first: "), " responsive UI optimized for Android devices used on the ramp."]),
                            html.Li([html.Strong("Low bandwidth: "), " fast load; compress images; allow deferred upload if needed."]),
                            html.Li([html.Strong("Security: "), " role-based access control; optional MFA; encrypted data at rest and in transit."]),
                            html.Li([html.Strong("Privacy: "), " support confidential and anonymous reporting per policy; limit access to reporter identity."]),
                            html.Li([html.Strong("Auditability: "), " immutable audit log of edits, status changes, assignments, and closures."]),
                            html.Li([html.Strong("Reliability: "), " backups and restore testing; uptime target defined by business."]),
                            html.Li([html.Strong("Performance: "), " search/filter returns results quickly; report submission under 10 seconds on normal connectivity."]),
                            html.Li([html.Strong("Retention: "), " configurable retention (e.g., 5–7 years) aligned with organizational policy."]),
                        ],
                        className="doc-list",
                    ),
                ],
                className="doc-section",
            ),
            # Section 8
            html.Section(
                [
                    html.H2("8. Recommended delivery phases", id="sec8", className="doc-section-title"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H4("Phase 1 – MVP", className="doc-h4"),
                                    html.Ul(
                                        [
                                            html.Li("Hazard capture + attachments"),
                                            html.Li("Risk matrix + triage + notifications"),
                                            html.Li("CAPA tracking + reminders + verification"),
                                            html.Li("Dashboards + exports + audit trail"),
                                        ],
                                        className="doc-list",
                                    ),
                                ],
                                className="doc-phase",
                            ),
                            html.Div(
                                [
                                    html.H4("Phase 2 – Safety maturity", className="doc-h4"),
                                    html.Ul(
                                        [
                                            html.Li("Investigation templates (REDA-style contributing factors)"),
                                            html.Li("Lessons learned bulletin generation"),
                                            html.Li("QR codes for location-based reporting"),
                                            html.Li("Offline capture and sync (if required)"),
                                        ],
                                        className="doc-list",
                                    ),
                                ],
                                className="doc-phase",
                            ),
                            html.Div(
                                [
                                    html.H4("Phase 3 – Integrations & optimization", className="doc-h4"),
                                    html.Ul(
                                        [
                                            html.Li("Integration with HR / directory / training records"),
                                            html.Li("Messaging gateway (SMS/WhatsApp) where appropriate"),
                                            html.Li("Advanced analytics and automation"),
                                        ],
                                        className="doc-list",
                                    ),
                                ],
                                className="doc-phase",
                            ),
                        ],
                        className="doc-phases",
                    ),
                ],
                className="doc-section",
            ),
            # Section 9 - Reference links
            html.Section(
                [
                    html.H2("9. Reference reading (non-exhaustive)", id="sec9", className="doc-section-title"),
                    html.P(
                        "The system structure and taxonomy are informed by common ramp safety and ground handling operational themes from the sources below."
                    ),
                    html.Ul(
                        [
                            html.Li(html.A(label, href=url, target="_blank", rel="noopener noreferrer", className="doc-link"))
                            for label, url in REFERENCE_LINKS
                        ],
                        className="doc-list doc-ref-list",
                    ),
                ],
                className="doc-section",
            ),
            html.Footer(
                [
                    html.Hr(),
                    html.P(
                        "HIRS Requirements · Prepared for YESAYA YESAYA · 25 Feb 2026 · Version 1.0",
                        className="doc-footer",
                    ),
                ],
                className="doc-footer-wrap",
            ),
        ],
        className="doc-body",
    )


def reference_page():
    """Reference: quick links and document summary."""
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Reference", className="page-title"),
                ],
                className="page-header",
            ),
            html.Div(
                [
                    html.P("Quick access to the full Requirements document and external references.", className="doc-lead"),
                    html.A("View full Requirements document →", href="/requirements", className="primary-btn doc-inline-btn"),
                    html.H4("External references", className="doc-h4"),
                    html.Ul(
                        [
                            html.Li(html.A(label, href=url, target="_blank", rel="noopener noreferrer", className="doc-link"))
                            for label, url in REFERENCE_LINKS
                        ],
                        className="doc-list doc-ref-list",
                    ),
                ],
                className="page-body-card",
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Hazards page – dashboard with KPIs, charts, then table
# ---------------------------------------------------------------------------
def hazards_page():
    """Hazards dashboard with KPIs, charts, filters, and table."""
    all_h = list(SAMPLE_HAZARDS) + list(HAZARDS)
    n_total = len(all_h)
    status_counts = {}
    category_counts = {}
    risk_counts = {"High": 0, "Critical": 0, "Moderate": 0, "Low": 0}
    for h in all_h:
        s = h.get("status") or "Unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
        c = h.get("category") or "Other"
        category_counts[c] = category_counts.get(c, 0) + 1
        r = h.get("perceived_risk") or ""
        if r in risk_counts:
            risk_counts[r] += 1
    n_open = sum(status_counts.get(x, 0) for x in ("Submitted", "Triage", "Assigned actions", "In progress"))
    n_closed = status_counts.get("Closed", 0)
    n_high_critical = risk_counts.get("High", 0) + risk_counts.get("Critical", 0)
    status_options = [{"label": s, "value": s} for s in WORKFLOW_STATUSES]
    category_options = [{"label": c, "value": c} for c in HAZARD_AREAS]
    # Chart: Hazards by status
    status_labels = list(status_counts.keys()) or ["No data"]
    status_vals = list(status_counts.values()) or [0]
    colors = ["#5e4a7a", "#10b981", "#3b82f6", "#f59e0b", "#94a3b8", "#ef4444"]
    hazards_status_fig = go.Figure(
        data=[
            go.Pie(
                labels=status_labels,
                values=status_vals,
                hole=0.55,
                marker_colors=colors[: len(status_labels)],
                textinfo="label+percent",
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="Hazards by status",
            margin=dict(l=10, r=10, t=36, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            showlegend=False,
        ),
    )
    # Chart: Hazards by category
    cat_labels = list(category_counts.keys()) or ["No data"]
    cat_vals = list(category_counts.values()) or [0]
    hazards_cat_fig = go.Figure(
        data=[
            go.Bar(
                x=cat_labels,
                y=cat_vals,
                marker_color="#5e4a7a",
                text=cat_vals,
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="Hazards by category",
            margin=dict(l=20, r=20, t=36, b=80),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            xaxis=dict(tickangle=-35),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        ),
    )
    # Chart: By risk level
    risk_labels = [k for k in risk_counts if risk_counts[k] > 0] or ["Low"]
    risk_vals = [risk_counts.get(k, 0) for k in risk_labels] or [0]
    risk_colors = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444"]
    hazards_risk_fig = go.Figure(
        data=[
            go.Bar(
                x=risk_labels,
                y=risk_vals,
                marker_color=risk_colors[: len(risk_labels)],
                text=risk_vals,
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="By risk level",
            margin=dict(l=20, r=20, t=36, b=50),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=200,
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        ),
    )
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H2("Hazards", className="page-title"),
                            html.P("Overview of all hazards, then filter and manage the list below.", className="page-lead"),
                        ],
                        className="hazards-header-left",
                    ),
                    dcc.Link(
                        html.Button(
                            [html.Span("↑", className="hazards-add-icon"), "Add report"],
                            className="primary-btn hazards-add-btn",
                        ),
                        href="/report",
                        className="hazards-header-action",
                    ),
                ],
                className="page-header hazards-page-header",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("Total hazards", className="hazards-kpi-title"),
                                            html.Div("📂", className="hazards-kpi-icon"),
                                            html.Div(str(n_total), className="hazards-kpi-value"),
                                            html.Div("All records", className="hazards-kpi-sub"),
                                        ],
                                        className="hazards-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Open / active", className="hazards-kpi-title"),
                                            html.Div("🔓", className="hazards-kpi-icon"),
                                            html.Div(str(n_open), className="hazards-kpi-value"),
                                            html.Div("In progress", className="hazards-kpi-sub"),
                                        ],
                                        className="hazards-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Closed", className="hazards-kpi-title"),
                                            html.Div("✅", className="hazards-kpi-icon"),
                                            html.Div(str(n_closed), className="hazards-kpi-value"),
                                            html.Div("Resolved", className="hazards-kpi-sub"),
                                        ],
                                        className="hazards-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("High / Critical", className="hazards-kpi-title"),
                                            html.Div("⚠️", className="hazards-kpi-icon"),
                                            html.Div(str(n_high_critical), className="hazards-kpi-value"),
                                            html.Div("Needs attention", className="hazards-kpi-sub"),
                                        ],
                                        className="hazards-kpi-card",
                                    ),
                                ],
                                className="hazards-kpi-row",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [dcc.Graph(figure=hazards_status_fig, config={"displayModeBar": False})],
                                        className="hazards-chart-card",
                                    ),
                                    html.Div(
                                        [dcc.Graph(figure=hazards_cat_fig, config={"displayModeBar": False})],
                                        className="hazards-chart-card",
                                    ),
                                    html.Div(
                                        [dcc.Graph(figure=hazards_risk_fig, config={"displayModeBar": False})],
                                        className="hazards-chart-card",
                                    ),
                                ],
                                className="hazards-charts-row",
                            ),
                        ],
                        className="hazards-dashboard-section",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span("🔍", className="hazards-search-icon"),
                                    dcc.Input(
                                        id="hazards-search",
                                        type="text",
                                        placeholder="Search by name, category, or location...",
                                        className="hazards-search-input",
                                    ),
                                ],
                                className="hazards-search-wrap",
                            ),
                            html.Div(
                                [
                                    html.Label("Category:", className="hazards-filter-inline-label"),
                                    dcc.Dropdown(
                                        id="hazards-filter-category",
                                        options=[{"label": "All", "value": ""}] + category_options,
                                        value="",
                                        clearable=False,
                                        className="hazards-filter-dropdown",
                                    ),
                                ],
                                className="hazards-filter-inline",
                            ),
                            html.Div(
                                [
                                    html.Label("Status:", className="hazards-filter-inline-label"),
                                    dcc.Dropdown(
                                        id="hazards-filter-status",
                                        options=[{"label": "All", "value": ""}] + status_options,
                                        value="",
                                        clearable=False,
                                        className="hazards-filter-dropdown",
                                    ),
                                ],
                                className="hazards-filter-inline",
                            ),
                        ],
                        className="hazards-toolbar",
                    ),
                    html.Div(id="hazards-list-container", className="hazards-list-container"),
                ],
                className="hazards-body",
            ),
        ],
        className="hazards-page",
    )


# ---------------------------------------------------------------------------
# CAPA page – same layout as Hazards (pixel-aligned) with dashboard and graphs
# ---------------------------------------------------------------------------
def capa_page():
    """Corrective and preventive actions – dashboard (KPIs + charts), then toolbar and table."""
    all_c = list(SAMPLE_CAPA)
    n_total = len(all_c)
    status_counts = {}
    type_counts = {}
    priority_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for c in all_c:
        s = c.get("status") or "Unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
        t = c.get("type") or "Other"
        type_counts[t] = type_counts.get(t, 0) + 1
        p = c.get("priority") or ""
        if p in priority_counts:
            priority_counts[p] += 1
    n_open = status_counts.get("Open", 0)
    n_in_progress = status_counts.get("In progress", 0)
    n_closed = status_counts.get("Closed", 0)
    n_high_critical = priority_counts.get("High", 0) + priority_counts.get("Critical", 0)

    # Chart: CAPA by type (donut)
    type_labels = list(type_counts.keys()) or ["No data"]
    type_vals = list(type_counts.values()) or [0]
    colors = ["#5e4a7a", "#10b981", "#3b82f6", "#f59e0b", "#94a3b8"]
    capa_type_fig = go.Figure(
        data=[
            go.Pie(
                labels=type_labels,
                values=type_vals,
                hole=0.55,
                marker_colors=colors[: len(type_labels)],
                textinfo="label+percent",
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="CAPA by type",
            margin=dict(l=10, r=10, t=36, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            showlegend=False,
        ),
    )
    # Chart: CAPA by priority (bar)
    prio_labels = [k for k in priority_counts if priority_counts[k] > 0] or ["Low"]
    prio_vals = [priority_counts.get(k, 0) for k in prio_labels] or [0]
    prio_colors = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444"]
    capa_priority_fig = go.Figure(
        data=[
            go.Bar(
                x=prio_labels,
                y=prio_vals,
                marker_color=prio_colors[: len(prio_labels)],
                text=prio_vals,
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="By priority",
            margin=dict(l=20, r=20, t=36, b=50),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        ),
    )
    # Chart: CAPA by status (bar)
    status_labels = list(status_counts.keys()) or ["No data"]
    status_vals = list(status_counts.values()) or [0]
    capa_status_fig = go.Figure(
        data=[
            go.Bar(
                x=status_labels,
                y=status_vals,
                marker_color="#5e4a7a",
                text=status_vals,
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="By status",
            margin=dict(l=20, r=20, t=36, b=80),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            xaxis=dict(tickangle=-25),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        ),
    )

    type_options = [{"label": t, "value": t} for t in CAPA_ACTION_TYPES]
    priority_options = [{"label": p, "value": p} for p in CAPA_PRIORITIES]
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H2("CAPA", className="page-title"),
                            html.P("Manage corrective and preventive actions linked to hazards.", className="page-lead"),
                        ],
                        className="hazards-header-left",
                    ),
                    dcc.Link(
                        html.Button([html.Span("↑", className="hazards-add-icon"), "Add action"], className="primary-btn hazards-add-btn"),
                        href="/report",
                        className="hazards-header-action",
                    ),
                ],
                className="page-header hazards-page-header",
            ),
            html.Div(id="capa-action-toast", className="capa-action-toast"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("Total actions", className="capa-kpi-title"),
                                            html.Div("📌", className="capa-kpi-icon"),
                                            html.Div(str(n_total), className="capa-kpi-value"),
                                            html.Div("All CAPA", className="capa-kpi-sub"),
                                        ],
                                        className="capa-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Open", className="capa-kpi-title"),
                                            html.Div("🔓", className="capa-kpi-icon"),
                                            html.Div(str(n_open), className="capa-kpi-value"),
                                            html.Div("Not started", className="capa-kpi-sub"),
                                        ],
                                        className="capa-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("In progress", className="capa-kpi-title"),
                                            html.Div("🔄", className="capa-kpi-icon"),
                                            html.Div(str(n_in_progress), className="capa-kpi-value"),
                                            html.Div("Active", className="capa-kpi-sub"),
                                        ],
                                        className="capa-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Closed", className="capa-kpi-title"),
                                            html.Div("✅", className="capa-kpi-icon"),
                                            html.Div(str(n_closed), className="capa-kpi-value"),
                                            html.Div("Completed", className="capa-kpi-sub"),
                                        ],
                                        className="capa-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("High / Critical", className="capa-kpi-title"),
                                            html.Div("⚠️", className="capa-kpi-icon"),
                                            html.Div(str(n_high_critical), className="capa-kpi-value"),
                                            html.Div("Needs attention", className="capa-kpi-sub"),
                                        ],
                                        className="capa-kpi-card",
                                    ),
                                ],
                                className="capa-kpi-row",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [dcc.Graph(figure=capa_type_fig, config={"displayModeBar": False})],
                                        className="capa-chart-card",
                                    ),
                                    html.Div(
                                        [dcc.Graph(figure=capa_priority_fig, config={"displayModeBar": False})],
                                        className="capa-chart-card",
                                    ),
                                    html.Div(
                                        [dcc.Graph(figure=capa_status_fig, config={"displayModeBar": False})],
                                        className="capa-chart-card",
                                    ),
                                ],
                                className="capa-charts-row",
                            ),
                        ],
                        className="capa-dashboard-section",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span("🔍", className="hazards-search-icon"),
                                    dcc.Input(
                                        id="capa-search",
                                        type="text",
                                        placeholder="Search by action, hazard ID...",
                                        className="hazards-search-input",
                                    ),
                                ],
                                className="hazards-search-wrap",
                            ),
                            html.Div(
                                [
                                    html.Label("Type:", className="hazards-filter-inline-label"),
                                    dcc.Dropdown(
                                        id="capa-filter-type",
                                        options=[{"label": "All", "value": ""}] + type_options,
                                        value="",
                                        clearable=False,
                                        className="hazards-filter-dropdown",
                                    ),
                                ],
                                className="hazards-filter-inline",
                            ),
                            html.Div(
                                [
                                    html.Label("Priority:", className="hazards-filter-inline-label"),
                                    dcc.Dropdown(
                                        id="capa-filter-priority",
                                        options=[{"label": "All", "value": ""}] + priority_options,
                                        value="",
                                        clearable=False,
                                        className="hazards-filter-dropdown",
                                    ),
                                ],
                                className="hazards-filter-inline",
                            ),
                        ],
                        className="hazards-toolbar",
                    ),
                    html.Div(id="capa-list-container", className="hazards-list-container"),
                ],
                className="hazards-body",
            ),
        ],
        className="hazards-page capa-page",
    )


# ---------------------------------------------------------------------------
# Investigation page – dashboard with KPIs, charts, icons presenting investigation
# ---------------------------------------------------------------------------
def investigation_page():
    """Structured investigations for serious events – dashboard, icons, then table."""
    all_inv = list(SAMPLE_INVESTIGATIONS)
    n_total = len(all_inv)
    status_counts = {}
    with_lead = 0
    for inv in all_inv:
        s = inv.get("status") or "Unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
        if inv.get("lead") and inv.get("lead") != "—":
            with_lead += 1
    n_open = status_counts.get("Open", 0)
    n_in_progress = status_counts.get("In progress", 0)
    n_closed = status_counts.get("Closed", 0)

    # Charts: by status (donut) and status bar
    status_labels = list(status_counts.keys()) or ["No data"]
    status_vals = list(status_counts.values()) or [0]
    colors = ["#5e4a7a", "#10b981", "#3b82f6", "#f59e0b", "#94a3b8"]
    inv_status_fig = go.Figure(
        data=[
            go.Pie(
                labels=status_labels,
                values=status_vals,
                hole=0.55,
                marker_colors=colors[: len(status_labels)],
                textinfo="label+percent",
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="Investigations by status",
            margin=dict(l=10, r=10, t=36, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            showlegend=False,
        ),
    )
    inv_status_bar_fig = go.Figure(
        data=[
            go.Bar(
                x=status_labels,
                y=status_vals,
                marker_color="#5e4a7a",
                text=status_vals,
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="Status overview",
            margin=dict(l=20, r=20, t=36, b=80),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            xaxis=dict(tickangle=-25),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        ),
    )
    # Lead assigned count as simple bar (with lead vs without)
    lead_labels = ["Lead assigned", "No lead"]
    lead_vals = [with_lead, n_total - with_lead]
    inv_lead_fig = go.Figure(
        data=[
            go.Bar(
                x=lead_labels,
                y=lead_vals,
                marker_color=["#10b981", "#94a3b8"],
                text=lead_vals,
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="Lead assignment",
            margin=dict(l=20, r=20, t=36, b=60),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        ),
    )

    status_options = [{"label": "Open", "value": "Open"}, {"label": "In progress", "value": "In progress"}, {"label": "Closed", "value": "Closed"}]
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H2("Investigation", className="page-title"),
                            html.P("Structured investigations for serious events and incidents. Link to hazards and capture contributing factors.", className="page-lead"),
                        ],
                        className="hazards-header-left",
                    ),
                    dcc.Link(
                        html.Button([html.Span("↑", className="hazards-add-icon"), "New investigation"], className="primary-btn hazards-add-btn"),
                        href="/report",
                        className="hazards-header-action",
                    ),
                ],
                className="page-header hazards-page-header",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Investigation at a glance", className="inv-icons-section-title"),
                            html.Div(
                                [
                                    html.Div([html.Span("🔍", className="inv-icon-lg"), html.Span("Investigate", className="inv-icon-label")], className="inv-icon-tile"),
                                    html.Div([html.Span("📋", className="inv-icon-lg"), html.Span("Case file", className="inv-icon-label")], className="inv-icon-tile"),
                                    html.Div([html.Span("👤", className="inv-icon-lg"), html.Span("Lead", className="inv-icon-label")], className="inv-icon-tile"),
                                    html.Div([html.Span("📅", className="inv-icon-lg"), html.Span("Started", className="inv-icon-label")], className="inv-icon-tile"),
                                    html.Div([html.Span("✅", className="inv-icon-lg"), html.Span("Closed", className="inv-icon-label")], className="inv-icon-tile"),
                                ],
                                className="inv-icons-row",
                            ),
                        ],
                        className="inv-icons-block",
                    ),
                    html.Div(id="investigation-action-toast", className="capa-action-toast"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("Total investigations", className="inv-kpi-title"),
                                            html.Div("🔍", className="inv-kpi-icon"),
                                            html.Div(str(n_total), className="inv-kpi-value"),
                                            html.Div("All cases", className="inv-kpi-sub"),
                                        ],
                                        className="inv-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Open", className="inv-kpi-title"),
                                            html.Div("📋", className="inv-kpi-icon"),
                                            html.Div(str(n_open), className="inv-kpi-value"),
                                            html.Div("Not started", className="inv-kpi-sub"),
                                        ],
                                        className="inv-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("In progress", className="inv-kpi-title"),
                                            html.Div("🔄", className="inv-kpi-icon"),
                                            html.Div(str(n_in_progress), className="inv-kpi-value"),
                                            html.Div("Active", className="inv-kpi-sub"),
                                        ],
                                        className="inv-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Closed", className="inv-kpi-title"),
                                            html.Div("✅", className="inv-kpi-icon"),
                                            html.Div(str(n_closed), className="inv-kpi-value"),
                                            html.Div("Completed", className="inv-kpi-sub"),
                                        ],
                                        className="inv-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("With lead", className="inv-kpi-title"),
                                            html.Div("👤", className="inv-kpi-icon"),
                                            html.Div(str(with_lead), className="inv-kpi-value"),
                                            html.Div("Assigned", className="inv-kpi-sub"),
                                        ],
                                        className="inv-kpi-card",
                                    ),
                                ],
                                className="inv-kpi-row",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [dcc.Graph(figure=inv_status_fig, config={"displayModeBar": False})],
                                        className="inv-chart-card",
                                    ),
                                    html.Div(
                                        [dcc.Graph(figure=inv_status_bar_fig, config={"displayModeBar": False})],
                                        className="inv-chart-card",
                                    ),
                                    html.Div(
                                        [dcc.Graph(figure=inv_lead_fig, config={"displayModeBar": False})],
                                        className="inv-chart-card",
                                    ),
                                ],
                                className="inv-charts-row",
                            ),
                        ],
                        className="inv-dashboard-section",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span("🔍", className="hazards-search-icon"),
                                    dcc.Input(
                                        id="investigation-search",
                                        type="text",
                                        placeholder="Search by title, investigation ID, hazard...",
                                        className="hazards-search-input",
                                    ),
                                ],
                                className="hazards-search-wrap",
                            ),
                            html.Div(
                                [
                                    html.Label("Status:", className="hazards-filter-inline-label"),
                                    dcc.Dropdown(
                                        id="investigation-filter-status",
                                        options=[{"label": "All", "value": ""}] + status_options,
                                        value="",
                                        clearable=False,
                                        className="hazards-filter-dropdown",
                                    ),
                                ],
                                className="hazards-filter-inline",
                            ),
                        ],
                        className="hazards-toolbar",
                    ),
                    html.Div(id="investigation-list-container", className="hazards-list-container"),
                ],
                className="hazards-body",
            ),
        ],
        className="hazards-page investigation-page",
    )


# ---------------------------------------------------------------------------
# Exports page – robust card design with icons; all export buttons clickable
# ---------------------------------------------------------------------------
def exports_page():
    """Export data to PDF, CSV, and Excel – card layout with icons and clickable buttons."""
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Exports", className="page-title"),
                    html.P(
                        "Export reports, hazards, CAPA, and investigations to PDF, CSV, or Excel for audits and external reporting.",
                        className="page-lead",
                    ),
                ],
                className="page-header exports-page-header",
            ),
            html.Div(id="export-toast", className="export-toast"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div("📂", className="exports-card-icon"),
                                    html.H3("Hazards & reports", className="exports-card-title"),
                                    html.P("Export hazard reports and submitted data. Use filters on the Hazards page first, then export.", className="exports-card-desc"),
                                    html.Div(
                                        [
                                            html.Button("Export as CSV", id="export-hazards-csv", className="primary-btn exports-btn"),
                                            html.Button("Export as Excel", id="export-hazards-excel", className="primary-btn exports-btn"),
                                            html.Button("Export as PDF", id="export-hazards-pdf", className="primary-btn exports-btn"),
                                        ],
                                        className="exports-actions",
                                    ),
                                ],
                                className="exports-card",
                            ),
                            html.Div(
                                [
                                    html.Div("📌", className="exports-card-icon"),
                                    html.H3("CAPA actions", className="exports-card-title"),
                                    html.P("Export corrective and preventive actions with due dates and status.", className="exports-card-desc"),
                                    html.Div(
                                        [
                                            html.Button("Export as CSV", id="export-capa-csv", className="primary-btn exports-btn"),
                                            html.Button("Export as Excel", id="export-capa-excel", className="primary-btn exports-btn"),
                                        ],
                                        className="exports-actions",
                                    ),
                                ],
                                className="exports-card",
                            ),
                            html.Div(
                                [
                                    html.Div("🔍", className="exports-card-icon"),
                                    html.H3("Investigations", className="exports-card-title"),
                                    html.P("Export investigation summaries and contributing factors. PDF is suitable for printable reports.", className="exports-card-desc"),
                                    html.Div(
                                        [
                                            html.Button("Export as PDF", id="export-inv-pdf", className="primary-btn exports-btn"),
                                            html.Button("Export as CSV", id="export-inv-csv", className="primary-btn exports-btn"),
                                        ],
                                        className="exports-actions",
                                    ),
                                ],
                                className="exports-card",
                            ),
                            html.Div(
                                [
                                    html.Div("📜", className="exports-card-icon"),
                                    html.H3("Audit trail", className="exports-card-title"),
                                    html.P("Export system audit log (who did what, when) for compliance and reviews.", className="exports-card-desc"),
                                    html.Div(
                                        [html.Button("Export as CSV", id="export-audit-csv", className="primary-btn exports-btn")],
                                        className="exports-actions",
                                    ),
                                ],
                                className="exports-card",
                            ),
                        ],
                        className="exports-grid",
                    ),
                ],
                className="exports-body",
            ),
        ],
        className="exports-page",
    )


def risk_triage_page():
    """Risk & Triage dashboard: KPIs, charts, risk matrix, escalation rules, and hazards table."""
    all_hazards = list(SAMPLE_HAZARDS) + list(HAZARDS)
    awaiting = [h for h in all_hazards if h.get("status") in ("Submitted", "Triage")]
    n_awaiting = len(awaiting)
    n_high_extreme = sum(1 for h in all_hazards if h.get("perceived_risk") in ("High", "Critical"))
    n_in_progress = sum(1 for h in all_hazards if h.get("status") in ("Assigned actions", "In progress"))
    n_closed = sum(1 for h in all_hazards if h.get("status") == "Closed")
    status_counts = {}
    risk_counts = {"Low": 0, "Moderate": 0, "High": 0, "Critical": 0}
    for h in all_hazards:
        s = h.get("status") or "Unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
        r = h.get("perceived_risk") or ""
        if r in risk_counts:
            risk_counts[r] += 1
    # Chart: Hazards by risk level
    risk_labels = [k for k in risk_counts if risk_counts[k] > 0] or ["Low"]
    risk_vals = [risk_counts.get(k, 0) for k in risk_labels] or [0]
    risk_color_map = {"Low": "#10b981", "Moderate": "#3b82f6", "High": "#f59e0b", "Critical": "#ef4444"}
    risk_colors = [risk_color_map.get(k, "#94a3b8") for k in risk_labels]
    risk_level_fig = go.Figure(
        data=[
            go.Bar(
                x=risk_labels,
                y=risk_vals,
                marker_color=risk_colors,
                text=risk_vals,
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="Hazards by risk level",
            margin=dict(l=20, r=20, t=36, b=50),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        ),
    )
    # Chart: Triage status (donut)
    status_labels = list(status_counts.keys()) or ["No data"]
    status_vals = list(status_counts.values()) or [0]
    colors = ["#5e4a7a", "#10b981", "#3b82f6", "#f59e0b", "#94a3b8", "#ef4444"]
    triage_status_fig = go.Figure(
        data=[
            go.Pie(
                labels=status_labels,
                values=status_vals,
                hole=0.55,
                marker_colors=colors[: len(status_labels)],
                textinfo="label+percent",
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="Status breakdown",
            margin=dict(l=10, r=10, t=36, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            showlegend=False,
        ),
    )
    # Chart: Risk score distribution (dummy distribution for demo)
    score_buckets = ["Low (1-6)", "Medium (7-12)", "High (13-20)", "Extreme (21-25)"]
    score_vals = [4, 3, 2, 1]  # demo counts
    score_fig = go.Figure(
        data=[
            go.Bar(
                x=score_buckets,
                y=score_vals,
                marker_color=["#10b981", "#3b82f6", "#f59e0b", "#ef4444"],
                text=score_vals,
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="Risk score distribution",
            margin=dict(l=20, r=20, t=36, b=70),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            xaxis=dict(tickangle=-25),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        ),
    )
    # Build 5×5 matrix
    matrix_header = html.Tr(
        [html.Th("", className="risk-matrix-corner")] +
        [html.Th(SEVERITY_LABELS[i], className="risk-matrix-th") for i in range(1, 6)]
    )
    matrix_rows = []
    for L in range(1, 6):
        cells = [html.Td(LIKELIHOOD_LABELS[L], className="risk-matrix-row-label")]
        for S in range(1, 6):
            score, level = risk_matrix_level(L, S)
            level_class = f"risk-cell-{level.lower()}"
            cells.append(html.Td(f"{score} {level}", className=f"risk-matrix-cell {level_class}"))
        matrix_rows.append(html.Tr(cells))
    matrix_table = html.Table(
        [html.Thead(matrix_header), html.Tbody(matrix_rows)],
        className="risk-matrix-table",
    )
    escalation_cards = [
        html.Div(
            [
                html.Div(level, className="risk-escalation-level"),
                html.P(ESCALATION_RULES[level], className="risk-escalation-desc"),
            ],
            className="risk-escalation-card",
        )
        for level in RISK_LEVELS_DISPLAY
    ]
    awaiting_rows = [
        html.Tr(
            [
                html.Td(h.get("title") or "—"),
                html.Td(h.get("category") or "—"),
                html.Td(h.get("perceived_risk") or "—"),
                html.Td(h.get("status", "—")),
            ],
            className="risk-triage-tr",
        )
        for h in awaiting[:10]
    ]
    awaiting_table = html.Table(
        [
            html.Thead(html.Tr([html.Th("HAZARD"), html.Th("CATEGORY"), html.Th("PERCEIVED RISK"), html.Th("STATUS")])),
            html.Tbody(awaiting_rows),
        ],
        className="risk-triage-table",
    ) if awaiting_rows else html.P("No hazards currently awaiting triage.", className="risk-triage-empty")
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Risk & Triage", className="page-title"),
                    html.P(
                        "Assess risk with the matrix, apply escalation rules, and manage hazards awaiting triage.",
                        className="page-lead",
                    ),
                ],
                className="page-header risk-triage-header",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("Awaiting triage", className="risk-kpi-title"),
                                            html.Div("⏳", className="risk-kpi-icon"),
                                            html.Div(str(n_awaiting), className="risk-kpi-value"),
                                            html.Div("Need review", className="risk-kpi-sub"),
                                        ],
                                        className="risk-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("High / Critical", className="risk-kpi-title"),
                                            html.Div("⚠️", className="risk-kpi-icon"),
                                            html.Div(str(n_high_extreme), className="risk-kpi-value"),
                                            html.Div("Priority focus", className="risk-kpi-sub"),
                                        ],
                                        className="risk-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("In progress", className="risk-kpi-title"),
                                            html.Div("🔧", className="risk-kpi-icon"),
                                            html.Div(str(n_in_progress), className="risk-kpi-value"),
                                            html.Div("Actions active", className="risk-kpi-sub"),
                                        ],
                                        className="risk-kpi-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Closed", className="risk-kpi-title"),
                                            html.Div("✅", className="risk-kpi-icon"),
                                            html.Div(str(n_closed), className="risk-kpi-value"),
                                            html.Div("Resolved", className="risk-kpi-sub"),
                                        ],
                                        className="risk-kpi-card",
                                    ),
                                ],
                                className="risk-kpi-row",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [dcc.Graph(figure=risk_level_fig, config={"displayModeBar": False})],
                                        className="risk-chart-card",
                                    ),
                                    html.Div(
                                        [dcc.Graph(figure=triage_status_fig, config={"displayModeBar": False})],
                                        className="risk-chart-card",
                                    ),
                                    html.Div(
                                        [dcc.Graph(figure=score_fig, config={"displayModeBar": False})],
                                        className="risk-chart-card",
                                    ),
                                ],
                                className="risk-charts-row",
                            ),
                        ],
                        className="risk-dashboard-section",
                    ),
                    html.Div(
                        [
                            html.H3("Risk matrix (5×5)", className="report-section-title"),
                            html.P(
                                "Likelihood × Severity = Score. Levels: Low (1–6), Medium (7–12), High (13–20), Extreme (21–25).",
                                className="risk-matrix-intro",
                            ),
                            matrix_table,
                        ],
                        className="report-section risk-matrix-section",
                    ),
                    html.Div(
                        [
                            html.H3("Escalation rules by risk level", className="report-section-title"),
                            html.Div(escalation_cards, className="risk-escalation-grid"),
                        ],
                        className="report-section risk-escalation-section",
                    ),
                    html.Div(
                        [
                            html.H3("Hazards awaiting triage", className="report-section-title"),
                            awaiting_table,
                        ],
                        className="report-section risk-triage-section",
                    ),
                ],
                className="page-body-card risk-triage-card",
            ),
        ],
        className="risk-triage-page",
    )


# ---------------------------------------------------------------------------
# Dashboard page – picture-perfect layout (reference style)
# ---------------------------------------------------------------------------
def dashboard_page():
    # KPI card data: metric, label, trend text, trend up (green)
    # Bar chart: Reports by day (Submitted vs Closed) – Mon–Sun
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    submitted = [42, 58, 65, 72, 68, 45, 38]
    closed = [35, 48, 52, 61, 55, 40, 32]
    bar_in_out = go.Figure(
        data=[
            go.Bar(name="Submitted", x=days, y=submitted, marker_color="#5e4a7a"),
            go.Bar(name="Closed", x=days, y=closed, marker_color="#94a3b8"),
        ],
        layout=go.Layout(
            title="Reports (Submitted vs Closed)",
            barmode="group",
            margin=dict(l=20, r=20, t=36, b=20),
            legend=dict(orientation="h", y=1.02, x=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=260,
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)", dtick=20),
        ),
    )

    # Donut: Lead sources style → Report sources / categories
    donut_sources = go.Figure(
        data=[
            go.Pie(
                labels=["Airside / Ramp", "Aircraft servicing", "GSE", "Cargo", "Other"],
                values=[42, 28, 18, 8, 4],
                hole=0.6,
                marker_colors=["#5e4a7a", "#10b981", "#3b82f6", "#f59e0b", "#94a3b8"],
                textinfo="label+percent",
                textposition="outside",
            )
        ],
        layout=go.Layout(
            title="Report categories",
            margin=dict(l=10, r=10, t=36, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=260,
            showlegend=False,
        ),
    )

    # Line chart: Weekly trends (Conversations + Open)
    weeks = ["W1", "W2", "W3", "W4"]
    conversations = [120, 165, 195, 180]
    hot_leads = [14, 18, 22, 19]
    line_trends = go.Figure(
        data=[
            go.Scatter(name="Reports", x=weeks, y=conversations, mode="lines+markers", line=dict(color="#5e4a7a", width=2), marker=dict(size=8)),
            go.Scatter(name="Open", x=weeks, y=hot_leads, mode="lines+markers", line=dict(color="#10b981", width=2), marker=dict(size=8)),
        ],
        layout=go.Layout(
            title="Weekly trends",
            margin=dict(l=20, r=20, t=36, b=20),
            legend=dict(orientation="h", y=1.02, x=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=220,
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        ),
    )

    # Reports by risk level (replaces Bot vs Human)
    risk_labels = ["Low", "Medium", "High", "Critical"]
    risk_values = [42, 28, 18, 12]
    risk_level_fig = go.Figure(
        data=[
            go.Bar(
                x=risk_labels,
                y=risk_values,
                marker_color=["#10b981", "#3b82f6", "#f59e0b", "#ef4444"],
            ),
        ],
        layout=go.Layout(
            title="Reports by risk level",
            margin=dict(l=20, r=20, t=36, b=50),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=200,
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        ),
    )
    # Alias so any reference to the old chart name still works
    bot_human = risk_level_fig

    # Response time distribution
    resp_labels = ["< 1 day", "1–2 days", "2–5 days", "> 5 days"]
    resp_values = [48, 28, 16, 8]
    resp_dist = go.Figure(
        data=[
            go.Bar(x=resp_labels, y=resp_values, marker_color=["#10b981", "#3b82f6", "#f59e0b", "#94a3b8"]),
        ],
        layout=go.Layout(
            title="Time to triage",
            margin=dict(l=20, r=20, t=36, b=60),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            height=200,
        ),
    )

    return html.Div(
        [
            html.Div(
                [html.H2("Dashboard", className="page-title")],
                className="page-header",
            ),
            html.Div(
                [
                    # Top row: 4 summary cards with icon + trend
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div("Total Reports", className="dashboard-kpi-title"),
                                    html.Div("💬", className="dashboard-kpi-icon"),
                                    html.Div("1,247", className="dashboard-kpi-value"),
                                    html.Div("+12% vs last week", className="dashboard-kpi-trend"),
                                ],
                                className="dashboard-kpi-card",
                            ),
                            html.Div(
                                [
                                    html.Div("Open", className="dashboard-kpi-title"),
                                    html.Div("🔥", className="dashboard-kpi-icon"),
                                    html.Div("89", className="dashboard-kpi-value"),
                                    html.Div("+8% vs last week", className="dashboard-kpi-trend"),
                                ],
                                className="dashboard-kpi-card",
                            ),
                            html.Div(
                                [
                                    html.Div("Bot Handled", className="dashboard-kpi-title"),
                                    html.Div("🤖", className="dashboard-kpi-icon"),
                                    html.Div("68%", className="dashboard-kpi-value"),
                                    html.Div("+5% vs last week", className="dashboard-kpi-trend"),
                                ],
                                className="dashboard-kpi-card",
                            ),
                            html.Div(
                                [
                                    html.Div("Avg Triage Time", className="dashboard-kpi-title"),
                                    html.Div("⏱", className="dashboard-kpi-icon"),
                                    html.Div("2.4 min", className="dashboard-kpi-value"),
                                    html.Div("-15% vs last week", className="dashboard-kpi-trend"),
                                ],
                                className="dashboard-kpi-card",
                            ),
                        ],
                        className="dashboard-kpi-row",
                    ),
                    # Middle: bar chart (2/3) + donut (1/3)
                    html.Div(
                        [
                            html.Div(
                                [dcc.Graph(figure=bar_in_out, config={"displayModeBar": False})],
                                className="dashboard-chart-card dashboard-chart-left",
                            ),
                            html.Div(
                                [dcc.Graph(figure=donut_sources, config={"displayModeBar": False})],
                                className="dashboard-chart-card dashboard-chart-right",
                            ),
                        ],
                        className="dashboard-charts-split",
                    ),
                    # Bottom: left 2/3 (two stacked charts), right 1/3 (Quick Stats + small chart)
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [dcc.Graph(figure=line_trends, config={"displayModeBar": False})],
                                        className="dashboard-chart-card",
                                    ),
                                    html.Div(
                                        [dcc.Graph(figure=risk_level_fig, config={"displayModeBar": False})],
                                        className="dashboard-chart-card",
                                    ),
                                ],
                                className="dashboard-bottom-left",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("Quick Stats", className="dashboard-quick-title"),
                                            html.Div([html.Span("23", className="dashboard-quick-value"), html.Span("Pending triage", className="dashboard-quick-label")], className="dashboard-quick-row"),
                                            html.Div([html.Span("156", className="dashboard-quick-value"), html.Span("Unread messages", className="dashboard-quick-label")], className="dashboard-quick-row"),
                                            html.Div([html.Span("12", className="dashboard-quick-value"), html.Span("Needs attention", className="dashboard-quick-label")], className="dashboard-quick-row"),
                                        ],
                                        className="dashboard-chart-card dashboard-quick-stats",
                                    ),
                                    html.Div(
                                        [dcc.Graph(figure=resp_dist, config={"displayModeBar": False})],
                                        className="dashboard-chart-card",
                                    ),
                                ],
                                className="dashboard-bottom-right",
                            ),
                        ],
                        className="dashboard-bottom",
                    ),
                ],
                className="dashboard-body",
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Admin page – premium UI for managing users, taxonomy, workflow, risk, system
# ---------------------------------------------------------------------------
def _admin_card(title, icon, description, children, action_label=None, action_id=None):
    """Reusable admin card with icon, title, description, and optional primary action."""
    header = html.Div(
        [
            html.Div(icon, className="admin-card-icon"),
            html.Div(
                [
                    html.H3(title, className="admin-card-title"),
                    html.P(description, className="admin-card-desc") if description else None,
                ],
                className="admin-card-header-text",
            ),
        ],
        className="admin-card-header",
    )
    action_btn = html.Button(action_label, id=action_id, className="primary-btn admin-card-action") if action_label and action_id else None
    return html.Div(
        [
            html.Div(
                [header, action_btn],
                className="admin-card-top",
            ),
            html.Div(children, className="admin-card-body"),
        ],
        className="admin-card",
    )


def _admin_section_users():
    """Users & roles: roles table + sample users table + Add user."""
    roles_table = html.Table(
        [
            html.Thead(html.Tr([html.Th("Role"), html.Th("Permissions")])),
            html.Tbody(
                [
                    html.Tr([html.Td(role, className="admin-td-role"), html.Td(ROLE_PERMISSIONS.get(role, "—"), className="admin-td-permissions")])
                    for role in ROLES
                ]
            ),
        ],
        className="admin-table",
    )
    sample_users = [
        {"name": "Jane Smith", "email": "jane.smith@example.com", "role": "Safety (SMS/QHSE)", "last_login": "2026-02-25"},
        {"name": "John Doe", "email": "john.doe@example.com", "role": "Administrator", "last_login": "2026-02-26"},
        {"name": "Alex Lee", "email": "alex.lee@example.com", "role": "Supervisor / Team Lead", "last_login": "2026-02-24"},
    ]
    users_table = html.Table(
        [
            html.Thead(html.Tr([html.Th("Name"), html.Th("Email"), html.Th("Role"), html.Th("Last login"), html.Th("Actions")])),
            html.Tbody(
                [
                    html.Tr(
                        [
                            html.Td(u["name"]),
                            html.Td(u["email"]),
                            html.Td(u["role"]),
                            html.Td(u["last_login"]),
                            html.Td(
                                html.Div(
                                    [
                                        html.Button("Edit", id={"type": "admin-user-edit", "index": u["email"]}, className="admin-btn admin-btn-edit"),
                                        html.Button("Deactivate", id={"type": "admin-user-deactivate", "index": u["email"]}, className="admin-btn admin-btn-danger"),
                                    ],
                                    className="admin-actions-cell",
                                )
                            ),
                        ]
                    )
                    for u in sample_users
                ]
            ),
        ],
        className="admin-table",
    )
    return html.Div(
        [
            _admin_card("Roles & permissions", "👥", "Manage system roles and what each role can do. Changes apply to new sessions.", roles_table),
            _admin_card("Users", "👤", "Add and manage user accounts. Assign roles and deactivate access when needed.", [users_table], "Add user", "admin-add-user-btn"),
        ],
        className="admin-section-content",
    )


def _admin_section_stations():
    """Stations & areas: configurable stations and areas for hazard reporting."""
    sample_stations = [
        {"station": "Main Ramp", "areas": "Stand 1–24, Gates A–B"},
        {"station": "North Ramp", "areas": "Stand 25–40"},
        {"station": "Cargo", "areas": "Cargo Bay A, B"},
        {"station": "Terminal B", "areas": "Gate B1–B20"},
    ]
    table = html.Table(
        [
            html.Thead(html.Tr([html.Th("Station"), html.Th("Areas"), html.Th("Actions")])),
            html.Tbody(
                [
                    html.Tr(
                        [
                            html.Td(s["station"]),
                            html.Td(s["areas"]),
                            html.Td(
                                html.Div(
                                    [html.Button("Edit", id={"type": "admin-station-edit", "index": s["station"]}, className="admin-btn admin-btn-edit")],
                                    className="admin-actions-cell",
                                )
                            ),
                        ]
                    )
                    for s in sample_stations
                ]
            ),
        ],
        className="admin-table",
    )
    return html.Div(
        [_admin_card("Stations & areas", "📍", "Define stations and areas used in hazard reports. Used for filtering and dashboards.", [table], "Add station", "admin-add-station-btn")],
        className="admin-section-content",
    )


def _admin_section_categories():
    """Categories & taxonomy: hazard categories and subcategories from config."""
    rows = []
    for cat in HAZARD_AREAS:
        subcats = SUBCATEGORIES.get(cat, [])
        sub_list = html.Ul([html.Li(s) for s in subcats], className="admin-subcat-list") if subcats else html.Span("—", className="admin-no-sub")
        rows.append(
            html.Tr(
                [
                    html.Td(html.Strong(cat), className="admin-td-cat"),
                    html.Td(sub_list),
                    html.Td(
                        html.Div(
                            [html.Button("Edit", id={"type": "admin-cat-edit", "index": cat}, className="admin-btn admin-btn-edit")],
                            className="admin-actions-cell",
                        )
                    ),
                ]
            )
        )
    table = html.Table(
        [
            html.Thead(html.Tr([html.Th("Category"), html.Th("Subcategories"), html.Th("Actions")])),
            html.Tbody(rows),
        ],
        className="admin-table",
    )
    return html.Div(
        [_admin_card("Hazard taxonomy", "📂", "Categories and subcategories for hazard classification. Align with local operations and regulatory requirements.", [table], "Add category", "admin-add-category-btn")],
        className="admin-section-content",
    )


def _admin_section_workflow():
    """Workflow & statuses: ordered list of workflow statuses."""
    status_list = html.Ol(
        [html.Li(s, className="admin-workflow-item") for s in WORKFLOW_STATUSES],
        className="admin-workflow-list",
    )
    return html.Div(
        [
            _admin_card("Workflow statuses", "🔄", "Define the lifecycle of a hazard report. Order matters for triage and reporting.", [status_list], "Edit order", "admin-edit-workflow-btn"),
            _admin_card("Classification types", "🏷️", "Types used when classifying a report (hazard, near miss, incident, etc.).", [html.P(", ".join(CLASSIFICATION_TYPES), className="admin-inline-list")], "Edit", "admin-edit-classification-btn"),
        ],
        className="admin-section-content",
    )


def _admin_section_risk():
    """Risk matrix & escalation rules."""
    levels_table = html.Table(
        [
            html.Thead(html.Tr([html.Th("Risk level"), html.Th("Escalation rule")])),
            html.Tbody([html.Tr([html.Td(level), html.Td(ESCALATION_RULES.get(level, "—"))]) for level in RISK_LEVELS_DISPLAY]),
        ],
        className="admin-table",
    )
    likelihood_list = html.Div([html.Div(f"{k} – {v}", className="admin-matrix-row") for k, v in LIKELIHOOD_LABELS.items()], className="admin-matrix-block")
    severity_list = html.Div([html.Div(f"{k} – {v}", className="admin-matrix-row") for k, v in SEVERITY_LABELS.items()], className="admin-matrix-block")
    return html.Div(
        [
            _admin_card("Escalation rules", "⚠️", "Automatic actions and notifications by risk level. Edit to match your SMS policy.", [levels_table], "Edit rules", "admin-edit-escalation-btn"),
            _admin_card("Likelihood scale (1–5)", "📊", "Used in risk matrix for likelihood rating.", [likelihood_list]),
            _admin_card("Severity scale (1–5)", "📊", "Used in risk matrix for severity rating.", [severity_list]),
        ],
        className="admin-section-content",
    )


def _admin_section_capa():
    """CAPA action types and priorities."""
    types_block = html.Div([html.Span(t, className="admin-pill") for t in CAPA_ACTION_TYPES], className="admin-pills")
    prio_block = html.Div([html.Span(p, className="admin-pill admin-pill-priority") for p in CAPA_PRIORITIES], className="admin-pills")
    return html.Div(
        [
            _admin_card("CAPA action types", "📌", "Types of corrective/preventive actions (Immediate, Corrective, Preventive).", [types_block], "Edit types", "admin-edit-capa-types-btn"),
            _admin_card("CAPA priorities", "🎯", "Priority levels for actions (Low, Medium, High, Critical).", [prio_block], "Edit priorities", "admin-edit-capa-prio-btn"),
        ],
        className="admin-section-content",
    )


def _admin_section_system():
    """System settings: app name, audit retention, etc."""
    fields = [
        ("Application name", "HIRS – Hazard Identification & Reporting System"),
        ("Audit log retention", "365 days"),
        ("Time zone", "UTC"),
        ("Session timeout", "8 hours"),
    ]
    rows = [html.Tr([html.Td(html.Strong(label), className="admin-sys-label"), html.Td(value)]) for label, value in fields]
    table = html.Table([html.Tbody(rows)], className="admin-table admin-table-plain")
    return html.Div(
        [_admin_card("System settings", "⚙️", "Global application settings. Changes may require restart.", [table], "Save changes", "admin-save-system-btn")],
        className="admin-section-content",
    )


ADMIN_SECTIONS = {
    "users": _admin_section_users,
    "stations": _admin_section_stations,
    "categories": _admin_section_categories,
    "workflow": _admin_section_workflow,
    "risk": _admin_section_risk,
    "capa": _admin_section_capa,
    "system": _admin_section_system,
}

ADMIN_NAV_ITEMS = [
    ("users", "👥", "Users & roles"),
    ("stations", "📍", "Stations & areas"),
    ("categories", "📂", "Categories & taxonomy"),
    ("workflow", "🔄", "Workflow & statuses"),
    ("risk", "⚠️", "Risk matrix & escalation"),
    ("capa", "📌", "CAPA settings"),
    ("system", "⚙️", "System"),
]


def admin_page():
    """Admin: premium UI with sidebar nav and section-based content."""
    nav_items = [
        ("users", "👥", "Users & roles"),
        ("stations", "📍", "Stations & areas"),
        ("categories", "📂", "Categories & taxonomy"),
        ("workflow", "🔄", "Workflow & statuses"),
        ("risk", "⚠️", "Risk matrix & escalation"),
        ("capa", "📌", "CAPA settings"),
        ("system", "⚙️", "System"),
    ]
    nav_buttons = []
    for section_id, icon, label in ADMIN_NAV_ITEMS:
        nav_buttons.append(
            html.Button(
                [html.Span(icon, className="admin-nav-icon"), html.Span(label, className="admin-nav-label")],
                id={"type": "admin-nav", "index": section_id},
                className="admin-nav-item",
                n_clicks=0,
            )
        )
    sidebar_nav = html.Div(nav_buttons, className="admin-sidebar-nav", id="admin-sidebar-nav-wrap")

    return html.Div(
        [
            html.Div(
                [
                    html.H2("Admin", className="admin-page-title"),
                    html.P("Configure users, taxonomy, workflow, risk matrix, and system settings. Changes here affect the whole system.", className="admin-page-lead"),
                ],
                className="admin-header",
            ),
            dcc.Store(id="admin-section-store", data="users"),
            html.Div(id="admin-toast", className="admin-toast"),
            html.Div(
                [
                    html.Aside(
                        html.Div(sidebar_nav, className="admin-sidebar-inner"),
                        className="admin-sidebar",
                    ),
                    html.Main(
                        html.Div(id="admin-content", className="admin-main-inner"),
                        className="admin-main",
                    ),
                ],
                className="admin-body",
            ),
        ],
        className="admin-page",
    )


def page_for_path(pathname: str):
    name = (pathname or "/dashboard").lstrip("/") or "dashboard"
    valid_names = {n for n, _, _ in SIDEBAR_ITEMS}
    if name not in valid_names:
        name = "report"
    title = next(label for n, _, label in SIDEBAR_ITEMS if n == name)

    if name == "report":
        return report_page()
    if name == "dashboard":
        return dashboard_page()
    if name == "requirements":
        return html.Div(
            [
                html.Div(
                    [html.H2("Requirements", className="page-title")],
                    className="page-header",
                ),
                requirements_document(),
            ]
        )
    if name == "reference":
        return reference_page()
    if name == "hazards":
        return hazards_page()
    if name == "risk":
        return risk_triage_page()
    if name == "capa":
        return capa_page()
    if name == "investigation":
        return investigation_page()
    if name == "exports":
        return exports_page()
    if name == "admin":
        return admin_page()
    return page_shell(title)


app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="auth-store", data={"logged_in": False, "user": "Jane Smith", "region": "AMER-EMEA"}),
        top_header(),
        html.Div(
            [
                sidebar(),
                html.Div(id="page-content", className="page-content"),
            ],
            className="layout-row",
            id="main-layout-row",
        ),
    ],
    className="app-root",
    id="app-root",
)


@app.callback(
    Output("page-content", "children"),
    Output("url", "pathname", allow_duplicate=True),
    Input("url", "pathname"),
    Input("auth-store", "data"),
    prevent_initial_call='initial_duplicate',
)
def render_page(pathname, auth):
    """Serve login page, logout placeholder, or main app; redirect when auth required."""
    pathname = pathname or "/dashboard"
    logged_in = auth.get("logged_in", False) if auth else False

    if pathname == "/login":
        if logged_in:
            return None, "/dashboard"
        return login_page(), dash.no_update
    if pathname == "/logout":
        return logout_placeholder(), dash.no_update
    if not logged_in:
        return None, "/login"
    return page_for_path(pathname), dash.no_update


@app.callback(
    Output("auth-store", "data"),
    Output("url", "pathname", allow_duplicate=True),
    Input("url", "pathname"),
    prevent_initial_call=True,
)
def logout_clear_and_redirect(pathname):
    """On /logout: clear auth and redirect to /login."""
    if pathname != "/logout":
        raise PreventUpdate
    return {"logged_in": False, "user": "", "region": "AMER-EMEA"}, "/login"


@app.callback(
    Output("auth-store", "data", allow_duplicate=True),
    Output("url", "pathname", allow_duplicate=True),
    Input("login-submit", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def login_submit(n_clicks, email, password):
    """On login submit: set auth and navigate to dashboard (demo: any credentials)."""
    if not n_clicks:
        raise PreventUpdate
    return {"logged_in": True, "user": "Jane Smith", "region": "AMER-EMEA"}, "/dashboard"


@app.callback(
    Output("main-layout-row", "className"),
    Input("url", "pathname"),
)
def layout_row_class(pathname):
    """Hide sidebar on login page (full-width login)."""
    if pathname == "/login":
        return "layout-row login-route"
    return "layout-row"


@app.callback(
    Output("top-right-content", "children"),
    Input("auth-store", "data"),
)
def header_right_content(auth):
    """Show user + region + Log out when logged in; Sign in link when logged out."""
    if auth and auth.get("logged_in"):
        return [
            html.Span(auth.get("user") or "Jane Smith", className="top-user"),
            html.Span((auth.get("region") or "AMER–EMEA") + " ▾", className="top-region"),
            html.Div("+", className="top-plus", id="top-add-btn"),
            dcc.Link("Log out", href="/logout", className="top-logout-link"),
        ]
    return [
        dcc.Link("Sign in", href="/login", className="top-signin-link"),
    ]


@app.callback(
    Output("admin-section-store", "data"),
    Input({"type": "admin-nav", "index": ALL}, "n_clicks"),
)
def admin_nav_click(n_clicks_list):
    """Switch admin section when a nav item is clicked."""
    if not callback_context.triggered:
        raise PreventUpdate
    prop = callback_context.triggered[0]["prop_id"]
    if ".n_clicks" not in prop:
        raise PreventUpdate
    try:
        id_str = prop.split(".n_clicks")[0].strip()
        id_dict = json.loads(id_str)
        section = id_dict.get("index", "users")
    except (json.JSONDecodeError, KeyError):
        raise PreventUpdate
    return section


@app.callback(
    Output("admin-content", "children"),
    Input("admin-section-store", "data"),
)
def admin_content_from_store(section):
    """Render admin section content based on selected section."""
    if not section:
        section = "users"
    builder = ADMIN_SECTIONS.get(section, _admin_section_users)
    return builder()


@app.callback(
    Output("admin-sidebar-nav-wrap", "children"),
    Input("admin-section-store", "data"),
)
def admin_nav_active(section):
    """Rebuild nav with active state for current section."""
    if not section:
        section = "users"
    buttons = []
    for section_id, icon, label in ADMIN_NAV_ITEMS:
        is_active = section_id == section
        buttons.append(
            html.Button(
                [html.Span(icon, className="admin-nav-icon"), html.Span(label, className="admin-nav-label")],
                id={"type": "admin-nav", "index": section_id},
                className="admin-nav-item admin-nav-item--active" if is_active else "admin-nav-item",
                n_clicks=0,
            )
        )
    return buttons


@app.callback(
    Output("admin-toast", "children"),
    Input("admin-add-user-btn", "n_clicks"),
    Input("admin-add-station-btn", "n_clicks"),
    Input("admin-add-category-btn", "n_clicks"),
    Input("admin-edit-workflow-btn", "n_clicks"),
    Input("admin-edit-classification-btn", "n_clicks"),
    Input("admin-edit-escalation-btn", "n_clicks"),
    Input("admin-edit-capa-types-btn", "n_clicks"),
    Input("admin-edit-capa-prio-btn", "n_clicks"),
    Input("admin-save-system-btn", "n_clicks"),
)
def admin_primary_action_toast(
    add_user, add_station, add_cat, edit_workflow, edit_class, edit_esc, edit_capa_t, edit_capa_p, save_sys
):
    """Show toast when a primary admin action button is clicked (demo)."""
    if not callback_context.triggered:
        raise PreventUpdate
    trigger_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    messages = {
        "admin-add-user-btn": "Add user dialog would open (not implemented in demo).",
        "admin-add-station-btn": "Add station dialog would open (not implemented in demo).",
        "admin-add-category-btn": "Add category dialog would open (not implemented in demo).",
        "admin-edit-workflow-btn": "Edit workflow order would open (not implemented in demo).",
        "admin-edit-classification-btn": "Edit classification types would open (not implemented in demo).",
        "admin-edit-escalation-btn": "Edit escalation rules would open (not implemented in demo).",
        "admin-edit-capa-types-btn": "Edit CAPA types would open (not implemented in demo).",
        "admin-edit-capa-prio-btn": "Edit CAPA priorities would open (not implemented in demo).",
        "admin-save-system-btn": "System settings saved (demo).",
    }
    msg = messages.get(trigger_id)
    if not msg:
        raise PreventUpdate
    return html.Span(msg, className="admin-toast-msg")


@app.callback(
    Output("admin-toast", "children", allow_duplicate=True),
    Input({"type": "admin-user-edit", "index": ALL}, "n_clicks"),
    Input({"type": "admin-user-deactivate", "index": ALL}, "n_clicks"),
    Input({"type": "admin-station-edit", "index": ALL}, "n_clicks"),
    Input({"type": "admin-cat-edit", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def admin_table_action_toast(*_):
    """Show toast when Edit/Deactivate (or other table action) is clicked in admin."""
    if not callback_context.triggered:
        raise PreventUpdate
    prop = callback_context.triggered[0]["prop_id"]
    if ".n_clicks" not in prop:
        raise PreventUpdate
    try:
        id_str = prop.split(".n_clicks")[0].strip()
        id_dict = json.loads(id_str)
        action_type = id_dict.get("type", "")
        index = id_dict.get("index", "")
    except (json.JSONDecodeError, KeyError):
        raise PreventUpdate
    if "admin-user-edit" in action_type:
        return html.Span(f"Edit user {index} (dialog not implemented in demo).", className="admin-toast-msg")
    if "admin-user-deactivate" in action_type:
        return html.Span(f"Deactivate user {index} (confirm not implemented in demo).", className="admin-toast-msg")
    if "admin-station-edit" in action_type:
        return html.Span(f"Edit station '{index}' (dialog not implemented in demo).", className="admin-toast-msg")
    if "admin-cat-edit" in action_type:
        return html.Span(f"Edit category '{index}' (dialog not implemented in demo).", className="admin-toast-msg")
    raise PreventUpdate


@app.callback(
    Output("report-form-visible", "data"),
    Input("report-new-btn", "n_clicks"),
    Input("report-cancel-btn", "n_clicks"),
)
def toggle_report_form(new_clicks, cancel_clicks):
    """Show form when 'New report' is clicked, hide when 'Cancel' is clicked."""
    if not callback_context.triggered:
        raise PreventUpdate
    trigger_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    if trigger_id == "report-new-btn":
        return True
    if trigger_id == "report-cancel-btn":
        return False
    raise PreventUpdate


@app.callback(
    Output("report-form-block", "style"),
    Input("report-form-visible", "data"),
)
def show_hide_report_form(visible):
    """Hide form block by default; show when report-form-visible is True."""
    if visible:
        return {}
    return {"display": "none"}


@app.callback(
    Output("report-list-container", "children"),
    Input("url", "pathname"),
    Input("report-submit", "n_clicks"),
)
def update_report_list(pathname, n_clicks):
    """Build the list of generated reports from dummy data + HAZARDS (newest first)."""
    if pathname != "/report":
        raise PreventUpdate
    # Show dummy reports first for a professional prototype, then user-submitted (newest first)
    all_reports = list(SAMPLE_REPORTS) + list(HAZARDS)
    if not all_reports:
        return html.P("No reports yet. Use the form below to submit your first report.", className="report-list-empty")
    items = []
    for h in reversed(all_reports):  # newest first
        items.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(h.get("id", ""), className="report-list-id"),
                            html.Span(h.get("status", ""), className="report-list-status"),
                        ],
                        className="report-list-row-header",
                    ),
                    html.Div(h.get("title") or "—", className="report-list-title"),
                    html.Div(
                        f"{h.get('category', '') or '—'} · {h.get('area', '') or '—'}",
                        className="report-list-meta",
                    ),
                ],
                className="report-list-item",
            ),
        )
    return html.Div(items, className="report-list")


@app.callback(
    Output("hazards-list-container", "children"),
    Input("url", "pathname"),
    Input("hazards-filter-status", "value"),
    Input("hazards-filter-category", "value"),
    Input("hazards-search", "value"),
)
def update_hazards_list(pathname, filter_status, filter_category, search_text):
    """Build the hazards table and footer from hardcoded sample data + HAZARDS, applying filters and search."""
    if pathname != "/hazards":
        raise PreventUpdate
    # Use hardcoded sample data first so the page always looks like the reference
    hazards = list(SAMPLE_HAZARDS) + list(HAZARDS)
    if filter_status:
        hazards = [h for h in hazards if h.get("status") == filter_status]
    if filter_category:
        hazards = [h for h in hazards if h.get("category") == filter_category]
    if search_text and search_text.strip():
        q = search_text.strip().lower()
        hazards = [
            h for h in hazards
            if q in (h.get("id") or "").lower()
            or q in (h.get("title") or "").lower()
            or q in (h.get("area") or "").lower()
            or q in (h.get("station") or "").lower()
            or q in (h.get("category") or "").lower()
        ]
    n = len(hazards)
    # Empty state
    if n == 0:
        return html.Div(
            [
                html.Table(
                    [html.Thead(html.Tr([html.Th(c) for c in ["NAME", "CATEGORY", "LOCATION", "RISK", "STATUS", "ACTIONS"]])), html.Tbody([])],
                    className="hazards-table",
                ),
                html.Div(
                    [
                        html.Span("No hazards match your filters. Try adjusting filters or submit a new report.", className="hazards-footer-left"),
                        html.Span("No data", className="hazards-footer-right"),
                    ],
                    className="hazards-footer",
                ),
            ],
            className="hazards-table-block",
        )
    # Table header
    thead = html.Thead(
        html.Tr(
            [
                html.Th("NAME", className="hazards-th-name"),
                html.Th("CATEGORY"),
                html.Th("LOCATION"),
                html.Th("RISK"),
                html.Th("STATUS"),
                html.Th("ACTIONS"),
            ]
        )
    )
    rows = []
    for i, h in enumerate(reversed(hazards)):
        risk = h.get("perceived_risk") or "—"
        risk_class = "hazards-risk-low" if risk in ("Low", "Moderate") else "hazards-risk-high" if risk in ("High", "Critical") else ""
        row_class = "hazards-tr-even" if i % 2 == 0 else "hazards-tr-odd"
        location = h.get("area") or h.get("station") or "—"
        actions = html.Td(
            html.Div(
                [
                    html.Span("👁", className="hazards-action hazards-action-view", title="View"),
                    html.Span("✏️", className="hazards-action hazards-action-edit", title="Edit"),
                    html.Span("🗑", className="hazards-action hazards-action-delete", title="Delete"),
                ],
                className="hazards-actions-cell",
            ),
            className="hazards-td-actions",
        )
        rows.append(
            html.Tr(
                [
                    html.Td(h.get("title") or "—", className="hazards-td-name"),
                    html.Td(h.get("category") or "—"),
                    html.Td(location),
                    html.Td(html.Span(risk, className=f"hazards-risk-pill {risk_class}".strip())),
                    html.Td(h.get("status", "—")),
                    actions,
                ],
                className=row_class,
            )
        )
    tbody = html.Tbody(rows)
    table = html.Table([thead, tbody], className="hazards-table")
    footer = html.Div(
        [
            html.Span(f"Showing 1 to {n} of {n} results.", className="hazards-footer-left"),
            html.Span("All data displayed.", className="hazards-footer-right"),
        ],
        className="hazards-footer",
    )
    return html.Div([table, footer], className="hazards-table-block")


@app.callback(
    Output("capa-list-container", "children"),
    Input("url", "pathname"),
    Input("capa-filter-type", "value"),
    Input("capa-filter-priority", "value"),
    Input("capa-search", "value"),
)
def update_capa_list(pathname, filter_type, filter_priority, search_text):
    """Build the CAPA table and footer from SAMPLE_CAPA, applying filters and search."""
    if pathname != "/capa":
        raise PreventUpdate
    capas = list(SAMPLE_CAPA)
    if filter_type:
        capas = [c for c in capas if c.get("type") == filter_type]
    if filter_priority:
        capas = [c for c in capas if c.get("priority") == filter_priority]
    if search_text and search_text.strip():
        q = search_text.strip().lower()
        capas = [
            c for c in capas
            if q in (c.get("action") or "").lower()
            or q in (c.get("id") or "").lower()
            or q in (c.get("hazard_id") or "").lower()
        ]
    n = len(capas)
    if n == 0:
        return html.Div(
            [
                html.Table(
                    [
                        html.Thead(html.Tr([html.Th(x) for x in ["ACTION", "TYPE", "PRIORITY", "HAZARD", "DUE DATE", "STATUS", "ACTIONS"]])),
                        html.Tbody([]),
                    ],
                    className="hazards-table",
                ),
                html.Div(
                    [
                        html.Span("No actions match your filters.", className="hazards-footer-left"),
                        html.Span("No data", className="hazards-footer-right"),
                    ],
                    className="hazards-footer",
                ),
            ],
            className="hazards-table-block",
        )
    thead = html.Thead(
        html.Tr(
            [
                html.Th("ACTION", className="hazards-th-name"),
                html.Th("TYPE"),
                html.Th("PRIORITY"),
                html.Th("HAZARD"),
                html.Th("DUE DATE"),
                html.Th("STATUS"),
                html.Th("ACTIONS"),
            ]
        )
    )
    rows = []
    for i, c in enumerate(capas):
        row_class = "hazards-tr-even" if i % 2 == 0 else "hazards-tr-odd"
        priority = c.get("priority") or "—"
        p_class = "hazards-risk-low" if priority in ("Low", "Medium") else "hazards-risk-high" if priority in ("High", "Critical") else ""
        actions_cell = html.Td(
            html.Div(
                [
                    html.Button(
                        "👁",
                        id={"type": "capa-action-view", "index": c["id"]},
                        className="hazards-action hazards-action-view",
                        title="View",
                        n_clicks=0,
                    ),
                    html.Button(
                        "✏️",
                        id={"type": "capa-action-edit", "index": c["id"]},
                        className="hazards-action hazards-action-edit",
                        title="Edit",
                        n_clicks=0,
                    ),
                    html.Button(
                        "🗑",
                        id={"type": "capa-action-delete", "index": c["id"]},
                        className="hazards-action hazards-action-delete",
                        title="Delete",
                        n_clicks=0,
                    ),
                ],
                className="hazards-actions-cell",
            ),
            className="hazards-td-actions",
        )
        rows.append(
            html.Tr(
                [
                    html.Td(c.get("action") or "—", className="hazards-td-name"),
                    html.Td(c.get("type") or "—"),
                    html.Td(html.Span(priority, className=f"hazards-risk-pill {p_class}".strip())),
                    html.Td(c.get("hazard_id") or "—"),
                    html.Td(c.get("due_date") or "—"),
                    html.Td(c.get("status", "—")),
                    actions_cell,
                ],
                className=row_class,
            )
        )
    tbody = html.Tbody(rows)
    table = html.Table([thead, tbody], className="hazards-table")
    footer = html.Div(
        [
            html.Span(f"Showing 1 to {n} of {n} results.", className="hazards-footer-left"),
            html.Span("All data displayed.", className="hazards-footer-right"),
        ],
        className="hazards-footer",
    )
    return html.Div([table, footer], className="hazards-table-block")


@app.callback(
    Output("capa-action-toast", "children"),
    Input({"type": "capa-action-view", "index": ALL}, "n_clicks"),
    Input({"type": "capa-action-edit", "index": ALL}, "n_clicks"),
    Input({"type": "capa-action-delete", "index": ALL}, "n_clicks"),
)
def capa_action_click(*_):
    """Show feedback when a CAPA table action (view/edit/delete) is clicked."""
    if not callback_context.triggered:
        raise PreventUpdate
    prop = callback_context.triggered[0]["prop_id"]
    if ".n_clicks" not in prop:
        raise PreventUpdate
    try:
        id_str = prop.split(".n_clicks")[0].strip()
        id_dict = json.loads(id_str)
        action_type = id_dict.get("type", "")
        index = id_dict.get("index", "")
    except (json.JSONDecodeError, IndexError):
        raise PreventUpdate
    if "capa-action-view" in action_type:
        return html.Span(f"Viewing {index}", className="capa-toast-msg")
    if "capa-action-edit" in action_type:
        return html.Span(f"Edit {index} (form not implemented)", className="capa-toast-msg")
    if "capa-action-delete" in action_type:
        return html.Span(f"Delete {index} (confirm not implemented)", className="capa-toast-msg")
    raise PreventUpdate


@app.callback(
    Output("investigation-action-toast", "children"),
    Input({"type": "inv-action-view", "index": ALL}, "n_clicks"),
    Input({"type": "inv-action-edit", "index": ALL}, "n_clicks"),
    Input({"type": "inv-action-delete", "index": ALL}, "n_clicks"),
)
def inv_action_click(*_):
    """Show feedback when an Investigation table action (view/edit/delete) is clicked."""
    if not callback_context.triggered:
        raise PreventUpdate
    prop = callback_context.triggered[0]["prop_id"]
    if ".n_clicks" not in prop:
        raise PreventUpdate
    try:
        id_str = prop.split(".n_clicks")[0].strip()
        id_dict = json.loads(id_str)
        action_type = id_dict.get("type", "")
        index = id_dict.get("index", "")
    except (json.JSONDecodeError, IndexError):
        raise PreventUpdate
    if "inv-action-view" in action_type:
        return html.Span(f"Viewing investigation {index}", className="capa-toast-msg")
    if "inv-action-edit" in action_type:
        return html.Span(f"Edit {index} (form not implemented)", className="capa-toast-msg")
    if "inv-action-delete" in action_type:
        return html.Span(f"Delete {index} (confirm not implemented)", className="capa-toast-msg")
    raise PreventUpdate


@app.callback(
    Output("export-toast", "children"),
    Input("export-hazards-csv", "n_clicks"),
    Input("export-hazards-excel", "n_clicks"),
    Input("export-hazards-pdf", "n_clicks"),
    Input("export-capa-csv", "n_clicks"),
    Input("export-capa-excel", "n_clicks"),
    Input("export-inv-pdf", "n_clicks"),
    Input("export-inv-csv", "n_clicks"),
    Input("export-audit-csv", "n_clicks"),
)
def export_button_click(h_csv, h_excel, h_pdf, c_csv, c_excel, i_pdf, i_csv, audit_csv):
    """Show feedback when an export button is clicked (demo – no file generated)."""
    if not callback_context.triggered:
        raise PreventUpdate
    trigger_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    labels = {
        "export-hazards-csv": "Hazards & reports → CSV",
        "export-hazards-excel": "Hazards & reports → Excel",
        "export-hazards-pdf": "Hazards & reports → PDF",
        "export-capa-csv": "CAPA actions → CSV",
        "export-capa-excel": "CAPA actions → Excel",
        "export-inv-pdf": "Investigations → PDF",
        "export-inv-csv": "Investigations → CSV",
        "export-audit-csv": "Audit trail → CSV",
    }
    label = labels.get(trigger_id, "Export")
    return html.Span(f"Export requested: {label} (demo – file not generated)", className="export-toast-msg")


@app.callback(
    Output("investigation-list-container", "children"),
    Input("url", "pathname"),
    Input("investigation-filter-status", "value"),
    Input("investigation-search", "value"),
)
def update_investigation_list(pathname, filter_status, search_text):
    """Build the investigation table and footer from SAMPLE_INVESTIGATIONS."""
    if pathname != "/investigation":
        raise PreventUpdate
    invs = list(SAMPLE_INVESTIGATIONS)
    if filter_status:
        invs = [i for i in invs if i.get("status") == filter_status]
    if search_text and search_text.strip():
        q = search_text.strip().lower()
        invs = [
            i for i in invs
            if q in (i.get("title") or "").lower()
            or q in (i.get("id") or "").lower()
            or q in (i.get("hazard_id") or "").lower()
            or q in (i.get("lead") or "").lower()
        ]
    n = len(invs)
    if n == 0:
        return html.Div(
            [
                html.Table(
                    [
                        html.Thead(html.Tr([html.Th(x) for x in ["INVESTIGATION", "HAZARD", "STATUS", "LEAD", "STARTED", "ACTIONS"]])),
                        html.Tbody([]),
                    ],
                    className="hazards-table",
                ),
                html.Div(
                    [
                        html.Span("No investigations match your filters.", className="hazards-footer-left"),
                        html.Span("No data", className="hazards-footer-right"),
                    ],
                    className="hazards-footer",
                ),
            ],
            className="hazards-table-block",
        )
    thead = html.Thead(
        html.Tr(
            [
                html.Th("INVESTIGATION", className="hazards-th-name"),
                html.Th("HAZARD"),
                html.Th("STATUS"),
                html.Th("LEAD"),
                html.Th("STARTED"),
                html.Th("ACTIONS"),
            ]
        )
    )
    rows = []
    for i, inv in enumerate(invs):
        row_class = "hazards-tr-even" if i % 2 == 0 else "hazards-tr-odd"
        actions_cell = html.Td(
            html.Div(
                [
                    html.Button(
                        "👁",
                        id={"type": "inv-action-view", "index": inv["id"]},
                        className="hazards-action hazards-action-view",
                        title="View",
                        n_clicks=0,
                    ),
                    html.Button(
                        "✏️",
                        id={"type": "inv-action-edit", "index": inv["id"]},
                        className="hazards-action hazards-action-edit",
                        title="Edit",
                        n_clicks=0,
                    ),
                    html.Button(
                        "🗑",
                        id={"type": "inv-action-delete", "index": inv["id"]},
                        className="hazards-action hazards-action-delete",
                        title="Delete",
                        n_clicks=0,
                    ),
                ],
                className="hazards-actions-cell",
            ),
            className="hazards-td-actions",
        )
        rows.append(
            html.Tr(
                [
                    html.Td(inv.get("title") or "—", className="hazards-td-name"),
                    html.Td(inv.get("hazard_id") or "—"),
                    html.Td(inv.get("status", "—")),
                    html.Td(inv.get("lead") or "—"),
                    html.Td(inv.get("started") or "—"),
                    actions_cell,
                ],
                className=row_class,
            )
        )
    tbody = html.Tbody(rows)
    table = html.Table([thead, tbody], className="hazards-table")
    footer = html.Div(
        [
            html.Span(f"Showing 1 to {n} of {n} results.", className="hazards-footer-left"),
            html.Span("All data displayed.", className="hazards-footer-right"),
        ],
        className="hazards-footer",
    )
    return html.Div([table, footer], className="hazards-table-block")


app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            var el = document.getElementById("report-form-card");
            if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("report-scroll-sentinel", "data"),
    Input("report-new-btn", "n_clicks"),
)


@app.callback(
    Output("report-status", "children"),
    Input("report-submit", "n_clicks"),
    State("report-title", "value"),
    State("report-station", "value"),
    State("report-area", "value"),
    State("report-category", "value"),
    State("report-subcategory", "value"),
    State("report-description", "value"),
    State("report-people", "value"),
    State("report-severity-reporter", "value"),
    State("report-classification", "value"),
    State("report-tags", "value"),
    State("report-mode", "value"),
    State("reporter-name", "value"),
    State("reporter-dept", "value"),
    State("reporter-role", "value"),
)
def handle_report_submit(
    n_clicks,
    title,
    station,
    area,
    category,
    subcategory,
    description,
    people,
    perceived_risk,
    classification,
    tags,
    mode,
    reporter_name,
    reporter_dept,
    reporter_role,
):
    if not n_clicks:
        raise PreventUpdate

    # Basic validation
    missing = []
    if not title:
        missing.append("Short title")
    if not category:
        missing.append("Category")
    if not description:
        missing.append("Description")
    if not area:
        missing.append("Area")

    if missing:
        return html.Div(
            f"Please complete the required fields: {', '.join(missing)}.",
            style={"color": "#b91c1c", "fontWeight": 500},
        )

    hazard = {
        "id": _next_hazard_id(),
        "title": title,
        "station": station or "",
        "area": area or "",
        "category": category or "",
        "subcategory": subcategory or "",
        "description": description or "",
        "people_exposed": people or "",
        "perceived_risk": perceived_risk or "",
        "classification": classification or "",
        "tags": tags or [],
        "reporting_mode": mode or "Named",
        "reporter_name": reporter_name or "",
        "reporter_dept": reporter_dept or "",
        "reporter_role": reporter_role or "",
        "status": "Submitted",
    }
    HAZARDS.append(hazard)

    return html.Div(
        f"Report {hazard['id']} submitted. You can see it under Hazards (sidebar).",
        style={"color": "#166534", "fontWeight": 500},
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)


