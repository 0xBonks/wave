#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from tabulate import tabulate

from data_loader import DataLoader
from elliott_wave import ElliottWaveAnalyzer

def parse_args():
    """
    Parst die Kommandozeilenargumente.
    
    Returns:
        argparse.Namespace: Geparste Argumente
    """
    parser = argparse.ArgumentParser(description='Elliott Wave Analyzer - Ein Tool zur Analyse von Aktien mit der Elliott-Wellen-Theorie')
    
    parser.add_argument('--data', type=str, required=True,
                        help='Dateipfad oder Ticker-Symbol für die zu analysierenden Daten')
    
    parser.add_argument('--mode', type=str, choices=['analyse', 'backtest', 'live'], default='analyse',
                        help='Betriebsmodus: "analyse" für Elliott-Wellen-Analyse, "backtest" für Backtesting, "live" für Live-Analyse')
    
    parser.add_argument('--start', type=str, default=None,
                        help='Startdatum im Format YYYY-MM-DD')
    
    parser.add_argument('--end', type=str, default=None,
                        help='Enddatum im Format YYYY-MM-DD')
    
    parser.add_argument('--threshold', type=float, default=0.03,
                        help='Schwellenwert für ZigZag-Filter (in Dezimalform, Standard: 0.03 = 3%%)')
    
    parser.add_argument('--window', type=int, default=10,
                        help='Fenstergröße für die Extrema-Erkennung (Standard: 10)')
    
    parser.add_argument('--save', type=str, default=None,
                        help='Speichert die Analysegrafik in der angegebenen Datei')
    
    parser.add_argument('--invest', type=float, default=10000,
                        help='Anfänglicher Investitionsbetrag für Backtests (Standard: 10000)')
    
    parser.add_argument('--output', type=str, choices=['table', 'csv', 'json'], default='table',
                        help='Ausgabeformat für Ergebnisse: "table", "csv" oder "json"')
    
    parser.add_argument('--days', type=int, default=90,
                        help='Anzahl der Tage für die Live-Analyse (Standard: 90)')
    
    parser.add_argument('--risk', type=float, default=0.02,
                        help='Risikotoleranz für Handelsempfehlungen (Standard: 0.02 = 2%)')
    
    return parser.parse_args()

# Hilfsfunktion, um sicherzustellen, dass Werte als native Python-Typen vorliegen
def ensure_native_type(value):
    """
    Konvertiert numpy-Typen in native Python-Typen.
    
    Args:
        value: Ein Wert, der möglicherweise ein numpy-Typ ist
        
    Returns:
        Der Wert als nativer Python-Typ
    """
    if isinstance(value, (np.number, np.ndarray)):
        return value.item() if hasattr(value, 'item') else float(value)
    return value

