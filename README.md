# IOT projekat - Tim 11
- Petar Prlina
- Boris Markov

## Uređaji po PI-u

| PI | Skripta | Settings | Senzori/aktuatori |
|----|---------|----------|--------------------|
| PI1 | `main_pi1.py` | `settings_pi1.json` | DS1, DL, DUS1, DB, DPIR1, DMS |
| PI2 | `main_pi2.py` | `settings_pi2.json` | DS2, DUS2, DPIR2, 4SD, BTN, DHT3, GSG |
| PI3 | `main_pi3.py` | `settings_pi3.json` | DHT1, DHT2, IR, BRGB, LCD, DPIR3 |

Web kamera (WEBC) implementirana je na PI1 (`components/webc.py`) - simulirano kao ručno
napisani MJPEG server, realno kao `mjpg_streamer` subproces.

## Kompletan test scenario

Redosled za testiranje celog sistema od nule (sve u simuliranom režimu, bez pravog hardvera):

### 1. Infrastruktura + server

```
docker compose up -d
python -m server.app
```

Proveriti: `curl http://localhost:5000/health` -> `{"status":"ok"}`.

### 2. Pokrenuti sva tri PI-a (svaki u svom terminalu)

```
python main_pi1.py
python main_pi2.py
python main_pi3.py
```

Svaki bi trebalo odmah da ispisuje očitavanja u konzoli i da javi `[MQTT] publisher daemon started`.
Ako je previše ispisa, ukucati `QUIET ON` u bilo kojoj konzoli (`QUIET OFF` da se vrati).

### 3. Provera KT1/KT2 osnova

- Konzolne komande za aktuatore: `DL ON`/`DL OFF`, `DB BUZZ` (PI1); `4SD SET 0130` (PI2);
  `BRGB SET 255 0 0`, `LCD SET 0 Hello` (PI3) - svaka treba odmah da se ispiše u konzoli.
