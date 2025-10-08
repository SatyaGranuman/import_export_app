# import_export_app.py
import streamlit as st
import pandas as pd
import os
from datetime import date, datetime, timedelta
from io import BytesIO
import matplotlib.pyplot as plt

st.set_page_config(page_title="Import-Export Tracker", layout="wide")

# ------------------------
# File paths & default cols
# ------------------------
BASE_DIR = os.path.dirname(__file__)
USERS_FILE = os.path.join(BASE_DIR, "users.csv")
PURCHASES_FILE = os.path.join(BASE_DIR, "purchases.csv")
PURCHASE_PAYMENTS_FILE = os.path.join(BASE_DIR, "purchase_payments.csv")

PURCHASE_COLS = [
    "SlNo", "Date", "Supplier", "Material", "Qty", "UOM", "UnitRate", "Total",
    "PortLoading", "PortDelivery", "PaymentOption", "ShipmentStatus",
    "ProformaInvoice", "InvoiceNo", "BLNo", "ETA", "ShippingLine",
    "NextPaymentDue", "Paid", "Due"
]

PAYMENT_COLS = ["PaymentID", "PurchaseSlNo", "Date", "Amount", "Note", "NextPaymentDue"]

# ------------------------
# Helpers: CSV ensure/load/save
# ------------------------
def ensure_csv(path, cols):
    if not os.path.exists(path) or os.stat(path).st_size == 0:
        pd.DataFrame(columns=cols).to_csv(path, index=False)

ensure_csv(USERS_FILE, ["username", "password", "role"])
ensure_csv(PURCHASES_FILE, PURCHASE_COLS)
ensure_csv(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)

# seed users if empty
_users = pd.read_csv(USERS_FILE)
if _users.empty:
    seed = pd.DataFrame([
        {"username":"admin","password":"admin123","role":"admin"},
        {"username":"user1","password":"user123","role":"user"},
        {"username":"user2","password":"user234","role":"user"},
    ])
    seed.to_csv(USERS_FILE, index=False)

def load_df(path, cols):
    try:
        df = pd.read_csv(path)
    except Exception:
        df = pd.DataFrame(columns=cols)
    # ensure columns and order
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df.reindex(columns=cols)

def save_df(df, path):
    df.to_csv(path, index=False)

# ------------------------
# Small utility funcs
# ------------------------
def next_slno(df):
    if df.empty:
        return 1
    return int(pd.to_numeric(df["SlNo"], errors="coerce").max()) + 1

def next_payment_id(df):
    if df.empty:
        return 1
    return int(pd.to_numeric(df["PaymentID"], errors="coerce").max()) + 1

def to_date_safe(val):
    if pd.isna(val) or val == "":
        return None
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None

def df_to_excel_bytes(df):
    out = BytesIO()
    df.to_excel(out, index=False)
    out.seek(0)
    return out

# ------------------------
# Business logic: payments & balances
# ------------------------
def recalc_balances(purchases_df, payments_df):
    """Return purchases_df copy with Paid and Due recalculated from payments_df."""
    p = purchases_df.copy()
    p["Total"] = pd.to_numeric(p.get("Total", 0), errors="coerce").fillna(0.0)
    p["Paid"] = 0.0
    p["Due"] = p["Total"].astype(float)
    if payments_df.empty:
        p["Paid"] = 0.0
        p["Due"] = p["Total"]
        return p
    grouped = payments_df.groupby("PurchaseSlNo")["Amount"].sum().to_dict()
    for idx, row in p.iterrows():
        sl = row["SlNo"]
        paid = float(grouped.get(sl, 0.0))
        p.at[idx, "Paid"] = round(paid, 2)
        p.at[idx, "Due"] = round(max(float(row["Total"]) - paid, 0.0), 2)
    return p

def payment_flag(row):
    """Return flag: Paid / DueSoon / Overdue"""
    if float(row["Due"]) <= 0:
        return "Paid"
    nd = to_date_safe(row.get("NextPaymentDue"))
    if nd is None:
        return "Due"
    if nd < date.today():
        return "Overdue"
    if nd <= date.today() + timedelta(days=7):
        return "DueSoon"
    return "Due"

