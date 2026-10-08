# Simulatore LEGO SPIKE Prime

Un simulatore con interfaccia grafica per i programmi Python scritti per il
robot **LEGO Education SPIKE Prime**. Carichi un file `.py`, premi *Simula*, e
vedi il robot muoversi su un campo 2D mentre il programma gira: dove va, quanto
ruota, cosa accende sulla matrice LED, e soprattutto **cosa non funziona**.

Il programma dell'utente non va modificato: la libreria SPIKE 3 viene
reimplementata e resa disponibile con i nomi originali (`import motor`,
`from hub import port`, ...), e il modulo `time` di MicroPython riceve
`sleep_ms`, `ticks_ms` e compagne.

La libreria segue la documentazione
[SPIKEPythonDocs — SPIKE 3](https://tuftsceeo.github.io/SPIKEPythonDocs/SPIKE3.html).
L'estrazione del testo di quella pagina usata come riferimento per
l'implementazione è in [`docs/spike3-reference.txt`](docs/spike3-reference.txt).

---

## Avvio rapido

```bash
python3 -m pip install -r requirements.txt      # serve solo PyQt5
python3 run_simulator.py                        # oppure: python3 -m spikesim
python3 run_simulator.py examples/quadrato.py   # aprendo subito un esempio
```

Requisiti: Python 3.10 o superiore, PyQt5 5.15, nessun'altra dipendenza.

## Come si usa

1. **Carica il programma** in uno dei due modi:
   * trascina il file `.py` sopra la finestra (il pannello del codice si
     evidenzia quando il file è valido), oppure
   * incolla il percorso nel campo in alto e premi *Apri* o Invio.
2. Guarda il pannello **Problemi**: viene aggiornato subito, senza eseguire
   nulla. Un doppio clic su un problema porta alla riga di codice.
3. **Simula** con il pulsante o con `F5`. Il programma gira in un processo
   separato; al termine la simulazione parte da sola.
4. Usa la **barra del tempo** per rivedere il movimento: pausa, riavvolgimento
   a un istante preciso, velocità da 0,25x a 10x. Il tempo scorre da solo:
   il grilletto si sposta, il robot avanza e la console si riempie.
5. Chiudendo la finestra durante una simulazione il processo figlio viene
   ucciso subito: non resta niente a girare in sottofondo.
5. Nel pannello **Hardware** dichiara cosa è collegato a ciascuna porta: è
   quello che permette al simulatore di dire «su questa porta non c'è
   niente» e di sapere quali ruote muovono il robot.

## Cosa segnala

Il controllo statico gira *prima* dell'esecuzione, la diagnostica di runtime
mentre il programma gira. Ogni messaggio porta il codice e, quando esiste, il
numero di riga.

### Errori di scrittura del programma

| Codice | Cosa significa |
|---|---|
| `SYN001` | errore di sintassi, con riga e colonna |
| `SYN002` | file non leggibile |
| `PYTHON` | eccezione di Python durante l'esecuzione (riga del programma e traceback completo) |
| `SPIKE100` | modulo scritto male (`import motr` → «intendevi motor?») |
| `SPIKE101` | nome inesistente in un modulo SPIKE (`motor.runn`, `color.PINK`, `port.G`) |
| `SPIKE102` | funzione asincrona chiamata senza `await`: non fa assolutamente nulla |
| `SPIKE103` | `runloop.run(main)` senza parentesi |
| `SPIKE104` | una funzione `async def` definita e mai avviata |
| `SPIKE105` | coppia motori usata prima di `motor_pair.pair(...)` |
| `SPIKE106` | motore o sensore usato su una porta dove non c'è |

### Errori e avvisi durante la simulazione

| Codice | Cosa significa |
|---|---|
| `SPIKE010` | porta non valida (le porte sono `port.A` … `port.F`) |
| `SPIKE011` | sulla porta non c'è il sensore richiesto |
| `SPIKE012` | sulla porta non c'è un motore |
| `SPIKE013` | coppia motori mai creata con `motor_pair.pair` |
| `SPIKE014` | argomento non valido (per esempio velocità 0 in un movimento a durata) |
| `SPIKE015` | pixel fuori dalla griglia del dispositivo |
| `SPIKE016` | il programma non termina: fermato al limite di tempo o di passi |
| `SPIKE018` | traccia troncata: programma troppo lungo |
| `SPIKE019` | il motore non si muove e non raggiungerà la posizione richiesta |
| `SPIKE020` | comando creato e mai atteso con `await` |
| `SPIKE021` | tutte le attività sono bloccate su qualcosa di non pianificabile |
| `SPIKE022` | `await` su qualcosa che non è un'operazione SPIKE (per esempio `asyncio`) |
| `SPIKE023` | `runloop.run(main)` senza parentesi: la funzione viene avviata comunque |
| `SPIKE024` | `runloop.run` non ha ricevuto nessuna funzione `async` |
| `SPIKE031`–`SPIKE034` | intensità, volume, velocità o sterzo fuori intervallo: valore limitato |
| `TIMEOUT` | il processo non ha risposto ed è stato interrotto |
| `CANCELLED` | la simulazione è stata annullata (chiusura della finestra) |
| `RUNNER` | il processo che esegue il programma non ha prodotto una traccia valida |

## Il modello di simulazione

### Tempo

Il tempo è **virtuale**: `sleep_ms(1000)` costa qualche millisecondo reale e
non un secondo. Gli otto esempi in `examples/`, ciclo infinito compreso,
vengono simulati in circa mezzo secondo. Il tempo avanza solo quando tutte le
attività sono in attesa, quindi il risultato è anche riproducibile.

### Movimento

Il robot è un drive base a due ruote differenziali:

* solo i motori collegati alle due porte indicate come *ruota sinistra* e
  *ruota destra* muovono il robot; un motore su un'altra porta gira ma non
  sposta nulla (è un braccio);
* la rotazione del motore diventa spazio percorso dalla ruota attraverso il
  diametro (`motor_degrees_to_mm`), e le due ruote diventano avanzamento e
  rotazione del robot (`integrate`);
* l'integrazione usa la soluzione esatta del moto a curvatura costante, quindi
  un arco percorso in un solo passo o in cento passi dà lo stesso risultato;
* il giroscopio (`motion_sensor.tilt_angles()`, `reset_yaw`, `angular_velocity`)
  segue l'orientamento del robot: un programma che ruota di 90° leggendo lo
  yaw funziona davvero (vedi `examples/quadrato.py`).

Lo sterzo segue la convenzione dei blocchi Word: `0` dritto, `100` a destra,
`-100` a sinistra. Per una coppia, `degrees` è la rotazione della ruota più
veloce.

### Limitazioni note

Il simulatore è pensato per il *comportamento* del programma, non per la
meccanica fine. Cosa non è modellato:

* rampe di accelerazione e decelerazione: la velocità è costante per tutta la
  durata del comando (i parametri `acceleration`/`deceleration` sono accettati
  e ignorati);
* attrito, inerzia, slittamento delle ruote e urti: il robot non sbanda e non
  incontra ostacoli;
* i pulsanti del hub non vengono mai premuti e i gesti non avvengono mai:
  un ciclo che aspetta un pulsante non termina e viene fermato dal limite di
  passi, con un messaggio che lo spiega;
* i valori dei sensori sono quelli impostati nel pannello Hardware: non c'è un
  ambiente da misurare;
* `app.display`, `app.bargraph`, `app.linegraph`, `app.music` e `app.sound`
  scrivono nella console invece di disegnare su un tablet;
* le 67 immagini della matrice LED sono i bitmap 5x5 del progetto MicroPython
  micro:bit (licenza MIT), che LEGO riusa. I quattro `IMAGE_GO_*` non hanno un
  equivalente micro:bit e sono mappati sui corrispondenti `IMAGE_ARROW_*`;
* il campo è il piano matematico: `+x` verso est, `+y` verso nord, il robot
  parte nell'origine rivolto a est.

### Nota sui pacchetti `spike3_stubs`

Alcuni ambienti hanno in `site-packages` un pacchetto `spike3_stubs` che
fornisce moduli chiamati `hub`, `motor`, `runloop`, … e che si limita a
interrompersi dicendo che funziona solo sull'hardware. Il simulatore registra i
propri moduli in `sys.modules` prima di eseguire il programma, quindi la
libreria della simulazione vince sempre su quella installata: il programma
dell'utente non deve sapere quale delle due è presente.

## Struttura del progetto

```
run_simulator.py            avvio della GUI
examples/                   programmi di esempio, anche volutamente sbagliati
spikesim/
  kinematics.py             modello fisico puro (nessuna dipendenza da Qt)
  config.py                 cosa è collegato a ogni porta, geometria del robot
  errors.py                 eccezioni della libreria SPIKE, con codice stabile
  trace.py                  traccia della simulazione: eventi, pose, diagnostica
  runtime.py                orologio virtuale, hardware simulato, scheduler
  spike/                    la libreria SPIKE 3 eseguibile
    motor.py  motor_pair.py  runloop.py  device.py  color.py  orientation.py
    color_sensor.py  distance_sensor.py  force_sensor.py  color_matrix.py
    hub/                    port, button, light, light_matrix, motion_sensor, sound
    app/                    bargraph, display, linegraph, music, sound
  spike_api.py              registrazione dei moduli e shim di `time`
  runner.py                 esecuzione del programma (in processo o separata)
  checker.py                analisi statica, prima di eseguire
  gui/                      finestra PyQt5, campo 2D, matrice LED, console
docs/spike3-reference.txt   riferimento della libreria SPIKE 3
docs/plans/                 piano di implementazione
```

La logica (`spikesim` senza `gui`) non importa Qt: si può testare e usare da
riga di comando.

## Test

```bash
python3 -m pytest -q
```

I test della GUI girano senza schermo (`QT_QPA_PLATFORM=offscreen` viene
impostato da `tests/conftest.py`): la finestra viene davvero costruita, il
programma davvero eseguito in un processo separato, e la vista del robot
davvero disegnata e confrontata fra l'inizio e la fine della simulazione.

## Uso da riga di comando

```bash
python3 -m spikesim.runner --file examples/quadrato.py            # traccia JSON su stdout
python3 -m spikesim.runner --file examples/quadrato.py --out t.json
```

Il processo figlio scrive **solo** la traccia JSON su `stdout`; tutto il resto
va su `stderr`.
