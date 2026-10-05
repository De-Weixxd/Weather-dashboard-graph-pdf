import datetime
import os
import matplotlib.pyplot as plt
import pandas as pd
import requests
from dotenv import load_dotenv
from fpdf import FPDF

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")
DB_FILE = "weather_history.csv"
PLOT_FILE = "weather_plot.png"
PDF_FILE = "weather_report.pdf"


def get_weather(city: str = "Jos"):
    if not API_KEY:
        print("Error: OPENWEATHER_API_KEY is not set in your .env file.")
        return None

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        return {
            "city": data["name"],
            "temp": round(data["main"]["temp"], 1),
            "feels_like": round(data["main"]["feels_like"], 1),
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"].title(),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except requests.exceptions.HTTPError as e:
        if r.status_code == 401:
            print("Error: Invalid OpenWeather API key.")
        elif r.status_code == 404:
            print(f"Error: City '{city}' not found.")
        else:
            print(f"HTTP error occurred: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    return None


def save_to_history(data: dict):
    if not data:
        return
    df = pd.DataFrame([data])
    file_exists = os.path.exists(DB_FILE)
    df.to_csv(DB_FILE, mode="a", header=not file_exists, index=False)
    print(f"Data saved to {DB_FILE}")


def plot_history(city: str = None, show: bool = True):
    if not os.path.exists(DB_FILE):
        print("No history file found yet. Record some weather data first.")
        return False

    df = pd.read_csv(DB_FILE)
    if "timestamp" not in df.columns:
        print(f"Outdated CSV detected. Delete {DB_FILE} and fetch data again.")
        return False

    # Filter by city if specified or use the most recent city
    target_city = city or df["city"].iloc[-1]
    city_df = df[df["city"].str.lower() == target_city.lower()].copy()

    if city_df.empty:
        print(f"No history found for city: {target_city}")
        return False

    city_df["timestamp"] = pd.to_datetime(city_df["timestamp"])
    city_df = city_df.sort_values("timestamp")

    plt.figure(figsize=(10, 5))
    plt.plot(city_df["timestamp"], city_df["temp"], marker="o", label="Temp (°C)")
    plt.plot(city_df["timestamp"], city_df["feels_like"], marker="x", linestyle="--", label="Feels Like (°C)")
    plt.title(f"Temperature History - {target_city}")
    plt.xlabel("Time")
    plt.ylabel("Temperature (°C)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(PLOT_FILE)
    print(f"Plot saved as {PLOT_FILE}")

    if show:
        plt.show()
    plt.close()
    return True


def export_pdf(city: str = None):
    if not os.path.exists(DB_FILE):
        print("No data available to export.")
        return

    df = pd.read_csv(DB_FILE)
    target_city = city or df["city"].iloc[-1]
    city_df = df[df["city"].str.lower() == target_city.lower()].copy()

    if city_df.empty:
        print(f"No records found for {target_city}.")
        return

    # Automatically generate the latest plot for this city
    plot_history(city=target_city, show=False)

    pdf = FPDF()
    pdf.add_page()

    # Title & Metadata
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Weather Report - {target_city}", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"Generated: {datetime.date.today().isoformat()}", ln=True, align="C")
    pdf.ln(6)

    # Table Header
    pdf.set_font("Arial", "B", 10)
    pdf.cell(45, 8, "Timestamp", border=1)
    pdf.cell(30, 8, "Temp (C)", border=1)
    pdf.cell(30, 8, "Humidity", border=1)
    pdf.cell(75, 8, "Description", border=1)
    pdf.ln()

    # Table Rows (last 7 entries)
    pdf.set_font("Arial", "", 9)
    for _, row in city_df.tail(7).iterrows():
        timestamp_str = str(row.get("timestamp", ""))
        temp_str = f"{row.get('temp', '')} C"
        humidity_str = f"{row.get('humidity', '')}%"
        desc_str = str(row.get("description", ""))

        pdf.cell(45, 8, timestamp_str, border=1)
        pdf.cell(30, 8, temp_str, border=1)
        pdf.cell(30, 8, humidity_str, border=1)
        pdf.cell(75, 8, desc_str, border=1)
        pdf.ln()

    # Insert Plot Image
    if os.path.exists(PLOT_FILE):
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Temperature Trend", ln=True, align="C")
        pdf.image(PLOT_FILE, x=10, y=25, w=190)

    pdf.output(PDF_FILE)
    print(f"PDF saved as {PDF_FILE}")


if __name__ == "__main__":
    print("\n--- Weather Tracker ---")
    print("1. Fetch Weather")
    print("2. Plot History")
    print("3. Export PDF Report")
    choice = input("Choose (1/2/3): ").strip()

    if choice == "1":
        city = input("City [Jos]: ").strip() or "Jos"
        data = get_weather(city)
        if data:
            print("\nCurrent Weather:")
            for k, v in data.items():
                print(f"  {k}: {v}")
            save_to_history(data)
    elif choice == "2":
        city = input("City (press Enter for latest): ").strip() or None
        plot_history(city=city)
    elif choice == "3":
        city = input("City (press Enter for latest): ").strip() or None
        export_pdf(city=city)
    else:
        print("Invalid choice.")