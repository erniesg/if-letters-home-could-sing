import QtQuick 2.5
import QtQuick.Controls 2.5

Item {
    id: inkLayer
    property var strokes: []
    Accessible.name: "Participant ink layer"
    Accessible.role: Accessible.Canvas

    onStrokesChanged: canvas.requestPaint()
    onWidthChanged: canvas.requestPaint()
    onHeightChanged: canvas.requestPaint()

    Canvas {
        id: canvas
        anchors.fill: parent

        onPaint: {
            var context = getContext("2d")
            context.clearRect(0, 0, width, height)
            context.strokeStyle = "#33475b"
            context.lineCap = "round"
            context.lineJoin = "round"
            for (var strokeIndex = 0; strokeIndex < inkLayer.strokes.length; strokeIndex++) {
                var points = inkLayer.strokes[strokeIndex].points
                if (!points || points.length === 0)
                    continue
                var pressure = 0
                for (var pressureIndex = 0; pressureIndex < points.length; pressureIndex++)
                    pressure += points[pressureIndex].pressure || 0.5
                context.lineWidth = Math.max(3, pressure / points.length * 10)
                context.beginPath()
                context.moveTo(points[0].x * width, points[0].y * height)
                for (var pointIndex = 1; pointIndex < points.length; pointIndex++)
                    context.lineTo(points[pointIndex].x * width, points[pointIndex].y * height)
                context.stroke()
            }
        }
    }
}
