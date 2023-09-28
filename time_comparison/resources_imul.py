import datetime
import random
from typing import Any, Callable

from simulator.world_resource import RESOURCE_LIST, Resources


class ResourcesReal(Resources):
    def __imul__(self, multiplier: int | float) -> "Resources":
        for resource in RESOURCE_LIST:
            self[resource] *= multiplier
        return self


class ResourcesTest1(Resources):
    def __imul__(self, multiplier: int | float) -> "Resources":
        for resource in self:
            self[resource] *= multiplier
        return self


class ResourcesTest2(Resources):
    def __imul__(self, multiplier: int | float) -> "Resources":
        for resource, amount in self.items():
            self[resource] = amount * multiplier
        return self


def random_data() -> tuple:
    borders = (0, 1000)
    resources_len = len(RESOURCE_LIST)
    random_dict_a = {resource: random.randint(*borders)
                     for resource in set(random.choices(RESOURCE_LIST, k = random.randint(0, resources_len)))}
    b = random.randint(*borders)
    classes = (
        ResourcesReal,
        ResourcesTest1,
        ResourcesTest2
    )
    data = tuple((cls(random_dict_a), b) for cls in classes)

    return data


TEST_DATA_LENGTH = 10000000
TEST_DATA = (random_data() for _ in range(TEST_DATA_LENGTH))


def timer(functions: dict[str, Callable]) -> dict[str, datetime.timedelta]:
    durations = {name: datetime.timedelta() for name in functions}
    for data in TEST_DATA:
        for index, name in enumerate(functions):
            function = functions[name]
            start = datetime.datetime.now()
            function(*data[index])
            durations[name] += datetime.datetime.now() - start
    return durations


def test(a: Resources, b: int) -> Any:
    result = a * b
    return result


times = timer(
    {
        "real": test,
        "test_1": test,
        "test_2": test,
    }
)
times = [(key, value) for key, value in times.items()]
times.sort(key = lambda x: x[1])
max_length = max(len(x[0]) for x in times)

print("--------------------------")
for k, v in times:
    print(f"{k.ljust(max_length, ' ')}: \t{v} \tx{v / times[0][1]}")
