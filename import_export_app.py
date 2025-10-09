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
SALES_FILE = os.path.join(BASE_DIR, "sales.csv")

PURCHASE_COLS = [
    "SlNo", "Date", "Supplier", "Material", "Qty", "UOM", "UnitRate", "Total",
    "PortLoading", "PortDelivery", "PaymentOption", "ShipmentStatus",
    "ProformaInvoice", "InvoiceNo", "BLNo", "ETA", "ShippingLine",
    "NextPaymentDue", "Paid", "Due"
]

PAYMENT_COLS = ["PaymentID", "PurchaseSlNo", "Date", "Amount", "Note", "NextPaymentDue"]

SALES_COLS = [
    "SlNo", "Date", "Customer", "Material", "LinkedPurchase", "Qty", "UOM",
    "UnitRate", "Total", "PurchaseRate", "ProfitPerUnit", "TotalProfit",
    "ShipmentStatus", "InvoiceNo", "BLNo", "ETA", "ShippingLine", "Paid", "Due"
]

# ------------------------
# Helpers: CSV ensure/load/save
# ------------------------
def ensure_csv(path, cols):
    if not os.path.exists(path) or os.stat(path).st_size == 0:
        pd.DataFrame(columns=cols).to_csv(path, index=False)

ensure_csv(USERS_FILE, ["username", "password", "role"])
ensure_csv(PURCHASES_FILE, PURCHASE_COLS)
ensure_csv(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)
ensure_csv(SALES_FILE, SALES_COLS)

# seed users if empty
_users = pd.read_csv(USERS_FILE)
if _users.empty:
    seed = pd.DataFrame([
        {"username": "admin", "password": "admin123", "role": "admin"},
        {"username": "user1", "password": "user123", "role": "user"},
        {"username": "user2", "password": "user234", "role": "user"},
    ])
    seed.to_csv(USERS_FILE, index=False)

def load_df(path, cols):
    try:
        df = pd.read_csv(path)
    except Exception:
        df = pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df.reindex(columns=cols)

def save_df(df, path):
    df.to_csv(path, index=False)

# ------------------------
# Utility functions
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
    p = purchases_df.copy()
    p["Total"] = pd.to_numeric(p.get("Total", 0), errors="coerce").fillna(0.0)
    p["Paid"] = 0.0
    p["Due"] = p["Total"].astype(float)
    if payments_df.empty:
        return p
    grouped = payments_df.groupby("PurchaseSlNo")["Amount"].sum().to_dict()
    for idx, row in p.iterrows():
        sl = row["SlNo"]
        paid = float(grouped.get(sl, 0.0))
        p.at[idx, "Paid"] = round(paid, 2)
        p.at[idx, "Due"] = round(max(float(row["Total"]) - paid, 0.0), 2)
    return p

# ------------------------
# Load data
# ------------------------
purchases = load_df(PURCHASES_FILE, PURCHASE_COLS)
payments = load_df(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)
purchases["Total"] = pd.to_numeric(purchases["Total"], errors="coerce").fillna(0.0)
purchases = recalc_balances(purchases, payments)

# ------------------------
# Authentication
# ------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

def login_screen():
    st.title("Import-Export Tracker — Login")
    users = load_df(USERS_FILE, ["username", "password", "role"])
    uname = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        matched = users[(users["username"] == uname) & (users["password"] == pwd)]
        if not matched.empty:
            st.session_state.logged_in = True
            st.session_state.username = uname
            st.session_state.role = matched.iloc[0]["role"]
            st.success(f"Welcome {uname} ({st.session_state.role})")
            st.rerun()
        else:
            st.error("Invalid credentials")

if not st.session_state.logged_in:
    login_screen()
    st.stop()

st.sidebar.markdown(f"**User:** {st.session_state.username} ({st.session_state.role})")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

page = st.sidebar.selectbox(
    "Menu",
    ["Dashboard", "Add Purchase", "Purchase Update",
     "Add Sale / Sales Update", "Payments", "Reports", "Users (admin)"]
)

