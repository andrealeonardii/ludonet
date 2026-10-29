#include "rete_forza4.hpp"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <limits>
#include <stdexcept>

ReteForza4::ReteForza4(const std::string& percorso) {
    std::ifstream file(percorso);
    std::string formato;
    if (!(file >> formato) || formato != "NICKGAME_FORZA4_V1")
        throw std::runtime_error("File dei pesi assente o formato non valido.");
    const int dimensioni[] = {84, 128, 64, 7};
    for (int i = 0; i < 3; ++i) {
        Strato strato;
        if (!(file >> strato.ingressi >> strato.uscite) ||
            strato.ingressi != dimensioni[i] || strato.uscite != dimensioni[i + 1])
            throw std::runtime_error("Dimensioni della rete non valide.");
        strato.pesi.resize(strato.ingressi * strato.uscite);
        strato.bias.resize(strato.uscite);
        for (auto* valori : {&strato.pesi, &strato.bias})
            for (float& valore : *valori)
                if (!(file >> valore) || !std::isfinite(valore))
                    throw std::runtime_error("Pesi della rete incompleti o non validi.");
        strati.push_back(strato);
    }
    if (file >> formato) throw std::runtime_error("Dati inattesi alla fine dei pesi.");
}

std::vector<float> ReteForza4::valuta(const std::string& griglia, int colore) const {
    if (griglia.size() != 42 || griglia.find_first_not_of("012") != std::string::npos ||
        (colore != 1 && colore != 2))
        throw std::runtime_error("Stato della partita non valido.");
    // Primo piano: mie pedine. Secondo piano: pedine dell'avversario.
    std::vector<float> valori(84, 0);
    for (int i = 0; i < 42; ++i) {
        valori[i] = griglia[i] == '0' + colore;
        valori[42 + i] = griglia[i] == '0' + (3 - colore);
    }
    for (std::size_t livello = 0; livello < strati.size(); ++livello) {
        const auto& strato = strati[livello];
        std::vector<float> uscita(strato.uscite);
        for (int n = 0; n < strato.uscite; ++n) {
            float somma = strato.bias[n];
            for (int i = 0; i < strato.ingressi; ++i)
                somma += valori[i] * strato.pesi[n * strato.ingressi + i];
            // ReLU solo negli strati intermedi; l'ultimo produce sette punteggi.
            uscita[n] = livello + 1 < strati.size() ? std::max(0.0f, somma) : somma;
            if (!std::isfinite(uscita[n])) throw std::runtime_error("Calcolo della rete non valido.");
        }
        valori = uscita;
    }
    return valori;
}

int ReteForza4::scegli(const std::string& griglia, int colore) const {
    const auto punteggi = valuta(griglia, colore);
    int scelta = -1;
    float migliore = -std::numeric_limits<float>::infinity();
    for (int colonna = 0; colonna < 7; ++colonna) {
        // L'unico filtro esterno alla rete esclude le colonne piene.
        if (griglia[colonna] == '0' && punteggi[colonna] > migliore) {
            migliore = punteggi[colonna];
            scelta = colonna;
        }
    }
    if (scelta == -1) throw std::runtime_error("Nessuna colonna disponibile.");
    return scelta;
}
