# Halloween Pack

A plugin for the [Ballest plugin manager](https://github.com/AnythingGoes-ballest/ballest-plugin-manager): ten
Halloween balls and five hats, added to the **Customize** page through
[Cosmetic Kit](https://github.com/AnythingGoes-ballest/ballest-cosmetic-kit).

| Ball | Look |
|---|---|
| Pumpkin | the ball is a jack-o'-lantern, rolling as a pumpkin |
| Skull | the ball is a skull |
| Ghost | a ghost floating inside a clear ball with a misty purple lower half |
| Bat | a bat flapping inside a clear ball with a dark purple lower half |
| Ghost Skull | a ghost skull floating inside a clear ball with an eerie green lower half |
| Witch's Brew | a clear ball half full of glowing green potion that stays level, with bubbles |
| Graveyard Globe | a tiny graveyard with graves and a dead tree inside a clear ball, kept upright |
| Spider Web | white webs on a dark purple ball |
| Mummy | a ball wrapped in bandages, with two eyes peeking out |
| Candy Corn | yellow, orange and white |

The ghost, the bat and the ghost skull stay upright, face where the ball is going, and fly faster as it speeds up.

| Hat | Look |
|---|---|
| Witch Hat | a wide brim, a tall bent cone, a purple band and a gold buckle |
| Jack-o'-Lantern | a little carved pumpkin |
| Devil Horns | two red horns |
| Bat | a bat hovering and flapping over the ball |
| Skull Candle | a skull with three lit candles |

## Install

In the game: footer **plugins** > **browse** > Halloween Pack > **install** (Cosmetic Kit comes with it).
Needs the plugin manager host 0.17.1 or newer.

## Credits

All the models are CC0 (public domain):

- [KayKit: Halloween Bits](https://kaylousberg.itch.io/halloween-bits) by Kay Lousberg: the jack-o'-lantern (recoloured
  orange here), the skull, the skull candle, the two graves and the dead tree.
- [Quaternius](https://quaternius.com): the ghost, the ghost skull and the bat.

Downloaded from [Poly Pizza](https://poly.pizza).

## Files

- `main.as`: adds the balls and hats.
- `models/`: the model files (the format is in the plugin manager's
  [custom cosmetics guide](https://anythinggoes-ballest.github.io/ballest-plugin-manager/guides/cosmetics/)) and the
  3D models they use.
- `textures/`, `previews/`, `icon.png`, `models/jackolantern_orange.glb` and the model text files are made by
  `make_pack.py` (Python with NumPy and Pillow), from `sources/jackolantern.glb` and the models.

## License

MIT for this plugin's code and files; the models keep their CC0 licence.
