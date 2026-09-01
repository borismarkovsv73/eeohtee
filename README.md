# IOT projekat - Tim 11
- Petar Prlina
- Boris Markov

## Uređaji po PI-u

| PI | Skripta | Settings | Senzori/aktuatori |
|----|---------|----------|--------------------|
| PI1 | `main_pi1.py` | `settings_pi1.json` | DS1, DL, DUS1, DB, DPIR1, DMS, WEBC |
| PI2 | `main_pi2.py` | `settings_pi2.json` | DS2, DUS2, DPIR2, 4SD, BTN, DHT3, GSG |
| PI3 | `main_pi3.py` | `settings_pi3.json` | DHT1, DHT2, IR, BRGB, LCD, DPIR3 |

## Pokretanje

```
docker compose up -d      # Mosquitto, InfluxDB, Grafana
python -m server.app      # server (svoj terminal)
python main_pi1.py        # po jedan terminal po PI-u
python main_pi2.py
python main_pi3.py
```

Sve podrazumevano radi simulirano (`"simulated": true` u `settings_piN.json`) - nije potreban
pravi hardver. Za pravi Pi/broker, izmeniti `broker`/`port`/`influxdb` u `settings_piN.json` i
`server/settings.json`.

## Kako pristupiti svemu

- **Web dashboard**: http://localhost:5000/ - tabovi PI1/PI2/PI3/Alarm, kartica po uređaju sa
  trenutnom vrednošću i dugmićima za svaku akciju, web kamera uživo, i Grafana panel ugrađen po tabu.
- **Grafana**: http://localhost:3000 (admin/admin) - po jedan dashboard za svaki PI plus Alarm sistem.
- **InfluxDB**: http://localhost:8086 (admin/adminadmin).
- **Konzola svakog PI-a**: iste komande kao dugmići u dashboard-u (npr. `DL ON`, `DS1 HOLD`,
  `DMS KEY 1234`, `TIMER SET 30`, `BRGB SET 255 0 0`) - ukucati `QUIET ON`/`OFF` da se utiša ispis.
- **API**: `GET /api/latest`, `GET /api/alarm`, `POST /api/alarm/disarm`, `POST /api/pi/<PI>/command`.

## Pipeline

```
senzor/aktuator (PI1-3) --MQTT (batch, daemon nit)--> server --> InfluxDB --> Grafana
                                                          |
                                                    ALARM state-mašina
                                                          |
                                              MQTT komanda nazad ka PI-u (npr. upali DB)
```

Svaki PI čita/simulira svoje senzore i šalje očitavanja u batch-evima preko MQTT-a. Server sve
upisuje u InfluxDB (prikaz u Grafani) i vodi ALARM logiku (vrata, pokret, PIN, žiroskop) - kad
treba da nešto uključi na nekom PI-u (npr. bzučač), šalje MQTT komandu nazad, koju taj PI
prosleđuje u isti mehanizam koji koristi i njegova konzola. Web dashboard samo poziva REST API
servera, koji dalje sve prosleđuje preko istog tog MQTT kanala - dugme u browseru i komanda
otkucana u terminalu rade identično.

## Arhitektura

- `components/`, `sensors/`, `simulators/`, `actuators/` - po tip uređaja; svaki komponent
  ispisuje na konzolu i šalje očitavanje u MQTT bafer (`mqtt_client/buffer.py`).
- `mqtt_client/publisher.py` - jedan generički daemon thread po PI-u, šalje sve nakupljeno u
  batch-evima na MQTT.
- `mqtt_client/commands.py`, `remote_console.py` - PI prima komande nazad preko MQTT-a
  (za aktuatore, odnosno za celu konzolnu gramatiku).
- `mqtt_client/remote_reading.py` - PI direktno prati senzor drugog PI-a preko MQTT-a (npr. PI3
  prati PI2-ov DHT3 za LCD).
- `server/alarm.py` - centralna ALARM/occupancy/arming state-mašina.
- `server/app.py` - Flask: MQTT -> InfluxDB, REST API, Web dashboard (`server/static/dashboard.html`).
- `docker/` - Mosquitto konfiguracija i Grafana provisioning (datasource + dashboard-i).
