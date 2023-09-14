import abc

from core.mixin import ApplyDescriptorMixin, GetSubclassesMixin
from core.service import ObjectDescriptionReader
from evolution import settings


action_descriptors = ObjectDescriptionReader[dict]().read_folder_to_dict(
    settings.ACTION_DESCRIPTIONS_PATH,
    dict
)


class ActionInterface(GetSubclassesMixin["ActionInterface"], ApplyDescriptorMixin, abc.ABC):
    name = "action_interface"
    duration: int
    # относительный вес при выборе следующего действия
    base_weight: float

    def __init__(self, world_age: int) -> None:
        self.stop_tick = world_age + self.duration + 1

    def __repr__(self) -> str:
        return f"{self.name}: {self.duration}"

    @staticmethod
    def get_wait_action(world_age: int) -> "WaitAction":
        # noinspection PyTypeChecker
        return ACTION_CLASSES["wait_action"](world_age)

    @classmethod
    def get_next_action(cls, world_age: int) -> "ActionInterface":
        # todo: write it
        return cls.get_wait_action(world_age)


class WaitAction(ActionInterface):
    name = "wait_action"


class ConsumeAction(ActionInterface):
    name = "consume_action"


ActionInterface.apply_descriptor(action_descriptors[ActionInterface.name])
ACTION_CLASSES = {x.name: x for x in ActionInterface.get_all_subclasses()}
# обновляются данные в классах действий
for name, action_class in ACTION_CLASSES.items():
    action_class.apply_descriptor(action_descriptors[name])
