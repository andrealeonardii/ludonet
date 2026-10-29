// Interfaccia a riga di comando: Python passa argomenti e legge un numero.
#include "economia.hpp"
#include <charconv>
#include <iostream>
#include <stdexcept>
#include <string>

int numero(const std::string& testo) {
    int valore = 0;
    const auto risultato = std::from_chars(testo.data(), testo.data() + testo.size(), valore);
    if (risultato.ec != std::errc{} || risultato.ptr != testo.data() + testo.size() || valore < 0)
        throw std::invalid_argument("Numero non valido.");
    return valore;
}

int main(int argc, char* argv[]) {
    try {
        if (argc == 4 && std::string(argv[1]) == "premio") {
            std::cout << premio(argv[2], numero(argv[3])) << '\n';
        } else if (argc == 5 && std::string(argv[1]) == "acquista") {
            const int posseduto = numero(argv[4]);
            if (posseduto > 1) throw std::invalid_argument("Possesso non valido.");
            std::cout << acquista(numero(argv[2]), numero(argv[3]), posseduto == 1) << '\n';
        } else {
            throw std::invalid_argument("Comando non valido.");
        }
        return 0;
    } catch (const std::exception& errore) {
        std::cerr << errore.what() << '\n';
        return 1;
    }
}