# ------------------------
# Dashboard
# ------------------------
if page == "Dashboard":
    st.header("📊 Dashboard")
    total_purchases = purchases["Total"].sum() if not purchases.empty else 0.0
    total_paid = purchases["Paid"].sum() if not purchases.empty else 0.0
    total_due = purchases["Due"].sum() if not purchases.empty else 0.0

    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Total Purchases", f"${total_purchases:,.2f}")
    with col2: st.metric("Total Paid (Purchases)", f"${total_paid:,.2f}")
    with col3: st.metric("Total Due (Purchases)", f"${total_due:,.2f}")

    st.subheader("Purchase Shipment Status")
    status_counts = purchases["ShipmentStatus"].value_counts().reindex(
        ["Yet to Dispatch","Dispatched","Delayed","Delivered"], fill_value=0)
    fig1, ax1 = plt.subplots(figsize=(6,3))
    status_counts.plot(kind="bar", ax=ax1)
    ax1.set_ylabel("Count")
    st.pyplot(fig1)

    # ---- Sales Summary ----
    st.subheader("Sales Summary & Profit")
    sales = load_df(SALES_FILE, SALES_COLS)
    if not sales.empty:
        total_sales = pd.to_numeric(sales["Total"], errors="coerce").fillna(0.0).sum()
        total_profit = pd.to_numeric(sales["TotalProfit"], errors="coerce").fillna(0.0).sum()

        col4, col5 = st.columns(2)
        with col4: st.metric("Total Sales", f"${total_sales:,.2f}")
        with col5: st.metric("Total Profit", f"${total_profit:,.2f}")

        top_profit = (sales.groupby("Material")["TotalProfit"]
                      .sum().sort_values(ascending=False).head(5))
        fig2, ax2 = plt.subplots(figsize=(6,3))
        top_profit.plot(kind="bar", ax=ax2)
        ax2.set_ylabel("Profit ($)")
        st.pyplot(fig2)
    else:
        st.info("No sales recorded yet.")

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
        payment_option = st.selectbox(
            "Payment Option", ["10% advance","20% advance","30% advance","100% advance"]
        )
        submitted = st.form_submit_button("Save Purchase")
        if submitted:
            purchases = load_df(PURCHASES_FILE, PURCHASE_COLS)
            payments = load_df(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)
            sl = next_slno(purchases)
            new = {
                "SlNo": sl, "Date": dt.isoformat(), "Supplier": supplier, "Material": material,
                "Qty": qty, "UOM": uom, "UnitRate": unit_rate, "Total": total,
                "PortLoading": port_loading, "PortDelivery": port_delivery,
                "PaymentOption": payment_option, "ShipmentStatus": "Yet to Dispatch",
                "ProformaInvoice": "", "InvoiceNo": "", "BLNo": "", "ETA": "",
                "ShippingLine": "", "NextPaymentDue": "", "Paid": 0.0, "Due": total
            }
            new_df = pd.DataFrame([new], columns=PURCHASE_COLS)
            purchases = pd.concat([purchases, new_df], ignore_index=True)
            save_df(purchases, PURCHASES_FILE)

            percent = {"10% advance":0.1,"20% advance":0.2,"30% advance":0.3,"100% advance":1.0}[payment_option]
            advance_amount = round(total * percent, 2)
            if advance_amount > 0:
                payments = load_df(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)
                pid = next_payment_id(payments)
                payrow = {
                    "PaymentID": pid, "PurchaseSlNo": sl, "Date": date.today().isoformat(),
                    "Amount": advance_amount, "Note": "Initial advance", "NextPaymentDue": ""
                }
                payments = pd.concat([payments, pd.DataFrame([payrow], columns=PAYMENT_COLS)], ignore_index=True)
                save_df(payments, PURCHASE_PAYMENTS_FILE)

            st.success(f"Purchase {sl} created. Initial advance recorded: {advance_amount:.2f}")
            st.rerun()

