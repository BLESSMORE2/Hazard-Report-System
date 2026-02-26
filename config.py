"""
HIRS configuration: taxonomy (categories + subcategories), risk matrix, workflow, roles.
Aligned with requirements doc – configurable by Admin in production.
"""

# ---------------------------------------------------------------------------
# Workflow statuses (Section 6.1)
# ---------------------------------------------------------------------------
WORKFLOW_STATUSES = [
    "Draft",
    "Submitted",
    "Triage",
    "Assigned actions",
    "In progress",
    "Awaiting verification",
    "Closed",
    "Rejected",
]

# ---------------------------------------------------------------------------
# Classification (Module A)
# ---------------------------------------------------------------------------
CLASSIFICATION_TYPES = [
    "Hazard",
    "Near miss",
    "Incident",
    "Unsafe act",
    "Unsafe condition",
]

TAGS_OPTIONS = ["Safety", "Security", "Environment", "Quality"]

# ---------------------------------------------------------------------------
# Hazard taxonomy – categories and subcategories (Section 5)
# Admin-configurable in production; here as dropdown configuration.
# ---------------------------------------------------------------------------
HAZARD_AREAS = [
    "Airside / Ramp",
    "Aircraft servicing",
    "Cargo, baggage & loading",
    "Ground Support Equipment (GSE)",
    "Security & Environment",
    "Other",
]

SUBCATEGORIES = {
    "Airside / Ramp": [
        "FOD (foreign object debris) and housekeeping",
        "Vehicle-pedestrian conflict, speeding, blind spots",
        "Aircraft stand safety: wingtip clearance, cone placement, stand markings",
        "Jet blast/prop wash exposure",
        "Lighting/marking deficiencies; congestion",
        "Slips/trips/falls (hoses, cables, wet surfaces)",
    ],
    "Aircraft servicing": [
        "Refueling/fueling safety (bonding/earthing, ignition sources, spill control)",
        "Docking/marshalling/guidance communication",
        "Towing/pushback (tug condition, bypass pin, headset/radio comms, clearance)",
        "Ground power (GPU) and pre-conditioned air (PCA) connections",
        "Utility pits, cables and hoses",
        "Lavatory service hazards; catering truck positioning",
        "Passenger boarding bridge / stairs positioning",
    ],
    "Cargo, baggage & loading": [
        "Cargo loading/unloading (ULD handling, restraint, pinch points)",
        "Manual handling ergonomics and lifting injuries",
        "Belt loader / container loader interface hazards",
        "Dangerous goods awareness flags",
    ],
    "Ground Support Equipment (GSE)": [
        "Equipment defects or maintenance issues",
        "Incorrect equipment selection for aircraft type",
        "Brake failure/rolling equipment",
        "Battery charging hazards",
    ],
    "Security & Environment": [
        "Airside access breach / suspicious item",
        "Spills (fuel/oil), waste handling, environmental release",
        "Wildlife hazards (if applicable)",
    ],
    "Other": ["Other"],
}

# ---------------------------------------------------------------------------
# Risk matrix (Section 4.2) – Likelihood 1–5 × Severity 1–5
# ---------------------------------------------------------------------------
LIKELIHOOD_LABELS = {1: "1 – Rare", 2: "2 – Unlikely", 3: "3 – Possible", 4: "4 – Likely", 5: "5 – Almost certain"}
SEVERITY_LABELS = {1: "1 – Negligible", 2: "2 – Minor", 3: "3 – Moderate", 4: "4 – Major", 5: "5 – Catastrophic"}

# Risk score = L × S (1–25). Level by score:
# Low 1–6, Medium 7–12, High 13–20, Extreme 21–25
def risk_matrix_level(likelihood: int, severity: int) -> tuple:
    """Returns (score, level_name). level_name in ('Low','Medium','High','Extreme')."""
    if not (1 <= likelihood <= 5 and 1 <= severity <= 5):
        return 0, "Not assessed"
    score = likelihood * severity
    if score <= 6:
        return score, "Low"
    if score <= 12:
        return score, "Medium"
    if score <= 20:
        return score, "High"
    return score, "Extreme"

