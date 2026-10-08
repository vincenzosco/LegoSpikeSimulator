"""La matrice a 25 LED del hub: immagini predefinite e testo scorrevole."""

import runloop
from hub import light_matrix


async def main():
    light_matrix.show_image(light_matrix.IMAGE_HEART)
    await runloop.sleep_ms(800)

    light_matrix.show_image(light_matrix.IMAGE_HAPPY)
    await runloop.sleep_ms(800)

    await light_matrix.write("CIAO SPIKE", time_per_character=300)

    light_matrix.show_image(light_matrix.IMAGE_SNAKE)
    await runloop.sleep_ms(800)

    light_matrix.clear()


runloop.run(main())
