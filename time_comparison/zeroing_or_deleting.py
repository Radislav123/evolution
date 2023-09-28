import datetime
import random
from typing import Any, Callable

from simulator.world_resource import RESOURCE_LIST


start_all = datetime.datetime.now()


def random_data() -> tuple:
    borders = (-1000, 1000)
    resources_len = len(RESOURCE_LIST)
    random_dict = {resource: random.randint(*borders)
                   for resource in set(random.choices(RESOURCE_LIST, k = random.randint(0, resources_len)))}
    tests_amount = 7
    data = tuple(random_dict.copy() for _ in range(tests_amount))
    return data


TEST_DATA_LENGTH = 1000000
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


def test_comprehension_0(a: dict) -> Any:
    a = {key: value for key, value in a.items() if value < 0}
    return a


def test_comprehension_1(a: dict) -> Any:
    return {key: value for key, value in a.items() if value < 0}


def test_zeroing_0(a: dict) -> Any:
    for key, value in a.items():
        if value > 0:
            a[key] = 0
    return a


def test_zeroing_1(a: dict) -> Any:
    for key, value in a.items():
        if value >= 0:
            a[key] = 0
    return a


def test_zeroing_2(a: dict) -> Any:
    b = a.copy()
    for key, value in a.items():
        if value >= 0:
            b[key] = 0
    return b


def test_del_0(a: dict) -> Any:
    b = a.copy()
    for key, value in a.items():
        if value > 0:
            del b[key]
    return b


def test_del_1(a: dict) -> Any:
    b = a.copy()
    for key, value in a.items():
        if value >= 0:
            del b[key]
    return b


times = timer(
    {
        "comprehension_0": test_comprehension_0,
        "comprehension_1": test_comprehension_1,
        "zeroing_0": test_zeroing_0,
        "zeroing_1": test_zeroing_1,
        "zeroing_2": test_zeroing_2,
        "del_0": test_del_0,
        "del_1": test_del_1,
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
