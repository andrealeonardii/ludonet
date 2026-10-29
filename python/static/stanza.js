const elenco = document.getElementById("partecipanti");
const stato = document.getElementById("sincronizzazione");
let socket;
let chiusuraPagina = false;
let aggiornamentoInCorso = false;
let aggiornamentoRichiesto = false;

// La vista è condivisa nel database: solo l'admin può cambiarla per tutti.
function aggiornaVista() {
    const dati = document.querySelector("[data-partita-id]");
    const partita = Boolean(dati?.dataset.partitaId);
    const vistaGioco = partita && dati.dataset.inSala === "0";
    document.getElementById("sala").hidden = vistaGioco;
    document.getElementById("saluto-stanza").hidden = vistaGioco;
    document.getElementById("codice-stanza").hidden = vistaGioco;
    document.getElementById("logout-stanza").hidden = vistaGioco;
    const torna = document.getElementById("torna-stanza");
    const riprendi = document.getElementById("rientra-partita");
    if (torna) torna.hidden = !vistaGioco;
    if (riprendi) riprendi.hidden = !partita;
    document.getElementById("partita").hidden = partita && !vistaGioco;
}

function aggiornaPannello(pannello, html) {
    // Conserva il testo in scrittura e le spunte se partita, manche e fase sono uguali.
    const form = pannello.querySelector("form[data-conserva]");
    const campi = form ? Array.from(form.querySelectorAll("input:not([type=hidden])")) : [];
    const attivo = document.activeElement;
    const inizio = attivo?.selectionStart;
    const fine = attivo?.selectionEnd;
    pannello.innerHTML = html;
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
                return riga;
            });
            elenco.replaceChildren(...righe);
            const aggiungiBot = document.querySelector("[data-bot-aggiungi]");
            const rimuoviBot = document.querySelector("[data-bot-rimuovi]");
            if (aggiungiBot) aggiungiBot.hidden = partecipanti.length !== 1;
            if (rimuoviBot) rimuoviBot.hidden = !partecipanti.some(utente => utente.is_bot);
            // Il server genera anche i pulsanti corretti per admin e partecipanti.
            for (const id of ["giochi", "partita"]) {
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
            avviaTimerNomi();
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
connetti();

avviaTimerNomi();
