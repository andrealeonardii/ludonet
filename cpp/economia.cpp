#include "economia.hpp"
#include <stdexcept>

int premio(const std::string& esito, int parole) {
    if (esito == "vittoria") return 30;
    if (esito == "pareggio") return 15;
    if (esito == "sconfitta") return 0;
    if (esito == "cooperativo" && parole >= 0 && parole <= 8) return parole * 10;
    throw std::invalid_argument("Esito non valido.");
}

int acquista(int saldo, int prezzo, bool posseduto) {
    if (saldo < 0 || prezzo < 0) throw std::invalid_argument("Importo non valido.");
    if (posseduto) throw std::invalid_argument("Possiedi gia questo oggetto.");
    if (saldo < prezzo) throw std::invalid_argument("Ludocoin insufficienti.");
    return saldo - prezzo;
}
