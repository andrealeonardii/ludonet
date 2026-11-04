const elenco = document.getElementById("partecipanti");
const stato = document.getElementById("sincronizzazione");
let socket;
let chiusuraPagina = false;
let aggiornamentoInCorso = false;
let aggiornamentoRichiesto = false;
let sequenzaPartita = 0;
let mossaInCorso = false;
const durataAnimazionePedina = 360;
const animazioniPedine = new Map();
let partitaAnimata = "";

function animaNuovePedine(pannello, precedenteId, pedinePrecedenti) {
    const partitaId = pannello.querySelector("[data-partita-id]")?.dataset.partitaId;
    if (partitaId !== partitaAnimata) {
        animazioniPedine.clear();
        partitaAnimata = partitaId;
    }
    if (!partitaId || precedenteId !== partitaId) return;
    const adesso = performance.now();
    pannello.querySelectorAll(".pedina").forEach((pedina, indice) => {
        if (pedinePrecedenti[indice] === "0" && pedina.dataset.valore !== "0") {
            animazioniPedine.set(indice, adesso);
        }
        if (!animazioniPedine.has(indice)) return;
        const trascorso = adesso - animazioniPedine.get(indice);
        if (trascorso >= durataAnimazionePedina) {
            animazioniPedine.delete(indice);
            return;
        }
        // Un secondo aggiornamento riprende l'animazione dallo stesso istante.
        pedina.style.setProperty("--ritardo-pedina", `${-trascorso}ms`);
        pedina.classList.add("pedina-appena-giocata");
    });
}

// La vista è condivisa nel database: solo l'admin può cambiarla per tutti.
function aggiornaVista() {
    const dati = document.querySelector("[data-partita-id]");
    if (dati?.dataset.saldoMonete !== undefined) {
        for (const id of ["saldo-monete", "saldo-avatar"]) {
            const saldo = document.getElementById(id);
            if (saldo) saldo.textContent = dati.dataset.saldoMonete;
        }
    }
    const partita = Boolean(dati?.dataset.partitaId);
    const vistaGioco = partita && dati.dataset.inSala === "0";
    const vistaForza4 = vistaGioco && dati.dataset.gioco === "forza4";
    document.querySelector(".layout-stanza").classList.toggle("vista-partita", vistaGioco);
    document.querySelector(".layout-stanza").classList.toggle("vista-forza4", vistaForza4);
    document.querySelector(".intestazione-stanza").classList.toggle("intestazione-partita", vistaGioco);
    const titolo = document.getElementById("titolo-gioco-header");
    titolo.hidden = !vistaGioco;
    titolo.textContent = dati?.dataset.nomeGioco || "";
    const fonteGiocatori = document.getElementById("giocatori-partita");
    for (const lato of ["sinistra", "destra"]) {
        const contenitore = document.getElementById(`giocatore-partita-${lato}`);
        contenitore.hidden = !vistaGioco;
        const fonte = fonteGiocatori?.content.querySelector(`[data-giocatore="${lato}"]`);
        if (fonte && contenitore.innerHTML !== fonte.innerHTML) {
            contenitore.replaceChildren(...Array.from(fonte.childNodes, nodo => nodo.cloneNode(true)));
        }
    }
    const monete = document.getElementById("monete-stanza");
    monete.hidden = vistaGioco || monete.dataset.ospite === "1";
    document.getElementById("sala").hidden = vistaGioco;
    document.getElementById("saluto-stanza").hidden = vistaGioco;
    const comandiIntestazione = document.querySelector(".comandi-intestazione");
    if (comandiIntestazione) comandiIntestazione.hidden = vistaGioco;
    const torna = document.getElementById("torna-stanza");
    const riprendi = document.getElementById("rientra-partita");
    if (torna) torna.hidden = !vistaGioco;
    if (riprendi) riprendi.hidden = !partita;
    document.getElementById("partita").hidden = partita && !vistaGioco;
}

async function aggiornaPartita() {
    const sequenza = ++sequenzaPartita;
    const pannello = document.getElementById("partita");
    const risposta = await fetch(pannello.dataset.url, {cache: "no-store"});
    if (risposta.status === 401) {
        window.location.replace("/");
        return;
    }
    if (!risposta.ok) throw new Error("Partita non disponibile. Riprova.");
    const html = await risposta.text();
    if (sequenza !== sequenzaPartita) return;
    const precedenteId = pannello.querySelector("[data-partita-id]")?.dataset.partitaId;
    const pedinePrecedenti = Array.from(pannello.querySelectorAll(".pedina"), pedina => pedina.dataset.valore);
    aggiornaPannello(pannello, html);
    animaNuovePedine(pannello, precedenteId, pedinePrecedenti);
    aggiornaVista();
    avviaTimerNomi();
}

