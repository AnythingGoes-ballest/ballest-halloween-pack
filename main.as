// Halloween Pack: ten balls and five hats on the Customize page, through Cosmetic Kit (a dependency: see info.toml).
// The models are CC0 (KayKit Halloween Bits by Kay Lousberg, and Quaternius); the textures, the brew, the witch's hat
// and the devil horns are made by make_pack.py.

import bool AddBall(const string &in, const string &in, const string &in, const string &in, const string &in) from "cosmetic-kit";
import bool AddHat(const string &in, const string &in, const string &in, double, const string &in, const string &in) from "cosmetic-kit";

void Main()
{
    string f = Plugins::Folder();
    string p = f + "previews/", m = f + "models/", t = f + "textures/";
    // balls: a texture (or "" for clear glass), a tile picture, a model ("" for none)
    AddBall("halloween-pack.pumpkin", "Pumpkin", t + "orange.png", p + "pumpkin.png", m + "pumpkin_ball.txt");
    AddBall("halloween-pack.skull", "Skull", t + "bone.png", p + "skull.png", m + "skull_ball.txt");
    AddBall("halloween-pack.ghost", "Ghost", "", p + "ghost.png", m + "ghost_ball.txt");
    AddBall("halloween-pack.bat", "Bat", "", p + "bat.png", m + "bat_ball.txt");
    AddBall("halloween-pack.ghost-skull", "Ghost Skull", "", p + "ghost_skull.png", m + "ghost_skull_ball.txt");
    AddBall("halloween-pack.witchs-brew", "Witch's Brew", "", p + "brew.png", m + "brew_ball.txt");
    AddBall("halloween-pack.graveyard", "Graveyard Globe", "", p + "graveyard.png", m + "graveyard_ball.txt");
    AddBall("halloween-pack.spider-web", "Spider Web", t + "spider_web.png", p + "spider_web.png", "");
    AddBall("halloween-pack.mummy", "Mummy", t + "mummy.png", p + "mummy.png", "");
    AddBall("halloween-pack.candy-corn", "Candy Corn", t + "candy_corn.png", p + "candy_corn.png", "");
    // hats: no mesh of the game's, size 1, a tile picture, a model
    AddHat("halloween-pack.witch-hat", "Witch Hat", "", 1.0, p + "witch_hat.png", m + "witch_hat.txt");
    AddHat("halloween-pack.jack-o-lantern", "Jack-o'-Lantern", "", 1.0, p + "jackolantern_hat.png", m + "jackolantern_hat.txt");
    AddHat("halloween-pack.devil-horns", "Devil Horns", "", 1.0, p + "devil_horns.png", m + "devil_horns.txt");
    AddHat("halloween-pack.bat-hat", "Bat", "", 1.0, p + "bat_hat.png", m + "bat_hat.txt");
    AddHat("halloween-pack.skull-candle", "Skull Candle", "", 1.0, p + "skull_candle_hat.png", m + "skull_candle_hat.txt");
}