# ------------------------
# Load data
# ------------------------
purchases = load_df(PURCHASES_FILE, PURCHASE_COLS)
payments = load_df(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)

# coerce numeric totals
purchases["Total"] = pd.to_numeric(purchases["Total"], errors="coerce").fillna(0.0)

# recalc paid/due
purchases = recalc_balances(purchases, payments)

# ------------------------
# Authentication UI
# ------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

def login_screen():
    st.title("Import-Export Tracker — Login")
    users = load_df(USERS_FILE, ["username","password","role"])
    uname = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        matched = users[(users["username"] == uname) & (users["password"] == pwd)]
        if not matched.empty:
            st.session_state.logged_in = True
            st.session_state.username = uname
            st.session_state.role = matched.iloc[0]["role"]
            st.success(f"Welcome {uname} ({st.session_state.role})")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

if not st.session_state.logged_in:
    login_screen()
    st.stop()

# Sidebar + nav
st.sidebar.markdown(f"**User:** {st.session_state.username} ({st.session_state.role})")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.experimental_rerun()

page = st.sidebar.selectbox("Menu", ["Dashboard", "Add Purchase", "Purchase Update", "Payments", "Reports", "Users (admin)"])

# ------------------------
# Dashboard
# ------------------------
if page == "Dashboard":
    st.header("📊 Dashboard")
    col1, col2 = st.columns([2,1])

    # summary KPIs
    total_purchases = purchases["Total"].sum() if not purchases.empty else 0.0
    total_paid = purchases["Paid"].sum() if not purchases.empty else 0.0
    total_due = purchases["Due"].sum() if not purchases.empty else 0.0
    col1.metric("Total Purchases", f"${total_purchases:,.2f}")
    col1.metric("Total Paid", f"${total_paid:,.2f}")
    col1.metric("Total Due", f"${total_due:,.2f}")

    # shipment status distribution
    st.subheader("Shipment Status Distribution")
    status_counts = purchases["ShipmentStatus"].value_counts().reindex(["Yet to Dispatch","Dispatched","Delayed","Delivered"], fill_value=0)
    fig1, ax1 = plt.subplots(figsize=(6,3))
    status_counts.plot(kind="bar", ax=ax1, color=["#6CACE4","#FFD166","#F29E4C","#80CFA9"])
    ax1.set_ylabel("Count")
    st.pyplot(fig1)

    # Paid vs Due by supplier
    st.subheader("Paid vs Due by Supplier")
    if not purchases.empty:
        chart_df = purchases.groupby("Supplier")[["Paid","Due"]].sum()
        fig2, ax2 = plt.subplots(figsize=(8,3))
        chart_df.plot(kind="bar", ax=ax2)
        ax2.set_ylabel("Amount")
        st.pyplot(fig2)

    # Overdue alerts
    st.subheader("Alerts: Overdue Payments & Delayed Shipments")
    # Overdue payments
    purchases["NextPaymentDue_date"] = purchases["NextPaymentDue"].apply(to_date_safe)
    overdue_payments = purchases[(purchases["Due"] > 0) & (purchases["NextPaymentDue_date"].notna()) & (purchases["NextPaymentDue_date"] < date.today())]
    if not overdue_payments.empty:
        st.warning(f"⚠️ {len(overdue_payments)} overdue payments. See table below.")
        st.dataframe(overdue_payments[["SlNo","Supplier","Total","Paid","Due","NextPaymentDue"]])
    else:
        st.success("No overdue payments.")

    # Delayed shipments: ETA passed and not delivered
    purchases["ETA_date"] = purchases["ETA"].apply(to_date_safe)
    delayed = purchases[(purchases["ShipmentStatus"].isin(["Dispatched","Yet to Dispatch","Delayed"])) & (purchases["ETA_date"].notna()) & (purchases["ETA_date"] < date.today()) & (purchases["ShipmentStatus"] != "Delivered")]
    if not delayed.empty:
        st.warning(f"🚢 {len(delayed)} shipments delayed (ETA passed).")
        st.dataframe(delayed[["SlNo","Supplier","Material","ShipmentStatus","ETA"]])
    else:
        st.info("No delayed shipments.")

