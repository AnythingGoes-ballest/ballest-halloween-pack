# Halloween Pack

A plugin for the [Ballest plugin manager](https://github.com/AnythingGoes-ballest/ballest-plugin-manager): ten
Halloween balls and five hats, added to the **Customize** page through
[Cosmetic Kit](https://github.com/AnythingGoes-ballest/ballest-cosmetic-kit).

| Ball | Look |
|---|---|
| Pumpkin | the ball is a jack-o'-lantern, its carved face glowing from inside |
| Skull | the ball is a skull |
| Ghost | a glowing ghost floating inside a clear ball with a misty purple lower half |
| Bat | a purple bat with glowing red eyes flapping inside a clear ball with a dark purple lower half |
| Ghost Skull | a glowing green ghost with a skull face inside a clear ball with an eerie green lower half |
| Witch's Brew | glowing green potion that stays level, with a swirl of light, rising bubbles, a skull and two eyeballs |
| Graveyard Globe | a moonlit graveyard kept upright: graves, a dead tree with a lantern, glowing jack-o'-lanterns, mist, stars and a circling bat |
| Spider Web | white webs on a purple ball, with two spiders |
| Mummy | a ball wrapped in bandages, with two eyes peeking out |
| Candy Corn | yellow, orange and white |

The ghost, the bat and the ghost skull stay upright, face where the ball is going, and fly faster as it speeds up.
The pumpkin, the skull, the mummy's eyes and the big spider start facing the camera.

| Hat | Look |
|---|---|
| Witch Hat | a wide brim, a tall bent cone, a purple band and a gold buckle |
| Jack-o'-Lantern | a carved pumpkin with a glowing face, looking back at the camera |
| Devil Horns | two red horns |
| Bat | a bat hovering and flapping over the ball, looking back at the camera |
| Skull Candle | a skull with three lit candles, looking back at the camera |

## Install

In the game: footer **plugins** > **browse** > Halloween Pack > **install** (Cosmetic Kit comes with it).
Needs the plugin manager host 0.17.1 or newer.

## Credits

All the models are CC0 (public domain):

- [KayKit: Halloween Bits](https://kaylousberg.itch.io/halloween-bits) by Kay Lousberg: the jack-o'-lantern (recoloured
  orange here), the skull, the skull candle, the two graves and the dead tree.
- [Quaternius](https://quaternius.com): the ghost, the ghost skull and the bat (recoloured here).

Downloaded from [Poly Pizza](https://poly.pizza).

## Files

- `main.as`: adds the balls and hats.
- `models/`: the model files (the format is in the plugin manager's
  [custom cosmetics guide](https://anythinggoes-ballest.github.io/ballest-plugin-manager/guides/cosmetics/)) and the
  3D models they use.
- `textures/`, `previews/`, `icon.png`, the model text files, and the recoloured `jackolantern_orange.glb`, `ghost.glb`,
  `ghost_skull.glb` and `bat.glb` are made by `make_pack.py` (Python with NumPy and Pillow) from `sources/` and the
  models. `bubbles.glb` is Fish Bowl's (a rising-bubbles animation made by its `make_bowl.py`).

## License

MIT for this plugin's code and files; the models keep their CC0 licence.