def get_trade_recommendations(current_wave, prediction, current_price, risk_tolerance=0.02):
    """
    Generiert Handelsempfehlungen basierend auf der Elliott-Wellen-Analyse.
    
    Args:
        current_wave (dict): Informationen zur aktuellen Welle
        prediction (dict): Vorhersage des ElliottWaveAnalyzer
        current_price (float): Aktueller Preis
        risk_tolerance (float): Risikotoleranz für Stop-Loss (als Dezimalzahl)
        
    Returns:
        dict: Handelsempfehlungen
    """
    # Stelle sicher, dass current_price ein nativer Python-Typ ist
    current_price = ensure_native_type(current_price)
    
    if not current_wave or prediction['confidence'] < 0.5:
        return {
            'empfehlung': 'Neutral - Abwarten',
            'grund': 'Unzureichende Wellenstruktur oder niedrige Konfidenz',
            'ziele': None,
            'stop_loss': None,
            'risk_reward': None
        }
    
    wave_type = current_wave['type']
    targets = current_wave['next_target']
    
    # Standardwerte
    recommendation = {
        'empfehlung': 'Neutral',
        'grund': 'Keine klare Handelsempfehlung',
        'einstieg': current_price,
        'ziele': [],
        'stop_loss': None,
        'risk_reward': None
    }
    
    if prediction['prediction'] == 'Trendfortsetzung erwartet':
        # Nach einer Korrekturwelle erwarten wir einen Aufwärtstrend
        if isinstance(targets, tuple):
            # Stelle sicher, dass die Zielwerte native Python-Typen sind
            target1 = ensure_native_type(targets[0])
            target2 = ensure_native_type(targets[1])
            
            # Berechne die prozentuale Veränderung
            target1_change = (target1 - current_price) / current_price
            target2_change = (target2 - current_price) / current_price
            
            # Bestimme die Richtung des erwarteten Trends
            is_uptrend = target1_change > 0
            
            if is_uptrend:
                # Kaufempfehlung bei erwartetem Aufwärtstrend
                stop_loss = current_price * (1 - risk_tolerance)
                risk = current_price - stop_loss
                reward1 = target1 - current_price
                reward2 = target2 - current_price
                risk_reward1 = reward1 / risk if risk > 0 else 0
                risk_reward2 = reward2 / risk if risk > 0 else 0
                
                recommendation = {
                    'empfehlung': 'Kaufen',
                    'grund': f'Fortsetzung des Aufwärtstrends nach {wave_type} Welle',
                    'einstieg': current_price,
                    'ziele': [
                        {'preis': target1, 'änderung': f"{target1_change*100:.2f}%"},
                        {'preis': target2, 'änderung': f"{target2_change*100:.2f}%"}
                    ],
                    'stop_loss': stop_loss,
                    'risk_reward': [risk_reward1, risk_reward2]
                }
            else:
                # Verkaufsempfehlung bei erwartetem Abwärtstrend
                stop_loss = current_price * (1 + risk_tolerance)
                risk = stop_loss - current_price
                reward1 = current_price - target1
                reward2 = current_price - target2
                risk_reward1 = reward1 / risk if risk > 0 else 0
                risk_reward2 = reward2 / risk if risk > 0 else 0
                
                recommendation = {
                    'empfehlung': 'Verkaufen',
                    'grund': f'Fortsetzung des Abwärtstrends nach {wave_type} Welle',
                    'einstieg': current_price,
                    'ziele': [
                        {'preis': target1, 'änderung': f"{target1_change*100:.2f}%"},
                        {'preis': target2, 'änderung': f"{target2_change*100:.2f}%"}
                    ],
                    'stop_loss': stop_loss,
                    'risk_reward': [risk_reward1, risk_reward2]
                }
        
    elif prediction['prediction'] == 'Korrektur erwartet':
        # Nach einer Impulswelle erwarten wir eine Korrektur
        if isinstance(targets, tuple):
            # Stelle sicher, dass die Zielwerte native Python-Typen sind
            target1 = ensure_native_type(targets[0])
            target2 = ensure_native_type(targets[1])
            
            # Berechne die prozentuale Veränderung
            target1_change = (target1 - current_price) / current_price
            target2_change = (target2 - current_price) / current_price
            
            # Bestimme die Richtung der erwarteten Korrektur
            is_downward_correction = target1_change < 0
            
            if is_downward_correction:
                # Verkaufsempfehlung bei erwarteter Abwärtskorrektur
                stop_loss = current_price * (1 + risk_tolerance)
                risk = stop_loss - current_price
                reward1 = current_price - target1
                reward2 = current_price - target2
                risk_reward1 = reward1 / risk if risk > 0 else 0
                risk_reward2 = reward2 / risk if risk > 0 else 0
                
                recommendation = {
                    'empfehlung': 'Verkaufen',
                    'grund': f'Erwartete Korrektur nach {wave_type} Welle',
                    'einstieg': current_price,
                    'ziele': [
                        {'preis': target1, 'änderung': f"{target1_change*100:.2f}%"},
                        {'preis': target2, 'änderung': f"{target2_change*100:.2f}%"}
                    ],
                    'stop_loss': stop_loss,
                    'risk_reward': [risk_reward1, risk_reward2]
                }
            else:
                # Kaufempfehlung bei erwarteter Aufwärtskorrektur (selten)
                stop_loss = current_price * (1 - risk_tolerance)
                risk = current_price - stop_loss
                reward1 = target1 - current_price
                reward2 = target2 - current_price
                risk_reward1 = reward1 / risk if risk > 0 else 0
                risk_reward2 = reward2 / risk if risk > 0 else 0
                
                recommendation = {
                    'empfehlung': 'Kaufen',
                    'grund': f'Erwartete Aufwärtskorrektur nach {wave_type} Welle',
                    'einstieg': current_price,
                    'ziele': [
                        {'preis': target1, 'änderung': f"{target1_change*100:.2f}%"},
                        {'preis': target2, 'änderung': f"{target2_change*100:.2f}%"}
                    ],
                    'stop_loss': stop_loss,
                    'risk_reward': [risk_reward1, risk_reward2]
                }
    
    return recommendation

