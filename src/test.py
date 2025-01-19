a = 24
b = 36
c = 48
m = 864

for k1 in range(int(m / a) + 1):
    for k2 in range(int(m / b) + 1):
        for k3 in range(int(m / c) + 1):
            if k1 * a + k2 * b + k3 * c == m:
                print(f"{k1} * {a} + {k2} * {b} + {k3} * {c} = {m}")

for k1 in range(int(m / a) + 1):
    for k2 in range(int(m / b) + 1):
        for k3 in range(int(m / c) + 1):
            if k1 * a + k2 * b + k3 * c == m:
                print(f"{k1}\t{k2}\t{k3}")
