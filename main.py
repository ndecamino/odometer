# Preamble ---------------------------------------------------------------------

# Imports
import streamlit as st
from datetime import datetime
import os
import pandas as pd

# Page config
st.set_page_config(
    page_title="Tracker Gol",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Predefined constants
DATA_DIR = 'data'
RECORDS_FILE = os.path.join(DATA_DIR, 'records.csv')
TANKS_FILE = os.path.join(DATA_DIR, 'tanks.csv')
USERS = ['nicolas', 'agustin', 'rosario', 'mama', 'papa']

# Initialize session state
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'home'
if 'selected_record_id' not in st.session_state:
    st.session_state.selected_record_id = None
if 'message' not in st.session_state:
    st.session_state.message = None
if 'message_type' not in st.session_state:
    st.session_state.message_type = None

# Functions --------------------------------------------------------------------

def load_records():
    """Load records from CSV file"""
    df = pd.read_csv(RECORDS_FILE, parse_dates=['timestamp'])
    df['id'] = df['id'].astype(int)
    df['odometer'] = df['odometer'].astype(int)
    df['trip'] = df['trip'].astype(int)
    df['tank_id'] = df['tank_id'].astype(int)
    df['pay'] = df['pay'].astype(int)
    return df

def save_records(df):
    """Save records to CSV file"""
    df.to_csv(RECORDS_FILE, index=False)

def load_tanks():
    """Load tanks from CSV file"""
    df = pd.read_csv(TANKS_FILE, parse_dates=['timestamp'])
    df['id'] = df['id'].astype(int)
    df['price'] = df['price'].astype(int)
    for user in USERS: df[user] = df[user].astype(int)
    return df

def save_tanks(df):
    """Save tanks to CSV file"""
    df.to_csv(TANKS_FILE, index=False)

def verify_odometer(record):
    """Verify that the odometer reading is valid"""
    df = load_records()
    timestamp = pd.to_datetime(f"{record['date']}T{record['time']}")

    # Check against last record
    last_records = df[df['timestamp'] < timestamp].sort_values('odometer', ascending=False)
    if not last_records.empty:
        last_record = last_records.iloc[0]
        current_odometer = int(record['odometer'])
        last_odometer = int(last_record['odometer'])
        if current_odometer < last_odometer:
            return '⚠️ Error: El kilometraje debe ser mayor que el registro anterior'

    # Check against next record
    next_records = df[df['timestamp'] > timestamp].sort_values('odometer', ascending=True)
    if not next_records.empty:
        next_record = next_records.iloc[0]
        current_odometer = int(record['odometer'])
        next_odometer = int(next_record['odometer'])
        if current_odometer > next_odometer:
            return '⚠️ Error: El kilometraje debe ser menor que el registro siguiente'

    return None

def update_records():
    """Update trip distances and tank IDs for all records"""
    df = load_records()
    df = df.sort_values('odometer').reset_index(drop=True)

    # Calculate trips
    for i in range(len(df) - 1):
        current_odometer = int(df.loc[i, 'odometer'])
        next_odometer = int(df.loc[i + 1, 'odometer'])
        df.loc[i, 'trip'] = next_odometer - current_odometer

    # Update tank IDs
    for i in range(1, len(df)):
        current_pay = int(df.loc[i, 'pay'])
        last_pay = int(df.loc[i - 1, 'pay'])
        current_tank_id = int(df.loc[i, 'tank_id'])
        last_tank_id = int(df.loc[i - 1, 'tank_id'])

        if current_pay > 0 and current_tank_id == last_tank_id:
            df.loc[i, 'tank_id'] = current_tank_id + 1
        elif current_pay == 0 and current_tank_id != last_tank_id:
            df.loc[i, 'tank_id'] = last_tank_id

    save_records(df)

def update_tanks():
    """Update tank information based on records"""
    records_df = load_records()
    records_df = records_df.sort_values('odometer').reset_index(drop=True)

    tanks_list = []

    # Find all records with pay > 0
    pay_records = records_df[records_df['pay'] > 0]

    for _, record in pay_records.iterrows():
        tank_id = int(record['tank_id']) - 1
        timestamp = record['timestamp']
        price = int(record['pay'])
        user = record['user']

        tank = {
            'id': tank_id,
            'timestamp': timestamp,
            'price': price,
        }

        # Calculate each user's share
        for user in USERS:
            user_records = records_df[(records_df['user'] == user) & (records_df['tank_id'] == tank_id)]
            user_km = user_records['trip'].sum()

            total_records = records_df[records_df['tank_id'] == tank_id]
            total_km = total_records['trip'].sum()

            user_share = round(user_km / total_km * price, 0) if total_km > 0 else 0
            tank[user] = int(user_share)

        tanks_list.append(tank)

    if tanks_list:
        tanks_df = pd.DataFrame(tanks_list)
        # Remove duplicates, keeping the last one
        tanks_df = tanks_df.drop_duplicates(subset=['id'], keep='last')
        save_tanks(tanks_df)
    else:
        # Save empty dataframe with correct columns
        tanks_df = pd.DataFrame(columns=[
            'id', 'timestamp', 'price', 'nicolas', 'agustin', 'rosario', 'mama'
        ])
        save_tanks(tanks_df)

def add_record(record):
    """Add a new record to the dataframe"""
    df = load_records()

    new_timestamp = pd.to_datetime(f"{record['date']}T{record['time']}")
    new_odometer = int(record['odometer'])
    new_price = 0 if record['pay'] == '' else int(record['pay'])
    new_user = record['user']
    new_trip = 0

    # Find last record with smaller odometer
    last_records = df[df['odometer'] < new_odometer].sort_values('odometer', ascending=False)
    if not last_records.empty:
        last_tank_id = int(last_records.iloc[0]['tank_id'])
    else:
        last_tank_id = 1

    new_tank_id = last_tank_id + 1 if new_price > 0 else last_tank_id

    # Get next ID
    new_id = df['id'].max() + 1 if not df.empty else 1

    new_record = pd.DataFrame({
        'id': [new_id],
        'timestamp': [new_timestamp],
        'user': [new_user],
        'odometer': [new_odometer],
        'trip': [new_trip],
        'tank_id': [new_tank_id],
        'pay': [new_price]
    })

    df = pd.concat([df, new_record], ignore_index=True)
    save_records(df)

    update_records()
    update_tanks()

def update_record(record_id, new_record):
    """Update an existing record"""
    df = load_records()

    # Verify odometer before updating
    new_record['id'] = record_id
    error = verify_odometer(new_record)
    if error is not None:
        return error

    # Find the record to update
    idx = df[df['id'] == record_id].index[0]

    # Update the record
    df.loc[idx, 'timestamp'] = f"{new_record['date']}T{new_record['time']}"
    df.loc[idx, 'user'] = new_record['user']
    df.loc[idx, 'odometer'] = int(new_record['odometer'])
    df.loc[idx, 'pay'] = int(new_record['pay'])

    save_records(df)
    update_records()
    update_tanks()

    return None

def delete_record(record_id):
    """Delete a record from the dataframe"""
    df = load_records()
    df = df[df['id'] != record_id]
    save_records(df)
    update_records()
    update_tanks()

def format_number(num):
    return f"{int(num):,}".replace(",", ".")

def go_home():
    st.session_state.current_view = 'home'
    st.session_state.selected_record_id = None
    st.session_state.message = None

def go_all_records():
    st.session_state.current_view = 'all_records'

def go_all_tanks():
    st.session_state.current_view = 'all_tanks'

def go_edit_record(record_id):
    st.session_state.current_view = 'edit_record'
    st.session_state.selected_record_id = record_id

def form_add_record():
    st.markdown("### ⊕ Añadir registro")

    # Show message if exists
    if st.session_state.message:
        if st.session_state.message_type == 'success':
            st.success(st.session_state.message)
        else:
            st.error(st.session_state.message)

    with st.form("add_record_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Fecha", value=datetime.now(), format="DD/MM/YYYY")
        with col2:
            time = st.time_input("Hora", value=datetime.now().time())

        user = st.selectbox("Usuario", options=[''] + USERS, format_func=lambda x: 'Usuario' if x == '' else x.capitalize())
        odometer = st.text_input("Kilometraje", placeholder="Kilometraje")
        price = st.text_input("Bencina", placeholder="Bencina (opcional)")

        submitted = st.form_submit_button("Registrar", use_container_width=True)

        if submitted:
            if not user or not odometer:
                st.session_state.message = "⚠️ Por favor completa todos los campos requeridos"
                st.session_state.message_type = 'error'
                st.rerun()
            else:
                record = {
                    'date': date.strftime("%Y-%m-%d"),
                    'time': time.strftime("%H:%M"),
                    'user': user,
                    'odometer': odometer,
                    'pay': price if price else ''
                }
                error = verify_odometer(record)
                if error:
                    st.session_state.message = error
                    st.session_state.message_type = 'error'
                    st.rerun()
                else:
                    add_record(record)
                    st.session_state.message = "👍 Listoco"
                    st.session_state.message_type = 'success'
                    st.rerun()

def table_last_records():
    st.markdown("### ☑︎ Registros")

    df = load_records()
    df = df.sort_values('odometer', ascending=False).head(5)

    if not df.empty:
        data = []
        record_ids = []
        for _, row in df.iterrows():
            dt = row['timestamp']
            data.append({
                'Fecha': dt.strftime("%d/%m"),
                'Hora': dt.strftime("%H:%M"),
                'Usuario': row['user'].capitalize(),
                'Kilometraje': format_number(row['odometer']),
                'Viaje': format_number(row['trip']),
                'Paga': format_number(row['pay']),
            })
            record_ids.append(row['id'])

        display_df = pd.DataFrame(data)

        # Use on_select to handle row selection
        event = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        # Handle selection
        if event.selection.rows:
            selected_idx = event.selection.rows[0]
            selected_id = record_ids[selected_idx]
            go_edit_record(selected_id)
            st.rerun()

    st.button("Ver todos", on_click=go_all_records, use_container_width=True, type="secondary", key="records_view_all")

def table_all_records():
    st.markdown("### ☑︎ Registros")

    df = load_records()
    df = df.sort_values('odometer', ascending=False)

    if not df.empty:
        data = []
        record_ids = []
        for _, row in df.iterrows():
            dt = row['timestamp']
            data.append({
                'Fecha': dt.strftime("%d/%m"),
                'Hora': dt.strftime("%H:%M"),
                'Usuario': row['user'].capitalize(),
                'Kilometraje': format_number(row['odometer']),
                'Viaje': format_number(row['trip']),
                'Paga': format_number(row['pay']),
            })
            record_ids.append(row['id'])

        display_df = pd.DataFrame(data)

        # Use on_select to handle row selection with scrolling
        event = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            height=600
        )

        # Handle selection
        if event.selection.rows:
            selected_idx = event.selection.rows[0]
            selected_id = record_ids[selected_idx]
            go_edit_record(selected_id)
            st.rerun()

    st.button("Volver", on_click=go_home, use_container_width=True, type="secondary", key="records_back")

