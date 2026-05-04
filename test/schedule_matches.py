def func(n):
    a = []
    b = []
    c = (n * (n - 1)) / 2
    c = int(c)
    e = []
    f = []
    result = []
    result1 = []

    # creating (0,1), (0,2) ··· (n-1, n)
    for i1 in range(n):
        for i2 in range(n):
            if i1 < i2:
                f.append((i1, i2))

                # creating list of waiting time a = [0,1,2, ··· , n-1] and b = [0,0, ··· , 0]
    for i in range(n):
        a.append(i)
        b.append(0)

    # main dish
    for i1 in range(c):
        d1 = b.copy()
        d2 = a.copy()
        e = []

        # ordering from largest waiting time to smallest waiting time e = [largest to smallest] in index
        # d1 is the waiting time list
        # d2 is [0,1,···,n-1] but decreases gradually
        for j in range(n):
            m = max(d1)
            for k in range(n):
                if b[k] == m and k not in e:
                    n1 = k
                    e.append(n1)
                    d1.remove(m)
                    d2.remove(n1)
                    break
                else:
                    continue

        for (p, q) in f:
            if (e[p], e[q]) not in result and (e[q], e[p]) not in result:
                result.append((e[p], e[q]))
                for i in range(n):
                    if i != e[p] and i != e[q]:
                        b[i] = b[i] + 1
                    else:
                        b[i] = 0
                break
            else:
                continue

    # making (2,0)s into (0,2)s
    for (k1, k2) in result:
        if k1 < k2:
            result1.append((k1 + 1, k2 + 1))
        else:
            result1.append((k2 + 1, k1 + 1))

    return result1

print(func(5))




