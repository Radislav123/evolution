import collections
import copy
import datetime
import functools
import operator
import random
from typing import Any, Callable

from simulator.world_resource import RESOURCE_LIST, Resources


class ResourcesReal(Resources):
    def __add__(self, other: "Resources") -> "Resources":
        return self.__class__({resource: self[resource] + other[resource] for resource in RESOURCE_LIST})


class ResourcesTest1(Resources):
    def __add__(self, other: "Resources") -> "Resources":
        return super().__init__(functools.reduce(operator.add, map(collections.Counter, (self, other))))


class ResourcesTest2(Resources):
    def __add__(self, other: "Resources") -> "Resources":
        temp = self.__class__()
        temp += self
        temp += other
        return temp


class ResourcesTest3(Resources):
    def __add__(self, other: "Resources") -> "Resources":
        return self.__class__({resource: self[resource] + other[resource] for resource in set(self) | set(other)})


class ResourcesTest4(Resources):
    def __add__(self, other: "Resources") -> "Resources":
        return operator.iadd(operator.iadd(self.__class__(), self), other)


class ResourcesTest5(Resources):
    def __add__(self, other: "Resources") -> "Resources":
        temp = self.copy()
        temp += other
        return temp


class ResourcesTest6(Resources):
    def __add__(self, other: "Resources") -> "Resources":
        temp = copy.copy(self)
        temp += other
        return temp


def random_data() -> tuple:
    borders = (0, 1000)
    resources_len = len(RESOURCE_LIST)
    random_dict_a = {resource: random.randint(*borders)
                     for resource in set(random.choices(RESOURCE_LIST, k = random.randint(0, resources_len)))}
    random_dict_b = {resource: random.randint(*borders)
                     for resource in set(random.choices(RESOURCE_LIST, k = random.randint(0, resources_len)))}
    classes = (
        ResourcesReal,
        ResourcesTest1,
        ResourcesTest2,
        ResourcesTest3,
        ResourcesTest4,
        ResourcesTest5,
        ResourcesTest6
    )
    data = tuple((cls(random_dict_a), cls(random_dict_b)) for cls in classes)

    return data


TEST_DATA_LENGTH = 1000000
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


def test(a: Resources, b: Resources) -> Any:
    result = a + b
    return result


times = timer(
    {
        "real": test,
        "test_1": test,
        "test_2": test,
        "test_3": test,
        "test_4": test,
        "test_5": test,
    }
)
times = [(key, value) for key, value in times.items()]
times.sort(key = lambda x: x[1])
max_length = max(len(x[0]) for x in times)

print("--------------------------")
for k, v in times:
    print(f"{k.ljust(max_length, ' ')}: \t{v} \tx{v / times[0][1]}")
