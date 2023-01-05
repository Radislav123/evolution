import time
from simulator.world_resource import Resources


DEFAULT_REPEAT = 100000


def test_time(function, *args, **kwargs):
    start_time = time.time()
    for _ in range(DEFAULT_REPEAT):
        function(*args, **kwargs)
    stop_time = time.time()
    return stop_time - start_time


def prepare():
    return Resources(), Resources()


def func_a():
    a, b = prepare()
    a + b


def func_b():
    a, b = prepare()
    a += b


prepare_time = test_time(prepare)
time_a = test_time(func_a) - prepare_time
time_b = test_time(func_b) - prepare_time
print(time_a)
print(time_b)
