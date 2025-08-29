import sys
import sqlite3
import requests
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, Qt
from PySide6.QtWidgets import QTableWidgetItem
from datetime import datetime
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
        """Dohvat podataka s OpenWeather API-ja."""
        if not self.api_key:
            self.error.emit("Nevažeći API ključ. Provjerite postavke.")
            return

        if not self.city:
            self.error.emit("Molimo unesite naziv grada.")
            return

        base_url = "http://api.openweathermap.org/data/2.5"
        weather_params = {
            "q": self.city,  # Ostaje 'q' jer je to ispravan parametar za OpenWeather API
            "appid": self.api_key, # Ostaje 'appid' jer je to ispravan parametar za OpenWeather API
            "units": self.units
        }
        forecast_params = {
            "q": self.city,
            "appid": self.api_key,
            "units": self.units
        }

        try:
            weather_response = requests.get(f"{base_url}/weather", params=weather_params)
            forecast_response = requests.get(f"{base_url}/forecast", params=forecast_params)

            weather_response.raise_for_status()
            forecast_response.raise_for_status()

            weather_data = weather_response.json()
            forecast_data = forecast_response.json()

            self.finished.emit({
                "current": weather_data,
                "forecast": forecast_data
            })

        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 401:
                self.error.emit("Nevažeći API ključ. Provjerite postavke.")
            elif err.response.status_code == 404:
                self.error.emit(f"Grad '{self.city}' nije pronađen.")
            else:
                self.error.emit(f"Greška s mrežnom vezom. Provjerite internet.")
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Greška s mrežnom vezom. Provjerite internet.")
        except Exception as e:
            self.error.emit(f"Neočekivana greška: {e}")

