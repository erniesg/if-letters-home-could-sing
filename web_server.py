from draw_rm import RemarkableDrawer
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger('web_server')

drawer = None

async def handle_websocket(websocket, path):
    global drawer
    try:
        log.info("New WebSocket connection established")
        connected_clients.add(websocket)
        await websocket.send(json.dumps({'type': 'connection_established'}))
        log.debug("Sent connection_established message")
        await send_all_strokes(websocket)
        async for message in websocket:
            log.debug(f"Received message: {message}")
            data = json.loads(message)
            if data['type'] == 'clear':
                log.info("Clearing strokes")
                drawer.clear()
                await broadcast_clear()
    except websockets.exceptions.ConnectionClosed:
        log.info("WebSocket connection closed")
    except Exception as e:
        log.error(f"Error in handle_websocket: {str(e)}")
        import traceback
        log.error(traceback.format_exc())
    finally:
        connected_clients.remove(websocket)
        log.info(f"Client disconnected, {len(connected_clients)} clients remaining")

async def broadcast_clear():
    message = json.dumps({'type': 'clear'})
    log.debug("Broadcasting clear command")
    for websocket in connected_clients.copy():
        try:
            await websocket.send(message)
        except websockets.exceptions.ConnectionClosed:
            connected_clients.remove(websocket)

def normalize_strokes(strokes, width, height):
    normalized = []
    for stroke in strokes:
        normalized_stroke = [(x / width, y / height) for x, y in stroke]
        normalized.append(normalized_stroke)
        log.info(f"Normalized stroke: start: {normalized_stroke[0]}, end: {normalized_stroke[-1]}")
    return normalized

async def send_all_strokes(websocket):
    global drawer
    strokes = drawer.get_strokes()
    log.debug(f"Raw strokes: {strokes}")
    normalized_strokes = normalize_strokes(strokes, drawer.rm_width, drawer.rm_height)
    log.debug(f"Normalized strokes: {normalized_strokes}")
    message = json.dumps({'type': 'strokes', 'data': normalized_strokes})
    log.debug(f"Sending message: {message}")
    await websocket.send(message)

async def capture_input():
    global drawer
    last_stroke_count = 0
    while True:
        drawer.capture_input()
        strokes = drawer.get_strokes()
        if len(strokes) > last_stroke_count:
            new_strokes = strokes[last_stroke_count:]
            log.info(f"Captured {len(new_strokes)} new strokes")
            await broadcast_new_strokes(new_strokes)
            last_stroke_count = len(strokes)
        await asyncio.sleep(0.01)  # Small sleep to prevent CPU hogging
connected_clients = set()

async def broadcast_new_strokes(new_strokes):
    global drawer
    normalized_strokes = normalize_strokes(new_strokes, drawer.rm_width, drawer.rm_height)
    message = json.dumps({'type': 'new_strokes', 'data': normalized_strokes})
    log.info(f"Broadcasting new strokes to {len(connected_clients)} clients")
    for websocket in connected_clients.copy():
        try:
            await websocket.send(message)
            log.debug(f"Sent new strokes to a client")
        except websockets.exceptions.ConnectionClosed:
            log.warning(f"Client connection closed, removing from connected clients")
            connected_clients.remove(websocket)

async def main():
    global drawer
    drawer = RemarkableDrawer('10.11.99.1')  # Replace with your reMarkable's IP
    await asyncio.sleep(1)  # Add a small delay to ensure setup is complete
    log.info("Starting WebSocket server...")
    server = await websockets.serve(handle_websocket, "localhost", 8765)
    log.info("WebSocket server started on ws://localhost:8765")
    await asyncio.gather(
        server.wait_closed(),
        capture_input()
    )

if __name__ == "__main__":
    asyncio.run(main())
