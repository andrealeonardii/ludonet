"""Test indipendente dei pesi esportati e partite contro avversari di riferimento."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys

import numpy as np
import torch
from torch import nn

from allena import ROOT, crea_rete, ingressi, carica_esempi, misura
sys.path.insert(0, str(ROOT/'python'))
from regole_forza4 import gioca


def carica_rete(percorso):
    pezzi = iter(percorso.read_text().split())
    if next(pezzi) != 'NICKGAME_FORZA4_V1':
        raise ValueError('Formato dei pesi non valido')
    rete = crea_rete()
    with torch.no_grad():
        for strato in rete:
            if isinstance(strato, nn.Linear):
                assert int(next(pezzi)) == strato.in_features
                assert int(next(pezzi)) == strato.out_features
                for p in (strato.weight, strato.bias):
                    p.copy_(torch.tensor([float(next(pezzi)) for _ in range(p.numel())]).reshape(p.shape))
    assert next(pezzi, None) is None
    rete.eval()
    return rete


def scegli(rete, griglia, colore):
    g = np.array([[int(c) for c in griglia]], dtype=np.int8)
    x = np.concatenate((g == colore, g == 3-colore), axis=1).astype(np.float32)
    with torch.no_grad():
        valori = rete(torch.tensor(x))[0].numpy()
    valori[g[0,:7] != 0] = -np.inf
    return int(valori.argmax())


def avversario(griglia, colore, tattico, rng):
    libere = [c for c in range(7) if griglia[c] == '0']
    if tattico:
        # Questa strategia appartiene SOLO all'avversario di prova, mai a NickBot.
        for giocatore in (colore, 3-colore):
            vincenti = [c for c in libere if gioca(griglia, giocatore, c)[1] == giocatore]
            if vincenti: return rng.choice(vincenti)
    return rng.choice(libere)


def partite(rete, numero, tattico, seed):
    rng = random.Random(seed)
    risultati = {'vittorie':0, 'pareggi':0, 'sconfitte':0, 'partite':numero}
    for n in range(numero):
        griglia, turno, risultato = '0'*42, 1, 0
        colore_rete = 1 + n%2
        while risultato == 0:
            colonna = scegli(rete, griglia, turno) if turno == colore_rete else avversario(griglia, turno, tattico, rng)
            griglia, risultato = gioca(griglia, turno, colonna)
            turno = 3-turno
        risultati['pareggi' if risultato == 3 else ('vittorie' if risultato == colore_rete else 'sconfitte')] += 1
    return risultati


def chiave(g):
    return min(g, ''.join(g[i:i+7][::-1] for i in range(0,42,7)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--modello', type=Path, default=ROOT/'modelli/forza4/pesi.txt')
    p.add_argument('--dati-training', type=Path, default=ROOT/'allenamento/build/esempi.txt')
    p.add_argument('--partite', type=int, default=200)
    p.add_argument('--seed', type=int, default=2026)
    args = p.parse_args()
    torch.set_num_threads(1)
    torch.manual_seed(args.seed)
    build = ROOT/'allenamento/build'
    build.mkdir(parents=True, exist_ok=True)
    binario = build/'insegnante'
    subprocess.run(['g++','-std=c++17','-O3',str(ROOT/'allenamento/insegnante.cpp'),'-o',str(binario)], check=True)
    dati = build/'test_indipendente.txt'
    subprocess.run([str(binario),str(dati),'30000','4',str(args.seed)], check=True)
    noti = {chiave(riga.split()[0]) for riga in args.dati_training.read_text().splitlines()}
    g, valori, v, b, _ = carica_esempi(dati)
    nuovi = np.array([chiave(''.join(map(str, riga))) not in noti for riga in g])
    g, valori, v, b = g[nuovi], valori[nuovi], v[nuovi], b[nuovi]
    buone = valori == valori.max(axis=1, keepdims=True)
    buone[v.any(1)] = v[v.any(1)]
    bloccare = b.any(1) & ~v.any(1)
    buone[bloccare] = b[bloccare]
    rete = carica_rete(args.modello)
    rapporto = {
        'sha256_pesi':hashlib.sha256(args.modello.read_bytes()).hexdigest(),
        'seed_test':args.seed,
        'posizioni_escluse_per_sovrapposizione':int((~nuovi).sum()),
        'test_indipendente':misura(rete, *[torch.tensor(x) for x in (ingressi(g),g[:,:7]==0,buone,v,b)]),
        'contro_casuale':partite(rete, args.partite, False, args.seed),
        'contro_tattico':partite(rete, args.partite, True, args.seed+1),
        'nota':'Colori alternati. Il tattico vince o blocca in una mossa, altrimenti sceglie a caso. Non è un solver.'
    }
    percorso = args.modello.parent/'valutazione.json'
    percorso.write_text(json.dumps(rapporto, indent=2)+'\n')
    print(json.dumps(rapporto, indent=2))


if __name__ == '__main__': main()