# ------------------------
# Add Purchase
# ------------------------
elif page == "Add Purchase":
    st.header("➕ Add Purchase")
    with st.form("add_purchase"):
        dt = st.date_input("Purchase Date", value=date.today())
        supplier = st.text_input("Supplier")
        material = st.text_input("Material / Short Text")
        qty = st.number_input("Qty (Net WT)", min_value=0.0, format="%.3f")
        uom = st.selectbox("UOM", ["Metric Ton","Kg","Pieces"])
        unit_rate = st.number_input("Unit Rate", min_value=0.0, format="%.2f")
        total = round(qty * unit_rate, 2)
        port_loading = st.text_input("Port of Loading")
        port_delivery = st.text_input("Port of Delivery")
        payment_option = st.selectbox("Payment Option", ["10% advance","20% advance","30% advance","100% advance"])
        submitted = st.form_submit_button("Save Purchase")
        if submitted:
            # load fresh
            purchases = load_df(PURCHASES_FILE, PURCHASE_COLS)
            payments = load_df(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)
            sl = next_slno(purchases)
            new = {
                "SlNo": sl,
                "Date": dt.isoformat(),
                "Supplier": supplier,
                "Material": material,
                "Qty": qty,
                "UOM": uom,
                "UnitRate": unit_rate,
                "Total": total,
                "PortLoading": port_loading,
                "PortDelivery": port_delivery,
                "PaymentOption": payment_option,
                "ShipmentStatus": "Yet to Dispatch",
                "ProformaInvoice": "",
                "InvoiceNo": "",
                "BLNo": "",
                "ETA": "",
                "ShippingLine": "",
                "NextPaymentDue": "",
                "Paid": 0.0,
                "Due": total
            }
            new_df = pd.DataFrame([new], columns=PURCHASE_COLS)
            purchases = pd.concat([purchases, new_df], ignore_index=True).reindex(columns=PURCHASE_COLS)
            save_df(purchases, PURCHASES_FILE)

            # record initial advance payment automatically
            percent = {"10% advance":0.1,"20% advance":0.2,"30% advance":0.3,"100% advance":1.0}[payment_option]
            advance_amount = round(total * percent, 2)
            if advance_amount > 0:
                payments = load_df(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)
                pid = next_payment_id(payments)
                payrow = {"PaymentID": pid, "PurchaseSlNo": sl, "Date": date.today().isoformat(), "Amount": advance_amount, "Note": "Initial advance", "NextPaymentDue": ""}
                payments = pd.concat([payments, pd.DataFrame([payrow], columns=PAYMENT_COLS)], ignore_index=True).reindex(columns=PAYMENT_COLS)
                save_df(payments, PURCHASE_PAYMENTS_FILE)
            st.success(f"Purchase {sl} created. Initial advance recorded: {advance_amount:.2f}")
            st.experimental_rerun()

