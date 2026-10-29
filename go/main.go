// Avvio e configurazione del server locale.
package main

import (
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gorilla/websocket"
)

func main() {
	percorso := os.Getenv("NICKGAME_SECRET_FILE")
	if percorso == "" {
		percorso = "../python/instance/secret.key"
	}
	chiave, err := os.ReadFile(percorso)
	if err != nil || len(chiave) < 32 {
		log.Fatal("Chiave locale assente o non valida: avvia prima Flask.")
	}
	porta := os.Getenv("NICKGAME_GO_PORT")
	if porta == "" {
		porta = "50011"
	}
	host := os.Getenv("NICKGAME_GO_HOST")
	if host == "" {
		host = "127.0.0.1"
	}
	s := &server{chiave: string(chiave), connessioni: make(map[*websocket.Conn]string)}
	mux := http.NewServeMux()
	mux.HandleFunc("/ws", s.collega)
	mux.HandleFunc("/notifica", s.notifica)
	serverHTTP := &http.Server{
		Addr:              host + ":" + porta,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}
	log.Printf("Sincronizzazione Go su http://%s", serverHTTP.Addr)
	log.Fatal(serverHTTP.ListenAndServe())
}
