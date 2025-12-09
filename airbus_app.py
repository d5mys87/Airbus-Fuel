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

# --- 2. HEADER FUNCTION (Airbus Style) ---
def render_header():
    header_html = """
    <style>
        /* AIRBUS HEADER - Dark Blue */
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
        
        /* ECAM TEXT STYLE */
        .tech-text {
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.9rem; color: #00FF00; /* ECAM Green */
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
    
    if not os.path.exists(file_name):
        return None, "File Missing"

    try:
        db = pd.read_csv(file_name)
        # Clean Data
        for col in ['Roll', 'Reading', 'Qty']:
            if col in db.columns: db[col] = pd.to_numeric(db[col], errors='coerce')
        for col in ['MLI', 'Pitch', 'Tank']:
            if col in db.columns: db[col] = db[col].astype(str).str.strip()
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
    if not exact.empty:
        return exact.iloc[0]['Qty']
    return None

# --- 6. NO DATA WARNING ---
if df_db is None:
    st.warning("⚠️ **Database Missing**")
    st.info("Please create `Airbus_Fuel_Data.csv` or run the builder script.")
    st.stop()

# --- 7. SIDEBAR ---
with st.sidebar:
    st.header("Flight Parameters")
    
    avail_pitches = sorted(df_db['Pitch'].unique())
    p_index = 0
    for i, p in enumerate(avail_pitches):
        if "0.0" in p: p_index = i
    g_pitch = st.selectbox("Pitch Attitude", avail_pitches, index=p_index)
    
    avail_rolls = sorted(df_db['Roll'].unique())
    r_index = 0
    if 0.0 in avail_rolls: r_index = avail_rolls.index(0.0)
    g_roll = st.selectbox("Roll Attitude", avail_rolls, index=r_index)
    
    st.markdown("---")
    if st.button("Reset All"):
        for k in ['left_qty', 'center_qty', 'right_qty', 'act_qty']:
            st.session_state[k] = 0
        st.rerun()

# --- 8. TOTALIZER PLACEHOLDER (Always on View) ---
# We create an empty container here, and fill it at the VERY END of the script
totalizer_container = st.empty()

# --- 9. TABS ---
# Removed Totalizer Tab, only Input Tabs remain
t1, t2, t3 = st.tabs(["Left Wing", "Center / ACT", "Right Wing"])

def render_mli_input(label, key, tank_name):
    st.subheader(f"{label}")
    
    if st.checkbox(f"{label} Empty", value=True, key=f"{key}_empty"):
        st.session_state[f"{key}_qty"] = 0
        st.info("0 KG")
        return

    c1, c2 = st.columns(2)
    with c1:
        valid_mlis = sorted(df_db[df_db['Tank'] == tank_name]['MLI'].unique())
        mli_val = st.selectbox(f"MLI Number", valid_mlis, key=f"{key}_mli")
        
    with c2:
        subset = df_db[
            (df_db['Tank'] == tank_name) &
            (df_db['MLI'] == mli_val) &
            (df_db['Pitch'] == g_pitch) &
            (np.isclose(df_db['Roll'], g_roll, atol=0.01))
        ]
        valid_readings = sorted(subset['Reading'].unique())
        
        if not valid_readings:
            st.warning("No Data")
            reading_val = 0.0
        else:
            reading_val = st.selectbox("Reading (mm)", valid_readings, key=f"{key}_read")
            
    if reading_val > 0:
        qty = get_fuel_qty(mli_val, g_pitch, g_roll, reading_val, tank_name)
        if qty is not None:
            st.success(f"✅ {int(qty)} KG")
            st.session_state[f"{key}_qty"] = qty
        else:
            st.error("Not Found")
            st.session_state[f"{key}_qty"] = 0

with t1: render_mli_input("Left Wing", "left", "Left")
with t3: render_mli_input("Right Wing", "right", "Right")

with t2:
    st.write("### Center Tank")
    render_mli_input("Center Tank", "center", "Center")
    st.markdown("---")
    st.write("### ACT (Rear)")
    render_mli_input("ACT", "act", "ACT")

# --- 10. UPDATE THE TOTALIZER (ECAM STYLE) ---
# This runs last, but updates the container we created at the top
total_fuel = (
    st.session_state.left_qty + 
    st.session_state.center_qty + 
    st.session_state.right_qty + 
    st.session_state.act_qty
)

ecam_html = f"""
<style>
    /* ECAM PANEL CONTAINER */
    .ecam-panel {{
        background-color: #000000;
        border: 3px solid #555;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        font-family: 'Consolas', 'Courier New', monospace;
        color: #00FF00; /* ECAM Green */
        box-shadow: inset 0 0 20px rgba(0, 50, 0, 0.5);
        display: flex;
        flex-direction: column;
        align-items: center;
    }}
    
    /* TOTAL FOB SECTION */
    .ecam-header {{
        width: 100%;
        display: flex;
        justify-content: space-between;
        border-bottom: 2px solid #555;
        padding-bottom: 5px;
        margin-bottom: 10px;
    }}
    .ecam-label {{ color: #00FFFF; font-size: 1.1rem; font-weight: bold; letter-spacing: 1px; }}
    .ecam-total {{ font-size: 2.5rem; font-weight: bold; color: #00FF00; line-height: 1; }}
    .ecam-unit {{ font-size: 1.2rem; color: #FFFFFF; margin-left: 5px; }}

    /* INDIVIDUAL TANKS ROW */
    .ecam-tanks {{
        width: 100%;
        display: flex;
        justify-content: space-around;
        font-size: 1.1rem;
        color: #FFFFFF;
    }}
    .tank-box {{ display: flex; flex-direction: column; align-items: center; }}
    .tank-name {{ color: #00FFFF; font-size: 0.9rem; margin-bottom: 2px; }}
    .tank-val {{ font-weight: bold; font-size: 1.3rem; }}
    
    /* ACT SECTION */
    .ecam-act {{
        margin-top: 10px;
        border-top: 1px dashed #333;
        padding-top: 5px;
        width: 100%;
        text-align: center;
        color: #888;
    }}
    .act-active {{ color: #00FFFF; }}
</style>

<div class="ecam-panel">
    <div class="ecam-header">
        <div style="display:flex; flex-direction:column; justify-content:center;">
            <span class="ecam-label">FOB</span>
            <span style="font-size:0.8rem; color:#888;">TOTAL FUEL</span>
        </div>
        <div style="display:flex; align-items:baseline;">
            <span class="ecam-total">{int(total_fuel):,}</span>
            <span class="ecam-unit">KG</span>
        </div>
    </div>

    <div class="ecam-tanks">
        <div class="tank-box">
            <span class="tank-name">LEFT</span>
            <span class="tank-val">{int(st.session_state.left_qty)}</span>
        </div>
        <div class="tank-box">
            <span class="tank-name">CTR</span>
            <span class="tank-val">{int(st.session_state.center_qty)}</span>
        </div>
        <div class="tank-box">
            <span class="tank-name">RIGHT</span>
            <span class="tank-val">{int(st.session_state.right_qty)}</span>
        </div>
    </div>

    <div class="ecam-act {'act-active' if st.session_state.act_qty > 0 else ''}">
        ACT: {int(st.session_state.act_qty)}
    </div>
</div>
"""

totalizer_container.markdown(ecam_html, unsafe_allow_html=True)