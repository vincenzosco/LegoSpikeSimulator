# Simulatore LEGO SPIKE Prime

*[Read this document in English →](README.md)*

Un simulatore con interfaccia grafica per i programmi Python scritti per il hub
**LEGO Education SPIKE Prime**. Carichi un file `.py`, premi **Simula**, e vedi
il robot muoversi su un campo 2D mentre il programma gira: dove va, quanto
ruota, cosa accende sulla matrice LED, e soprattutto **cosa non funziona**.

Il robot può muoversi su un **tappeto fatto di mattonelle**. Il sensore di
colore legge la mattonella su cui si trova il robot, quindi un programma
*segui-linea* reagisce come un robot vero: vede una mattonella verde e gira di
90° a sinistra. Le mattonelle vengono disposte **a caso**, e si può abbassare la
luce per vedere il robot perdere la pista.

![Il simulatore con il template seguilinea caricato](docs/screenshots/01-avvio.png)

**Il tuo programma non viene mai modificato.** La libreria SPIKE 3 viene
reimplementata e resa disponibile con i nomi originali (`import motor`,
`from hub import port`, …), e il modulo `time` di MicroPython riceve
`sleep_ms`, `ticks_ms` e compagne.

La libreria segue la documentazione
[SPIKEPythonDocs — SPIKE 3](https://tuftsceeo.github.io/SPIKEPythonDocs/SPIKE3.html).
L'estrazione del testo di quella pagina usata come riferimento per
l'implementazione è in [`docs/spike3-reference.txt`](docs/spike3-reference.txt).

---

## Installazione

Serve **Python 3.10 o superiore**. L'unica dipendenza è Qt.

```bash
# 1. scarica il codice
git clone https://github.com/vincenzosco/LegoSpikeSimulator.git
cd LegoSpikeSimulator

# 2. (consigliato) crea un ambiente virtuale
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. installa la dipendenza
python3 -m pip install -r requirements.txt

# 4. avvialo
python3 run_simulator.py
```

Tutto qui: nessun passo di compilazione, nessuna installazione di Qt, nessun
hardware.

### Verifica dell'installazione

```bash
python3 -m pytest -q     # tutta la suite di test, circa 6 secondi
```

Se leggi `230 passed`, è tutto a posto.

## Avvio rapido

```bash
python3 run_simulator.py                        # la finestra si apre su una pista pronta
python3 run_simulator.py examples/quadrato.py   # oppure dentro un esempio
python3 -m spikesim                             # equivalente a run_simulator.py
```

Il simulatore si apre con il template **Seguilinea facile** già caricato: premi
**Simula (F5)** e il robot percorrerà la pista.

## Passo per passo

### 1. Scegli un template

Il pannello a destra, **«Tappeto e luce»**, elenca i percorsi pronti all'uso:

| Template | Cos'è |
|---|---|
| **Seguilinea facile** | una pista corta con due curve: il primo da provare |
| **Seguilinea** | una pista media: il segui-linea legge ogni mattonella e gira di 90° |
| **Seguilinea lungo** | una pista lunga con molte curve |

Scegliendone uno si genera una **pista casuale nuova** e si carica il programma
che la percorre. La pista non ti piace? Premi **🎲 Nuovo percorso**. Il campo
**Seme** è quello che rende il sorteggio riproducibile: lo stesso seme dà sempre
la stessa pista, così una simulazione che ti è piaciuta si può rifare identica.

### 2. Capire le mattonelle

Il tappeto è una griglia di mattonelle. Il sensore di colore misura la
mattonella **sotto il centro del robot**: è questo che permette al programma di
reagire.

| Mattonella | Colore letto dal sensore | Cosa fa il segui-linea |
|---|---|---|
| Partenza | blu | va dritto |
| Dritto | nera | va dritto |
| Curva a sinistra | **verde** | gira di 90° a sinistra |
| Curva a destra | **rossa** | gira di 90° a destra |
| Arrivo | gialla | si ferma |

Le mattonelle sono disposte a caso in una pista continua, che parte sempre dalla
mattonella blu e finisce su quella gialla. Ogni curva è una rotazione **sul
posto**: il robot resta al centro della mattonella e la mattonella successiva è
sempre esattamente davanti a lui.

![Il segui-linea a metà percorso](docs/screenshots/02-seguilinea.png)

La console in basso racconta cosa vede il robot a ogni passo:

```
seguilinea: parto
passo 0 -> partenza - riflessione 55
passo 1 -> dritto - riflessione 6
passo 2 -> curva a sinistra - riflessione 45
curva a sinistra
passo 3 -> dritto - riflessione 6
...
arrivato!
```

![Primo piano del campo con il tappeto disegnato](docs/screenshots/03-campo.png)

### 3. Abbassa la luce

Il cursore **Luce** imposta la luce ambientale da 100 % a 0 %. La riflessione è
proporzionale alla luce: a metà luce la lettura si dimezza. Sotto il **25 %** il
sensore di colore non riesce più a distinguere i colori e riporta *sconosciuto*:
esattamente quello che succederebbe a un sensore vero al buio.

![La stessa pista con la luce al 5 %: il robot non si muove](docs/screenshots/05-buio.png)

Al 5 % lo stesso identico programma si ferma subito con
`non vedo più la pista: mi fermo`. Rimetti il cursore a 100 %, premi di nuovo
**Simula**, e completa la pista. È tutto qui: la luce cambia il comportamento
del robot.

### 4. Prova una pista più lunga

![La pista lunga: il campo si allarga per contenerla](docs/screenshots/06-percorso-lungo.png)

### 5. Carica un tuo programma

1. **Carica il programma** in uno dei due modi:
   * trascina il file `.py` sopra la finestra (il pannello del codice si
     evidenzia quando il file è valido), oppure
   * incolla il percorso nel campo in alto e premi *Apri* o Invio.
2. Guarda il pannello **Problemi**: viene aggiornato subito, senza eseguire
   nulla. Un doppio clic su un problema porta alla riga di codice.
3. **Simula** con il pulsante o con `F5`. Il programma gira in un processo
   separato; al termine la riproduzione parte da sola.
4. Usa la **barra del tempo** per rivedere il movimento: pausa, riavvolgimento a
   un istante preciso, velocità da 0,25x a 10x. Il tempo scorre da solo: il
   robot avanza e la console si riempie.
5. Chiudendo la finestra durante una simulazione il processo figlio viene
   ucciso subito: non resta niente a girare in sottofondo.
6. Nel pannello **Hardware** dichiara cosa è collegato a ciascuna porta: è quello
   che permette al simulatore di dire «su questa porta non c'è niente» e di
   sapere quali ruote muovono il robot.

Un programma che guida il robot si può anche scrivere da zero:

```python
import motor_pair, runloop
from hub import motion_sensor, port

async def main():
    motor_pair.pair(motor_pair.PAIR_1, port.A, port.B)
    await motor_pair.move_for_degrees(motor_pair.PAIR_1, 720, 0, velocity=500)

runloop.run(main())
```

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

Il tempo è **virtuale**: `sleep_ms(1000)` costa qualche millisecondo reale e non
un secondo. Gli otto esempi in `examples/`, ciclo infinito compreso, vengono
simulati in circa mezzo secondo. Il tempo avanza solo quando tutte le attività
sono in attesa, quindi il risultato è anche riproducibile.

### Movimento

Il robot è un drive base a due ruote differenziali:

* solo i motori collegati alle due porte indicate come *ruota sinistra* e *ruota
  destra* muovono il robot; un motore su un'altra porta gira ma non sposta nulla
  (è un braccio);
* la rotazione del motore diventa spazio percorso dalla ruota attraverso il
  diametro (`motor_degrees_to_mm`), e le due ruote diventano avanzamento e
  rotazione del robot (`integrate`);
* l'integrazione usa la soluzione esatta del moto a curvatura costante, quindi
  un arco percorso in un solo passo o in cento passi dà lo stesso risultato;
* il giroscopio (`motion_sensor.tilt_angles()`, `reset_yaw`, `angular_velocity`)
  segue l'orientamento del robot: un programma che ruota di 90° leggendo lo yaw
  funziona davvero (vedi `examples/quadrato.py`).

Lo sterzo segue la convenzione dei blocchi Word: `0` dritto, `100` a destra,
`-100` a sinistra. Per una coppia, `degrees` è la rotazione della ruota più
veloce.

### Il tappeto

* Il tappeto è una griglia di mattonelle (100 mm di lato per default) generata
  **una volta sola**, nella GUI, e poi trasportata dentro la configurazione fino
  al processo che esegue il programma: così il robot percorre sempre il tappeto
  che stai guardando.
* Il sensore di colore campiona la mattonella sotto il **centro** del robot. Una
  rotazione sul posto quindi non cambia la lettura: è questo che tiene il
  segui-linea allineato alla griglia.
* La riflessione è proporzionale alla luce ambientale, e sotto il 25 % i colori
  diventano indistinguibili (`color.UNKNOWN`).

### Limitazioni note

Il simulatore è pensato per il *comportamento* del programma, non per la
meccanica fine. Cosa non è modellato:

* rampe di accelerazione e decelerazione: la velocità è costante per tutta la
  durata del comando (i parametri `acceleration`/`deceleration` sono accettati e
  ignorati);
* attrito, inerzia, slittamento delle ruote e urti: il robot non sbanda e non
  incontra ostacoli;
* i pulsanti del hub non vengono mai premuti e i gesti non avvengono mai: un
  ciclo che aspetta un pulsante non termina e viene fermato dal limite di passi,
  con un messaggio che lo spiega;
* i sensori diversi dal sensore di colore restituiscono i valori impostati nel
  pannello Hardware: non c'è un ambiente da misurare (il sensore di colore è
  quello che legge il tappeto);
