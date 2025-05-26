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
import threading
import time
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

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
    
    parser.add_argument('--mode', type=str, choices=['analyse', 'backtest', 'live', 'dashboard'], default='analyse',
                        help='Betriebsmodus: "analyse" für Elliott-Wellen-Analyse, "backtest" für Backtesting, "live" für Live-Analyse, "dashboard" für interaktives Dashboard')
    
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
    
    parser.add_argument('--refresh', type=int, default=60,
                        help='Aktualisierungsintervall in Sekunden für das Dashboard (Standard: 60)')
    
    return parser.parse_args()

def ensure_native_type(value):
    """
    Konvertiert NumPy-Datentypen in native Python-Datentypen.
    
    Args:
        value: Ein beliebiger Wert, der möglicherweise ein NumPy-Datentyp ist
        
    Returns:
        Der entsprechende native Python-Datentyp
    """
    if hasattr(value, 'item'):
        return value.item()
    return value

def get_trade_recommendations(current_wave, prediction, current_price, risk_tolerance=0.02):
    """
    Generiert Handelsempfehlungen basierend auf der aktuellen Wellenanalyse und Vorhersage.
    
    Args:
        current_wave (dict): Informationen zur aktuellen Welle
        prediction (dict): Marktvorhersage
        current_price (float): Aktueller Preis
        risk_tolerance (float): Risikotoleranz für Stop-Loss-Berechnung (Dezimalwert)
        
    Returns:
        dict: Handelsempfehlungen
    """
    recommendations = {
        'empfehlung': 'Neutral',
        'grund': 'Keine klare Handelsempfehlung möglich',
        'ziele': [],
        'stop_loss': None,
        'risk_reward': []
    }
    
    # Konfidenz der Vorhersage prüfen
    if prediction['confidence'] < 0.5:
        recommendations['grund'] = 'Niedrige Konfidenz in der aktuellen Vorhersage'
        return recommendations
    
    # Trend-Fortsetzung
    if prediction['prediction'] == 'Trendfortsetzung erwartet':
        # Bestimme die Handelsrichtung basierend auf dem aktuellen Trend
        if current_wave and current_wave['points']:
            # Prüfe die letzten beiden Punkte der aktuellen Welle
            points = current_wave['points']
            if len(points) >= 2:
                last_point = ensure_native_type(points[-1][1])
                second_last_point = ensure_native_type(points[-2][1])
                
                # Aufwärtstrend
                if last_point > second_last_point:
                    recommendations['empfehlung'] = 'Kaufen'
                    recommendations['grund'] = 'Aufwärtstrend wird voraussichtlich fortgesetzt'
                    
                    # Stop-Loss berechnen - direkter Ansatz mit Risikotoleranz
                    # Entweder den niedrigsten Punkt der letzten Welle oder prozentual zum aktuellen Kurs, was näher ist
                    wave_low = min([ensure_native_type(p[1]) for p in points[-3:]]) if len(points) >= 3 else current_price * (1 - risk_tolerance * 1.5)
                    percent_stop = current_price * (1 - risk_tolerance)
                    
                    # Wähle den höheren der beiden Werte, um nicht zu weit vom aktuellen Kurs entfernt zu sein
                    recommendations['stop_loss'] = max(wave_low, percent_stop)
                    
                    # Kursziele basierend auf Fibonacci-Projektionen
                    if prediction['target'] and isinstance(prediction['target'], tuple):
                        target1 = ensure_native_type(prediction['target'][0])
                        target2 = ensure_native_type(prediction['target'][1])
                        
                        # Für Long-Positionen sollten die Ziele höher sein
                        recommendations['ziele'] = [
                            {'preis': target1, 'änderung': f"+{((target1 / current_price) - 1) * 100:.2f}%"},
                            {'preis': target2, 'änderung': f"+{((target2 / current_price) - 1) * 100:.2f}%"}
                        ]
                        
                        # Risk/Reward berechnen
                        risk = (current_price - recommendations['stop_loss']) / current_price
                        reward1 = (target1 - current_price) / current_price
                        reward2 = (target2 - current_price) / current_price
                        
                        if risk > 0:
                            recommendations['risk_reward'] = [reward1 / risk, reward2 / risk]
                
                # Abwärtstrend
                elif last_point < second_last_point:
                    recommendations['empfehlung'] = 'Verkaufen'
                    recommendations['grund'] = 'Abwärtstrend wird voraussichtlich fortgesetzt'
                    
                    # Stop-Loss berechnen - direkter Ansatz mit Risikotoleranz
                    # Entweder den höchsten Punkt der letzten Welle oder prozentual zum aktuellen Kurs, was näher ist
                    wave_high = max([ensure_native_type(p[1]) for p in points[-3:]]) if len(points) >= 3 else current_price * (1 + risk_tolerance * 1.5)
                    percent_stop = current_price * (1 + risk_tolerance)
                    
                    # Wähle den niedrigeren der beiden Werte, um nicht zu weit vom aktuellen Kurs entfernt zu sein
                    recommendations['stop_loss'] = min(wave_high, percent_stop)
                    
                    # Kursziele basierend auf Fibonacci-Projektionen
                    if prediction['target'] and isinstance(prediction['target'], tuple):
                        target1 = ensure_native_type(prediction['target'][0])
                        target2 = ensure_native_type(prediction['target'][1])
                        
                        # Für Short-Positionen sollten die Ziele niedriger sein und die Änderung negativ
                        # Stelle sicher, dass die Ziele in absteigender Reihenfolge sind (näher zuerst)
                        if target1 > target2:
                            target1, target2 = target2, target1
                            
                        recommendations['ziele'] = [
                            {'preis': target1, 'änderung': f"-{((1 - (target1 / current_price)) * 100):.2f}%"},
                            {'preis': target2, 'änderung': f"-{((1 - (target2 / current_price)) * 100):.2f}%"}
                        ]
                        
                        # Risk/Reward berechnen für Short-Position
                        risk = (recommendations['stop_loss'] - current_price) / current_price
                        reward1 = (current_price - target1) / current_price
                        reward2 = (current_price - target2) / current_price
                        
                        if risk > 0:
                            recommendations['risk_reward'] = [reward1 / risk, reward2 / risk]
    
    # Korrektur erwartet
    elif prediction['prediction'] == 'Korrektur erwartet':
        if current_wave and current_wave['points']:
            # Prüfe die letzten beiden Punkte der aktuellen Welle
            points = current_wave['points']
            if len(points) >= 2:
                last_point = ensure_native_type(points[-1][1])
                second_last_point = ensure_native_type(points[-2][1])
                
                # Aktueller Aufwärtstrend könnte korrigieren
                if last_point > second_last_point:
                    recommendations['empfehlung'] = 'Gewinne mitnehmen'
                    recommendations['grund'] = 'Korrektur des Aufwärtstrends erwartet'
                    
                    # Einfachen Stop-Loss für bestehende Long-Positionen setzen
                    recommendations['stop_loss'] = current_price * (1 - risk_tolerance / 2)
                    
                    # Potenzielle Korrekturziele basierend auf Fibonacci-Retracements
                    if prediction['target'] and isinstance(prediction['target'], tuple):
                        target1 = ensure_native_type(prediction['target'][0])
                        target2 = ensure_native_type(prediction['target'][1])
                        
                        # Für Korrekturen in einem Aufwärtstrend sind die Ziele niedriger
                        if target1 > target2:
                            target1, target2 = target2, target1
                            
                        recommendations['ziele'] = [
                            {'preis': target1, 'änderung': f"-{((1 - (target1 / current_price)) * 100):.2f}%"},
                            {'preis': target2, 'änderung': f"-{((1 - (target2 / current_price)) * 100):.2f}%"}
                        ]
                
                # Aktueller Abwärtstrend könnte korrigieren
                elif last_point < second_last_point:
                    recommendations['empfehlung'] = 'Warten oder Short-Position schließen'
                    recommendations['grund'] = 'Korrektur des Abwärtstrends erwartet'
                    
                    # Einfachen Stop-Loss für bestehende Short-Positionen setzen
                    recommendations['stop_loss'] = current_price * (1 + risk_tolerance / 2)
                    
                    # Potenzielle Korrekturziele basierend auf Fibonacci-Retracements
                    if prediction['target'] and isinstance(prediction['target'], tuple):
                        target1 = ensure_native_type(prediction['target'][0])
                        target2 = ensure_native_type(prediction['target'][1])
                        
                        # Für Korrekturen in einem Abwärtstrend sind die Ziele höher
                        if target1 < target2:
                            target1, target2 = target2, target1
                            
                        recommendations['ziele'] = [
                            {'preis': target1, 'änderung': f"+{((target1 / current_price) - 1) * 100:.2f}%"},
                            {'preis': target2, 'änderung': f"+{((target2 / current_price) - 1) * 100:.2f}%"}
                        ]
    
    # Welle könnte abgeschlossen sein
    elif prediction['prediction'] == 'Welle könnte abgeschlossen sein':
        recommendations['empfehlung'] = 'Vorsichtig sein'
        recommendations['grund'] = 'Möglicher Trendwechsel, warten auf Bestätigung'
        
        # Stop-Loss näher setzen, da Unsicherheit besteht
        if current_wave and current_wave['points']:
            points = current_wave['points']
            if len(points) >= 2:
                last_point = ensure_native_type(points[-1][1])
                second_last_point = ensure_native_type(points[-2][1])
                
                # Im Aufwärtstrend
                if last_point > second_last_point:
                    # Engerer Stop-Loss basierend auf Risikotoleranz
                    recommendations['stop_loss'] = current_price * (1 - risk_tolerance / 2)
                # Im Abwärtstrend
                else:
                    # Engerer Stop-Loss basierend auf Risikotoleranz
                    recommendations['stop_loss'] = current_price * (1 + risk_tolerance / 2)
    
    return recommendations

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
            # Bestimme, ob es sich um eine Long- oder Short-Position handelt
            is_long = recommendations['empfehlung'] in ['Kaufen', 'Gewinne mitnehmen']
            is_short = recommendations['empfehlung'] in ['Verkaufen', 'Warten oder Short-Position schließen']
            
            # Stop-Loss-Linie
            stop_loss_value = recommendations['stop_loss']
            
            # Richtiger Text und Farbe für Stop-Loss abhängig von Position
            if is_long:
                stop_loss_label = f"Stop-Loss (Long): {stop_loss_value:.2f}"
                stop_loss_color = 'green'
            elif is_short:
                stop_loss_label = f"Stop-Loss (Short): {stop_loss_value:.2f}"
                stop_loss_color = 'red'
            else:
                stop_loss_label = f"Stop-Loss: {stop_loss_value:.2f}"
                stop_loss_color = 'orange'
            
            ax.axhline(y=stop_loss_value, color=stop_loss_color, linestyle='--', alpha=0.7)
            ax.annotate(stop_loss_label, 
                       (hist_data.index[-1], stop_loss_value), 
                       xytext=(10, 0), 
                       textcoords='offset points',
                       color=stop_loss_color,
                       fontweight='bold')
            
            # Kursziele
            if recommendations['ziele']:
                for i, ziel in enumerate(recommendations['ziele']):
                    ziel_preis = ziel['preis']
                    
                    # Bestimme die Farbe basierend auf der Handelsrichtung und der Position des Ziels
                    if is_long:
                        # Bei Long-Positionen sind Ziele über dem aktuellen Kurs positiv (grün)
                        ziel_color = 'green' if ziel_preis > current_price else 'purple'
                    elif is_short:
                        # Bei Short-Positionen sind Ziele unter dem aktuellen Kurs positiv (grün)
                        ziel_color = 'green' if ziel_preis < current_price else 'purple'
                    else:
                        ziel_color = 'blue'
                    
                    ax.axhline(y=ziel_preis, color=ziel_color, linestyle='--', alpha=0.7)
                    ax.annotate(f"Ziel {i+1}: {ziel_preis:.2f} ({ziel['änderung']})", 
                               (hist_data.index[-1], ziel_preis), 
                               xytext=(10, 0), 
                               textcoords='offset points',
                               color=ziel_color)
        
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

