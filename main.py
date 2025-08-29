import sys
import sqlite3
import requests
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem
from PySide6.QtCore import QThread, Signal,QDateTime
from PySide6.QtGui import QPixmap
from ui_vrijeme import Ui_MainWindow
# ---------------------------------------
# Baza podataka - inicijalizacija
# ---------------------------------------
def init_db():
    """Kreira SQLite bazu i tablice ako ne postoje."""
    conn = sqlite3.connect("weather_app.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            date TEXT NOT NULL,
            temp REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# ---------------------------------------
# Worker thread za dohvat podataka
# ---------------------------------------
class WeatherFetcher(QThread):
    finished = Signal(dict)   # emitira dict s current i forecast
    error = Signal(str)       # emitira poruku greške

    def __init__(self, city: str, api_key: str, units: str):
        super().__init__()
        self.city = city
        self.api_key = api_key
        self.units = units

    def run(self):
        """Dohvat podataka s OpenWeather API-ja."""
        # TODO: implementirati GET pozive na /weather i /forecast
        #       te emitirati self.finished({...}) ili self.error("...").
        try:
            # Primjer GET poziva (zamijeniti s pravim URL-ovima i parametrima)
            current_url = f"http://api.openweathermap.org/data/2.5/weather?q={self.city}&appid={self.api_key}&units={self.units}"
            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={self.city}&appid={self.api_key}&units={self.units}"

            current_resp = requests.get(current_url)
            forecast_resp = requests.get(forecast_url)

            if current_resp.status_code != 200 or forecast_resp.status_code != 200:
                self.error.emit("Greška pri dohvaćanju podataka.")
                return

            current_data = current_resp.json()
            forecast_data = forecast_resp.json()

            self.finished.emit({
                "current": current_data,
                "forecast": forecast_data
            })
        except Exception as e:
            self.error.emit(f"Greška: {str(e)}")


# ---------------------------------------
# Glavna aplikacija
# ---------------------------------------
class WeatherApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        init_db()
        # API key should be securely loaded from settings or environment variable.
        # Replace 'YOUR_API_KEY_HERE' with your actual OpenWeather API key if not using settings.
        import os
        self.api_key = os.environ.get("OPENWEATHER_API_KEY", "YOUR_API_KEY_HERE")
        self.units = "metric"
        self.weather_thread = None

        # TODO: povezati gumbe i combo box s metodama
        # npr. self.fetch_button.clicked.connect(self.start_fetch_weather)
        self.load_settings()
        self.fetch_button.clicked.connect(self.start_fetch_weather)

        


    def load_settings(self):
        """Učitava spremljene postavke iz baze."""
        # TODO: dohvatiti api_key i units iz tablice settings
        conn = sqlite3.connect("weather_app.db")
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'api_key'")
        api_key_row = cursor.fetchone()
        if api_key_row is not None:
            self.api_key = api_key_row[0]
        else:
            self.api_key = "YOUR_API_KEY_HERE"
        cursor.execute("SELECT value FROM settings WHERE key = 'units'")
        units_row = cursor.fetchone()
        if units_row is not None:
            self.units = units_row[0]
        else:
            self.units = "metric"
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('api_key', self.api_key))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('units', self.units))
        conn.commit()
        conn.close()
        """Sprema postavke u bazu podataka."""
        # TODO: zapisati api_key i units u tablicu settings
        conn = sqlite3.connect("weather_app.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES
            ('api_key', ?),
            ('units', ?)
        """, (self.api_key, self.units))
        conn.commit()
        conn.close()


    def start_fetch_weather(self):
        """Pokreće nit za dohvat vremena."""
        # TODO: provjera unosa, kreiranje i start WeatherFetcher niti
        city = self.city_input.text().strip()
        if not city:
            self.show_error("Unesite naziv grada.")
            return

        self.weather_thread = WeatherFetcher(city, self.api_key, self.units)
        self.weather_thread.finished.connect(self.handle_weather_data)
        self.weather_thread.error.connect(self.show_error)
        self.weather_thread.start()

    def handle_weather_data(self, data: dict):
        """Ažurira UI s dohvaćenim podacima."""
        # TODO: popuniti city_label, temp_label, desc_label, itd.
        #       pozvati update_icon, update_forecast_table, draw_temp_graph
        current = data.get("current", {})
        self.city_label.setText(current.get("name", ""))
        self.temp_label.setText(f"{current.get('main', {}).get('temp', 0)} °C")
        self.desc_label.setText(current.get("weather", [{}])[0].get("description", ""))
        self.update_icon(current.get("weather", [{}])[0].get("icon", ""))
        self.update_forecast_table(data.get("forecast", {}))
        self.draw_temp_graph(data.get("forecast", {}))

    def update_icon(self, icon_code: str):
        """Prikazuje ikonu vremena u city_label."""
        # TODO: dohvatiti ikonu s openweathermap i postaviti QPixmap
        try:
            response = requests.get(f"http://openweathermap.org/img/wn/{icon_code}.png")
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                self.icon_label.setPixmap(pixmap)
            else:
                self.icon_label.clear()
        except Exception:
            self.icon_label.clear()

    def update_forecast_table(self, forecast: dict):
        """Popunjava QTableWidget podacima prognoze."""
        # Dodaje do 24 unosa iz "list" (3-satni intervali)
        forecast_list = forecast.get("list", [])
        self.forecast_table.clearContents()
        row_count = min(24, len(forecast_list))
        self.forecast_table.setRowCount(row_count)
        for i in range(row_count):
            entry = forecast_list[i]
            time = entry.get("dt", 0)
            temp = entry.get("main", {}).get("temp", 0)
            desc = entry.get("weather", [{}])[0].get("description", "")
            self.forecast_table.setItem(i, 0, QTableWidgetItem(QDateTime.fromSecsSinceEpoch(time).toString()))
            self.forecast_table.setItem(i, 1, QTableWidgetItem(f"{temp} °C"))
            self.forecast_table.setItem(i, 2, QTableWidgetItem(desc))
        forecast_list = forecast.get("list", [])
        temperatures = [entry.get("main", {}).get("temp", 0) for entry in forecast_list[:24]]
        # Ovdje bi išao kod za crtanje grafikona, npr. koristeći matplotlib

    def draw_temp_graph(self, forecast: dict):
        from PySide6.QtCore import Qt
        cursor.execute("""
            INSERT INTO history (city, date, temp) VALUES (?, ?, ?)
        """, (city, QDateTime.currentDateTime().toString(Qt.ISODate), temp))
        conn.commit()
        conn.close()

    def save_to_history(self, city: str, temp: float):
        """Sprema unos u tablicu history."""
        # TODO: insert u bazu (city, date, temp)
        conn = sqlite3.connect("weather_app.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO history (city, date, temp) VALUES (?, ?, ?)
        """, (city, QDateTime.currentDateTime().toString(), temp))
        conn.commit()
        conn.close()

    def show_error(self, message: str):
        """Prikazuje poruku o grešci."""
        QMessageBox.critical(self, "Greška", message)


# ---------------------------------------
# Entry point
# ---------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WeatherApp()
    window.show()
    sys.exit(app.exec())

