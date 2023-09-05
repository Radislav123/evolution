import datetime
import random
import string
from typing import Callable


def random_string() -> str:
    string_length = (1, 100)
    return "".join(random.choices(string.ascii_uppercase + string.digits, k = random.randint(*string_length)))


TEST_DATA_LENGTH = 1000000
TEST_DATA = tuple((random_string(), random_string()) for _ in range(TEST_DATA_LENGTH))


def timer(function: Callable) -> datetime.timedelta:
    start = datetime.datetime.now()
    for a, b in TEST_DATA:
        function(a, b)
    finish = datetime.datetime.now()
    return finish - start


def test_percent(a: str, b: str) -> str:
    return "%s: %s" % (a, b)


def test_format(a: str, b: str) -> str:
    return "{}: {}".format(a, b)


def test_f_string(a: str, b: str) -> str:
    return f"{a}: {b}"


times = {
    "percent": timer(test_percent),
    "format": timer(test_format),
    "f_string": timer(test_f_string)
}

print("--------------------------")
print("time in microseconds")
for k, v in times.items():
    print(f"{k}: \t{v.microseconds}")
