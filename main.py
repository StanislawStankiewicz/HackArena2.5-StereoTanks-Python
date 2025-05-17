import datetime
import time
import random

from action_state import ActionState


from hackathon_bot import *


class BaseBot(StereoTanksBot):

    def __init__(self):
        super().__init__()
        self.grid_dimension = None
        self.teamname = None
        self.bot = None
        self.tank: Tank
        self.teammate_tank: Tank = None
        self.id: str
        self.turret_direction: Direction = None
        self.hull_direction: Direction = None
        self.x: int = None
        self.y: int = None
        self.action_state: int = ActionState.GO_TO_ZONE

        self.mine_tiles = []
        self.penalties = GoTo.Penalties(
        mine=100,
        laser=10000,
        blindly=10,
        # per_tile=self.mine_tiles
    )

    def on_lobby_data_received(self, lobby_data: LobbyData) -> None:
        is_light = self._is_light_tank(lobby_data)
        self.grid_dimension = lobby_data.server_settings.grid_dimension
        self.teamname = self._get_team_name(lobby_data)
        if self._is_light_tank(lobby_data):
            from light_bot import LightBot
            self.bot = LightBot(self.teamname, self.grid_dimension)
        else:
            from heavy_bot import HeavyBot
            self.bot = HeavyBot(self.teamname, self.grid_dimension)

    def next_move(self, game_state: GameState) -> ResponseAction:
        my_tank = self._find_my_tank(game_state)
        if my_tank is None:
            return Pass()
        self._update_state(game_state)

        if self.bot:
            move = self.bot.next_move(game_state)
            if move is None:
                return self._get_random_action()
            return move
        return self._get_random_action()

    def _update_state(self, game_state: GameState) -> None:
        tank = self._find_my_tank(game_state)
        self.tank = tank
        self.teammate_tank = self._find_teammate_tank(game_state)
        self.turret_direction = tank.turret.direction
        self.hull_direction = tank.direction
        self.bullet_count = tank.turret.bullet_count
        coords = self.get_my_coords(game_state)
        if coords:
            self.x, self.y = coords

        if self.teammate_tank is not None:
            team_mate_coords = self.get_teammate_coords(game_state)
            if team_mate_coords:
                self.teammate_x, self.teammate_y = team_mate_coords
        else:
            self.teammate_x, self.teammate_y = None,None

    def on_game_ended(self, game_result: GameResult) -> None:
        print(f"Game ended: {game_result}")

    def on_warning_received(self, warning: WarningType, message: str | None) -> None:
        print(f"Warning received: {warning} - {message}")

    def _find_my_tank(self, game_state: GameState) -> Tank | None:
        """Finds the agent in the game state."""
        for row in game_state.map.tiles:
            for tile in row:
                if tile.entities:
                    entity = tile.entities[0]
                    if isinstance(entity, Tank) and entity.owner_id == game_state.my_id:
                        return entity
        return None

    def get_my_coords(self, game_state: GameState) -> (int, int):
        """Returns cords of the agent in the game state as an (x, y) pair."""
        for i in range(len(game_state.map.tiles)):
            for j in range(len(game_state.map.tiles[0])):
                if game_state.map.tiles[i][j].entities:
                    entity = game_state.map.tiles[i][j].entities[0]
                    if isinstance(entity, Tank) and entity.owner_id == game_state.my_id:
                        return j, i
        return None

    def get_teammate_coords(self, game_state: GameState) -> (int,int):
        """Returns cords of the agent's teammate in the game state as an (x, y) pair."""
        team = next(
            t
            for t in game_state.teams
            if any(map(lambda x: x.id == game_state.my_id, t.players))
        )

        teammate = next((p for p in team.players if p.id != game_state.my_id), None)
        if teammate is None:
            return None

        for i in range(len(game_state.map.tiles)):
            for j in range(len(game_state.map.tiles[0])):
                if game_state.map.tiles[i][j].entities:
                    entity = game_state.map.tiles[i][j].entities[0]
                    if isinstance(entity, Tank) and entity.owner_id == teammate.id:
                        return j, i
        return None

    def _is_light_tank(self, lobby_data: LobbyData) -> bool:
        """Checks if the agent is a light tank."""
        for team in lobby_data.teams:
            for player in team.players:
                if player.id == lobby_data.my_id:
                    return player.tank_type == TankType.LIGHT
        return False


    def _find_teammate_tank(self, game_state: GameState) -> Tank | None:
        """Finds the agent in the game state."""

        team = next(
            t
            for t in game_state.teams
            if any(map(lambda x: x.id == game_state.my_id, t.players))
        )

        teammate = next((p for p in team.players if p.id != game_state.my_id), None)

        if teammate is None:
            return None

        for row in game_state.map.tiles:
            for tile in row:
                if tile.entities:
                    entity = tile.entities[0]
                    if isinstance(entity, Tank) and entity.owner_id == teammate.id:
                        return entity
        return None

    def is_enemy_in_clear_line_of_sight(self, game_state: GameState) -> tuple[bool, int]:
        """
        Checks if an enemy tank is in a clear line of sight in the turret's direction.
        Returns a tuple (bool, int) where:
        - First value is True if enemy is in clear line of sight, False otherwise
        - Second value is distance to the enemy (number of tiles) or -1 if no enemy in sight
        """
        direction_map = {
            Direction.LEFT: (-1, 0),
            Direction.RIGHT: (1, 0),
            Direction.UP: (0, -1),
            Direction.DOWN: (0, 1),
        }

        distance_to_enemy = 0
        dx, dy = direction_map[self.turret_direction]
        x, y = self.x + dx, self.y + dy

        while 0 <= x < len(game_state.map.tiles[0]) and 0 <= y < len(game_state.map.tiles):
            distance_to_enemy += 1
            tile = game_state.map.tiles[y][x]

            if tile.entities:
                entity = tile.entities[0]

                # Napotkano przeszkodę
                if isinstance(entity, Wall) and entity.type == WallType.SOLID:
                    return False, -1

                # Napotkano czołg
                if isinstance(entity, Tank):
                    # Sprawdzanie czy to wróg
                    if self._is_tank_enemy(game_state, entity):
                        return True, distance_to_enemy
                    else:
                        # To sojusznik
                        return False, -1

            # Przesuwamy się w kierunku patrzenia wieży
            x += dx
            y += dy

        # Nie znaleziono nic w linii prostej
        return False, -1

    def is_teammate_in_clear_line_of_sight(self, game_state: GameState) -> bool:
        """Checks if an enemy tank is in a clear line of sight in the turret's direction."""
        direction_map = {
            Direction.LEFT: (-1, 0),
            Direction.RIGHT: (1, 0),
            Direction.UP: (0, -1),
            Direction.DOWN: (0, 1),
        }
        dx, dy = direction_map[self.turret_direction]
        x, y = self.x + dx, self.y + dy
        while 0 <= x < len(game_state.map.tiles[0]) and 0 <= y < len(game_state.map.tiles):
            tile = game_state.map.tiles[y][x]
            teammate_tank = self._find_teammate_tank(game_state)
            if tile.entities:
                entity = tile.entities[0]
                if isinstance(entity, Wall) and Wall.type == WallType.SOLID:
                    return False
                if teammate_tank != None and isinstance(entity, Tank) :
                    return entity.owner_id == teammate_tank.owner_id
            x += dx
            y += dy
        return False

    def _get_random_action(self):
        return random.choice(
            [
                GoTo(
                    random.randint(0, self.grid_dimension - 1),
                    random.randint(0, self.grid_dimension - 1),
                    costs=GoTo.Costs(forward=10, backward=1, rotate=1),
                    penalties = self.penalties,
                ),
            ]
        )

    def _is_tank_in_zone(self, game_state: GameState) -> bool:
            my_tank = self._find_my_tank(game_state)
            if not my_tank:
                return False
            for row in game_state.map.tiles:
                for tile in row:
                    if tile.entities and tile.entities[0] == my_tank:
                        return tile.zone is not None
            return False

    def _find_zone(self, game_state: GameState) -> Zone | None:
        """Finds the zone in the game state."""
        for row in game_state.map.tiles:
            for tile in row:
                if tile.zone:
                    return tile.zone
        return None

    def _get_zone_coordinates(self, game_state: GameState):
        """find all tiles that a tank can be on in the zone"""
        tiles = []
        x,y = 0,0
        for row in game_state.map.tiles:
            x=0
            for tile in row:
                if tile.zone:
                    is_good_to_add = True
                    for entity in tile.entities:
                        if isinstance(entity, Wall) or isinstance(entity, Mine):
                            is_good_to_add = False
                    if is_good_to_add:
                        tiles.append((x, y))
                x += 1
            y+= 1
        return tiles

    def _is_enemy_in_zone(self, game_state: GameState) -> bool:
        """Checks if an enemy tank is in the zone."""
        for row in game_state.map.tiles:
            for tile in row:
                if tile.zone and tile.entities:
                    for entity in tile.entities:
                        if isinstance(entity, Tank) and (entity.owner_id != game_state.my_id or (self.teammate_tank is not None and entity.owner_id != self.teammate_tank.owner_id)):
                            return True


        return False

    def _is_my_tank_in_zone(self, game_state: GameState) -> bool:
        """Checks if my tank is in the zone."""
        for row in game_state.map.tiles:
            for tile in row:
                if tile.zone and tile.entities:
                    for entity in tile.entities:
                        if isinstance(entity, Tank) and entity.owner_id == game_state.my_id:
                            return True
        return False

    def _goto_zone(self, game_state: GameState, ofset=0):
        """go to the zone"""
        coords = self._get_zone_coordinates(game_state)[int(time.time()) % len(self._get_zone_coordinates(game_state))]

        return GoTo(coords[0], coords[1], penalties=self.penalties)

    def _is_zone_ours(self, game_state: GameState) -> bool:
        zone = self._find_zone(game_state)
        if self.teamname in zone.shares:
            return zone.shares[self.teamname] > 0.90
        else:
            return False

    def _get_team_name(self, lobby_data: LobbyData) -> str:
        """Returns the name of the team."""
        for team in lobby_data.teams:
            for player in team.players:
                if player.id == lobby_data.my_id:
                    return team.name
        return None



    def _find_enemies(self, game_state: GameState) -> list[Tank]:
        """choose an enemy to attack"""
        enemies = []
        for row in game_state.map.tiles:
            for tile in row:
                if tile.entities:
                    for entity in tile.entities:
                        if isinstance(entity, Tank) and self._is_tank_enemy(game_state, entity):
                            enemies.append(entity)

        return enemies

    def _is_tank_enemy(self, game_state: GameState, tank: Tank) -> bool:
        """Checks if the tank is an enemy."""
        is_not_me = tank.owner_id != game_state.my_id
        has_teammate = self.teammate_tank is not None
        is_not_teammate = not has_teammate or tank.owner_id != self.teammate_tank.owner_id
        return is_not_me and is_not_teammate

    def _get_enemy_coordinates(self, game_state: GameState, enemy: Tank):
        """ get coordinates of the enemy"""
        for i in range(len(game_state.map.tiles)):
            for j in range(len(game_state.map.tiles[0])):
                if game_state.map.tiles[i][j].entities:
                    entity = game_state.map.tiles[i][j].entities[0]
                    if isinstance(entity, Tank) and entity.owner_id == enemy.owner_id:
                        return j, i
        return None

    def _choose_enemy(self, game_state: GameState):
        """choose an enemy to attack"""
        enemies = self._find_enemies(game_state)
        if len(enemies) == 0:
            return None
        else:
            #choose the enemy closest to the zone
            closest_enemy = None
            closest_distance = float("inf")
            zone = self._find_zone(game_state)
            for enemy in enemies:
                coords = self._get_enemy_coordinates(game_state, enemy)
                if coords is None:
                    continue
                distance = abs(coords[0] - zone.x+2) + abs(coords[1] - zone.y+2)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_enemy = enemy
            return closest_enemy

    def _move_to_enemy(self, game_state: GameState):
        """move to the enemy"""
        enemy = self._choose_enemy(game_state)
        if enemy is None:
            return None
        coords = self._get_enemy_coordinates(game_state, enemy)
        if coords is None:
            return None
        # always turn in the direction of the enemy
        enemy_direction = None
        dx = coords[0] - self.x
        dy = coords[1] - self.y
        if abs(dx) > abs(dy):
            if dx > 0:
                enemy_direction = Direction.RIGHT
            else:
                enemy_direction = Direction.LEFT
        else:
            if dy > 0:
                enemy_direction = Direction.DOWN
            else:
                enemy_direction = Direction.UP
        if enemy_direction != self.turret_direction:
            if enemy_direction == Direction.LEFT:
                return Rotation(None,RotationDirection.LEFT)
            elif enemy_direction == Direction.RIGHT:
                return Rotation(None, RotationDirection.RIGHT)
            elif enemy_direction == Direction.UP:
                return Rotation(None, RotationDirection.RIGHT)
            elif enemy_direction == Direction.DOWN:
                return Rotation(None, RotationDirection.LEFT)
        return GoTo(coords[0], coords[1], penalties=self.penalties)


if __name__ == "__main__":
    bot = BaseBot()
    bot.run()
