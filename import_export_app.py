import streamlit as st
import pandas as pd
import os

# ------------------------
# File paths
# ------------------------
users_file = "users.xlsx"
purchases_file = "purchases.xlsx"
sales_file = "sales.xlsx"

# ------------------------
# Initialize default users
# ------------------------
default_users = {
    "admin": {"password": "admin123", "role": "admin"},
    "sales": {"password": "sales123", "role": "sales"},
    "accountant": {"password": "acc123", "role": "accountant"}
}

# ------------------------
# Load users safely
# ------------------------
if "users" not in st.session_state:
    if os.path.exists(users_file):
        try:
            st.session_state.users = pd.read_excel(users_file).set_index("username").T.to_dict()
        except Exception as e:
            st.error(f"Error reading users file: {e}")
            st.session_state.users = default_users.copy()
    else:
        st.session_state.users = default_users.copy()
        # Save default users for future
        df_users = pd.DataFrame([
            {"username": u, "password": info["password"], "role": info["role"]}
            for u, info in default_users.items()
        ])
        df_users.to_excel(users_file, index=False)

# ------------------------
# Initialize session state
# ------------------------
if "login" not in st.session_state:
    st.session_state.login = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None

# ------------------------
# Ensure Excel files exist
# ------------------------
for file, columns in [
    (purchases_file, ["ID", "Date", "Supplier", "Item", "Qty", "Unit Price", "Total"]),
    (sales_file, ["ID", "Date", "Customer", "Item", "Qty", "Unit Price", "Total"])
]:
    if not os.path.exists(file):
        pd.DataFrame(columns=columns).to_excel(file, index=False)

# ------------------------
# App title
# ------------------------
st.title("Import–Export Business Manager")

# ------------------------
# Login screen
# ------------------------
if not st.session_state.login:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        users = st.session_state.users
        if username in users and users[username]["password"] == password:
            st.session_state.login = True
            st.session_state.user = username
            st.session_state.user_role = users[username]["role"]
            st.success(f"Welcome {username} ({st.session_state.user_role})!")
        else:
            st.error("Invalid username or password")

# ------------------------
# Main App after login
# ------------------------
else:
    st.write(f"Logged in as: {st.session_state.user} ({st.session_state.user_role})")

    # --- Admin: manage users ---
    if st.session_state.user_role == "admin":
        st.subheader("User Management")
        with st.expander("Create New User"):
            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")
            role = st.selectbox("Role", ["sales", "accountant"])
            if st.button("Add User"):
                if new_user in st.session_state.users:
                    st.error("Username already exists!")
                else:
                    st.session_state.users[new_user] = {"password": new_pass, "role": role}
                    # Save to Excel
                    users_df = pd.DataFrame.from_dict(st.session_state.users, orient="index")
                    users_df.reset_index(inplace=True)
                    users_df.rename(columns={"index": "username"}, inplace=True)
                    users_df.to_excel(users_file, index=False)
                    st.success(f"User '{new_user}' added with role '{role}'!")

        st.write("### Current Users")
        for u, info in st.session_state.users.items():
            st.write(f"- {u} ({info['role']})")

    # --- Determine accessible tabs ---
    role_tabs = {
        "admin": ["Purchases", "Sales", "Accounting", "User Management"],
        "sales": ["Sales"],
        "accountant": ["Accounting"]
    }

    available_tabs = role_tabs.get(st.session_state.user_role, [])

    if available_tabs:
        tab = st.radio("Select Tab", available_tabs)

        # ------------------------
        # Purchases tab
        # ------------------------
        if tab == "Purchases":
            st.subheader("Purchase Management")
            df = pd.read_excel(purchases_file)
            st.dataframe(df)

            with st.expander("Add New Purchase"):
                date = st.date_input("Date")
                supplier = st.text_input("Supplier")
                item = st.text_input("Item")
                qty = st.number_input("Quantity", min_value=1)
                unit_price = st.number_input("Unit Price", min_value=0.0)
                if st.button("Add Purchase"):
                    new_id = len(df) + 1
                    total = qty * unit_price
                    df.loc[len(df)] = [new_id, date, supplier, item, qty, unit_price, total]
                    df.to_excel(purchases_file, index=False)
                    st.success("Purchase added!")
                    st.experimental_rerun()

        # ------------------------
        # Sales tab
        # ------------------------
        elif tab == "Sales":
            st.subheader("Sales Management")
            df = pd.read_excel(sales_file)
            st.dataframe(df)

            with st.expander("Add New Sale"):
                date = st.date_input("Date")
                customer = st.text_input("Customer")
                item = st.text_input("Item")
                qty = st.number_input("Quantity", min_value=1, key="sales_qty")
                unit_price = st.number_input("Unit Price", min_value=0.0, key="sales_unit_price")
                if st.button("Add Sale"):
                    new_id = len(df) + 1
                    total = qty * unit_price
                    df.loc[len(df)] = [new_id, date, customer, item, qty, unit_price, total]
                    df.to_excel(sales_file, index=False)
                    st.success("Sale added!")
                    st.experimental_rerun()

        # ------------------------
        # Accounting tab
        # ------------------------
        elif tab == "Accounting":
            st.subheader("Profit & Loss")
            purchases_df = pd.read_excel(purchases_file)
            sales_df = pd.read_excel(sales_file)

            total_revenue = sales_df["Total"].sum()
            total_cost = purchases_df["Total"].sum()
            profit = total_revenue - total_cost

            st.write(f"**Total Revenue:** {total_revenue}")
            st.write(f"**Total Cost:** {total_cost}")
            st.write(f"**Profit:** {profit}")