document.getElementById("partita").addEventListener("submit", async (evento) => {
    const form = evento.target;
    if (!form.matches("form[data-mossa-forza4]") && !form.closest(".partita-multigioco")) return;
    evento.preventDefault();
    if (mossaInCorso || evento.submitter?.disabled) return;
    mossaInCorso = true;
    const corpo = new FormData(form);
    if (evento.submitter?.name) corpo.set(evento.submitter.name, evento.submitter.value);
    const pulsanti = Array.from(form.querySelectorAll("button:not(:disabled)"));
    pulsanti.forEach(pulsante => { pulsante.disabled = true; });
    const errorePrecedente = document.querySelector("#errore-mossa-forza4, #errore-azione-partita");
    if (errorePrecedente) errorePrecedente.hidden = true;
    try {
        const risposta = await fetch(form.action, {
            method: "POST", body: corpo, headers: {Accept: "application/json"}
        });
        if (risposta.status === 401) {
            window.location.replace("/");
            return;
        }
        const dati = await risposta.json().catch(() => ({errore: "Azione non disponibile. Riprova."}));
        await aggiornaPartita();
        if (!risposta.ok) throw new Error(dati.errore || "Azione non riuscita.");
    } catch (problema) {
        const errore = document.querySelector("#errore-mossa-forza4, #errore-azione-partita");
        if (errore) {
            errore.textContent = problema.message;
            errore.hidden = false;
        }
    } finally {
        mossaInCorso = false;
        pulsanti.forEach(pulsante => { if (pulsante.isConnected) pulsante.disabled = false; });
    }
});

function aggiornaPannello(pannello, html) {
    // Conserva il testo in scrittura e le spunte se partita, manche e fase sono uguali.
    const form = pannello.querySelector("form[data-conserva]");
    const campi = form ? Array.from(form.querySelectorAll("input:not([type=hidden])")) : [];
    const attivo = document.activeElement;
    const inizio = attivo?.selectionStart;
    const fine = attivo?.selectionEnd;
    const contenuto = pannello.querySelector(".contenuto-multigioco");
    const scorrimento = contenuto?.scrollTop || 0;
    const partitaPrecedente = pannello.querySelector("[data-partita-id]")?.dataset.partitaId;
    pannello.innerHTML = html;
    if (partitaPrecedente === pannello.querySelector("[data-partita-id]")?.dataset.partitaId) {
        const nuovoContenuto = pannello.querySelector(".contenuto-multigioco");
        if (nuovoContenuto) nuovoContenuto.scrollTop = scorrimento;
    }
    const nuovo = pannello.querySelector("form[data-conserva]");
    if (!form || !nuovo || form.dataset.conserva !== nuovo.dataset.conserva) return;
    for (const campo of campi) {
        const sostituto = Array.from(nuovo.querySelectorAll("input")).find(input =>
            input.name === campo.name && (campo.type !== "checkbox" || input.value === campo.value));
        if (!sostituto) continue;
        if (campo.type === "checkbox") sostituto.checked = campo.checked;
        else sostituto.value = campo.value;
        if (campo === attivo) {
            sostituto.focus({preventScroll: true});
            if (campo.type === "text") sostituto.setSelectionRange(inizio, fine);
        }
    }
}

