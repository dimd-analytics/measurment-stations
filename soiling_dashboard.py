import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Dynamic Soiling Economic Optimization",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DUMMY DATA FALLBACK ---
@st.cache_data
def generate_dummy_data():
    """Generates synthetic dataframe for UI testing if the actual path is missing or dummy mode is on."""
    dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq='D')
    
    all_stations = []
    station_names = ['Darb (Dummy)', 'Samtah (Dummy)', 'Riyadh (Dummy)']
    
    for station in station_names:
        sr = []
        rain = []
        current_sr = 1.0
        decay_rate = np.random.uniform(0.001, 0.003)
        
        for _ in dates:
            # 3% chance of rain
            if np.random.rand() < 0.03:
                r = np.random.uniform(1.0, 15.0)
                rain.append(r)
                current_sr = 1.0 # wash panel
            else:
                rain.append(0.0)
                current_sr = max(0.4, current_sr - decay_rate)
                
            sr.append(current_sr)
            
        df = pd.DataFrame({
            'Station_Name': station,
            'SR': sr,
            'Rain_mm_Tot': rain
        }, index=dates)
        all_stations.append(df)
        
    return pd.concat(all_stations)

# --- DATA INGESTION & PREPROCESSING ---
@st.cache_data
def load_and_process_data(root_path_str):
    root_path = Path(root_path_str)
    
    if not root_path.exists():
        st.warning(f"Warning: Directory '{root_path}' not found. Loading dummy data for UI demonstration.")
        return generate_dummy_data()
        
    all_dfs = []
    
    # Top-level folders are Station Names
    for station_dir in root_path.iterdir():
        if not station_dir.is_dir():
            continue
            
        station_name = station_dir.name
        data_dir = station_dir / ".03 Data sets"
        
        if not data_dir.exists() or not data_dir.is_dir():
            continue
            
        # Try to find all .csv and .xlsx
        # IGNORE "Raw", Prioritize "Final" -> We will collect all, sort by 'Final' presence then parse
        file_paths = []
        for file in data_dir.rglob('*'):
            if file.is_file() and file.suffix in ['.csv', '.xlsx']:
                # Strictly ignore 'Raw' in the path parts
                if 'Raw' in file.parts:
                    continue
                file_paths.append(file)
                
        if not file_paths:
            continue
            
        # Prioritize 'Final'
        file_paths.sort(key=lambda p: 'Final' in p.parts, reverse=True)
        
        station_df_list = []
        for file in file_paths:
            try:
                if file.suffix == '.csv':
                    temp_df = pd.read_csv(file)
                else:
                    temp_df = pd.read_excel(file)
                    
                # Basic check for required columns
                required_cols = {'TIMESTAMP', 'ISCClean_Avg', 'ISCSoil_Avg', 'Rain_mm_Tot'}
                if not required_cols.issubset(temp_df.columns):
                    continue
                
                # Preprocessing
                # Set TIMESTAMP column as a DatetimeIndex and sort
                temp_df['TIMESTAMP'] = pd.to_datetime(temp_df['TIMESTAMP'])
                temp_df.set_index('TIMESTAMP', inplace=True)
                temp_df.sort_index(inplace=True)
                
                # Extract specific columns
                temp_df = temp_df[['ISCClean_Avg', 'ISCSoil_Avg', 'Rain_mm_Tot']]
                
                # Nighttime Filter: Drop rows where ISCClean_Avg < 5 mA
                temp_df = temp_df[temp_df['ISCClean_Avg'] >= 5]
                
                # Calculate Soiling Ratio (SR): ISCSoil_Avg / ISCClean_Avg
                temp_df['SR'] = temp_df['ISCSoil_Avg'] / temp_df['ISCClean_Avg']
                # Clamp the max value at 1.0
                temp_df['SR'] = temp_df['SR'].clip(upper=1.0)
                
                # Resample: Daily Frequency ('D')
                # mean for SR, sum for Rain
                resampled_df = temp_df.resample('D').agg({
                    'SR': 'mean',
                    'Rain_mm_Tot': 'sum'
                }).dropna()
                
                station_df_list.append(resampled_df)
                
            except Exception as e:
                # Silently skip file read/processing errors for the POC
                continue
                
        if station_df_list:
            combined_station_df = pd.concat(station_df_list)
            # Remove duplicated timestamps if multiple files overlap (keep last)
            combined_station_df = combined_station_df[~combined_station_df.index.duplicated(keep='last')]
            combined_station_df.sort_index(inplace=True)
            combined_station_df['Station_Name'] = station_name
            all_dfs.append(combined_station_df)
            
    if all_dfs:
        merged_df = pd.concat(all_dfs)
        return merged_df
    else:
        st.warning("Warning: No valid datasets found matching the criteria. Loading dummy data.")
        return generate_dummy_data()