def run_dashboard(args):
    """
    Startet ein interaktives Dashboard mit Live-Daten und einstellbarem Timeframe.
    
    Args:
        args (argparse.Namespace): Kommandozeilenargumente
    """
    symbol = args.data
    
    # Überprüfe, ob es sich um ein Tickersymbol handelt
    if os.path.isfile(symbol):
        print(f"Fehler: Der Dashboard-Modus erfordert ein Tickersymbol, nicht einen Dateipfad.")
        sys.exit(1)
    
    # Erstelle das Hauptfenster
    root = tk.Tk()
    root.title(f"Elliott Wave Analyzer - {symbol}")
    root.geometry("1400x800")
    
    # Definiere Farbschema (Bloomberg Terminal-ähnlich)
    colors = {
        'bg': '#000000',           # Hintergrund schwarz
        'fg': '#FFFFFF',           # Text weiß
        'accent': '#404040',       # Akzentfarbe grau
        'highlight': '#606060',    # Highlight grau
        'up': '#00FF00',           # Grün für Aufwärtsbewegung
        'down': '#FF0000',         # Rot für Abwärtsbewegung
        'neutral': '#FFFF00'       # Gelb für neutrale Signale
    }
    
    # Konfiguriere das Farbschema für das Hauptfenster
    root.configure(bg=colors['bg'])
    style = ttk.Style()
    style.theme_use('clam')  # Nutze ein einfaches Theme als Basis
    
    # Konfiguriere Styles für verschiedene Widgets
    style.configure('TFrame', background=colors['bg'])
    style.configure('TLabel', background=colors['bg'], foreground=colors['fg'])
    style.configure('TButton', background=colors['accent'], foreground=colors['fg'])
    style.configure('Header.TLabel', background=colors['bg'], foreground=colors['fg'], font=('Arial', 12, 'bold'))
    style.configure('Title.TLabel', background=colors['bg'], foreground=colors['fg'], font=('Arial', 14, 'bold'))
    
    # Konfiguriere Treeview für Marktdaten
    style.configure('Treeview', 
                    background=colors['bg'], 
                    foreground=colors['fg'],
                    fieldbackground=colors['bg'])
    style.map('Treeview', 
             background=[('selected', colors['accent'])])
    
    style.configure('TCombobox', 
                    fieldbackground=colors['bg'],
                    background=colors['accent'],
                    foreground=colors['fg'])
    
    # Status-Variablen
    current_days = tk.IntVar(value=args.days)
    refresh_interval = tk.IntVar(value=args.refresh)
    threshold = tk.DoubleVar(value=args.threshold)
    risk = tk.DoubleVar(value=args.risk)
    status_message = tk.StringVar(value="Bereit")
    
    # Setze die passende Börse basierend auf dem Symbol
    is_us_symbol = DataLoader.is_us_symbol(symbol)
    exchange = tk.StringVar(value="US" if is_us_symbol else "XETR")
    
    # Hauptlayout-Container
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Header-Bereich mit Titel und Steuerungen
    header_frame = ttk.Frame(main_frame)
    header_frame.pack(fill=tk.X, pady=5)
    
    # Titel und Symbol-Info
    title_frame = ttk.Frame(header_frame)
    title_frame.pack(side=tk.LEFT, padx=10)
    
    ttk.Label(title_frame, text=f"ELLIOTT WAVE ANALYZER - {symbol}", style='Title.TLabel').pack(side=tk.LEFT)
    
    # Steuerelemente
    controls_frame = ttk.Frame(header_frame)
    controls_frame.pack(side=tk.RIGHT, fill=tk.X, padx=10)
    
    # Erste Zeile von Steuerelementen
    row1 = ttk.Frame(controls_frame)
    row1.pack(fill=tk.X, pady=2)
    
    ttk.Label(row1, text="Timeframe:").pack(side=tk.LEFT, padx=2)
    timeframe_combo = ttk.Combobox(row1, textvariable=current_days, values=[30, 60, 90, 180, 365], width=5)
    timeframe_combo.pack(side=tk.LEFT, padx=2)
    
    ttk.Label(row1, text="Refresh:").pack(side=tk.LEFT, padx=2)
    refresh_combo = ttk.Combobox(row1, textvariable=refresh_interval, values=[30, 60, 120, 300, 600], width=5)
    refresh_combo.pack(side=tk.LEFT, padx=2)
    
    if not is_us_symbol:
        ttk.Label(row1, text="Börse:").pack(side=tk.LEFT, padx=2)
        exchange_combo = ttk.Combobox(row1, textvariable=exchange, values=list(DataLoader.GERMAN_EXCHANGES.keys()), width=5)
        exchange_combo.pack(side=tk.LEFT, padx=2)
    
    # Zweite Zeile von Steuerelementen
    row2 = ttk.Frame(controls_frame)
    row2.pack(fill=tk.X, pady=2)
    
    ttk.Label(row2, text="ZigZag:").pack(side=tk.LEFT, padx=2)
    threshold_combo = ttk.Combobox(row2, textvariable=threshold, values=[0.01, 0.02, 0.03, 0.05, 0.1], width=5)
    threshold_combo.pack(side=tk.LEFT, padx=2)
    
    ttk.Label(row2, text="Risiko:").pack(side=tk.LEFT, padx=2)
    risk_combo = ttk.Combobox(row2, textvariable=risk, values=[0.01, 0.02, 0.03, 0.05], width=5)
    risk_combo.pack(side=tk.LEFT, padx=2)
    
    update_button = ttk.Button(row2, text="Update")
    update_button.pack(side=tk.LEFT, padx=5)
    
    # Separator zwischen Header und Content
    separator = ttk.Separator(main_frame, orient='horizontal')
    separator.pack(fill=tk.X, pady=5)
    
    # Content-Bereich mit zwei Spalten
    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill=tk.BOTH, expand=True)
    
    # Linke Spalte: Textbasierte Analyse
    left_frame = ttk.Frame(content_frame)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    
    # Marktdaten-Bereich
    market_frame = ttk.LabelFrame(left_frame, text="MARKTDATEN")
    market_frame.pack(fill=tk.X, pady=5)
    
    market_data = ttk.Treeview(market_frame, columns=("value"), show="tree", height=10)
    market_data.heading("#0", text="Metrik")
    market_data.heading("value", text="Wert")
    market_data.column("#0", width=150)
    market_data.column("value", width=150)
    market_data.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Wellenanalyse-Bereich
    wave_frame = ttk.LabelFrame(left_frame, text="WELLENANALYSE")
    wave_frame.pack(fill=tk.X, pady=5)
    
    wave_info = tk.Text(wave_frame, height=5, bg=colors['bg'], fg=colors['fg'], wrap=tk.WORD)
    wave_info.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Handelsempfehlungen-Bereich
    rec_frame = ttk.LabelFrame(left_frame, text="HANDELSEMPFEHLUNGEN")
    rec_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    
    rec_text = tk.Text(rec_frame, bg=colors['bg'], fg=colors['fg'], wrap=tk.WORD)
    rec_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Rechte Spalte: Chart
    right_frame = ttk.Frame(content_frame)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
    
    # Chart-Bereich
    chart_frame = ttk.LabelFrame(right_frame, text="CHART")
    chart_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    
    # Figure für Matplotlib erstellen mit dunklem Hintergrund
    plt.style.use('dark_background')
    fig = Figure(figsize=(8, 8), dpi=100, facecolor=colors['bg'])
    ax = fig.add_subplot(111)
    ax.set_facecolor(colors['bg'])
    
    # Canvas für die Figur erstellen
    canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Matplotlib-Toolbar für Zoom und Navigation hinzufügen
    toolbar_frame = ttk.Frame(chart_frame)
    toolbar_frame.pack(fill=tk.X)
    toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
    toolbar.update()
    
    # Statusleiste
    status_bar = ttk.Label(root, textvariable=status_message, relief=tk.SUNKEN, anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Daten-Cache und Thread-Steuerung
    data_cache = {
        'live_data': None,
        'hist_data': None,
        'waves': None,
        'current_wave': None,
        'prediction': None,
        'recommendations': None
    }
    
    stop_thread = threading.Event()
    update_thread = None
    
    def update_data():
        """Aktualisiert die Daten und die Anzeige"""
        try:
            status_message.set("Aktualisiere Daten...")
            
            # Hole Live-Daten
            # Für US-Symbole verwende kein Exchange-Parameter
            if is_us_symbol:
                data_cache['live_data'] = DataLoader.get_live_data(symbol)
            else:
                data_cache['live_data'] = DataLoader.get_live_data(symbol, exchange=exchange.get())
            
            # Hole historische Daten für die Analyse
            days = current_days.get()
            if is_us_symbol:
                data_cache['hist_data'] = DataLoader.get_recent_data(symbol, days=days)
            else:
                data_cache['hist_data'] = DataLoader.get_recent_data(symbol, days=days, exchange=exchange.get())
            
            # Erstelle den Analyzer
            analyzer = ElliottWaveAnalyzer(data_cache['hist_data'])
            
            # Führe die Analyse durch
            data_cache['waves'] = analyzer.analyze(
                zigzag_threshold=threshold.get(), 
                window_size=args.window
            )
            
            # Aktuelle Wellenanalyse und Vorhersage
            data_cache['current_wave'] = analyzer.find_current_wave()
            data_cache['prediction'] = analyzer.predict_next_move()
            
            # Generiere Handelsempfehlungen
            current_price = data_cache['live_data']['price']
            data_cache['recommendations'] = get_trade_recommendations(
                data_cache['current_wave'], 
                data_cache['prediction'], 
                current_price, 
                risk.get()
            )
            
            # Aktualisiere die Anzeige
            update_display()
            
            status_message.set(f"Aktualisiert: {datetime.now().strftime('%H:%M:%S')} | Nächstes Update in {refresh_interval.get()} Sek.")
        except Exception as e:
            status_message.set(f"Fehler bei der Aktualisierung: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def update_display():
        """Aktualisiert die Anzeige mit den neuesten Daten"""
        if data_cache['live_data'] is None or data_cache['hist_data'] is None or data_cache['hist_data'].empty:
            return
            
        # Aktualisiere Marktdaten-Anzeige
        market_data.delete(*market_data.get_children())
        
        live_data = data_cache['live_data']
        market_data.insert("", "end", text="Symbol", values=(live_data['symbol'],))
        market_data.insert("", "end", text="Börse", values=("US" if is_us_symbol else exchange.get(),))
        market_data.insert("", "end", text="Zeitstempel", values=(live_data['timestamp'],))
        market_data.insert("", "end", text="Aktueller Preis", values=(f"{live_data['price']:.2f}",))
        
        # Farbige Darstellung der Veränderung
        change_value = f"{live_data['change']:.2f} ({live_data['change_percent']:.2f}%)"
        change_item = market_data.insert("", "end", text="Veränderung", values=(change_value,))
        if live_data['change'] > 0:
            market_data.item(change_item, tags=('positive',))
        elif live_data['change'] < 0:
            market_data.item(change_item, tags=('negative',))
        market_data.tag_configure('positive', foreground=colors['up'])
        market_data.tag_configure('negative', foreground=colors['down'])
        
        market_data.insert("", "end", text="Tageshoch", values=(f"{live_data['day_high']:.2f}",))
        market_data.insert("", "end", text="Tagestief", values=(f"{live_data['day_low']:.2f}",))
        market_data.insert("", "end", text="Eröffnungskurs", values=(f"{live_data['open']:.2f}",))
        market_data.insert("", "end", text="Vortagesschluss", values=(f"{live_data['previous_close']:.2f}",))
        market_data.insert("", "end", text="Volumen", values=(f"{live_data['volume']:,}",))
        
        # Aktualisiere Welleninfo
        wave_info.delete(1.0, tk.END)
        current_wave = data_cache['current_wave']
        prediction = data_cache['prediction']
        
        wave_lines = []
        
        # Aktuelle Welle
        if current_wave:
            wave_lines.append(f"Aktuelle Welle: {current_wave['type'].capitalize()}")
            wave_lines.append(f"Wellenpunkte: {len(current_wave['points'])}")
            
            if current_wave['next_target']:
                targets = current_wave['next_target']
                if isinstance(targets, tuple):
                    target1 = ensure_native_type(targets[0])
                    target2 = ensure_native_type(targets[1])
                    wave_lines.append(f"Potenzielle Kursziele: {target1:.2f} - {target2:.2f}")
                else:
                    target = ensure_native_type(targets)
                    wave_lines.append(f"Potenzielles Kursziel: {target:.2f}")
        else:
            wave_lines.append("Keine klare Wellenstruktur erkennbar.")
        
        # Marktvorhersage
        wave_lines.append(f"\nMarktvorhersage: {prediction['prediction']} (Konfidenz: {prediction['confidence']:.2f})")
        
        wave_info.insert(tk.END, "\n".join(wave_lines))
        
        # Aktualisiere Empfehlungstext
        rec_text.delete(1.0, tk.END)
        recommendations = data_cache['recommendations']
        
        rec_lines = []
        
        # Handelsempfehlung
        rec_lines.append(f"Empfehlung: {recommendations['empfehlung']}")
        rec_lines.append(f"Grund: {recommendations['grund']}")
        
        # Füge Tags für farbige Darstellung hinzu
        rec_text.insert(tk.END, "Empfehlung: ")
        if recommendations['empfehlung'] in ['Kaufen', 'Gewinne mitnehmen']:
            rec_text.insert(tk.END, recommendations['empfehlung'] + "\n", 'green')
        elif recommendations['empfehlung'] in ['Verkaufen', 'Warten oder Short-Position schließen']:
            rec_text.insert(tk.END, recommendations['empfehlung'] + "\n", 'red')
        else:
            rec_text.insert(tk.END, recommendations['empfehlung'] + "\n", 'yellow')
        
        rec_text.insert(tk.END, f"Grund: {recommendations['grund']}\n")
        
        if recommendations['ziele']:
            rec_text.insert(tk.END, "Kursziele:\n")
            for i, ziel in enumerate(recommendations['ziele']):
                rec_text.insert(tk.END, f"  Ziel {i+1}: {ziel['preis']:.2f} ({ziel['änderung']})\n")
        
        if recommendations['stop_loss']:
            current_price = live_data['price']
            stop_loss_percent = abs((recommendations['stop_loss'] - current_price) / current_price * 100)
            rec_text.insert(tk.END, f"Stop-Loss: {recommendations['stop_loss']:.2f} (Abstand: {stop_loss_percent:.2f}%)\n")
        
        if recommendations['risk_reward']:
            rec_text.insert(tk.END, "Risk/Reward:\n")
            for i, rr in enumerate(recommendations['risk_reward']):
                rec_text.insert(tk.END, f"  Ziel {i+1}: {rr:.2f}\n")
        
        # Konfiguriere farbige Tags für den Text
        rec_text.tag_configure('green', foreground=colors['up'])
        rec_text.tag_configure('red', foreground=colors['down'])
        rec_text.tag_configure('yellow', foreground=colors['neutral'])
        
        # Aktualisiere Chart
        ax.clear()
        
        # Preisdaten plotten
        ax.plot(data_cache['hist_data'].index, data_cache['hist_data']['Close'], color='white', alpha=0.8, label='Preis')
        
        # Farbcodes für verschiedene Wellentypen
        wave_colors = {
            'impulse': '#00BFFF',   # Deep Sky Blue
            'corrective': '#FF6347', # Tomato
            'motive': '#32CD32',     # Lime Green
            'diagonal': '#BA55D3'    # Medium Orchid
        }
        
        # Wellen plotten
        for wave_type, wave_list in data_cache['waves'].items():
            if wave_type in wave_colors and wave_list:
                for wave in wave_list:
                    indices = wave['indices']
                    if not indices or len(indices) < 2:
                        continue
                    
                    # Extrahiere die Preispunkte an den Wellenindizes
                    x_points = [data_cache['hist_data'].index[i] for i in indices if i < len(data_cache['hist_data'])]
                    y_points = [data_cache['hist_data']['Close'].iloc[i] for i in indices if i < len(data_cache['hist_data'])]
                    
                    # Plotte die Wellenpunkte und verbinde sie
                    ax.plot(x_points, y_points, 'o-', color=wave_colors[wave_type], alpha=0.7, 
                            label=f"{wave_type.capitalize()} Wave {wave['wave_count']}")
                    
                    # Beschrifte die Wellenpunkte
                    for i, (x, y) in enumerate(zip(x_points, y_points)):
                        ax.annotate(f"{i+1}", (x, y), xytext=(5, 5), textcoords='offset points', color='white')
        
        # Aktuellen Preis markieren
        ax.axhline(y=live_data['price'], color='white', linestyle='-', alpha=0.7)
        ax.annotate(f"Aktueller Preis: {live_data['price']:.2f}", 
                   (data_cache['hist_data'].index[-1], live_data['price']), 
                   xytext=(10, 0), 
                   textcoords='offset points',
                   color='white',
                   fontweight='bold')
        
        # Formatierung des Plots
        market_text = "US-MARKT" if is_us_symbol else f"{exchange.get()}"
        ax.set_title(f"{symbol} ({market_text}) - {current_days.get()} TAGE", color='white')
        ax.set_xlabel('DATUM', color='white')
        ax.set_ylabel('PREIS', color='white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.grid(True, alpha=0.3, color='gray')
        
        # Füge Handelsempfehlungen zur Visualisierung hinzu
        if recommendations['empfehlung'] != 'Neutral' and recommendations['stop_loss']:
            # Bestimme, ob es sich um eine Long- oder Short-Position handelt
            is_long = recommendations['empfehlung'] in ['Kaufen', 'Gewinne mitnehmen']
            is_short = recommendations['empfehlung'] in ['Verkaufen', 'Warten oder Short-Position schließen']
            current_price = live_data['price']
            
            # Stop-Loss-Linie
            stop_loss_value = recommendations['stop_loss']
            
            # Richtiger Text und Farbe für Stop-Loss abhängig von Position
            if is_long:
                stop_loss_label = f"SL(L): {stop_loss_value:.2f}"
                stop_loss_color = colors['up']
            elif is_short:
                stop_loss_label = f"SL(S): {stop_loss_value:.2f}"
                stop_loss_color = colors['down']
            else:
                stop_loss_label = f"SL: {stop_loss_value:.2f}"
                stop_loss_color = colors['neutral']
            
            ax.axhline(y=stop_loss_value, color=stop_loss_color, linestyle='--', alpha=0.7)
            ax.annotate(stop_loss_label, 
                       (data_cache['hist_data'].index[-1], stop_loss_value), 
                       xytext=(10, 0), 
                       textcoords='offset points',
                       color=stop_loss_color,
                       fontweight='bold')
            
            # Kursziele
            if recommendations['ziele']:
                for i, ziel in enumerate(recommendations['ziele']):
                    ziel_preis = ziel['preis']
                    
                    # Bestimme die Farbe basierend auf der Handelsrichtung und der Position des Ziels
                    if is_long:
                        # Bei Long-Positionen sind Ziele über dem aktuellen Kurs positiv (grün)
                        ziel_color = colors['up'] if ziel_preis > current_price else '#FF00FF'  # Magenta
                    elif is_short:
                        # Bei Short-Positionen sind Ziele unter dem aktuellen Kurs positiv (grün)
                        ziel_color = colors['up'] if ziel_preis < current_price else '#FF00FF'  # Magenta
                    else:
                        ziel_color = '#00FFFF'  # Cyan
                    
                    ax.axhline(y=ziel_preis, color=ziel_color, linestyle='--', alpha=0.7)
                    ax.annotate(f"Z{i+1}: {ziel_preis:.2f}", 
                               (data_cache['hist_data'].index[-1], ziel_preis), 
                               xytext=(10, 0), 
                               textcoords='offset points',
                               color=ziel_color)
        
        ax.legend(loc='upper left')
        fig.tight_layout()
        canvas.draw()
        
        # Aktualisiere die Toolbar
        toolbar.update()
    
    def periodic_update():
        """Periodische Aktualisierung der Daten"""
        while not stop_thread.is_set():
            update_data()
            
            # Warte für das angegebene Intervall oder bis stop_thread gesetzt wird
            for _ in range(refresh_interval.get()):
                if stop_thread.is_set():
                    break
                time.sleep(1)
    
    def on_update_button():
        """Manuelles Update bei Knopfdruck"""
        update_data()
    
    def on_closing():
        """Wird beim Schließen des Fensters aufgerufen"""
        stop_thread.set()
        if update_thread:
            update_thread.join()
        root.destroy()
    
    def on_timeframe_changed(event):
        """Wird aufgerufen, wenn der Timeframe geändert wird"""
        update_data()
    
    def on_refresh_changed(event):
        """Wird aufgerufen, wenn das Aktualisierungsintervall geändert wird"""
        status_message.set(f"Aktualisierungsintervall geändert auf {refresh_interval.get()} Sekunden")
    
    def on_exchange_changed(event):
        """Wird aufgerufen, wenn die Börse geändert wird"""
        update_data()
    
    # Verknüpfe Event-Handler
    update_button.config(command=on_update_button)
    timeframe_combo.bind("<<ComboboxSelected>>", on_timeframe_changed)
    refresh_combo.bind("<<ComboboxSelected>>", on_refresh_changed)
    if not is_us_symbol:
        exchange_combo.bind("<<ComboboxSelected>>", on_exchange_changed)
    threshold_combo.bind("<<ComboboxSelected>>", lambda e: update_data())
    risk_combo.bind("<<ComboboxSelected>>", lambda e: update_data())
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Initialer Daten-Load und Start des Update-Threads
    update_data()
    
    update_thread = threading.Thread(target=periodic_update)
    update_thread.daemon = True
    update_thread.start()
    
    # Starte das GUI
    root.mainloop()

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
    elif args.mode == 'dashboard':
        run_dashboard(args)
    else:
        print(f"Unbekannter Modus: {args.mode}")
        sys.exit(1)

if __name__ == "__main__":
    main() 