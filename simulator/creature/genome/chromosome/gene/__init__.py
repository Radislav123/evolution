import abc
import random
from typing import Generic, Literal, TYPE_CHECKING, Type, TypeVar

from core.mixin import ApplyDescriptorMixin, GetSubclassesMixin
from core.service import ObjectDescriptionReader
from evolution import settings
from simulator.world_resource import RESOURCE_DICT


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.creature.genome import Genome

# step type
ST = TypeVar("ST", int, float)

gene_interface_descriptors = ObjectDescriptionReader[dict]().read_folder_to_dict(
    settings.GENE_INTERFACE_DESCRIPTIONS_PATH,
    dict
)
gene_descriptors = ObjectDescriptionReader[dict]().read_folder_to_dict(
    settings.GENE_DESCRIPTIONS_PATH,
    dict
)


# todo: если пропадает ген, который необходим для других генов, делать эти гены неактивными
# todo: если появляется ген, которому необходим ген, которого еще нет, делать появившийся ген неактивным
#  (переписать появление генов, уменьшить вероятность появления гена, если в геному отсутствуют необходимые ему гены)
# todo: сделать ResourceStorageGene и ResourceConsumptionGene полностью динамическими?
class GeneInterface(GetSubclassesMixin["GeneInterface"], ApplyDescriptorMixin, abc.ABC):
    name = "gene_interface"
    # название интерфейса, определяющего ген
    interface: str
    # обязательно ли присутствие хотя бы одного такого гена в геноме (могут ли все копии пропасть из генома)
    # и будет ли этот ген у первого существа
    required_for_creature: bool
    # список названий (name) генов, необходимых для активации этого гена
    # необходимые гены не должны быть интерфейсами, так как интерфейсы не могут появиться у существа,
    # значит не будет активен и тот, что содержит в этом списке хотя бы один интерфейс
    required_genes: list[str]
    mutation_chance: float
    base_disappearance_chance: float
    appearance_chance: float
    _required_for_creature_gene_classes: list[Type["GeneInterfaceClass"]] = None
    # количество появлений этого гена
    appearances = 0

    # интерфейсы не должны использовать конструктор
    # не использовать обратные ссылки (gene -> chromosome -> genome),
    # они сильно усложняют код и вызывают проблемы при копировании (а значит и при создании потомков) хромосом и генов
    def __init__(self, first: bool) -> None:
        # first - принадлежит ли ген первому существу
        self.first = first
        # влияет ли ген на существо
        self.active: bool | None = None
        self.__class__.appearances += 1

    def __repr__(self) -> str:
        if self.active is None:
            active = None
        else:
            if self.active:
                active = '+'
            else:
                active = '-'

        return f"{self.__class__.__name__}({active})"

    @classmethod
    def construct_genes(cls, first: bool, gene_classes: list[Type["GeneInterfaceClass"]]) -> list["GeneInterfaceClass"]:
        return [x(first) for x in gene_classes]

    # результат должен вычисляться каждый раз, так как геном мутирует при наследовании
    def get_disappearance_chance(self, genome: "Genome") -> float:
        if not self.can_disappear(genome):
            disappearance_chance = 0
        else:
            disappearance_chance = self.base_disappearance_chance
        return disappearance_chance

    # результат должен вычисляться каждый раз, так как геном мутирует при наследовании
    def can_disappear(self, genome: "Genome") -> bool:
        """Проверяет, может ли ген исчезнуть."""

        return not self.required_for_creature or (self.required_for_creature and genome.gene_counter[self.name] > 1)

    def check_activation(self, genome: "Genome") -> None:
        if len(self.required_genes) > 0:
            condition = genome.contains_all(self.required_genes)
        else:
            condition = True

        if condition:
            self.active = True
        else:
            self.active = False

    @abc.abstractmethod
    def mutate(self, genome: "Genome") -> None:
        """Меняет характеристики гена."""

        raise NotImplementedError()

    @abc.abstractmethod
    def apply(self, genome: "Genome") -> None:
        """Записывает эффекты гена в хранилище."""

        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def correct(cls, genome: "Genome") -> None:
        """Корректирует суммарный эффект генов данного типа после применения каждого по отдельности."""

        raise NotImplementedError()

    @classmethod
    def get_required_for_creature_gene_classes(cls) -> list[Type["GeneInterfaceClass"]]:
        """Возвращает классы генов, необходимые для любого существа."""

        if cls._required_for_creature_gene_classes is None:
            cls._required_for_creature_gene_classes = [x for x in GENE_CLASSES.values() if x.required_for_creature]
        return cls._required_for_creature_gene_classes

    # todo: переделать по "todo" над классом
    @classmethod
    def get_available_gene_classes(cls, genome: "Genome") -> list[Type["GeneInterfaceClass"]]:
        """Возвращает классы генов, возможных для добавления в процессе мутации."""

        return [x for x in GENE_CLASSES_CAN_APPEAR.values()
                if x.appearance_chance > 0 and genome.contains_all(x.required_genes)]


