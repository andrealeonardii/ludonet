#include "rete_forza4.hpp"
#include <iostream>
#include <stdexcept>

int main(int argc, char* argv[]) {
    try {
        if (argc != 2) throw std::runtime_error("Indicare il file dei pesi della rete.");
        std::string griglia;
        int colore;
        if (!(std::cin >> griglia >> colore)) throw std::runtime_error("Stato della partita assente.");
        ReteForza4 rete(argv[1]);
        std::cout << rete.scegli(griglia, colore) << '\n';
    } catch (const std::exception& errore) {
        std::cerr << errore.what() << '\n';
        return 1;
    }
}
