import QtQuick 2.15
import com.remarkable.desktop 1.0

Item {
    id: documentView
    objectName: "document-view"

    // fixture-region: cjk-font:start
    QtObject {
        id: fontSettings
        property string family: "sans-serif"
    }
    // fixture-region: cjk-font:end

    // fixture-region: cjk-language:start
    QtObject {
        id: languageSettings
        property string locale: "en_US"
    }
    // fixture-region: cjk-language:end

    // fixture-region: toolbar:start
    ToolBar {
        id: notebookToolbar

        Column {
            id: editingTools
            property string modelSource: "toolbarProvider.editingTools"

            ToolButton {
                id: penTool
                objectName: "pen-tool"
            }

            ToolButton {
                id: eraserTool
                objectName: "eraser-tool"
            }
            // letters-home-insertion-point
        }
    }
    // fixture-region: toolbar:end

    Item {
        id: notebookCanvas
        objectName: "notebook-canvas"
    }
}
