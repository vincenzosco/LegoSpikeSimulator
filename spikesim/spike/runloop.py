"""``runloop``: avvio e attese del programma.

``runloop.run()`` è l'unico punto in cui il programma passa il controllo
allo scheduler: finché non viene chiamata, le funzioni ``async`` definite
dall'utente non vengono mai eseguite, ed è proprio questo che il simulatore
segnala.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

from ..errors import InvalidArgumentError
from ..runtime import hardware

__all__ = ["run", "sleep_ms", "until"]


def run(*functions: Any) -> None:
    """Avvia una o più funzioni ``async`` in parallelo.

    Esempio::

        async def main():
            await motor.run_for_degrees(port.A, 360, 720)

        runloop.run(main())
    """
    hw = hardware()
    if hw.scheduler is None:
        raise RuntimeError("nessuno scheduler attivo: il programma non è in esecuzione.")

    coroutines: list[Any] = []
    names: list[str] = []
    for function in functions:
        if inspect.iscoroutine(function):
            coroutines.append(function)
            names.append(getattr(function, "__qualname__", "attività"))
        elif inspect.iscoroutinefunction(function):
            hw.note(
                "warning",
                "SPIKE023",
                f"runloop.run() ha ricevuto la funzione «{getattr(function, '__name__', '?')}» "
                "senza parentesi: la avvio io, ma la forma corretta è "
                f"runloop.run({getattr(function, '__name__', '?')}()).",
                line=hw.caller_line(),
            )
            coroutines.append(function())
            names.append(getattr(function, "__name__", "attività"))
        elif function is not None:
            hw.note(
                "error",
                "SPIKE024",
                "runloop.run() richiede funzioni async: "
                f"ricevuto {type(function).__name__}. Usa runloop.run(main()) con "
                "«async def main()».",
                line=hw.caller_line(),
            )

    if not coroutines:
        hw.note(
            "error",
            "SPIKE024",
            "runloop.run() non ha ricevuto nessuna funzione async da avviare.",
            line=hw.caller_line(),
        )
        return
    hw.scheduler.run(coroutines, names=names)


def sleep_ms(duration: int):
    """Attende ``duration`` millisecondi di tempo simulato."""
    hw = hardware()
    try:
        milliseconds = float(duration)
    except (TypeError, ValueError) as exc:
        raise InvalidArgumentError(
            f"durata non valida: {duration!r}; usa un numero di millisecondi."
        ) from exc
    if milliseconds < 0:
        raise InvalidArgumentError(f"durata negativa: {duration!r}.")
    return hw.awaitable(
        kind="sleep",
        label=f"runloop.sleep_ms({milliseconds:g})",
        ready_at=hw.t_ms + milliseconds,
    )


def until(function: Callable[[], bool], timeout: int = 0):
    """Attende che ``function`` restituisca ``True`` (o che scada ``timeout``).

    Con ``timeout = 0`` non c'è scadenza: l'attesa finisce solo quando la
    condizione diventa vera.
    """
    hw = hardware()
    if not callable(function):
        raise InvalidArgumentError(
            "runloop.until() richiede una funzione o una lambda senza parametri."
        )
    deadline = hw.t_ms + float(timeout) if timeout else None
    return hw.awaitable(
        kind="until",
        label="runloop.until(...)",
        ready_at=hw.t_ms,
        predicate=lambda: bool(function()),
        deadline=deadline,
    )
