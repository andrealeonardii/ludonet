const stanze = document.getElementById("stanze");
const nessunaStanza = document.getElementById("nessuna-stanza");
let collegamento;
let paginaChiusa = false;
let aggiornamentoInCorso = false;
let aggiornamentoRichiesto = false;

// Riusa il form esistente: la validazione definitiva rimane sul server.
stanze.addEventListener("click", (evento) => {
    const pulsante = evento.target.closest("button[data-codice]");
    if (!pulsante) return;
    const ospite = document.getElementById("username-ospite");
    if (ospite) {
        ospite.value = ospite.value.trim();
        if (!ospite.reportValidity()) return;
    }
    document.getElementById("codice").value = pulsante.dataset.codice;
    document.getElementById("accesso").requestSubmit(document.getElementById("entra-con-codice"));
});

function mostraStanze(elenco) {
    const righe = [];
    for (const stanza of elenco) {
        const riga = document.createElement("li");
        riga.className = "riga-stanza";
        riga.dataset.codice = stanza.codice;
        const informazioni = document.createElement("div");
        const titolo = document.createElement("strong");
        titolo.textContent = "Stanza " + stanza.codice;
        const dettagli = document.createElement("p");
        dettagli.textContent = "Admin: " + stanza.admin + " · Partecipanti: " + stanza.partecipanti;
        informazioni.append(titolo, dettagli);
        const pulsante = document.createElement("button");
        pulsante.type = "button";
        pulsante.className = "btn-secondary";
        pulsante.textContent = "Entra";
        pulsante.dataset.codice = stanza.codice;
        pulsante.setAttribute("aria-label", "Entra nella stanza " + stanza.codice);
        riga.append(informazioni, pulsante);
        righe.push(riga);
    }
    stanze.replaceChildren(...righe);
    nessunaStanza.hidden = elenco.length > 0;
}

async function aggiornaStanze() {
    aggiornamentoRichiesto = true;
    if (aggiornamentoInCorso) return;
    aggiornamentoInCorso = true;
    try {
        while (aggiornamentoRichiesto) {
            aggiornamentoRichiesto = false;
            const risposta = await fetch(stanze.dataset.url, {cache: "no-store"});
            if (!risposta.ok) throw new Error("Elenco non disponibile");
            mostraStanze(await risposta.json());
        }
    } catch (errore) {
        if (!paginaChiusa) setTimeout(aggiornaStanze, 3000);
    } finally {
        aggiornamentoInCorso = false;
    }
}

function connettiStanze() {
    if (paginaChiusa) return;
    const indirizzo = new URL(stanze.dataset.websocket);
    indirizzo.hostname = window.location.hostname;
    indirizzo.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    collegamento = new WebSocket(indirizzo);
    collegamento.onmessage = (evento) => {
        const messaggio = JSON.parse(evento.data);
        if (messaggio.tipo === "stanze_aggiornate") aggiornaStanze();
    };
    collegamento.onclose = () => {
        if (!paginaChiusa) setTimeout(connettiStanze, 3000);
    };
    collegamento.onerror = () => collegamento.close();
}

window.addEventListener("pagehide", () => {
    paginaChiusa = true;
    if (collegamento) collegamento.close();
});
window.addEventListener("pageshow", (evento) => {
    if (evento.persisted) {
        paginaChiusa = false;
        connettiStanze();
    }
});
connettiStanze();