class StepGeneMixin(Generic[ST]):
    # шаг изменения влияния гена
    step: ST
    positive_step: ST
    # число должно быть положительным (см. make_step)
    negative_step: ST
    # минимальное значение влияния гена
    min_limit: ST
    # максимальное значение влияния гена
    max_limit: ST
    # минимальное значение влияния всех таких генов
    common_min_limit: ST
    # максимальное значение влияния всех таких генов
    common_max_limit: ST

    def make_step(self, sign: Literal['+', '-'] = None) -> ST:
        negative_step = self.negative_step if hasattr(self, "negative_step") else self.step
        positive_step = self.positive_step if hasattr(self, "positive_step") else self.step
        if sign is None:
            step = [-negative_step, positive_step][random.randint(0, 1)]
        elif sign == '+':
            step = positive_step
        elif sign == '-':
            step = negative_step
        else:
            raise ValueError(f"sign ({sign}) must be one of {None}, '+' or '-'.")
        return step


class BodypartGeneInterface(StepGeneMixin, GeneInterface):
    """Интерфейс для генов, добавляющих часть тела."""

    name = "bodypart_gene_interface"
    # является ли часть тела уникальной (тело, хранилище) для существа
    # true - у существа будет только одна такая часть тела
    uniq: bool
    bodypart: str
    size_coeff: float
    required_bodypart_gene: str

    def __init__(self, first: bool) -> None:
        super().__init__(first)
        # номер гена части тела (bodypart_gene.number) к которой присоединена эта часть тела
        self.required_gene_number: int | None = None
        # порядковый номер гена этого типа/класса в геноме
        self.number: int | None = None

    def __repr__(self) -> str:
        return f"{super().__repr__()}({self.number}) x{self.size_coeff}"

    def check_activation(self, genome: "Genome") -> None:
        genes = genome.effects.bodyparts_genes
        dependent_genes = genome.effects.dependent_bodypart_genes

        if ((self.required_bodypart_gene in genes and
             self.required_gene_number in genes[self.required_bodypart_gene]) or
                self.name == "body_gene"):
            if len(self.required_genes) > 0:
                condition = genome.contains_all(self.required_genes)
            else:
                condition = True
        else:
            condition = False

        if condition:
            self.active = True
        else:
            self.active = False
            if self.name in genes and self.number in genes[self.name]:
                del genes[self.name][self.number]
            if (self.required_bodypart_gene in dependent_genes and
                    self.required_gene_number in dependent_genes[self.required_bodypart_gene]):
                dependent_genes[self.required_bodypart_gene][self.required_gene_number].remove(self)

    def mutate(self, genome: "Genome") -> None:
        new_size_coeff = self.size_coeff + self.make_step()
        if new_size_coeff < self.min_limit:
            self.size_coeff += self.make_step("+")
        else:
            self.size_coeff = new_size_coeff

    def apply(self, genome: "Genome") -> None:
        pass

    @classmethod
    def correct(cls, genome: "Genome") -> None:
        genes = genome.effects.bodyparts_genes
        dependent_genes = genome.effects.dependent_bodypart_genes

        if cls.uniq and len(genes[cls.name]) > 1:
            uniq_genes = list(genes[cls.name].values())
            selected_gene = uniq_genes[random.randint(0, len(uniq_genes) - 1)]
            genes[cls.name] = {selected_gene.number: selected_gene}

            for not_used in uniq_genes:
                if not_used != selected_gene:
                    # переприсоединяются зависимые гены
                    not_used_dependent = dependent_genes[not_used.name][not_used.number]
                    for reappending_gene in not_used_dependent:
                        reappending_gene.required_gene_number = selected_gene.number
                    dependent_genes[selected_gene.name][selected_gene.number].update(not_used_dependent)
                    del dependent_genes[not_used.name][not_used.number]
                    # неиспользуемый ген убирается из зависимых
                    dependent_genes[not_used.required_bodypart_gene][not_used.required_gene_number].remove(not_used)


class ResourceStorageGeneInterface(BodypartGeneInterface):
    """Интерфейс для генов, добавляющих хранилище ресурса."""

    name = "resource_storage_gene_interface"
    resource: str


class ResourceConsumptionGeneInterface(StepGeneMixin, GeneInterface):
    """Интерфейс для генов, позволяющих потреблять ресурсы."""

    name = "resource_consumption_gene_interface"
    default_consumption: int
    resource: str

    def __init__(self, first: bool) -> None:
        super().__init__(first)
        if self.first:
            self.consumption = self.default_consumption
        else:
            self.consumption = self.make_step()

    def __repr__(self) -> str:
        return f"{super().__repr__()}: {self.consumption}"

    def mutate(self, genome: "Genome") -> None:
        self.consumption += self.make_step()

    def apply(self, genome: "Genome") -> None:
        genome.effects.consumption_amount[RESOURCE_DICT[self.resource]] += self.consumption

    @classmethod
    def correct(cls, genome: "Genome") -> None:
        if genome.effects.consumption_amount[RESOURCE_DICT[cls.resource]] < cls.common_min_limit:
            genome.effects.consumption_amount[RESOURCE_DICT[cls.resource]] = cls.common_min_limit


