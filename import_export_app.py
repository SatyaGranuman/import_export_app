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
# Default users
# ------------------------
default_users = {
    "admin": {"password": "admin123", "role": "admin"},
    "sales": {"password": "sales123", "role": "sales"},
    "accountant": {"password": "acc123", "role": "accountant"}
}

# ------------------------
# Initialize session state
# ------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "users" not in st.session_state:
    try:
        st.session_state.users = pd.read_excel(users_file).set_index("username").T.to_dict()
    except Exception:
        st.session_state.users = default_users.copy()

# ------------------------
# Login function
# ------------------------
def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        users = st.session_state.users
        if username in users and users[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = users[username]["role"]
            st.success(f"Logged in as {username} ({st.session_state.role})")
        else:
            st.error("Invalid username or password")

# ------------------------
# Logout function
# ------------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.success("Logged out successfully")

# ------------------------
# Load Excel safely
# ------------------------
def load_excel(file_path, columns=[]):
    try:
        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
        else:
            df = pd.DataFrame(columns=columns)
        return df
    except Exception as e:
        st.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame(columns=columns)

# ------------------------
# Save Excel safely
# ------------------------
def save_excel(df, file_path):
    try:
        df.to_excel(file_path, index=False)
    except Exception as e:
        st.error(f"Error saving {file_path}: {e}")

# ------------------------
# App main
# ------------------------
if not st.session_state.logged_in:
    login()
else:
    st.sidebar.write(f"Logged in as: {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        logout()

    tab = st.sidebar.selectbox("Select Tab", ["Purchases", "Sales", "Accounting", "User Management"])

    # ------------------------
    # Purchases Tab
    # ------------------------
    if tab == "Purchases":
        st.header("Purchase Management")
        purchases_columns = ["Date", "Item", "Quantity", "Price"]
        df_purchases = load_excel(purchases_file, purchases_columns)
        st.dataframe(df_purchases)

        if st.session_state.role in ["admin", "sales"]:
            with st.form("Add Purchase"):
                date = st.date_input("Date")
                item = st.text_input("Item")
                qty = st.number_input("Quantity", min_value=1)
                price = st.number_input("Price", min_value=0.0)
                submitted = st.form_submit_button("Add Purchase")
                if submitted:
                    new_row = pd.DataFrame([[date, item, qty, price]], columns=purchases_columns)
                    df_purchases = pd.concat([df_purchases, new_row], ignore_index=True)
                    save_excel(df_purchases, purchases_file)
                    st.success("Purchase added successfully")

    # ------------------------
    # Sales Tab
    # ------------------------
    elif tab == "Sales":
        st.header("Sales Management")
        sales_columns = ["Date", "Item", "Quantity", "Price"]
        df_sales = load_excel(sales_file, sales_columns)
        st.dataframe(df_sales)

        if st.session_state.role in ["admin", "sales"]:
            with st.form("Add Sale"):
                date = st.date_input("Date")
                item = st.text_input("Item")
                qty = st.number_input("Quantity", min_value=1)
                price = st.number_input("Price", min_value=0.0)
                submitted = st.form_submit_button("Add Sale")
                if submitted:
                    new_row = pd.DataFrame([[date, item, qty, price]], columns=sales_columns)
                    df_sales = pd.concat([df_sales, new_row], ignore_index=True)
                    save_excel(df_sales, sales_file)
                    st.success("Sale added successfully")

    # ------------------------
    # Accounting Tab
    # ------------------------
    elif tab == "Accounting":
        st.header("Profit & Loss")
        df_purchases = load_excel(purchases_file, ["Date", "Item", "Quantity", "Price"])
        df_sales = load_excel(sales_file, ["Date", "Item", "Quantity", "Price"])
        total_purchase = df_purchases["Price"].sum() if not df_purchases.empty else 0
        total_sales = df_sales["Price"].sum() if not df_sales.empty else 0
        profit = total_sales - total_purchase
        st.metric("Total Purchases", total_purchase)
        st.metric("Total Sales", total_sales)
        st.metric("Profit / Loss", profit)

    # ------------------------
    # User Management Tab
    # ------------------------
    elif tab == "User Management":
        st.header("User Management")
        if st.session_state.role != "admin":
            st.warning("Only admin can manage users.")
        else:
            users = st.session_state.users
            st.dataframe(pd.DataFrame(users).T)
            with st.form("Add User"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                role = st.selectbox("Role", ["admin", "sales", "accountant"])
                submitted = st.form_submit_button("Add User")
                if submitted:
                    if username in users:
                        st.error("User already exists.")
                    else:
                        users[username] = {"password": password, "role": role}
                        st.session_state.users = users
                        try:
                            pd.DataFrame(users).T.reset_index().rename(columns={"index":"username"}).to_excel(users_file, index=False)
                        except Exception as e:
                            st.warning(f"Could not save users file: {e}")
                        st.success(f"User {username} added successfully")