# SSHTunnel

Erreichbarkeit des Venus-Geräts über einen eigenen SSH-Server. Der normale Victron-Tunnel bleibt erhalten.

## Installation

[SetupHelper](https://github.com/kwindrem/SetupHelper) installieren. Im Paketmanager: Paket `SSHTunnel`, GitHub-Benutzer `CoYoDuDe`, Branch `main`.

## Einrichtung

Nach der Installation als root auf dem Venus-Gerät ausführen:

```sh
python3 /data/SSHTunnel/configure.py
```

1. Eigenen Server und Benutzer angeben.
2. Den angezeigten Fingerabdruck unabhängig am Server prüfen, etwa mit `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`.
3. Der Assistent erzeugt einen eigenen Schlüssel auf dem Pi und richtet den gewählten Rücktunnel ein. Ein gegebenenfalls abgefragtes Serverpasswort wird nicht gespeichert.

Im Menü **Einstellungen → SSH Tunnel** lassen sich Dienst, Server, Schlüssel und Tunnelports ändern. Neue Installationen starten deaktiviert und ohne Serveradresse. Bestehende Einstellungen bleiben erhalten.

## Zugriff und Ports

Der Standard-Rücktunnel verbindet **Server localhost:2201 → Pi localhost:22**. Mit `--remote-web-port 8081` ist zusätzlich die Webkonsole möglich. Dafür zuerst einen Reverse Proxy mit TLS und Anmeldeschutz einrichten. Tunnelports bleiben auf dem Server an localhost gebunden; keine ungeschützte Konsole öffentlich freigeben.

Der Server braucht OpenSSH mit `restrict`/`permitlisten` sowie `flock`, `awk` und `mktemp`. Der eingerichtete Schlüssel darf nur die ausgewählten Rücktunnel öffnen; Shell, PTY, Agent- und X11-Weiterleitung sind gesperrt. Andere vorhandene Server-Schlüssel bleiben erhalten.

Ohne Server-Passwortlogin: `--prepare-only` verwenden, den ausgegebenen Befehl über den vorhandenen Administratorzugang ausführen und mit `--skip-provision` fortsetzen. `--port` setzt einen anderen SSH-Port, `--fingerprint` einen bereits unabhängig bestätigten Fingerabdruck.

## Updates und Diagnose

Updates und Entfernen über SetupHelper. Eigene Serverdaten und private Schlüssel gehören nicht ins Repository. Der private Pi-Schlüssel bleibt auf dem Pi. Fehler oder belegte Ports stehen in `/var/log/com.coyodude.sshtunnel/current`.

## Unterstützung

Die Pakete sind kostenlos. Freiwillige Unterstützung: [PayPal](https://paypal.me/CoYoDuDe), [Buy Me a Coffee](https://www.buymeacoffee.com/CoYoDuDe), [weitere Projekte](https://dnsmith.net/). Kein Abo-Zwang.