# ------------------------
# Purchase Update
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
        tab_ship, tab_pay = st.tabs(["Shipment Update", "Payment Update"])

        # Shipment Update
        with tab_ship:
            st.markdown("### Shipment Update")
            status_options = ["Yet to Dispatch", "Dispatched", "Delayed", "Delivered"]
            current_status = record["ShipmentStatus"]
            if pd.isna(current_status) or current_status not in status_options:
                current_status = "Yet to Dispatch"
            new_status = st.selectbox("Set Shipment Status", status_options,
                                      index=status_options.index(current_status))

            if new_status == "Dispatched" and current_status != "Dispatched":
                st.info("Enter dispatch details:")
                inv = st.text_input("Invoice No", value=record.get("InvoiceNo",""))
                bl = st.text_input("BL No", value=record.get("BLNo",""))
                eta = st.date_input("ETA", value=to_date_safe(record.get("ETA")) or date.today())
                shipline = st.text_input("Shipping Line", value=record.get("ShippingLine",""))
                pol = st.text_input("Port Loading", value=record.get("PortLoading",""))
                pod = st.text_input("Port Delivery", value=record.get("PortDelivery",""))
                if st.button("Save Dispatch"):
                    if not inv or not bl:
                        st.error("Invoice & BL required.")
                    else:
                        purchases.at[idx, "ShipmentStatus"] = "Dispatched"
                        purchases.at[idx, "InvoiceNo"] = inv
                        purchases.at[idx, "BLNo"] = bl
                        purchases.at[idx, "ETA"] = eta.isoformat()
                        purchases.at[idx, "ShippingLine"] = shipline
                        purchases.at[idx, "PortLoading"] = pol
                        purchases.at[idx, "PortDelivery"] = pod
                        save_df(purchases, PURCHASES_FILE)
                        st.success("Shipment marked as Dispatched.")
                        st.rerun()

            elif new_status == "Delivered" and current_status != "Delivered":
                if st.button("Mark Delivered"):
                    purchases.at[idx, "ShipmentStatus"] = "Delivered"
                    save_df(purchases, PURCHASES_FILE)
                    st.success("Shipment marked Delivered.")
                    st.rerun()
            elif new_status != current_status:
                if st.button("Save Status"):
                    purchases.at[idx, "ShipmentStatus"] = new_status
                    save_df(purchases, PURCHASES_FILE)
                    st.success(f"Status updated to {new_status}.")
                    st.rerun()

        # Payment Update
        with tab_pay:
            st.markdown("### Payment Update")
            hist = payments[payments["PurchaseSlNo"] == chosen_sl]
            if not hist.empty:
                st.dataframe(hist.sort_values("Date"))
            if float(record["Due"]) > 0:
                with st.form("record_payment"):
                    pay_date = st.date_input("Payment Date", value=date.today())
                    amount = st.number_input("Amount", min_value=0.0, max_value=float(record["Due"]), format="%.2f")
                    note = st.text_input("Note (optional)")
                    next_due = st.date_input(
                        "Next Payment Due",
                        value=to_date_safe(record.get("NextPaymentDue")) or (date.today()+timedelta(days=30))
                    )
                    submit = st.form_submit_button("Record Payment")
                    if submit:
                        if amount <= 0:
                            st.error("Enter valid amount.")
                        else:
                            payments = load_df(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)
                            pid = next_payment_id(payments)
                            pay = {
                                "PaymentID": pid, "PurchaseSlNo": chosen_sl, "Date": pay_date.isoformat(),
                                "Amount": round(amount,2), "Note": note, "NextPaymentDue": next_due.isoformat()
                            }
                            payments = pd.concat([payments, pd.DataFrame([pay])], ignore_index=True)
                            save_df(payments, PURCHASE_PAYMENTS_FILE)
                            purchases.at[idx, "NextPaymentDue"] = next_due.isoformat()
                            save_df(purchases, PURCHASES_FILE)
                            st.success(f"Payment {amount:.2f} saved.")
                            st.rerun()
            else:
                st.success("Fully paid — no due amount.")

