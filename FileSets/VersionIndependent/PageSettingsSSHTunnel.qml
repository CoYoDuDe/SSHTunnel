import QtQuick 2
import com.victron.velib 1.0
import "utils.js" as Utils

MbPage {
    id: root
    title: qsTr("SSH Tunnel")

    property string settingsPrefix: "com.victronenergy.settings/Settings/SSHTunnel"
    property VBusItem enabledItem: VBusItem { bind: Utils.path(settingsPrefix, "/Enabled") }
    property VBusItem tunnel1EnabledItem: VBusItem { bind: Utils.path(settingsPrefix, "/Tunnel1Enabled") }
    property VBusItem tunnel2EnabledItem: VBusItem { bind: Utils.path(settingsPrefix, "/Tunnel2Enabled") }
    property VBusItem managementModeItem: VBusItem { bind: Utils.path(settingsPrefix, "/ManagementMode") }

    function integerValue(text, minimum, maximum) {
        var value = String(text).trim()
        if (!/^[0-9]+$/.test(value)) return null
        var number = Number(value)
        return isFinite(number) && number >= minimum && number <= maximum ? number : null
    }

    model: VisibleItemModel {
        MbSwitch {
            name: qsTr("Dienst aktiv")
            bind: Utils.path(root.settingsPrefix, "/Enabled")
            valueTrue: 1
            valueFalse: 0
            writeAccessLevel: User.AccessInstaller
        }

        MbEditBox {
            description: qsTr("Server")
            item.bind: Utils.path(root.settingsPrefix, "/Server")
            maximumLength: 80
            overwriteMode: false
            writeAccessLevel: User.AccessInstaller
        }

        MbEditBox {
            description: qsTr("Benutzer")
            item.bind: Utils.path(root.settingsPrefix, "/Username")
            maximumLength: 32
            overwriteMode: false
            writeAccessLevel: User.AccessInstaller
        }

        MbEditBox {
            description: qsTr("SSH-Server-Port")
            item.bind: Utils.path(root.settingsPrefix, "/ServerPort")
            maximumLength: 5
            writeAccessLevel: User.AccessInstaller
            function editTextToValue() {
                if (!/^[0-9]+$/.test(_editText.trim())) return null
                var port = Number(_editText.trim())
                return port >= 1 && port <= 65535 ? port : null
            }
        }

        MbEditBox {
            description: qsTr("Schlüsselpfad")
            item.bind: Utils.path(root.settingsPrefix, "/KeyPath")
            maximumLength: 120
            overwriteMode: false
            writeAccessLevel: User.AccessInstaller
        }

        MbSwitch {
            name: qsTr("StrictHostKeyChecking")
            bind: Utils.path(root.settingsPrefix, "/StrictHostKeyChecking")
            valueTrue: 1
            valueFalse: 0
            writeAccessLevel: User.AccessInstaller
        }

        MbEditBox {
            description: qsTr("Reconnect-Verzögerung [s]")
            item.bind: Utils.path(root.settingsPrefix, "/ReconnectDelay")
            maximumLength: 4
            writeAccessLevel: User.AccessInstaller
            function editTextToValue() { return root.integerValue(_editText, 1, 600) }
        }

        MbItemOptions {
            description: qsTr("Verbindungsweg")
            bind: Utils.path(root.settingsPrefix, "/ManagementMode")
            writeAccessLevel: User.AccessInstaller
            possibleValues: [
                MbOption { description: qsTr("Systemverbindung"); value: 0 },
                MbOption { description: qsTr("RoadLink-VPN"); value: 1 }
            ]
        }

        MbEditBox {
            description: qsTr("Öffentliche Server-IPv4")
            item.bind: Utils.path(root.settingsPrefix, "/ManagementIPv4")
            maximumLength: 15
            overwriteMode: false
            writeAccessLevel: User.AccessInstaller
            function editTextToValue() {
                var parts = _editText.trim().split(".")
                if (parts.length !== 4) return null
                for (var i = 0; i < parts.length; i++) {
                    if (!/^(0|[1-9][0-9]{0,2})$/.test(parts[i]) || Number(parts[i]) > 255) return null
                }
                return parts.join(".")
            }
        }

        MbItemText {
            show: root.managementModeItem.valid && Number(root.managementModeItem.value) === 1
            text: qsTr("RoadLink-VPN wartet auf den geprüften VPN-Weg. Servername und Hostschlüssel bleiben maßgeblich. Bei ausgeschaltetem VPN verbindet dieser Modus nicht.")
            wrapMode: Text.WordWrap
        }

        MbItemText { text: qsTr("Tunnel 1") }

        MbSwitch {
            name: qsTr("Tunnel 1 aktiv")
            bind: Utils.path(root.settingsPrefix, "/Tunnel1Enabled")
            valueTrue: 1
            valueFalse: 0
            writeAccessLevel: User.AccessInstaller
        }

        MbEditBox {
            description: qsTr("Tunnel 1 Remote-Port")
            item.bind: Utils.path(root.settingsPrefix, "/Tunnel1RemotePort")
            maximumLength: 5
            writeAccessLevel: User.AccessInstaller
            function editTextToValue() { return root.integerValue(_editText, 1, 65535) }
        }

        MbEditBox {
            description: qsTr("Tunnel 1 Zielhost lokal")
            item.bind: Utils.path(root.settingsPrefix, "/Tunnel1LocalHost")
            maximumLength: 80
            overwriteMode: false
            writeAccessLevel: User.AccessInstaller
        }

        MbEditBox {
            description: qsTr("Tunnel 1 Zielport lokal")
            item.bind: Utils.path(root.settingsPrefix, "/Tunnel1LocalPort")
            maximumLength: 5
            writeAccessLevel: User.AccessInstaller
            function editTextToValue() { return root.integerValue(_editText, 1, 65535) }
        }

        MbItemText { text: qsTr("Tunnel 2") }

        MbSwitch {
            name: qsTr("Tunnel 2 aktiv")
            bind: Utils.path(root.settingsPrefix, "/Tunnel2Enabled")
            valueTrue: 1
            valueFalse: 0
            writeAccessLevel: User.AccessInstaller
        }

        MbEditBox {
            description: qsTr("Tunnel 2 Remote-Port")
            item.bind: Utils.path(root.settingsPrefix, "/Tunnel2RemotePort")
            maximumLength: 5
            writeAccessLevel: User.AccessInstaller
            function editTextToValue() { return root.integerValue(_editText, 1, 65535) }
        }

        MbEditBox {
            description: qsTr("Tunnel 2 Zielhost lokal")
            item.bind: Utils.path(root.settingsPrefix, "/Tunnel2LocalHost")
            maximumLength: 80
            overwriteMode: false
            writeAccessLevel: User.AccessInstaller
        }

        MbEditBox {
            description: qsTr("Tunnel 2 Zielport lokal")
            item.bind: Utils.path(root.settingsPrefix, "/Tunnel2LocalPort")
            maximumLength: 5
            writeAccessLevel: User.AccessInstaller
            function editTextToValue() { return root.integerValue(_editText, 1, 65535) }
        }

        MbItemText {
            text: qsTr("Ersteinrichtung im Terminal: python3 /data/SSHTunnel/configure.py. Der Assistent prüft den Hostschlüssel und richtet die Anmeldung per Schlüssel ein. Kein Passwort wird gespeichert.")
            wrapMode: Text.WordWrap
        }
    }
}
