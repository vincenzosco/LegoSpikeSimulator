"""Eccezioni sollevate dalla libreria SPIKE simulata.

Ogni eccezione porta un ``code`` stabile: la GUI lo mostra nel pannello
problemi, così l'utente può cercare il codice nella documentazione.

Gli avvisi (``SPIKE1xx``) non interrompono il programma: il runtime li
registra nella traccia e prosegue saturando il valore, esattamente come fa
il firmware, che limita i valori fuori intervallo invece di bloccarsi.
"""

from __future__ import annotations


class SpikeError(Exception):
    """Errore di un programma SPIKE."""

    code = "SPIKE001"
    severity = "error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PortOutOfRangeError(SpikeError):
    """La porta non esiste: le porte valide sono 0..5 (A..F)."""

    code = "SPIKE010"


class NoDeviceError(SpikeError):
    """La porta non ha il dispositivo richiesto collegato."""

    code = "SPIKE011"


class NotAMotorError(SpikeError):
    """La porta non ha un motore collegato."""

    code = "SPIKE012"


class NotPairedError(SpikeError):
    """Uso di una Motor Pair mai creata con ``motor_pair.pair``."""

    code = "SPIKE013"


class InvalidArgumentError(SpikeError):
    """Argomento non valido (indice fuori griglia, velocità zero, ...)."""

    code = "SPIKE014"


class PixelOutOfRangeError(InvalidArgumentError):
    """Coordinate di un pixel fuori dalla griglia del dispositivo."""

    code = "SPIKE015"


class ProgramLimitError(SpikeError):
    """Il programma ha superato il limite di tempo o di passi simulati."""

    code = "SPIKE016"


class UnsupportedError(SpikeError):
    """Funzione della libreria non modellata dal simulatore."""

    code = "SPIKE017"