# ------------------------
# Sales Module
# ------------------------
elif page == "Add Sale / Sales Update":
    st.header("💰 Sales Module — Add & Update")

    purchases = load_df(PURCHASES_FILE, PURCHASE_COLS)
    sales = load_df(SALES_FILE, SALES_COLS)

    tab_add, tab_update = st.tabs(["Add Sale", "Sales Update"])

    # Add Sale
    with tab_add:
        with st.form("add_sale"):
            sale_date = st.date_input("Sale Date", value=date.today())
            customer = st.text_input("Customer Name")
            material = st.text_input("Material / Short Text")

            if purchases.empty:
                st.warning("No purchases available to link. Please add a purchase first.")
                st.form_submit_button("Save Sale", disabled=True)
            else:
                linked_purchase = st.selectbox(
                    "Linked Purchase (choose purchase to base cost)",
                    options=[f"{int(r['SlNo'])} - {r['Material']} ({r['Supplier']})" for _, r in purchases.iterrows()]
                )
                linked_sl = int(linked_purchase.split(" - ")[0])
                purchase_row = purchases[purchases["SlNo"] == linked_sl].iloc[0]
                purchase_rate = float(purchase_row["UnitRate"])

                qty = st.number_input("Quantity", min_value=0.0, format="%.3f")
                uom = st.selectbox("UOM", ["Metric Ton", "Kg", "Pieces"])
                sale_rate = st.number_input("Sale Rate", min_value=0.0, format="%.2f")
                total = round(qty * sale_rate, 2)
                profit_per_unit = round(sale_rate - purchase_rate, 2)
                total_profit = round(profit_per_unit * qty, 2)

                st.info(f"💹 Profit per unit: {profit_per_unit:.2f} | Total Profit: {total_profit:.2f}")

                submitted = st.form_submit_button("Save Sale")
                if submitted:
                    sales = load_df(SALES_FILE, SALES_COLS)
                    sl = next_slno(sales)
                    new_sale = {
                        "SlNo": sl,
                        "Date": sale_date.isoformat(),
                        "Customer": customer,
                        "Material": material,
                        "LinkedPurchase": linked_sl,
                        "Qty": qty,
                        "UOM": uom,
                        "UnitRate": sale_rate,
                        "Total": total,
                        "PurchaseRate": purchase_rate,
                        "ProfitPerUnit": profit_per_unit,
                        "TotalProfit": total_profit,
                        "ShipmentStatus": "Yet to Dispatch",
                        "InvoiceNo": "",
                        "BLNo": "",
                        "ETA": "",
                        "ShippingLine": "",
                        "Paid": 0.0,
                        "Due": total
                    }
                    sales = pd.concat([sales, pd.DataFrame([new_sale], columns=SALES_COLS)], ignore_index=True)
                    save_df(sales, SALES_FILE)
                    st.success(f"Sale {sl} added. Profit: ${total_profit:.2f}")
                    st.rerun()

    # Sales Update
    with tab_update:
        sales = load_df(SALES_FILE, SALES_COLS)
        if sales.empty:
            st.info("No sales available.")
        else:
            sale_sl_choices = list(sales["SlNo"].astype(int))
            chosen_sale_sl = st.selectbox("Select Sale SlNo", sale_sl_choices)
            sidx = sales.index[sales["SlNo"] == chosen_sale_sl][0]
            srecord = sales.loc[sidx]

            st.subheader(f"Sale {chosen_sale_sl} — {srecord['Customer']} / {srecord['Material']}")
            st.write(f"**Total:** ${float(srecord['Total']):,.2f}  |  **Profit:** ${float(srecord['TotalProfit']):,.2f}")

            stab1, stab2 = st.tabs(["Shipment Update", "Payment Update"])

            with stab1:
                status_options = ["Yet to Dispatch", "Dispatched", "Delivered"]
                current_status = srecord["ShipmentStatus"] if srecord["ShipmentStatus"] in status_options else "Yet to Dispatch"
                new_status = st.selectbox("Shipment Status", status_options,
                                          index=status_options.index(current_status))

                if new_status == "Dispatched" and current_status != "Dispatched":
                    st.info("Enter dispatch details:")
                    sinv = st.text_input("Invoice No", value=srecord.get("InvoiceNo",""))
                    sbl = st.text_input("BL No", value=srecord.get("BLNo",""))
                    seta = st.date_input("ETA", value=to_date_safe(srecord.get("ETA")) or date.today())
                    sline = st.text_input("Shipping Line", value=srecord.get("ShippingLine",""))
                    if st.button("Save Dispatch (Sales)"):
                        if not sinv or not sbl:
                            st.error("Invoice & BL required.")
                        else:
                            sales.at[sidx, "ShipmentStatus"] = "Dispatched"
                            sales.at[sidx, "InvoiceNo"] = sinv
                            sales.at[sidx, "BLNo"] = sbl
                            sales.at[sidx, "ETA"] = seta.isoformat()
                            sales.at[sidx, "ShippingLine"] = sline
                            save_df(sales, SALES_FILE)
                            st.success("Sale marked as Dispatched.")
                            st.rerun()

                elif new_status == "Delivered" and current_status != "Delivered":
                    if st.button("Mark Delivered (Sales)"):
                        sales.at[sidx, "ShipmentStatus"] = "Delivered"
                        save_df(sales, SALES_FILE)
                        st.success("Sale marked Delivered.")
                        st.rerun()
                elif new_status != current_status:
                    if st.button("Save Status (Sales)"):
                        sales.at[sidx, "ShipmentStatus"] = new_status
                        save_df(sales, SALES_FILE)
                        st.success(f"Sale status updated to {new_status}.")
                        st.rerun()

            with stab2:
                st.caption("Sales payments (simple tracker).")
                # lightweight inline tracker; not mixing with purchase payments
                shist = sales.loc[[sidx], ["Date", "Customer", "Total", "Paid", "Due"]]
                st.dataframe(shist)
                due_amt = float(pd.to_numeric(srecord["Due"], errors="coerce").fillna(0.0))
                if due_amt > 0:
                    with st.form("record_sale_payment"):
                        spay_date = st.date_input("Payment Date", value=date.today(), key="sale_pay_date")
                        samount = st.number_input("Amount", min_value=0.0, max_value=due_amt, format="%.2f")
                        ssubmit = st.form_submit_button("Record Sale Payment")
                        if ssubmit:
                            new_paid = round(float(srecord["Paid"] or 0) + samount, 2)
                            new_due = round(float(srecord["Total"]) - new_paid, 2)
                            if new_due < 0:
                                st.error("Payment exceeds total.")
                            else:
                                sales.at[sidx, "Paid"] = new_paid
                                sales.at[sidx, "Due"] = max(new_due, 0.0)
                                save_df(sales, SALES_FILE)
                                st.success(f"Recorded ${samount:.2f}. New due: ${max(new_due,0):.2f}")
                                st.rerun()
                else:
                    st.success("Fully paid — no due amount.")

