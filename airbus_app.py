import streamlit as st
import pandas as pd
import numpy as np
import os

# --- 1. CONFIGURATION ---
if os.path.exists("airbus_logo.png"):
    app_icon = "airbus_logo.png"
else:
    app_icon = "✈️"

st.set_page_config(
    page_title="A321 neo Fuel Calc",
    page_icon=app_icon,
    layout="wide"
)

# --- 2. HEADER FUNCTION ---
def render_header():
    header_html = """
    <style>
        .tech-header-container {
            position: fixed; top: 0; left: 0; width: 100%;
            height: 3.5rem; background-color: #00205B;
            color: #FFFFFF; z-index: 50; display: flex;
            align-items: center; justify-content: space-between;
            padding: 0 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            font-family: Helvetica, Arial, sans-serif; 
            border-bottom: 3px solid #95A5A6;
        }
        .block-container { padding-top: 5rem !important; }
        header[data-testid="stHeader"] { background-color: transparent; }
        .tech-text {
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.9rem; color: #00FF00;
            display: flex; gap: 20px; letter-spacing: 1px;
        }
        .ref-badge {
            background-color: #FFFFFF; color: #00205B;
            padding: 2px 8px; border-radius: 2px;
            font-weight: bold; font-size: 0.8rem;
        }
        @media (max-width: 700px) {
            .tech-header-container { padding: 0 15px; }
            .tech-text { font-size: 0.75rem; gap: 10px; }
        }
    </style>
    
    <div class="tech-header-container">
        <div style="display:flex;align-items:center;gap:10px;">
            <div class="ref-badge">A321neo</div>
            <span style="font-weight:bold;">FUEL CALC</span>
        </div>
        <div class="tech-text">
            <span>AMM 12-11-28</span>
            <span style="color:cyan;">|</span>
            <span>MLI CHECK</span>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

render_header()
st.title("Airbus A321 neo Fuel Calculator")
st.caption("Magnetic Level Indicator (MLI) Calculation")

# --- 3. DATA LOADER ---
@st.cache_data
def load_data():
    file_name = 'Airbus_Fuel_Data.csv'
    if not os.path.exists(file_name): return None, "File Missing"

    try:
        db = pd.read_csv(file_name)
        # Clean Data
        if 'Roll' in db.columns: 
            db['Roll'] = pd.to_numeric(db['Roll'], errors='coerce').round(2)
        if 'Reading' in db.columns:
            db['Reading'] = pd.to_numeric(db['Reading'], errors='coerce').round(1)
        if 'Qty' in db.columns:
            db['Qty'] = pd.to_numeric(db['Qty'], errors='coerce')
            
        for col in ['MLI', 'Pitch', 'Tank']:
            if col in db.columns: 
                db[col] = db[col].astype(str).str.strip()
                # Remove "nan" strings if they exist
                db = db[db[col].str.lower() != 'nan']
        return db, None
    except Exception as e:
        return None, str(e)

df_db, error_msg = load_data()

# --- 4. SESSION STATE ---
for k in ['left_qty', 'center_qty', 'right_qty', 'act_qty']:
    if k not in st.session_state: st.session_state[k] = 0

# --- 5. LOGIC ---
def get_fuel_qty(mli, pitch, roll, reading, tank):
    if df_db is None: return None
    
    subset = df_db[
        (df_db['Tank'] == tank) &
        (df_db['MLI'] == mli) &
        (df_db['Pitch'] == pitch) &
        (np.isclose(df_db['Roll'], roll, atol=0.01))
    ]
    exact = subset[np.isclose(subset['Reading'], reading, atol=0.01)]
    if not exact.empty: return exact.iloc[0]['Qty']
    return None

if df_db is None:
    st.warning("⚠️ **Database Missing**")
    st.info("Please ensure 'Airbus_Fuel_Data.csv' is uploaded.")
    st.stop()

# --- 7. SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    if st.button("Reset All"):
        # This was the line causing the error - fixed below
        for k in ['left_qty', 'center_qty', 'right_qty', 'act_qty']:
            st.session_state[k] = 0
        st.rerun()

# --- 8. TOTALIZER PLACEHOLDER ---
totalizer_container = st.empty()

# --- 9. INPUT TABS ---
t1, t2, t3 = st.tabs(["Left Wing", "Center / ACT", "Right Wing"])

def render_mli_input(label, key, tank_name):
    st.subheader(f"{label}")
    
    # Empty Checkbox (Defaults to True)
    if st.checkbox(f"{label} Empty", value=True, key=f"{key}_empty"):
        st.session_state[f"{key}_qty"] = 0
        st.info("0 KG")
        return

    # 1. Select MLI
    tank_data = df_db[df_db['Tank'] == tank_name]
    valid_mlis = sorted(tank_data['MLI'].unique())
    
    c1, c2 = st.columns(2)
    with c1:
        mli_val = st.selectbox(f"MLI Number", valid_mlis, key=f"{key}_mli")
    
    # 2. Select Pitch
    def safe_sort_key(val):
        try: return (0, float(val))
        except: return (1, str(val))

    mli_scope = tank_data[tank_data['MLI'] == mli_val]
    valid_pitches = sorted(mli_scope['Pitch'].unique(), key=safe_sort_key)
    
    # Default Pitch to 0 if possible
    p_index = 0
    for i, p in enumerate(valid_pitches):
        if str(p).replace('.0','').strip() == "0": p_index = i

    with c2:
        p_label = "Attitude Monitor" if tank_name == "Center" else "Pitch Attitude"
        pitch_val = st.selectbox(p_label, valid_pitches, index=p_index, key=f"{key}_pitch")

    # 3. Select Roll
    pitch_scope = mli_scope[mli_scope['Pitch'] == pitch_val]
    valid_rolls = sorted(pitch_scope['Roll'].unique())
    
    c3, c4 = st.columns(2)
    with c3:
        if len(valid_rolls) > 1 or (len(valid_rolls)==1 and valid_rolls[0] != 0):
            r_index = 0
            if 0.0 in valid_rolls: r_index = valid_rolls.index(0.0)
            roll_val = st.selectbox("Roll Attitude", valid_rolls, index=r_index, key=f"{key}_roll")
        else:
            roll_val = 0.0
            st.info("Roll: 0.0 (Fixed)")

    # 4. Select Reading
    final_scope = pitch_scope[np.isclose(pitch_scope['Roll'], roll_val, atol=0.01)]
    valid_readings = sorted(final_scope['Reading'].unique())
    
    with c4:
        if not valid_readings:
            st.warning("No Data")
            reading_val = 0.0
        else:
            reading_val = st.selectbox("Reading