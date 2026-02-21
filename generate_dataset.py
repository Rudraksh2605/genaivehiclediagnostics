"""
Run this script once to generate the static `data/telemetry_dataset.csv`
This mimics downloading a real-world predictive maintenance dataset from Kaggle.
"""
import os
import pandas as pd
import numpy as np

def create_dataset():
    np.random.seed(42)
    num_rows = 5000
    
    # Generate realistic driving scenarios
    speeds = np.random.uniform(0, 140, num_rows)
    socs = np.random.uniform(5, 100, num_rows)
    discharge_rates = np.random.uniform(0.1, 1.5, num_rows)
    
    # Calculate target variable: minutes until 20%
    minutes_to_20 = np.where(socs > 20, (socs - 20) / discharge_rates, 0)
    
    # Tire wear progression
    odometers = np.random.uniform(0, 150000, num_rows)
    tire_base = 35.0 - (odometers / 150000 * 12.0)
    wear_labels = (odometers / 150000) + np.random.normal(0, 0.1, num_rows)
    wear_labels = np.clip(wear_labels, 0, 1)

    df = pd.DataFrame({
        "timestamp": pd.date_range(start="2026-01-01", periods=num_rows, freq="1min"),
        "speed": speeds,
        "battery_soc": socs,
        "battery_voltage": 320 + (socs / 100) * 80 + np.random.normal(0, 1, num_rows),
        "battery_temp": np.random.uniform(15, 45, num_rows),
        "discharge_rate": discharge_rates,
        "minutes_to_20_soc": minutes_to_20,
        
        "tire_fl_psi": tire_base + np.random.normal(0, 1.5, num_rows),
        "tire_fr_psi": tire_base + np.random.normal(0, 1.5, num_rows),
        "tire_rl_psi": tire_base + np.random.normal(0, 2.0, num_rows),
        "tire_rr_psi": tire_base + np.random.normal(0, 2.0, num_rows),
        "odometer": odometers,
        "tire_wear_label": wear_labels,
        
        "throttle": np.where(speeds > 10, speeds / 1.5 + np.random.normal(0, 5, num_rows), 0),
        "brake": np.where(speeds < 10, np.random.uniform(20, 100, num_rows), 0),
        "ev_range": socs * 3.5 + np.random.normal(0, 10, num_rows)
    })
    
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    df.to_csv(os.path.join(data_dir, "telemetry_dataset.csv"), index=False)
    print("Successfully generated data/telemetry_dataset.csv (Kaggle mock)")

if __name__ == "__main__":
    create_dataset()
