import QtQuick 2.5

Item {
    id: marginaliaLayer
    property var annotations: []
    Accessible.name: "Reversible marginalia overlay"
    Accessible.role: Accessible.Pane

    Repeater {
        model: marginaliaLayer.annotations
        delegate: Item {
            property var annotation: modelData
            x: annotation.anchor.x * marginaliaLayer.width
            y: annotation.anchor.y * marginaliaLayer.height
            width: Math.max(12, annotation.anchor.width * marginaliaLayer.width)
            height: Math.max(12, annotation.anchor.height * marginaliaLayer.height)

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: "#74362f"
                border.width: 5
                radius: 4
            }

            Rectangle {
                anchors.left: parent.left
                anchors.bottom: parent.top
                anchors.bottomMargin: 10
                width: Math.min(Math.max(320, note.implicitWidth + 36), marginaliaLayer.width * 0.62)
                height: Math.max(96, note.implicitHeight + 28)
                color: "#f6efdf"
                border.color: "#74362f"
                border.width: 2
                radius: 6

                Text {
                    id: note
                    anchors.fill: parent
                    anchors.margins: 14
                    color: "#2f2923"
                    font.pixelSize: 25
                    text: annotation.message
                    wrapMode: Text.WordWrap
                    elide: Text.ElideNone
                    Accessible.name: annotation.message
                    Accessible.role: Accessible.StaticText
                }
            }
        }
    }
}
