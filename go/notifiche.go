// Ricezione degli avvisi da Flask e invio ai browser della stanza.
package main

import (
	"crypto/hmac"
	"net/http"
	"time"

	"github.com/gorilla/websocket"
)

// Chiamata sempre con il mutex acquisito: una sola scrittura per volta.
func inviaAvviso(conn *websocket.Conn, canale string) error {
	tipo := "partecipanti_aggiornati"
	if canale == "lobby" {
		tipo = "stanze_aggiornate"
	}
	conn.SetWriteDeadline(time.Now().Add(2 * time.Second))
	return conn.WriteJSON(map[string]string{"tipo": tipo})
}

func (s *server) notifica(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Metodo non consentito", http.StatusMethodNotAllowed)
		return
	}
	if !hmac.Equal([]byte(r.Header.Get("Authorization")), []byte("Bearer "+s.chiave)) {
		http.Error(w, "Accesso non autorizzato", http.StatusForbidden)
		return
	}
	codice := r.URL.Query().Get("stanza")
	if !codiceValido(codice) {
		http.Error(w, "Codice non valido", http.StatusBadRequest)
		return
	}
	s.mutex.Lock()
	for conn, stanza := range s.connessioni {
		if stanza == codice || stanza == "lobby" {
			if err := inviaAvviso(conn, stanza); err != nil {
				conn.Close()
				delete(s.connessioni, conn)
			}
		}
	}
	s.mutex.Unlock()
	w.WriteHeader(http.StatusNoContent)
}
