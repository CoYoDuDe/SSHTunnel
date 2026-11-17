# SSHTunnel

## Deutsch

Macht ein Venus-Gerät über einen eigenen SSH-Server erreichbar; der Victron-Tunnel bleibt erhalten.

**Voraussetzungen:** Venus OS mit Python/OpenSSH und SetupHelper; eigener SSH-Server mit erlaubten Rücktunnelports. Der zusätzliche RoadLink-VPN-Modus braucht einen geprüften RoadLink-Managementpfad. Eine universelle GX-/Firmwarefreigabe ist noch nicht abgeschlossen.

**Installation:** [SetupHelper](https://github.com/kwindrem/SetupHelper); Paket `SSHTunnel`, GitHub-Benutzer `CoYoDuDe`, Branch `main`.

**Einrichtung/Bedienung:** Als root `python3 /data/SSHTunnel/configure.py` ausführen. Eigenen Server/Benutzer angeben und dessen Hostschlüssel unabhängig prüfen. Danach Einstellungen → SSH Tunnel verwenden. Neuinstallationen starten deaktiviert, ohne Serveradresse; vorhandene Einstellungen bleiben erhalten. Der private Geräteschlüssel bleibt lokal, ein abgefragtes Serverpasswort wird nicht gespeichert.

**Zugriff/Grenzen:** Standard: Server `localhost:2201` → Gerät `localhost:22`; optionale Webweiterleitung mit `--remote-web-port 8081`. Webzugriff braucht eigenen TLS-Proxy und Anmeldung. Ports bleiben am Server auf Loopback begrenzt. RoadLink-VPN als Verbindungsweg nutzt ausschließlich einen aktuell geprüften VPN; ohne diesen besteht keine Verbindung. Keepalive ist keine garantierte Wiederherstellungszeit.

**Zahleneingaben:** Im Venus-Menü sind Ports ganze Zahlen von 1 bis 65535, die Reconnect-Verzögerung von 1 bis 600 Sekunden. Ungültige Eingaben bleiben zur Korrektur im Feld und ändern den gespeicherten Wert nicht.

**Update/Deinstallation/Recovery:** SetupHelper verwenden, private Konfiguration/Schlüssel separat sichern. Vor Umstellung unabhängigen Geräte- und Serverzugang behalten; beide Ports nach Unterbrechung prüfen. Diagnose: `/var/log/com.coyodude.sshtunnel/current`. Fremde Sitzungen/Portinhaber nicht beenden.

**Gemeinsame Menüs:** Schlägt die Rücknahme eines Menüpatches fehl, bleiben die betroffene Datei und ihre Paketeinträge erhalten. Die Deinstallation meldet einen Fehler; nach Behebung über SetupHelper erneut versuchen.

## English

Makes a Venus device reachable through your own SSH server; the Victron tunnel is preserved.

**Requirements:** Venus OS with Python/OpenSSH and SetupHelper; your own SSH server allowing the selected reverse ports. The optional RoadLink-VPN mode requires a verified RoadLink management path. Universal GX/firmware acceptance is pending.

**Installation:** Use [SetupHelper](https://github.com/kwindrem/SetupHelper); package `SSHTunnel`, GitHub user `CoYoDuDe`, branch `main`.

**Configuration/operation:** Run `python3 /data/SSHTunnel/configure.py` as root. Enter your server/user and independently verify its host key. Then use Settings → SSH Tunnel. Fresh installations start disabled without a server address; existing settings are preserved. The device private key stays local; a requested server password is not stored.

**Access/limits:** Default: server `localhost:2201` → device `localhost:22`; optional web forwarding with `--remote-web-port 8081`. Web access needs your own TLS proxy and authentication. Server ports remain loopback-only. RoadLink-VPN transport exclusively uses a currently verified VPN; without it there is no connection. Keepalive does not guarantee recovery time.

**Numeric input:** In the Venus menu, ports must be whole numbers from 1 to 65535 and the reconnect delay from 1 to 600 seconds. Invalid input stays in the field for correction without changing the saved value.

**Update/uninstall/recovery:** Use SetupHelper and separately back up private configuration/keys. Keep independent device/server access before switching; test both ports after interruptions. Diagnostics: `/var/log/com.coyodude.sshtunnel/current`. Do not terminate unrelated sessions or port owners.

**Shared menus:** If reversing a menu patch fails, the affected file and its package registrations are retained. Uninstall reports an error; resolve the cause and retry through SetupHelper.
