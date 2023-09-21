import abc
import enum
import random
from typing import Callable, TYPE_CHECKING, Type

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
    _can_perform: Callable[["SimulationCreature"], bool] = None

    def __init__(self, creature: "SimulationCreature") -> None:
        self.creature = creature
        self.world = self.creature.world
        # длительность действия накопленная из-за округлений предыдущих действий (всегда должна быть < 1)
        if creature.action is None:
            self.duration_accumulated = 0
        else:
            self.duration_accumulated = self.creature.action.duration_accumulated
        # действие выбирается в момент окончания предыдущего, а начинается лишь в следующий тик
        self.start_tick = self.world.age + 1

        self.aborted = False
        self._stop_tick: int | None = None
        self._estimated_duration: int | None = None
        # момент ожидаемого окончания действия
        self.estimated_stop_tick: int | None = None
        # устанавливается, если действие было прервано
        self.aborted_duration = None
        self.type = ACTION_CLASS_TO_TYPE[self.__class__]

        self.prepare()
        self.estimated_stop_tick = self.start_tick + self.duration
        self.world.active_creatures[self.estimated_stop_tick][self.creature.id] = self.creature

    def __repr__(self) -> str:
        return f"{self.name}: {self.duration}"

    @staticmethod
    def get_wait_action(creature: "SimulationCreature") -> "WaitAction":
        # noinspection PyTypeChecker
        return ACTION_CLASSES["wait_action"](creature)

    @classmethod
    def can_perform(cls, creature: "SimulationCreature") -> bool:
        if cls._can_perform is None:
            method_name = f"can_{'_'.join(cls.name.split('_')[:-1])}"
            cls._can_perform = getattr(creature.__class__, method_name)
        return cls._can_perform(creature)

    @classmethod
    def get_next_action(cls, creature: "SimulationCreature") -> "ActionInterface":
        actions = {action: weight for action in ACTION_CLASSES.values()
                   if (weight := action.get_weight(creature)) > 0 and action.can_perform(creature)}

        if len(actions) > 0:
            next_action = random.choices(list(actions), list(actions.values()))[0](creature)
        else:
            next_action = cls.get_wait_action(creature)
        return next_action

    def prepare(self) -> None:
        # todo: добавить коэффициент длительности действия из генома (например завязать на действие метаболизма)
        # длительность действия не может быть меньше 1 тика
        estimated_duration = self.estimated_duration * self.duration_coeff + self.duration_accumulated
        self._estimated_duration = max(int(estimated_duration), 1)
        if self._estimated_duration == 1:
            self.duration_accumulated = 0
        else:
            self.duration_accumulated = estimated_duration % 1

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
            duration = self.aborted_duration
        else:
            duration = self._estimated_duration
        return duration

    def abort(self) -> None:
        """Досрочно прерывает действие."""

        self.aborted = True
        self._stop_tick = self.creature.world
        self.aborted_duration = self.world.age - self.start_tick
        del self.world.active_creatures[self.stop_tick][self.creature.id]

    @classmethod
    def get_weight(cls, creature: "SimulationCreature") -> float:
        # todo: реализовать изменение веса из-за влияния других факторов
        return cls.base_weight * creature.genome.effects.action_weights[cls.name]


class WaitAction(ActionInterface):
    name = "wait_action"


class ConsumeAction(ActionInterface):
    name = "consume_action"

    def prepare(self) -> None:
        resource_durations = (
            self.creature.storage.available_space[resource] / self.creature.consumption_amount[resource]
            for resource in (x for x in self.creature.storage.available_space
                             if not x.is_energy and self.creature.consumption_amount[x] > 0)
        )
        estimated_duration = min(
            *resource_durations,
            self.estimated_duration * self.duration_coeff
        ) + self.duration_accumulated

        # длительность действия не может быть меньше 1 тика
        self._estimated_duration = max(int(estimated_duration), 1)
        if self._estimated_duration == 1:
            self.duration_accumulated = 0
        else:
            self.duration_accumulated = estimated_duration % 1


class RegenerateAction(ActionInterface):
    name = "regenerate_action"

    def prepare(self) -> None:
        resource_durations = (
            amount / self.creature.genome.effects.regeneration_amount
            for resource, amount in self.creature.regenerating_bodypart.damage.items() if amount > 0
        )
        estimated_duration = min(
            *resource_durations,
            self.estimated_duration * self.duration_coeff
        ) + self.duration_accumulated

        # длительность действия не может быть меньше 1 тика
        self._estimated_duration = max(int(estimated_duration), 1)
        if self._estimated_duration == 1:
            self.duration_accumulated = 0
        else:
            self.duration_accumulated = estimated_duration % 1


class ReproduceAction(ActionInterface):
    name = "reproduce_action"


ActionInterface.apply_descriptor(action_descriptors[ActionInterface.name])
ACTION_CLASSES: dict[str, Type[ActionInterface]] = {x.name: x for x in ActionInterface.get_all_subclasses()}
# обновляются данные в классах действий
for name, action_class in ACTION_CLASSES.items():
    action_class.apply_descriptor(action_descriptors[name])

ACTION_CLASS_TO_TYPE: dict[Type[ActionInterface], ActionInterface.Type] = {
    WaitAction: ActionInterface.Type.WAIT,
    ConsumeAction: ActionInterface.Type.CONSUME,
    RegenerateAction: ActionInterface.Type.REGENERATE,
    ReproduceAction: ActionInterface.Type.REPRODUCE
}