* `app.display`, `app.bargraph`, `app.linegraph`, `app.music` e `app.sound`
  scrivono nella console invece di disegnare su un tablet;
* le 67 immagini della matrice LED sono i bitmap 5x5 del progetto MicroPython
  micro:bit (licenza MIT), che LEGO riusa. I quattro `IMAGE_GO_*` non hanno un
  equivalente micro:bit e sono mappati sui corrispondenti `IMAGE_ARROW_*`;
* il campo è il piano matematico: `+x` verso est, `+y` verso nord, e il robot
  parte dalla posa di partenza del tappeto, rivolto a est.

### Nota sui pacchetti `spike3_stubs`

Alcuni ambienti hanno in `site-packages` un pacchetto `spike3_stubs` che
fornisce moduli chiamati `hub`, `motor`, `runloop`, … e che si limita a
interrompersi dicendo che funziona solo sull'hardware. Il simulatore registra i
propri moduli in `sys.modules` prima di eseguire il programma, quindi la libreria
della simulazione vince sempre su quella installata: il programma dell'utente non
deve sapere quale delle due è presente.

## Struttura del progetto

```
run_simulator.py            avvio della GUI
templates/                  programmi SPIKE pronti all'uso (seguilinea.py, ...)
examples/                   programmi di esempio, anche volutamente sbagliati
tools/make_screenshots.py   rigenera le immagini di questo README, senza schermo
spikesim/
  kinematics.py             modello fisico puro (nessuna dipendenza da Qt)
  mat.py                    il tappeto a mattonelle: superfici, luce, percorsi
  templates.py              il catalogo dei template (pista + programma + porte)
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
docs/screenshots/           le immagini usate dai README
docs/plans/                 i piani di implementazione
```

La logica (`spikesim` senza `gui`) non importa Qt: si può testare e usare da riga
di comando.

## Test

```bash
python3 -m pytest -q
```

I test della GUI girano senza schermo (`QT_QPA_PLATFORM=offscreen` viene
impostato da `tests/conftest.py`): la finestra viene davvero costruita, il
programma davvero eseguito in un processo separato, e la vista del robot davvero
disegnata e confrontata fra l'inizio e la fine della simulazione.

## Uso da riga di comando

```bash
python3 -m spikesim.runner --file examples/quadrato.py            # traccia JSON su stdout
python3 -m spikesim.runner --file examples/quadrato.py --out t.json
```

Il processo figlio scrive **solo** la traccia JSON su `stdout`; tutto il resto va
su `stderr`.

## Rigenerare gli screenshot

```bash
python3 tools/make_screenshots.py
```

Costruisce la finestra vera senza schermo, esegue i template e riscrive
`docs/screenshots/*.png`, verificando che ogni immagine mostri davvero quello che
la didascalia promette.

## Licenza

MIT — vedi [LICENSE](LICENSE). I bitmap della matrice LED vengono dal progetto
MicroPython micro:bit (MIT).
