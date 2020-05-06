# HSS + Rhein-Main-Verkehrsverbund

Skill zur Abfrage von Verbindungen des RMV.

Benötigt den [Hermes Skill Server](https://github.com/patrickjane/hss-server) (HSS).

# Installation

#### 1) Registrierung bei RMV Open Data

Die Fahrpläne werden direkt bei der RMV über die Open Data API abgefragt. Hierfür ist eine Registrierung/Zugangstoken nötig.

Die Registrierung ist hier möglich: https://opendata.rmv.de/site/anmeldeseite.html

Nach einigen Tagen erhält man eine E-Mail mit Details, unter anderem den **API-KEY** (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx). Dieser wird als Parameter an den Skill übergeben und für jede Abfrage verwendet. Ohne den Key sind keine Abfragen möglich.

#### 2) Installation des Skills im HSS

```
/home/s710 $> cd hss
/home/s710/hss $> source venv/bin/activate

(venv) /home/s710/hss $> hss-cli --install --url=https://github.com/patrickjane/hss-s710-rmv
Installing 'hss-s710-rmv' into '/home/pi/.config/hss_server/skills/hss-s710-rmv'
Cloning repository ...
Creating venv ...
Installing dependencies ...
[...]
Initializing config.ini ...
Section 'skill'
Enter value for parameter 'rmv_homestation': Hauptwache
Enter value for parameter 'rmv_homecity': Frankfurt
Enter value for parameter 'rmv_homecity_only': False
Enter value for parameter 'time_offset': 0
Enter value for parameter 'short_info': False
Enter value for parameter 'rmv_api_key': xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

Skill 'hss-s710-rmv' successfully installed.

(venv) /home/s710/hss $>
```

#### 3) HSS neu starten

Nach der Installation von Skills muss der Hermes Skill Server neu gestartet werden.

# Parameter

Die App bentöigt die folgenden Parameter:

- `rmv_homestation`: Home-Station von der aus Verbindungen gesucht werden
- `rmv_homecity`: Heimatstadt
- `rmv_homecity_only`: Alle Verbindungen werden nur in der Heimatstadt gesucht
- `rmv_api_key`: Der API-Key (siehe Schritt Installation/1))
- `time_offset`: Anzahl Minuten die zur aktuellen Zeit addiert werden, wenn die nächste Bahn ohne Zeitangabe abgefragt wird. Es wird dann also eine Verbindung ab "in `time_offset` Minuten" abgefragt. Wenn `time_offset` auf 0 gesetzt wird, wird die aktuelle Uhrzeit verwendet.
- `short_info`: Bei `short_info=True`: Die Antwort enthält nur eine Kurzinfo bestehend aus erster Bahnverbindung und der Ankunftszeit, also ohne Umsteigeinformationen bzw. Zwischenverbindungen.

# Funktionen

Die App umfasst folgende Intents:

- `s710:getTrainTo` - Suche einer Verbindung von der Home-Station zu einer Zielstation. Optional zu einer bestimmen Uhrzeit.

Die App kann Verbindungen im gesamten RMV-Gebiet abfragen. Hierbei kann es passieren, dass Stationen nicht eindeutig sind ("Willy-Brand-Platz Darmstadt" vs. "Willy-Brand-Platz Frankfurt").     

Um dieses Problem zu lösen, gibt es 2 Möglichkeiten:

1) Im Sprachkommando den Städtenamen mit sprechen ("Wann fährt die nächste Bahn zum Willy-Brandt-Platz Frankfurt?")    
2) Den Parameter `rmv_homecity_only` aktivieren

Bei Variante 2) ergänzt die App bei jeder Stationssuche den Namen der Heimatstadt. Das bedeutet, bei *"Wann fährt die nächste Bahn zum Willy-Brandt-Platz?"* wird nach "Willy-Brandt-Platz Frankfurt" gesucht. Das bedeutet gleichzeitig, dass dabei keine Suche mehr ausserhalb der Heimatstadt möglich ist (*"Wann fährt die nächste Bahn zum Willy-Brandt-Platz Darmstadt?"* würde entsprechend zu "Willy-Brandt-Platz Darmstadt Frankfurt").

Der Parameter `rmv_homecity_only` ist daher ein Komfortparameter wenn die App nur verwendet wird, um Verbindungen innerhalb der Heimatstadt abzufragen.

Vor jeder Abfrage ermittelt die App über die RMV-API die Start- und Zielstation. Hierbei kann es zu mehr als einem Ergebnis pro Station kommen. Die App wählt automatisch das erste Ergebnis der RMV-Abfrage. Führt dies zu falschen Ergebnissen, muss der Zielort genauer angegeben werden, bzw. die Home-Station genauer konfiguriert werden (z. B. "Willy-Brandt-Platz Frankfurt" anstatt "Willy-Brandt-Platz").
