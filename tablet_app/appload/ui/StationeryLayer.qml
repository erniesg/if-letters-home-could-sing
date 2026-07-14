import QtQuick 2.5

Item {
    id: stationery
    property int guideColumns: 12
    Accessible.name: "Blank huipi stationery"
    Accessible.description: "Paper, fold memory, border, and writing guides without handwriting or remittance marks"
    Accessible.role: Accessible.Pane

    Rectangle {
        anchors.fill: parent
        color: "#f6efdf"
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: Math.max(36, Math.min(parent.width, parent.height) * 0.065)
        color: "transparent"
        border.color: "#a45149"
        border.width: 3
        opacity: 0.62
    }

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        width: 2
        height: parent.height
        color: "#796d5e"
        opacity: 0.10
    }

    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width
        height: 2
        color: "#796d5e"
        opacity: 0.10
    }

    Repeater {
        model: stationery.guideColumns
        delegate: Rectangle {
            property real inset: Math.max(36, Math.min(stationery.width, stationery.height) * 0.065)
            x: inset + (stationery.width - inset * 2) * (index + 1) / (stationery.guideColumns + 1)
            y: inset
            width: 2
            height: stationery.height - inset * 2
            color: "#a45149"
            opacity: 0.24
        }
    }


    Repeater {
        model: [0.10, 0.90]
        delegate: Rectangle {
            property real inset: Math.max(36, Math.min(stationery.width, stationery.height) * 0.065)
            x: inset
            y: inset + (stationery.height - inset * 2) * modelData
            width: stationery.width - inset * 2
            height: 2
            color: "#a45149"
            opacity: 0.22
        }
    }
}
