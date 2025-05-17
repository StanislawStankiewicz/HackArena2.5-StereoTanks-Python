"""This is an example of a bot participating in the HackArena 2.5.

This bot will randomly move around the map,
use abilities and print the map to the console.
"""

import os
import random

from hackathon_bot import *


class ExampleBot(StereoTanksBot):

    grid_dimension: int

    def on_lobby_data_received(self, lobby_data: LobbyData) -> None:
        print(f"Lobby data received: {lobby_data}")
        self.grid_dimension = lobby_data.server_settings.grid_dimension

    def next_move(self, game_state: GameState) -> ResponseAction:
        my_tank = self._find_my_tank(game_state)
        teammate_tank = self._find_teammate_tank(game_state)

        self._print_map(game_state.map, my_tank, teammate_tank)

        # Check if my tank is dead
        if my_tank is None:
            # Return pass to avoid warnings from the server
            # when the bot tries to make an action with a dead tank
            return Pass()

        return self._get_random_action()

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

    def _get_random_action(self):
        return random.choice(
            [
                Movement(MovementDirection.FORWARD),
                Movement(MovementDirection.BACKWARD),
                Rotation(RotationDirection.LEFT, RotationDirection.LEFT),
                Rotation(RotationDirection.LEFT, RotationDirection.RIGHT),
                Rotation(RotationDirection.LEFT, None),
                Rotation(RotationDirection.RIGHT, RotationDirection.LEFT),
                Rotation(RotationDirection.RIGHT, RotationDirection.RIGHT),
                Rotation(RotationDirection.RIGHT, None),
                Rotation(None, RotationDirection.LEFT),
                Rotation(None, RotationDirection.RIGHT),
                Rotation(None, None),  # Useless, better use Pass()
                AbilityUse(Ability.FIRE_BULLET),
                AbilityUse(Ability.FIRE_DOUBLE_BULLET),
                AbilityUse(Ability.USE_LASER),
                AbilityUse(Ability.USE_RADAR),
                AbilityUse(Ability.DROP_MINE),
                AbilityUse(Ability.FIRE_HEALING_BULLET),
                AbilityUse(Ability.FIRE_STUN_BULLET),
                CaptureZone(),
                GoTo(
                    random.randint(0, self.grid_dimension - 1),
                    random.randint(0, self.grid_dimension - 1),
                ),
                GoTo(
                    random.randint(0, self.grid_dimension - 1),
                    random.randint(0, self.grid_dimension - 1),
                    costs=GoTo.Costs(forward=10, backward=1, rotate=1),
                    penalties=GoTo.Penalties(
                        mine=-5,
                        laser=1,
                        blindly=-1,
                        per_tile=[
                            GoTo.Penalties.PerTile(x=5, y=5, penalty=100),
                        ],
                    ),
                ),
                Pass(),
            ]
        )

    def _print_map(
        self, game_map: Map, my_tank: Tank | None, teammate_tank: Tank | None
    ):
        os.system("cls" if os.name == "nt" else "clear")
        end = " "

        for y, row in enumerate(game_map.tiles):
            for x, tile in enumerate(row):
                entity = tile.entities[0] if tile.entities else None

                is_visible_by_my_tank = (
                    my_tank and my_tank.visibility and my_tank.visibility[y][x]
                )
                is_visible_by_teammate_tank = (
                    teammate_tank
                    and teammate_tank.visibility
                    and teammate_tank.visibility[y][x]
                )
                is_visible = is_visible_by_my_tank or is_visible_by_teammate_tank

                if isinstance(entity, Wall):
                    print("#" if entity.type is WallType.SOLID else "%", end=end)
                elif isinstance(entity, Laser):
                    if entity.orientation is Orientation.HORIZONTAL:
                        print("|", end=end)
                    elif entity.orientation is Orientation.VERTICAL:
                        print("-", end=end)
                elif isinstance(entity, Bullet):
                    if entity.direction is Direction.UP:
                        print("⇈" if entity.type is BulletType.DOUBLE else "↑", end=end)
                    elif entity.direction is Direction.RIGHT:
                        print("⇉" if entity.type is BulletType.DOUBLE else "→", end=end)
                    elif entity.direction is Direction.DOWN:
                        print("⇊" if entity.type is BulletType.DOUBLE else "↓", end=end)
                    elif entity.direction is Direction.LEFT:
                        print("⇇" if entity.type is BulletType.DOUBLE else "←", end=end)
                elif isinstance(entity, Tank):
                    if entity == my_tank:
                        print("M", end=end)
                    elif entity == teammate_tank:
                        print("T", end=end)
                    else:
                        print("P", end=end)
                elif isinstance(entity, Mine):
                    print("x" if entity.exploded else "X", end=end)
                elif tile.zone:
                    index = chr(tile.zone.index)
                    index = index.upper() if is_visible else index.lower()
                    print(index, end=end)
                elif is_visible:
                    print(".", end=end)
                else:
                    print(" ", end=end)
            print()


if __name__ == "__main__":
    bot = ExampleBot()
    bot.run()
