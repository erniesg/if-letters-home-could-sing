import QtQuick 2.5
import QtQuick.Controls 2.5
import net.asivery.AppLoad 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: "#f1e8d5"

    signal close

    property int minimumTouchTarget: 96
    property string stateName: "incoming"
    property string errorCode: ""
    property string firstInkAt: ""
    property var strokes: []
    property var annotations: []
    property string reviewStatus: ""
    property string reviewSummary: ""
    property bool emptyConfirmationVisible: false
    property bool marginaliaVisible: true
    property bool ferrariProfile: Math.max(width, height) / Math.min(width, height) > 1.55
    property var pendingStatePayload: null
    property var activePoints: []
    property double strokeStartedAt: 0
    property int nextStrokeNumber: 1
    property real pageMargin: Math.max(28, Math.min(width, height) * 0.035)
    property real headerHeight: Math.max(minimumTouchTarget, height * 0.075)
    property real footerHeight: Math.max(128, height * 0.10)

    function unloading() {
        endpoint.terminate()
    }

    function send(type, payload) {
        endpoint.sendMessage(type, JSON.stringify(payload || {}))
    }

    function acceptState(payload) {
        stateName = payload.state
        errorCode = payload.errorCode || ""
        firstInkAt = payload.firstInkAt || ""
        strokes = payload.strokes || []
        annotations = payload.annotations || []
        reviewStatus = payload.reviewStatus || ""
        reviewSummary = payload.reviewSummary || ""
        inkLayer.strokes = strokes
        marginaliaLayer.annotations = annotations
        marginaliaLayer.summary = reviewSummary
    }

    function addPoint(mouse) {
        var copy = activePoints.slice(0)
        copy.push({
            "x": Math.max(0, Math.min(1, mouse.x / penArea.width)),
            "y": Math.max(0, Math.min(1, mouse.y / penArea.height)),
            "pressure": mouse.pressure === undefined ? 0.5 : mouse.pressure,
            "elapsed_ms": Math.max(0, Math.round(Date.now() - strokeStartedAt))
        })
        activePoints = copy
    }

    AppLoad {
        id: endpoint
        applicationID: "letters-home"

        onMessageReceived: function(type, contents) {
            var payload = JSON.parse(contents || "{}")
            if (type === 101) {
                if (stateName === "submitting" && payload.state !== "submitting") {
                    pendingStatePayload = payload
                    progressDelay.restart()
                } else {
                    acceptState(payload)
                }
            } else if (type === 102) {
                emptyConfirmationVisible = true
            } else if (type === 103) {
                errorCode = payload.code || "invalid_message"
            }
        }
    }

    Timer {
        id: progressDelay
        interval: 250
        repeat: false
        onTriggered: {
            acceptState(pendingStatePayload)
            pendingStatePayload = null
        }
    }

    Component.onCompleted: send(1, {})

    Rectangle {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: root.headerHeight
        color: "#e5d9c2"

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 42
            anchors.verticalCenter: parent.verticalCenter
            color: "#2f2923"
            font.pixelSize: 44
            text: stateName === "incoming" ? "Incoming letter"
                  : stateName === "reply" ? "Your huipi"
                  : stateName === "marginalia" ? "A reading of your reply"
                  : stateName === "submitting" ? "Preparing marginalia"
                  : "Reply saved"
            Accessible.name: text
            Accessible.role: Accessible.Heading
        }

        Text {
            anchors.right: parent.right
            anchors.rightMargin: 42
            anchors.verticalCenter: parent.verticalCenter
            color: "#2f2923"
            font.pixelSize: 28
            text: root.width > root.height ? "Landscape fixture" : "Portrait fixture"
            Accessible.name: text
            Accessible.role: Accessible.StaticText
        }
    }

    Item {
        id: page
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.bottom: footer.top
        anchors.margins: root.pageMargin

        Rectangle {
            anchors.fill: parent
            color: "#f6efdf"
            border.color: "#8d7964"
            border.width: 3
            radius: 8
        }

        Item {
            id: incomingLayer
            anchors.fill: parent
            visible: stateName === "incoming"
            Accessible.name: "Incoming fictional letter"
            Accessible.role: Accessible.Pane

            Image {
                id: incomingFixture
                anchors.top: parent.top
                anchors.topMargin: parent.height * 0.05
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(parent.width * 0.76, height * 0.75)
                height: parent.height * 0.76
                fillMode: Image.PreserveAspectFit
                source: "qrc:/assets/incoming-qiaopi-001.png"
                Accessible.name: "Fictional qiao pi-inspired incoming letter fixture"
                Accessible.description: "Synthetic correspondence; not an archival accession"
                Accessible.role: Accessible.Graphic
            }

            Text {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 36
                color: "#2f2923"
                font.pixelSize: 32
                horizontalAlignment: Text.AlignHCenter
                text: "A fictional letter generated for this encounter"
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
                Accessible.name: text
                Accessible.description: "Provenance disclosure"
                Accessible.role: Accessible.StaticText
            }
        }

        StationeryLayer {
            id: stationeryLayer
            anchors.fill: parent
            guideColumns: root.ferrariProfile ? 8 : 12
            visible: stateName !== "incoming"
        }

        InkLayer {
            id: inkLayer
            anchors.fill: parent
            visible: stateName !== "incoming"
        }

        MarginaliaLayer {
            id: marginaliaLayer
            anchors.fill: parent
            visible: stateName === "marginalia" && root.marginaliaVisible
        }

        MouseArea {
            id: forwardSwipeArea
            anchors.fill: parent
            enabled: stateName === "incoming"
            property real pressX: 0
            onPressed: pressX = mouse.x
            onReleased: {
                if (mouse.x < pressX - Math.max(120, width * 0.12))
                    send(2, {"direction": "forward"})
            }
        }

        MouseArea {
            id: penArea
            anchors.fill: parent
            enabled: stateName === "reply"
            preventStealing: true
            onPressed: {
                activePoints = []
                strokeStartedAt = Date.now()
                addPoint(mouse)
            }
            onPositionChanged: {
                if (pressed)
                    addPoint(mouse)
            }
            onReleased: {
                addPoint(mouse)
                if (activePoints.length > 0) {
                    send(3, {
                        "stroke_id": "host-stroke-" + nextStrokeNumber,
                        "accepted_at": new Date().toISOString(),
                        "points": activePoints
                    })
                    nextStrokeNumber += 1
                }
                activePoints = []
            }
        }

        MouseArea {
            id: backSwipeArea
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: Math.max(minimumTouchTarget, parent.width * 0.07)
            enabled: stateName === "reply"
            z: 5
            property real pressX: 0
            onPressed: pressX = mouse.x
            onReleased: {
                if (mouse.x > pressX + Math.max(70, width * 0.5))
                    send(2, {"direction": "backward"})
            }
            Accessible.name: "Swipe backward to incoming letter"
            Accessible.role: Accessible.Button
        }
    }

    Rectangle {
        id: footer
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: root.footerHeight
        color: "#f1e8d5"

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 42
            anchors.right: actionButton.left
            anchors.rightMargin: 30
            anchors.verticalCenter: parent.verticalCenter
            color: "#2f2923"
            font.pixelSize: 27
            text: errorCode === "gateway_offline"
                  ? "Offline — your ink is safe on this page"
                  : errorCode === "reviewer_unavailable" || errorCode === "invalid_review" || errorCode === "reviewer_mutated_input"
                  ? "A reading is unavailable — your original ink is safe"
                  : "Heart rate unavailable — reply is still available"
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
            Accessible.name: text
            Accessible.role: Accessible.StaticText
        }

        Rectangle {
            id: actionButton
            anchors.right: parent.right
            anchors.rightMargin: root.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(480, Math.max(280, root.width * 0.26))
            height: root.minimumTouchTarget
            radius: 10
            color: "#2f2923"
            visible: stateName !== "submitting"
            Accessible.name: actionLabel.text
            Accessible.role: Accessible.Button

            Text {
                id: actionLabel
                anchors.fill: parent
                anchors.margins: 12
                color: "#fffaf0"
                font.pixelSize: 30
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                text: stateName === "incoming" ? "Swipe forward"
                      : stateName === "reply" ? "Submit huipi"
                      : stateName === "marginalia" ? (marginaliaVisible ? "Hide notes" : "Show notes")
                      : "Retry"
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    if (stateName === "incoming")
                        send(2, {"direction": "forward"})
                    else if (stateName === "reply")
                        send(4, {"confirm_empty": false, "submitted_at": new Date().toISOString()})
                    else if (stateName === "submission_error" || stateName === "review_error")
                        send(5, {})
                    else if (stateName === "marginalia")
                        marginaliaVisible = !marginaliaVisible
                }
            }
        }

        Text {
            anchors.centerIn: parent
            visible: stateName === "submitting"
            color: "#2f2923"
            font.pixelSize: 32
            text: "Reading your reply…"
            Accessible.name: text
            Accessible.role: Accessible.StaticText
        }
    }

    Rectangle {
        id: emptyConfirmation
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.78, 920)
        height: Math.max(360, confirmText.implicitHeight + 230)
        visible: emptyConfirmationVisible
        z: 20
        color: "#f6efdf"
        border.color: "#74362f"
        border.width: 4
        radius: 10
        Accessible.name: "Confirm blank huipi submission"
        Accessible.role: Accessible.Dialog

        Text {
            id: confirmText
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 42
            color: "#2f2923"
            font.pixelSize: 34
            text: "Your huipi is blank. Submit it without ink?"
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
            Accessible.name: text
            Accessible.role: Accessible.StaticText
        }

        Row {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 42
            spacing: 24

            Button {
                width: 240
                height: root.minimumTouchTarget
                text: "Keep writing"
                Accessible.name: text
                onClicked: emptyConfirmationVisible = false
            }

            Button {
                width: 320
                height: root.minimumTouchTarget
                text: "Submit blank huipi"
                Accessible.name: text
                onClicked: {
                    emptyConfirmationVisible = false
                    send(4, {"confirm_empty": true, "submitted_at": new Date().toISOString()})
                }
            }
        }
    }
}
