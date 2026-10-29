// Connessioni WebSocket, stanze e accesso concorrente alla mappa.
package main

import (
	"net/http"
	"net/url"
	"sync"

	"github.com/gorilla/websocket"
)

type server struct {
	chiave string
	mutex  sync.Mutex
	// Ogni connessione segue una stanza oppure la lista pubblica "lobby".
	connessioni map[*websocket.Conn]string
}

func codiceValido(codice string) bool {
	if len(codice) != 6 {
		return false
	}
	for _, cifra := range codice {
		if cifra < '0' || cifra > '9' {
			return false
		}
	}
	return true
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		origine, err := url.Parse(r.Header.Get("Origin"))
		if err != nil || (origine.Scheme != "http" && origine.Scheme != "https") {
			return false
		}
		// Accetta localhost e l'indirizzo LAN effettivamente usato per raggiungere
		// il server, ma rifiuta siti di terze parti con un'origine diversa.
		destinazione := &url.URL{Host: r.Host}
		return origine.Hostname() == destinazione.Hostname()
	},
}

func (s *server) rimuovi(conn *websocket.Conn) {
	s.mutex.Lock()
	delete(s.connessioni, conn)
	s.mutex.Unlock()
	conn.Close()
}

func (s *server) collega(w http.ResponseWriter, r *http.Request) {
	codice := r.URL.Query().Get("stanza")
	if r.Method != http.MethodGet || (codice != "lobby" && !codiceValido(codice)) {
		http.Error(w, "Richiesta non valida", http.StatusBadRequest)
		return
	}
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer s.rimuovi(conn)

	s.mutex.Lock()
	s.connessioni[conn] = codice
	err = inviaAvviso(conn, codice) // Recupera gli ingressi precedenti al collegamento.
	s.mutex.Unlock()
	if err != nil {
		return
	}

	// net/http gestisce già ogni connessione in modo concorrente.
	// Leggiamo per rilevare quando il browser chiude il WebSocket.
	conn.SetReadLimit(1024)
	for {
		_, _, err = conn.ReadMessage()
		if err != nil {
			return
		}
	}
}
