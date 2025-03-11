import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# File paths for data storage
INVENTORY_FILE = "inventory.csv"
TRANSACTIONS_FILE = "transactions.csv"
INITIAL_CAPITAL = 20000

# Function to load data from CSV files
def load_data():
    if os.path.exists(INVENTORY_FILE):
        inventory = pd.read_csv(INVENTORY_FILE)
    else:
        inventory = pd.DataFrame(
            columns=['Item', 'Quantity', 'Cost Per Unit', 'Selling Price']
        )

    if os.path.exists(TRANSACTIONS_FILE):
        transactions = pd.read_csv(TRANSACTIONS_FILE)
        transactions['Date'] = pd.to_datetime(transactions['Date'])
    else:
        transactions = pd.DataFrame(
            columns=[
                'Date',
                'Type',
                'Item',
                'Quantity',
                'Price',
                'Customer Name',
                'Payment Mode',
                'Expense',
            ]
        )
    return inventory, transactions

# Function to save data to CSV files
def save_data(inventory, transactions):
    inventory.to_csv(INVENTORY_FILE, index=False)
    transactions.to_csv(TRANSACTIONS_FILE, index=False)

# Load data on app start
if 'inventory' not in st.session_state:
    st.session_state.inventory, st.session_state.transactions = load_data()

# Sidebar for page selection
st.sidebar.title("Gajet Tech App")
page = st.sidebar.selectbox(
    "Select Page", ["Landing", "Inventory", "Transactions", "Debt Management"]
)

