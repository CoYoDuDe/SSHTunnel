# SSHTunnel

Eigenes SetupHelper-Paket für einen benutzerkonfigurierbaren SSH-Tunnel, getrennt vom systemeigenen Victron-`ssh-tunnel`.

Das Paket baut auf [SetupHelper](https://github.com/kwindrem/SetupHelper) von [kwindrem](https://github.com/kwindrem) auf.

## Zweck

- keine festen Serverdaten im Repository
- Benutzer tragen ihre eigenen Daten im GUI ein
- Werte liegen in `com.victronenergy.settings` und bleiben bei Paket-Updates erhalten
- der Standard-`KeyPath` ist `/data/keys/ssh_host_rsa_key`

## Installation

Voraussetzung:

- [SetupHelper](https://github.com/kwindrem/SetupHelper) von [kwindrem](https://github.com/kwindrem) ist bereits installiert

Im `Package manager`:

- `PackageName`: `SSHTunnel`
- `GitHubUser`: `CoYoDuDe`
- `GitHubBranch`: `main`

## GUI

Nach der Installation erscheint `SSH Tunnel` in den Einstellungen.

Konfigurierbar:

- Dienst aktiv
- Server
- Benutzer
- Schlüsselpfad
- `StrictHostKeyChecking`
- Reconnect-Verzögerung
- zwei optionale Tunnel mit je Remote-Port, lokalem Host und lokalem Port

## Hinweise

- Standardmäßig deaktiviert
- keine eingebetteten privaten Zielserverdaten
- kein Überschreiben des systemeigenen Victron-`ssh-tunnel`
- nutzt einen eigenen Dienst `com.coyodude.sshtunnel`
- für den ersten Paralleltest zuerst freie Remote-Ports verwenden, damit es keine Port-Kollision mit dem bestehenden Tunnel gibt
- Passwort-Login ist bewusst nicht vorgesehen; der Dienst ist für Schlüssel-basierte Anmeldung ausgelegt
