from hackathon_bot import GoTo, GameState, ResponseAction
from main import BaseBot


class LightBot(BaseBot):

    def __init__(self, teamname: str):
        super().__init__()
        self.teamname = teamname
        self.bullet_cd = 10
        self.double_cd = 60
        self.radar_cd = 200
        self.stun_cd = 200
        self.heal_cd = 50

    def _update_cds(self):
        if self.bullet_cd > 0:
            self.bullet_cd -= 1
        if self.double_cd > 0:
            self.double_cd -= 1
        if self.radar_cd > 0:
            self.radar_cd -= 1
        if self.stun_cd > 0:
            self.stun_cd -= 1
        if self.heal_cd > 0:
            self.heal_cd -= 1

    def next_move(self, game_state: GameState) -> ResponseAction:
        self._update_state(game_state)
        self._update_cds()
        return self._get_random_action()