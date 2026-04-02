import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import pickle
import os
from datetime import datetime
import re


def is_valid_india_plate(plate: str):
    """
    Valid Indian license plate formats:
    - Standard:     MH 12 AB 1234   (state, district, series, number)
    - BH Series:    23 BH 1234 AA   (year, BH, number, series) - Bharat series
    - Diplomatic:   CD 123 A        (Corps Diplomatique)
    - Army:         01 A 1234       (unit, series, number)
    """
    cleaned = plate.strip().upper()

    STATE_CODES = {
        "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN",
        "GA", "GJ", "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD",
        "MH", "ML", "MN", "MP", "MZ", "NL", "OD", "PB", "PY", "RJ",
        "SK", "TN", "TR", "TS", "UK", "UP", "WB"
    }

    # Standard: MH 12 AB 1234
    standard = re.fullmatch(r"([A-Z]{2})\s(\d{2})\s([A-Z]{1,3})\s(\d{1,4})", cleaned)
    # BH Series: 23 BH 1234 AA
    bh_series = re.fullmatch(r"(\d{2})\sBH\s(\d{4})\s([A-Z]{2})", cleaned)
    # Diplomatic: CD 123 A
    diplomatic = re.fullmatch(r"CD\s\d{1,4}\s[A-Z]", cleaned)
    # Army: 01 A 1234
    army = re.fullmatch(r"\d{2}\s[A-Z]\s\d{4}", cleaned)

    if standard:
        state = standard.group(1)
        if state not in STATE_CODES:
            return False, f"Unknown state code: '{state}'. Valid codes: {', '.join(sorted(STATE_CODES))}"
        district = int(standard.group(2))
        if district < 1 or district > 99:
            return False, f"Invalid district number: '{standard.group(2)}'"
        return True, None

    if bh_series:
        year = int(bh_series.group(1))
        if year < 21:
            return False, f"BH series started in 2021. Year '{year}' is invalid."
        return True, None

    if diplomatic:
        return True, None

    if army:
        return True, None

    return False, (
        f"'{plate}' does not match a valid Indian license plate format.\n"
        "Valid formats:\n"
        "• Standard:    MH 12 AB 1234\n"
        "• BH Series:   23 BH 1234 AA\n"
        "• Diplomatic:  CD 123 A\n"
        "• Army:        01 A 1234"
    )


st.set_page_config(page_title="License Plate Recognition", page_icon="🚗", layout="wide")

if 'known_plates' not in st.session_state:
    st.session_state.known_plates = set()
if 'plate_history' not in st.session_state:
    st.session_state.plate_history = []
if 'vehicles_inside' not in st.session_state:
    st.session_state.vehicles_inside = {}  # plate -> entry_time


def clean_license_plate(text):
    cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
    return cleaned


def save_model(known_plates, filename='plates_db.pkl'):
    data = {'known_plates': list(known_plates)}
    with open(filename, 'wb') as f:
        pickle.dump(data, f)


def load_model(filename='plates_db.pkl'):
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            data = pickle.load(f)
        return set(data['known_plates'])
    return set()


def check_access(plate_number, known_plates):
    return plate_number in known_plates


def calculate_duration(entry_time_str):
    """Calculate duration between entry and exit"""
    try:
        entry_time = datetime.strptime(entry_time_str, '%Y-%m-%d %H:%M:%S')
        exit_time = datetime.now()
        duration = exit_time - entry_time
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    except:
        return "N/A"


# Main UI
st.title("🚗 License Plate Recognition & Entry/Exit System")
st.markdown("**Recognize license plates and track vehicle entry/exit**")

# Sidebar with statistics
with st.sidebar:
    st.divider()
    st.markdown("### 📊 Statistics")
    st.metric("Known Plates", len(st.session_state.known_plates))
    st.metric("History Records", len(st.session_state.plate_history))
    st.metric("Vehicles Currently Inside", len(st.session_state.vehicles_inside))
    
    st.divider()
    st.markdown("### 🚙 Currently Inside")
    if st.session_state.vehicles_inside:
        for plate, entry_time in st.session_state.vehicles_inside.items():
            duration = calculate_duration(entry_time)
            st.write(f"• **{plate}** ({duration})")
    else:
        st.write("No vehicles inside")

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📚 Get Data", "🚪 Entry/Exit Board", "🔍 Recognize Plate", "📋 Known Plates", "📈 History"])

