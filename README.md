# Elliott Wave Analyzer

Ein Terminal-basiertes Tool zur Analyse von Aktien mittels der Elliott-Wellen-Theorie.

## Funktionen

- Importieren historischer Marktdaten (CSV, Yahoo Finance API)
- Identifizieren von Elliott-Wellen-Mustern
- Berechnen möglicher Umkehrpunkte und Kursziele
- Backtesting der Elliott-Wellen-Analyse auf historischen Daten
- Live-Analyse mit aktuellen Marktdaten und Vorhersagen
- Konkrete Handelsempfehlungen mit Kauf-/Verkaufssignalen, Stop-Loss und Kurszielen

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
python main.py --data <dateipfad_oder_symbol> --mode <analyse|backtest|live> [--start YYYY-MM-DD] [--end YYYY-MM-DD]
```

### Beispiele

Analyse eines bestimmten Aktien-Symbols:
```bash
python main.py --data AAPL --mode analyse
```

Backtesting mit lokaler Datei:
```bash
python main.py --data data/AAPL.csv --mode backtest --start 2020-01-01 --end 2022-12-31
```

Live-Analyse mit aktuellen Marktdaten:
```bash
python main.py --data AAPL --mode live --days 90
```

Live-Analyse mit angepasster Risikotoleranz für Stop-Loss (1%):
```bash
python main.py --data AAPL --mode live --days 90 --risk 0.01
```

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