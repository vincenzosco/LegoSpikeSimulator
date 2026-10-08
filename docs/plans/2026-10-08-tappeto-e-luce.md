# Plan — Tappeto a mattonelle, template, luce variabile e pubblicazione

## Spec (authority)

User request:
> fai in modo che si possano selezionare alcune template, come seguilinea, così con la
> rappresentazione, il robot quando passa sopra una mattonella, sarebbe come se un robot reale
> sarebbe passato sopra una, quindi il robot reagisce e se per esempio, è di girare a 90, il
> robot girerà a 90, devono essere messe in modo random, inoltre crea un github repo con lo
> stesso nome della cartella, e metti readme di default in inglese, e un altro in italiano,
> spiega step by step come usarlo, alcuni screenshot e come installarlo, inoltre fai in modo
> che si possa simulare diversa luce, in modo da vedere come il robot reagisce

Clarified with the user before planning (three forks settled by them):

- **Mattonelle**: *"Sensori sul tappeto (realistico)"* — the mat is a real surface; the
  colour/reflection sensors read the tile **under the robot**; the template program (a real
  Python SPIKE program) decides what to do. If the tile under the robot says "turn 90°", the
  program turns the robot 90°.
- **Luce**: *"Slider luce ambientale"* — one ambient-light slider (0-100 %) that scales the
  reflection reading and, below a threshold, makes colours indistinguishable, so the follower
  visibly fails in the dark.
- **Repo**: *"Pubblico"* — create the public GitHub repo `LegoSpikeSimulator` under
  `vincenzosco` and push `main`.

Derived acceptance criteria:

1. The mat is a **grid of tiles**; each tile has a kind (start / straight / turn-left /
   turn-right / cross / finish). The tiles are placed at **random** (a turtle walk over the
   grid, seeded so a run stays reproducible), forming a connected track.
2. `color_sensor.color(port)` / `reflection(port)` return the **surface of the tile the robot
   is standing on**, not a fixed constant. Moving the robot changes the reading.
3. A selectable **template** (line follower) exists in the GUI: picking it loads the
   line-follower program *and* the matching recommended port layout and a freshly generated
   track.
4. Running the line-follower template on a generated track makes the robot **reach the finish
   tile**: it turns 90° at every coloured turn tile and stops on the finish tile. Proven by a
   test, not by eye.
5. A GUI **ambient-light slider** (0-100 %) changes what the sensors read; at low light the
   follower loses the track. Proven by a test.
6. `README.md` is **English** (GitHub default) and `README.it.md` is Italian; both are
   step-by-step, with **screenshots** and **installation** instructions. Screenshots are real
   PNGs of the app, produced headlessly.
7. The public GitHub repo `LegoSpikeSimulator` exists, has `main` pushed, and its default
   README is the English one.

## Global Constraints

(unchanged from the previous plan, still binding)

- Python 3.14, PyQt5 5.15, `pytest`; run with `python3 -m pytest -q`.
- No simulator logic may require a `QApplication`: keep Qt imports inside `spikesim.gui`.
- Millimetres, degrees, milliseconds. `+x` east, `+y` north, heading 0 = east.
- User programs run in a **subprocess**; the child gets the whole `Config` as JSON. Anything
  the simulator needs at run time must therefore be serialisable in `Config`.
- The GUI reads the child's stdout (one JSON `Trace`); human text goes to stderr.
- Italian UI strings; English identifiers/comments. Existing 135 tests must stay green.
- New rules from this request:
  - A mat is generated **once** (in the GUI) and then travels in the `Config`: randomness must
    not live in the child process, or the run would not match what the user sees.
  - Sensor sampling happens at the **robot centre** (the tile the robot is standing on).
    Rotation about the centre therefore never changes the reading; that is what makes the
    turn-then-advance template deterministic.

## Interfaces (contracts between tasks)

- `spikesim/mat.py` (new) — produces, for T2/T3/T4/T5:
  - `Surface(color: int, reflection: int)`
  - tile kinds `START/STRAIGHT/TURN_LEFT/TURN_RIGHT/CROSS/FINISH/EMPTY`
  - `Tile(kind, rotation)`, `Mat(tile_size_mm, tiles, start_x, start_y, start_heading)`
    with `tile_at(x,y) -> Tile`, `surface_at(x,y) -> Surface`, `bounds()`, `to_dict()/from_dict()`
  - `apply_light(surface, ambient) -> Surface`, `LIGHT_THRESHOLD`
  - `generate_track(seed, straights, turns, tile_size_mm) -> Mat`
  - `TrackTemplate(name, program, ports, straights, turns, description)` and
    `TRACK_TEMPLATES` (ordered dict), `template_build(template, seed) -> Mat`
- `spikesim/config.py` — `Config` gains `mat: Mat | None` and `ambient_light: int`, both
  round-tripped in `to_dict()/from_dict()`. Consumed by T2/T3/T4.
- `spikesim/runtime.py` — `Hardware.surface() -> Surface` (mat tile under `self.pose`, lit by
  `config.ambient_light`; falls back to `config.sensors` when there is no mat) and the robot
  starting on the mat's start pose. Consumed by T2's sensor modules.
