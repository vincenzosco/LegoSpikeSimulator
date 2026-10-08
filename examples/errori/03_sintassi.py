"""ERRORE VOLUTO — manca una virgola.

Il programma non viene nemmeno eseguito: il controllo statico riporta
``SYN001`` con riga e colonna dell'errore di sintassi.
"""

import motor
from hub import port

motor.run(port.A 500)