# ------------------------
# Payments (Purchases only)
# ------------------------
elif page == "Payments":
    st.header("💳 Payments — Purchases")
    purchases = load_df(PURCHASES_FILE, PURCHASE_COLS)
    payments = load_df(PURCHASE_PAYMENTS_FILE, PAYMENT_COLS)
    purchases = recalc_balances(purchases, payments)

    if purchases.empty:
        st.info("No purchases available.")
    else:
        st.dataframe(purchases[["SlNo","Supplier","Material","Total","Paid","Due","NextPaymentDue","ShipmentStatus"]])
        st.subheader("All Purchase Payments")
        st.dataframe(payments.sort_values("Date") if not payments.empty else payments)

        st.download_button(
            "Download Payments (Excel)",
            data=df_to_excel_bytes(payments if not payments.empty else pd.DataFrame(columns=PAYMENT_COLS)),
            file_name="purchase_payments.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ------------------------
# Reports (basic)
# ------------------------
elif page == "Reports":
    st.header("📄 Reports")
    purchases = load_df(PURCHASES_FILE, PURCHASE_COLS)
    sales = load_df(SALES_FILE, SALES_COLS)

    colA, colB = st.columns(2)
    with colA:
        st.subheader("Purchases (All)")
        st.dataframe(purchases)
        st.download_button(
            "Download Purchases (Excel)",
            data=df_to_excel_bytes(purchases),
            file_name="purchases.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with colB:
        st.subheader("Sales (All)")
        st.dataframe(sales)
        st.download_button(
            "Download Sales (Excel)",
            data=df_to_excel_bytes(sales),
            file_name="sales.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ------------------------
# Users admin
# ------------------------
elif page == "Users (admin)":
    if st.session_state.role != "admin":
        st.error("Only admin can manage users.")
    else:
        st.header("User Management (Admin)")
        users = load_df(USERS_FILE, ["username", "password", "role"])
        st.dataframe(users)
        with st.form("add_user"):
            nu = st.text_input("Username")
            npwd = st.text_input("Password", type="password")
            nrole = st.selectbox("Role", ["user", "admin"])
            if st.form_submit_button("Create User"):
                if not nu.strip() or not npwd.strip():
                    st.error("Username & password required")
                elif nu in users["username"].values:
                    st.error("Username exists")
                else:
                    users = pd.concat([
                        users, pd.DataFrame([{"username": nu, "password": npwd, "role": nrole}])
                    ], ignore_index=True)
                    save_df(users, USERS_FILE)
                    st.success("User created.")
                    st.rerun()
