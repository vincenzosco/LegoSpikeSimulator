"""La libreria SPIKE 3 simulata.

Ogni sottomodulo corrisponde a un modulo della documentazione SPIKE 3
(``motor``, ``motor_pair``, ``hub``, ``color``, ...). I moduli non vanno
importati dal percorso normale: `spikesim.runner` li registra in
``sys.modules`` con il loro nome "nudo" (``motor``, ``hub``, ...) così che il
programma dell'utente possa scrivere ``import motor`` senza modifiche.

Questo modulo resta volutamente vuoto: importare qui i sottomoduli
creerebbe un ciclo, perché i sottomoduli importano `spikesim.runtime`.
"""
