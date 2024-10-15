const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const captureBtn = document.getElementById('captureBtn');
const clearBtn = document.getElementById('clearBtn');
const connectionStatus = document.getElementById('connectionStatus');

let socket;
let isWebSocketReady = false;
let connectionAttempts = 0;
const maxConnectionAttempts = 5;
const messageQueue = [];

function connectWebSocket() {
    socket = new WebSocket('ws://localhost:8765');

    socket.onopen = function(e) {
        console.log("Connected to server");
        isWebSocketReady = true;
        connectionStatus.textContent = 'Connected';
        connectionStatus.style.color = 'green';
        connectionAttempts = 0;
        sendQueuedMessages();
    };

    socket.onclose = function(event) {
        console.log("WebSocket connection closed");
        isWebSocketReady = false;
        connectionStatus.textContent = 'Disconnected';
        connectionStatus.style.color = 'red';
        if (connectionAttempts < maxConnectionAttempts) {
            connectionAttempts++;
            console.log(`Attempting to reconnect (${connectionAttempts}/${maxConnectionAttempts})...`);
            setTimeout(connectWebSocket, 2000);
        } else {
            console.error("Max connection attempts reached. Please refresh the page.");
        }
    };

    socket.onerror = function(error) {
        console.error(`WebSocket Error: ${error}`);
        connectionStatus.textContent = 'Error';
        connectionStatus.style.color = 'red';
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log("Received message from server:", data);
        switch(data.type) {
            case 'new_strokes':
                console.log("Received strokes:", data.data);
                drawStrokes(data.data);
                break;
            case 'connection_established':
                console.log("Connection established with server");
                break;
            case 'clear':
                clearCanvas();
                break;
            default:
                console.log("Unknown message type:", data.type);
        }
    };
}

function sendMessage(message) {
    if (isWebSocketReady) {
        socket.send(JSON.stringify(message));
    } else {
        console.log("WebSocket not ready. Queueing message.");
        messageQueue.push(message);
        if (connectionAttempts === 0) {
            connectWebSocket();
        }
    }
}

function sendQueuedMessages() {
    while (messageQueue.length > 0 && isWebSocketReady) {
        const message = messageQueue.shift();
        socket.send(JSON.stringify(message));
    }
}

function drawStrokes(strokes) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = 'black';
    ctx.lineWidth = 2;

    strokes.forEach((stroke, index) => {
        if (stroke.length > 1) {
            console.log(`Drawing stroke ${index + 1}:`);
            ctx.beginPath();
            ctx.moveTo(stroke[0][0] * canvas.width, stroke[0][1] * canvas.height);
            for (let i = 1; i < stroke.length; i++) {
                ctx.lineTo(stroke[i][0] * canvas.width, stroke[i][1] * canvas.height);
                console.log(`  Point ${i + 1}: (${stroke[i][0]}, ${stroke[i][1]})`);
            }
            ctx.stroke();
        }
    });
    drawGrid();
}

captureBtn.addEventListener('click', function() {
    console.log("Toggling capture");
    const isCapturing = this.textContent === 'Start Capture';
    this.textContent = isCapturing ? 'Stop Capture' : 'Start Capture';
    sendMessage({type: isCapturing ? 'start_capture' : 'stop_capture'});
});

clearBtn.addEventListener('click', function() {
    console.log("Clearing canvas and sending clear request to server");
    clearCanvas();
    sendMessage({type: 'clear'});
});

function clearCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawGrid();
}

function drawGrid() {
    ctx.setLineDash([1, 1]);
    ctx.lineWidth = 0.5;
    ctx.strokeStyle = "grey";

    // Draw border
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(canvas.width, 0);
    ctx.lineTo(canvas.width, canvas.height);
    ctx.lineTo(0, canvas.height);
    ctx.lineTo(0, 0);
    ctx.stroke();

    // Draw diagonals
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(canvas.width, canvas.height);
    ctx.moveTo(canvas.width, 0);
    ctx.lineTo(0, canvas.height);
    ctx.stroke();

    // Draw center lines
    ctx.beginPath();
    ctx.moveTo(canvas.width / 2, 0);
    ctx.lineTo(canvas.width / 2, canvas.height);
    ctx.moveTo(0, canvas.height / 2);
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
}

// Log canvas dimensions
console.log(`Canvas dimensions: ${canvas.width}x${canvas.height}`);

// Initial connection and grid drawing
connectWebSocket();
drawGrid();
