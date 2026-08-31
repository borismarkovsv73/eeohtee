# IOT projekat - Tim 11
- Petar Prlina
- Boris Markov

## Pokretanje (KT2)

### 1. Lokalna infrastruktura (MQTT broker, InfluxDB, Grafana)

Za lokalno testiranje, u repozitorijumu se nalazi `docker-compose.yml` koji podiže Mosquitto,
InfluxDB 2.x (unapred podešen sa organizacijom/bucket-om `smarthome` i tokenom `smarthome-dev-token`)
i Grafana (unapred podešen datasource + dashboard sa panelom za svaki tip senzora/aktuatora).
Podaci i kredencijali u ovom fajlu su namenjeni isključivo lokalnom razvoju/testiranju.

```
docker compose up -d
```

- MQTT broker: `localhost:1883`
- InfluxDB UI: http://localhost:8086 (admin / adminadmin)
- Grafana: http://localhost:3000 (admin / admin, dashboard "Smart Home - PI1 Sensors & Actuators")

Na pravom Raspberry Pi/labaratorijskom brokeru, samo izmeniti `broker`/`port`/`influxdb` vrednosti
u `settings.json` i `server/settings.json`.

### 2. PI1 skripta (senzori/aktuatori)

```
pip install -r requirements.txt
python main.py
```

Konfiguracija uređaja (PI, ime, lokacija) i MQTT podešavanja (broker, topic prefix, interval
slanja batch-eva) nalaze se u `settings.json`. Svaki senzor/aktuator se može pojedinačno
uključiti/isključiti i simulirati preko `"enabled"`/`"simulated"` polja.

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
- `mqtt_client/publisher.py` - generički daemon thread (radi za sve tipove senzora) koji periodično
  (`mqtt.batch_interval`) izvlači sve nakupljene vrednosti i šalje ih u batch-evima na MQTT, uz
  `"simulated"` tag u payload-u.
- `components/*.py` - svaki komponent i dalje ispisuje na konzolu (KT1 ponašanje), a dodatno
  prosleđuje očitavanje u MQTT bafer.
- `server/` - Flask aplikacija koja pokreće MQTT subscriber (paho-mqtt) i upisuje podatke u
  InfluxDB (`influxdb-client`, sopstveni interni batching write API).
- `docker/` - Mosquitto konfiguracija i Grafana provisioning (datasource + dashboard).