# Tab 1: Train Model
with tab1:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**Option 1: Upload CSV File**")
        csv_file = st.file_uploader(
            "Upload CSV with license plate numbers",
            type=['csv'],
            help="CSV should have a column named 'plate_number'"
        )

        if csv_file:
            df = pd.read_csv(csv_file)
            st.dataframe(df.head())

            if 'plate_number' in df.columns:
                plates = df['plate_number'].astype(str).tolist()
                st.success(f"Found {len(plates)} license plates")

                if st.button("Add to Database"):
                    for plate in plates:
                        cleaned = clean_license_plate(plate)
                        if cleaned:
                            st.session_state.known_plates.add(cleaned)
                    st.success(f"Added {len(plates)} plates to database")
                    st.rerun()

        st.divider()

        st.markdown("**Option 2: Manual Entry**")
        manual_plate = st.text_input(
            "Enter license plate number",
            placeholder="e.g., MH 12 AB 1234"
        )

        if st.button("Add Plate"):
            if manual_plate:
                is_valid, error_msg = is_valid_india_plate(manual_plate)
                if not is_valid:
                    st.error(f"Invalid plate format: {error_msg}")
                else:
                    st.success("Plate added successfully")
                    cleaned = clean_license_plate(manual_plate)
                    st.session_state.known_plates.add(cleaned)
                    st.rerun()
            else:
                st.warning("Please enter a license plate number.")

    with col2:
        st.subheader("Bulk Add Plates")
        st.info("💡 You can add multiple plates at once")

        bulk_text = st.text_area(
            "Enter multiple plates (one per line)",
            height=200,
            placeholder="MH 12 AB 1234\nDL 01 XY 5678\nKA 03 MN 9012"
        )

        if st.button("Add All Plates"):
            if bulk_text:
                lines = bulk_text.strip().split('\n')
                added = 0
                errors = []
                for line in lines:
                    line = line.strip()
                    if line:
                        is_valid, error_msg = is_valid_india_plate(line)
                        if is_valid:
                            cleaned = clean_license_plate(line)
                            st.session_state.known_plates.add(cleaned)
                            added += 1
                        else:
                            errors.append(f"• {line}: {error_msg}")

                if added:
                    st.success(f"Added {added} plates to database")
                if errors:
                    st.error("Some plates were invalid:\n" + "\n".join(errors))
                if added:
                    st.rerun()
            else:
                st.warning("Please enter at least one plate number.")

    st.divider()
    st.info(f"Current database size: {len(st.session_state.known_plates)} plates")


