(() => {
    "use strict";

    for (const dettagli of document.querySelectorAll(".codice-personale")) {
        dettagli.open = false;
        const riepilogo = dettagli.querySelector("summary");

        function aggiornaEtichetta() {
            if (riepilogo) {
                riepilogo.setAttribute("aria-expanded", String(dettagli.open));
            }
        }

        dettagli.addEventListener("toggle", aggiornaEtichetta);
        aggiornaEtichetta();
    }
})();