class NumberGeneInterface(StepGeneMixin[ST], GeneInterface):
    """Интерфейс для генов, влияющих численно."""

    name = "number_gene_interface"
    attribute_default: ST
    attribute_name: str

    def __init__(self, first: bool) -> None:
        super().__init__(first)
        if self.first:
            self.attribute_value = self.attribute_default
        else:
            self.attribute_value = self.make_step()

    def __repr__(self) -> str:
        return f"{super().__repr__()}: {self.attribute_value}"

    def mutate(self, genome: "Genome") -> None:
        step = self.make_step()
        new_value = self.attribute_value + step
        if hasattr(self, "min_limit") and new_value < self.min_limit:
            self.attribute_value += self.make_step("+")
        elif hasattr(self, "max_limit") and new_value > self.max_limit:
            self.attribute_value += self.make_step("-")
        else:
            self.attribute_value = new_value

    def apply(self, genome: "Genome") -> None:
        setattr(
            genome.effects,
            self.attribute_name,
            getattr(genome.effects, self.attribute_name) + self.attribute_value
        )

    @classmethod
    def correct(cls, genome: "Genome") -> None:
        if hasattr(cls, "common_min_limit") and getattr(genome.effects, cls.attribute_name) < cls.common_min_limit:
            setattr(genome.effects, cls.attribute_name, cls.common_min_limit)
        if hasattr(cls, "common_max_limit") and getattr(genome.effects, cls.attribute_name) > cls.common_min_limit:
            setattr(genome.effects, cls.attribute_name, cls.common_max_limit)


class ColorGeneInterface(StepGeneMixin[int], GeneInterface):
    name = "color_gene_interface"
    # RGB - red, green, blue - 0, 1, 2
    # разложение цвета на базовые (предполагается, что их сумма равна 1)
    red: float
    green: float
    blue: float
    # количество пигмента
    # сейчас вырабатываемый пигмент не дает расхода ресурсов
    # потом можно будет добавить следующее - пигмент является синтезируемым веществом, накапливаемом в организме
    pigment_amount: float

    def __repr__(self) -> str:
        return f"{super().__repr__()}: {self.pigment_amount}"

    def mutate(self, genome: "Genome"):
        self.pigment_amount += self.make_step()
        if self.pigment_amount < 0:
            self.pigment_amount = 0

    def apply(self, genome: "Genome"):
        genome.effects.color[0] += int(self.pigment_amount * self.red)
        genome.effects.color[1] += int(self.pigment_amount * self.green)
        genome.effects.color[2] += int(self.pigment_amount * self.blue)

    @classmethod
    def correct(cls, genome: "Genome"):
        # обработка цветов производится в Genome.apply_color
        pass


class ActionWeightCoeffGeneInterface(StepGeneMixin[int], GeneInterface):
    name = "action_weight_gene_interface"
    action: str
    weight_coeff: float

    def __repr__(self) -> str:
        return f"{super().__repr__()}: {self.weight_coeff}"

    def mutate(self, genome: "Genome") -> None:
        self.weight_coeff += self.make_step()

    def apply(self, genome: "Genome") -> None:
        genome.effects.action_weights[self.action] += self.weight_coeff

    @classmethod
    def correct(cls, genome: "Genome") -> None:
        if hasattr(cls, "common_min_limit") and genome.effects.action_weights[cls.action] < cls.common_min_limit:
            genome.effects.action_weights[cls.action] = cls.common_min_limit


GeneInterfaceClass = (GeneInterface | BodypartGeneInterface | ResourceStorageGeneInterface |
                      ResourceConsumptionGeneInterface | NumberGeneInterface | ColorGeneInterface |
                      ActionWeightCoeffGeneInterface)

# noinspection DuplicatedCode
GENE_INTERFACE_CLASSES: dict[str, Type[GeneInterfaceClass]] = {x.name: x for x in GeneInterface.get_all_subclasses()}
GENE_INTERFACE_CLASSES[GeneInterface.name] = GeneInterface
# обновляются данные в интерфейсах
GeneInterface.apply_descriptor(gene_interface_descriptors[GeneInterface.name])
for name, gene_interface_class in GENE_INTERFACE_CLASSES.items():
    gene_interface_class.apply_descriptor(gene_interface_descriptors[name])

# создаются классы генов
GENE_CLASSES: dict[str, Type[GeneInterfaceClass]] = {
    x["name"]: type(x["name"], (GENE_INTERFACE_CLASSES[x["interface"]],), x)
    for x in gene_descriptors.values()
}
# обновляются данные в классах генов
for name, gene_class in GENE_CLASSES.items():
    gene_class.apply_descriptor(gene_descriptors[name])

# классы генов, которые могут появиться
GENE_CLASSES_CAN_APPEAR: dict[str, Type[GeneInterfaceClass]] = {name: gene_class for name, gene_class in
                                                                GENE_CLASSES.items()
                                                                if gene_class.appearance_chance > 0}