# Tab 2: Entry/Exit Board
with tab2:
    st.header("🚪 Entry/Exit Board")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📍 Vehicle Entry")
        entry_plate = st.text_input(
            "Enter license plate for ENTRY",
            placeholder="e.g., MH 12 AB 1234",
            key='entry_plate'
        )
        
        if st.button("✅ ENTRY SCAN", use_container_width=True, key='entry_btn'):
            if entry_plate:
                cleaned_plate = clean_license_plate(entry_plate)
                
                if cleaned_plate in st.session_state.vehicles_inside:
                    st.warning(f"⚠️ Vehicle {cleaned_plate} already inside! Cannot re-enter.")
                else:
                    has_access = check_access(cleaned_plate, st.session_state.known_plates)
                    
                    if has_access:
                        entry_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        st.session_state.vehicles_inside[cleaned_plate] = entry_time
                        
                        st.session_state.plate_history.append({
                            'timestamp': entry_time,
                            'plate': cleaned_plate,
                            'event': 'ENTRY',
                            'status': 'Authorized',
                            'duration': '-'
                        })
                        
                        st.success(f"✅ Vehicle {cleaned_plate} ENTERED at {entry_time}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ ACCESS DENIED - Vehicle {cleaned_plate} not authorized")
            else:
                st.warning("Please enter a license plate number.")
    
    with col2:
        st.subheader("📤 Vehicle Exit")
        exit_plate = st.text_input(
            "Enter license plate for EXIT",
            placeholder="e.g., MH 12 AB 1234",
            key='exit_plate'
        )
        
        if st.button("🚫 EXIT SCAN", use_container_width=True, key='exit_btn'):
            if exit_plate:
                cleaned_plate = clean_license_plate(exit_plate)
                
                if cleaned_plate in st.session_state.vehicles_inside:
                    entry_time = st.session_state.vehicles_inside[cleaned_plate]
                    exit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    duration = calculate_duration(entry_time)
                    
                    # Remove from inside tracking
                    del st.session_state.vehicles_inside[cleaned_plate]
                    
                    # Add to history with EXIT event
                    st.session_state.plate_history.append({
                        'timestamp': exit_time,
                        'plate': cleaned_plate,
                        'event': 'EXIT',
                        'status': 'Exited',
                        'duration': duration
                    })
                    
                    st.success(f"🚫 Vehicle {cleaned_plate} EXITED at {exit_time}")
                    st.info(f"⏱️ Duration inside: {duration}")
                    st.rerun()
                else:
                    st.error(f"❌ Vehicle {cleaned_plate} not found inside. Cannot exit.")
            else:
                st.warning("Please enter a license plate number.")
    
    st.divider()
    st.markdown("### 📊 Current Status Dashboard")
    
    # Current vehicles inside
    if st.session_state.vehicles_inside:
        st.markdown("#### 🚗 Vehicles Currently Inside:")
        vehicles_df = pd.DataFrame([
            {
                'License Plate': plate,
                'Entry Time': entry_time,
                'Duration': calculate_duration(entry_time)
            }
            for plate, entry_time in st.session_state.vehicles_inside.items()
        ])
        st.dataframe(vehicles_df, use_container_width=True)
    else:
        st.info("✅ No vehicles inside - Parking area is empty")
    
    # Quick statistics
    st.markdown("#### 📈 Today's Statistics:")
    col1, col2, col3, col4 = st.columns(4)
    
    entries_count = len([h for h in st.session_state.plate_history if h['event'] == 'ENTRY'])
    exits_count = len([h for h in st.session_state.plate_history if h['event'] == 'EXIT'])
    
    with col1:
        st.metric("Total Entries", entries_count)
    with col2:
        st.metric("Total Exits", exits_count)
    with col3:
        st.metric("Vehicles Inside", len(st.session_state.vehicles_inside))
    with col4:
        st.metric("Net Change", entries_count - exits_count)


# Tab 3: Recognize Plate
with tab3:
    st.header("Recognize License Plate")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Enter License Plate")
        test_plate = st.text_input(
            "Enter license plate to check",
            placeholder="e.g., MH 12 AB 1234",
            key='test_plate'
        )

        if st.button("🔍 Check Plate", use_container_width=True):
            if test_plate:
                cleaned_plate = clean_license_plate(test_plate)

                st.markdown("### Entered Plate Number:")
                st.markdown(f"# `{cleaned_plate}`")

                has_access = check_access(cleaned_plate, st.session_state.known_plates)

                if has_access:
                    st.success("✅ ACCESS GRANTED - Vehicle Recognized")
                    st.balloons()
                else:
                    st.error("❌ ACCESS DENIED - Unknown Vehicle")

                st.session_state.plate_history.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'plate': cleaned_plate,
                    'event': 'SCAN',
                    'status': 'Authorized' if has_access else 'Unauthorized',
                    'duration': '-'
                })

                st.divider()
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Status", "Authorized" if has_access else "Unauthorized")
                with col_b:
                    st.metric("Database Match", "Yes" if has_access else "No")
            else:
                st.warning("Please enter a license plate number.")

    with col2:
        st.subheader("Quick Reference")
        st.info("""
        **How it works:**
        1. Enter a license plate number
        2. System checks against trained database
        3. Access granted if plate is recognized
        4. All checks are logged in history
        """)


