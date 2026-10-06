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

## Unterstützung

Dieses Projekt wird unabhängig und privat entwickelt und kostenlos bereitgestellt. Freiwillige Unterstützung hilft bei Infrastruktur, Servern, Domains, Tests, Wartung und Weiterentwicklung.

- [PayPal](https://paypal.me/CoYoDuDe)
- [Buy Me a Coffee](https://www.buymeacoffee.com/CoYoDuDe)
- [Weitere Projekte und Informationen](https://dnsmith.net/)

Unterstützung ist freiwillig. Es gibt keinen Abo-Zwang und daraus entsteht kein Anspruch auf bestimmte Funktionen oder persönlichen Support.

## Gefuehrte Ersteinrichtung ab v1.2

Nach der Installation als root auf dem Venus-Geraet ausfuehren:

```sh
python3 /data/SSHTunnel/configure.py
```

Server und Benutzer einmal angeben. Den angezeigten Hostschluessel-Fingerabdruck unabhaengig am Server pruefen; dort zum Beispiel `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` verwenden. Der Assistent erzeugt einen eigenen Schluessel auf dem Pi. OpenSSH fragt bei Bedarf einmal nach dem vorhandenen Serverpasswort; das Addon speichert es nicht. Der private Pi-Schluessel bleibt auf dem Pi.

Der Server benoetigt OpenSSH mit `restrict`/`permitlisten` und die Standardprogramme `flock`, `awk`, `mktemp`. Der installierte Schluessel darf nur die ausgewaehlten Loopback-Tunnelports oeffnen; Shell, PTY, Agent- und X11-Forwarding sind gesperrt. Ausgehende lokale Weiterleitungen sind auf den ungenutzten Port localhost:1 begrenzt. Bestehende andere Server-Schluessel bleiben erhalten.

Bei einem Server ohne Passwortlogin `--prepare-only` verwenden, den ausgegebenen Befehl ueber den vorhandenen Administratorzugang ausfuehren und den Assistenten mit `--skip-provision` wiederholen. `--port` setzt einen abweichenden SSH-Serverport. `--fingerprint` nimmt einen bereits unabhaengig bestaetigten Fingerabdruck entgegen.

Standardmaessig wird nur der SSH-Ruecktunnel (Server localhost:2201 auf Pi localhost:22) aktiviert. `--remote-web-port 8081` aktiviert zusaetzlich den Webtunnel; zuvor muss der externe Reverse Proxy TLS und einen Anmeldeschutz erhalten. Die lokale Venus-Konsole kann ungeschuetzt sein. Keine Tunnelports oeffentlich freigeben.

Die abschliessende Schluesselpruefung bestaetigt die SSH-Anmeldung. Eventuelle belegte oder serverseitig gesperrte Weiterleitungsports erscheinen im Dienstlog `/var/log/com.coyodude.sshtunnel/current`.
