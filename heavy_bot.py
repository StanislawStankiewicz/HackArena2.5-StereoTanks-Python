from action_state import ActionState
from hackathon_bot import GoTo, GameState, ResponseAction, Wall, Mine, AbilityUse, Ability, CaptureZone
from main import BaseBot


class HeavyBot(BaseBot):

    def __init__(self, teamname: str):
        super().__init__()
        self.teamname = teamname
        self.bullet_count = 0
        self.max_bullets = 3
        self.bullet_cd = 10
        self.laser_cd = 400
        self.mine_cd = 100
        self.stun_cd = 200
        self.heal_cd = 50
        self.lux_protocol = False

    def _update_cds(self):
        if self.bullet_cd > 0:
            self.bullet_cd -= 1
        if self.laser_cd > 0:
            self.laser_cd -= 1
        if self.mine_cd > 0:
            self.mine_cd -= 1
        if self.stun_cd > 0:
            self.stun_cd -= 1
        if self.heal_cd > 0:
            self.heal_cd -= 1
        if self.bullet_cd == 0 and self.bullet_count < self.max_bullets:
            self.bullet_count += 1
            self.bullet_cd = 10

    def next_move(self, game_state: GameState) -> ResponseAction:
        self._update_cds()
        self._update_state(game_state)

        if self.lux_protocol:
            self.lux_protocol = False
            self.laser_cd = 400
            return AbilityUse(Ability.USE_LASER)
        if self.mine_cd == 0 and self.action_state != ActionState.CAPTURING and self._is_mine_suitable(game_state):
            self.mine_cd = 100
            return AbilityUse(Ability.DROP_MINE)
        # print("is enemy in zone: ", self._is_enemy_in_zone(game_state)[0])
        if self.action_state == ActionState.GO_TO_ZONE:
            """Go to zone
            if in zone and no players in zone capture else attack"""
            if self._is_enemy_in_zone(game_state):
                self.action_state = ActionState.ATTACK
            elif self._is_my_tank_in_zone(game_state) and not self._is_zone_ours(game_state): #TODO check if zone captured
                self.action_state = ActionState.CAPTURING

            return self._goto_zone(game_state)

        elif self.action_state == ActionState.CAPTURING: # TODO Stop when captured
            """Capture zone"""
            if self._is_enemy_in_zone(game_state):
                self.action_state = ActionState.ATTACK
            elif not self._is_my_tank_in_zone(game_state):
                self.action_state = ActionState.GO_TO_ZONE
            else:
                return CaptureZone()

        elif self.action_state == ActionState.ATTACK:
            if not self._find_enemies(game_state):
                self.action_state = ActionState.GO_TO_ZONE
                return self._goto_zone(game_state)
            if self.is_enemy_in_clear_line_of_sight(game_state)[0]:
                action = self.shoot()
                if action is not None:
                    return action
            return self._move_to_enemy(game_state)

        return self._get_random_action()

    def shoot(self):
        if self.laser_cd == 0 and self.stun_cd == 0:
            self.lux_protocol = True
            self.stun_cd = 200
            return AbilityUse(Ability.FIRE_STUN_BULLET)
        elif self.stun_cd == 0:
            self.stun_cd = 200
            return AbilityUse(Ability.FIRE_STUN_BULLET)
        elif self.bullet_count > 0:
            self.bullet_count -= 1
            self.bullet_cd = 10
            return AbilityUse(Ability.FIRE_BULLET)
        return None



    def _is_mine_suitable(self, game_state) -> bool:
        """Returns True if the current tank position is in a corridor (straight or diagonal)."""
        x, y = self.x, self.y
        tiles = game_state.map.tiles
        width = len(tiles[0])
        height = len(tiles)

        def is_blocked(nx, ny):
            if not (0 <= nx < width and 0 <= ny < height):
                return True
            tile = tiles[ny][nx]
            return tile.entities and any(isinstance(e, Wall) or isinstance(e, Mine) for e in tile.entities)

        # Check straight corridors
        if is_blocked(x - 1, y) and is_blocked(x + 1, y) and not is_blocked(x, y - 1) and not is_blocked(x, y + 1):
            return True  # Horizontal corridor
        if is_blocked(x, y - 1) and is_blocked(x, y + 1) and not is_blocked(x - 1, y) and not is_blocked(x + 1, y):
            return True  # Vertical corridor

        # Check diagonal corridors
        if is_blocked(x - 1, y - 1) and is_blocked(x + 1, y + 1) and not is_blocked(x - 1, y + 1) and not is_blocked(
                x + 1, y - 1):
            return True
        if is_blocked(x - 1, y + 1) and is_blocked(x + 1, y - 1) and not is_blocked(x - 1, y - 1) and not is_blocked(
                x + 1, y + 1):
            return True

        return False