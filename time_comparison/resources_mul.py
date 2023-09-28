import datetime
import random
from typing import Any, Callable

from simulator.world_resource import RESOURCE_LIST, Resources


start_all = datetime.datetime.now()


class ResourcesReal(Resources):
    def __mul__(self, multiplier: int | float) -> "Resources":
        return self.__class__({resource: self[resource] * multiplier for resource in RESOURCE_LIST})


class ResourcesTest1(Resources):
    def __mul__(self, multiplier: int | float) -> "Resources":
        new = self.copy()
        new *= multiplier
        return new


class ResourcesTest2(Resources):
    def __mul__(self, multiplier: int | float) -> "Resources":
        new = self.copy()
        for resource, amount in new.items():
            new[resource] = amount * multiplier
        return new


class ResourcesTest3(Resources):
    def __mul__(self, multiplier: int | float) -> "Resources":
        return self.__class__({resource: amount * multiplier for resource, amount in self.items()})


class ResourcesTest4(Resources):
    def __mul__(self, multiplier: int | float) -> "Resources":
        return self.__class__({resource: self[resource] * multiplier for resource in self})


class ResourcesTest5(Resources):
    def __mul__(self, multiplier: int | float) -> "Resources":
        return ResourcesTest5({resource: self[resource] * multiplier for resource in RESOURCE_LIST})


class ResourcesTest6(Resources):
    def __mul__(self, multiplier: int | float) -> "Resources":
        return ResourcesTest6({resource: amount * multiplier for resource, amount in self.items()})


class ResourcesTest7(Resources):
    def __mul__(self, multiplier: int | float) -> "Resources":
        return ResourcesTest7({resource: self[resource] * multiplier for resource in self})


def random_data() -> tuple:
    borders = (0, 1000)
    resources_len = len(RESOURCE_LIST)
    random_dict_a = {resource: random.randint(*borders)
                     for resource in set(random.choices(RESOURCE_LIST, k = random.randint(0, resources_len)))}
    b = random.randint(*borders)
    classes = (
        ResourcesReal,
        ResourcesTest1,
        ResourcesTest2,
        ResourcesTest3,
        ResourcesTest4,
        ResourcesTest5,
        ResourcesTest6,
        ResourcesTest7,
    )
    data = tuple((cls(random_dict_a), b) for cls in classes)

    return data


TEST_DATA_LENGTH = 10000000
TEST_DATA = (random_data() for _ in range(TEST_DATA_LENGTH))


def print_progress_bar(current: int | float, total: int, bar_length: int) -> None:
    fraction = current / total

    arrow = int(fraction * bar_length - 1) * '=' + '>'
    padding = int(bar_length - len(arrow)) * ' '
    ending = '\n' if current == total else '\r'

    print(f"Progress: [{arrow}{padding}] {int(fraction * 100)}%", end = ending)


def timer(functions: dict[str, Callable]) -> dict[str, datetime.timedelta]:
    durations = {name: datetime.timedelta() for name in functions}
    for number, data in enumerate(TEST_DATA):
        if number % 100 == 0:
            print_progress_bar(number, TEST_DATA_LENGTH, 20)
        for index, name in enumerate(functions):
            function = functions[name]
            start = datetime.datetime.now()
            function(*data[index])
            durations[name] += datetime.datetime.now() - start
    return durations


def test(a: Resources, b: int) -> Any:
    a *= b
    return a


times = timer(
    {
        "real": test,
        "test_1": test,
        "test_2": test,
        "test_3": test,
        "test_4": test,
        "test_5": test,
        "test_6": test,
        "test_7": test,
    }
)
finish_all = datetime.datetime.now()

times = [(key, value) for key, value in times.items()]
times.sort(key = lambda x: x[1])
max_length = max(len(x[0]) for x in times)

all_time = finish_all - start_all
only_tests_time = sum((x[1] for x in times), datetime.timedelta())
only_service_time = all_time - only_tests_time
service_times = {
    "all time": all_time,
    "only tests time": only_tests_time,
    "only service time": only_service_time,
}
service_times = [(key, value) for key, value in service_times.items()]
max_service_length = max(len(x[0]) for x in service_times)

print("----------------------------------------------------")
for k, v in service_times:
    print(f"{k.ljust(max_service_length, ' ')}: \t{v}")
print("----------------------------------------------------")
for k, v in times:
    print(f"{k.ljust(max_length, ' ')}: \t{v} \tx{v / times[0][1]}")
print("----------------------------------------------------")
