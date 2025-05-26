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
    
    # Liste deutscher Börsen für Yahoo Finance
    GERMAN_EXCHANGES = {
        'FRA': '.F',    # Frankfurt
        'XETR': '.DE',  # Xetra
        'BER': '.BE',   # Berlin
        'STU': '.SG',   # Stuttgart
        'MUN': '.MU',   # München
        'HAM': '.HM',   # Hamburg
        'HAN': '.HA',   # Hannover
        'DUS': '.DU',   # Düsseldorf
    }
    
    # Liste bekannter US-Aktien und Indizes
    US_SYMBOLS = [
        'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'GOOG', 'META', 'TSLA', 'NVDA', 'JPM', 'V', 
        'JNJ', 'WMT', 'PG', 'MA', 'UNH', 'HD', 'BAC', 'DIS', 'ADBE', 'CRM',
        'NFLX', 'INTC', 'CSCO', 'VZ', 'PFE', 'KO', 'PEP', 'T', 'MRK', 'XOM'
    ]
    
    # Liste der US-Indizes
    US_INDICES = [
        '^GSPC',  # S&P 500
        '^DJI',   # Dow Jones Industrial Average
        '^IXIC',  # NASDAQ Composite
        '^RUT',   # Russell 2000
        '^VIX'    # Volatility Index
    ]
    
    # Standard-Börse für deutsche Aktien
    DEFAULT_GERMAN_EXCHANGE = 'XETR'
    
    @staticmethod
    def is_us_symbol(symbol):
        """
        Prüft, ob es sich um ein US-Symbol handelt.
        
        Args:
            symbol (str): Das zu prüfende Symbol
            
        Returns:
            bool: True, wenn es sich um ein US-Symbol handelt
        """
        # Entferne mögliche Suffixe für den Vergleich
        base_symbol = symbol.split('.')[0]
        
        # Prüfe, ob es ein bekanntes US-Symbol oder Index ist
        return (base_symbol in DataLoader.US_SYMBOLS or 
                symbol in DataLoader.US_INDICES or
                symbol.startswith('^'))
    
    @staticmethod
    def format_german_symbol(symbol, exchange=None):
        """
        Formatiert ein Symbol für den deutschen Markt.
        
        Args:
            symbol (str): Das Basis-Symbol (z.B. 'SAP')
            exchange (str, optional): Die Börse (z.B. 'XETR', 'FRA')
            
        Returns:
            str: Das formatierte Symbol (z.B. 'SAP.DE')
        """
        # Wenn es ein US-Symbol ist, nicht formatieren
        if DataLoader.is_us_symbol(symbol):
            return symbol
            
        # Prüfe, ob bereits ein Suffix vorhanden ist
        if any(suffix in symbol for suffix in DataLoader.GERMAN_EXCHANGES.values()):
            return symbol
            
        # Wenn eine Börse angegeben wurde, verwende deren Suffix
        if exchange and exchange in DataLoader.GERMAN_EXCHANGES:
            return f"{symbol}{DataLoader.GERMAN_EXCHANGES[exchange]}"
            
        # Ansonsten verwende die Standardbörse
        return f"{symbol}{DataLoader.GERMAN_EXCHANGES[DataLoader.DEFAULT_GERMAN_EXCHANGE]}"
    
    @staticmethod
    def is_german_index(symbol):
        """
        Prüft, ob es sich um einen deutschen Index handelt.
        
        Args:
            symbol (str): Das zu prüfende Symbol
            
        Returns:
            bool: True, wenn es sich um einen deutschen Index handelt
        """
        german_indices = [
            'DAX', '^GDAXI',     # DAX
            'MDAX', '^MDAXI',    # MDAX
            'SDAX', '^SDAXI',    # SDAX
            'TecDAX', '^TDXP',   # TecDAX
            'HDAX', '^HDAXI',    # HDAX
        ]
        return symbol in german_indices
    
    @staticmethod
    def load_data(source, start_date=None, end_date=None, exchange=None):
        """
        Lädt Marktdaten aus einer Datei oder von Yahoo Finance.
        
        Args:
            source (str): Dateipfad oder Tickersymbol
            start_date (str, optional): Startdatum im Format 'YYYY-MM-DD'
            end_date (str, optional): Enddatum im Format 'YYYY-MM-DD'
            exchange (str, optional): Deutsche Börse (z.B. 'XETR', 'FRA')
            
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
            # Prüfe, ob es ein deutscher Index ist
            if DataLoader.is_german_index(source):
                # Verwende das korrekte Symbol für den Index
                if source == 'DAX':
                    source = '^GDAXI'
                elif source == 'MDAX':
                    source = '^MDAXI'
                elif source == 'SDAX':
                    source = '^SDAXI'
                elif source == 'TecDAX':
                    source = '^TDXP'
                elif source == 'HDAX':
                    source = '^HDAXI'
            # Prüfe, ob es ein US-Symbol ist
            elif DataLoader.is_us_symbol(source):
                # Für US-Symbole keine weitere Formatierung
                pass
            # Ansonsten formatiere es als deutsches Aktien-Symbol, wenn keine Datei vorliegt
            elif not any(suffix in source for suffix in DataLoader.GERMAN_EXCHANGES.values()):
                source = DataLoader.format_german_symbol(source, exchange)
                
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
            print(f"Lade Daten für Symbol: {symbol}")
            df = yf.download(symbol, start=start_date, end=end_date)
            
            # Überprüfe, ob Daten heruntergeladen wurden
            if df.empty:
                raise ValueError(f"Keine Daten für Symbol {symbol} gefunden")
                
            return df
        except Exception as e:
            raise Exception(f"Fehler beim Herunterladen der Daten für {symbol}: {str(e)}")
    
    @staticmethod
    def get_live_data(symbol, exchange=None):
        """
        Holt aktuelle Live-Daten von Yahoo Finance API.
        
        Args:
            symbol (str): Aktien-Tickersymbol
            exchange (str, optional): Deutsche Börse (z.B. 'XETR', 'FRA')
            
        Returns:
            dict: Aktuelle Marktdaten für das Symbol
        """
        # Prüfe, ob es ein deutscher Index ist
        if DataLoader.is_german_index(symbol):
            # Verwende das korrekte Symbol für den Index
            if symbol == 'DAX':
                symbol = '^GDAXI'
            elif symbol == 'MDAX':
                symbol = '^MDAXI'
            elif symbol == 'SDAX':
                symbol = '^SDAXI'
            elif symbol == 'TecDAX':
                symbol = '^TDXP'
            elif symbol == 'HDAX':
                symbol = '^HDAXI'
        # Prüfe, ob es ein US-Symbol ist
        elif DataLoader.is_us_symbol(symbol):
            # Für US-Symbole keine weitere Formatierung
            pass
        # Ansonsten formatiere es als deutsches Aktien-Symbol, wenn nötig
        elif not any(suffix in symbol for suffix in DataLoader.GERMAN_EXCHANGES.values()):
            symbol = DataLoader.format_german_symbol(symbol, exchange)
            
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
            
            # Sammle Sentiment-Daten (Short Interest und Options-Daten)
            short_percent = info.get('shortPercentOfFloat', None)
            if short_percent is not None:
                # Konvertiere in Prozent falls als Dezimalwert
                if short_percent < 1:
                    short_percent = short_percent * 100
            
            # Hole Optionsdaten, wenn verfügbar
            put_call_ratio = None
            options_data = {}
            try:
                # Prüfe, ob Optionen verfügbar sind
                exp_dates = ticker.options
                
                if exp_dates:
                    # Nimm das nächste Verfallsdatum
                    nearest_date = exp_dates[0]
                    
                    # Hole Optionen für dieses Datum
                    options = ticker.option_chain(nearest_date)
                    
                    # Berechne Put/Call Ratio
                    total_calls_volume = options.calls['volume'].sum() if 'volume' in options.calls.columns else 0
                    total_puts_volume = options.puts['volume'].sum() if 'volume' in options.puts.columns else 0
                    
                    if total_calls_volume > 0:
                        put_call_ratio = total_puts_volume / total_calls_volume
                    
                    # Sammle weitere Optionsdaten
                    options_data = {
                        'expiry_date': nearest_date,
                        'calls_volume': total_calls_volume,
                        'puts_volume': total_puts_volume,
                        'total_options_volume': total_calls_volume + total_puts_volume
                    }
            except Exception as e:
                print(f"Keine Optionsdaten verfügbar für {symbol}: {str(e)}")
            
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
                'day_low': float(last_quote.get('Low', 0)),
                # Neue Sentiment-Daten
                'short_percent': short_percent,
                'short_ratio': info.get('shortRatio', None),  # Days to Cover
                'put_call_ratio': put_call_ratio,
                'options_data': options_data
            }
        except Exception as e:
            raise Exception(f"Fehler beim Abrufen der Live-Daten für {symbol}: {str(e)}")
    
    @staticmethod
    def get_recent_data(symbol, days=60, exchange=None):
        """
        Holt die Daten der letzten X Tage für ein Symbol.
        
        Args:
            symbol (str): Aktien-Tickersymbol
            days (int): Anzahl der Tage zurück (Standard: 60)
            exchange (str, optional): Deutsche Börse (z.B. 'XETR', 'FRA')
            
        Returns:
            pandas.DataFrame: DataFrame mit OHLCV-Daten der letzten X Tage
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Prüfe, ob es ein deutscher Index ist
        if DataLoader.is_german_index(symbol):
            # Verwende das korrekte Symbol für den Index
            if symbol == 'DAX':
                symbol = '^GDAXI'
            elif symbol == 'MDAX':
                symbol = '^MDAXI'
            elif symbol == 'SDAX':
                symbol = '^SDAXI'
            elif symbol == 'TecDAX':
                symbol = '^TDXP'
            elif symbol == 'HDAX':
                symbol = '^HDAXI'
        # Prüfe, ob es ein US-Symbol ist
        elif DataLoader.is_us_symbol(symbol):
            # Für US-Symbole keine weitere Formatierung
            pass
        # Ansonsten formatiere es als deutsches Aktien-Symbol, wenn nötig
        elif not any(suffix in symbol for suffix in DataLoader.GERMAN_EXCHANGES.values()):
            symbol = DataLoader.format_german_symbol(symbol, exchange)
            
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
    # Teste deutsche Aktie
    df_sap = DataLoader.load_data("SAP", start_date="2022-01-01", end_date="2022-12-31")
    print("SAP Daten (Xetra):")
    print(df_sap.head())
    
    # Teste deutschen Index
    df_dax = DataLoader.load_data("DAX", start_date="2022-01-01", end_date="2022-12-31")
    print("\nDAX Daten:")
    print(df_dax.head())
    
    # Teste US-Aktie
    df_aapl = DataLoader.load_data("AAPL", start_date="2022-01-01", end_date="2022-12-31")
    print("\nAAPL Daten (US-Markt):")
    print(df_aapl.head())
    
    # Teste Live-Daten
    live_data = DataLoader.get_live_data("SAP")
    print("\nLive Daten (SAP):")
    print(json.dumps(live_data, indent=2))
    
    # Teste US Live-Daten
    live_data_us = DataLoader.get_live_data("AAPL")
    print("\nLive Daten (AAPL):")
    print(json.dumps(live_data_us, indent=2))
    
    # Speichere die Daten in einer CSV-Datei zum späteren Testen des Dateiloaders
    DataLoader.save_data(df_sap, "data/SAP.csv") 