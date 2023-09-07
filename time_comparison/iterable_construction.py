import datetime
import random
from typing import Callable


def random_ranges() -> tuple[range, range]:
    borders = (0, 100)
    stop = random.randint(*borders)

    return range(stop), range(stop)


TEST_DATA_LENGTH = 10000000
TEST_DATA = tuple(random_ranges() for _ in range(TEST_DATA_LENGTH))


def timer(function: Callable, index: int) -> datetime.timedelta:
    start = datetime.datetime.now()
    for data in TEST_DATA:
        function(data[index])
    finish = datetime.datetime.now()
    return finish - start


def test(a) -> int:
    return hash(a)


times = [
    ("list", timer(test, 0)),
    ("tuple", timer(test, 1))
]
times.sort(key = lambda x: x[1])

print("--------------------------")
for k, v in times:
    print(f"{k}: \t{v} \tx{v / times[0][1]}")
