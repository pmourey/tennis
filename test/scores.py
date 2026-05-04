def paires_avec_somme_N(liste, N):
    paires = []
    for i in range(len(liste)):
        for j in range(i, len(liste)):  # Modifier la boucle pour inclure aussi i
            if liste[i] + liste[j] == N:
                paires.append((liste[i], liste[j]))
    return paires

print(paires_avec_somme_N([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 10))
