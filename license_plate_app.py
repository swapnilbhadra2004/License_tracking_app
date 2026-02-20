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


# Main UI
st.title("🚗 License Plate Recognition System")
st.markdown("**Recognize license plates automatically**")

# Sidebar
with st.sidebar:
    st.divider()
    st.markdown("### 📊 Statistics")
    st.metric("Known Plates", len(st.session_state.known_plates))
    st.metric("History Records", len(st.session_state.plate_history))

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📚 Get Data", "🔍 Recognize Plate", "📋 Known Plates", "📈 History"])

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

# Tab 2: Recognize Plate
with tab2:
    st.header("Recognize License Plate")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Enter License Plate")
        test_plate = st.text_input(
            "Enter license plate to check",
            placeholder="e.g., MH 12 AB 1234",
            key='test_plate'
        )

        if st.button("🚀 Check Plate", use_container_width=True):
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
                    'access': 'Granted' if has_access else 'Denied'
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


# Tab 3: Known Plates
with tab3:
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
        st.info("No plates in database yet. Add plates in the 'Train Model' tab.")

# Tab 4: History
with tab4:
    st.header("Recognition History")

    if st.session_state.plate_history:
        history_df = pd.DataFrame(st.session_state.plate_history)

        col1, col2 = st.columns(2)
        with col1:
            filter_access = st.multiselect(
                "Filter by access",
                ['Granted', 'Denied'],
                default=['Granted', 'Denied']
            )

        with col2:
            if st.button("🗑️ Clear History"):
                st.session_state.plate_history = []
                st.rerun()

        filtered_history = history_df[history_df['access'].isin(filter_access)]
        st.dataframe(filtered_history, use_container_width=True)

        st.divider()
        st.subheader("Statistics")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Scans", len(history_df))
        with col2:
            granted = len(history_df[history_df['access'] == 'Granted'])
            st.metric("Access Granted", granted)
        with col3:
            denied = len(history_df[history_df['access'] == 'Denied'])
            st.metric("Access Denied", denied)

        csv = filtered_history.to_csv(index=False)
        st.download_button("📥 Download History", csv, "recognition_history.csv", "text/csv")
    else:
        st.info("No recognition history yet. Check some plates in the 'Recognize Plate' tab.")

st.divider()
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "<p>License Plate Recognition System | Built with Streamlit</p>"
    "<p>💡 Tip: Train your model with known plates, then recognize new vehicles automatically!</p>"
    "</div>",
    unsafe_allow_html=True
)