- `curl http://localhost:5000/api/latest` - poslednje očitavanje svakog senzora/aktuatora.
- Grafana (http://localhost:3000, admin/admin) - dashboard-i "Smart Home - PI1/PI2/PI3 Sensors &
  Actuators" treba da pokazuju uživo podatke (osveženje na 5s).

### 4. WEBC (web kamera)

Otvoriti u browseru `http://localhost:8080/?action=stream` (sirovi stream) ili
`http://localhost:5000/camera` (stranica sa poljem za URL) - treba da se vidi kvadrat koji
polako menja boju (simulirana kamera).

### 5. ALARM (stavke 1-6, na PI1/PI2 konzoli)

```
DPIR1 TRIGGER              # stavka 1: DL treba da se upali na 10s
DUS1 SET 200
DUS1 SET 30
DPIR1 TRIGGER              # stavka 2: occupancy raste (osoba se približava)
DS1 HOLD                   # stavka 3: sačekati 5s+
curl http://localhost:5000/api/alarm   # alarm_active=true, reason=DOOR_HELD_OPEN
DMS KEY 1234                # PIN isključuje ALARM (radi u bilo kom trenutku)
DS1 RELEASE

DMS KEY 1234                # stavka 4a: PIN pali arm countdown (10s)
# sačekati 10s+, GET /api/alarm -> armed=true
DS1 HOLD                    # stavka 4b: sačekati 3s+
curl http://localhost:5000/api/alarm   # reason=UNAUTHORIZED_ENTRY
DMS KEY 1234                # stavka 4c: disarm
DS1 RELEASE

GSG TRIGGER                 # stavka 6 (na PI2 konzoli): reason=GSG_MOVEMENT
DMS KEY 1234                # disarm
```

Stavka 5 (occupancy==0 + pokret -> ALARM) se najlakše vidi kad se pusti da prođe malo vremena
bez ijednog `DPIR TRIGGER` uzastopno (occupancy ostaje 0), pa bilo koji `DPIRx TRIGGER` odmah
uključuje ALARM sa `reason=EMPTY_HOUSE_MOTION`.

Disarm ide i preko API-ja (budući Web app): `curl -X POST http://localhost:5000/api/alarm/disarm
-d '{"pin":"1234"}'`. Kompletna istorija ALARM/SECURITY/OCCUPANCY događaja je u Grafana
dashboard-u "Smart Home - Alarm System".

### 6. Nezavisne funkcionalnosti (stavke 7-10)

```
# stavka 7 - samo sačekati; LCD (PI3 konzola) rotira DHT1/DHT2/DHT3 na svake 4s
# (DHT3 dolazi sa PI2 - obe skripte moraju da rade istovremeno)

# stavka 8 - kuhinjska štoperica (PI2 konzola)
TIMER SET 10
# sačekati da otkuca do 0, 4SD treba da počne da treperi (Blinking: True)
BTN PRESS      # zaustavlja treperenje

# stavka 9 - BRGB preko IR (PI3 konzola)
IR CODE 0x46   # crvena
IR CODE 0x47   # zelena
IR CODE 0x45   # isključi

# stavka 10 - već pokriveno WEBC-om, videti korak 4
```

Napomena: pošto svi senzori imaju i svoje nasumične simulatore koji rade u pozadini (npr. BTN-ov
simulator može sam da doda vreme na štopericu dok testirate), ne treba se iznenaditi ako se
brojevi pomere i bez ručne komande - to je očekivano ponašanje, ne greška.

## ALARM logika (Odbrana, stavke 1-6)

Alarm/occupancy/arming logika živi centralno na serveru (`server/alarm.py`), jer je server
jedini proces koji već vidi očitavanja sa sva tri PI-a preko MQTT-a. Kada treba da uključi/isključi
DB (bzučač na PI1), server objavljuje MQTT komandu na `smarthome/PI1/DB/cmd`, koju PI1 (preko
`mqtt_client/commands.py`) prosleđuje direktno u već postojeći DB queue - isti mehanizam koji
koristi i konzolna komanda `DB BUZZ`.

Implementirano:
1. Pokret na DPIR1 pali DL na 10s - **lokalno** na PI1 (`main_pi1.py`), bez odlaska na server.
2. DUS1/DUS2 istorija (poslednjih par sekundi) određuje da li se neko približava (ulazi) ili
   udaljava (izlazi) od vrata; brojno stanje osoba (`occupancy`) se čuva na serveru.
3. DS1/DS2 pritisnut duže od 5s -> ALARM (`DOOR_HELD_OPEN`), bez obzira na `armed` stanje.
4. Ispravan 4-cifreni PIN na DMS-u aktivira sistem posle 10s; ako je sistem aktivan i DS1/DS2
   okine bez ispravnog PIN-a u roku od 3s -> ALARM (`UNAUTHORIZED_ENTRY`). PIN uvek deaktivira
   ALARM i sistem, bez obzira na trenutno stanje.
5. `occupancy == 0` + pokret na bilo kom DPIR1-3 -> ALARM (`EMPTY_HOUSE_MOTION`).
6. Pokret na GSG -> ALARM (`GSG_MOVEMENT`).

Svi ulazi/izlazi u ALARM, kao i ARM/DISARM i promene brojnog stanja osoba, upisuju se u InfluxDB
(measurement-i `ALARM`, `SECURITY`, `OCCUPANCY`) i prikazuju u Grafana dashboard-u
"Smart Home - Alarm System" (`docker/grafana/dashboards/smarthome-alarm.json`).

Trenutno stanje i disarm preko (buduće) Web aplikacije već rade preko API-ja:
- `GET /api/alarm` - `{alarm_active, alarm_reason, armed, occupancy, pending_arm}`
- `POST /api/alarm/disarm` - `{"pin": "1234"}` -> `200` ako je PIN tačan, inače `403`

PIN i sva vremena (arm delay, door threshold, grace period, distance window) su podesivi u
`server/settings.json` pod `"alarm"`.

### Testiranje u simuliranom režimu

Pošto simulatori senzora rade nezavisno i nasumično (DUS1 nema nikakvu vezu sa DPIR1, DS1 se
neće pouzdano zadržati u "pritisnutom" stanju tačno 5+ sekundi, DMS-ov nasumični generator
praktično nikad neće ukucati baš tačan PIN), svaki `main_piN.py` ima dodatne **trigger komande**
u konzoli koje direktno pozivaju pravi callback senzora (isti onaj koji koristi pravi/simulirani
GPIO), pa se svako pravilo alarma može ručno okinuti na zahtev:

- PI1: `DS1 HOLD` / `DS1 RELEASE`, `DPIR1 TRIGGER`, `DUS1 SET <cm>`, `DMS KEY <cifre>`
- PI2: `DS2 HOLD` / `DS2 RELEASE`, `DPIR2 TRIGGER`, `DUS2 SET <cm>`, `GSG TRIGGER`
- PI3: `DPIR3 TRIGGER`

Primer - testiranje "vrata otvorena >5s":
```
DS1 HOLD
# sačekati 5+ sekundi, GET /api/alarm treba da pokaže alarm_active=true, reason=DOOR_HELD_OPEN
DMS KEY 1234
# ALARM se isključuje, PIN takođe deaktivira sistem
```

Napomena: podrazumevani `batch_interval` je snižen na 1s (sa 5s) u svim `settings_piN.json`
fajlovima da bi alarm reagovao dovoljno brzo za demo - i dalje se šalje u batch-evima (KT2
zahtev), samo je prozor kraći.

## Nezavisne funkcionalnosti (Odbrana, stavke 7-10)

Za razliku od ALARM logike, ove funkcionalnosti su nezavisne jedna od druge - svaka živi lokalno
na svom PI-u (osim stavke 7, koja mora da pređe sa PI2 na PI3).

**7. LCD rotacija DHT1-3** (`main_pi3.py`) - LCD prikazuje temperaturu/vlažnost sa DHT1, DHT2,
DHT3 naizmenično na svake 4s. DHT1/DHT2 su lokalni na PI3 (čita se preko `on_reading` hook-a),
ali DHT3 je fizički na PI2 - PI3 ga direktno prati preko MQTT-a
(`mqtt_client/remote_reading.py`, pretplata na `smarthome/PI2/DHT3`), bez odlaska preko servera.
Isti mehanizam bi poslužio i za bilo koji drugi cross-PI slučaj.

**8. Kuhinjska štoperica** (`main_pi2.py`, `components/timer.py`) - lokalna state-mašina na PI2
(BTN i 4SD su oba tamo), pokreće postojeći 4SD queue (nema izmena u `actuators/sd4.py`).
Podešavanje vremena i N-a (koliko sekundi BTN dodaje) rade preko:
- konzole: `TIMER SET <sekunde>`, `TIMER INCREMENT <sekunde>`, `BTN PRESS` (force-trigger)
- (buduće) Web aplikacije već sada preko API-ja: `POST /api/timer/set {"seconds": N}`,
  `POST /api/timer/config {"add_seconds": N}`

Kad štoperica istekne, 4SD počinje da treperi ("00:00"); pritisak na BTN (ili `BTN PRESS`)
zaustavlja treperenje bez dodavanja vremena.

**9. BRGB preko IR i Web aplikacije** (`main_pi3.py`) - IR daljinski i BRGB su oba na PI3, pa je
mapiranje lokalno (`IR_REMOTE_MAP` u `main_pi3.py`): dekodirani kod daljinskog direktno šalje
`MANUAL_SET`/`MANUAL_OFF` komandu na BRGB queue - isti mehanizam koji koristi i konzolna komanda
`BRGB SET r g b`. Za testiranje bez pravog daljinskog: `IR CODE 0x46` (crvena), `0x47` (zelena),
`0x44` (plava), `0x40` (bela), `0x45` (isključi). Web aplikacija (već sada) preko
`POST /api/brgb {"r":.., "g":.., "b":..}` ili `{"on": false}`.

**10. Video sa web kamere na Web aplikaciji** - već pokriveno WEBC implementacijom
(`/camera` na Flask serveru); nije trebalo ništa dodatno graditi za ovu stavku.

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
