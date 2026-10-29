(() => {
    "use strict";

    const dialogo = document.getElementById("editor-avatar");
    const apertura = document.getElementById("apri-avatar");
    const chiusura = document.getElementById("chiudi-avatar");
    const form = document.getElementById("form-avatar");
    const datiElemento = document.getElementById("dati-avatar");

    if (!dialogo || !apertura || !chiusura || !form || !datiElemento) return;

    const configurazione = JSON.parse(datiElemento.textContent);
    const categorie = ["testa", "corpo", "piedi"];
    let catalogo = configurazione.catalogo;
    let sceltaSalvata = { ...configurazione.scelta };
    let scelta = { ...sceltaSalvata };

    function articoli(parte) {
        return catalogo.filter((articolo) => articolo.parte === parte);
    }

    function articoloScelto(parte) {
        return articoli(parte).find(
            (articolo) => articolo.immagine === scelta[parte]
        );
    }

    function percorsoImmagine(parte, nome) {
        return `${configurazione.base}${parte}/${nome}.png?v=2`;
    }

    function aggiornaInterfaccia() {
        let bloccato = false;

        for (const parte of categorie) {
            const articolo = articoloScelto(parte);
            if (!articolo) continue;

            const anteprima = document.querySelector(`[data-anteprima="${parte}"]`);
            const input = form.querySelector(`input[name="${parte}"]`);
            const lucchetto = form.querySelector(`[data-acquista="${parte}"]`);

            anteprima.src = percorsoImmagine(parte, articolo.immagine);
            input.value = articolo.immagine;

            if (lucchetto) {
                lucchetto.hidden = Boolean(articolo.posseduto);
                lucchetto.dataset.cosmeticoId = articolo.id;
                lucchetto.querySelector("[data-prezzo]").textContent = articolo.prezzo;
                lucchetto.setAttribute(
                    "aria-label",
                    `Acquista ${articolo.nome}: ${articolo.prezzo} Ludocoin`
                );
            }

            bloccato ||= !articolo.posseduto;
        }

        document.getElementById("aiuto-avatar").hidden = !bloccato;
        document.getElementById("salva-avatar").disabled = bloccato;
    }

    function cambiaParte(parte, passo) {
        const opzioni = articoli(parte);
        if (!opzioni.length) return;

        let indice = opzioni.findIndex(
            (articolo) => articolo.immagine === scelta[parte]
        );
        indice = (indice + passo + opzioni.length) % opzioni.length;
        scelta[parte] = opzioni[indice].immagine;
        aggiornaInterfaccia();
    }

    async function aggiornaEconomia() {
        const risposta = await fetch(configurazione.economia, {
            headers: { Accept: "application/json" },
            cache: "no-store"
        });
        const dati = await risposta.json();

        if (!risposta.ok) throw new Error(dati.errore || "Saldo non disponibile.");

        catalogo = dati.catalogo;
        const saldoAvatar = document.getElementById("saldo-avatar");
        const saldoStanza = document.getElementById("saldo-monete");
        if (saldoAvatar) saldoAvatar.textContent = dati.saldo;
        if (saldoStanza) saldoStanza.textContent = dati.saldo;
        aggiornaInterfaccia();
    }

    async function acquista(pulsante) {
        const errore = document.getElementById("errore-avatar");
        errore.textContent = "";

        const corpo = new FormData();
        corpo.set("cosmetico_id", pulsante.dataset.cosmeticoId);

        try {
            const risposta = await fetch(configurazione.acquista, {
                method: "POST",
                body: corpo,
                headers: { Accept: "application/json" }
            });
            const dati = await risposta.json();

            catalogo = dati.catalogo || catalogo;
            if (!risposta.ok) throw new Error(dati.errore || "Acquisto non riuscito.");

            const saldoAvatar = document.getElementById("saldo-avatar");
            const saldoStanza = document.getElementById("saldo-monete");
            if (saldoAvatar) saldoAvatar.textContent = dati.saldo;
            if (saldoStanza) saldoStanza.textContent = dati.saldo;
            aggiornaInterfaccia();
        } catch (problema) {
            errore.textContent = problema.message;
        }
    }

    apertura.addEventListener("click", async () => {
        scelta = { ...sceltaSalvata };
        document.getElementById("errore-avatar").textContent = "";
        aggiornaInterfaccia();
        dialogo.showModal();

        try {
            await aggiornaEconomia();
        } catch (problema) {
            document.getElementById("errore-avatar").textContent = problema.message;
        }
    });

    chiusura.addEventListener("click", () => {
        scelta = { ...sceltaSalvata };
        dialogo.close();
    });

    dialogo.addEventListener("cancel", () => {
        scelta = { ...sceltaSalvata };
    });

    form.addEventListener("click", (evento) => {
        const freccia = evento.target.closest("[data-parte][data-passo]");
        if (freccia) {
            cambiaParte(freccia.dataset.parte, Number(freccia.dataset.passo));
            return;
        }

        const lucchetto = evento.target.closest("[data-acquista]");
        if (lucchetto) acquista(lucchetto);
    });

    form.addEventListener("submit", async (evento) => {
        evento.preventDefault();
        const errore = document.getElementById("errore-avatar");
        errore.textContent = "";

        try {
            const risposta = await fetch(form.action, {
                method: "POST",
                body: new FormData(form),
                headers: { Accept: "application/json" }
            });
            const dati = await risposta.json();
            if (!risposta.ok) throw new Error(dati.errore || "Salvataggio non riuscito.");

            sceltaSalvata = { ...scelta };
            for (const parte of categorie) {
                const miniatura = document.querySelector(`[data-mini="${parte}"]`);
                if (miniatura) {
                    miniatura.src = percorsoImmagine(parte, sceltaSalvata[parte]);
                }
            }
            dialogo.close();
        } catch (problema) {
            errore.textContent = problema.message;
        }
    });

    aggiornaInterfaccia();
})();