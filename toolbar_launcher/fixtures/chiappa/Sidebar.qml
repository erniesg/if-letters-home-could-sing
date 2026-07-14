import QtQuick 2.15
import QtQuick.Layouts 1.15
import ark.controls 1.0 as ArkControls

DeviceKeyboardNavigationHandler {
    id: navigationHandler

    // fixture-region: sidebar:start
    ColumnLayout {
        id: filterColumn

        // letters-home-insertion-point
        ArkControls.SidebarItem {
            id: filterMyFiles
            objectName: "filter-my-files"
            title: qsTr("My files")
            iconSource: "qrc:/ark/icons/my-files"
            active: true
            enabled: true
            visible: true
            Layout.preferredHeight: Values.navigatorSidebarItemHeight
            Layout.preferredWidth: parent.width
            navigationHandler: sidebar
            onClicked: {}
        }

        ArkControls.SidebarItem {
            id: filterTags
            objectName: "filter-tags"
            title: qsTr("Tags")
            iconSource: "qrc:/ark/icons/tags"
            enabled: true
            visible: true
            Layout.preferredHeight: Values.navigatorSidebarItemHeight
            Layout.preferredWidth: parent.width
            navigationHandler: sidebar
            onClicked: {}
        }

        ArkControls.SidebarItem {
            id: filterTrash
            objectName: "filter-trash"
            title: qsTr("Trash")
            iconSource: "qrc:/ark/icons/trash"
            enabled: true
            visible: true
            Layout.preferredHeight: Values.navigatorSidebarItemHeight
            Layout.preferredWidth: parent.width
            navigationHandler: sidebar
            onClicked: {}
        }
    }
    // fixture-region: sidebar:end
}
