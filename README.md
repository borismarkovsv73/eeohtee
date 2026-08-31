# IOT projekat - Tim 11
- Petar Prlina
- Boris Markov

## Uređaji po PI-u

| PI | Skripta | Settings | Senzori/aktuatori |
|----|---------|----------|--------------------|
| PI1 | `main_pi1.py` | `settings_pi1.json` | DS1, DL, DUS1, DB, DPIR1, DMS |
| PI2 | `main_pi2.py` | `settings_pi2.json` | DS2, DUS2, DPIR2, 4SD, BTN, DHT3, GSG |
| PI3 | `main_pi3.py` | `settings_pi3.json` | DHT1, DHT2, IR, BRGB, LCD, DPIR3 |

Web kamera (WEBC) namerno nije implementirana (nije traženo specifikacijom do odbrane).

## Pokretanje (KT2, za sva tri PI-a)

### 1. Lokalna infrastruktura (MQTT broker, InfluxDB, Grafana)

Za lokalno testiranje, u repozitorijumu se nalazi `docker-compose.yml` koji podiže Mosquitto,
InfluxDB 2.x (unapred podešen sa organizacijom/bucket-om `smarthome` i tokenom `smarthome-dev-token`)
i Grafana (unapred podešen datasource + po jedan dashboard za svaki PI, sa panelom za svaki
tip senzora/aktuatora). Podaci i kredencijali u ovom fajlu su namenjeni isključivo lokalnom
razvoju/testiranju.

```
docker compose up -d
```

- MQTT broker: `localhost:1883`
- InfluxDB UI: http://localhost:8086 (admin / adminadmin)
- Grafana: http://localhost:3000 (admin / admin) - dashboards "Smart Home - PI1/PI2/PI3 Sensors & Actuators"

Na pravom Raspberry Pi/labaratorijskom brokeru, samo izmeniti `broker`/`port`/`influxdb` vrednosti
u odgovarajućem `settings_piN.json` i u `server/settings.json`.

### 2. PI skripte (senzori/aktuatori)

```
pip install -r requirements.txt
python main_pi1.py   # na PI1 uređaju
python main_pi2.py   # na PI2 uređaju
python main_pi3.py   # na PI3 uređaju
```

Svaki PI ima svoj settings fajl (`settings_pi1.json` / `settings_pi2.json` / `settings_pi3.json`)
sa konfiguracijom uređaja (PI id, ime, lokacija) i MQTT podešavanjima (broker, topic prefix,
interval slanja batch-eva). Svaki senzor/aktuator se pojedinačno uključuje/isključuje i
simulira preko `"enabled"`/`"simulated"` polja - realni GPIO kod se koristi samo kad je
`"simulated": false`.

Konzola za upravljanje aktuatorima (`console.py`) je generička - svaki `main_piN.py` prijavljuje
sopstvenu listu aktuatora sa komandama (npr. `DL ON`, `4SD SET 0130`, `BRGB SET 255 0 0`,
`LCD SET 0 tekst`), pa dodavanje novog aktuatora ne zahteva izmenu `console.py`.

### 3. Server (MQTT -> InfluxDB)

```
python -m server.app
```

Server se pretplaćuje na `smarthome/#`, upisuje očitavanja u InfluxDB i izlaže:
- `GET /health` - provera da server radi
- `GET /api/latest` - poslednje očitavanje za svaki senzor/aktuator

## Arhitektura (KT2)

- `mqtt_client/buffer.py` - deljeni bafer očitavanja; jedan `threading.Lock` čuva samo append/drain
  operacije (minimalna kritična sekcija), bez ugnježdenih lock-ova pa je deadlock isključen.
- `mqtt_client/publisher.py` - generički daemon thread (radi za sve tipove senzora, na sva tri PI-a)
  koji periodično (`mqtt.batch_interval`) izvlači sve nakupljene vrednosti i šalje ih u
  batch-evima na MQTT, uz `"simulated"` tag u payload-u.
- `components/*.py` - svaki komponent i dalje ispisuje na konzolu (KT1 ponašanje), a dodatno
  prosleđuje očitavanje u MQTT bafer. Senzori/aktuatori bez ikakve specifične logike (DS2, DUS2,
  DPIR2, DPIR3, BTN) ponovo koriste postojeće generičke komponente (`button.py`, `uds.py`, `pir.py`).
- `sensors/`, `simulators/`, `actuators/` - novi tipovi za PI2/PI3 (DHT, GSG, IR, BRGB, LCD, 4SD)
  su ručno implementirani direktno preko `RPi.GPIO`, bez ijedne dodatne hardverske biblioteke -
  isti pristup kao za PI1 (DUS1's bit-banged timing, DMS-ov skener tastature, itd). Senzori sa
  višestrukim merenjima po očitavanju (DHT temperatura+vlažnost, BRGB R/G/B, LCD dva reda, 4SD
  prikaz+treperenje) šalju svaku vrednost kao poseban InfluxDB *field* (ne kao odvojen "value"),
  da ne bi došlo do konflikta tipova u istom measurement-u.
- `server/` - Flask aplikacija koja pokreće MQTT subscriber (paho-mqtt) i upisuje podatke u
  InfluxDB (`influxdb-client`, sopstveni interni batching write API).
- `docker/` - Mosquitto konfiguracija i Grafana provisioning (datasource + tri dashboard-a,
  po jedan za svaki PI).
