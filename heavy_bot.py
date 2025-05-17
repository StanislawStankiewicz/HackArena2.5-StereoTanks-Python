import random

from action_state import ActionState
from hackathon_bot import GoTo, GameState, ResponseAction, Wall, Mine, AbilityUse, Ability, CaptureZone
from main import BaseBot


class HeavyBot(BaseBot):

    def __init__(self, teamname: str, grid_dimension: int):
        super().__init__()
        self.teamname = teamname
        self.grid_dimension = grid_dimension
        self.bullet_count = 0
        self.max_bullets = 3
        self.bullet_cd = 10
        self.laser_cd = 400
        self.mine_cd = 100
        self.stun_cd = 200
        self.heal_cd = 50
        self.tick = 0
        self.lux_protocol = False

        self.mine_tiles = []
        self.penalties = GoTo.Penalties(
            mine=100,
            laser=10000,
            blindly=10,
        )

    def _update_cds(self):
        self.tick += 1
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

        if self.is_teammate_in_clear_line_of_sight(game_state) and self.heal_cd == 0:
            self.heal_cd = 50
            return AbilityUse(Ability.FIRE_HEALING_BULLET)

        for _ in range(10):
            if self.lux_protocol:
                self.lux_protocol = False
                self.laser_cd = 400
                return AbilityUse(Ability.USE_LASER)

            if (
                    self.mine_cd == 0
                    and self.action_state != ActionState.CAPTURING
                    and self._is_mine_suitable(game_state)
            ):
                self.mine_cd = 100
                return AbilityUse(Ability.DROP_MINE)

            if self.action_state == ActionState.GO_TO_ZONE:
                if self._is_enemy_in_zone(game_state):
                    self.action_state = ActionState.ATTACK
                elif (
                        self._is_my_tank_in_zone(game_state)
                        and not self._is_zone_ours(game_state)
                        and not self.tick % 10 < 2
                ):
                    self.action_state = ActionState.CAPTURING
                return self._goto_zone(game_state, 10)


            if self.action_state == ActionState.CAPTURING:
                if self._find_enemies(game_state):
                    self.action_state = ActionState.ATTACK
                elif not self._is_my_tank_in_zone(game_state) or self._is_zone_ours(game_state) or self.tick % 10 < 2:
                    self.action_state = ActionState.GO_TO_ZONE
                else:
                    return CaptureZone()

            if self.action_state == ActionState.ATTACK:
                enemies = self._find_enemies(game_state)
                if not enemies and not self._is_my_tank_in_zone(game_state):
                    self.action_state = ActionState.GO_TO_ZONE
                else:
                    in_sight, distance = self.is_enemy_in_clear_line_of_sight(game_state)
                    if in_sight:
                        if self.can_shoot():
                            return self.shoot()
                        else:
                            return self._get_random_strafe(game_state)
                    else:
                        ret = self._move_to_enemy(game_state)
                        if ret is None:
                            self.action_state = ActionState.GO_TO_ZONE
                        else:
                            return ret
        self.action_state = ActionState.GO_TO_ZONE
        return self._goto_zone(game_state, 10)

    def _get_random_strafe(self, game_state):
        """Move to the nearest corner relative to the enemy position"""
        enemies = self._find_enemies(game_state)
        if not enemies:
            return None

        enemy = enemies[0]
        enemy_coords = self._get_enemy_coordinates(game_state, enemy)
        if not enemy_coords:
            return None

        ex, ey = enemy_coords
        tx, ty = self.x, self.y

        # Calculate relative position to enemy
        dx = 1 if tx < ex else -1  # Move away horizontally
        dy = 1 if ty < ey else -1  # Move away vertically

        # Choose either horizontal or vertical movement to the corner
        if abs(tx - ex) < abs(ty - ey):
            return GoTo(tx + dx, ty)
        else:
            return GoTo(tx, ty + dy)

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

    def can_shoot(self):
        if self.laser_cd == 0:
            return True
        elif self.stun_cd == 0:
            return True
        elif self.bullet_count > 0:
            return True
        return False

    def _is_mine_suitable(self, game_state) -> bool:
        """Returns True if the current tank position is in a corridor in the hull direction."""
        x, y = self.x, self.y
        tiles = game_state.map.tiles
        width = len(tiles[0])
        height = len(tiles)

        def is_blocked(nx, ny):
            if not (0 <= nx < width and 0 <= ny < height):
                return True
            tile = tiles[ny][nx]
            return tile.entities and any(isinstance(e, Wall) or isinstance(e, Mine) for e in tile.entities)

        # Direction vectors: (dx, dy)
        direction_map = {
            "UP": (0, -1),
            "DOWN": (0, 1),
            "LEFT": (-1, 0),
            "RIGHT": (1, 0),
        }
        dx, dy = direction_map[self.hull_direction.name]

        # Check if blocked on both sides perpendicular to hull direction, and open in hull direction
        if dx != 0:  # Facing LEFT or RIGHT
            if is_blocked(x, y - 1) and is_blocked(x, y + 1) and not is_blocked(x + dx, y):
                return True
        if dy != 0:  # Facing UP or DOWN
            if is_blocked(x - 1, y) and is_blocked(x + 1, y) and not is_blocked(x, y + dy):
                return True

        return False
