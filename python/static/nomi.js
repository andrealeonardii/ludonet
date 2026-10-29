// Il conto alla rovescia è locale; il server decide quando le risposte sono chiuse.
let timerNomi;
let attesaBozza;
let bozzaInCorso = false;
let bozzaDaInviare = null;

function avviaTimerNomi() {
    clearTimeout(timerNomi);
    const timer = document.getElementById("timer-nomi");
    if (!timer) return;
    const fine = performance.now() + Number(timer.dataset.secondi) * 1000;
    async function aggiorna() {
        if (!timer.isConnected) return;
        const secondi = Math.max(0, Math.ceil((fine - performance.now()) / 1000));
        timer.querySelector("strong").textContent = secondi;
        if (secondi > 0) {
            timerNomi = setTimeout(aggiorna, 100);
            return;
        }
        document.querySelectorAll('.form-nomi input, .form-nomi button').forEach(e => e.disabled = true);
        try {
            const risposta = await fetch(timer.dataset.url, {method: "POST"});
            if (risposta.status === 401) { window.location.replace("/"); return; }
            if (!risposta.ok) throw new Error("Errore nella chiusura della manche.");
            await aggiornaPartecipanti();
        } catch (errore) {
            timer.title = "Tempo scaduto. Riconnessione in corso…";
            timerNomi = setTimeout(aggiorna, 1000);
        }
    }
    aggiorna();
}

async function salvaBozzaNomi() {
    if (bozzaInCorso) return;
    bozzaInCorso = true;
    try {
        while (bozzaDaInviare) {
            const bozza = bozzaDaInviare;
            bozzaDaInviare = null;
            const risposta = await fetch(bozza.url, {method: "POST", body: bozza.dati});
            if (risposta.status === 401) { window.location.replace("/"); return; }
            if (risposta.status === 409) { await aggiornaPartecipanti(); return; }
            if (!risposta.ok) throw new Error("Salvataggio non riuscito. Controlla la connessione.");
            const errore = document.getElementById("errore-bozza");
            if (errore) errore.textContent = "";
        }
    } catch (problema) {
        const errore = document.getElementById("errore-bozza");
        if (errore) errore.textContent = problema.message;
    } finally {
        bozzaInCorso = false;
    }
}

document.addEventListener("input", evento => {
    const form = evento.target.closest(".form-nomi");
    if (!form) return;
    bozzaDaInviare = {url: form.dataset.bozza, dati: new FormData(form)};
    clearTimeout(attesaBozza);
    attesaBozza = setTimeout(salvaBozzaNomi, 100);
});