- `spikesim/spike/color_sensor.py` — `color`, `reflection`, `rgbi` read `Hardware.surface()`.
- `templates/*.py` (new) — SPIKE user programs; `templates/seguilinea.py` is the reference.
- `spikesim/gui/mat_panel.py` (new) — `MatPanel` with signals `matChanged`,
  `templateChosen(str)`, plus `mat()`, `ambient_light()`, `template()`. Consumed by T4/T5.
- `spikesim/gui/robot_view.py` — `RobotView.set_mat(mat)`; the mat is part of the auto-zoom
  bounds. Consumed by T4/T5.
- `spikesim/gui/port_config_panel.py` — `PortConfigPanel.apply_devices({port: device})`.
  Consumed by T4.
- `tools/make_screenshots.py` (new) — writes `docs/screenshots/*.png` headlessly. Consumed by T5.

## Tasks

### T1 — Mat: tiles, surface sampling, lighting, random generation
Steps:
1. `tests/test_mat.py`: tile→surface mapping; `surface_at` returns the tile the point is in
   (and EMPTY outside); `bounds()` covers every tile; a generated track is connected (each
   tile's exit cell holds the next tile), stays inside its own bounds and is deterministic for
   a given seed while differing across seeds; `apply_light` scales reflection, keeps full
   colour in bright light and collapses colours below the threshold; JSON round-trip of `Mat`.
   Run → expected FAIL (module missing).
2. Implement `spikesim/mat.py`.
3. Run `python3 -m pytest -q tests/test_mat.py` → expected: pass.
4. Commit.

### T2 — Wire the mat and the light into config, runtime and colour sensor
Steps:
1. `tests/test_mat_runtime.py`: `Config` round-trips a `mat` and `ambient_light`; a program
   that prints `color_sensor.color()`/`reflection()` after driving from the start tile onto the
   next tile prints that next tile's colour; `Hardware` starts the robot on the mat's start
   pose; halving the ambient light roughly halves the reflection; without a mat the old fixed
   values still come back (backward compatibility). Run → expected FAIL.
2. Implement the changes in `spikesim/config.py`, `spikesim/runtime.py`,
   `spikesim/spike/color_sensor.py`.
3. Run `python3 -m pytest -q tests/test_mat_runtime.py tests/test_spike_api.py tests/test_runtime.py`
   → expected: pass.
4. Commit.

### T3 — Templates and the line follower
Steps:
1. `tests/test_templates.py`: the registry exposes `seguilinea` and its program exists; running
   `templates/seguilinea.py` on several seeds makes the robot stop on the finish tile
   (final pose == finish tile centre, within a millimetre) with no error diagnostics, and the
   number of 90° turns equals the number of turn tiles on the track; with the ambient light
   turned down the same program fails to reach the finish (the visible "dark" behaviour).
   Run → expected FAIL.
2. Add `templates/` (seguilinea plus one deliberate-failure variant) and the template registry
   in `spikesim/mat.py`.
3. Run `python3 -m pytest -q tests/test_templates.py` → expected: pass.
4. Commit.

### T4 — GUI: template picker, mat view, light slider
Steps:
1. `tests/test_gui.py` (extend): `MatPanel` starts on the line-follower template and yields a
   mat and `ambient_light`; choosing a template emits the program path and applying it loads
   the program *and* the recommended ports; the slider changes `config().ambient_light`;
   `RobotView.set_mat` changes the auto-zoom bounds to cover the track; grabbing the window
   with a mat produces a non-null pixmap. Run → expected FAIL.
2. Implement `spikesim/gui/mat_panel.py`, `robot_view.py` mat drawing,
   `port_config_panel.apply_devices`, and the `main_window.py` wiring (new dock, config merge,
   template load).
3. Run `python3 -m pytest -q tests/test_gui.py` → expected: pass.
4. Commit.

### T5 — Screenshots and the two READMEs
Steps:
1. `tools/make_screenshots.py`: offscreen, load each template, simulate in process, park the
   timeline at a chosen instant and `grab()` the window into `docs/screenshots/*.png`.
   Run it → expected: PNG files exist, each larger than a trivial size.
2. `README.md` (English, default) rewritten: what it is, install, step-by-step use with the
   template/light features, screenshots, troubleshooting, link to the Italian version.
   `README.it.md`: the same in Italian. Both reference `docs/screenshots/`.
3. Run `python3 -m pytest -q` (whole suite) → expected: all green. Commit.

### T6 — Publish the repository
Steps:
1. `gh repo create LegoSpikeSimulator --public --source . --remote origin
   --description "..."` → expected: repo created, `origin` set.
2. `git push -u origin main` → expected: `main` on GitHub matches local `HEAD`.
3. Verify with `gh repo view vincenzosco/LegoSpikeSimulator --json name,visibility,defaultBranchRef,url`
   and `git ls-remote origin main` vs `git rev-parse HEAD`.
4. Ledger the result. No commit (nothing changes in the tree).

## Review Focus

Inputs the tests above do not exercise; check them deliberately at review:

- A track that would fold back onto itself (the generator must not place two tiles in one
  cell), and a track generated with zero turns.
- A turn tile as the *first* tile, and the finish tile immediately after the start.
- `ambient_light` at exactly the threshold, at 0 and at 100.
- A program that reads the colour sensor with no mat configured (old behaviour).
- The GUI with a mat but no program loaded, and re-rolling the track after a simulation.
- A mat whose tiles go to negative coordinates (view bounds, start pose).
