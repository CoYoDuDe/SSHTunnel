# SSHTunnel

Eigenes SetupHelper-Paket für einen benutzerkonfigurierbaren SSH-Tunnel, getrennt vom systemeigenen Victron-`ssh-tunnel`.

## Zweck

- keine festen Serverdaten im Repository
- Benutzer tragen ihre eigenen Daten im GUI ein
- Werte liegen in `com.victronenergy.settings` und bleiben bei Paket-Updates erhalten
- leerer `KeyPath` nutzt automatisch bekannte Standardpfade wie `/data/keys/ssh_host_rsa_key`

## Installation

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
