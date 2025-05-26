#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .patterns import WavePattern
from .utils import find_local_extrema, calculate_fibonacci_levels, zigzag_filter

class ElliottWaveAnalyzer:
    """
    Hauptklasse zur Analyse von Marktdaten mit Elliott-Wellen-Theorie.
    """
    
    def __init__(self, data, price_col='Close'):
        """
        Initialisiert den Analyzer mit Marktdaten.
        
        Args:
            data (pandas.DataFrame): DataFrame mit OHLCV-Daten
            price_col (str): Name der Spalte mit den zu analysierenden Preisdaten
        """
        self.data = data
        self.price_col = price_col
        self.prices = data[price_col].values
        self.waves = {
            'impulse': [],
            'corrective': [],
            'motive': [],
            'diagonal': []
        }
        
    def analyze(self, zigzag_threshold=0.03, window_size=10):
        """
        Führt die Elliott-Wellen-Analyse durch.
        
        Args:
            zigzag_threshold (float): Mindestprozentsatz für eine Trendumkehrung im ZigZag-Filter
            window_size (int): Fenstergröße für die Extrema-Erkennung
            
        Returns:
            dict: Dictionary mit identifizierten Wellen
        """
        # Identifiziere die Wendepunkte mit dem ZigZag-Filter
        pivot_points = zigzag_filter(self.prices, threshold=zigzag_threshold)
        
        # Oder alternativ lokale Extrema finden
        if len(pivot_points) < 5:  # Wenn ZigZag nicht genug Punkte liefert
            maxima, minima = find_local_extrema(self.prices, window=window_size)
            pivot_points = sorted(list(maxima) + list(minima))
        
        # Identifiziere potenzielle Wellen
        self._identify_waves(pivot_points)
        
        return self.waves
    
    def _identify_waves(self, pivot_points):
        """
        Identifiziert potenzielle Elliott-Wellen anhand der Wendepunkte.
        
        Args:
            pivot_points (list): Liste mit Indizes der Wendepunkte
        """
        # Um Wellen zu identifizieren, betrachten wir alle möglichen Sequenzen von 6 Punkten (5 Wellen)
        for i in range(len(pivot_points) - 5):
            points = [(idx, self.prices[idx]) for idx in pivot_points[i:i+6]]
            
            # Versuche, eine Impulswelle zu identifizieren
            impulse_pattern = WavePattern("impulse", points)
            if impulse_pattern.is_valid:
                self.waves['impulse'].append({
                    'indices': pivot_points[i:i+6],
                    'pattern': impulse_pattern,
                    'wave_count': len(self.waves['impulse']) + 1
                })
            
            # Versuche, eine Korrekturwelle zu identifizieren
            if i <= len(pivot_points) - 4:  # Mindestens 4 Punkte für eine Korrekturwelle
                corr_points = [(idx, self.prices[idx]) for idx in pivot_points[i:i+4]]
                corrective_pattern = WavePattern("corrective", corr_points)
                if corrective_pattern.is_valid:
                    self.waves['corrective'].append({
                        'indices': pivot_points[i:i+4],
                        'pattern': corrective_pattern,
                        'wave_count': len(self.waves['corrective']) + 1
                    })
    
    def find_current_wave(self, look_back=30):
        """
        Versucht, die aktuelle Elliott-Welle im letzten Abschnitt der Daten zu identifizieren.
        
        Args:
            look_back (int): Anzahl der letzten Datenpunkte, die betrachtet werden sollen
            
        Returns:
            dict: Informationen zur aktuellen Welle oder None, wenn keine gefunden wurde
        """
        # Wir analysieren nur den letzten Teil der Daten
        last_n_prices = self.prices[-look_back:]
        
        # Identifiziere Wendepunkte im betrachteten Abschnitt
        pivot_points = zigzag_filter(last_n_prices, threshold=0.03)
        
        # Konvertiere relative Indizes zu absoluten Indizes
        abs_pivot_points = [len(self.prices) - look_back + idx for idx in pivot_points]
        
        # Wenn wir mindestens 3 Wendepunkte haben, versuchen wir ein Muster zu erkennen
        if len(abs_pivot_points) >= 3:
            points = [(idx, self.prices[idx]) for idx in abs_pivot_points]
            
            # Prüfe auf typische Wellenmuster
            
            # 1. Wenn wir 5 oder mehr Punkte haben, könnte es eine Impulswelle sein
            if len(points) >= 5:
                impulse_pattern = WavePattern("impulse", points)
                if impulse_pattern.is_valid:
                    return {
                        'type': 'impulse',
                        'points': points,
                        'next_target': impulse_pattern.get_next_target()
                    }
            
            # 2. Wenn wir 3 oder mehr Punkte haben, könnte es eine Korrekturwelle sein
            if len(points) >= 3:
                corrective_pattern = WavePattern("corrective", points)
                if corrective_pattern.is_valid:
                    return {
                        'type': 'corrective',
                        'points': points,
                        'next_target': corrective_pattern.get_next_target()
                    }
        
        return None
    
    def predict_next_move(self):
        """
        Versucht, die nächste Marktbewegung basierend auf der Elliott-Wellen-Analyse vorherzusagen.
        
        Returns:
            dict: Vorhersage für die nächste Bewegung
        """
        current_wave = self.find_current_wave()
        
        if current_wave is None:
            return {
                'prediction': 'unbestimmt',
                'confidence': 0.0,
                'target': None
            }
        
        wave_type = current_wave['type']
        target = current_wave['next_target']
        
        if wave_type == 'impulse':
            # Nach einer Impulswelle erwarten wir typischerweise eine Korrektur
            return {
                'prediction': 'Korrektur erwartet',
                'confidence': 0.7,
                'target': target
            }
        elif wave_type == 'corrective':
            # Nach einer Korrekturwelle erwarten wir typischerweise eine Fortsetzung des übergeordneten Trends
            return {
                'prediction': 'Trendfortsetzung erwartet',
                'confidence': 0.6,
                'target': target
            }
        
        return {
            'prediction': 'unbestimmt',
            'confidence': 0.0,
            'target': None
        }
    
    def backtest(self, start_date=None, end_date=None, invest_amount=10000):
        """
        Führt einen einfachen Backtest der Elliott-Wellen-Strategie durch.
        
        Args:
            start_date (str): Startdatum für den Backtest
            end_date (str): Enddatum für den Backtest
            invest_amount (float): Anfänglicher Investitionsbetrag
            
        Returns:
            dict: Ergebnisse des Backtests
        """
        # Filtere Daten für den Backtest-Zeitraum
        if start_date:
            start_idx = self.data.index.get_loc(pd.to_datetime(start_date), method='nearest')
        else:
            start_idx = 0
            
        if end_date:
            end_idx = self.data.index.get_loc(pd.to_datetime(end_date), method='nearest')
        else:
            end_idx = len(self.data) - 1
        
        backtest_data = self.data.iloc[start_idx:end_idx+1]
        
        # Initialisiere Backtest-Variablen
        cash = invest_amount
        shares = 0
        trades = []
        equity_curve = []
        
        # Führe den Backtest durch, indem wir die Daten Tag für Tag durchlaufen
        for i in range(60, len(backtest_data)):  # Starte nach 60 Tagen, um genug Daten für die Analyse zu haben
            # Erstelle einen temporären Analyzer für die Daten bis zum aktuellen Tag
            temp_analyzer = ElliottWaveAnalyzer(backtest_data.iloc[:i+1], self.price_col)
            prediction = temp_analyzer.predict_next_move()
            
            current_price = backtest_data.iloc[i][self.price_col]
            current_date = backtest_data.index[i]
            
            # Entscheidungslogik basierend auf der Vorhersage
            if prediction['prediction'] == 'Trendfortsetzung erwartet' and prediction['confidence'] > 0.5:
                # Kaufen, wenn wir noch keine Aktien haben
                if shares == 0 and cash > 0:
                    shares = cash / current_price
                    cash = 0
                    trades.append({
                        'date': current_date,
                        'action': 'buy',
                        'price': current_price,
                        'shares': shares,
                        'value': shares * current_price
                    })
            
            elif prediction['prediction'] == 'Korrektur erwartet' and prediction['confidence'] > 0.5:
                # Verkaufen, wenn wir Aktien haben
                if shares > 0:
                    cash = shares * current_price
                    trades.append({
                        'date': current_date,
                        'action': 'sell',
                        'price': current_price,
                        'shares': shares,
                        'value': cash
                    })
                    shares = 0
            
            # Aktualisiere die Equity-Kurve
            equity = cash + shares * current_price
            equity_curve.append({
                'date': current_date,
                'equity': equity
            })
        
        # Berechne Backtest-Metriken
        initial_equity = invest_amount
        final_equity = equity_curve[-1]['equity'] if equity_curve else invest_amount
        
        # Rendite berechnen
        total_return = (final_equity - initial_equity) / initial_equity * 100
        
        # Maximal Drawdown berechnen
        peak = invest_amount
        drawdowns = []
        
        for point in equity_curve:
            equity = point['equity']
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            drawdowns.append(drawdown)
        
        max_drawdown = max(drawdowns) if drawdowns else 0
        
        # Gewinn/Verlust pro Trade
        trade_returns = []
        for i in range(0, len(trades) - 1, 2):
            if i + 1 < len(trades) and trades[i]['action'] == 'buy' and trades[i+1]['action'] == 'sell':
                buy_value = trades[i]['value']
                sell_value = trades[i+1]['value']
                trade_return = (sell_value - buy_value) / buy_value * 100
                trade_returns.append(trade_return)
        
        avg_trade_return = sum(trade_returns) / len(trade_returns) if trade_returns else 0
        win_rate = sum(1 for r in trade_returns if r > 0) / len(trade_returns) if trade_returns else 0
        
        return {
            'initial_investment': invest_amount,
            'final_equity': final_equity,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'num_trades': len(trades) // 2,  # Jeder vollständige Trade ist ein Kauf + Verkauf
            'win_rate': win_rate * 100,  # In Prozent
            'avg_trade_return': avg_trade_return,
            'trades': trades,
            'equity_curve': equity_curve
        }
    
    def plot_backtest_results(self, backtest_results):
        """
        Plottet die Ergebnisse eines Backtests.
        
        Args:
            backtest_results (dict): Ergebnisse eines Backtests
            
        Returns:
            matplotlib.figure.Figure: Figure-Objekt des Plots
        """
        trades = backtest_results['trades']
        equity_curve = backtest_results['equity_curve']
        
        # Erstelle einen Plot mit zwei Subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]})
        
        # Plot 1: Preis und Trades
        ax1.plot(self.data.index, self.data[self.price_col], color='black', alpha=0.6, label='Preis')
        
        # Markiere Kauf- und Verkaufspunkte
        for trade in trades:
            if trade['action'] == 'buy':
                ax1.scatter(trade['date'], trade['price'], color='green', marker='^', s=100, label='Kauf')
                ax1.annotate(f"Kauf: {trade['price']:.2f}", 
                           (trade['date'], trade['price']), 
                           xytext=(5, 5), 
                           textcoords='offset points')
            else:  # 'sell'
                ax1.scatter(trade['date'], trade['price'], color='red', marker='v', s=100, label='Verkauf')
                ax1.annotate(f"Verkauf: {trade['price']:.2f}", 
                           (trade['date'], trade['price']), 
                           xytext=(5, -15), 
                           textcoords='offset points')
        
        # Entferne doppelte Legendeneinträge
        handles, labels = ax1.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax1.legend(by_label.values(), by_label.keys())
        
        ax1.set_title('Elliott-Wellen-Backtest: Preis und Trades')
        ax1.set_ylabel('Preis')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Equity-Kurve
        equity_dates = [point['date'] for point in equity_curve]
        equity_values = [point['equity'] for point in equity_curve]
        
        ax2.plot(equity_dates, equity_values, color='blue', label='Equity')
        ax2.set_title('Equity-Kurve')
        ax2.set_xlabel('Datum')
        ax2.set_ylabel('Equity (€)')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        # Füge Backtest-Metriken als Text hinzu
        metrics_text = (
            f"Anfangsinvestition: {backtest_results['initial_investment']:.2f}€\n"
            f"Endwert: {backtest_results['final_equity']:.2f}€\n"
            f"Gesamtrendite: {backtest_results['total_return']:.2f}%\n"
            f"Max. Drawdown: {backtest_results['max_drawdown']:.2f}%\n"
            f"Anzahl Trades: {backtest_results['num_trades']}\n"
            f"Gewinnrate: {backtest_results['win_rate']:.2f}%\n"
            f"Ø Trade-Rendite: {backtest_results['avg_trade_return']:.2f}%"
        )
        
        # Platziere den Text in der oberen rechten Ecke des ersten Plots
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.02, 0.98, metrics_text, transform=ax1.transAxes, fontsize=10,
                verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        return fig 