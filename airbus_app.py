import streamlit as st
import pandas as pd
import numpy as np
import os

# --- CONFIGURATION ---
if os.path.exists("airbus_logo.png"): app_icon = "airbus_logo.png"
else: app_icon = "✈️"

st.set_page_config(page_title="A321 neo Fuel Calc", page_icon=app_icon, layout="wide")

# --- HEADER ---
def render_header():
    st.markdown("""
    <style>
        .tech-header-container {
            position: fixed; top: 0; left: 0; width: 100%;
            height: 3.5rem; background-color: #00205B;
            color: #FFFFFF; z-index: 50; display: flex;
            align-items: center; justify-content: space-between;
            padding: 0 40px; border-bottom: 3px solid #95A5A6;
            font-family: Helvetica, Arial, sans-serif;
        }
        .block-container { padding-top: 5rem !important; }
        header[data-testid="stHeader"] { background-color: transparent; }
        .tech-text {
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.9rem; color: #00FF00; letter-spacing: 1px;
        }
    </style>
    <div class="tech-header-container">
        <div style="font-weight:bold; font-size:1.2rem;">A321neo FUEL CALC</div>
        <div class="tech-text">AMM 12-11-28 | MLI CHECK</div>
    </div>
    """, unsafe_allow_html=True)

render_header()

# --- DATA LOADER ---
@st.cache_data
def load_data():
    if not os.path.exists('Airbus_Fuel_Data.csv'): return None
    db = pd.read_csv('Airbus_Fuel_Data.csv')
    db['Roll'] = pd.to_numeric(db['Roll'], errors='coerce')
    db['Reading'] = pd.to_numeric(db['Reading'], errors='coerce')
    db['Qty'] = pd.to_numeric(db['Qty'], errors='coerce')
    db['MLI'] = db['MLI'].astype(str).str.strip()
    db['Pitch'] = db['Pitch'].astype(str).str.strip()
    return db

df_db = load_data()
if df_db is None:
    st.error("⚠️ Database Missing. Please run `python build_db.py` first.")
    st.stop()

# --- SESSION ---
for k in ['left_qty', 'center_qty', 'right_qty', 'act_qty']:
    if k not in st.session_state: st.session_state[k] = 0

# --- LOGIC ---
def get_fuel_qty(tank, mli, pitch, roll, reading):
    subset = df_db[
        (df_db['Tank'] == tank) & (df_db['MLI'] == mli) & 
        (df_db['Pitch'] == pitch) & 
        (np.isclose(df_db['Roll'], roll, atol=0.01))
    ]
    match = subset[np.isclose(subset['Reading'], reading, atol=0.01)]
    if not match.empty: return match.iloc[0]['Qty']
    return None

# --- TABS ---
t1, t2, t3, t4 = st.tabs(["Left Wing", "Center / ACT", "Right Wing", "Totalizer"])

def render_tab(label, key, tank_name):
    st.subheader(label)
    
    if st.checkbox(f"{label} Empty", value=True, key=f"{key}_empty"):
        st.session_state[f"{key}_qty"] = 0
        st.info("0 KG")
        return

    valid_mlis = sorted(df_db[df_db['Tank'] == tank_name]['MLI'].unique())
    mli = st.selectbox("MLI Stick", valid_mlis, key=f"{key}_mli")
    
    scope = df_db[(df_db['Tank'] == tank_name) & (df_db['MLI'] == mli)]
    
    c1, c2 = st.columns(2)
    with c1:
        valid_pitches = sorted(scope['Pitch'].unique(), key=lambda x: float(x))
        p_label = "Attitude Monitor Unit" if tank_name == "Center" else "Pitch Attitude"
        pitch = st.selectbox(p_label, valid_pitches, key=f"{key}_pitch")
        
    with c2:
        valid_rolls = sorted(scope['Roll'].unique())
        if len(valid_rolls) <= 1 and valid_rolls[0] == 0:
            roll = 0.0
            st.info("Roll: 0.0 (Fixed)")
        else:
            roll = st.selectbox("Roll Attitude", valid_rolls, key=f"{key}_roll")

    final_scope = scope[
        (scope['Pitch'] == pitch) & 
        (np.isclose(scope['Roll'], roll, atol=0.01))
    ]
    valid_readings = sorted(final_scope['Reading'].unique())
    
    if not valid_readings:
        st.warning("No Data")
        return

    reading = st.selectbox("Stick Reading (mm)", valid_readings, key=f"{key}_read")
    
    qty = get_fuel_qty(tank_name, mli, pitch, roll, reading)
    if qty is not None:
        st.success(f"✅ {int(qty)} KG")
        st.session_state[f"{key}_qty"] = qty
    else:
        st.error("Data Not Found")

with t1: render_tab("Left Wing", "left", "Left")
with t3: render_tab("Right Wing", "right", "Right")

with t2:
    st.write("### Center Tank")
    render_tab("Center Tank", "center", "Center")
    st.markdown("---")
    if not df_db[df_db['Tank']=='ACT'].empty:
        render_tab("ACT", "act", "ACT")
    else:
        st.info("ACT Data not available in current database.")

total = sum([st.session_state[k] for k in ['left_qty', 'center_qty', 'right_qty', 'act_qty']])

with t4:
    st.markdown(f"""
    <div style="background-color:black; color:#0F0; padding:20px; border-radius:10px; text-align:center; font-family:monospace; border:4px solid #444;">
        <div style="color:cyan; font-size:1.5rem; margin-bottom:10px;">FOB (TOTAL)</div>
        <div style="font-size:4rem; font-weight:bold;">{int(total):,} KG</div>
        <hr style="border-color:#333;">
        <div style="display:flex; justify-content:space-around; color:white; font-size:1.2rem;">
            <div>L: {int(st.session_state.left_qty)}</div>
            <div>CTR: {int(st.session_state.center_qty)}</div>
            <div>R: {int(st.session_state.right_qty)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)