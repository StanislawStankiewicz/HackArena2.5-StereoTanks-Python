from enum import EnumType


class ActionState(EnumType):
    CAPTURING = 0
    GO_TO_ZONE = 1
    ATTACK = 2
    ROAMING = 3
    HEALING = 4