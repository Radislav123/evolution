import time


class A:
    def __init__(self):
        self.dict = {}

    def __setitem__(self, key, value):
        self.dict[key] = value


a = A()
b = {}


def timer(dict_like) -> float:
    repetitions = 1000000

    start = time.time()
    for i in range(repetitions):
        dict_like[i] = (i, i)
    stop = time.time()
    return stop - start


print(timer(a))
print(timer(b))


rep = 1000000
dict_1 = {j: (j, j) for j in range(rep)}
dict_2 = {j: (j, j) for j in range(rep)}
dict_3 = {j: (j, j) for j in range(rep)}

start_1 = time.time()
for j in dict_1:
    c_1 = dict_1[j]
stop_1 = time.time()

start_2 = time.time()
for key_2, value_2 in dict_2.items():
    c_2 = value_2
stop_2 = time.time()

start_3 = time.time()
for value_3 in dict_3.values():
    c_3 = value_3
stop_3 = time.time()

print("-------------------")
print(stop_1 - start_1)
print(stop_2 - start_2)
print(stop_3 - start_3)
