"""Simulatore di codice per il robot LEGO Education SPIKE Prime.

Il pacchetto reimplementa la libreria Python ufficiale (SPIKE 3) e la esegue
su un modello cinematico a due ruote, con una GUI PyQt5 di supporto.

Layout:

``spikesim.kinematics``
    Modello fisico puro (nessuna dipendenza da Qt).
``spikesim.runtime``
    Orologio virtuale, stato dell'hardware simulato e scheduler cooperativo.
``spikesim.spike``
    La libreria SPIKE 3 eseguibile (``motor``, ``motor_pair``, ``hub``, ...).
``spikesim.runner``
    Esecuzione di un programma utente in un processo separato.
``spikesim.checker``
    Analisi statica del sorgente con diagnostica in italiano.
``spikesim.gui``
    Finestra PyQt5: drag & drop, campo di gioco, pannello problemi.
"""

__version__ = "0.1.0"
