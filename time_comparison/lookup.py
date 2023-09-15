import datetime
import random
from typing import Any, Callable


def random_data() -> tuple:
    def random_callable() -> None:
        pass

    borders = (0, 1000)
    random_list = [x for x in range(borders[1] + 1)]
    random_dict = {x: random_callable for x in range(borders[1] + 1)}
    random_b = random.randint(*borders)
    list_data = (random_list, random_b, random_callable)
    dict_data = (random_dict, random_b)
    match_case_data = (random_b, random_callable)
    if_elif_data = (random_b, random_callable)
    return list_data, dict_data, match_case_data, if_elif_data


TEST_DATA_LENGTH = 100000
TEST_DATA = tuple(random_data() for _ in range(TEST_DATA_LENGTH))


def timer(function: Callable, index: int) -> datetime.timedelta:
    duration = datetime.timedelta()
    for data in TEST_DATA:
        start = datetime.datetime.now()
        function(*data[index])
        finish = datetime.datetime.now()
        duration += finish - start
    return duration


def test_list(a: list[int], b: int, c: Callable) -> Any:
    if b in a:
        result = c()
    return result


def test_dict(a: dict[int, Callable], b: int) -> Any:
    return a[b]()


def test_match_case(b: int, c: Callable) -> Any:
    match b:
        case 0:
            result = c()
        case 1:
            result = c()
        case 2:
            result = c()
        case 3:
            result = c()
        case 4:
            result = c()
        case 5:
            result = c()
        case 6:
            result = c()
        case 7:
            result = c()
        case 8:
            result = c()
        case 9:
            result = c()
        case 10:
            result = c()
        case _:
            result = c()
    return result


def test_if_elif_else(b: int, c: Callable) -> Any:
    if b == 0:
        result = c()
    elif b == 1:
        result = c()
    elif b == 2:
        result = c()
    elif b == 3:
        result = c()
    elif b == 4:
        result = c()
    elif b == 5:
        result = c()
    elif b == 6:
        result = c()
    elif b == 7:
        result = c()
    elif b == 8:
        result = c()
    elif b == 9:
        result = c()
    elif b == 10:
        result = c()
    else:
        result = c()
    return result


times = [
    ("list", timer(test_list, 0)),
    ("dict", timer(test_dict, 1)),
    ("match_case", timer(test_match_case, 2)),
    ("if_elif", timer(test_if_elif_else, 3))
]
times.sort(key = lambda x: x[1])
max_length = max(len(x[0]) for x in times)

print("--------------------------")
for k, v in times:
    print(f"{k.ljust(max_length, ' ')}: \t{v} \tx{v / times[0][1]}")
