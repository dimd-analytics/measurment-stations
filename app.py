from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="Bankable Soiling Strategy Workbench",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def generate_dummy_data(days: int = 365, seed: int = 42) -> pd.DataFrame:
    """Fallback synthetic daily SR/rain by station when real path is unavailable."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start="2025-01-01", periods=days, freq="D")
    station_names = ["Darb (Dummy)", "Samtah (Dummy)", "Riyadh (Dummy)"]

    all_stations = []
    for station in station_names:
        decay_rate = rng.uniform(0.001, 0.003)
        sr = []
        rain = []
        current_sr = 0.99

        for _ in dates:
            if rng.random() < 0.10:
                r = float(rng.gamma(2.0, 2.8))
                rain.append(r)
                # partial natural wash instead of full instant reset
                current_sr = min(1.0, current_sr + (1 - current_sr) * 0.55)
            else:
                rain.append(0.0)
                current_sr = max(0.72, current_sr - decay_rate)
            sr.append(current_sr)

        all_stations.append(
            pd.DataFrame(
                {
                    "Station_Name": station,
                    "SR": sr,
                    "Rain_mm_Tot": rain,
                },
                index=dates,
            )
        )

    return pd.concat(all_stations)


@st.cache_data
def load_and_process_data(root_path_str: str) -> pd.DataFrame:
    """Original station-folder ingestion with ISCClean/ISCSoil/Rain processing."""
    root_path = Path(root_path_str)
    if not root_path.exists():
        st.warning(f"Directory '{root_path}' not found. Loading dummy data.")
        return generate_dummy_data()

    all_dfs = []
    for station_dir in root_path.iterdir():
        if not station_dir.is_dir():
            continue

        station_name = station_dir.name
        data_dir = station_dir / ".03 Data sets"
        if not data_dir.exists() or not data_dir.is_dir():
            continue

        file_paths = []
        for file in data_dir.rglob("*"):
            if file.is_file() and file.suffix in [".csv", ".xlsx"]:
                if "Raw" in file.parts:
                    continue
                file_paths.append(file)

        if not file_paths:
            continue

        file_paths.sort(key=lambda p: "Final" in p.parts, reverse=True)

        station_df_list = []
        for file in file_paths:
            try:
                temp_df = pd.read_csv(file) if file.suffix == ".csv" else pd.read_excel(file)
                required_cols = {"TIMESTAMP", "ISCClean_Avg", "ISCSoil_Avg", "Rain_mm_Tot"}
                if not required_cols.issubset(temp_df.columns):
                    continue

                temp_df["TIMESTAMP"] = pd.to_datetime(temp_df["TIMESTAMP"])
                temp_df = temp_df.set_index("TIMESTAMP").sort_index()
                temp_df = temp_df[["ISCClean_Avg", "ISCSoil_Avg", "Rain_mm_Tot"]]

                temp_df = temp_df[temp_df["ISCClean_Avg"] >= 5]
                temp_df["SR"] = (temp_df["ISCSoil_Avg"] / temp_df["ISCClean_Avg"]).clip(lower=0.72, upper=1.0)

                resampled_df = temp_df.resample("D").agg({"SR": "mean", "Rain_mm_Tot": "sum"}).dropna()
                station_df_list.append(resampled_df)
            except Exception:
                continue

        if station_df_list:
            combined = pd.concat(station_df_list)
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            combined["Station_Name"] = station_name
            all_dfs.append(combined)

    if not all_dfs:
        st.warning("No valid station datasets found. Loading dummy data.")
        return generate_dummy_data()

    return pd.concat(all_dfs)


@st.cache_data
def enrich_station_context(station_df: pd.DataFrame, seed: int = 13) -> pd.DataFrame:
    """Add baseline/weather/context fields needed for bankability panels."""
    out = station_df.copy().sort_index()
    rng = np.random.default_rng(seed)
    n = len(out)

    day = np.arange(n)
    seasonal = 0.10 * np.sin(2 * np.pi * day / 365)
    out["Irradiance_Norm"] = np.clip(0.78 + seasonal + rng.normal(0, 0.03, n), 0.45, 1.08)

    out["Rain_Intensity_mmph"] = np.where(out["Rain_mm_Tot"] > 0, np.clip(rng.normal(5, 1.8, n), 0.5, None), 0.0)
    out["Rain_Duration_h"] = np.where(out["Rain_mm_Tot"] > 0, np.clip(rng.normal(1.7, 0.6, n), 0.2, None), 0.0)

    outages = np.clip(rng.beta(2, 32, n), 0, 0.20)
    curtailment = np.clip(rng.beta(2, 26, n), 0, 0.12)
    clipping = np.clip(rng.beta(1.8, 35, n), 0, 0.08)

    out["Outages"] = outages
    out["Availability"] = np.clip(1 - outages, 0.82, 1.0)
    out["Curtailment"] = curtailment
    out["Clipping"] = clipping
    out["PR"] = np.clip(0.83 + rng.normal(0, 0.015, n), 0.76, 0.89)

    # Proxy realized SR (for backtesting) close to measured SR, with mild latent error
    out["SR_True"] = np.clip(out["SR"] + rng.normal(0, 0.005, n), 0.72, 1.0)
    return out


def rain_effectiveness(mm: float, intensity: float, duration_h: float, threshold_mm: float, curve_k: float) -> float:
    if mm < threshold_mm:
        return 0.0
    event_strength = (mm - threshold_mm) * np.sqrt(max(intensity, 0.1)) * np.log1p(max(duration_h, 0.05))
    return float(1 - np.exp(-curve_k * event_strength))


def build_expected_baseline(df: pd.DataFrame, capacity_mw: float, yield_kwh_mw_day: float) -> pd.DataFrame:
    out = df.copy()
    clean_kwh = capacity_mw * yield_kwh_mw_day * out["Irradiance_Norm"]
    out["Expected_kWh_Clean"] = clean_kwh
    out["Expected_kWh_Availability_PR"] = clean_kwh * out["Availability"] * out["PR"]
    return out


def run_strategy(
    df: pd.DataFrame,
    tariff: float,
    threshold_mm: float,
    curve_k: float,
    delayed_days: int,
    cleaning_mix: dict,
    crew_per_day: int,
    water_m3_day: float,
    zones: int,
    zone_share_clean: float,
    hse_wind_limit: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    sim = df.copy()
    n = len(sim)
    zone_sr = np.full((n, zones), float(sim["SR"].iloc[0]))
    pending_recovery = np.zeros((n + delayed_days + 2, zones))

    rng = np.random.default_rng(7)
    sim["Wind_mps"] = np.clip(rng.normal(6, 2.5, n), 0.0, 16.0)

    records = []
    logistics = []

    for i, (dt, row) in enumerate(sim.iterrows()):
        if i > 0:
            zone_sr[i, :] = np.maximum(0.72, zone_sr[i - 1, :] - (1 - row["SR_True"]) * 0.005)

        zone_sr[i, :] = np.clip(zone_sr[i, :] + pending_recovery[i, :], 0.72, 1.0)

        eff = rain_effectiveness(
            row["Rain_mm_Tot"], row["Rain_Intensity_mmph"], row["Rain_Duration_h"], threshold_mm, curve_k
        )
        if eff > 0:
            gain = (1.0 - zone_sr[i, :]) * eff
            zone_sr[i, :] = np.clip(zone_sr[i, :] + gain * 0.45, 0.72, 1.0)
            if delayed_days > 0 and i + delayed_days < len(pending_recovery):
                pending_recovery[i + delayed_days, :] += gain * 0.55

        is_weekday = dt.weekday() < 5
        hse_ok = row["Wind_mps"] <= hse_wind_limit
        water_ok = water_m3_day >= 15
        dispatch_allowed = is_weekday and hse_ok and water_ok

        cleaned_zones = 0
        day_opex = 0.0
        day_log = 0.0

        if dispatch_allowed and crew_per_day > 0:
            zone_losses = 1 - zone_sr[i, :]
            rank = np.argsort(zone_losses)[::-1]
            max_zones = min(int(np.ceil(zones * zone_share_clean)), crew_per_day)

            for z in rank[:max_zones]:
                best = None
                for name, cfg in cleaning_mix.items():
                    recovered = zone_losses[z] * cfg["effectiveness"]
                    gross = recovered * row["Expected_kWh_Availability_PR"] / zones * tariff
                    net = gross - cfg["cost_per_zone"] - cfg["logistics_per_dispatch"] / max(1, max_zones)
                    if (best is None) or (net > best["net_value"]):
                        best = {"type": name, "net_value": net, **cfg}

                if best and best["net_value"] > 0:
                    rec = zone_losses[z] * best["effectiveness"]
                    zone_sr[i, z] = np.clip(zone_sr[i, z] + rec * 0.6, 0.72, 1.0)
                    rec_day = min(i + int(best["recovery_days"]), len(pending_recovery) - 1)
                    pending_recovery[rec_day, z] += rec * 0.4
                    cleaned_zones += 1
                    day_opex += best["cost_per_zone"]
                    day_log += best["logistics_per_dispatch"] / max(1, max_zones)
                    records.append({"Date": dt, "Zone": z, "Type": best["type"], "Expected_Net_Value_USD": best["net_value"]})

        logistics.append((day_opex, day_log, cleaned_zones, dispatch_allowed))

    sim["SR_Strategy"] = zone_sr.mean(axis=1)
    sim["Predicted_kWh"] = sim["Expected_kWh_Availability_PR"] * sim["SR_Strategy"] * (1 - sim["Curtailment"] - sim["Clipping"])
    sim["Realized_kWh"] = sim["Expected_kWh_Availability_PR"] * sim["SR_True"] * (1 - sim["Curtailment"] - sim["Clipping"])

    ops = pd.DataFrame(logistics, columns=["Cleaning_OPEX", "Logistics_Cost", "Zones_Cleaned", "Dispatch_Allowed"], index=sim.index)
    sim = sim.join(ops)
    sim["Avoided_Loss_USD"] = (sim["Predicted_kWh"] - sim["Realized_kWh"]).clip(lower=0) * tariff
    sim["Net_Benefit_USD"] = sim["Avoided_Loss_USD"] - sim["Cleaning_OPEX"] - sim["Logistics_Cost"]

    return sim, pd.DataFrame(records)


def monte_carlo_bands(sim: pd.DataFrame, tariff: float, n_runs: int = 400, seed: int = 12) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    annual_benefits = []
    annual_losses = []
    contributions = {"sensor": [], "rain": [], "tariff": [], "yield": []}

    base_yield = sim["Expected_kWh_Clean"].sum()
    for _ in range(n_runs):
        sensor_mult = 1 + rng.normal(0, 0.012)
        rain_mult = 1 + rng.normal(0, 0.08)
        tariff_mult = 1 + rng.normal(0, 0.10)
        yield_mult = 1 + rng.normal(0, 0.07)

        sampled_loss = (
            ((1 - sim["SR_Strategy"] * sensor_mult) * sim["Expected_kWh_Availability_PR"] * yield_mult)
            .clip(lower=0)
            .sum()
            * tariff
            * tariff_mult
        )
        sampled_savings = sim["Avoided_Loss_USD"].sum() * sensor_mult * rain_mult * tariff_mult * yield_mult

        annual_losses.append(sampled_loss)
        annual_benefits.append(sampled_savings)
        contributions["sensor"].append(sampled_savings * abs(sensor_mult - 1))
        contributions["rain"].append(sampled_savings * abs(rain_mult - 1))
        contributions["tariff"].append(sampled_savings * abs(tariff_mult - 1))
        contributions["yield"].append(sampled_savings * abs(yield_mult - 1))

    quant = lambda arr: np.quantile(arr, [0.5, 0.75, 0.9])
    loss_q = quant(annual_losses)
    save_q = quant(annual_benefits)

    bands = pd.DataFrame(
        {
            "Metric": ["Annual Loss (USD)", "Annual Savings (USD)"],
            "P50": [loss_q[0], save_q[0]],
            "P75": [loss_q[1], save_q[1]],
            "P90": [loss_q[2], save_q[2]],
            "Expected_GWh_Basis": [base_yield / 1e6, base_yield / 1e6],
        }
    )
    decomp = pd.DataFrame({k: np.mean(v) for k, v in contributions.items()}, index=["Contribution_USD"]).T.reset_index()
    decomp.columns = ["Uncertainty_Source", "Contribution_USD"]
    return bands, decomp


def npv_irr(cashflows: list[float], discount_rate: float) -> tuple[float, float]:
    years = np.arange(len(cashflows))
    npv = float(np.sum(np.array(cashflows) / ((1 + discount_rate) ** years)))

    low, high = -0.99, 2.5
    for _ in range(60):
        mid = (low + high) / 2
        v = np.sum(np.array(cashflows) / ((1 + mid) ** years))
        if v > 0:
            low = mid
        else:
            high = mid
    return npv, float((low + high) / 2)


def loss_attribution(sim: pd.DataFrame) -> pd.DataFrame:
    clean = sim["Expected_kWh_Clean"]
    return pd.DataFrame(
        {
            "Bucket": ["Soiling", "Outages/Availability", "Curtailment", "Clipping"],
            "Loss_MWh": [
                (clean * (1 - sim["SR_Strategy"])).sum() / 1000,
                (clean * (1 - sim["Availability"])).sum() / 1000,
                (clean * sim["Curtailment"]).sum() / 1000,
                (clean * sim["Clipping"]).sum() / 1000,
            ],
        }
    )


def main():
    st.title("📈 Bankable Soiling Strategy Workbench")
    st.caption("Now wired to the same station ingestion flow as your original app, with upgraded bankability analytics.")

    st.sidebar.header("Data source")
    use_dummy = st.sidebar.checkbox("Use dummy data", value=True)
    root_path = st.sidebar.text_input("Station root path", value=r"C:\Users\khalAA0A\Dev\measurment stations\Solar Sample")

    with st.spinner("Loading data..."):
        raw_df = generate_dummy_data() if use_dummy else load_and_process_data(root_path)

    stations = sorted(raw_df["Station_Name"].dropna().unique().tolist())
    selected_station = st.sidebar.selectbox("Station", stations)
    station_df = raw_df[raw_df["Station_Name"] == selected_station][["SR", "Rain_mm_Tot"]].copy().dropna().sort_index()
    station_df.index.name = "Date"

    st.sidebar.header("Plant & commercial inputs")
    capacity_mw = st.sidebar.number_input("Capacity (MW)", value=300.0, step=25.0)
    yield_kwh_mw_day = st.sidebar.number_input("Expected clean yield (kWh/MW/day)", value=4300.0, step=100.0)
    tariff = st.sidebar.number_input("Tariff (USD/kWh)", value=0.028, format="%.3f")
    discount = st.sidebar.slider("Discount rate", 0.04, 0.18, 0.10, 0.01)

    st.sidebar.header("Rain effectiveness")
    threshold_mm = st.sidebar.slider("Effective rain threshold (mm)", 0.5, 8.0, 2.0, 0.5)
    curve_k = st.sidebar.slider("Wash curve sensitivity", 0.01, 0.35, 0.08, 0.01)
    delayed_days = st.sidebar.slider("Delayed recovery lag (days)", 0, 5, 2)

    st.sidebar.header("Dispatch constraints")
    crew_per_day = st.sidebar.slider("Crew dispatch slots/day", 0, 12, 4)
    water_m3_day = st.sidebar.slider("Water availability (m³/day)", 0, 80, 30)
    hse_wind_limit = st.sidebar.slider("HSE wind limit (m/s)", 4.0, 14.0, 9.0, 0.5)
    zones = st.sidebar.slider("Plant zones", 4, 40, 12)
    zone_share_clean = st.sidebar.slider("Max zone share cleaned/day", 0.1, 1.0, 0.35, 0.05)

    cleaning_mix = {
        "Manual Dry": {"cost_per_zone": 170, "effectiveness": 0.50, "recovery_days": 1, "logistics_per_dispatch": 210},
        "Manual Wet": {"cost_per_zone": 260, "effectiveness": 0.72, "recovery_days": 2, "logistics_per_dispatch": 260},
        "Robotic": {"cost_per_zone": 220, "effectiveness": 0.62, "recovery_days": 0, "logistics_per_dispatch": 190},
    }

    base = enrich_station_context(station_df, seed=abs(hash(selected_station)) % (2**16))
    base = build_expected_baseline(base, capacity_mw, yield_kwh_mw_day)
    sim, clean_log = run_strategy(
        base,
        tariff,
        threshold_mm,
        curve_k,
        delayed_days,
        cleaning_mix,
        crew_per_day,
        water_m3_day,
        zones,
        zone_share_clean,
        hse_wind_limit,
    )

    bands, decomp = monte_carlo_bands(sim, tariff)
    attrib = loss_attribution(sim)

    annual_net = sim["Net_Benefit_USD"].sum()
    annual_opex = sim["Cleaning_OPEX"].sum() + sim["Logistics_Cost"].sum()
    no_strategy_loss = ((1 - sim["SR"]) * sim["Expected_kWh_Availability_PR"] * tariff).sum()

    cashflows = [-2_000_000] + [annual_net * (1 + 0.01 * y) for y in range(1, 11)]
    npv, irr = npv_irr(cashflows, discount)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Annual net benefit", f"${annual_net:,.0f}")
    c2.metric("Annual cleaning + logistics", f"${annual_opex:,.0f}")
    c3.metric("NPV (10y strategy)", f"${npv:,.0f}")
    c4.metric("IRR", f"{irr*100:.1f}%")

    t1, t2, t3, t4, t5 = st.tabs(["Uncertainty & CI", "Cleaning economics", "Rain effectiveness", "Baseline & attribution", "Backtesting"])

    with t1:
        st.subheader("P50 / P75 / P90 bands")
        st.dataframe(
            bands.style.format({"P50": "${:,.0f}", "P75": "${:,.0f}", "P90": "${:,.0f}", "Expected_GWh_Basis": "{:.2f}"}),
            width="stretch",
        )
        fig_u = px.bar(decomp, x="Uncertainty_Source", y="Contribution_USD", color="Uncertainty_Source", title="Uncertainty decomposition")
        st.plotly_chart(fig_u, width="stretch")

    with t2:
        st.subheader("Dispatch-constrained, partial cleaning economics")
        st.write(f"No-strategy modeled loss: **${no_strategy_loss:,.0f}**")
        ops = sim[["Cleaning_OPEX", "Logistics_Cost", "Avoided_Loss_USD", "Net_Benefit_USD", "Zones_Cleaned"]].copy()
        ops_roll = ops.rolling(14).mean()
        ops_roll["Date"] = ops_roll.index
        st.plotly_chart(
            px.line(ops_roll.reset_index(drop=True), x="Date", y=["Avoided_Loss_USD", "Cleaning_OPEX", "Logistics_Cost", "Net_Benefit_USD"], title="14-day rolling economics"),
            width="stretch",
        )
        st.dataframe(clean_log.tail(40), width="stretch")

    with t3:
        st.subheader("Rain wash dynamics (threshold + delayed/partial recovery)")
        rain_view = sim[["Rain_mm_Tot", "SR_Strategy", "SR_True"]].copy().reset_index()
        fig_r = go.Figure()
        fig_r.add_trace(go.Bar(x=rain_view["Date"], y=rain_view["Rain_mm_Tot"], name="Rain mm", yaxis="y2", opacity=0.4))
        fig_r.add_trace(go.Scatter(x=rain_view["Date"], y=rain_view["SR_Strategy"], name="SR Strategy", mode="lines"))
        fig_r.add_trace(go.Scatter(x=rain_view["Date"], y=rain_view["SR_True"], name="SR Realized", mode="lines", line=dict(dash="dot")))
        fig_r.update_layout(yaxis=dict(title="Soiling ratio"), yaxis2=dict(title="Rain mm", overlaying="y", side="right"), title="Rain effectiveness avoids binary reset assumptions")
        st.plotly_chart(fig_r, width="stretch")

    with t4:
        st.subheader("Weather-normalized baseline + loss attribution waterfall")
        st.plotly_chart(
            px.line(sim.reset_index(), x="Date", y=["Expected_kWh_Clean", "Expected_kWh_Availability_PR", "Realized_kWh"], title="Expected baseline vs realized generation"),
            width="stretch",
        )
        st.plotly_chart(px.bar(attrib, x="Bucket", y="Loss_MWh", title="Loss attribution"), width="stretch")

    with t5:
        st.subheader("Backtesting: predicted vs realized after rain and cleaning")
        back = sim[["Predicted_kWh", "Realized_kWh", "Dispatch_Allowed", "Zones_Cleaned", "Rain_mm_Tot"]].copy().reset_index()
        back["APE_%"] = (np.abs(back["Predicted_kWh"] - back["Realized_kWh"]) / back["Realized_kWh"].clip(lower=1)) * 100
        st.plotly_chart(px.scatter(back, x="Predicted_kWh", y="Realized_kWh", color="Rain_mm_Tot", title="Predicted vs Realized (rain-colored)"), width="stretch")
        st.plotly_chart(px.line(back, x="Date", y="APE_%", title="Absolute percentage error (%)"), width="stretch")
        st.dataframe(back.tail(60), width="stretch")


if __name__ == "__main__":
    main()