# ---------------------------------------
# Glavna aplikacija
# ---------------------------------------
class WeatherApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        init_db()
        self.api_key = "YOUR_API_KEY_HERE"
        self.units = "metric"
        self.weather_thread = None

        # TODO: povezati gumbe i combo box s metodama
        # npr. self.fetch_button.clicked.connect(self.start_fetch_weather)
        self.fetch_button.clicked.connect(self.start_fetch_weather)
        self.save_settings_button.clicked.connect(self.save_settings)
        self.units_combo.currentTextChanged.connect(self.update_units_state)

        self.load_settings()

    def load_settings(self):
        """Učitava spremljene postavke iz baze."""
        # TODO: dohvatiti api_key i units iz tablice settings
        with sqlite3.connect("weather_app.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'api_key'")
            row = cursor.fetchone()
            if row:
                self.api_key = row[0]
                self.api_key_input.setText(self.api_key)
            cursor.execute("SELECT value FROM settings WHERE key = 'units'")
            row = cursor.fetchone()
            if row:
                self.units = row[0]
                if self.units == "metric":
                    self.units_combo.setCurrentText("Celzijus")
                else:
                    self.units_combo.setCurrentText("Fahrenheit")
            
            cursor.execute("SELECT value FROM settings WHERE key = 'last_city'")
            last_city_row = cursor.fetchone()
            if last_city_row:
                self.city_input.setText(last_city_row[0])
        self.statusbar.showMessage("Postavke uspješno učitane.")

    def save_settings(self):
        """Sprema postavke u bazu podataka."""
        # TODO: zapisati api_key i units u tablicu settings
        self.api_key = self.api_key_input.text()
        self.units = "metric" if self.units_combo.currentText() == "Celzijus" else "imperial"
        self.last_city = self.city_input.text().strip()

        with sqlite3.connect("weather_app.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("api_key", self.api_key))
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("units", self.units))
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("last_city", self.last_city))
            conn.commit()
        self.statusbar.showMessage("Postavke uspješno spremljene.")

    def update_units_state(self, text):
        """Ažurira interni state jedinica."""
        self.units = "metric" if text == "Celzijus" else "imperial"

    def start_fetch_weather(self):
        """Pokreće nit za dohvat vremena."""
        # TODO: provjera unosa, kreiranje i start WeatherFetcher niti
        city = self.city_input.text().strip()
        if not city:
            self.show_error("Molimo unesite naziv grada.", 5000)
            return

        if self.weather_thread and self.weather_thread.isRunning():
            self.statusbar.showMessage("Dohvaćanje u tijeku...", 5000)
            return
        
        self.save_last_city(city)

        self.statusbar.showMessage("Dohvaćanje podataka...", 0)
        self.weather_thread = WeatherFetcher(city, self.api_key, self.units)
        self.weather_thread.finished.connect(self.handle_weather_data)
        self.weather_thread.error.connect(self.handle_error)
        self.weather_thread.start()

    def save_last_city(self, city: str):
        """Sprema zadnji uneseni grad u bazu podataka."""
        with sqlite3.connect("weather_app.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("last_city", city))
            conn.commit()

    def handle_weather_data(self, data: dict):
        """Ažurira UI s dohvaćenim podacima."""
        # TODO: popuniti city_label, temp_label, desc_label, itd.
        #       pozvati update_icon, update_forecast_table, draw_temp_graph
        current_data = data.get("current")
        forecast_data = data.get("forecast")
        
        if current_data:
            city_name = current_data["name"]
            country_code = current_data["sys"]["country"]
            temperature = current_data["main"]["temp"]
            description = current_data["weather"][0]["description"]
            humidity = current_data["main"]["humidity"]
            wind_speed = current_data["wind"]["speed"]
            icon_code = current_data["weather"][0]["icon"]

            temp_unit = "°C" if self.units == "metric" else "°F"
            wind_unit = "m/s" if self.units == "metric" else "mph"

            self.city_label.setText(f"{city_name}, {country_code}")
            self.temp_label.setText(f"{temperature}{temp_unit}")
            self.desc_label.setText(description.capitalize())
            self.humidity_label.setText(f"Vlažnost: {humidity}%")
            self.wind_label.setText(f"Vjetar: {wind_speed} {wind_unit}")
            
            self.update_icon(icon_code)
            self.save_to_history(city_name, temperature)
            
        if forecast_data:
            self.update_forecast_table(forecast_data)
            self.draw_temp_graph(forecast_data)
        
        self.statusbar.showMessage("Podaci uspješno dohvaćeni.", 5000)

    def update_icon(self, icon_code: str):
        """Prikazuje ikonu vremena u city_label."""
        # TODO: dohvatiti ikonu s openweathermap i postaviti QPixmap
        icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"
        try:
            icon_data = requests.get(icon_url).content
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.icon_label.setPixmap(pixmap)
        except requests.RequestException:
            self.icon_label.setText("Ikona nedostupna")

    def update_forecast_table(self, forecast: dict):
        """Popunjava QTableWidget podacima prognoze."""
        # TODO: dodati 24 unosa (vrijeme, temperatura, opis)
        self.forecast_table.setRowCount(0) # Čisti tablicu
        
        list_data = forecast.get("list", [])
        self.forecast_table.setRowCount(len(list_data))
        
        temp_unit = "°C" if self.units == "metric" else "°F"

        for i, item in enumerate(list_data):
            date_time = datetime.fromtimestamp(item["dt"])
            temp = item["main"]["temp"]
            description = item["weather"][0]["description"]
            
            self.forecast_table.setItem(i, 0, QTableWidgetItem(date_time.strftime("%H:%M %d.%m.")))
            self.forecast_table.setItem(i, 1, QTableWidgetItem(f"{temp}{temp_unit}"))
            self.forecast_table.setItem(i, 2, QTableWidgetItem(description.capitalize()))
            
        self.forecast_table.resizeColumnsToContents()

    def draw_temp_graph(self, forecast: dict):
        """Crtanje grafikona temperature."""
        # TODO: nacrtati jednostavan grafikon unutar graph_label
        list_data = forecast.get("list", [])
        if not list_data:
            return

        pixmap = QPixmap(self.graph_label.width(), self.graph_label.height())
        pixmap.fill(Qt.white)
        painter = QPainter(pixmap)
        
        temps = [item["main"]["temp"] for item in list_data]
        min_temp = min(temps)
        max_temp = max(temps)

        if min_temp == max_temp:
            min_temp -= 1
            max_temp += 1

        pen = QPen(QColor(0, 120, 215))
        pen.setWidth(2)
        painter.setPen(pen)

        width = self.graph_label.width()
        height = self.graph_label.height()
        padding = 10

        points = []
        for i, temp in enumerate(temps):
            x = padding + (i / (len(temps) - 1)) * (width - 2 * padding)
            y = height - padding - ((temp - min_temp) / (max_temp - min_temp)) * (height - 2 * padding)
            points.append((x, y))

        for i in range(len(points) - 1):
            painter.drawLine(int(points[i][0]), int(points[i][1]), int(points[i+1][0]), int(points[i+1][1]))
        
        painter.end()
        self.graph_label.setPixmap(pixmap)


    def save_to_history(self, city: str, temp: float):
        """Sprema unos u tablicu history."""
        # TODO: insert u bazu (city, date, temp)
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect("weather_app.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO history (city, date, temp) VALUES (?, ?, ?)", (city, date_str, temp))
            conn.commit()

    def show_error(self, message: str):
        """Prikazuje poruku o grešci."""
        QMessageBox.critical(self, "Greška", message)

    def handle_error(self, message: str):
        """Prikazuje poruku o grešci."""
        self.statusbar.showMessage(f"Greška: {message}", 0)
        QMessageBox.warning(self, "Greška", message)
# ---------------------------------------
# Entry point
# ---------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WeatherApp()
    window.show()
    sys.exit(app.exec())