def run_analysis(args):
    """
    Führt die Elliott-Wellen-Analyse durch.
    
    Args:
        args (argparse.Namespace): Kommandozeilenargumente
    """
    # Lade die Daten
    try:
        print(f"Lade Daten für {args.data}...")
        data = DataLoader.load_data(args.data, args.start, args.end)
        
        if data.empty:
            print(f"Fehler: Keine Daten für {args.data} gefunden.")
            sys.exit(1)
            
        print(f"Daten geladen: {len(data)} Datenpunkte von {data.index[0].strftime('%Y-%m-%d')} bis {data.index[-1].strftime('%Y-%m-%d')}")
    except Exception as e:
        print(f"Fehler beim Laden der Daten: {str(e)}")
        sys.exit(1)
    
    # Erstelle den Analyzer
    analyzer = ElliottWaveAnalyzer(data)
    
    # Führe die Analyse durch
    print("Analysiere Elliott-Wellen-Muster...")
    waves = analyzer.analyze(zigzag_threshold=args.threshold, window_size=args.window)
    
    # Zeige die Ergebnisse an
    print("\nGefundene Elliott-Wellen-Muster:")
    
    pattern_count = 0
    for wave_type, wave_list in waves.items():
        if wave_list:
            print(f"\n{wave_type.capitalize()} Wellen: {len(wave_list)}")
            pattern_count += len(wave_list)
            
            # Erstelle eine Tabelle mit den Welleninformationen
            table_data = []
            for wave in wave_list:
                indices = wave['indices']
                dates = [data.index[i].strftime('%Y-%m-%d') for i in indices if i < len(data)]
                prices = [data['Close'].iloc[i] for i in indices if i < len(data)]
                
                # Füge die Daten zur Tabelle hinzu
                table_data.append([
                    wave['wave_count'],
                    dates[0] if dates else "N/A",
                    dates[-1] if dates else "N/A",
                    prices[0] if prices else 0,
                    prices[-1] if prices else 0,
                    f"{((prices[-1] / prices[0]) - 1) * 100:.2f}%" if prices and prices[0] != 0 else "N/A"
                ])
            
            # Zeige die Tabelle an
            headers = ["#", "Start-Datum", "End-Datum", "Start-Preis", "End-Preis", "Änderung"]
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    if pattern_count == 0:
        print("Keine Elliott-Wellen-Muster gefunden. Versuchen Sie, den Threshold-Parameter anzupassen.")
    
    # Aktuelle Wellenanalyse und Vorhersage
    current_wave = analyzer.find_current_wave()
    prediction = analyzer.predict_next_move()
    
    print("\nAktuelle Marktposition:")
    if current_wave:
        print(f"  Aktuelle Welle: {current_wave['type'].capitalize()}")
        points = current_wave['points']
        print(f"  Wellenpunkte: {len(points)}")
        
        if current_wave['next_target']:
            targets = current_wave['next_target']
            if isinstance(targets, tuple):
                # Stelle sicher, dass die Zielwerte native Python-Typen sind
                target1 = ensure_native_type(targets[0])
                target2 = ensure_native_type(targets[1])
                print(f"  Potenzielle Kursziele: {target1:.2f} - {target2:.2f}")
            else:
                target = ensure_native_type(targets)
                print(f"  Potenzielles Kursziel: {target:.2f}")
    else:
        print("  Keine klare Wellenstruktur im aktuellen Markt erkennbar.")
    
    print("\nMarktvorhersage:")
    print(f"  {prediction['prediction']} (Konfidenz: {prediction['confidence']:.2f})")
    
    if prediction['target'] and isinstance(prediction['target'], tuple):
        # Stelle sicher, dass die Zielwerte native Python-Typen sind
        target1 = ensure_native_type(prediction['target'][0])
        target2 = ensure_native_type(prediction['target'][1])
        print(f"  Kursziele: {target1:.2f} - {target2:.2f}")
    
    # Generiere Handelsempfehlungen
    current_price = ensure_native_type(data['Close'].iloc[-1])
    recommendations = get_trade_recommendations(current_wave, prediction, current_price, args.risk)
    
    print("\nHandelsempfehlung:")
    print(f"  {recommendations['empfehlung']}")
    print(f"  Grund: {recommendations['grund']}")
    
    if recommendations['ziele']:
        print("  Kursziele:")
        for i, ziel in enumerate(recommendations['ziele']):
            print(f"    Ziel {i+1}: {ziel['preis']:.2f} ({ziel['änderung']})")
    
    if recommendations['stop_loss']:
        print(f"  Stop-Loss: {recommendations['stop_loss']:.2f}")
    
    if recommendations['risk_reward']:
        for i, rr in enumerate(recommendations['risk_reward']):
            print(f"  Risk/Reward (Ziel {i+1}): {rr:.2f}")
    
    # Visualisierung
    print("\nErstelle Visualisierung...")
    from elliott_wave.utils import plot_waves
    fig, _ = plot_waves(data, waves, title=f"Elliott-Wellen-Analyse: {args.data}")
    
    # Speichere die Grafik, falls gewünscht
    if args.save:
        try:
            fig.savefig(args.save)
            print(f"Grafik wurde in {args.save} gespeichert.")
        except Exception as e:
            print(f"Fehler beim Speichern der Grafik: {str(e)}")
    
    plt.show()

