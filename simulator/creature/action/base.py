import abc
import enum
import random
from typing import TYPE_CHECKING, Type

from core.mixin import ApplyDescriptorMixin, GetSubclassesMixin
from core.service import ObjectDescriptionReader
from evolution import settings


if TYPE_CHECKING:
    from simulator.creature import SimulationCreature

action_descriptors = ObjectDescriptionReader[dict]().read_folder_to_dict(
    settings.ACTION_DESCRIPTIONS_PATH,
    dict
)


class ActionInterface(GetSubclassesMixin["ActionInterface"], ApplyDescriptorMixin, abc.ABC):
    class Type(enum.Enum):
        WAIT = 0
        CONSUME = 1
        REGENERATE = 2
        REPRODUCE = 3

    name = "action_interface"
    # ожидаемая длительность действия
    estimated_duration: int
    duration_coeff: float
    # относительный вес при выборе следующего действия
    base_weight: float
    _stop_tick = None
    _duration = None

    def __init__(self, creature: "SimulationCreature") -> None:
        self.creature = creature
        self.world = self.creature.world

        # действие выбирается в момент окончания предыдущего
        self.start_tick = self.world.age + 1
        # todo: добавить коэффициент длительности действия из генома (например завязать на действие метаболизма)
        # длительность действия не может быть меньше 1 тика
        self._estimated_duration = max(int(self.estimated_duration * self.duration_coeff), 1)
        # момент ожидаемого окончания действия
        self.estimated_stop_tick = self.start_tick + self._estimated_duration
        self.world.active_creatures[self.estimated_stop_tick][self.creature.id] = self.creature

        self.aborted = False
        self.type = ACTION_CLASS_TO_TYPE[self.__class__]

    def __repr__(self) -> str:
        return f"{self.name}: {self.duration}"

    @staticmethod
    def get_wait_action(creature: "SimulationCreature") -> "WaitAction":
        # noinspection PyTypeChecker
        return ACTION_CLASSES["wait_action"](creature)

    @classmethod
    def get_next_action(cls, creature: "SimulationCreature") -> "ActionInterface":
        action_list: list[ActionInterface] = []
        if creature.can_consume():
            action_list.append(ACTION_CLASSES[ConsumeAction.name])
        if creature.can_regenerate():
            action_list.append(ACTION_CLASSES[RegenerateAction.name])
        if creature.can_reproduce():
            action_list.append(ACTION_CLASSES[ReproduceAction.name])

        weights = [x.get_weight(creature) for x in action_list]
        if sum(weights) > 0:
            next_action = random.choices(action_list, weights, k = 1)[0](creature)
        else:
            next_action = WaitAction(creature)
        return next_action

    @property
    def stop_tick(self) -> int:
        if self.aborted:
            stop_tick = self._stop_tick
        else:
            stop_tick = self.estimated_stop_tick
        return stop_tick

    @property
    def duration(self) -> int:
        if self.aborted:
            duration = self._duration
        else:
            duration = self._estimated_duration
        return duration

    def abort(self) -> None:
        """Досрочно прерывает действие."""

        self.aborted = True
        self._stop_tick = self.creature.world
        self._duration = self.world.age - self.start_tick
        del self.world.active_creatures[self.stop_tick][self.creature.id]

    @classmethod
    def get_weight(cls, creature: "SimulationCreature") -> float:
        # todo: реализовать изменение веса из-за влияния генов и других факторов
        return cls.base_weight


class WaitAction(ActionInterface):
    name = "wait_action"


class ConsumeAction(ActionInterface):
    name = "consume_action"


class RegenerateAction(ActionInterface):
    name = "regenerate_action"


class ReproduceAction(ActionInterface):
    name = "reproduce_action"


ActionInterface.apply_descriptor(action_descriptors[ActionInterface.name])
ACTION_CLASSES = {x.name: x for x in ActionInterface.get_all_subclasses()}
# обновляются данные в классах действий
for name, action_class in ACTION_CLASSES.items():
    action_class.apply_descriptor(action_descriptors[name])

ACTION_CLASS_TO_TYPE: dict[Type[ActionInterface], ActionInterface.Type] = {
    WaitAction: ActionInterface.Type.WAIT,
    ConsumeAction: ActionInterface.Type.CONSUME,
    RegenerateAction: ActionInterface.Type.REGENERATE,
    ReproduceAction: ActionInterface.Type.REPRODUCE
}