async function aggiornaPartecipanti() {
    // Serializza le richieste per non mostrare una risposta vecchia dopo una nuova.
    aggiornamentoRichiesto = true;
    if (aggiornamentoInCorso) return;
    aggiornamentoInCorso = true;
    try {
        while (aggiornamentoRichiesto) {
            aggiornamentoRichiesto = false;
            const risposta = await fetch(elenco.dataset.url, {cache: "no-store"});
            if (risposta.status === 401) {
                window.location.replace("/");
                return;
            }
            if (!risposta.ok) throw new Error("Elenco non disponibile");
            const partecipanti = await risposta.json();
            const righe = partecipanti.map((utente) => {
                const riga = document.createElement("li");
                // textContent mostra il nome come testo, senza interpretarlo come HTML.
                riga.className = "partecipante";
                const nome = document.createElement("span");
                nome.textContent = utente.username;
                riga.append(nome);
                if (utente.is_bot) {
                    const ruolo = document.createElement("strong");
                    ruolo.textContent = "Rete neurale";
                    riga.append(ruolo);
                }
                if (utente.is_admin) {
                    const ruolo = document.createElement("strong");
                    riga.classList.add("partecipante-admin");
                    ruolo.className = "ruolo-admin";
                    ruolo.textContent = "Admin";
                    riga.append(ruolo);
                }
                if (elenco.dataset.admin === "1" && !utente.is_admin && !utente.is_bot) {
                    const form = document.createElement("form");
                    form.method = "post";
                    form.action = elenco.dataset.rimuovi;
                    form.className = "rimuovi-partecipante";
                    const pulsante = document.createElement("button");
                    pulsante.className = "btn-secondary";
                    pulsante.name = "username";
                    pulsante.value = utente.username;
                    pulsante.textContent = "Rimuovi";
                    pulsante.setAttribute("aria-label", `Rimuovi ${utente.username} dalla stanza`);
                    form.append(pulsante);
                    riga.append(form);
                }
                return riga;
            });
            elenco.replaceChildren(...righe);
            const aggiungiBot = document.querySelector("[data-bot-aggiungi]");
            const rimuoviBot = document.querySelector("[data-bot-rimuovi]");
            if (aggiungiBot) aggiungiBot.hidden = partecipanti.length !== 1;
            if (rimuoviBot) rimuoviBot.hidden = !partecipanti.some(utente => utente.is_bot);
            // Il server genera anche i pulsanti corretti per admin e partecipanti.
            for (const id of ["giochi", "partita"]) {
                if (id === "partita") {
                    await aggiornaPartita();
                    continue;
                }
                const pannello = document.getElementById(id);
                const rispostaPannello = await fetch(pannello.dataset.url, {cache: "no-store"});
                if (rispostaPannello.status === 401) {
                    window.location.replace("/");
                    return;
                }
                if (!rispostaPannello.ok) throw new Error("Pannello non disponibile");
                aggiornaPannello(pannello, await rispostaPannello.text());
            }
            aggiornaVista();
            const saldo = document.getElementById("saldo-monete");
            const rispostaSaldo = await fetch(saldo.dataset.url, {cache: "no-store"});
            if (!rispostaSaldo.ok) throw new Error("Saldo non disponibile");
            saldo.textContent = (await rispostaSaldo.json()).saldo;
            document.getElementById("saldo-avatar").textContent = saldo.textContent;
        }
        if (socket && socket.readyState === WebSocket.OPEN) {
            stato.textContent = "Partecipanti aggiornati in tempo reale.";
        }
    } catch (errore) {
        stato.textContent = "Aggiornamento non riuscito. Nuovo tentativo in corso…";
        if (!chiusuraPagina) setTimeout(aggiornaPartecipanti, 3000);
    } finally {
        aggiornamentoInCorso = false;
    }
}

async function connetti() {
    if (chiusuraPagina) return;
    stato.textContent = "Collegamento agli aggiornamenti…";
    try {
        const risposta = await fetch(stato.dataset.url, {cache: "no-store"});
        if (risposta.status === 401) {
            window.location.replace("/");
            return;
        }
        if (!risposta.ok) throw new Error("Collegamento non disponibile");
        const dati = await risposta.json();
        if (chiusuraPagina) return;
        socket = new WebSocket(dati.url);
        socket.onmessage = (evento) => {
            const messaggio = JSON.parse(evento.data);
            if (messaggio.tipo === "partecipanti_aggiornati") aggiornaPartecipanti();
        };
        socket.onclose = () => {
            if (!chiusuraPagina) {
                stato.textContent = "Aggiornamenti sospesi. Riconnessione in corso…";
                setTimeout(connetti, 3000);
            }
        };
        socket.onerror = () => socket.close();
    } catch (errore) {
        stato.textContent = "Collegamento non disponibile. Nuovo tentativo in corso…";
        if (!chiusuraPagina) setTimeout(connetti, 3000);
    }
}

window.addEventListener("pagehide", () => {
    chiusuraPagina = true;
    if (socket) socket.close();
});
window.addEventListener("pageshow", (evento) => {
    if (evento.persisted) {
        chiusuraPagina = false;
        connetti();
    }
});
aggiornaVista();
connetti();

avviaTimerNomi();
