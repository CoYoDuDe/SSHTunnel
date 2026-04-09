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

    model: VisibleItemModel {
        MbItemText {
            text: qsTr("Konfiguriert einen eigenen SSH-Tunnel getrennt vom systemeigenen Victron-Tunnel.")
            wrapMode: Text.WordWrap
        }

        MbItemText {
            text: qsTr("Die Einstellungen werden in com.victronenergy.settings gespeichert und bleiben dadurch nach Paket-Updates erhalten.")
            wrapMode: Text.WordWrap
        }

        MbItemText {
            text: qsTr("Für den ersten Test neben einem bestehenden Tunnel zuerst eigene freie Remote-Ports verwenden.")
            wrapMode: Text.WordWrap
        }

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
            inputMethodHints: Qt.ImhDigitsOnly
            maximumLength: 4
            writeAccessLevel: User.AccessInstaller
            onEditDone: {
                var value = parseInt(newValue, 10)
                if (!isNaN(value) && value > 0)
                    item.setValue(value)
            }
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
            inputMethodHints: Qt.ImhDigitsOnly
            maximumLength: 5
            show: enabledItem.valid && enabledItem.value && tunnel1EnabledItem.valid && tunnel1EnabledItem.value
            writeAccessLevel: User.AccessInstaller
            onEditDone: {
                var value = parseInt(newValue, 10)
                if (!isNaN(value) && value > 0)
                    item.setValue(value)
            }
        }

        MbEditBox {
            description: qsTr("Tunnel 1 Zielhost lokal")
            item.bind: Utils.path(root.settingsPrefix, "/Tunnel1LocalHost")
            maximumLength: 80
            overwriteMode: false
            show: enabledItem.valid && enabledItem.value && tunnel1EnabledItem.valid && tunnel1EnabledItem.value
            writeAccessLevel: User.AccessInstaller
        }

        MbEditBox {
            description: qsTr("Tunnel 1 Zielport lokal")
            item.bind: Utils.path(root.settingsPrefix, "/Tunnel1LocalPort")
            inputMethodHints: Qt.ImhDigitsOnly
            maximumLength: 5
            show: enabledItem.valid && enabledItem.value && tunnel1EnabledItem.valid && tunnel1EnabledItem.value
            writeAccessLevel: User.AccessInstaller
            onEditDone: {
                var value = parseInt(newValue, 10)
                if (!isNaN(value) && value > 0)
                    item.setValue(value)
            }
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
            inputMethodHints: Qt.ImhDigitsOnly
            maximumLength: 5
            show: enabledItem.valid && enabledItem.value && tunnel2EnabledItem.valid && tunnel2EnabledItem.value
            writeAccessLevel: User.AccessInstaller
            onEditDone: {
                var value = parseInt(newValue, 10)
                if (!isNaN(value) && value > 0)
                    item.setValue(value)
            }
        }

        MbEditBox {
            description: qsTr("Tunnel 2 Zielhost lokal")
            item.bind: Utils.path(root.settingsPrefix, "/Tunnel2LocalHost")
            maximumLength: 80
            overwriteMode: false
            show: enabledItem.valid && enabledItem.value && tunnel2EnabledItem.valid && tunnel2EnabledItem.value
            writeAccessLevel: User.AccessInstaller
        }

        MbEditBox {
            description: qsTr("Tunnel 2 Zielport lokal")
            item.bind: Utils.path(root.settingsPrefix, "/Tunnel2LocalPort")
            inputMethodHints: Qt.ImhDigitsOnly
            maximumLength: 5
            show: enabledItem.valid && enabledItem.value && tunnel2EnabledItem.valid && tunnel2EnabledItem.value
            writeAccessLevel: User.AccessInstaller
            onEditDone: {
                var value = parseInt(newValue, 10)
                if (!isNaN(value) && value > 0)
                    item.setValue(value)
            }
        }
    }
}