def run_backtest(args):
    """
    Führt einen Backtest der Elliott-Wellen-Strategie durch.
    
    Args:
        args (argparse.Namespace): Kommandozeilenargumente
    """
    # Lade die Daten
    try:
        print(f"Lade Daten für {args.data}...")
        data = DataLoader.load_data(args.data, args.start, args.end)
        
        if data.empty:
            print(f"Fehler: Keine Daten für {args.data} gefunden.")
            sys.exit(1)
            
        print(f"Daten geladen: {len(data)} Datenpunkte von {data.index[0].strftime('%Y-%m-%d')} bis {data.index[-1].strftime('%Y-%m-%d')}")
    except Exception as e:
        print(f"Fehler beim Laden der Daten: {str(e)}")
        sys.exit(1)
    
    # Erstelle den Analyzer
    analyzer = ElliottWaveAnalyzer(data)
    
    # Führe den Backtest durch
    print(f"Führe Backtest mit Anfangsinvestition von {args.invest:.2f}€ durch...")
    backtest_results = analyzer.backtest(
        start_date=args.start, 
        end_date=args.end, 
        invest_amount=args.invest
    )
    
    # Zeige die Ergebnisse an
    print("\nBacktest-Ergebnisse:")
    print(f"  Anfangsinvestition: {backtest_results['initial_investment']:.2f}€")
    print(f"  Endwert: {backtest_results['final_equity']:.2f}€")
    print(f"  Gesamtrendite: {backtest_results['total_return']:.2f}%")
    print(f"  Max. Drawdown: {backtest_results['max_drawdown']:.2f}%")
    print(f"  Anzahl Trades: {backtest_results['num_trades']}")
    print(f"  Gewinnrate: {backtest_results['win_rate']:.2f}%")
    print(f"  Ø Trade-Rendite: {backtest_results['avg_trade_return']:.2f}%")
    
    # Detaillierte Trade-Informationen
    if backtest_results['trades']:
        print("\nTrade-Historie:")
        trade_data = []
        
        for trade in backtest_results['trades']:
            trade_data.append([
                trade['date'].strftime('%Y-%m-%d'),
                trade['action'].capitalize(),
                f"{trade['price']:.2f}€",
                f"{trade['shares']:.4f}",
                f"{trade['value']:.2f}€"
            ])
        
        headers = ["Datum", "Aktion", "Preis", "Anteile", "Wert"]
        print(tabulate(trade_data, headers=headers, tablefmt="grid"))
    
    # Visualisierung
    print("\nErstelle Backtest-Visualisierung...")
    fig = analyzer.plot_backtest_results(backtest_results)
    
    # Speichere die Grafik, falls gewünscht
    if args.save:
        try:
            fig.savefig(args.save)
            print(f"Grafik wurde in {args.save} gespeichert.")
        except Exception as e:
            print(f"Fehler beim Speichern der Grafik: {str(e)}")
    
    # Exportiere die Ergebnisse im gewünschten Format
    if args.output != 'table':
        # Bereite die Daten für den Export vor
        output_data = {
            'backtest_summary': {
                'initial_investment': backtest_results['initial_investment'],
                'final_equity': backtest_results['final_equity'],
                'total_return': backtest_results['total_return'],
                'max_drawdown': backtest_results['max_drawdown'],
                'num_trades': backtest_results['num_trades'],
                'win_rate': backtest_results['win_rate'],
                'avg_trade_return': backtest_results['avg_trade_return']
            },
            'trades': []
        }
        
        for trade in backtest_results['trades']:
            output_data['trades'].append({
                'date': trade['date'].strftime('%Y-%m-%d'),
                'action': trade['action'],
                'price': trade['price'],
                'shares': trade['shares'],
                'value': trade['value']
            })
        
        # Erstelle einen Dateinamen basierend auf dem Symbol und Datum
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        symbol = os.path.basename(args.data).split('.')[0]
        
        if args.output == 'csv':
            # Exportiere als CSV
            import csv
            
            # Exportiere die Zusammenfassung
            summary_file = f"backtest_{symbol}_summary_{timestamp}.csv"
            with open(summary_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Metrik', 'Wert'])
                for key, value in output_data['backtest_summary'].items():
                    writer.writerow([key, value])
            
            # Exportiere die Trades
            trades_file = f"backtest_{symbol}_trades_{timestamp}.csv"
            with open(trades_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'action', 'price', 'shares', 'value'])
                writer.writeheader()
                writer.writerows(output_data['trades'])
            
            print(f"Ergebnisse wurden exportiert als {summary_file} und {trades_file}")
            
        elif args.output == 'json':
            # Exportiere als JSON
            import json
            
            output_file = f"backtest_{symbol}_{timestamp}.json"
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"Ergebnisse wurden exportiert als {output_file}")
    
    plt.show()

