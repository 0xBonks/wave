#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from scipy.signal import find_peaks, argrelextrema
import matplotlib.pyplot as plt

def find_local_extrema(prices, window=5):
    """
    Findet lokale Maxima und Minima in einer Preisreihe.
    
    Args:
        prices (array-like): Array mit Preisdaten
        window (int): Fenstergröße für die Extrema-Erkennung
        
    Returns:
        tuple: (maxima_indices, minima_indices) Arrays mit Indizes der Extrema
    """
    prices = np.array(prices)
    # Lokale Maxima finden
    maxima_indices = argrelextrema(prices, np.greater, order=window)[0]
    # Lokale Minima finden
    minima_indices = argrelextrema(prices, np.less, order=window)[0]
    
    return maxima_indices, minima_indices

def calculate_fibonacci_levels(start_price, end_price):
    """
    Berechnet Fibonacci-Retracement-Levels zwischen zwei Preispunkten.
    
    Args:
        start_price (float): Startpreis (z.B. Beginn einer Welle)
        end_price (float): Endpreis (z.B. Ende einer Welle)
        
    Returns:
        dict: Dictionary mit Fibonacci-Levels und entsprechenden Preisen
    """
    diff = end_price - start_price
    direction = 1 if diff > 0 else -1
    
    # Standard Fibonacci-Levels
    levels = {
        "0.0": start_price,
        "0.236": start_price + 0.236 * diff,
        "0.382": start_price + 0.382 * diff,
        "0.5": start_price + 0.5 * diff,
        "0.618": start_price + 0.618 * diff,
        "0.786": start_price + 0.786 * diff,
        "1.0": end_price,
        "1.272": end_price + direction * 0.272 * abs(diff),
        "1.618": end_price + direction * 0.618 * abs(diff)
    }
    
    return levels

def plot_waves(df, waves, title="Elliott Wellen Analyse"):
    """
    Plottet die identifizierten Elliott-Wellen auf einem Preischart.
    
    Args:
        df (pandas.DataFrame): DataFrame mit Preisdaten (muss einen 'Close' Spalte haben)
        waves (dict): Dictionary mit Welleninfos (von ElliottWaveAnalyzer)
        title (str): Titel des Plots
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Preisdaten plotten
    ax.plot(df.index, df['Close'], color='black', alpha=0.6, label='Preis')
    
    # Farbcodes für verschiedene Wellentypen
    colors = {
        'impulse': 'blue',
        'corrective': 'red',
        'motive': 'green',
        'diagonal': 'purple'
    }
    
    # Wellen plotten
    for wave_type, wave_list in waves.items():
        if wave_type in colors and wave_list:
            for wave in wave_list:
                indices = wave['indices']
                if not indices or len(indices) < 2:
                    continue
                
                # Extrahiere die Preispunkte an den Wellenindizes
                x_points = [df.index[i] for i in indices if i < len(df)]
                y_points = [df['Close'].iloc[i] for i in indices if i < len(df)]
                
                # Plotte die Wellenpunkte und verbinde sie
                ax.plot(x_points, y_points, 'o-', color=colors[wave_type], alpha=0.7, 
                        label=f"{wave_type.capitalize()} Wave {wave['wave_count']}")
                
                # Beschrifte die Wellenpunkte
                for i, (x, y) in enumerate(zip(x_points, y_points)):
                    ax.annotate(f"{i+1}", (x, y), xytext=(5, 5), textcoords='offset points')
    
    # Formatierung des Plots
    ax.set_title(title)
    ax.set_xlabel('Datum')
    ax.set_ylabel('Preis')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    return fig, ax

def plot_fibonacci_levels(df, start_idx, end_idx, title="Fibonacci Retracement"):
    """
    Plottet Fibonacci-Retracement-Levels zwischen zwei Punkten.
    
    Args:
        df (pandas.DataFrame): DataFrame mit Preisdaten
        start_idx (int): Startindex für das Retracement
        end_idx (int): Endindex für das Retracement
        title (str): Titel des Plots
    """
    start_price = df['Close'].iloc[start_idx]
    end_price = df['Close'].iloc[end_idx]
    
    fib_levels = calculate_fibonacci_levels(start_price, end_price)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Preisdaten plotten
    ax.plot(df.index, df['Close'], color='black', alpha=0.6, label='Preis')
    
    # Start- und Endpunkt markieren
    ax.plot(df.index[start_idx], start_price, 'go', markersize=10, label='Start')
    ax.plot(df.index[end_idx], end_price, 'ro', markersize=10, label='Ende')
    
    # Fibonacci-Levels plotten
    for level, price in fib_levels.items():
        ax.axhline(y=price, color='blue', linestyle='--', alpha=0.5)
        ax.annotate(f"Fib {level}: {price:.2f}", 
                   (df.index[-1], price), 
                   xytext=(5, 0), 
                   textcoords='offset points',
                   color='blue')
    
    # Formatierung des Plots
    ax.set_title(title)
    ax.set_xlabel('Datum')
    ax.set_ylabel('Preis')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    return fig, ax

def zigzag_filter(prices, threshold=0.05):
    """
    Implementiert einen ZigZag-Filter, um Trendumkehrungen zu identifizieren.
    
    Args:
        prices (array-like): Array mit Preisdaten
        threshold (float): Mindestprozentsatz für eine Trendumkehrung (0.05 = 5%)
        
    Returns:
        list: Liste mit Indizes der Wendepunkte
    """
    prices = np.array(prices)
    up_trend = True
    last_extreme = prices[0]
    last_extreme_idx = 0
    turning_points = [0]  # Start mit dem ersten Punkt
    
    for i in range(1, len(prices)):
        if up_trend:
            # In einem Aufwärtstrend suchen wir nach höheren Hochs oder niedrigeren Tiefs
            if prices[i] > last_extreme:
                # Neues Hoch gefunden
                last_extreme = prices[i]
                last_extreme_idx = i
            elif prices[i] < last_extreme * (1 - threshold):
                # Umkehr gefunden - füge den letzten Extremwert hinzu und wechsle zu Abwärtstrend
                turning_points.append(last_extreme_idx)
                up_trend = False
                last_extreme = prices[i]
                last_extreme_idx = i
        else:
            # In einem Abwärtstrend suchen wir nach niedrigeren Tiefs oder höheren Hochs
            if prices[i] < last_extreme:
                # Neues Tief gefunden
                last_extreme = prices[i]
                last_extreme_idx = i
            elif prices[i] > last_extreme * (1 + threshold):
                # Umkehr gefunden - füge den letzten Extremwert hinzu und wechsle zu Aufwärtstrend
                turning_points.append(last_extreme_idx)
                up_trend = True
                last_extreme = prices[i]
                last_extreme_idx = i
    
    # Füge den letzten Punkt hinzu, wenn er noch nicht in der Liste ist
    if last_extreme_idx != turning_points[-1]:
        turning_points.append(last_extreme_idx)
    
    return turning_points 