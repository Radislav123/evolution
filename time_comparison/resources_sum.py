import datetime
import random
from typing import Any, Callable, Iterable

from simulator.world_resource import RESOURCE_LIST, Resources


start_all = datetime.datetime.now()


class ResourcesReal(Resources):
    @classmethod
    def sum(cls, resources_iterable: Iterable["Resources"]) -> "Resources":
        temp_iterable = list(resources_iterable)
        return Resources({resource: sum(x[resource] for x in temp_iterable) for resource in RESOURCE_LIST})


class ResourcesTest1(Resources):
    @classmethod
    def sum(cls, resources_iterable: Iterable["Resources"]) -> "Resources":
        return sum(resources_iterable, Resources())


class ResourcesTest2(Resources):
    @classmethod
    def sum(cls, resources_iterable: Iterable["Resources"]) -> "Resources":
        resources_sum = Resources()
        for resources in resources_iterable:
            resources_sum += resources
        return resources_sum


class ResourcesTest3(Resources):
    @classmethod
    def sum(cls, resources_iterable: Iterable["Resources"]) -> "Resources":
        resources_sum = Resources()
        for resources in resources_iterable:
            for resource, amount in resources.items():
                resources_sum[resource] += amount
        return resources_sum


class ResourcesTest4(Resources):
    @classmethod
    def sum(cls, resources_iterable: Iterable["Resources"]) -> "Resources":
        temp_iterable = list(resources_iterable)
        resources_sum = temp_iterable[0].copy()
        for resources in resources_iterable[1:]:
            resources_sum += resources
        return resources_sum


class ResourcesTest5(Resources):
    @classmethod
    def sum(cls, resources_iterable: Iterable["Resources"]) -> "Resources":
        temp_iterable = list(resources_iterable)
        resources_sum = temp_iterable[0].copy()
        for resources in resources_iterable[1:]:
            for resource, amount in resources.items():
                resources_sum[resource] += amount
        return resources_sum


def random_data() -> tuple:
    borders = (0, 1000)
    list_borders = (0, 1000)
    resources_len = len(RESOURCE_LIST)
    random_dicts_list = [
        {
            resource: random.randint(*borders) for resource in
            set(random.choices(RESOURCE_LIST, k = random.randint(0, resources_len)))
        } for _ in range(random.randint(*list_borders))
    ]
    classes = (
        ResourcesReal,
        ResourcesReal,
        ResourcesTest1,
        ResourcesTest1,
        ResourcesTest2,
        ResourcesTest2,
        ResourcesTest3,
        ResourcesTest3,
        ResourcesTest4,
        ResourcesTest4,
        ResourcesTest5,
        ResourcesTest5,
    )
    data = tuple([cls(x) for x in random_dicts_list] for cls in classes)
    return data


TEST_DATA_LENGTH = 10000
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
            function(data[index])
            durations[name] += datetime.datetime.now() - start
    return durations


def test(a: Iterable[Resources]) -> Any:
    result = Resources.sum(a)
    return result


def test_typed(a: Iterable[Resources]) -> Any:
    result = Resources[int].sum(a)
    return result


times = timer(
    {
        "real": test,
        "real_typed": test_typed,
        "test_1": test,
        "test_1_typed": test_typed,
        "test_2": test,
        "test_2_typed": test_typed,
        "test_3": test,
        "test_3_typed": test_typed,
        "test_4": test,
        "test_4_typed": test_typed,
        "test_5": test,
        "test_5_typed": test_typed,
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
