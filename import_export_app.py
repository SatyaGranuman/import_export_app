import streamlit as st
import pandas as pd
import os

# -----------------------------
# FILE PATHS
# -----------------------------
PURCHASE_FILE = "purchases.xlsx"
SALES_FILE = "sales.xlsx"
ACCOUNT_FILE = "accounts.xlsx"

# -----------------------------
# LOAD OR CREATE DATA
# -----------------------------
def load_or_create(file, columns):
    if os.path.exists(file):
        return pd.read_excel(file)
    else:
        return pd.DataFrame(columns=columns)

purchase_df = load_or_create(PURCHASE_FILE, ["PurchaseID", "Supplier", "Item", "Quantity", "UnitPrice", "Total"])
sales_df = load_or_create(SALES_FILE, ["SalesID", "Customer", "Item", "Quantity", "UnitPrice", "Total"])
account_df = load_or_create(ACCOUNT_FILE, ["Type", "Description", "Amount"])

# -----------------------------
# SAVE DATA
# -----------------------------
def save_data():
    purchase_df.to_excel(PURCHASE_FILE, index=False)
    sales_df.to_excel(SALES_FILE, index=False)
    account_df.to_excel(ACCOUNT_FILE, index=False)

# -----------------------------
# ACCOUNTING LOGIC
# -----------------------------
def update_accounting(entry_type, description, amount):
    global account_df
    new_row = pd.DataFrame([[entry_type, description, amount]], columns=account_df.columns)
    account_df = pd.concat([account_df, new_row], ignore_index=True)
    save_data()

# -----------------------------
# STREAMLIT APP
# -----------------------------
st.set_page_config(page_title="Import-Export ERP", layout="wide")
st.title("🌍 Import–Export Business Manager")

tab1, tab2, tab3 = st.tabs(["📦 Purchases", "💼 Sales", "📊 Accounting"])

# -----------------------------
# PURCHASE TAB
# -----------------------------
with tab1:
    st.header("Purchase Management")

    with st.form("add_purchase_form"):
        col1, col2, col3, col4, col5 = st.columns(5)
        pid = col1.text_input("Purchase ID")
        supplier = col2.text_input("Supplier")
        item = col3.text_input("Item")
        qty = col4.number_input("Quantity", min_value=1, step=1)
        price = col5.number_input("Unit Price", min_value=0.0, step=0.1)
        submitted = st.form_submit_button("➕ Add Purchase")

        if submitted:
            total = qty * price
            new_row = pd.DataFrame([[pid, supplier, item, qty, price, total]], columns=purchase_df.columns)
            purchase_df = pd.concat([purchase_df, new_row], ignore_index=True)
            update_accounting("Expense", f"Purchase {item} from {supplier}", total)
            save_data()
            st.success(f"Added purchase of {item} from {supplier} (Total ₹{total:.2f})")

    st.subheader("📄 Purchase Records")
    st.dataframe(purchase_df, use_container_width=True)

# -----------------------------
# SALES TAB
# -----------------------------
with tab2:
    st.header("Sales Management")

    with st.form("add_sales_form"):
        col1, col2, col3, col4, col5 = st.columns(5)
        sid = col1.text_input("Sales ID")
        customer = col2.text_input("Customer")
        item = col3.text_input("Item")
        qty = col4.number_input("Quantity", min_value=1, step=1)
        price = col5.number_input("Unit Price", min_value=0.0, step=0.1)
        submitted = st.form_submit_button("➕ Add Sale")

        if submitted:
            total = qty * price
            new_row = pd.DataFrame([[sid, customer, item, qty, price, total]], columns=sales_df.columns)
            sales_df = pd.concat([sales_df, new_row], ignore_index=True)
            update_accounting("Income", f"Sale {item} to {customer}", total)
            save_data()
            st.success(f"Added sale of {item} to {customer} (Total ₹{total:.2f})")

    st.subheader("📄 Sales Records")
    st.dataframe(sales_df, use_container_width=True)

# -----------------------------
# ACCOUNTING TAB
# -----------------------------
with tab3:
    st.header("Accounting & Profit / Loss Summary")
    st.subheader("💰 Ledger Entries")
    st.dataframe(account_df, use_container_width=True)

    income = account_df[account_df['Type'] == 'Income']['Amount'].sum()
    expense = account_df[account_df['Type'] == 'Expense']['Amount'].sum()
    profit = income - expense

    st.metric("Total Income", f"₹{income:,.2f}")
    st.metric("Total Expense", f"₹{expense:,.2f}")
    st.metric("Net Profit / Loss", f"₹{profit:,.2f}", delta_color="inverse")

    if st.button("💾 Save All Data"):
        save_data()
        st.success("All data saved successfully!")