# ------------------------
# Purchase Update (Shipment & Payment in one branch)
# ------------------------
elif page == "Purchase Update":
    st.header("🔧 Purchase Update — Shipment & Payment")

    purchases = load_df(PURCHASES_FILE, PURCHASE_COLS)
    payments = load_df(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)
    purchases = recalc_balances(purchases, payments)

    if purchases.empty:
        st.info("No purchases to update.")
    else:
        sl_choices = list(purchases["SlNo"].astype(int))
        chosen_sl = st.selectbox("Select Purchase SlNo", sl_choices)
        idx = purchases.index[purchases["SlNo"] == chosen_sl][0]
        record = purchases.loc[idx]

        st.subheader(f"Purchase {chosen_sl} — {record['Supplier']} / {record['Material']}")
        cols_left, cols_right = st.columns(2)
        with cols_left:
            st.write("**Totals**")
            st.write(f"Total: ${record['Total']:.2f}")
            st.write(f"Paid: ${record['Paid']:.2f}")
            st.write(f"Due: ${record['Due']:.2f}")
            # progress bar (0..100)
            pct = 0 if record["Total"] == 0 else int(record["Paid"] / record["Total"] * 100)
            st.progress(min(max(pct,0),100))
            flag = payment_flag(record)
            if flag == "Paid":
                st.success("Status: Paid")
            elif flag == "Overdue":
                st.error("Status: Overdue")
            elif flag == "DueSoon":
                st.warning("Status: Due Soon")
            else:
                st.info("Status: Due")

        with cols_right:
            st.write("**Shipment**")
            st.write(f"Shipment Status: **{record['ShipmentStatus']}**")
            st.write(f"Invoice No: {record.get('InvoiceNo','')}")
            st.write(f"BL No: {record.get('BLNo','')}")
            st.write(f"ETA: {record.get('ETA','')}")
            st.write(f"Shipping Line: {record.get('ShippingLine','')}")
            st.write(f"Port Loading: {record.get('PortLoading','')}")
            st.write(f"Port Delivery: {record.get('PortDelivery','')}")
            st.write(f"Next Payment Due: {record.get('NextPaymentDue','')}")

        st.markdown("---")
        tab_ship, tab_pay = st.tabs(["Shipment Update", "Payment Update"])

        # ---- Shipment Update ----
        with tab_ship:
            st.markdown("### Shipment Update")
            current_status = record["ShipmentStatus"]
            st.write(f"Current: **{current_status}**")
            new_status = st.selectbox("Set Shipment Status", ["Yet to Dispatch","Dispatched","Delayed","Delivered"], index=["Yet to Dispatch","Dispatched","Delayed","Delivered"].index(current_status))

            if new_status == "Dispatched" and current_status != "Dispatched":
                st.info("Please enter dispatch details (Invoice, BL, ETA, Shipping Line, Ports)")
                inv = st.text_input("Invoice Number", value=record.get("InvoiceNo",""))
                bl = st.text_input("Bill of Lading Number", value=record.get("BLNo",""))
                eta = st.date_input("ETA (expected delivery)", value=to_date_safe(record.get("ETA")) or date.today())
                shipline = st.text_input("Shipping Line", value=record.get("ShippingLine",""))
                pol = st.text_input("Port of Loading", value=record.get("PortLoading",""))
                pod = st.text_input("Port of Delivery", value=record.get("PortDelivery",""))

                if st.button("Confirm Dispatch"):
                    if not inv or not bl:
                        st.error("Invoice No and BL No are required to confirm dispatch.")
                    else:
                        purchases.at[idx, "ShipmentStatus"] = "Dispatched"
                        purchases.at[idx, "InvoiceNo"] = inv
                        purchases.at[idx, "BLNo"] = bl
                        purchases.at[idx, "ETA"] = eta.isoformat()
                        purchases.at[idx, "ShippingLine"] = shipline
                        purchases.at[idx, "PortLoading"] = pol
                        purchases.at[idx, "PortDelivery"] = pod
                        save_df(purchases, PURCHASES_FILE)
                        st.success("Shipment set to Dispatched and details saved.")
                        st.experimental_rerun()

            elif new_status == "Delivered" and current_status != "Delivered":
                if st.button("Mark Delivered"):
                    purchases.at[idx, "ShipmentStatus"] = "Delivered"
                    save_df(purchases, PURCHASES_FILE)
                    st.success("Shipment marked Delivered.")
                    st.experimental_rerun()
            else:
                if st.button("Save Shipment Status (no extra details)"):
                    purchases.at[idx, "ShipmentStatus"] = new_status
                    save_df(purchases, PURCHASES_FILE)
                    st.success("Shipment status saved.")
                    st.experimental_rerun()

        # ---- Payment Update ----
        with tab_pay:
            st.markdown("### Payment Update")
            st.write(f"Total: ${record['Total']:.2f} | Paid: ${record['Paid']:.2f} | Due: ${record['Due']:.2f}")
            hist = payments[payments["PurchaseSlNo"] == chosen_sl].copy()
            if hist.empty:
                st.info("No payments recorded yet.")
            else:
                st.write("Payment History")
                st.dataframe(hist.sort_values("Date"))

            if float(record["Due"]) > 0:
                with st.form("record_payment"):
                    pay_date = st.date_input("Payment Date", value=date.today())
                    max_val = float(record["Due"])
                    amount = st.number_input("Amount", min_value=0.0, max_value=max_val, format="%.2f")
                    note = st.text_input("Note (optional)")
                    next_due = st.date_input("Next Payment Due (optional)", value=to_date_safe(record.get("NextPaymentDue")) or (date.today() + timedelta(days=30)))
                    submit_payment = st.form_submit_button("Record Payment")
                    if submit_payment:
                        if amount <= 0:
                            st.error("Enter amount greater than 0")
                        else:
                            payments = load_df(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)
                            pid = next_payment_id(payments)
                            new_pay = {
                                "PaymentID": pid,
                                "PurchaseSlNo": chosen_sl,
                                "Date": pay_date.isoformat(),
                                "Amount": round(amount,2),
                                "Note": note,
                                "NextPaymentDue": next_due.isoformat() if next_due else ""
                            }
                            payments = pd.concat([payments, pd.DataFrame([new_pay], columns=PAYMENT_COLS)], ignore_index=True).reindex(columns=PAYMENT_COLS)
                            save_df(payments, PURCHASE_PAYMENTS_FILE)

                            # update NextPaymentDue on purchase
                            purchases.at[idx, "NextPaymentDue"] = next_due.isoformat() if next_due else ""
                            save_df(purchases, PURCHASES_FILE)

                            st.success(f"Payment recorded: {amount:.2f}")
                            st.experimental_rerun()
            else:
                st.success("Fully paid — no due amount.")

            # delete payment
            st.markdown("#### Delete payment (if wrong entry)")
            pay_hist = payments[payments["PurchaseSlNo"] == chosen_sl]
            if not pay_hist.empty:
                del_choice = st.selectbox("Select PaymentID to delete", pay_hist["PaymentID"].tolist())
                if st.button("Delete Payment"):
                    payments = payments[payments["PaymentID"] != del_choice]
                    save_df(payments, PURCHASE_PAYMENTS_FILE)
                    st.success("Payment deleted")
                    st.experimental_rerun()

