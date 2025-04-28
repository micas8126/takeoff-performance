import streamlit as st
import pandas as pd

# Lade die CSV-Dateien
files = {
    '650': 'takeoff_performance.csv',
    '600': 'takeoff_performance_3.csv',
    '550': 'takeoff_performance_2.csv'
}

def load_all_data():
    data = {}
    for weight, file in files.items():
        df = pd.read_csv(file)
        df['Pressure Altitude (ft)'] = pd.to_numeric(df['Pressure Altitude (ft)'], errors='coerce')
        data[int(weight)] = df
    return data

def find_bounds(values, target):
    values = sorted(values)
    lower = max([v for v in values if v <= target])
    upper = min([v for v in values if v >= target])
    return lower, upper

def interpolate(value1, value2, point1, point2, target_point):
    if point1 == point2:
        return value1
    return value1 + (value2 - value1) * (target_point - point1) / (point2 - point1)

def apply_corrections(ground_roll, distance_50ft, wind, runway_type, slope):
    if wind > 0:
        # Positive Wind = Gegenwind -> Strecke kürzer
        correction_factor = (wind / 9) * 0.10
        ground_roll *= (1 - correction_factor)
        distance_50ft *= (1 - correction_factor)
    elif wind < 0:
        # Negative Wind = Rückenwind -> Strecke länger
        wind_tail = abs(wind)
        if wind_tail > 10:
            st.warning("Tailwind greater than 10kt entered. Correction limited to 10kt as per manual.")
            wind_tail = 10
        correction_factor = (wind_tail / 2) * 0.10
        ground_roll *= (1 + correction_factor)
        distance_50ft *= (1 + correction_factor)

    # Runway surface correction
    if runway_type == 'Paved':
        ground_roll *= 0.9
    elif runway_type == 'Grass':
        ground_roll *= 1.15

    # Slope correction
    ground_roll *= (1 + (slope * 0.07))

    return round(ground_roll), round(distance_50ft)

def main():
    st.title("Take-Off Performance Calculator")

    st.sidebar.header("Input Parameters")

    weight = st.sidebar.slider("Aircraft Weight (kg)", 550, 650, 600)
    altitude = st.sidebar.slider("Pressure Altitude (ft)", 0, 10000, 0, step=500)
    temperature = st.sidebar.slider("Temperature (°C)", -25, 50, 15)
    wind = st.sidebar.slider("Wind (kts) - Positive = Headwind, Negative = Tailwind", -20, 20, 0)
    runway_type = st.sidebar.selectbox("Runway Surface", ("Paved", "Grass"))
    slope = st.sidebar.number_input("Runway Slope (%)", -10.0, 10.0, 0.0)

    if st.sidebar.button("Calculate Take-Off Performance"):
        data = load_all_data()

        if weight <= 600:
            low_wt, high_wt = 550, 600
        else:
            low_wt, high_wt = 600, 650

        df_low = data[low_wt]
        df_high = data[high_wt]

        alt_low, alt_high = find_bounds(df_low['Pressure Altitude (ft)'].unique(), altitude)
        temp_points = [-25, 0, 25, 50]
        temp_low, temp_high = find_bounds(temp_points, temperature)

        temp_col_low = f"{temp_low}°C"
        temp_col_high = f"{temp_high}°C"

        def get_values(df, alt, temp_col):
            subset = df[df['Pressure Altitude (ft)'] == alt]
            ground_roll = subset[subset['Measurement'] == 'Ground Roll'][temp_col].values[0]
            distance_50ft = subset[subset['Measurement'] == 'At 50 ft AGL'][temp_col].values[0]
            return ground_roll, distance_50ft

        gr_low_temp_low, dist_low_temp_low = get_values(df_low, alt_low, temp_col_low)
        gr_low_temp_high, dist_low_temp_high = get_values(df_low, alt_low, temp_col_high)
        gr_high_temp_low, dist_high_temp_low = get_values(df_low, alt_high, temp_col_low)
        gr_high_temp_high, dist_high_temp_high = get_values(df_low, alt_high, temp_col_high)

        gr_loww_temp_low, dist_loww_temp_low = get_values(df_high, alt_low, temp_col_low)
        gr_loww_temp_high, dist_loww_temp_high = get_values(df_high, alt_low, temp_col_high)
        gr_highw_temp_low, dist_highw_temp_low = get_values(df_high, alt_high, temp_col_low)
        gr_highw_temp_high, dist_highw_temp_high = get_values(df_high, alt_high, temp_col_high)

        gr_low = interpolate(gr_low_temp_low, gr_low_temp_high, temp_low, temp_high, temperature)
        dist_low = interpolate(dist_low_temp_low, dist_low_temp_high, temp_low, temp_high, temperature)

        gr_high = interpolate(gr_high_temp_low, gr_high_temp_high, temp_low, temp_high, temperature)
        dist_high = interpolate(dist_high_temp_low, dist_high_temp_high, temp_low, temp_high, temperature)

        gr_loww = interpolate(gr_loww_temp_low, gr_loww_temp_high, temp_low, temp_high, temperature)
        dist_loww = interpolate(dist_loww_temp_low, dist_loww_temp_high, temp_low, temp_high, temperature)

        gr_highw = interpolate(gr_highw_temp_low, gr_highw_temp_high, temp_low, temp_high, temperature)
        dist_highw = interpolate(dist_highw_temp_low, dist_highw_temp_high, temp_low, temp_high, temperature)

        gr_low_final = interpolate(gr_low, gr_high, alt_low, alt_high, altitude)
        dist_low_final = interpolate(dist_low, dist_high, alt_low, alt_high, altitude)

        gr_high_final = interpolate(gr_loww, gr_highw, alt_low, alt_high, altitude)
        dist_highw_final = interpolate(dist_loww, dist_highw, alt_low, alt_high, altitude)

        ground_roll = interpolate(gr_low_final, gr_high_final, low_wt, high_wt, weight)
        distance_50ft = interpolate(dist_low_final, dist_highw_final, low_wt, high_wt, weight)

        corrected_ground_roll, corrected_distance_50ft = apply_corrections(
            ground_roll, distance_50ft, wind, runway_type, slope
        )

        st.success(f"Corrected Ground Roll Distance: {corrected_ground_roll} meters")
        st.success(f"Corrected Distance over 50 ft AGL: {corrected_distance_50ft} meters")

if __name__ == "__main__":
    main()
