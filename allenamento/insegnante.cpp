// Generatore OFFLINE di esempi. Non viene compilato o chiamato da run.sh.
#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>
#include <vector>

using Griglia = std::array<int, 42>;
const std::array<int, 7> ordine = {3, 2, 4, 1, 5, 0, 6};
std::vector<std::array<int, 4>> finestre;

int inserisci(Griglia& g, int c, int giocatore) {
    for (int r = 5; r >= 0; --r)
        if (!g[r * 7 + c]) { g[r * 7 + c] = giocatore; return r * 7 + c; }
    return -1;
}

bool vince(const Griglia& g, int cella) {
    for (auto direzione : {std::pair<int,int>{0,1}, {1,0}, {1,1}, {1,-1}}) {
        int n = 1;
        for (int verso : {-1, 1}) {
            int r = cella / 7 + verso * direzione.first;
            int c = cella % 7 + verso * direzione.second;
            while (r >= 0 && r < 6 && c >= 0 && c < 7 && g[r*7+c] == g[cella]) {
                ++n; r += verso * direzione.first; c += verso * direzione.second;
            }
        }
        if (n >= 4) return true;
    }
    return false;
}

int vittorie(Griglia& g, int giocatore) {
    int maschera = 0;
    for (int c = 0; c < 7; ++c) if (!g[c]) {
        int cella = inserisci(g, c, giocatore);
        if (vince(g, cella)) maschera |= 1 << c;
        g[cella] = 0;
    }
    return maschera;
}

int valuta(const Griglia& g, int giocatore) {
    int totale = 0;
    const int pesi[] = {0, 1, 8, 50, 10000};
    for (auto finestra : finestre) {
        int mie = 0, altre = 0;
        for (int i : finestra) { mie += g[i] == giocatore; altre += g[i] == 3-giocatore; }
        if (!altre) totale += pesi[mie];
        if (!mie) totale -= pesi[altre];
    }
    for (int r = 0; r < 6; ++r) {
        if (g[r*7+3] == giocatore) totale += 3;
        if (g[r*7+3] == 3-giocatore) totale -= 3;
    }
    return totale;
}

int cerca(Griglia& g, int giocatore, int profondita, int alfa, int beta) {
    bool libera = false;
    for (int c : ordine) libera |= !g[c];
    if (!libera) return 0;
    if (profondita == 0) return valuta(g, giocatore);
    int migliore = -20000;
    for (int c : ordine) if (!g[c]) {
        int cella = inserisci(g, c, giocatore);
        int valore = vince(g, cella) ? 10000 + profondita :
            -cerca(g, 3-giocatore, profondita-1, -beta, -alfa);
        g[cella] = 0;
        migliore = std::max(migliore, valore);
        alfa = std::max(alfa, valore);
        if (alfa >= beta) break;
    }
    return migliore;
}

int main(int argc, char* argv[]) {
    try {
        if (argc != 5) throw std::runtime_error("Uso: insegnante file esempi profondita seed");
        int quanti = std::stoi(argv[2]), profondita = std::stoi(argv[3]);
        if (quanti < 1 || profondita < 1 || profondita > 7) throw std::runtime_error("Parametri non validi");
        std::mt19937 casuale(std::stoul(argv[4]));
        std::ofstream file(argv[1]);
        if (!file) throw std::runtime_error("Impossibile creare gli esempi");
        for (int r=0; r<6; ++r) for (int c=0; c<7; ++c)
            for (auto d : {std::pair<int,int>{0,1}, {1,0}, {1,1}, {1,-1}})
                if (r+3*d.first < 6 && c+3*d.second >= 0 && c+3*d.second < 7) {
                    std::array<int,4> f{};
                    for (int k=0; k<4; ++k) f[k]=(r+k*d.first)*7+c+k*d.second;
                    finestre.push_back(f);
                }
        Griglia g{};
        int giocatore = 1, mosse = 0;
        for (int esempio=0; esempio<quanti; ++esempio) {
            std::array<int,7> valori;
            valori.fill(-30000);
            int vincenti = vittorie(g, giocatore), minacce = vittorie(g, 3-giocatore), blocchi = 0;
            for (int c : ordine) if (!g[c]) {
                int cella = inserisci(g, c, giocatore);
                if (vince(g, cella)) valori[c] = 10000 + profondita;
                else valori[c] = -cerca(g, 3-giocatore, profondita-1, -20000, 20000);
                if (minacce && !vittorie(g, 3-giocatore)) blocchi |= 1 << c;
                g[cella] = 0;
            }
            // Colori relativi: 1 = giocatore di turno, 2 = avversario.
            for (int v : g) file << (v == 0 ? 0 : (v == giocatore ? 1 : 2));
            for (int v : valori) file << ' ' << v;
            file << ' ' << vincenti << ' ' << blocchi << '\n';
            std::vector<int> libere, migliori;
            int massimo = *std::max_element(valori.begin(), valori.end());
            for (int c : ordine) if (!g[c]) {
                libere.push_back(c);
                if (valori[c] == massimo) migliori.push_back(c);
            }
            // Partite miste: esplorazione casuale e mosse dell'insegnante.
            auto& scelte = casuale()%100 < 55 ? libere : migliori;
            int cella = inserisci(g, scelte[casuale()%scelte.size()], giocatore);
            if (vince(g, cella) || ++mosse == 42) { g.fill(0); mosse=0; giocatore=1; }
            else giocatore = 3-giocatore;
            if ((esempio+1)%25000 == 0) std::cerr << esempio+1 << " esempi\n";
        }
        if (!file) throw std::runtime_error("Scrittura degli esempi fallita");
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