# --- FINANCIAL LOGIC ---
def apply_financial_model(df, capacity_mw, yield_kwh, tariff, cleaning_cost):
    """Calculates cumulative loss and determines cleaning triggers."""
    df = df.copy()
    
    # Calculate daily max potential revenue
    max_daily_revenue = capacity_mw * yield_kwh * tariff
    
    # Daily Revenue Loss ($) = (1.0 - SR) * Max Daily Revenue
    df['Daily_Revenue_Loss'] = (1.0 - df['SR']) * max_daily_revenue
    
    cumulative_loss = []
    recommend_cleaning = []
    
    current_loss = 0.0
    
    for i in range(len(df)):
        daily_loss = df['Daily_Revenue_Loss'].iloc[i]
        rain = df['Rain_mm_Tot'].iloc[i]
        
        current_loss += daily_loss
        
        clean_now = False
        
        # Check thresholds / natural cleaning
        if current_loss >= cleaning_cost:
            clean_now = True
            current_loss = 0.0 # Reset
        elif rain > 0:
            current_loss = 0.0 # Reset from natural wash
            
        cumulative_loss.append(current_loss)
        recommend_cleaning.append(clean_now)
        
    df['Cumulative_Loss'] = cumulative_loss
    df['Recommend_Cleaning'] = recommend_cleaning
    
    return df