# Landing Page
if page == "Landing":
    st.header("Gajet Financial Overview")

    sales = st.session_state.transactions[
        (st.session_state.transactions['Type'].isin(['Sale', 'Debt Payment'])) & (st.session_state.transactions['Payment Mode'] != 'Debt')
    ]
    purchases = st.session_state.transactions[
        st.session_state.transactions['Type'] == 'Purchase'
    ]

    sales['Total'] = sales['Quantity'] * sales['Price']
    purchases['Total'] = purchases['Quantity'] * purchases['Price']

    total_sales = sales['Total'].sum() if not sales.empty else 0
    total_purchases = purchases['Total'].sum() if not purchases.empty else 0

    total_expenses = st.session_state.transactions['Expense'].sum() if not st.session_state.transactions.empty else 0

    gross_profit = total_sales - total_purchases - total_expenses
    net_capital = INITIAL_CAPITAL + gross_profit

    # Beautify metrics with colors
    st.metric("Total Sales (Ksh)", f"{total_sales:.2f}", delta_color="normal")
    st.metric("Total Expenses (Ksh)", f"{total_expenses:.2f}", delta_color="inverse")
    st.metric("Gross Profit (Ksh)", f"{gross_profit:.2f}", delta_color="normal")
    st.metric("Net Capital (Ksh)", f"{net_capital:.2f}", delta_color="normal")

    if INITIAL_CAPITAL != 0:
        capital_variation = ((net_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
        st.metric("Capital Variation (%)", f"{capital_variation:.2f}%", delta_color="normal")
    else:
        st.write("Initial capital is zero, variation cannot be calculated.")

    if not st.session_state.transactions.empty:
        daily_transactions = st.session_state.transactions.copy()
        daily_transactions['Date'] = pd.to_datetime(daily_transactions['Date']).dt.date
        daily_sales = (
            daily_transactions[daily_transactions['Type'] == 'Sale']
            .groupby('Date')['Price']
            .sum()
        )
        daily_purchases = (
            daily_transactions[daily_transactions['Type'] == 'Purchase']
            .groupby('Date')['Price']
            .sum()
        )

        # Use a line chart for daily sales and a bar chart for expenses
        fig_sales = px.line(daily_sales, title="Daily Sales (Ksh)")
        st.plotly_chart(fig_sales)

        expenses_data = st.session_state.transactions[st.session_state.transactions['Expense'] > 0]
        if not expenses_data.empty:
            fig_expenses = px.bar(expenses_data, x='Date', y='Expense', title="Expenses")
            st.plotly_chart(fig_expenses)

        profit_data = {
            'Metric': ['Total Sales', 'Total Expenses', 'Gross Profit'],
            'Value': [total_sales, total_expenses, gross_profit]
        }
        fig_profit = px.bar(profit_data, x='Metric', y='Value', title='Financial Metrics')
        st.plotly_chart(fig_profit)

    else:
        st.write('Record transactions to view profit/loss analysis.')

        # Inventory Page
elif page == "Inventory":
    st.header('Inventory Management')

    if not st.session_state.inventory.empty:
        st.dataframe(st.session_state.inventory)
        selected_index = st.selectbox("Select Item to Delete", st.session_state.inventory.index, format_func=lambda x: st.session_state.inventory['Item'][x])

        if st.button("Delete Selected Item"):
            deleted_item = st.session_state.inventory.loc[selected_index]

            # Remove the item from inventory
            st.session_state.inventory = st.session_state.inventory.drop(selected_index).reset_index(drop=True)

            # Find and remove related transactions
            related_transactions = st.session_state.transactions[
                (st.session_state.transactions['Item'] == deleted_item['Item']) &
                (st.session_state.transactions['Type'] == 'Purchase')  # Consider other transaction types if needed
            ]

            if not related_transactions.empty:
                # Remove related transactions from the DataFrame
                st.session_state.transactions = st.session_state.transactions.drop(related_transactions.index).reset_index(drop=True)

            save_data(st.session_state.inventory, st.session_state.transactions)
            st.rerun()

        st.subheader('Low Stock Alerts')
        low_stock = st.session_state.inventory[st.session_state.inventory['Quantity'] < 50]
        if not low_stock.empty:
            st.warning('Low stock items:')
            st.dataframe(low_stock)

        fig_inventory = px.bar(st.session_state.inventory, x='Item', y='Quantity', title='Available Items')
        st.sidebar.plotly_chart(fig_inventory)

    st.subheader("Add New Item")

    item_name = st.text_input("Item Name")
    amount = st.number_input("Amount", min_value=0.0)
    units_purchased = st.number_input("Units Purchased", min_value=0)

    if st.button("Add Item"):
        if item_name:
            if item_name in st.session_state.inventory['Item'].values:
                st.session_state.inventory.loc[st.session_state.inventory['Item'] == item_name, 'Quantity'] += units_purchased
            else:
                new_item = pd.DataFrame(
                    {
                        "Item": [item_name],
                        "Quantity": [units_purchased],
                        "Cost Per Unit": [amount / units_purchased] if units_purchased > 0 else 0,
                        "Selling Price": [0],
                    }
                )
                st.session_state.inventory = pd.concat(
                    [st.session_state.inventory, new_item], ignore_index=True
                )

            # Record expense in transactions
            new_transaction = pd.DataFrame(
                {
                    'Date': [datetime.now()],
                    'Type': ['Purchase'],
                    'Item': [item_name],
                    'Quantity': [units_purchased],
                    'Price': [0],
                    'Customer Name': [''],
                    'Payment Mode': [''],
                    'Expense': [amount],
                }
            )
            st.session_state.transactions = pd.concat(
                [st.session_state.transactions, new_transaction], ignore_index=True
            )

            save_data(st.session_state.inventory, st.session_state.transactions)
            st.rerun()
        else:
            st.warning("Please enter Item Name.")

    # Display Inventory Table
    if not st.session_state.inventory.empty:
        st.subheader("Inventory Table")
        st.dataframe(st.session_state.inventory)

# Transactions Page
elif page == "Transactions":
    st.header('Transaction Recording')

    if not st.session_state.inventory.empty:
        item = st.selectbox('Item', st.session_state.inventory['Item'])
        quantity = st.number_input('Quantity', min_value=1)
        price = st.number_input('Price per Unit', min_value=0.0)
        customer_name = st.text_input('Customer Name')
        payment_mode = st.selectbox('Payment Mode', ['Full', 'Partial', 'Debt'])

        if st.button('Record Transaction'):
            new_transaction = pd.DataFrame(
                {
                    'Date': [datetime.now()],
                    'Type': ['Sale'],
                    'Item': [item],
                    'Quantity': [quantity],
                    'Price': [price],
                    'Customer Name': [customer_name],
                    'Payment Mode': [payment_mode],
                    'Expense': [0],
                }
            )
            st.session_state.transactions = pd.concat(
                [st.session_state.transactions, new_transaction], ignore_index=True
            )

            st.session_state.inventory.loc[
                st.session_state.inventory['Item'] == item, 'Quantity'
            ] -= quantity

            save_data(st.session_state.inventory, st.session_state.transactions)
            st.rerun()

        if not st.session_state.transactions.empty:
            transactions_display = st.session_state.transactions.dropna(axis=1, how='all')
            st.dataframe(transactions_display)

            selected_transaction_index = st.selectbox("Select Transaction to Delete", transactions_display.index)

            if st.button("Delete Selected Transaction"):
                deleted_transaction = st.session_state.transactions.iloc[selected_transaction_index]

                if deleted_transaction['Type'] == 'Sale':
                    st.session_state.inventory.loc[st.session_state.inventory['Item'] == deleted_transaction['Item'], 'Quantity'] += deleted_transaction['Quantity']
                elif deleted_transaction['Type'] == 'Purchase':
                    st.session_state.inventory.loc[st.session_state.inventory['Item'] == deleted_transaction['Item'], 'Quantity'] -= deleted_transaction['Quantity']

                st.session_state.transactions = st.session_state.transactions.drop(selected_transaction_index).reset_index(drop=True)
                save_data(st.session_state.inventory, st.session_state.transactions)
                st.rerun()

    else:
        st.write("Please add items to the inventory first.")

# Profit/Loss Page
elif page == "Profit/Loss":
    st.header('Profit/Loss Analysis')

    sales = st.session_state.transactions[
        (st.session_state.transactions['Type'] == 'Sale') & (st.session_state.transactions['Payment Mode'] != 'Debt')
    ]
    purchases = st.session_state.transactions[
        st.session_state.transactions['Type'] == 'Purchase'
    ]

    sales['Total'] = sales['Quantity'] * sales['Price']
    purchases['Total'] = purchases['Quantity'] * purchases['Price']

    total_sales = sales['Total'].sum() if not sales.empty else 0
    total_purchases = purchases['Total'].sum() if not purchases.empty else 0

    total_expenses = st.session_state.transactions['Expense'].sum() if not st.session_state.transactions.empty else 0

    gross_profit = total_sales - total_purchases - total_expenses

    st.metric('Total Sales (Ksh)', f'${total_sales:.2f}')
    st.metric('Total Expenses (Ksh)', f'${total_expenses:.2f}')
    st.metric('Gross Profit (Ksh)', f'${gross_profit:.2f}')

    if not st.session_state.transactions.empty:
        # Use a line chart for daily sales and a bar chart for expenses
        daily_sales = st.session_state.transactions[st.session_state.transactions['Type'] == 'Sale'].groupby('Date')['Price'].sum()
        fig_sales = px.line(daily_sales, title="Daily Sales (Ksh)")
        st.plotly_chart(fig_sales)

        expenses_data = st.session_state.transactions[st.session_state.transactions['Expense'] > 0]
        if not expenses_data.empty:
            fig_expenses = px.bar(expenses_data, x='Date', y='Expense', title="Expenses")
            st.plotly_chart(fig_expenses)

        profit_data = {
            'Metric': ['Total Sales', 'Total Expenses', 'Gross Profit'],
            'Value': [total_sales, total_expenses, gross_profit]
        }
        fig_profit = px.bar(profit_data, x='Metric', y='Value', title='Financial Metrics')
        st.plotly_chart(fig_profit)

    else:
        st.write('Record transactions to view profit/loss analysis.')

# Debt Management Page
elif page == "Debt Management":
    st.header('Debt Management')

    if not st.session_state.transactions.empty:
        debtors = st.session_state.transactions[
            (st.session_state.transactions['Payment Mode'] == 'Debt')
            & (st.session_state.transactions['Type'] == 'Sale')
        ]
        st.dataframe(debtors)

        if not debtors.empty:
            debtor_list = debtors['Customer Name'].unique()
            st.subheader('Debtor List')
            st.write(debtor_list)

            for debtor in debtor_list:
                if st.button(f"Clear Debt: {debtor}"):
                    debt_amount = debtors[debtors['Customer Name'] == debtor]['Price'].sum()

                    # Record debt payment in transactions
                    new_transaction = pd.DataFrame(
                        {
                            'Date': [datetime.now()],
                            'Type': ['Debt Payment'],
                            'Item': ['Debt Payment'],
                            'Quantity': [1],
                            'Price': [debt_amount],
                            'Customer Name': [debtor],
                            'Payment Mode': ['Full'],
                            'Expense': [0],
                        }
                    )
                    st.session_state.transactions = pd.concat(
                        [st.session_state.transactions, new_transaction], ignore_index=True
                    )

                    # Remove cleared debt from debtors list (by filtering)
                    st.session_state.transactions = st.session_state.transactions[
                        ~((st.session_state.transactions['Customer Name'] == debtor) & (st.session_state.transactions['Payment Mode'] == 'Debt'))
                    ]

                    save_data(st.session_state.inventory, st.session_state.transactions)
                    st.rerun()

        if not debtors.empty:
            debtors['Date'] = pd.to_datetime(debtors['Date']).dt.date
            daily_debt = debtors.groupby('Date')['Price'].sum()
            fig_debt = px.line(daily_debt, title='Daily Debt Accumulation')
            st.plotly_chart(fig_debt)
    else:
        st.write('Record transactions to view Debt Management.')
