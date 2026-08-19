import streamlit as st
import pandas as pd
import datetime
import re
import io
import os
import sqlite3
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# Optional ReportLab support for PDF generation
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="Lehri Masala Cold Storage Register",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# APPLE THEME PALETTES & DYNAMIC CSS (SAFE RETRIEVAL)
# ---------------------------------------------------------
THEMES = {
    "Cupertino Blue (Apple Classic)": {
        "accent": "#0071E3",
        "accent_hover": "#0077ED",
        "accent_border": "rgba(0, 113, 227, 0.35)",
        "gradient1": "rgba(0, 113, 227, 0.08)",
        "gradient2": "rgba(50, 215, 75, 0.06)",
        "badge_border": "#0071E3",
    },
    "Space Gray & Saffron (Brand)": {
        "accent": "#FF3B30",
        "accent_hover": "#FF453A",
        "accent_border": "rgba(255, 59, 48, 0.35)",
        "gradient1": "rgba(255, 149, 0, 0.09)",
        "gradient2": "rgba(255, 59, 48, 0.06)",
        "badge_border": "#FF9500",
    },
    "Pro Emerald": {
        "accent": "#34C759",
        "accent_hover": "#30D158",
        "accent_border": "rgba(52, 199, 89, 0.35)",
        "gradient1": "rgba(52, 199, 89, 0.09)",
        "gradient2": "rgba(48, 209, 88, 0.06)",
        "badge_border": "#34C759",
    },
    "Vision Midnight (Dark OLED)": {
        "accent": "#64D2FF",
        "accent_hover": "#70D7FF",
        "accent_border": "rgba(100, 210, 255, 0.40)",
        "gradient1": "rgba(100, 210, 255, 0.09)",
        "gradient2": "rgba(191, 90, 242, 0.07)",
        "badge_border": "#64D2FF",
    }
}

DEFAULT_THEME = "Cupertino Blue (Apple Classic)"

if "app_theme" not in st.session_state or st.session_state.app_theme not in THEMES:
    st.session_state.app_theme = DEFAULT_THEME

active_palette = THEMES.get(st.session_state.app_theme, THEMES[DEFAULT_THEME])

