import streamlit as st
import pandas as pd
import os

# === FILE PATHS ===
USERS_FILE = "users.csv"
PURCHASES_FILE = "purchases.csv"
SALES_FILE = "sales.csv"
ACCOUNTS_FILE = "accounts.csv"

# === DEFAULT COLUMNS ===
PURCHASE_COLUMNS = ["Date", "Supplier", "Material", "Quantity", "Rate", "Total", "Remarks"]
SALES_COLUMNS = ["Date", "Customer", "Material", "Quantity", "Rate", "Total", "Remarks"]
ACCOUNT_COLUMNS = ["Date", "Description", "Credit", "Debit", "Balance"]

# === FUNCTION TO LOAD OR CREATE CSV FILE ===
def load_csv(file, columns):
    if not os.path.exists(file) or os.stat(file).st_size == 0:
        df = pd.DataFrame(columns=columns)
        df.to_csv(file, index=False)
    else:
        try:
            df = pd.read_csv(file)
        except pd.errors.EmptyDataError:
            df = pd.DataFrame(columns=columns)
            df.to_csv(file, index=False)
    return df

# === LOAD USERS CSV ===
def load_users():
    if not os.path.exists(USERS_FILE):
        # create default users file
        with open(USERS_FILE, "w") as f:
            f.write("username,password,role\nadmin,admin123,admin\nuser1,user123,user\nuser2,user234,user\n")
    df = pd.read_csv(USERS_FILE)
    return df.set_index("username").T.to_dict()

# === INITIAL SETUP ===
if "users" not in st.session_state:
    st.session_state.users = load_users()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

# === APP TITLE ===
st.title("📦 Import Export Management App")

# === LOGIN SECTION ===
if not st.session_state.logged_in:
    input_username = st.text_input("Username")
    input_password = st.text_input("Password", type="password")

    if st.button("Login"):
        user_data = st.session_state.users.get(input_username)
        if user_data and user_data["password"] == input_password:
            st.session_state.logged_in = True
            st.session_state.username = input_username
            st.session_state.role = user_data["role"]
            st.success(f"Welcome {input_username}!")
            st.rerun()
        else:
            st.error("Invalid username or password.")
else:
    st.sidebar.success(f"Logged in as: {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.rerun()

    # === LOAD DATA ===
    purchases = load_csv(PURCHASES_FILE, PURCHASE_COLUMNS)
    sales = load_csv(SALES_FILE, SALES_COLUMNS)
    accounts = load_csv(ACCOUNTS_FILE, ACCOUNT_COLUMNS)

    # === MENU ===
    menu_options = ["Purchase", "Sales"]
    if st.session_state.role == "admin":
        menu_options.append("Accounts")
    menu = st.sidebar.radio("Select Section", menu_options)

    # === PURCHASE SECTION ===
    if menu == "Purchase":
        st.header("🧾 Purchase Records")
        st.dataframe(purchases)

        with st.expander("➕ Add New Purchase Entry"):
            new_data = {}
            for col in PURCHASE_COLUMNS:
                new_data[col] = st.text_input(col, key=f"purchase_{col}")
            if st.button("Save Purchase Entry"):
                purchases.loc[len(purchases)] = list(new_data.values())
                purchases.to_csv(PURCHASES_FILE, index=False)
                st.success("✅ Purchase entry saved!")
                st.rerun()

    # === SALES SECTION ===
    elif menu == "Sales":
        st.header("💰 Sales Records")
        st.dataframe(sales)

        with st.expander("➕ Add New Sales Entry"):
            new_data = {}
            for col in SALES_COLUMNS:
                new_data[col] = st.text_input(col, key=f"sales_{col}")
            if st.button("Save Sales Entry"):
                sales.loc[len(sales)] = list(new_data.values())
                sales.to_csv(SALES_FILE, index=False)
                st.success("✅ Sales entry saved!")
                st.rerun()

    # === ACCOUNTS SECTION (Admin Only) ===
    elif menu == "Accounts":
        if st.session_state.role != "admin":
            st.error("🚫 Access denied. Only admin can view this section.")
        else:
            st.header("📒 Account Records (Admin Only)")
            st.dataframe(accounts)

            with st.expander("➕ Add New Account Entry"):
                new_data = {}
                for col in ACCOUNT_COLUMNS:
                    new_data[col] = st.text_input(col, key=f"account_{col}")
                if st.button("Save Account Entry"):
                    accounts.loc[len(accounts)] = list(new_data.values())
                    accounts.to_csv(ACCOUNTS_FILE, index=False)
                    st.success("✅ Account entry saved!")
                    st.rerun()