# Tab 4: Known Plates
with tab4:
    st.header("Known License Plates Database")

    if st.session_state.known_plates:
        plates_df = pd.DataFrame({
            'Plate Number': sorted(list(st.session_state.known_plates)),
            'Status': ['Active'] * len(st.session_state.known_plates)
        })

        search = st.text_input("🔍 Search plates", "")
        if search:
            filtered_df = plates_df[plates_df['Plate Number'].str.contains(search.upper())]
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.dataframe(plates_df, use_container_width=True)

        csv = plates_df.to_csv(index=False)
        st.download_button("📥 Download Database", csv, "known_plates.csv", "text/csv")

        st.divider()
        plate_to_remove = st.selectbox("Select plate to remove", sorted(list(st.session_state.known_plates)))

        if st.button("🗑️ Remove Selected Plate"):
            st.session_state.known_plates.remove(plate_to_remove)
            st.success(f"Removed {plate_to_remove}")
            st.rerun()
    else:
        st.info("No plates in database yet. Add plates in the 'Get Data' tab.")


# Tab 5: History
with tab5:
    st.header("📋 Recognition & Entry/Exit History")

    if st.session_state.plate_history:
        history_df = pd.DataFrame(st.session_state.plate_history)

        col1, col2, col3 = st.columns(3)
        
        with col1:
            event_filter = st.multiselect(
                "Filter by event type",
                ['ENTRY', 'EXIT', 'SCAN'],
                default=['ENTRY', 'EXIT', 'SCAN']
            )

        with col2:
            status_filter = st.multiselect(
                "Filter by status",
                history_df['status'].unique().tolist(),
                default=history_df['status'].unique().tolist()
            )

        with col3:
            if st.button("🗑️ Clear History", use_container_width=True):
                st.session_state.plate_history = []
                st.rerun()

        filtered_history = history_df[
            (history_df['event'].isin(event_filter)) & 
            (history_df['status'].isin(status_filter))
        ]
        
        # Display with better formatting
        st.dataframe(filtered_history, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📊 Statistics")

        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Events", len(history_df))
        with col2:
            entries = len(history_df[history_df['event'] == 'ENTRY'])
            st.metric("Total Entries", entries)
        with col3:
            exits = len(history_df[history_df['event'] == 'EXIT'])
            st.metric("Total Exits", exits)
        with col4:
            scans = len(history_df[history_df['event'] == 'SCAN'])
            st.metric("Total Scans", scans)
        with col5:
            authorized = len(history_df[history_df['status'] == 'Authorized'])
            st.metric("Authorized Access", authorized)

        st.divider()
        st.subheader("🚗 Vehicle Summary")
        
        # Summary of each vehicle
        vehicle_summary = []
        for plate in history_df['plate'].unique():
            plate_events = history_df[history_df['plate'] == plate]
            entries = len(plate_events[plate_events['event'] == 'ENTRY'])
            exits = len(plate_events[plate_events['event'] == 'EXIT'])
            status = "INSIDE" if entries > exits else "OUTSIDE"
            
            vehicle_summary.append({
                'License Plate': plate,
                'Entries': entries,
                'Exits': exits,
                'Current Status': status,
                'Last Event': plate_events.iloc[-1]['event'],
                'Last Timestamp': plate_events.iloc[-1]['timestamp']
            })
        
        summary_df = pd.DataFrame(vehicle_summary)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        csv = filtered_history.to_csv(index=False)
        st.download_button("📥 Download History", csv, "recognition_history.csv", "text/csv")
    else:
        st.info("No history yet. Scan plates in the 'Entry/Exit Board' or 'Recognize Plate' tabs.")

st.divider()
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "<p>License Plate Recognition & Entry/Exit System | Built with Streamlit</p>"
    "<p>💡 Tip: Add authorized plates, then use Entry/Exit Board to track vehicles!</p>"
    "</div>",
    unsafe_allow_html=True
)