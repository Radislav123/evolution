import datetime
import random
from typing import Callable, Iterable

from simulator.world_resource import RESOURCE_LIST, Resources


def random_resources() -> tuple[Iterable[Resources], Iterable[Resources]]:
    borders = (0, 1000)
    amount = (0, 1000)
    resources_list = [Resources({resource: random.randint(*amount) for resource in RESOURCE_LIST})
                      for _ in range(random.randint(*borders))]

    return (x for x in resources_list), (x for x in resources_list)


TEST_DATA_LENGTH = 10000
TEST_DATA = tuple(random_resources() for _ in range(TEST_DATA_LENGTH))


def timer(function: Callable, index: int) -> datetime.timedelta:
    start = datetime.datetime.now()
    for data in TEST_DATA:
        function(data[index])
    finish = datetime.datetime.now()
    return finish - start


def test_loop(resources_iterable) -> Resources:
    resources = Resources()
    for other_resources in resources_iterable:
        resources += other_resources
    return resources


def test_comp(resources_iterable) -> Resources:
    temp_iterable = list(resources_iterable)
    return Resources({resource: sum(x[resource] for x in temp_iterable) for resource in RESOURCE_LIST})


times = [
    ("loop", timer(test_loop, 0)),
    ("comp", timer(test_comp, 1))
]
times.sort(key = lambda x: x[1])

print("--------------------------")
for k, v in times:
    print(f"{k}: \t{v} \tx{v / times[0][1]}")