# ------------------------
# Payments overview & exports
# ------------------------
elif page == "Payments":
    st.header("Payments Overview & Export")
    payments = load_df(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)
    if payments.empty:
        st.info("No payments recorded.")
    else:
        st.dataframe(payments.sort_values(["PurchaseSlNo","Date"]))
        b = df_to_excel_bytes(payments)
        st.download_button("Download Payments Excel", data=b, file_name="purchase_payments.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ------------------------
# Reports
# ------------------------
elif page == "Reports":
    st.header("Reports")
    st.subheader("Purchases")
    purchases = load_df(PURCHASES_FILE, PURCHASE_COLS)
    purchases = recalc_balances(purchases, payments)
    st.dataframe(purchases.sort_values("SlNo"))
    st.download_button("Download Purchases Excel", data=df_to_excel_bytes(purchases), file_name="purchases.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ------------------------
# Users admin
# ------------------------
elif page == "Users (admin)":
    if st.session_state.role != "admin":
        st.error("Only admin can manage users.")
    else:
        st.header("User Management (Admin)")
        users = load_df(USERS_FILE, ["username","password","role"])
        st.dataframe(users)
        with st.form("add_user"):
            nu = st.text_input("Username")
            npwd = st.text_input("Password", type="password")
            nrole = st.selectbox("Role", ["user","admin"])
            if st.form_submit_button("Create User"):
                if nu.strip() == "" or npwd.strip() == "":
                    st.error("Username & password required")
                elif nu in users["username"].values:
                    st.error("Username exists")
                else:
                    users = pd.concat([users, pd.DataFrame([{"username":nu,"password":npwd,"role":nrole}])], ignore_index=True)
                    save_df(users, USERS_FILE)
                    st.success("User created")
                    st.experimental_rerun()
