import datetime
import io
import os
import re
import sqlite3
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Optional ReportLab support for PDF generation
try:
  from reportlab.lib import colors
  from reportlab.lib.pagesizes import landscape, letter
  from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
  from reportlab.platypus import (
      Image,
      Paragraph,
      SimpleDocTemplate,
      Spacer,
      Table,
      TableStyle,
  )

  HAS_REPORTLAB = True
except ImportError:
  HAS_REPORTLAB = False

# ---------------------------------------------------------
# PAGE CONFIG & STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="Lehri Masala Cold Storage Register",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .live-calc-box {
        background-color: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
        margin-top: 4px;
    }
    .live-calc-label {
        font-size: 12.5px;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .live-calc-val {
        font-size: 22px;
        font-weight: 700;
        color: #0F172A;
        margin-top: 2px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# DATABASE ENGINE
# ---------------------------------------------------------
def get_db_connection():
  conn = sqlite3.connect("cold_storage.db", check_same_thread=False)
  return conn


def init_db():
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS outward (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT,
            reference_no TEXT,
            receipt_no TEXT UNIQUE,
            cold_storage TEXT,
            item_name TEXT,
            qty INTEGER,
            unit_size REAL DEFAULT 0,
            total_qty REAL DEFAULT 0
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS inward (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT,
            receipt_no TEXT,
            item_name TEXT,
            qty INTEGER
        )
    """)
  conn.commit()
  conn.close()


init_db()


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def format_date_str(d_val):
  if isinstance(d_val, (datetime.date, datetime.datetime)):
    return d_val.strftime("%d/%m/%y")
  d_str = str(d_val).strip()
  parts = re.split(r"[-/.]", d_str)
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
  doc = SimpleDocTemplate(
      buffer,
      pagesize=page_size,
      leftMargin=25,
      rightMargin=25,
      topMargin=25,
      bottomMargin=25,
  )
  elements = []
  styles = getSampleStyleSheet()

  if os.path.exists("logo.png"):
    try:
      pdf_logo = Image("logo.png", width=110, height=45)
      pdf_logo.hAlign = "CENTER"
      elements.append(pdf_logo)
      elements.append(Spacer(1, 8))
    except Exception:
      pass

  elements.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
  elements.append(
      Paragraph(
          f"Generated on: {datetime.date.today().strftime('%d/%m/%y')}",
          styles["Normal"],
      )
  )
  elements.append(Spacer(1, 12))

  headers = list(df.columns)
  data = [headers] + df.astype(str).values.tolist()

  avail_width = doc.width
  col_w = avail_width / len(headers) if headers else avail_width
  col_widths = [col_w] * len(headers)

  cell_style = ParagraphStyle(
      "CellText",
      parent=styles["Normal"],
      fontName="Helvetica",
      fontSize=8,
      leading=10,
      alignment=1,
  )
  header_style = ParagraphStyle(
      "HeaderText",
      parent=styles["Normal"],
      fontName="Helvetica-Bold",
      fontSize=8,
      leading=10,
      textColor=colors.whitesmoke,
      alignment=1,
  )

  formatted_table_data = []
  for row_idx, row in enumerate(data):
    formatted_row = []
    for cell in row:
      st_use = header_style if row_idx == 0 else cell_style
      formatted_row.append(Paragraph(str(cell), st_use))
    formatted_table_data.append(formatted_row)

  t = Table(formatted_table_data, colWidths=col_widths)
  t.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
          ("ALIGN", (0, 0), (-1, -1), "CENTER"),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("TOPPADDING", (0, 0), (-1, -1), 4),
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
      ])
  )
  elements.append(t)
  doc.build(elements)
  buffer.seek(0)
  return buffer


# ---------------------------------------------------------
# HEADER / BRANDING
# ---------------------------------------------------------
col_logo, col_title = st.columns([1, 8])
with col_logo:
  if os.path.exists("logo.png"):
    st.image("logo.png", width=90)
with col_title:
  st.markdown(
      "<div class='main-header'>Lehri Masala Cold Storage Register</div>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<div class='sub-header'>Cloud-Enabled Batch Tracking & Stock"
      " Ledger</div>",
      unsafe_allow_html=True,
  )

# ---------------------------------------------------------
# SIDEBAR / DATABASE TOOLS
# ---------------------------------------------------------
with st.sidebar:
  st.header("⚙️ Database & Security")

  if os.path.exists("cold_storage.db"):
    with open("cold_storage.db", "rb") as f:
      st.download_button(
          label="💾 Download DB Backup",
          data=f,
          file_name=f"cold_storage_backup_{datetime.date.today().strftime('%Y%m%d')}.db",
          mime="application/x-sqlite3",
          use_container_width=True,
      )

  if st.button("🛡️ Check DB Integrity", use_container_width=True):
    conn = get_db_connection()
    res = conn.execute("PRAGMA integrity_check;").fetchone()[0]
    conn.close()
    if res == "ok":
      st.success("Database status: Healthy (0 errors).")
    else:
      st.warning(f"Integrity alert: {res}")

  if st.button("⚡ Optimize DB (VACUUM)", use_container_width=True):
    conn = get_db_connection()
    conn.execute("VACUUM;")
    conn.close()
    st.success("Database compressed and optimized.")

# ---------------------------------------------------------
# APPLICATION TABS
# ---------------------------------------------------------
tab_outward, tab_inward, tab_summary, tab_reports = st.tabs([
    "1. Outward Register",
    "2. Inward Register",
    "3. Stock Summary",
    "4. Custom Reports",
])

# =========================================================
# TAB 1: OUTWARD REGISTER
# =========================================================
with tab_outward:
  st.subheader("Record Outward Dispatch")

  conn = get_db_connection()
  cursor = conn.cursor()
  cs_opts = [
      r[0]
      for r in cursor.execute(
          "SELECT DISTINCT cold_storage FROM outward WHERE cold_storage IS NOT"
          " NULL AND cold_storage != '' ORDER BY cold_storage"
      ).fetchall()
  ]
  item_opts = [
      r[0]
      for r in cursor.execute(
          "SELECT DISTINCT item_name FROM outward WHERE item_name IS NOT NULL"
          " AND item_name != '' ORDER BY item_name"
      ).fetchall()
  ]
  conn.close()

  r1c1, r1c2, r1c3 = st.columns(3)
  out_date = r1c1.date_input(
      "Date (DD/MM/YY)",
      datetime.date.today(),
      format="DD/MM/YYYY",
      key="out_d",
  )
  out_ref = r1c2.text_input("Reference No. (Optional)", key="out_ref")
  out_lot = r1c3.text_input("Lot No. * (Numbers, '-' or '/' only)", key="out_lot")

  r2c1, r2c2 = st.columns(2)
  with r2c1:
    cs_selected = st.selectbox(
        "Select Past Cold Storage",
        options=["-- Type New Below --"] + cs_opts,
        key="out_cs_sel",
    )
    cs_new = st.text_input(
        "Or Type Cold Storage Name *",
        placeholder="Leave blank if selected from above",
        key="out_cs_new",
    )

  with r2c2:
    item_selected = st.selectbox(
        "Select Past Item",
        options=["-- Type New Below --"] + item_opts,
        key="out_item_sel",
    )
    item_new = st.text_input(
        "Or Type Item Name *",
        placeholder="Leave blank if selected from above",
        key="out_item_new",
    )

  r3c1, r3c2, r3c3 = st.columns(3)
  out_units = r3c1.number_input(
      "Number of Units *", min_value=1, step=1, value=10, key="out_u"
  )
  out_unit_size = r3c2.number_input(
      "Unit Weight (KG) *", min_value=0.01, step=0.5, value=25.0, key="out_us"
  )

  initial_total = out_units * out_unit_size
  with r3c3:
    st.markdown(
        f"""
        <div class="live-calc-box">
            <div class="live-calc-label">Calculated Total Weight</div>
            <div id="live_total_weight_val" class="live-calc-val">{initial_total:,.2f} KG</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  components.html(
      """
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
      """,
      height=0,
      width=0,
  )

  if st.button("Save Outward Entry", type="primary", use_container_width=True):
    final_cs = (
        cs_new.strip()
        if cs_new.strip()
        else (cs_selected if cs_selected != "-- Type New Below --" else "")
    )
    final_item = (
        item_new.strip()
        if item_new.strip()
        else (item_selected if item_selected != "-- Type New Below --" else "")
    )
    out_lot_clean = out_lot.strip()
    auto_total_weight = out_units * out_unit_size

    if not (out_lot_clean and final_cs and final_item):
      st.error(
          "Please fill in all required fields (Lot No., Cold Storage Name, and"
          " Item Name)."
      )
    elif not re.match(r"^[0-9/-]+$", out_lot_clean):
      st.error(
          "Invalid Lot No.: Alphabets are not allowed. Use only numbers, '-', or"
          " '/'."
      )
    else:
      conn = get_db_connection()
      dup_check = conn.execute(
          "SELECT COUNT(*) FROM outward WHERE receipt_no = ?", (out_lot_clean,)
      ).fetchone()[0]
      if dup_check > 0:
        st.error(
            f"Lot No. '{out_lot_clean}' already exists! Duplicates are not"
            " permitted."
        )
      else:
        conn.execute(
            """
                    INSERT INTO outward (entry_date, reference_no, receipt_no, cold_storage, item_name, qty, unit_size, total_qty)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                format_date_str(out_date),
                out_ref.strip() or "-",
                out_lot_clean,
                final_cs,
                final_item,
                int(out_units),
                float(out_unit_size),
                float(auto_total_weight),
            ),
        )
        conn.commit()
        st.success(
            f"Saved: Lot '{out_lot_clean}' ({out_units} units of {final_item})"
        )
        st.rerun()
      conn.close()

  st.divider()

  conn = get_db_connection()
  df_out = pd.read_sql_query(
      """
        SELECT id AS "ID", entry_date AS "Date", reference_no AS "Reference No.", 
               receipt_no AS "Lot No.", cold_storage AS "Cold Storage", 
               item_name AS "Item Name", qty AS "Units", unit_size AS "Unit Qty (KG)", 
               total_qty AS "Total Qty (KG)"
        FROM outward ORDER BY id DESC
    """,
      conn,
  )
  conn.close()

  search_out = st.text_input("🔍 Search Outward Records (Type to Filter)", key="search_out")
  if search_out:
    df_out = df_out[
        df_out.apply(
            lambda row: row.astype(str)
            .str.contains(search_out, case=False)
            .any(),
            axis=1,
        )
    ]

  st.dataframe(df_out, use_container_width=True, hide_index=True)

  c_exp1, c_exp2 = st.columns(2)
  with c_exp1:
    st.download_button(
        "📥 Export to CSV / Excel",
        df_out.to_csv(index=False).encode("utf-8"),
        "Outward_Register.csv",
        "text/csv",
        use_container_width=True,
    )
  with c_exp2:
    pdf_buffer = generate_pdf(df_out, "Outward Register Report")
    if pdf_buffer:
      st.download_button(
          "📄 Export to PDF",
          pdf_buffer,
          "Outward_Register.pdf",
          "application/pdf",
          use_container_width=True,
      )

# =========================================================
# TAB 2: INWARD REGISTER (BIDIRECTIONAL SMART LOOKUP)
# =========================================================
with tab_inward:
  st.subheader("Record Inward Retrieval")

  # Fetch all active available stock records
  conn = get_db_connection()
  active_records = conn.execute(
      """
        SELECT o.receipt_no, o.item_name, o.cold_storage, (o.qty - COALESCE(i.total_inward, 0)) AS bal_units
        FROM outward o
        LEFT JOIN (
            SELECT receipt_no, item_name, SUM(qty) as total_inward FROM inward GROUP BY receipt_no, item_name
        ) i ON o.receipt_no = i.receipt_no AND o.item_name = i.item_name
        WHERE (o.qty - COALESCE(i.total_inward, 0)) > 0
        ORDER BY o.item_name, o.receipt_no
    """
  ).fetchall()
  conn.close()

  all_active_items = sorted(list(set(r[1] for r in active_records)))
  all_active_lots = sorted(list(set(r[0] for r in active_records)))

  # Selection Mode Radio (Choose By Lot No. or By Item Name)
  lookup_mode = st.radio(
      "Lookup Method:",
      ["Search by Lot No.", "Search by Item Name (Reverse Lookup)"],
      horizontal=True,
  )

  r1c1, r1c2 = st.columns(2)
  in_date = r1c1.date_input(
      "Retrieval Date (DD/MM/YY)",
      datetime.date.today(),
      format="DD/MM/YYYY",
      key="in_date_picker",
  )

  sel_lot_final = ""
  sel_item_final = ""
  max_avail_units = 1

  if lookup_mode == "Search by Lot No.":
    sel_in_lot = r1c2.selectbox(
        "Select Active Lot No. *",
        options=[""] + all_active_lots,
        key="in_lot_sel",
    )
    if sel_in_lot:
      matching = [r for r in active_records if r[0] == sel_in_lot]
      item_candidates = [m[1] for m in matching]
      sel_lot_final = sel_in_lot
      
      r2c1, r2c2 = st.columns(2)
      sel_item_final = r2c1.selectbox(
          "Allotted Item Name *",
          options=item_candidates,
          key="in_item_sel_by_lot",
      )
      curr_rec = [m for m in matching if m[1] == sel_item_final]
      max_avail_units = max(1, int(curr_rec[0][3])) if curr_rec else 1

      in_qty = r2c2.number_input(
          "Inward Units Received *",
          min_value=1,
          max_value=max_avail_units,
          step=1,
          value=1,
          key="in_qty_val_lot",
          help=f"Remaining Balance: {max_avail_units} units available",
      )
    else:
      r2c1, r2c2 = st.columns(2)
      r2c1.selectbox("Allotted Item Name *", options=["(Select Lot No. first)"], disabled=True)
      in_qty = r2c2.number_input("Inward Units Received *", min_value=1, value=1, disabled=True)

  else:  # Reverse Lookup by Item Name
    sel_in_item = r1c2.selectbox(
        "Select Stored Item Name *",
        options=[""] + all_active_items,
        key="in_item_sel_reverse",
    )
    if sel_in_item:
      matching = [r for r in active_records if r[1] == sel_in_item]
      lot_candidates = [f"{m[0]} ({m[2]} - {m[3]} Bal Units)" for m in matching]
      sel_item_final = sel_in_item

      r2c1, r2c2 = st.columns(2)
      sel_lot_display = r2c1.selectbox(
          "Select Available Lot No. *",
          options=lot_candidates,
          key="in_lot_sel_by_item",
      )
      
      # Extract actual lot number
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
          help=f"Remaining Balance: {max_avail_units} units available",
      )
    else:
      r2c1, r2c2 = st.columns(2)
      r2c1.selectbox("Select Available Lot No. *", options=["(Select Item first)"], disabled=True)
      in_qty = r2c2.number_input("Inward Units Received *", min_value=1, value=1, disabled=True)

  if sel_lot_final and sel_item_final:
    st.info(
        f"Selected Lot **{sel_lot_final}** has **{max_avail_units} units** of"
        f" **{sel_item_final}** remaining in storage."
    )

  if st.button("Save Inward Retrieval", type="primary", use_container_width=True):
    if not (sel_lot_final and sel_item_final and in_qty > 0):
      st.error("Please select a valid Lot No. and Item Name.")
    else:
      conn = get_db_connection()
      conn.execute(
          """
                INSERT INTO inward (entry_date, receipt_no, item_name, qty)
                VALUES (?, ?, ?, ?)
            """,
          (format_date_str(in_date), sel_lot_final, sel_item_final, int(in_qty)),
      )
      conn.commit()
      conn.close()
      st.success(
          f"Retrieved {in_qty} units of '{sel_item_final}' from Lot '{sel_lot_final}'."
      )
      st.rerun()

  st.divider()

  conn = get_db_connection()
  df_in = pd.read_sql_query(
      """
        SELECT id AS "ID", entry_date AS "Date", receipt_no AS "Lot No.", 
               item_name AS "Item Name", qty AS "Inward Units Received"
        FROM inward ORDER BY id DESC
    """,
      conn,
  )
  conn.close()

  search_in = st.text_input("🔍 Search Inward Records (Type to Filter)", key="search_in")
  if search_in:
    df_in = df_in[
        df_in.apply(
            lambda row: row.astype(str).str.contains(search_in, case=False).any(),
            axis=1,
        )
    ]

  st.dataframe(df_in, use_container_width=True, hide_index=True)

  c_in1, c_in2 = st.columns(2)
  with c_in1:
    st.download_button(
        "📥 Export to CSV / Excel",
        df_in.to_csv(index=False).encode("utf-8"),
        "Inward_Register.csv",
        "text/csv",
        use_container_width=True,
    )
  with c_in2:
    pdf_in_buf = generate_pdf(df_in, "Inward Register Report")
    if pdf_in_buf:
      st.download_button(
          "📄 Export to PDF",
          pdf_in_buf,
          "Inward_Register.pdf",
          "application/pdf",
          use_container_width=True,
      )

# =========================================================
# TAB 3: STOCK SUMMARY
# =========================================================
with tab_summary:
  st.subheader("Live Cold Storage Stock Summary")

  conn = get_db_connection()
  df_sum = pd.read_sql_query(
      """
        SELECT 
            o.receipt_no AS "Lot No.",
            o.cold_storage AS "Cold Storage",
            o.item_name AS "Item Name",
            o.unit_size AS "Unit Qty (KG)",
            o.qty AS "Outward Units",
            COALESCE(SUM(i.qty), 0) AS "Inward Units",
            (o.qty - COALESCE(SUM(i.qty), 0)) AS "Bal. Units",
            (o.total_qty - (COALESCE(SUM(i.qty), 0) * o.unit_size)) AS "Bal. Total Qty (KG)",
            CASE 
                WHEN (o.qty - COALESCE(SUM(i.qty), 0)) <= 0 THEN 'CLEARED'
                WHEN COALESCE(SUM(i.qty), 0) > 0 THEN 'PARTIAL'
                ELSE 'UNTOUCHED'
            END AS "Status"
        FROM outward o
        LEFT JOIN inward i ON o.receipt_no = i.receipt_no AND o.item_name = i.item_name
        GROUP BY o.id
        ORDER BY o.receipt_no
    """,
      conn,
  )
  conn.close()

  m1, m2, m3, m4 = st.columns(4)
  total_outward_u = df_sum["Outward Units"].sum() if not df_sum.empty else 0
  total_inward_u = df_sum["Inward Units"].sum() if not df_sum.empty else 0
  total_bal_u = df_sum["Bal. Units"].sum() if not df_sum.empty else 0
  total_bal_kg = (
      df_sum["Bal. Total Qty (KG)"].sum() if not df_sum.empty else 0.0
  )

  m1.metric("Total Dispatched", f"{total_outward_u:,} Units")
  m2.metric("Total Retrieved", f"{total_inward_u:,} Units")
  m3.metric("Remaining In Storage", f"{total_bal_u:,} Units")
  m4.metric("Current Stored Weight", f"{total_bal_kg:,.2f} KG")

  st.divider()

  c_sum_ctrl1, c_sum_ctrl2 = st.columns([1, 2])
  hide_cleared = c_sum_ctrl1.checkbox("Hide Fully Cleared Lots", value=True, key="sum_hide_c")
  search_sum = c_sum_ctrl2.text_input("🔍 Search Stock Summary (Type to Filter)", key="search_sum")

  if hide_cleared:
    df_sum = df_sum[df_sum["Status"] != "CLEARED"]
  if search_sum:
    df_sum = df_sum[
        df_sum.apply(
            lambda row: row.astype(str)
            .str.contains(search_sum, case=False)
            .any(),
            axis=1,
        )
    ]

  st.dataframe(df_sum, use_container_width=True, hide_index=True)

  c_sum1, c_sum2 = st.columns(2)
  with c_sum1:
    st.download_button(
        "📥 Export to CSV / Excel",
        df_sum.to_csv(index=False).encode("utf-8"),
        "Stock_Summary.csv",
        "text/csv",
        use_container_width=True,
    )
  with c_sum2:
    pdf_sum_buf = generate_pdf(df_sum, "Stock Summary Report")
    if pdf_sum_buf:
      st.download_button(
          "📄 Export to PDF",
          pdf_sum_buf,
          "Stock_Summary.pdf",
          "application/pdf",
          use_container_width=True,
      )

# =========================================================
# TAB 4: CUSTOM REPORTS
# =========================================================
with tab_reports:
  st.subheader("Filter & Custom Report Engine")

  conn = get_db_connection()
  all_lots = ["ALL"] + [
      r[0]
      for r in conn.execute(
          "SELECT DISTINCT receipt_no FROM outward ORDER BY receipt_no"
      ).fetchall()
  ]
  all_cs = ["ALL"] + [
      r[0]
      for r in conn.execute(
          "SELECT DISTINCT cold_storage FROM outward ORDER BY cold_storage"
      ).fetchall()
  ]
  all_items = ["ALL"] + [
      r[0]
      for r in conn.execute(
          "SELECT DISTINCT item_name FROM outward ORDER BY item_name"
      ).fetchall()
  ]
  conn.close()

  rf1, rf2, rf3, rf4 = st.columns(4)
  rep_type = rf1.selectbox(
      "Report Type",
      [
          "Combined Lot Ledger",
          "Outward Register",
          "Inward Register",
          "Stock Summary",
      ],
      key="rep_type_sel",
  )
  rep_group = rf2.selectbox(
      "Group By", ["None", "Item Name", "Cold Storage", "Date"], key="rep_grp_sel"
  )
  rep_from_dt = rf3.date_input(
      "From Date",
      datetime.date.today().replace(day=1),
      format="DD/MM/YYYY",
      key="rf_from",
  )
  rep_to_dt = rf4.date_input(
      "To Date", datetime.date.today(), format="DD/MM/YYYY", key="rf_to"
  )

  rf5, rf6, rf7 = st.columns(3)
  sel_lot = rf5.selectbox("Lot No. Filter", options=all_lots, key="rep_lot_f")
  sel_cs = rf6.selectbox("Cold Storage Filter", options=all_cs, key="rep_cs_f")
  sel_item = rf7.selectbox("Item Filter", options=all_items, key="rep_item_f")

  conn = get_db_connection()

  if rep_group != "None":
    df_raw = pd.read_sql_query(
        """
            SELECT 
                o.entry_date AS "Date", o.cold_storage AS "Cold Storage", 
                o.item_name AS "Item Name", o.receipt_no AS "Lot No.",
                o.qty AS "Outward Units",
                COALESCE(SUM(i.qty), 0) AS "Inward Units",
                (o.qty - COALESCE(SUM(i.qty), 0)) AS "Bal. Units",
                (o.total_qty - (COALESCE(SUM(i.qty), 0) * o.unit_size)) AS "Bal. Weight (KG)"
            FROM outward o
            LEFT JOIN inward i ON o.receipt_no = i.receipt_no AND o.item_name = i.item_name
            GROUP BY o.id
        """,
        conn,
    )
    conn.close()

    df_raw["dt_obj"] = df_raw["Date"].apply(parse_to_date_obj)
    df_filtered = df_raw[
        (df_raw["dt_obj"] >= rep_from_dt) & (df_raw["dt_obj"] <= rep_to_dt)
    ]
    if sel_lot != "ALL":
      df_filtered = df_filtered[df_filtered["Lot No."] == sel_lot]
    if sel_cs != "ALL":
      df_filtered = df_filtered[df_filtered["Cold Storage"] == sel_cs]
    if sel_item != "ALL":
      df_filtered = df_filtered[df_filtered["Item Name"] == sel_item]

    grp_col = rep_group
    df_res = (
        df_filtered.groupby(grp_col)
        .agg({
            "Lot No.": "count",
            "Outward Units": "sum",
            "Inward Units": "sum",
            "Bal. Units": "sum",
            "Bal. Weight (KG)": "sum",
        })
        .reset_index()
    )
    df_res.rename(columns={"Lot No.": "Total Lots / Entries"}, inplace=True)
    df_res["Bal. Weight (KG)"] = df_res["Bal. Weight (KG)"].round(2)

  else:
    if rep_type == "Combined Lot Ledger":
      df_res = pd.read_sql_query(
          """
                SELECT 
                    o.entry_date AS "Outward Date", o.receipt_no AS "Lot No.", 
                    o.cold_storage AS "Cold Storage", o.item_name AS "Item Name", 
                    o.unit_size AS "Unit Qty (KG)", o.qty AS "Outward Units",
                    COALESCE(SUM(i.qty), 0) AS "Inward Units",
                    (o.qty - COALESCE(SUM(i.qty), 0)) AS "Bal. Units",
                    (o.total_qty - (COALESCE(SUM(i.qty), 0) * o.unit_size)) AS "Bal. Weight (KG)",
                    CASE 
                        WHEN (o.qty - COALESCE(SUM(i.qty), 0)) <= 0 THEN 'CLEARED'
                        WHEN COALESCE(SUM(i.qty), 0) > 0 THEN 'PARTIAL'
                        ELSE 'UNTOUCHED'
                    END AS "Status"
                FROM outward o
                LEFT JOIN inward i ON o.receipt_no = i.receipt_no AND o.item_name = i.item_name
                GROUP BY o.id ORDER BY o.id DESC
            """,
          conn,
      )
      date_col = "Outward Date"
    elif rep_type == "Outward Register":
      df_res = pd.read_sql_query(
          """
                SELECT id AS "ID", entry_date AS "Date", reference_no AS "Reference No.", 
                       receipt_no AS "Lot No.", cold_storage AS "Cold Storage", 
                       item_name AS "Item Name", qty AS "Units", unit_size AS "Unit Qty (KG)", 
                       total_qty AS "Total Qty (KG)"
                FROM outward ORDER BY id DESC
            """,
          conn,
      )
      date_col = "Date"
    elif rep_type == "Inward Register":
      df_res = pd.read_sql_query(
          """
                SELECT id AS "ID", entry_date AS "Date", receipt_no AS "Lot No.", 
                       item_name AS "Item Name", qty AS "Inward Units Received"
                FROM inward ORDER BY id DESC
            """,
          conn,
      )
      date_col = "Date"
    elif rep_type == "Stock Summary":
      df_res = pd.read_sql_query(
          """
                SELECT 
                    o.receipt_no AS "Lot No.", o.cold_storage AS "Cold Storage", 
                    o.item_name AS "Item Name", o.unit_size AS "Unit Qty (KG)", 
                    o.qty AS "Outward Units", COALESCE(SUM(i.qty), 0) AS "Inward Units",
                    (o.qty - COALESCE(SUM(i.qty), 0)) AS "Bal. Units",
                    (o.total_qty - (COALESCE(SUM(i.qty), 0) * o.unit_size)) AS "Bal. Total Qty (KG)",
                    CASE 
                        WHEN (o.qty - COALESCE(SUM(i.qty), 0)) <= 0 THEN 'CLEARED'
                        WHEN COALESCE(SUM(i.qty), 0) > 0 THEN 'PARTIAL'
                        ELSE 'UNTOUCHED'
                    END AS "Status"
                FROM outward o
                LEFT JOIN inward i ON o.receipt_no = i.receipt_no AND o.item_name = i.item_name
                GROUP BY o.id ORDER BY o.receipt_no
            """,
          conn,
      )
      date_col = None
    conn.close()

    if date_col and not df_res.empty:
      df_res["dt_obj"] = df_res[date_col].apply(parse_to_date_obj)
      df_res = df_res[
          (df_res["dt_obj"] >= rep_from_dt) & (df_res["dt_obj"] <= rep_to_dt)
      ]
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
        df_res.to_csv(index=False).encode("utf-8"),
        "Custom_Report.csv",
        "text/csv",
        use_container_width=True,
    )
  with c_rep2:
    title_report = (
        f"{rep_type} (Grouped by {rep_group})"
        if rep_group != "None"
        else rep_type
    )
    pdf_rep_buf = generate_pdf(df_res, title_report)
    if pdf_rep_buf:
      st.download_button(
          "📄 Export Filtered PDF",
          pdf_rep_buf,
          "Custom_Report.pdf",
          "application/pdf",
          use_container_width=True,
      )