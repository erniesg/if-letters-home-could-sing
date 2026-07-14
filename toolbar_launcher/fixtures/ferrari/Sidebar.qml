import QtQuick
import QtQuick.Layouts

import common as Common
import ark.controls as ArkControls

FocusScope {
    id: root
    objectName: "Sidebar"

    property int activeView: 0

    function toggle() {}

    // fixture-region: sidebar:start
    ColumnLayout {
        id: filterColumn
        anchors.fill: parent
        spacing: 0

        Item {
            id: homeWidget
            Layout.fillWidth: true
            Layout.preferredHeight: Common.Values.navigatorSidebarItemHeight
        }

        ArkControls.SidebarItem {
            id: filterMyFiles
            objectName: "filterMyFiles"
            focus: true
            text: qsTr("My files")
            iconSource: "qrc:/ark/icons/my_files"
            highlighted: false
            enabled: true
            onClicked: {
                root.toggle();
            }
            Layout.preferredWidth: parent.width
        }

        ArkControls.SidebarItem {
            id: filterTags
            objectName: "filterTags"
            text: qsTr("Tags")
            highlighted: false
            iconSource: "qrc:/ark/icons/tag"
            onClicked: {
                root.toggle();
            }
            Layout.preferredHeight: Common.Values.navigatorSidebarItemHeight
            Layout.preferredWidth: parent.width
        }

        ArkControls.SidebarItem {
            id: integrations
            objectName: "integrations"
            text: qsTr("Import files")
            iconSource: "qrc:/ark/icons/cloud"
            highlighted: false
            Layout.preferredHeight: Common.Values.navigatorSidebarItemHeight
            Layout.preferredWidth: parent.width
        }

        // letters-home-insertion-point
        ArkControls.SidebarItem {
            id: filterTrashed
            objectName: "filterTrashed"
            text: qsTr("Trash")
            iconSource: "qrc:/ark/icons/trashcan"
            highlighted: false
            onClicked: {
                root.toggle();
            }
            Layout.preferredWidth: parent.width
        }
    }
    // fixture-region: sidebar:end
}
