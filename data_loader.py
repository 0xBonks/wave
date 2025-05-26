#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests
import json
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env-Datei
load_dotenv()

class DataLoader:
    """
    Klasse zum Laden von Marktdaten aus verschiedenen Quellen.
    """
    
    # API-Konfiguration
    YAHOO_APP_ID = os.getenv('AppID')
    YAHOO_CLIENT_ID = os.getenv('ClientID')
    YAHOO_CLIENT_SECRET = os.getenv('ClientSecret')
    
    @staticmethod
    def load_data(source, start_date=None, end_date=None):
        """
        Lädt Marktdaten aus einer Datei oder von Yahoo Finance.
        
        Args:
            source (str): Dateipfad oder Tickersymbol
            start_date (str, optional): Startdatum im Format 'YYYY-MM-DD'
            end_date (str, optional): Enddatum im Format 'YYYY-MM-DD'
            
        Returns:
            pandas.DataFrame: DataFrame mit OHLCV-Daten
        """
        # Setze das aktuelle Datum als Standardwert für end_date
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        # Wenn source eine existierende Datei ist, lade aus der Datei
        if os.path.isfile(source):
            return DataLoader._load_from_file(source)
        
        # Andernfalls versuche, es als Symbol für Yahoo Finance zu interpretieren
        else:
            return DataLoader._load_from_yahoo(source, start_date, end_date)
    
    @staticmethod
    def _load_from_file(file_path):
        """
        Lädt Daten aus einer CSV- oder Excel-Datei.
        
        Args:
            file_path (str): Pfad zur Datei
            
        Returns:
            pandas.DataFrame: DataFrame mit OHLCV-Daten
        """
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Nicht unterstütztes Dateiformat: {file_path}")
        
        # Stelle sicher, dass die Datumsspalte korrekt formatiert ist
        if 'Date' in df.columns or 'Datum' in df.columns:
            date_col = 'Date' if 'Date' in df.columns else 'Datum'
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)
        
        return df
    
    @staticmethod
    def _load_from_yahoo(symbol, start_date, end_date):
        """
        Lädt historische Daten von Yahoo Finance.
        
        Args:
            symbol (str): Aktien-Tickersymbol
            start_date (str): Startdatum im Format 'YYYY-MM-DD'
            end_date (str): Enddatum im Format 'YYYY-MM-DD'
            
        Returns:
            pandas.DataFrame: DataFrame mit OHLCV-Daten
        """
        try:
            df = yf.download(symbol, start=start_date, end=end_date)
            
            # Überprüfe, ob Daten heruntergeladen wurden
            if df.empty:
                raise ValueError(f"Keine Daten für Symbol {symbol} gefunden")
                
            return df
        except Exception as e:
            raise Exception(f"Fehler beim Herunterladen der Daten für {symbol}: {str(e)}")
    
    @staticmethod
    def get_live_data(symbol):
        """
        Holt aktuelle Live-Daten von Yahoo Finance API.
        
        Args:
            symbol (str): Aktien-Tickersymbol
            
        Returns:
            dict: Aktuelle Marktdaten für das Symbol
        """
        # Da die API-Anfragen zu 401-Fehlern führen, nutzen wir direkt den Fallback
        # Prüfe nur, ob API-Schlüssel vorhanden sind, nutze sie aber nicht mehr direkt
        if all([DataLoader.YAHOO_APP_ID, DataLoader.YAHOO_CLIENT_ID, DataLoader.YAHOO_CLIENT_SECRET]):
            print("Info: API-Schlüssel vorhanden, aber es wird yfinance als Datenquelle verwendet.")
        
        # Verwende direkt den Fallback-Mechanismus
        return DataLoader._get_live_data_fallback(symbol)
    
    @staticmethod
    def _get_live_data_fallback(symbol):
        """
        Fallback-Methode für Live-Daten, die yfinance verwendet.
        
        Args:
            symbol (str): Aktien-Tickersymbol
            
        Returns:
            dict: Aktuelle Marktdaten für das Symbol
        """
        try:
            # Verwende yfinance als Fallback
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Hole die aktuellen Marktdaten
            live_data = ticker.history(period='1d')
            
            if live_data.empty:
                raise ValueError(f"Keine Live-Daten für {symbol} verfügbar")
                
            last_quote = live_data.iloc[-1]
            
            # Stelle sicher, dass alle Werte als native Python-Typen (nicht numpy) zurückgegeben werden
            return {
                'symbol': symbol,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'price': float(last_quote.get('Close', 0)),
                'change': float(last_quote.get('Close', 0) - last_quote.get('Open', 0)),
                'change_percent': float(((last_quote.get('Close', 0) / last_quote.get('Open', 0)) - 1) * 100 if last_quote.get('Open', 0) != 0 else 0),
                'volume': float(last_quote.get('Volume', 0)),
                'market_cap': float(info.get('marketCap', 0)) if info.get('marketCap') else None,
                'previous_close': float(info.get('previousClose', 0)) if info.get('previousClose') else None,
                'open': float(last_quote.get('Open', 0)),
                'day_high': float(last_quote.get('High', 0)),
                'day_low': float(last_quote.get('Low', 0))
            }
        except Exception as e:
            raise Exception(f"Fehler beim Abrufen der Live-Daten für {symbol}: {str(e)}")
    
    @staticmethod
    def get_recent_data(symbol, days=60):
        """
        Holt die Daten der letzten X Tage für ein Symbol.
        
        Args:
            symbol (str): Aktien-Tickersymbol
            days (int): Anzahl der Tage zurück (Standard: 60)
            
        Returns:
            pandas.DataFrame: DataFrame mit OHLCV-Daten der letzten X Tage
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return DataLoader._load_from_yahoo(
            symbol, 
            start_date.strftime('%Y-%m-%d'), 
            end_date.strftime('%Y-%m-%d')
        )
    
    @staticmethod
    def save_data(df, file_path):
        """
        Speichert Daten in einer CSV-Datei.
        
        Args:
            df (pandas.DataFrame): DataFrame mit den zu speichernden Daten
            file_path (str): Pfad zur Ausgabedatei
        """
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Speichere die Daten
        df.to_csv(file_path)
        print(f"Daten wurden in {file_path} gespeichert.")


# Test-Funktion zum einfachen Testen des Datenloaders
if __name__ == "__main__":
    # Teste Yahoo Finance-Daten
    df_yahoo = DataLoader.load_data("AAPL", start_date="2022-01-01", end_date="2022-12-31")
    print("Yahoo Finance Daten:")
    print(df_yahoo.head())
    
    # Teste Live-Daten
    live_data = DataLoader.get_live_data("AAPL")
    print("\nLive Daten:")
    print(json.dumps(live_data, indent=2))
    
    # Speichere die Daten in einer CSV-Datei zum späteren Testen des Dateiloaders
    DataLoader.save_data(df_yahoo, "data/AAPL.csv") 