def run_live_analysis(args):
    """
    Führt eine Live-Analyse mit aktuellen Marktdaten durch.
    
    Args:
        args (argparse.Namespace): Kommandozeilenargumente
    """
    symbol = args.data
    
    # Überprüfe, ob es sich um ein Tickersymbol handelt
    if os.path.isfile(symbol):
        print(f"Fehler: Der Live-Modus erfordert ein Tickersymbol, nicht einen Dateipfad.")
        sys.exit(1)
    
    try:
        # Hole Live-Daten
        print(f"Hole aktuelle Marktdaten für {symbol}...")
        live_data = DataLoader.get_live_data(symbol)
        
        # Zeige aktuelle Marktinformationen
        print("\nAktuelle Marktdaten:")
        print(f"  Symbol: {live_data['symbol']}")
        print(f"  Zeitstempel: {live_data['timestamp']}")
        print(f"  Aktueller Preis: {live_data['price']:.2f}")
        print(f"  Veränderung: {live_data['change']:.2f} ({live_data['change_percent']:.2f}%)")
        print(f"  Tageshoch: {live_data['day_high']:.2f}")
        print(f"  Tagestief: {live_data['day_low']:.2f}")
        print(f"  Eröffnungskurs: {live_data['open']:.2f}")
        print(f"  Vortagesschluss: {live_data['previous_close']:.2f}")
        print(f"  Volumen: {live_data['volume']:,}")
        if live_data['market_cap']:
            print(f"  Marktkapitalisierung: {live_data['market_cap']:,}")
        
        # Hole historische Daten für die Analyse
        print(f"\nLade historische Daten der letzten {args.days} Tage...")
        hist_data = DataLoader.get_recent_data(symbol, days=args.days)
        
        print(f"Daten geladen: {len(hist_data)} Datenpunkte von {hist_data.index[0].strftime('%Y-%m-%d')} bis {hist_data.index[-1].strftime('%Y-%m-%d')}")
        
        # Erstelle den Analyzer
        analyzer = ElliottWaveAnalyzer(hist_data)
        
        # Führe die Analyse durch
        print("Analysiere Elliott-Wellen-Muster...")
        waves = analyzer.analyze(zigzag_threshold=args.threshold, window_size=args.window)
        
        # Aktuelle Wellenanalyse und Vorhersage
        current_wave = analyzer.find_current_wave()
        prediction = analyzer.predict_next_move()
        
        print("\nAktuelle Marktposition:")
        if current_wave:
            print(f"  Aktuelle Welle: {current_wave['type'].capitalize()}")
            points = current_wave['points']
            print(f"  Wellenpunkte: {len(points)}")
            
            # Zeige die aktuellen Wellenpunkte an
            print("  Wellenpunkte Details:")
            for i, point in enumerate(points):
                idx, price = point
                # Konvertiere numpy.float64 zu float für die Formatierung
                date = hist_data.index[idx].strftime('%Y-%m-%d')
                price_float = ensure_native_type(price)
                print(f"    Punkt {i+1}: {date}, Preis: {price_float:.2f}")
            
            if current_wave['next_target']:
                targets = current_wave['next_target']
                if isinstance(targets, tuple):
                    # Stelle sicher, dass die Zielwerte native Python-Typen sind
                    target1 = ensure_native_type(targets[0])
                    target2 = ensure_native_type(targets[1])
                    print(f"  Potenzielle Kursziele: {target1:.2f} - {target2:.2f}")
                    
                    # Berechne die prozentuale Veränderung zum aktuellen Preis
                    current_price = live_data['price']
                    target_changes = [
                        (target - current_price) / current_price * 100
                        for target in [target1, target2]
                    ]
                    print(f"  Potenzielle Bewegung: {target_changes[0]:.2f}% bis {target_changes[1]:.2f}%")
                else:
                    target = ensure_native_type(targets)
                    print(f"  Potenzielles Kursziel: {target:.2f}")
                    target_change = (target - live_data['price']) / live_data['price'] * 100
                    print(f"  Potenzielle Bewegung: {target_change:.2f}%")
        else:
            print("  Keine klare Wellenstruktur im aktuellen Markt erkennbar.")
        
        print("\nMarktvorhersage:")
        print(f"  {prediction['prediction']} (Konfidenz: {prediction['confidence']:.2f})")
        
        if prediction['target'] and isinstance(prediction['target'], tuple):
            # Stelle sicher, dass die Zielwerte native Python-Typen sind
            target1 = ensure_native_type(prediction['target'][0])
            target2 = ensure_native_type(prediction['target'][1])
            print(f"  Kursziele: {target1:.2f} - {target2:.2f}")
        
        # Generiere Handelsempfehlungen
        current_price = live_data['price']
        recommendations = get_trade_recommendations(current_wave, prediction, current_price, args.risk)
        
        print("\nHandelsempfehlung:")
        print(f"  {recommendations['empfehlung']}")
        print(f"  Grund: {recommendations['grund']}")
        print(f"  Aktueller Preis: {current_price:.2f}")
        
        if recommendations['ziele']:
            print("  Kursziele:")
            for i, ziel in enumerate(recommendations['ziele']):
                print(f"    Ziel {i+1}: {ziel['preis']:.2f} ({ziel['änderung']})")
        
        if recommendations['stop_loss']:
            print(f"  Stop-Loss: {recommendations['stop_loss']:.2f}")
            stop_loss_percent = abs((recommendations['stop_loss'] - current_price) / current_price * 100)
            print(f"  Stop-Loss Abstand: {stop_loss_percent:.2f}%")
        
        if recommendations['risk_reward']:
            for i, rr in enumerate(recommendations['risk_reward']):
                print(f"  Risk/Reward (Ziel {i+1}): {rr:.2f}")
        
        # Visualisierung
        print("\nErstelle Visualisierung...")
        from elliott_wave.utils import plot_waves
        fig, ax = plot_waves(hist_data, waves, title=f"Elliott-Wellen-Analyse: {symbol} (Live)")
        
        # Markiere den aktuellen Preis
        ax.axhline(y=live_data['price'], color='red', linestyle='-', alpha=0.7)
        ax.annotate(f"Aktueller Preis: {live_data['price']:.2f}", 
                   (hist_data.index[-1], live_data['price']), 
                   xytext=(10, 0), 
                   textcoords='offset points',
                   color='red',
                   fontweight='bold')
        
        # Füge Handelsempfehlungen zur Visualisierung hinzu
        if recommendations['empfehlung'] != 'Neutral' and recommendations['stop_loss']:
            # Stop-Loss-Linie
            ax.axhline(y=recommendations['stop_loss'], color='orange', linestyle='--', alpha=0.7)
            ax.annotate(f"Stop-Loss: {recommendations['stop_loss']:.2f}", 
                       (hist_data.index[-1], recommendations['stop_loss']), 
                       xytext=(10, 0), 
                       textcoords='offset points',
                       color='orange')
            
            # Kursziele
            if recommendations['ziele']:
                for i, ziel in enumerate(recommendations['ziele']):
                    ax.axhline(y=ziel['preis'], color='green', linestyle='--', alpha=0.7)
                    ax.annotate(f"Ziel {i+1}: {ziel['preis']:.2f}", 
                               (hist_data.index[-1], ziel['preis']), 
                               xytext=(10, 0), 
                               textcoords='offset points',
                               color='green')
        
        # Speichere die Grafik, falls gewünscht
        if args.save:
            try:
                fig.savefig(args.save)
                print(f"Grafik wurde in {args.save} gespeichert.")
            except Exception as e:
                print(f"Fehler beim Speichern der Grafik: {str(e)}")
        
        plt.show()
        
    except Exception as e:
        print(f"Fehler bei der Live-Analyse: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """
    Hauptfunktion des Programms.
    """
    args = parse_args()
    
    print("=== Elliott Wave Analyzer ===")
    
    if args.mode == 'analyse':
        run_analysis(args)
    elif args.mode == 'backtest':
        run_backtest(args)
    elif args.mode == 'live':
        run_live_analysis(args)
    else:
        print(f"Unbekannter Modus: {args.mode}")
        sys.exit(1)

if __name__ == "__main__":
    main() 