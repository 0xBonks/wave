#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class WavePattern:
    """
    Klasse zur Repräsentation und Validierung von Elliott-Wellen-Mustern.
    """
    
    # Elliott-Wellen-Regeln und -Richtlinien
    RULES = {
        # Regeln für Impulswellen
        "impulse": [
            "Welle 2 darf nicht unter den Beginn von Welle 1 zurückgehen",
            "Welle 3 muss länger sein als Welle 1 oder Welle 5",
            "Welle 3 darf nicht die kürzeste unter den Wellen 1, 3 und 5 sein",
            "Welle 4 darf nicht in den Preisbereich von Welle 1 eindringen"
        ],
        # Regeln für Korrekturwellen
        "corrective": [
            "In einem Zigzag (5-3-5) muss Welle B nicht den Start von Welle A überschreiten",
            "In einem Flat (3-3-5) erreicht Welle B typischerweise ca. 100% von Welle A",
            "In einem Triangle müssen alle Subwellen 3er-Wellen sein (a-b-c)"
        ]
    }
    
    # Fibonacci-Verhältnisse für typische Wellenlängen
    FIBONACCI_RATIOS = {
        "wave1_to_wave3": 1.618,  # Welle 3 ist oft 1.618 mal so lang wie Welle 1
        "wave2_retracement": 0.618,  # Welle 2 korrigiert oft 61.8% von Welle 1
        "wave4_retracement": 0.382,  # Welle 4 korrigiert oft 38.2% von Welle 3
    }
    
    def __init__(self, pattern_type, points):
        """
        Initialisiert ein Wellenmuster.
        
        Args:
            pattern_type (str): Typ des Musters ("impulse", "corrective", "motive", "diagonal")
            points (list): Liste von (index, price)-Tupeln, die die Wellenpunkte darstellen
        """
        self.pattern_type = pattern_type
        self.points = points
        self.is_valid = self.validate_pattern()
        
    def validate_pattern(self):
        """
        Validiert das Wellenmuster anhand der Elliott-Wellen-Regeln.
        
        Returns:
            bool: True, wenn das Muster gültig ist, sonst False
        """
        if self.pattern_type == "impulse":
            return self.validate_impulse_wave()
        elif self.pattern_type == "corrective":
            return self.validate_corrective_wave()
        elif self.pattern_type == "diagonal":
            return self.validate_diagonal_wave()
        else:
            return True  # Für andere Mustertypen keine spezifische Validierung
    
    def validate_impulse_wave(self):
        """
        Validiert eine Impulswelle.
        
        Returns:
            bool: True, wenn die Impulswelle gültig ist, sonst False
        """
        if len(self.points) < 6:  # Eine Impulswelle hat 6 Punkte (0-5)
            return False
        
        # Extrahiere die Preise für jede Welle
        prices = [point[1] for point in self.points]
        
        # Regel 1: Welle 2 darf nicht unter den Beginn von Welle 1 zurückgehen
        if prices[2] <= prices[0]:
            return False
        
        # Regel 2: Welle 3 muss länger sein als Welle 1 oder Welle 5
        wave1_length = abs(prices[2] - prices[0])
        wave3_length = abs(prices[4] - prices[2])
        wave5_length = abs(prices[5] - prices[4])
        
        if not (wave3_length > wave1_length or wave3_length > wave5_length):
            return False
        
        # Regel 3: Welle 3 darf nicht die kürzeste unter den Wellen 1, 3 und 5 sein
        if wave3_length < min(wave1_length, wave5_length):
            return False
        
        # Regel 4: Welle 4 darf nicht in den Preisbereich von Welle 1 eindringen
        # (Ausnahme bei Diagonalen, hier nicht behandelt)
        if (prices[0] < prices[2] and prices[4] < prices[2]) or (prices[0] > prices[2] and prices[4] > prices[2]):
            # Aufwärtstrend oder Abwärtstrend
            if (prices[0] < prices[2] and prices[4] < prices[0]) or (prices[0] > prices[2] and prices[4] > prices[0]):
                return False
        
        return True
    
    def validate_corrective_wave(self):
        """
        Validiert eine Korrekturwelle.
        
        Returns:
            bool: True, wenn die Korrekturwelle gültig ist, sonst False
        """
        if len(self.points) < 4:  # Eine einfache Korrekturwelle hat mindestens 4 Punkte (A-B-C)
            return False
        
        # Für jetzt nur eine einfache Überprüfung
        # In einer komplexeren Implementierung würden wir zwischen verschiedenen
        # Korrekturmustern (Zigzag, Flat, Triangle) unterscheiden
        
        return True
    
    def validate_diagonal_wave(self):
        """
        Validiert eine diagonale Welle.
        
        Returns:
            bool: True, wenn die diagonale Welle gültig ist, sonst False
        """
        # Diagonale Wellen haben ihre eigenen Regeln, sind aber im Grunde Abwandlungen von Impulswellen
        if len(self.points) < 6:
            return False
            
        # In einer komplexen Implementierung würden wir zwischen führenden und endenden
        # Diagonalen unterscheiden und ihre spezifischen Regeln prüfen
        
        return True
    
    def get_next_target(self):
        """
        Berechnet das nächste Kursziel basierend auf dem Wellenmuster.
        
        Returns:
            float: Geschätztes Kursziel
        """
        if not self.is_valid:
            return None
        
        # Extrahiere die Preise
        prices = [point[1] for point in self.points]
        
        if self.pattern_type == "impulse" and len(prices) >= 5:
            # Bei einer vollständigen Impulswelle können wir das Kursziel für eine folgende ABC-Korrektur schätzen
            wave_length = abs(prices[-1] - prices[0])
            direction = 1 if prices[-1] > prices[0] else -1
            
            # Typische Korrektur ist 38.2% bis 61.8% der vorherigen Impulswelle
            target_38 = prices[-1] - direction * 0.382 * wave_length
            target_62 = prices[-1] - direction * 0.618 * wave_length
            
            return (target_38, target_62)
        
        elif self.pattern_type == "corrective" and len(prices) >= 3:
            # Nach einer ABC-Korrektur folgt oft eine Impulswelle in Richtung des vorherigen Trends
            wave_length = abs(prices[-1] - prices[0])
            direction = 1 if prices[-1] < prices[0] else -1  # Umgekehrte Richtung zur Korrektur
            
            # Typische Erweiterung ist 100% bis 161.8% der vorherigen Korrekturwelle
            target_100 = prices[-1] + direction * 1.0 * wave_length
            target_162 = prices[-1] + direction * 1.618 * wave_length
            
            return (target_100, target_162)
        
        return None 