def table_last_tanks():
    st.markdown("### $ Estanques")

    df = load_tanks()

    if not df.empty:
        df = df.sort_values('timestamp', ascending=False)
        df = df.head(3)

        data = []
        for _, row in df.iterrows():
            dt = row['timestamp']
            tank_row = {
                'Fecha': dt.strftime("%d/%m"),
                'Precio': format_number(row['price'])
            }
            for user in USERS:
                tank_row[user.capitalize()] = format_number(row[user])
            data.append(tank_row)

        display_df = pd.DataFrame(data)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.button("Ver todos", on_click=go_all_tanks, use_container_width=True, type="secondary", key="tanks_view_all")

def table_all_tanks():
    st.markdown("### $ Estanques")

    df = load_tanks()

    if not df.empty:
        df = df.sort_values('timestamp', ascending=False)
        data = []
        for _, row in df.iterrows():
            dt = row['timestamp']
            tank_row = {
                'Fecha': dt.strftime("%d/%m"),
                'Precio': format_number(row['price'])
            }
            for user in USERS:
                tank_row[user.capitalize()] = format_number(row[user])
            data.append(tank_row)

        display_df = pd.DataFrame(data)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.button("Volver", on_click=go_home, use_container_width=True, type="secondary", key="tanks_back")

def form_edit_record():
    st.markdown("### ✏︎ Editar registro")

    record_id = st.session_state.selected_record_id
    df = load_records()
    old_record = df[df['id'] == record_id].iloc[0]

    old_date = old_record['timestamp'].date()
    old_time = old_record['timestamp'].time()

    # Show message if exists
    if st.session_state.message:
        if st.session_state.message_type == 'success':
            st.success(st.session_state.message)
        else:
            st.error(st.session_state.message)

    with st.form("edit_record_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Fecha", value=old_date, format="DD/MM/YYYY")
        with col2:
            time = st.time_input("Hora", value=old_time)

        user_index = USERS.index(old_record['user'])
        user = st.selectbox("Usuario", options=USERS, index=user_index, format_func=lambda x: x.capitalize())

        odometer = st.text_input("Kilometraje", value=str(old_record['odometer']))
        pay = st.text_input("Bencina", value=str(old_record['pay']))
        st.text_input("Viaje", value=str(old_record['trip']), disabled=True)

        submitted = st.form_submit_button("Actualizar", use_container_width=True)

        if submitted:
            new_record = {
                'date': date.strftime("%Y-%m-%d"),
                'time': time.strftime("%H:%M"),
                'user': user,
                'odometer': odometer,
                'pay': pay if pay else '0'
            }
            error = update_record(record_id, new_record)
            if error:
                st.session_state.message = error
                st.session_state.message_type = 'error'
            else:
                st.session_state.message = "👍 Listoco"
                st.session_state.message_type = 'success'
            st.rerun()

    # Delete button
    if st.button("Eliminar", use_container_width=True, type="secondary"):
        st.session_state.confirm_delete = True
        st.rerun()

    # Confirmation dialog for delete
    if st.session_state.get('confirm_delete', False):
        st.warning("¿Estás seguro?")
        col1, col2 = st.columns(2)
        if col1.button("Sí, eliminar", use_container_width=True):
            delete_record(record_id)
            st.session_state.message = "❌ Eliminado"
            st.session_state.message_type = 'success'
            st.session_state.confirm_delete = False
            go_home()
            st.rerun()
        if col2.button("Cancelar", use_container_width=True):
            st.session_state.confirm_delete = False
            st.rerun()

    # Back button
    st.button("Volver", on_click=go_home, use_container_width=True, type="primary")


# Main App ---------------------------------------------------------------------

st.title('Bencina Gol')

if st.session_state.current_view == 'home':
    form_add_record()
    st.divider()
    table_last_records()
    st.divider()
    table_last_tanks()

elif st.session_state.current_view == 'all_records':
    table_all_records()

elif st.session_state.current_view == 'all_tanks':
    table_all_tanks()

elif st.session_state.current_view == 'edit_record':
    form_edit_record()
