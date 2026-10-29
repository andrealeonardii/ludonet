"""Allena una policy 84-128-64-7. L'insegnante è usato solo prima dell'allenamento."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]


def crea_rete():
    return nn.Sequential(nn.Linear(84, 128), nn.ReLU(), nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 7))


def ingressi(griglie):
    return np.concatenate((griglie == 1, griglie == 2), axis=1).astype(np.float32)


def carica_esempi(percorso):
    righe = percorso.read_text().splitlines()
    griglie, punteggi, vittorie, blocchi, validazione = [], [], [], [], []
    visti = set()
    for riga in righe:
        g, *numeri = riga.split()
        specchio = ''.join(g[i:i+7][::-1] for i in range(0,42,7))
        chiave = min(g, specchio)
        if chiave in visti:
            continue
        visti.add(chiave)
        # La stessa posizione e il suo specchio non possono finire nei due insiemi.
        verifica = int.from_bytes(hashlib.sha256(chiave.encode()).digest()[:4], 'big') % 10 == 0
        griglie.append([int(c) for c in g])
        punteggi.append([int(v) for v in numeri[:7]])
        vittorie.append([bool(int(numeri[7]) & (1 << c)) for c in range(7)])
        blocchi.append([bool(int(numeri[8]) & (1 << c)) for c in range(7)])
        validazione.append(verifica)
    return (np.array(griglie, dtype=np.int8), np.array(punteggi), np.array(vittorie),
            np.array(blocchi), np.array(validazione))


def esporta(rete, percorso):
    temporaneo = percorso.with_suffix('.tmp')
    with temporaneo.open('w') as f:
        f.write('NICKGAME_FORZA4_V1\n')
        for strato in rete:
            if isinstance(strato, nn.Linear):
                f.write(f'{strato.in_features} {strato.out_features}\n')
                for matrice in (strato.weight, strato.bias):
                    valori = matrice.detach().cpu().numpy().ravel()
                    f.write(' '.join(f'{v:.9g}' for v in valori) + '\n')
    temporaneo.replace(percorso)


def misura(rete, x, libere, buone, vittorie, blocchi):
    with torch.no_grad():
        scelte = rete(x).masked_fill(~libere, -1e9).argmax(1)
    righe = torch.arange(len(x))
    def percentuale(maschera, obiettivi):
        return round(100 * obiettivi[righe, scelte][maschera].float().mean().item(), 2) if maschera.any() else None
    vincenti = vittorie.any(1)
    da_bloccare = blocchi.any(1) & ~vincenti
    return {
        'posizioni': len(x),
        'accordo_insegnante_percento': percentuale(torch.ones(len(x), dtype=torch.bool), buone),
        'vittorie_immediate': int(vincenti.sum()),
        'vittorie_colte_percento': percentuale(vincenti, vittorie),
        'minacce_bloccabili': int(da_bloccare.sum()),
        'minacce_bloccate_percento': percentuale(da_bloccare, blocchi),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--esempi', type=int, default=750000)
    p.add_argument('--epoche', type=int, default=160)
    p.add_argument('--profondita', type=int, default=4)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--output', type=Path, default=ROOT/'modelli/forza4')
    p.add_argument('--dati', type=Path, default=ROOT/'allenamento/build/esempi.txt')
    args = p.parse_args()
    if args.epoche < 1 or args.esempi < 1000:
        p.error('Servono almeno 1000 esempi e una epoca.')
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    args.dati.parent.mkdir(parents=True, exist_ok=True)
    metadati = args.dati.with_suffix('.json')
    descrizione = {'esempi':args.esempi, 'profondita':args.profondita, 'seed':args.seed}
    if not args.dati.exists() or not metadati.exists() or json.loads(metadati.read_text()) != descrizione:
        binario = args.dati.parent/'insegnante'
        subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror',
                        str(ROOT/'allenamento/insegnante.cpp'),'-o',str(binario)], check=True)
        temporaneo = args.dati.with_suffix('.tmp')
        subprocess.run([str(binario), str(temporaneo), str(args.esempi), str(args.profondita), str(args.seed)], check=True)
        temporaneo.replace(args.dati)
        metadati.write_text(json.dumps(descrizione, indent=2)+'\n')
    griglie, punteggi, vittorie, blocchi, verifica = carica_esempi(args.dati)
    buone = punteggi == punteggi.max(axis=1, keepdims=True)
    # Nei casi tattici supervisioniamo tutte e sole le vittorie o le parate immediate.
    vincenti = vittorie.any(1)
    da_bloccare = blocchi.any(1) & ~vincenti
    buone[vincenti] = vittorie[vincenti]
    buone[da_bloccare] = blocchi[da_bloccare]
    validazione = [torch.tensor(v[verifica]) for v in (
        ingressi(griglie), griglie[:,:7] == 0, buone, vittorie, blocchi)]
    # Riflettiamo anche gli esempi di training: destra e sinistra hanno le stesse regole.
    g = griglie[~verifica]
    x = torch.tensor(ingressi(np.concatenate((g, g.reshape(-1,6,7)[:,:,::-1].reshape(-1,42)))))
    y = torch.tensor(np.concatenate((buone[~verifica], buone[~verifica,::-1])))
    libere = torch.cat((torch.tensor(g[:,:7] == 0), torch.tensor(g[:,:7][:,::-1].copy() == 0)))
    peso = torch.tensor(np.where((vincenti | da_bloccare)[~verifica], 6., 1.), dtype=torch.float32).repeat(2)
    rete = crea_rete()
    ottimizzatore = torch.optim.Adam(rete.parameters(), lr=.001)
    migliore = -1
    print(f'Training: {len(x)} esempi con specchi; validazione: {int(verifica.sum())}', flush=True)
    for epoca in range(args.epoche):
        if epoca == args.epoche * 3 // 4:
            for gruppo in ottimizzatore.param_groups:
                gruppo['lr'] = .0003
        rete.train()
        ordine = torch.randperm(len(x))
        for batch in ordine.split(1024):
            logits = rete(x[batch]).masked_fill(~libere[batch], -1e9)
            # Una qualsiasi mossa fra quelle equivalenti dell'insegnante è corretta.
            perdita = (torch.logsumexp(logits, 1) - torch.logsumexp(logits.masked_fill(~y[batch], -1e9), 1))
            perdita = (perdita * peso[batch]).mean()
            ottimizzatore.zero_grad()
            perdita.backward()
            ottimizzatore.step()
        rete.eval()
        metriche = misura(rete, *validazione)
        punteggio = sum(metriche[k] or 0 for k in (
            'accordo_insegnante_percento', 'vittorie_colte_percento', 'minacce_bloccate_percento'))
        if punteggio > migliore:
            migliore = punteggio
            esporta(rete, args.output/'pesi.txt')
            torch.save(rete.state_dict(), args.dati.parent/'migliore.pt')
            rapporto = {'architettura':[84,128,64,7], 'parametri':sum(p.numel() for p in rete.parameters()),
                        'seed':args.seed, 'epoca':epoca+1, 'epoche_richieste':args.epoche,
                        'profondita_insegnante':args.profondita, 'esempi_generati':args.esempi,
                        'torch':torch.__version__, 'numpy':np.__version__,
                        'sha256_dati':hashlib.sha256(args.dati.read_bytes()).hexdigest(),
                        'posizioni_training_distinte':int((~verifica).sum()),
                        'validazione':metriche, 'nota':'Validazione usata per scegliere i pesi; non è un test indipendente.'}
            (args.output/'allenamento.json').write_text(json.dumps(rapporto, indent=2)+'\n')
        if (epoca+1)%10 == 0 or epoca == 0:
            print(f'Epoca {epoca+1}: {metriche}', flush=True)


if __name__ == '__main__': main()