RISK_LEVELS_DISPLAY = ["Low", "Medium", "High", "Extreme"]

ESCALATION_RULES = {
    "Extreme": "Immediate stop/contain checklist; notify Safety and Operations Manager immediately; investigation mandatory.",
    "High": "Same-shift review required; actions assigned with short due dates; Safety notified.",
    "Medium": "Action plan required; due date set; periodic review.",
    "Low": "Record and monitor; housekeeping/awareness actions as needed.",
}

# ---------------------------------------------------------------------------
# CAPA action types (Section 4.3)
# ---------------------------------------------------------------------------
CAPA_ACTION_TYPES = ["Immediate", "Corrective", "Preventive"]
CAPA_PRIORITIES = ["Low", "Medium", "High", "Critical"]

# ---------------------------------------------------------------------------
# Roles and permissions (Section 3)
# ---------------------------------------------------------------------------
ROLES = [
    "Reporter (staff/contractor)",
    "Supervisor / Team Lead",
    "Safety (SMS/QHSE)",
    "Operations Manager",
    "Administrator",
    "Auditor (read-only)",
]

ROLE_PERMISSIONS = {
    "Reporter (staff/contractor)": "Create reports; upload evidence; view own reports; receive feedback; add follow-up info (non-destructive).",
    "Supervisor / Team Lead": "Review and assign actions; set due dates; verify local fixes; view area dashboards.",
    "Safety (SMS/QHSE)": "Triage; validate risk ratings; initiate investigations; verify effectiveness; publish lessons learned.",
    "Operations Manager": "Escalation approvals; resource decisions; monitor performance KPIs; view all dashboards.",
    "Administrator": "Manage users/roles; configure stations/areas/categories; manage risk matrix; system settings.",
    "Auditor (read-only)": "Read-only access to reports, actions, audit trail, and exports.",
}

# ---------------------------------------------------------------------------
# Reference reading (Section 9)
# ---------------------------------------------------------------------------
REFERENCE_LINKS = [
    ("Aviation Learnings - Ground Handling Operations", "https://aviationlearnings.com/category/airport-management/ground-handling-operations/"),
    ("Aviation Learnings - Airport Ramp Safety", "https://aviationlearnings.com/category/aviation-safety/airport-ramp-safety/"),
    ("Aviation Learnings - Ramp Error Decision Aid (REDA)", "https://aviationlearnings.com/ramp-error-decision-aid-reda/"),
    ("Aviation Learnings - HIRS at Airports", "https://aviationlearnings.com/hazard-identification-reporting-system-at-airports-enhancing-safety-in-aircraft-ground-handling-ramp-operations/"),
    ("Aviation Learnings - Ramp Hazards & Safety Precautions", "https://aviationlearnings.com/ramp-hazards-at-an-airport-ramp-safety-precautions-for-ground-handling-agents-ramp-workers/"),
    ("Aviation Learnings - Air Cargo Handling Safety", "https://aviationlearnings.com/safety-precautions-in-air-cargo-handling-on-the-ramp-safety-in-procedures-of-aircraft-cargo-loading-unloading/"),
    ("Aviation Learnings - Aircraft Refueling Safety", "https://aviationlearnings.com/aircraft-refueling-safety-procedures-precautions-safety-in-aircraft-fueling-on-ground/"),
    ("Aviation Learnings - Ramp Safety in Aircraft Docking", "https://aviationlearnings.com/ramp-safety-in-aircraft-docking/"),
    ("Aviation Learnings - Importance of FOD in Ramp Safety", "https://aviationlearnings.com/importance-of-foreign-object-debris-fod-in-ramp-safety/"),
    ("Flight Safety Foundation - Ground Accident Prevention (GAP)", "https://flightsafety.org/toolkits-resources/past-safety-initiatives/ground-accident-prevention-gap/ground-accident-prevention-ramp-operational-safety-procedures/"),
    ("EASA - Ground handling safety", "https://www.easa.europa.eu/en/light/topics/ground-handling-forgotten-piece-aviation-safety-puzzle"),
]