# --- MAIN APP ---
def main():
    # --- HEADER ---
    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        # Local text placeholder instead of an external image URL which can cause network hangs
        st.markdown("<h1 style='text-align: center;'>☀️</h1><p style='text-align: center; font-weight: bold;'>LOGO</p>", unsafe_allow_html=True)
    with col_title:
        st.title("Dynamic Soiling Economic Optimization Model")
        st.markdown("Quantifying the financial impact of dust accumulation to optimize manual cleaning schedules.")
        
    st.divider()

    # --- SIDEBAR: USER INPUTS ---
    st.sidebar.header("⚙️ Optimization Parameters")
    
    capacity_mw = st.sidebar.number_input("Plant Capacity (MW)", value=500, step=50)
    yield_kwh = st.sidebar.number_input("Expected Daily yield (kWh/MW)", value=4500, step=100)
    tariff = st.sidebar.number_input("PPA Tariff ($/kWh)", value=0.02, format="%.3f")
    cleaning_cost = st.sidebar.number_input("Cleaning Cost ($)", value=15000, step=1000)
    
    st.sidebar.divider()
    st.sidebar.header("🔧 Data Source")
    use_dummy_data = st.sidebar.checkbox("Use Dummy Data (Fast Load)", value=True, help="Toggle to use realistic generated data instead of parsing heavy local files. Ideal for Github deployment.")
    
    # --- LOAD DATA ---
    root_path = r"C:\Users\khalAA0A\Dev\measurment stations\Solar Sample"
    with st.spinner("Loading data..."):
        if use_dummy_data:
            raw_df = generate_dummy_data()
        else:
            raw_df = load_and_process_data(root_path)
    
    station_list = raw_df['Station_Name'].unique()
    selected_station = st.sidebar.selectbox("Select Station", station_list)
    
    # Filter by selected station
    station_df = raw_df[raw_df['Station_Name'] == selected_station].copy()
    
    # Apply Financial calculations
    final_df = apply_financial_model(station_df, capacity_mw, yield_kwh, tariff, cleaning_cost)
    
    # --- TABS: DASHBOARD vs DATA ---
    tab_dash, tab_data = st.tabs(["📊 Dashboard", "🗄️ Dataset View"])
    
    with tab_dash:
        # --- KPIs ---
        # Current/Recent values
        latest_sr = final_df['SR'].iloc[-1]
        
        # Estimated money lost this month (last 30 days)
        # Using .loc to avoid pandas .last() deprecation warning
        cutoff_date = final_df.index.max() - pd.Timedelta(days=30)
        last_30 = final_df.loc[final_df.index >= cutoff_date]
        monthly_loss = last_30['Daily_Revenue_Loss'].sum()
        
        # Next recommended cleaning date (first True looking forward, or just upcoming)
        cleaning_dates = final_df[final_df['Recommend_Cleaning']].index
        if len(cleaning_dates) > 0:
            last_clean_date = cleaning_dates[-1]
        else:
            last_clean_date = None

        col1, col2, col3 = st.columns(3)
        col1.metric("Current Avg Soiling Ratio", f"{latest_sr*100:.1f}%")
        col2.metric("Est. Revenue Lost (Last 30 Days)", f"${monthly_loss:,.0f}")
        
        if last_clean_date:
            col3.metric("Last 'Clean Now' Trigger", last_clean_date.strftime("%Y-%m-%d"))
        else:
            col3.metric("Next Recommended Cleaning", "N/A - Threshold Not Met")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- CHART 1: Soiling Decay & Rain Events ---
        st.subheader("Soiling Decay vs Natural Rain Events")
        
        fig1 = go.Figure()
        
        # Soiling Ratio Line
        fig1.add_trace(go.Scatter(
            x=final_df.index, y=final_df['SR'],
            mode='lines',
            name='Soiling Ratio (SR)',
            line=dict(color='#ff9900', width=2)
        ))
        
        # Rain Highlights
        rain_days = final_df[final_df['Rain_mm_Tot'] > 0]
        for date, row in rain_days.iterrows():
            fig1.add_vline(x=date, line_width=1, line_dash="dash", line_color="blue", opacity=0.4)
            
        fig1.update_layout(
            yaxis_title="Soiling Ratio (0.0 to 1.0)",
            xaxis_title="Date",
            template="plotly_dark", # Sleek dark mode
            hovermode="x unified",
            margin=dict(l=40, r=40, t=40, b=40)
        )
        # Add a dummy trace for legend
        fig1.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                                  line=dict(color='blue', width=1, dash='dash'), 
                                  name='Rain > 0mm (Natural Wash)'))
                                  
        st.plotly_chart(fig1, use_container_width=True)

        # --- CHART 2: The Financial Tipping Point ---
        st.subheader("Financial Tipping Point - Cumulative Loss")
        
        fig2 = go.Figure()
        
        # Area chart for cumulative loss
        fig2.add_trace(go.Scatter(
            x=final_df.index, y=final_df['Cumulative_Loss'],
            mode='lines',
            fill='tozeroy',
            name='Cumulative Loss ($)',
            line=dict(color='#ff4b4b', width=2),
            fillcolor='rgba(255, 75, 75, 0.3)'
        ))
        
        # Cleaning Cost Threshold line
        fig2.add_hline(
            y=cleaning_cost, 
            line_width=2, 
            line_dash="dash", 
            line_color="red",
            annotation_text="Cleaning Cost Threshold", 
            annotation_position="top left"
        )
        
        # Scatter markers for Clean Now triggers
        clean_now_df = final_df[final_df['Recommend_Cleaning']]
        fig2.add_trace(go.Scatter(
            x=clean_now_df.index, y=clean_now_df['Cumulative_Loss'],
            mode='markers',
            name='Clean Now Trigger',
            marker=dict(color='red', size=10, symbol='circle-open', line=dict(width=2))
        ))
        
        fig2.update_layout(
            yaxis_title="Loss Amount ($)",
            xaxis_title="Date",
            template="plotly_dark",
            hovermode="x unified",
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tab_data:
        st.subheader("Raw Data & Processing Audit")
        st.markdown(f"Currently viewing data for **{selected_station}**.")
        
        st.dataframe(
            final_df.style.format({
                'SR': '{:.3f}',
                'Rain_mm_Tot': '{:.1f}',
                'Daily_Revenue_Loss': '${:,.2f}',
                'Cumulative_Loss': '${:,.2f}'
            }),
            use_container_width=True
        )

if __name__ == "__main__":
    main()