st.markdown(f"""
    <style>
    @import url('https://fonts.cdnfonts.com/css/sf-pro-display');

    html, body, [class*="css"], .stApp {{
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif !important;
        letter-spacing: -0.015em;
        -webkit-font-smoothing: antialiased;
    }}

    .stApp {{
        background-color: var(--background-color);
        background-image: 
            radial-gradient(at 15% 10%, {active_palette['gradient1']} 0px, transparent 50%),
            radial-gradient(at 85% 15%, {active_palette['gradient2']} 0px, transparent 50%),
            radial-gradient(at 50% 95%, rgba(120, 120, 128, 0.04) 0px, transparent 50%);
        background-attachment: fixed;
    }}
    
    header[data-testid="stHeader"] {{
        background: transparent !important;
        height: 2.5rem !important;
    }}
    
    .block-container {{
        padding-top: 5.2rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1240px;
    }}
    
    .main-header {{
        font-size: 2.1rem;
        font-weight: 700;
        color: var(--text-color);
        letter-spacing: -0.035em;
        margin: 0;
        line-height: 1.15;
    }}
    .sub-header {{
        font-size: 0.95rem;
        color: var(--text-color);
        opacity: 0.65;
        font-weight: 400;
        margin: 0;
        margin-top: 4px;
        letter-spacing: -0.01em;
    }}
    
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: var(--secondary-background-color) !important;
        border: 1px solid rgba(120, 120, 128, 0.18) !important;
        border-radius: 20px !important;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.04), 0 0 0 1px rgba(255, 255, 255, 0.05) inset !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        padding: 6px !important;
    }}

    .kpi-card {{
        background: var(--secondary-background-color);
        border: 1px solid rgba(120, 120, 128, 0.16);
        border-radius: 20px;
        padding: 20px 22px;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.03), 0 1px 0 rgba(255, 255, 255, 0.1) inset;
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.22s ease;
        height: 100%;
    }}
    .kpi-card:hover {{
        transform: scale(1.018);
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.08), 0 1px 0 rgba(255, 255, 255, 0.15) inset;
    }}
    .kpi-title {{
        font-size: 11.5px;
        font-weight: 600;
        text-transform: uppercase;
        color: var(--text-color);
        opacity: 0.60;
        letter-spacing: 0.06em;
    }}
    .kpi-value {{
        font-size: 29px;
        font-weight: 700;
        color: var(--text-color);
        margin-top: 6px;
        letter-spacing: -0.03em;
    }}
    .kpi-sub {{
        font-size: 12.5px;
        color: {active_palette['accent']};
        font-weight: 600;
        margin-top: 4px;
        letter-spacing: -0.01em;
    }}

    .live-calc-box {{
        background: {active_palette['gradient1']};
        border: 1px solid {active_palette['accent_border']};
        border-radius: 16px;
        padding: 14px 18px;
        text-align: center;
        margin-top: 4px;
        backdrop-filter: blur(15px);
    }}
    .live-calc-label {{
        font-size: 11.5px;
        color: var(--text-color);
        opacity: 0.70;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .live-calc-val {{
        font-size: 26px;
        font-weight: 700;
        color: {active_palette['accent']};
        margin-top: 2px;
        letter-spacing: -0.025em;
    }}
    
    .item-subcard {{
        background: var(--background-color);
        border: 1px solid rgba(120, 120, 128, 0.14);
        border-left: 4px solid {active_palette['accent']};
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 8px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
    }}
    .item-subcard-title {{
        font-weight: 600;
        font-size: 15px;
        color: var(--text-color);
        letter-spacing: -0.015em;
    }}
    .item-subcard-body {{
        font-size: 13px;
        color: var(--text-color);
        opacity: 0.82;
        margin-top: 3px;
    }}

    .lot-subcard {{
        background: var(--background-color);
        border: 1px solid rgba(120, 120, 128, 0.14);
        border-left: 4px solid {active_palette['badge_border']};
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 8px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
    }}
    .lot-subcard-title {{
        font-weight: 600;
        font-size: 15px;
        color: var(--text-color);
        letter-spacing: -0.015em;
    }}
    .lot-subcard-body {{
        font-size: 13px;
        color: var(--text-color);
        opacity: 0.82;
        margin-top: 3px;
    }}

    /* Minimal Finder Location Row */
    .finder-loc-card {{
        background: var(--background-color);
        border: 1px solid rgba(120, 120, 128, 0.16);
        border-radius: 12px;
        padding: 10px 16px;
        margin-top: 6px;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .finder-loc-name {{
        font-weight: 600;
        font-size: 14.5px;
        color: var(--text-color);
    }}
    .finder-loc-val {{
        font-weight: 700;
        font-size: 15px;
        color: {active_palette['accent']};
    }}

    div[data-testid="stRadio"] > div[role="radiogroup"] {{
        background-color: var(--secondary-background-color);
        padding: 5px;
        border-radius: 16px;
        border: 1px solid rgba(120, 120, 128, 0.18);
        gap: 5px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.03);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {{
        background-color: transparent;
        padding: 8px 18px;
        border-radius: 12px;
        font-weight: 500;
        font-size: 13.5px;
        transition: all 0.2s cubic-bezier(0.25, 1, 0.5, 1);
        border: 1px solid transparent;
    }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {{
        background-color: rgba(120, 120, 128, 0.08);
    }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] {{
        background-color: var(--background-color);
        border: 1px solid rgba(120, 120, 128, 0.22);
        box-shadow: 0 3px 10px rgba(0,0,0,0.06);
        font-weight: 600;
    }}

    .stButton > button {{
        border-radius: 12px !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
        transition: all 0.18s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    }}
    .stButton > button:hover {{
        transform: scale(1.015) !important;
    }}
    .stButton > button:active {{
        transform: scale(0.98) !important;
    }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SESSION STATE NAVIGATION & CALLBACKS
# ---------------------------------------------------------
nav_options = [
    "📊 Operational Dashboard",
    "1. Outward Register",
    "2. Inward Register",
    "3. Stock Summary",
    "4. Custom Reports"
]

if "nav_selection" not in st.session_state:
    st.session_state.nav_selection = "📊 Operational Dashboard"
if "prefill_cs" not in st.session_state:
    st.session_state.prefill_cs = ""
if "prefill_item" not in st.session_state:
    st.session_state.prefill_item = ""
if "prefill_lot" not in st.session_state:
    st.session_state.prefill_lot = ""

def navigate_to(page_name, cs="", item="", lot=""):
    st.session_state.nav_selection = page_name
    st.session_state.prefill_cs = cs
    st.session_state.prefill_item = item
    st.session_state.prefill_lot = lot

# ---------------------------------------------------------
# GOOGLE DRIVE / SHEETS ENGINE (WITH SMART CACHING)
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

OUTWARD_COLS = ["id", "entry_date", "reference_no", "receipt_no", "cold_storage", "item_name", "qty", "unit_size", "total_qty"]
INWARD_COLS = ["id", "entry_date", "receipt_no", "item_name", "qty"]

@st.cache_data(ttl=120)
def get_outward_df():
    try:
        df = conn.read(worksheet="outward", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=OUTWARD_COLS)
        df = df.dropna(how="all")
        for col in OUTWARD_COLS:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception:
        return pd.DataFrame(columns=OUTWARD_COLS)

@st.cache_data(ttl=120)
def get_inward_df():
    try:
        df = conn.read(worksheet="inward", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=INWARD_COLS)
        df = df.dropna(how="all")
        for col in INWARD_COLS:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception:
        return pd.DataFrame(columns=INWARD_COLS)

def compute_stock_summary_df(out_df, in_df):
    if out_df.empty:
        return pd.DataFrame(columns=[
            "Lot No.", "Outward Date", "Cold Storage", "Item Name", "Unit Qty (KG)",
            "Outward Units", "Inward Units", "Bal. Units", "Bal. Total Qty (KG)", "Status"
        ])
    
    out_df = out_df.copy()
    out_df["qty"] = pd.to_numeric(out_df["qty"], errors="coerce").fillna(0)
    out_df["unit_size"] = pd.to_numeric(out_df["unit_size"], errors="coerce").fillna(0)
    out_df["total_qty"] = pd.to_numeric(out_df["total_qty"], errors="coerce").fillna(0)

    if not in_df.empty:
        in_df = in_df.copy()
        in_df["qty"] = pd.to_numeric(in_df["qty"], errors="coerce").fillna(0)
        in_grouped = in_df.groupby(["receipt_no", "item_name"])["qty"].sum().reset_index()
        in_grouped.rename(columns={"qty": "Inward Units"}, inplace=True)
        df_sum = pd.merge(out_df, in_grouped, on=["receipt_no", "item_name"], how="left")
    else:
        df_sum = out_df.copy()
        df_sum["Inward Units"] = 0

    df_sum["Inward Units"] = df_sum["Inward Units"].fillna(0)
    df_sum["Bal. Units"] = df_sum["qty"] - df_sum["Inward Units"]
    df_sum["Bal. Total Qty (KG)"] = df_sum["Bal. Units"] * df_sum["unit_size"]
    
    df_sum["Status"] = df_sum.apply(
        lambda r: "CLEARED" if r["Bal. Units"] <= 0 else ("PARTIAL" if r["Inward Units"] > 0 else "UNTOUCHED"),
        axis=1
    )
    
    return df_sum.rename(columns={
        "receipt_no": "Lot No.",
        "entry_date": "Outward Date",
        "cold_storage": "Cold Storage",
        "item_name": "Item Name",
        "unit_size": "Unit Qty (KG)",
        "qty": "Outward Units"
    })[["Lot No.", "Outward Date", "Cold Storage", "Item Name", "Unit Qty (KG)", "Outward Units", "Inward Units", "Bal. Units", "Bal. Total Qty (KG)", "Status"]]

def sync_sheet_stock_summary(df_s):
    try:
        conn.update(worksheet="stock_summary", data=df_s)
    except Exception:
        pass

def save_outward_entry(record):
    df = get_outward_df()
    next_id = int(df["id"].max()) + 1 if not df.empty and str(df["id"].max()).isdigit() else 1
    record["id"] = next_id
    new_df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    conn.update(worksheet="outward", data=new_df)
    get_outward_df.clear()
    df_i = get_inward_df()
    df_s = compute_stock_summary_df(new_df, df_i)
    sync_sheet_stock_summary(df_s)

def update_outward_entry(entry_id, updated_record):
    df = get_outward_df()
    idx = df[df["id"].astype(str) == str(entry_id)].index
    if not idx.empty:
        for k, v in updated_record.items():
            df.loc[idx[0], k] = v
        conn.update(worksheet="outward", data=df)
        get_outward_df.clear()
        df_i = get_inward_df()
        df_s = compute_stock_summary_df(df, df_i)
        sync_sheet_stock_summary(df_s)

def delete_outward_entry(entry_id):
    df = get_outward_df()
    df = df[df["id"].astype(str) != str(entry_id)]
    conn.update(worksheet="outward", data=df)
    get_outward_df.clear()
    df_i = get_inward_df()
    df_s = compute_stock_summary_df(df, df_i)
    sync_sheet_stock_summary(df_s)

def save_inward_entry(record):
    df = get_inward_df()
    next_id = int(df["id"].max()) + 1 if not df.empty and str(df["id"].max()).isdigit() else 1
    record["id"] = next_id
    new_df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    conn.update(worksheet="inward", data=new_df)
    get_inward_df.clear()
    df_o = get_outward_df()
    df_s = compute_stock_summary_df(df_o, new_df)
    sync_sheet_stock_summary(df_s)

def update_inward_entry(entry_id, updated_record):
    df = get_inward_df()
    idx = df[df["id"].astype(str) == str(entry_id)].index
    if not idx.empty:
        for k, v in updated_record.items():
            df.loc[idx[0], k] = v
        conn.update(worksheet="inward", data=df)
        get_outward_df.clear()
        df_o = get_outward_df()
        df_s = compute_stock_summary_df(df_o, df)
        sync_sheet_stock_summary(df_s)

def delete_inward_entry(entry_id):
    df = get_inward_df()
    df = df[df["id"].astype(str) != str(entry_id)]
    conn.update(worksheet="inward", data=df)
    get_inward_df.clear()
    df_o = get_outward_df()
    df_s = compute_stock_summary_df(df_o, df)
    sync_sheet_stock_summary(df_s)

def generate_sqlite_backup(df_o, df_i, df_s):
    db_buffer = io.BytesIO()
    temp_conn = sqlite3.connect(':memory:')
    df_o.to_sql('outward', temp_conn, if_exists='replace', index=False)
    df_i.to_sql('inward', temp_conn, if_exists='replace', index=False)
    df_s.to_sql('stock_summary', temp_conn, if_exists='replace', index=False)
    for line in temp_conn.iterdump():
        db_buffer.write(f'{line}\n'.encode('utf-8'))
    temp_conn.close()
    db_buffer.seek(0)
    return db_buffer

def format_date_str(d_val):
    if isinstance(d_val, (datetime.date, datetime.datetime)):
        return d_val.strftime("%d/%m/%y")
    d_str = str(d_val).strip()
    parts = re.split(r'[-/.]', d_str)
    if len(parts) == 3:
        p1, p2, p3 = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if len(p1) <= 2 and len(p2) <= 2 and p1.isdigit() and p2.isdigit():
            return f"{p1.zfill(2)}/{p2.zfill(2)}/{p3[-2:].zfill(2)}"
        elif len(p1) == 4 and p1.isdigit():
            return f"{p3.zfill(2)}/{p2.zfill(2)}/{p1[-2:]}"
    return d_str

def parse_to_date_obj(d_str):
    clean = format_date_str(d_str)
    try:
        p = clean.split("/")
        if len(p) == 3:
            y = int(p[2]) + 2000 if int(p[2]) < 100 else int(p[2])
            return datetime.date(y, int(p[1]), int(p[0]))
    except Exception:
        pass
    return None

def generate_pdf(df, title):
    if not HAS_REPORTLAB or df.empty:
        return None
    buffer = io.BytesIO()
    page_size = landscape(letter) if len(df.columns) > 5 else letter
    doc = SimpleDocTemplate(buffer, pagesize=page_size, leftMargin=25, rightMargin=25, topMargin=25, bottomMargin=25)
    elements = []
    styles = getSampleStyleSheet()

    if os.path.exists("logo.png"):
        try:
            pdf_logo = Image("logo.png", width=110, height=45)
            pdf_logo.hAlign = 'CENTER'
            elements.append(pdf_logo)
            elements.append(Spacer(1, 8))
        except Exception:
            pass

    elements.append(Paragraph(f"<b>{title}</b>", styles['Title']))
    elements.append(Paragraph(f"Generated on: {datetime.date.today().strftime('%d/%m/%y')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    headers = list(df.columns)
    data = [headers] + df.astype(str).values.tolist()

    avail_width = doc.width
    col_w = avail_width / len(headers) if headers else avail_width
    col_widths = [col_w] * len(headers)

    cell_style = ParagraphStyle('CellText', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, alignment=1)
    header_style = ParagraphStyle('HeaderText', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.whitesmoke, alignment=1)

    formatted_table_data = []
    for row_idx, row in enumerate(data):
        formatted_row = []
        for cell in row:
            st_use = header_style if row_idx == 0 else cell_style
            formatted_row.append(Paragraph(str(cell), st_use))
        formatted_table_data.append(formatted_row)

    t = Table(formatted_table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# HERO HEADER SECTION
# ---------------------------------------------------------
col_h1, col_h2 = st.columns([1, 7], vertical_alignment="center")
with col_h1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=95)
with col_h2:
    st.markdown("<div class='main-header'>Lehri Masala Cold Storage Register</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Apple-Engineered Inventory Tracking & Precision Cold Ledger</div>", unsafe_allow_html=True)

# Fetch Data
df_raw_out = get_outward_df()
df_raw_in = get_inward_df()
df_sum = compute_stock_summary_df(df_raw_out, df_raw_in)

# ---------------------------------------------------------
# SIDEBAR / THEMES, BACKUP & CONTROL
# ---------------------------------------------------------
with st.sidebar:
    st.header("🎨 Appearance & Palette")
    theme_options = list(THEMES.keys())
    current_idx = theme_options.index(st.session_state.app_theme) if st.session_state.app_theme in theme_options else 0
    new_theme = st.selectbox(
        "Design System Palette",
        options=theme_options,
        index=current_idx,
        help="Select an Apple-inspired visual aesthetic"
    )
    if new_theme != st.session_state.app_theme:
        st.session_state.app_theme = new_theme
        st.rerun()

    st.divider()
    st.header("☁️ Cloud Storage")
    st.success("Apple Cloud Sync: Active")
    
    st.divider()
    st.header("💾 Automatic Database Backup")
    
    db_backup_bytes = generate_sqlite_backup(df_raw_out, df_raw_in, df_sum)
    backup_name = f"cold_storage_backup_{datetime.date.today().strftime('%Y%m%d')}.sql"
    
    st.download_button(
        label="📥 Download Full Database (.sql / .db)",
        data=db_backup_bytes,
        file_name=backup_name,
        mime="application/sql",
        use_container_width=True
    )
    
    if st.button("🔄 Force Refresh All Data", use_container_width=True):
        get_outward_df.clear()
        get_inward_df.clear()
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------
# APPLICATION NAVIGATION MENU (MACOS SEGMENTED PILLS)
# ---------------------------------------------------------
selected_tab = st.radio(
    "Navigation Menu",
    options=nav_options,
    key="nav_selection",
    horizontal=True,
    label_visibility="collapsed"
)

st.write("")

# =========================================================
# TAB: OPERATIONAL DASHBOARD
# =========================================================
if selected_tab == "📊 Operational Dashboard":
    today = datetime.date.today()
    def calc_age(d_str):
        dt = parse_to_date_obj(d_str)
        return (today - dt).days if dt else 0

    active_df = df_sum[df_sum["Bal. Units"] > 0].copy() if not df_sum.empty else pd.DataFrame()

    if not active_df.empty:
        active_df["Days in Storage"] = active_df["Outward Date"].apply(calc_age)
        active_df = active_df.sort_values(by="Days in Storage", ascending=False)
        
        total_bal_kg = active_df["Bal. Total Qty (KG)"].sum()
        total_bal_u = active_df["Bal. Units"].sum()
        active_lots_count = len(active_df)

        # 1. TOP METRIC CARDS
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">⚖️ Total Weight</div>
                <div class="kpi-value">{total_bal_kg:,.2f} <span style="font-size:16px; font-weight:600;">KG</span></div>
                <div class="kpi-sub">Active in storage</div>
            </div>
            """, unsafe_allow_html=True)
            st.button("👉 View Summary by Weight", key="btn_kpi_weight", on_click=navigate_to, args=("3. Stock Summary",), use_container_width=True)

        with kpi2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📦 Total Units / Bags</div>
                <div class="kpi-value">{int(total_bal_u):,} <span style="font-size:16px; font-weight:600;">Units</span></div>
                <div class="kpi-sub">Available stock</div>
            </div>
            """, unsafe_allow_html=True)
            st.button("👉 View Summary by Units", key="btn_kpi_units", on_click=navigate_to, args=("3. Stock Summary",), use_container_width=True)

        with kpi3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🏷️ Active Batches</div>
                <div class="kpi-value">{active_lots_count} <span style="font-size:16px; font-weight:600;">Lots</span></div>
                <div class="kpi-sub">Un-cleared storage lots</div>
            </div>
            """, unsafe_allow_html=True)
            st.caption("ℹ️ Expand directory below to retrieve")

        st.write("")

        # 2. ACTIVE BATCHES EXPANDABLE DIRECTORY
        with st.expander(f"🏷️ **Active Batches Directory ({active_lots_count} Lots)** — Click to View & Retrieve"):
            for _, lot_row in active_df.iterrows():
                lot_no = str(lot_row["Lot No."])
                item_name = str(lot_row["Item Name"])
                cs_name = str(lot_row["Cold Storage"])
                bal_u = int(lot_row["Bal. Units"])
                bal_kg = float(lot_row["Bal. Total Qty (KG)"])
                days_held = int(lot_row["Days in Storage"])

                c_lot_info, c_lot_btn = st.columns([3.2, 0.8])
                with c_lot_info:
                    st.markdown(f"""
                    <div class="lot-subcard">
                        <div class="lot-subcard-title">📦 Lot {lot_no} — {item_name}</div>
                        <div class="lot-subcard-body">
                            <b>{bal_u:,} Units</b> ({bal_kg:,.2f} KG) &nbsp;|&nbsp; 
                            <span>Facility: <b>{cs_name}</b></span> &nbsp;|&nbsp; 
                            <span>Age: <b>{days_held} days</b> (Since {lot_row['Outward Date']})</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with c_lot_btn:
                    st.write("")
                    st.button(
                        "📥 Inward",
                        key=f"btn_in_lot_{lot_no}",
                        on_click=navigate_to,
                        args=("2. Inward Register", cs_name, item_name, lot_no),
                        use_container_width=True,
                        help=f"Retrieve units from Lot {lot_no}"
                    )

        # 3. COLD STORAGE FACILITIES DIRECTORY
        fac_names = sorted(list(active_df["Cold Storage"].unique()))
        with st.expander(f"🏢 **Cold Storage Facilities ({len(fac_names)} Facilities)** — Click to Expand & Dispatch"):
            for fac_name in fac_names:
                fac_items_df = active_df[active_df["Cold Storage"] == fac_name]
                tot_fac_u = int(fac_items_df["Bal. Units"].sum())
                tot_fac_kg = fac_items_df["Bal. Total Qty (KG)"].sum()
                tot_fac_lots = len(fac_items_df)

                st.markdown(f"##### 🏬 **{fac_name}** — {tot_fac_u:,} Units | {tot_fac_kg:,.2f} KG ({tot_fac_lots} Lots)")

                item_grp = fac_items_df.groupby("Item Name").agg({
                    "Bal. Units": "sum",
                    "Bal. Total Qty (KG)": "sum",
                    "Lot No.": lambda x: ", ".join(x.astype(str).unique())
                }).reset_index()

                for _, it_row in item_grp.iterrows():
                    item_name = it_row["Item Name"]

                    c_info, c_btn1 = st.columns([3.0, 1.0])
                    with c_info:
                        st.markdown(f"""
                        <div class="item-subcard">
                            <div class="item-subcard-title">🌶️ {item_name}</div>
                            <div class="item-subcard-body">
                                <b>{int(it_row['Bal. Units']):,} Units</b> &nbsp;|&nbsp; 
                                <b>{it_row['Bal. Total Qty (KG)']:,.2f} KG</b> &nbsp;|&nbsp; 
                                <span>Lots: {it_row['Lot No.']}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    with c_btn1:
                        st.write("")
                        st.button(
                            "➕ Outward",
                            key=f"btn_out_{fac_name}_{item_name}",
                            on_click=navigate_to,
                            args=("1. Outward Register", fac_name, item_name, ""),
                            use_container_width=True,
                            help=f"Register new Outward for {item_name} at {fac_name}"
                        )
                st.write("")

        st.divider()

        # 4. QUICK ITEM STOCK FINDER (CLEAN TOTALS PER LOCATION)
        st.markdown("##### ⚡ Quick Item Stock Finder")
        with st.container(border=True):
            avail_items = sorted(list(active_df["Item Name"].unique()))
            selected_finder_item = st.selectbox(
                "Check Instant Item Balance",
                options=["-- Select Item --"] + avail_items,
                key="dash_finder_sel"
            )

            if selected_finder_item != "-- Select Item --":
                item_rows = active_df[active_df["Item Name"] == selected_finder_item]
                tot_item_u = item_rows["Bal. Units"].sum()
                tot_item_kg = item_rows["Bal. Total Qty (KG)"].sum()

                st.metric(f"Total {selected_finder_item}", f"{tot_item_kg:,.2f} KG", f"{int(tot_item_u)} Units Available")
                
                st.write("")
                # Clean location summary
                loc_grp = item_rows.groupby("Cold Storage").agg({
                    "Bal. Units": "sum",
                    "Bal. Total Qty (KG)": "sum"
                }).reset_index()

                for _, loc_r in loc_grp.iterrows():
                    st.markdown(f"""
                    <div class="finder-loc-card">
                        <div class="finder-loc-name">🏬 {loc_r['Cold Storage']}</div>
                        <div class="finder-loc-val">{loc_r['Bal. Total Qty (KG)']:,.2f} KG <span style="font-size:12.5px; opacity:0.8; font-weight:500;">({int(loc_r['Bal. Units']):,} Units)</span></div>
                    </div>
                    """, unsafe_allow_html=True)

            else:
                st.caption("Select any item above to see immediate totals and cold storage breakdown.")

        st.divider()

        # 5. DETAILED AGING TABLE
        st.markdown("##### ⏳ Detailed Aging Status (Oldest to Newest)")
        
        def get_aging_badge(days):
            if days >= 90:
                return "🔴 Critical (90+ Days)"
            elif days >= 60:
                return "🟠 Alert (60-89 Days)"
            elif days >= 30:
                return "🟡 Moderate (30-59 Days)"
            else:
                return "🟢 Fresh (<30 Days)"

        active_df["Aging Category"] = active_df["Days in Storage"].apply(get_aging_badge)

        aging_display_df = active_df[[
            "Lot No.", "Outward Date", "Days in Storage", "Aging Category",
            "Cold Storage", "Item Name", "Bal. Units", "Bal. Total Qty (KG)"
        ]]

        search_aging = st.text_input("🔍 Search Aging Records (Filter by Lot, Storage, or Item)", key="search_aging")
        if search_aging:
            aging_display_df = aging_display_df[aging_display_df.apply(lambda row: row.astype(str).str.contains(search_aging, case=False).any(), axis=1)]

        st.dataframe(aging_display_df, use_container_width=True, hide_index=True)

        c_age_exp1, c_age_exp2 = st.columns(2)
        with c_age_exp1:
            st.download_button(
                "📥 Export Aging Report to CSV",
                aging_display_df.to_csv(index=False).encode('utf-8'),
                "Detailed_Aging_Report.csv",
                "text/csv",
                use_container_width=True
            )
        with c_age_exp2:
            pdf_age_buf = generate_pdf(aging_display_df, "Detailed Aging Report")
            if pdf_age_buf:
                st.download_button(
                    "📄 Export Aging Report to PDF",
                    pdf_age_buf,
                    "Detailed_Aging_Report.pdf",
                    "application/pdf",
                    use_container_width=True
                )

    else:
        st.info("No active stock available. Record Outward entries to view the operational dashboard.")

# =========================================================
# TAB 1: OUTWARD REGISTER
# =========================================================
elif selected_tab == "1. Outward Register":
    st.subheader("Record Outward Dispatch")

    if st.session_state.prefill_cs or st.session_state.prefill_item:
        st.info(f"⚡ Quick-Entry Mode: Pre-selected **{st.session_state.prefill_item}** for **{st.session_state.prefill_cs}**.")

    cs_opts = sorted([str(x) for x in df_raw_out["cold_storage"].dropna().unique() if str(x).strip()])
    item_opts = sorted([str(x) for x in df_raw_out["item_name"].dropna().unique() if str(x).strip()])

    cs_default_idx = cs_opts.index(st.session_state.prefill_cs) + 1 if st.session_state.prefill_cs in cs_opts else 0
    item_default_idx = item_opts.index(st.session_state.prefill_item) + 1 if st.session_state.prefill_item in item_opts else 0

    with st.container(border=True):
        r1c1, r1c2, r1c3 = st.columns(3)
        out_date = r1c1.date_input("Date (DD/MM/YY)", datetime.date.today(), format="DD/MM/YYYY", key="out_d")
        out_ref = r1c2.text_input("Reference No. (Optional)", key="out_ref")
        out_lot = r1c3.text_input("Lot No. * (Numbers, '-' or '/' only)", key="out_lot")

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            cs_selected = st.selectbox("Select Cold Storage *", options=["-- Type New Below --"] + cs_opts, index=cs_default_idx, key="out_cs_sel")
            cs_new = st.text_input("Or Type Cold Storage Name *", placeholder="Leave blank if selected from above", key="out_cs_new")

        with r2c2:
            item_selected = st.selectbox("Select Item *", options=["-- Type New Below --"] + item_opts, index=item_default_idx, key="out_item_sel")
            item_new = st.text_input("Or Type Item Name *", placeholder="Leave blank if selected from above", key="out_item_new")

        r3c1, r3c2, r3c3 = st.columns(3)
        out_units = r3c1.number_input("Number of Units *", min_value=1, step=1, value=10, key="out_u")
        out_unit_size = r3c2.number_input("Unit Weight (KG) *", min_value=0.01, step=0.5, value=25.0, key="out_us")
        
        initial_total = out_units * out_unit_size
        with r3c3:
            st.markdown(f"""
            <div class="live-calc-box">
                <div class="live-calc-label">Calculated Total Weight</div>
                <div id="live_total_weight_val" class="live-calc-val">{initial_total:,.2f} KG</div>
            </div>
            """, unsafe_allow_html=True)

        components.html("""
          <script>
          function attachLiveCalc() {
              const doc = window.parent.document;
              const unitsInput = doc.querySelector('input[aria-label*="Number of Units"]');
              const sizeInput = doc.querySelector('input[aria-label*="Unit Weight"]');
              const displayVal = doc.getElementById('live_total_weight_val');

              function update() {
                  if (!unitsInput || !sizeInput || !displayVal) return;
                  const u = parseFloat(unitsInput.value) || 0;
                  const s = parseFloat(sizeInput.value) || 0;
                  const tot = u * s;
                  displayVal.innerText = tot.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' KG';
              }

              if (unitsInput && !unitsInput.dataset.liveListened) {
                  unitsInput.dataset.liveListened = "true";
                  unitsInput.addEventListener('input', update);
                  unitsInput.addEventListener('keyup', update);
                  unitsInput.addEventListener('change', update);
              }
              if (sizeInput && !sizeInput.dataset.liveListened) {
                  sizeInput.dataset.liveListened = "true";
                  sizeInput.addEventListener('input', update);
                  sizeInput.addEventListener('keyup', update);
                  sizeInput.addEventListener('change', update);
              }
          }
          setInterval(attachLiveCalc, 200);
          </script>
        """, height=0, width=0)

        if st.button("Save Outward Entry", type="primary", use_container_width=True):
            final_cs = cs_new.strip() if cs_new.strip() else (cs_selected if cs_selected != "-- Type New Below --" else "")
            final_item = item_new.strip() if item_new.strip() else (item_selected if item_selected != "-- Type New Below --" else "")
            out_lot_clean = out_lot.strip()
            auto_total_weight = out_units * out_unit_size

            if not (out_lot_clean and final_cs and final_item):
                st.error("Please fill in all required fields (Lot No., Cold Storage Name, and Item Name).")
            elif not re.match(r'^[0-9/-]+$', out_lot_clean):
                st.error("Invalid Lot No.: Alphabets are not allowed. Use only numbers, '-', or '/'.")
            else:
                existing_lots = df_raw_out["receipt_no"].astype(str).tolist()
                if out_lot_clean in existing_lots:
                    st.error(f"Lot No. '{out_lot_clean}' already exists! Duplicates are not permitted.")
                else:
                    new_record = {
                        "entry_date": format_date_str(out_date),
                        "reference_no": out_ref.strip() or "-",
                        "receipt_no": out_lot_clean,
                        "cold_storage": final_cs,
                        "item_name": final_item,
                        "qty": int(out_units),
                        "unit_size": float(out_unit_size),
                        "total_qty": float(auto_total_weight)
                    }
                    with st.spinner("Saving to Google Drive..."):
                        save_outward_entry(new_record)
                    st.session_state.prefill_cs = ""
                    st.session_state.prefill_item = ""
                    st.session_state.prefill_lot = ""
                    st.success(f"Saved: Lot '{out_lot_clean}' ({out_units} units of {final_item})")
                    st.rerun()

    # OUTWARD EDIT & DELETE MANAGER
    with st.expander("🛠️ Manage / Edit / Delete Outward Records"):
        if not df_raw_out.empty:
            out_list = [f"ID {r['id']} | Lot: {r['receipt_no']} ({r['item_name']} - {r['qty']} Units @ {r['cold_storage']})" for _, r in df_raw_out.iloc[::-1].iterrows()]
            sel_edit_out = st.selectbox("Select Outward Entry to Manage", options=out_list, key="sel_edit_out")
            sel_id_out = sel_edit_out.split(" | ")[0].replace("ID ", "").strip()
            target_out = df_raw_out[df_raw_out["id"].astype(str) == str(sel_id_out)].iloc[0]

            e_c1, e_c2, e_c3 = st.columns(3)
            e_out_dt = e_c1.date_input("Edit Date", parse_to_date_obj(target_out["entry_date"]) or datetime.date.today(), key="e_out_dt")
            e_out_ref = e_c2.text_input("Edit Reference", value=str(target_out["reference_no"]), key="e_out_ref")
            e_out_lot = e_c3.text_input("Lot No. (Read-Only)", value=str(target_out["receipt_no"]), disabled=True, key="e_out_lot")

            e_c4, e_c5 = st.columns(2)
            e_out_cs = e_c4.text_input("Edit Cold Storage", value=str(target_out["cold_storage"]), key="e_out_cs")
            e_out_item = e_c5.text_input("Edit Item Name", value=str(target_out["item_name"]), key="e_out_item")

            e_c6, e_c7 = st.columns(2)
            e_out_units = e_c6.number_input("Edit Units", min_value=1, value=int(target_out["qty"]), step=1, key="e_out_units")
            e_out_size = e_c7.number_input("Edit Unit Weight (KG)", min_value=0.01, value=float(target_out["unit_size"]), step=0.5, key="e_out_size")

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("💾 Update Outward Entry", type="primary", use_container_width=True):
                    upd_data = {
                        "entry_date": format_date_str(e_out_dt),
                        "reference_no": e_out_ref.strip() or "-",
                        "cold_storage": e_out_cs.strip(),
                        "item_name": e_out_item.strip(),
                        "qty": int(e_out_units),
                        "unit_size": float(e_out_size),
                        "total_qty": float(e_out_units * e_out_size)
                    }
                    with st.spinner("Updating entry..."):
                        update_outward_entry(sel_id_out, upd_data)
                    st.success("Outward entry updated successfully!")
                    st.rerun()

            with btn_col2:
                if st.button("🗑️ Delete Outward Entry", use_container_width=True):
                    in_use = not df_raw_in[df_raw_in["receipt_no"].astype(str) == str(target_out["receipt_no"])].empty
                    if in_use:
                        st.error("Cannot delete! Inward retrievals already exist for this lot. Delete inward entries first.")
                    else:
                        with st.spinner("Deleting entry..."):
                            delete_outward_entry(sel_id_out)
                        st.warning(f"Deleted Lot '{target_out['receipt_no']}' successfully.")
                        st.rerun()
        else:
            st.info("No outward records available to manage.")

    st.divider()

    df_out_display = df_raw_out.copy()
    if not df_out_display.empty:
        df_out_display = df_out_display.rename(columns={
            "id": "ID", "entry_date": "Date", "reference_no": "Reference No.",
            "receipt_no": "Lot No.", "cold_storage": "Cold Storage", "item_name": "Item Name",
            "qty": "Units", "unit_size": "Unit Qty (KG)", "total_qty": "Total Qty (KG)"
        })
        df_out_display = df_out_display.iloc[::-1]

    search_out = st.text_input("🔍 Search Outward Records (Type to Filter)", key="search_out")
    if search_out and not df_out_display.empty:
        df_out_display = df_out_display[df_out_display.apply(lambda row: row.astype(str).str.contains(search_out, case=False).any(), axis=1)]

    st.dataframe(df_out_display, use_container_width=True, hide_index=True)

    c_exp1, c_exp2 = st.columns(2)
    with c_exp1:
        st.download_button(
            "📥 Export to CSV / Excel",
            df_out_display.to_csv(index=False).encode('utf-8'),
            "Outward_Register.csv",
            "text/csv",
            use_container_width=True
        )
    with c_exp2:
        pdf_buffer = generate_pdf(df_out_display, "Outward Register Report")
        if pdf_buffer:
            st.download_button(
                "📄 Export to PDF",
                pdf_buffer,
                "Outward_Register.pdf",
                "application/pdf",
                use_container_width=True
            )

# =========================================================
# TAB 2: INWARD REGISTER
# =========================================================
elif selected_tab == "2. Inward Register":
    st.subheader("Record Inward Retrieval")

    if st.session_state.prefill_lot:
        st.info(f"⚡ Quick-Entry Mode: Pre-selected **Lot {st.session_state.prefill_lot}** ({st.session_state.prefill_item} @ {st.session_state.prefill_cs}).")

    active_records = []
    if not df_sum.empty:
        active_df_in = df_sum[df_sum["Bal. Units"] > 0]
        for _, row in active_df_in.iterrows():
            active_records.append((str(row["Lot No."]), str(row["Item Name"]), str(row["Cold Storage"]), int(row["Bal. Units"])))

    all_active_items = sorted(list(set(r[1] for r in active_records)))
    all_active_lots = sorted(list(set(r[0] for r in active_records)))

    if st.session_state.prefill_lot:
        default_mode_idx = 0
    elif st.session_state.prefill_item:
        default_mode_idx = 1
    else:
        default_mode_idx = 0

    with st.container(border=True):
        lookup_mode = st.radio(
            "Lookup Method:",
            ["Search by Lot No.", "Search by Item Name (Reverse Lookup)"],
            index=default_mode_idx,
            horizontal=True
        )

        r1c1, r1c2 = st.columns(2)
        in_date = r1c1.date_input("Retrieval Date (DD/MM/YY)", datetime.date.today(), format="DD/MM/YYYY", key="in_date_picker")

        sel_lot_final = ""
        sel_item_final = ""
        max_avail_units = 1

        if lookup_mode == "Search by Lot No.":
            lot_default_idx = all_active_lots.index(st.session_state.prefill_lot) + 1 if st.session_state.prefill_lot in all_active_lots else 0
            sel_in_lot = r1c2.selectbox("Select Active Lot No. *", options=[""] + all_active_lots, index=lot_default_idx, key="in_lot_sel")
            if sel_in_lot:
                matching = [r for r in active_records if r[0] == sel_in_lot]
                item_candidates = [m[1] for m in matching]
                sel_lot_final = sel_in_lot

                r2c1, r2c2 = st.columns(2)
                sel_item_final = r2c1.selectbox("Allotted Item Name *", options=item_candidates, key="in_item_sel_by_lot")
                curr_rec = [m for m in matching if m[1] == sel_item_final]
                max_avail_units = max(1, int(curr_rec[0][3])) if curr_rec else 1

                in_qty = r2c2.number_input(
                    "Inward Units Received *",
                    min_value=1,
                    max_value=max_avail_units,
                    step=1,
                    value=1,
                    key="in_qty_val_lot",
                    help=f"Remaining Balance: {max_avail_units} units available"
                )
            else:
                r2c1, r2c2 = st.columns(2)
                r2c1.selectbox("Allotted Item Name *", options=["(Select Lot No. first)"], disabled=True)
                in_qty = r2c2.number_input("Inward Units Received *", min_value=1, value=1, disabled=True)

        else:
            item_in_def_idx = all_active_items.index(st.session_state.prefill_item) + 1 if st.session_state.prefill_item in all_active_items else 0
            sel_in_item = r1c2.selectbox("Select Stored Item Name *", options=[""] + all_active_items, index=item_in_def_idx, key="in_item_sel_reverse")
            if sel_in_item:
                matching = [r for r in active_records if r[1] == sel_in_item]
                lot_candidates = [f"{m[0]} ({m[2]} - {m[3]} Bal Units)" for m in matching]
                sel_item_final = sel_item_final = sel_in_item

                r2c1, r2c2 = st.columns(2)
                sel_lot_display = r2c1.selectbox("Select Available Lot No. *", options=lot_candidates, key="in_lot_sel_by_item")
                sel_lot_final = sel_lot_display.split(" ")[0] if sel_lot_display else ""
                curr_rec = [m for m in matching if m[0] == sel_lot_final]
                max_avail_units = max(1, int(curr_rec[0][3])) if curr_rec else 1

                in_qty = r2c2.number_input(
                    "Inward Units Received *",
                    min_value=1,
                    max_value=max_avail_units,
                    step=1,
                    value=1,
                    key="in_qty_val_item",
                    help=f"Remaining Balance: {max_avail_units} units available"
                )
            else:
                r2c1, r2c2 = st.columns(2)
                r2c1.selectbox("Select Available Lot No. *", options=["(Select Item first)"], disabled=True)
                in_qty = r2c2.number_input("Inward Units Received *", min_value=1, value=1, disabled=True)

        if sel_lot_final and sel_item_final:
            st.info(f"Selected Lot **{sel_lot_final}** has **{max_avail_units} units** of **{sel_item_final}** remaining in storage.")

        if st.button("Save Inward Retrieval", type="primary", use_container_width=True):
            if not (sel_lot_final and sel_item_final and in_qty > 0):
                st.error("Please select a valid Lot No. and Item Name.")
            else:
                new_inward_record = {
                    "entry_date": format_date_str(in_date),
                    "receipt_no": sel_lot_final,
                    "item_name": sel_item_final,
                    "qty": int(in_qty)
                }
                with st.spinner("Saving to Google Drive..."):
                    save_inward_entry(new_inward_record)
                st.session_state.prefill_cs = ""
                st.session_state.prefill_item = ""
                st.session_state.prefill_lot = ""
                st.success(f"Retrieved {in_qty} units of '{sel_item_final}' from Lot '{sel_lot_final}'.")
                st.rerun()

    # INWARD EDIT & DELETE MANAGER
    with st.expander("🛠️ Manage / Edit / Delete Inward Retrievals"):
        if not df_raw_in.empty:
            in_list = [f"ID {r['id']} | Date: {r['entry_date']} | Lot: {r['receipt_no']} ({r['item_name']} - {r['qty']} Units)" for _, r in df_raw_in.iloc[::-1].iterrows()]
            sel_edit_in = st.selectbox("Select Inward Entry to Manage", options=in_list, key="sel_edit_in")
            sel_id_in = sel_edit_in.split(" | ")[0].replace("ID ", "").strip()
            target_in = df_raw_in[df_raw_in["id"].astype(str) == str(sel_id_in)].iloc[0]

            ei_c1, ei_c2, ei_c3 = st.columns(3)
            ei_in_dt = ei_c1.date_input("Edit Retrieval Date", parse_to_date_obj(target_in["entry_date"]) or datetime.date.today(), key="ei_in_dt")
            ei_lot = ei_c2.text_input("Lot No. (Read-Only)", value=str(target_in["receipt_no"]), disabled=True, key="ei_lot")
            ei_item = ei_c3.text_input("Item Name (Read-Only)", value=str(target_in["item_name"]), disabled=True, key="ei_item")

            ei_qty = st.number_input("Edit Units Retrieved", min_value=1, value=int(target_in["qty"]), step=1, key="ei_qty")

            btn_in1, btn_in2 = st.columns(2)
            with btn_in1:
                if st.button("💾 Update Inward Retrieval", type="primary", use_container_width=True):
                    upd_in = {
                        "entry_date": format_date_str(ei_in_dt),
                        "qty": int(ei_qty)
                    }
                    with st.spinner("Updating retrieval record..."):
                        update_inward_entry(sel_id_in, upd_in)
                    st.success("Inward record updated successfully!")
                    st.rerun()

            with btn_in2:
                if st.button("🗑️ Delete Inward Retrieval", use_container_width=True):
                    with st.spinner("Deleting retrieval record..."):
                        delete_inward_entry(sel_id_in)
                    st.warning(f"Deleted Inward retrieval of {target_in['qty']} units from Lot '{target_in['receipt_no']}'.")
                    st.rerun()
        else:
            st.info("No inward retrieval records available to manage.")

    st.divider()

    df_in_display = df_raw_in.copy()
    if not df_in_display.empty:
        df_in_display = df_in_display.rename(columns={
            "id": "ID", "entry_date": "Date", "receipt_no": "Lot No.",
            "item_name": "Item Name", "qty": "Inward Units Received"
        })
        df_in_display = df_in_display.iloc[::-1]

    search_in = st.text_input("🔍 Search Inward Records (Type to Filter)", key="search_in")
    if search_in and not df_in_display.empty:
        df_in_display = df_in_display[df_in_display.apply(lambda row: row.astype(str).str.contains(search_in, case=False).any(), axis=1)]

    st.dataframe(df_in_display, use_container_width=True, hide_index=True)

    c_in1, c_in2 = st.columns(2)
    with c_in1:
        st.download_button(
            "📥 Export to CSV / Excel",
            df_in_display.to_csv(index=False).encode('utf-8'),
            "Inward_Register.csv",
            "text/csv",
            use_container_width=True
        )
    with c_in2:
        pdf_in_buf = generate_pdf(df_in_display, "Inward Register Report")
        if pdf_in_buf:
            st.download_button(
                "📄 Export to PDF",
                pdf_in_buf,
                "Inward_Register.pdf",
                "application/pdf",
                use_container_width=True
            )

# =========================================================
# TAB 3: STOCK SUMMARY
# =========================================================
elif selected_tab == "3. Stock Summary":
    st.subheader("Live Cold Storage Stock Summary")

    total_outward_u = df_sum["Outward Units"].sum() if not df_sum.empty else 0
    total_inward_u = df_sum["Inward Units"].sum() if not df_sum.empty else 0
    total_bal_u = df_sum["Bal. Units"].sum() if not df_sum.empty else 0
    total_bal_kg = df_sum["Bal. Total Qty (KG)"].sum() if not df_sum.empty else 0.0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">📤 Dispatched Total</div>
            <div class="kpi-value">{int(total_outward_u):,} <span style="font-size:16px; font-weight:600;">Units</span></div>
            <div class="kpi-sub">Lifetime Outward</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">📥 Retrieved Total</div>
            <div class="kpi-value">{int(total_inward_u):,} <span style="font-size:16px; font-weight:600;">Units</span></div>
            <div class="kpi-sub">Lifetime Inward</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">📦 Remaining Units</div>
            <div class="kpi-value">{int(total_bal_u):,} <span style="font-size:16px; font-weight:600;">Units</span></div>
            <div class="kpi-sub">In Storage Currently</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">⚖️ Net Stored Weight</div>
            <div class="kpi-value">{total_bal_kg:,.2f} <span style="font-size:16px; font-weight:600;">KG</span></div>
            <div class="kpi-sub">Live Cold Weight</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    c_sum_ctrl1, c_sum_ctrl2 = st.columns([1, 2])
    hide_cleared = c_sum_ctrl1.checkbox("Hide Fully Cleared Lots", value=True, key="sum_hide_c")
    search_sum = c_sum_ctrl2.text_input("🔍 Search Stock Summary (Type to Filter)", key="search_sum")

    df_sum_disp = df_sum.copy()
    if hide_cleared and not df_sum_disp.empty:
        df_sum_disp = df_sum_disp[df_sum_disp["Status"] != "CLEARED"]
    if search_sum and not df_sum_disp.empty:
        df_sum_disp = df_sum_disp[df_sum_disp.apply(lambda row: row.astype(str).str.contains(search_sum, case=False).any(), axis=1)]

    st.dataframe(df_sum_disp, use_container_width=True, hide_index=True)

    c_sum1, c_sum2 = st.columns(2)
    with c_sum1:
        st.download_button(
            "📥 Export to CSV / Excel",
            df_sum_disp.to_csv(index=False).encode('utf-8'),
            "Stock_Summary.csv",
            "text/csv",
            use_container_width=True
        )
    with c_sum2:
        pdf_sum_buf = generate_pdf(df_sum_disp, "Stock Summary Report")
        if pdf_sum_buf:
            st.download_button(
                "📄 Export to PDF",
                pdf_sum_buf,
                "Stock_Summary.pdf",
                "application/pdf",
                use_container_width=True
            )

# =========================================================
# TAB 4: CUSTOM REPORTS
# =========================================================
elif selected_tab == "4. Custom Reports":
    st.subheader("Filter & Custom Report Engine")

    all_lots = ["ALL"] + sorted(list(set(df_raw_out["receipt_no"].dropna().astype(str)))) if not df_raw_out.empty else ["ALL"]
    all_cs = ["ALL"] + sorted(list(set(df_raw_out["cold_storage"].dropna().astype(str)))) if not df_raw_out.empty else ["ALL"]
    all_items = ["ALL"] + sorted(list(set(df_raw_out["item_name"].dropna().astype(str)))) if not df_raw_out.empty else ["ALL"]

    with st.container(border=True):
        rf1, rf2, rf3, rf4 = st.columns(4)
        rep_type = rf1.selectbox("Report Type", ["Combined Lot Ledger", "Outward Register", "Inward Register", "Stock Summary"], key="rep_type_sel")
        rep_group = rf2.selectbox("Group By", ["None", "Item Name", "Cold Storage", "Date"], key="rep_grp_sel")
        rep_from_dt = rf3.date_input("From Date", datetime.date.today().replace(day=1), format="DD/MM/YYYY", key="rf_from")
        rep_to_dt = rf4.date_input("To Date", datetime.date.today(), format="DD/MM/YYYY", key="rf_to")

        rf5, rf6, rf7 = st.columns(3)
        sel_lot = rf5.selectbox("Lot No. Filter", options=all_lots, key="rep_lot_f")
        sel_cs = rf6.selectbox("Cold Storage Filter", options=all_cs, key="rep_cs_f")
        sel_item = rf7.selectbox("Item Filter", options=all_items, key="rep_item_f")

    if rep_group != "None" and not df_sum.empty:
        df_filtered = df_sum.copy()
        if sel_lot != "ALL":
            df_filtered = df_filtered[df_filtered["Lot No."] == sel_lot]
        if sel_cs != "ALL":
            df_filtered = df_filtered[df_filtered["Cold Storage"] == sel_cs]
        if sel_item != "ALL":
            df_filtered = df_filtered[df_filtered["Item Name"] == sel_item]

        grp_col = rep_group
        df_res = df_filtered.groupby(grp_col).agg({
            "Lot No.": "count",
            "Outward Units": "sum",
            "Inward Units": "sum",
            "Bal. Units": "sum",
            "Bal. Total Qty (KG)": "sum"
        }).reset_index()
        df_res.rename(columns={"Lot No.": "Total Lots / Entries", "Bal. Total Qty (KG)": "Bal. Weight (KG)"}, inplace=True)
        df_res["Bal. Weight (KG)"] = df_res["Bal. Weight (KG)"].round(2)

    else:
        if rep_type == "Combined Lot Ledger":
            df_res = df_sum.copy()
            date_col = None
        elif rep_type == "Outward Register":
            df_res = df_out_display.copy()
            date_col = "Date"
        elif rep_type == "Inward Register":
            df_res = df_in_display.copy()
            date_col = "Date"
        elif rep_type == "Stock Summary":
            df_res = df_sum.copy()
            date_col = None

        if date_col and not df_res.empty:
            df_res["dt_obj"] = df_res[date_col].apply(parse_to_date_obj)
            df_res = df_res[(df_res["dt_obj"] >= rep_from_dt) & (df_res["dt_obj"] <= rep_to_dt)]
            df_res.drop(columns=["dt_obj"], inplace=True)

        if "Lot No." in df_res.columns and sel_lot != "ALL":
            df_res = df_res[df_res["Lot No."] == sel_lot]
        if "Cold Storage" in df_res.columns and sel_cs != "ALL":
            df_res = df_res[df_res["Cold Storage"] == sel_cs]
        if "Item Name" in df_res.columns and sel_item != "ALL":
            df_res = df_res[df_res["Item Name"] == sel_item]

    st.dataframe(df_res, use_container_width=True, hide_index=True)

    c_rep1, c_rep2 = st.columns(2)
    with c_rep1:
        st.download_button(
            "📥 Export Filtered CSV / Excel",
            df_res.to_csv(index=False).encode('utf-8'),
            "Custom_Report.csv",
            "text/csv",
            use_container_width=True
        )
    with c_rep2:
        title_report = f"{rep_type} (Grouped by {rep_group})" if rep_group != "None" else rep_type
        pdf_rep_buf = generate_pdf(df_res, title_report)
        if pdf_rep_buf:
            st.download_button(
                "📄 Export Filtered PDF",
                pdf_rep_buf,
                "Custom_Report.pdf",
                "application/pdf",
                use_container_width=True
            )
