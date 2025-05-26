# Elliott Wave Analyzer

Ein Terminal-basiertes Tool zur Analyse von Aktien mittels der Elliott-Wellen-Theorie.

## Funktionen

- Importieren historischer Marktdaten (CSV, Yahoo Finance API)
- Identifizieren von Elliott-Wellen-Mustern
- Berechnen möglicher Umkehrpunkte und Kursziele
- Backtesting der Elliott-Wellen-Analyse auf historischen Daten
- Live-Analyse mit aktuellen Marktdaten und Vorhersagen
- Konkrete Handelsempfehlungen mit Kauf-/Verkaufssignalen, Stop-Loss und Kurszielen
- Interaktives Dashboard mit einstellbarem Timeframe und automatischer Aktualisierung der Daten
- Unterstützung deutscher Börsenplätze (Xetra, Frankfurt, etc.) und Indizes (DAX, MDAX, etc.)
- Automatische Erkennung und Unterstützung von US-Aktien und -Indizes
- Interaktives Chart mit Zoom- und Pan-Funktionen

## Installation

```bash
pip install -r requirements.txt
```

Wenn Sie Probleme bei der Installation haben, versuchen Sie:

```bash
pip install setuptools wheel
pip install -r requirements.txt
```

## Konfiguration

Für die Live-Analyse mit der Yahoo Finance API können Sie eine `.env`-Datei im Projektverzeichnis erstellen:

```
AppID=IhrAppId
ClientID=IhrClientId
ClientSecret=IhrClientSecret
```

Falls keine API-Schlüssel angegeben werden, wird ein Fallback auf die öffentliche yfinance-Bibliothek verwendet.

## Verwendung

```bash
python main.py --data <dateipfad_oder_symbol> --mode <analyse|backtest|live|dashboard> [--start YYYY-MM-DD] [--end YYYY-MM-DD]
```

### Beispiele

Analyse eines bestimmten Aktien-Symbols:
```bash
python main.py --data AAPL --mode analyse
```

Analyse einer deutschen Aktie:
```bash
python main.py --data SAP --mode analyse
```

Analyse des DAX-Index:
```bash
python main.py --data DAX --mode analyse
```

Backtesting mit lokaler Datei:
```bash
python main.py --data data/AAPL.csv --mode backtest --start 2020-01-01 --end 2022-12-31
```

Live-Analyse mit aktuellen Marktdaten:
```bash
python main.py --data SAP --mode live --days 90
```

Live-Analyse mit angepasster Risikotoleranz für Stop-Loss (1%):
```bash
python main.py --data SAP --mode live --days 90 --risk 0.01
```

Interaktives Dashboard mit Live-Aktualisierung:
```bash
python main.py --data SAP --mode dashboard --days 90 --refresh 60
```

Dashboard für US-Aktien:
```bash
python main.py --data AAPL --mode dashboard --days 90 --refresh 60
```

### Dashboard-Modus

Der Dashboard-Modus bietet eine interaktive Benutzeroberfläche mit folgenden Funktionen:

- Echtzeit-Aktualisierung der Marktdaten in einstellbaren Intervallen
- Anpassbarer Timeframe (30, 60, 90, 180, 365 Tage)
- Interaktive Kontrolle der Analyseparameter (ZigZag-Threshold, Risikotoleranz)
- Auswahl verschiedener deutscher Börsenplätze (Xetra, Frankfurt, etc.)
- Automatische Erkennung von US-Aktien und Indizes
- Live-Chart mit Elliott-Wellen, aktuellen Preisen und Handelsempfehlungen
- Interaktives Chart mit Zoom-, Pan- und Speicherfunktionen
- Detaillierte Marktdaten und Handelsempfehlungen

Parameter für den Dashboard-Modus:
- `--days`: Anfänglicher Timeframe in Tagen (Standard: 90)
- `--refresh`: Aktualisierungsintervall in Sekunden (Standard: 60)
- `--threshold`: ZigZag-Threshold für die Wellenanalyse (Standard: 0.03)
- `--risk`: Risikotoleranz für Handelsempfehlungen (Standard: 0.02)

### Unterstützte deutsche Börsenplätze

- XETR: Xetra (Standard)
- FRA: Frankfurt
- BER: Berlin
- STU: Stuttgart
- MUN: München
- HAM: Hamburg
- HAN: Hannover
- DUS: Düsseldorf

### Unterstützte deutsche Indizes

- DAX: Deutscher Aktienindex
- MDAX: Mid-Cap-DAX
- SDAX: Small-Cap-DAX
- TecDAX: Technologie-Index
- HDAX: Composite-Index aus DAX, MDAX und TecDAX

### Unterstützte US-Indizes

- ^GSPC: S&P 500
- ^DJI: Dow Jones Industrial Average
- ^IXIC: NASDAQ Composite
- ^RUT: Russell 2000
- ^VIX: Volatility Index

## Datenformat

Das Tool unterstützt CSV-Dateien mit folgendem Format:
```
Datum,Open,High,Low,Close,Volume
2023-01-01,150.23,152.45,149.92,151.73,1234567
...
```

Alternativ können Daten über das Yahoo Finance API abgerufen werden, indem das entsprechende Tickersymbol angegeben wird.

## Handelsempfehlungen

Das Tool generiert basierend auf der Elliott-Wellen-Analyse konkrete Handelsempfehlungen:

- **Kaufen/Verkaufen**: Klare Handelsrichtung mit Begründung
- **Kursziele**: Mehrere potenzielle Zielpreise mit prozentualer Änderung
- **Stop-Loss**: Empfohlener Stop-Loss-Kurs zur Risikobegrenzung
- **Risk/Reward-Verhältnis**: Verhältnis zwischen potenziellem Gewinn und Risiko

Die Handelsempfehlungen werden sowohl in der Konsolenausgabe als auch in der Visualisierung dargestellt. 