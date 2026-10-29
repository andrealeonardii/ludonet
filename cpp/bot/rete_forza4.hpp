#pragma once
#include <string>
#include <vector>

// Solo inferenza: nessuna ricerca di mosse future o correzione strategica.
class ReteForza4 {
public:
    explicit ReteForza4(const std::string& file);
    std::vector<float> valuta(const std::string& griglia, int colore) const;
    int scegli(const std::string& griglia, int colore) const;

private:
    struct Strato {
        int ingressi;
        int uscite;
        std::vector<float> pesi;
        std::vector<float> bias;
    };
    std::vector<Strato> strati;
};
