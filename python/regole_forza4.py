"""Regole di Forza 4, indipendenti da Flask e dal database."""


def gioca(griglia, giocatore, colonna):
    """Restituisce nuova griglia e risultato: 0 continua, 1/2 vittoria, 3 pareggio."""
    if len(griglia) != 42 or any(c not in '012' for c in griglia):
        raise ValueError('Griglia non valida.')
    if giocatore not in (1, 2) or colonna not in range(7):
        raise ValueError('Mossa non valida.')

    celle = list(griglia)
    riga = 5
    while riga >= 0 and celle[riga * 7 + colonna] != '0':
        riga -= 1
    if riga < 0:
        raise ValueError('Colonna piena.')
    pedina = str(giocatore)
    celle[riga * 7 + colonna] = pedina
    nuova_griglia = ''.join(celle)

    # Orizzontale, verticale e due diagonali, nei due versi.
    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        consecutive = 1
        for verso in (-1, 1):
            r = riga + dr * verso
            c = colonna + dc * verso
            while 0 <= r < 6 and 0 <= c < 7 and celle[r * 7 + c] == pedina:
                consecutive += 1
                r += dr * verso
                c += dc * verso
        if consecutive >= 4:
            return nuova_griglia, giocatore
    return nuova_griglia, 0 if '0' in celle else 3
