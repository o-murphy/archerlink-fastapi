import logging

import websockets
from . import archer_protocol_pb2

# Set the logging level to WARNING to disable debug messages
logging.getLogger('websockets').setLevel(logging.WARNING)

# WS = "ws://stream.trailcam.link:8080/websocket"
WS = "ws://192.168.100.1:8080/websocket"

def set_uri(uri: str):
    global WS
    WS = uri

# Define zoom levels
zoom_levels = [
    archer_protocol_pb2.UNKNOWN_ZOOM_LEVEL,
    archer_protocol_pb2.ZOOM_X1,
    archer_protocol_pb2.ZOOM_X2,
    archer_protocol_pb2.ZOOM_X3,
    archer_protocol_pb2.ZOOM_X4,
    archer_protocol_pb2.ZOOM_X6
]
zoom_cur = zoom_levels[0]

# Define AGC modes
agc_modes = [archer_protocol_pb2.AUTO_1, archer_protocol_pb2.AUTO_2, archer_protocol_pb2.AUTO_3]

# Define available color schemes
color_schemes = [
    archer_protocol_pb2.WHITE_HOT,
    archer_protocol_pb2.BLACK_HOT,
    archer_protocol_pb2.SEPIA,
]


async def change_color_scheme():
    resp = await get_current_dev_status()
    if resp.HasField('devStatus'):
        color_cur = resp.devStatus.colorScheme
        idx = color_schemes.index(color_cur)

        if idx < len(color_schemes) - 1:
            color_cur = color_schemes[idx + 1]
        else:
            color_cur = color_schemes[0]

        print("Scheme: ", color_cur)

        # Create a SetColorScheme message
        set_color = archer_protocol_pb2.SetColorScheme(scheme=color_cur)

        # Create a Command message and set the SetColorScheme message
        command = archer_protocol_pb2.Command()
        command.setPallette.CopyFrom(set_color)

        # Create a ClientPayload message and set the Command message
        client_payload = archer_protocol_pb2.ClientPayload()
        client_payload.command.CopyFrom(command)

        # Serialize the ClientPayload message to a binary string
        payload = client_payload.SerializeToString()
        await send(payload)


async def change_agc():
    resp = await get_current_dev_status()
    if resp.HasField('devStatus'):
        agc_cur = resp.devStatus.modAGC
        idx = agc_modes.index(agc_cur)

        if idx < len(agc_modes) - 1:
            agc_cur = agc_modes[idx + 1]
        else:
            agc_cur = agc_modes[0]

        print("AGC: ", agc_cur)

        # Create a SetAgcMode message
        set_agc = archer_protocol_pb2.SetAgcMode(mode=agc_cur)

        # Create a Command message and set the SetAgcMode message
        command = archer_protocol_pb2.Command()
        command.setAgc.CopyFrom(set_agc)

        # Create a ClientPayload message and set the Command message
        client_payload = archer_protocol_pb2.ClientPayload()
        client_payload.command.CopyFrom(command)

        # Serialize the ClientPayload message to a binary string
        payload = client_payload.SerializeToString()
        await send(payload)

async def change_zoom():
    resp = await get_current_dev_status()
    if resp.HasField('devStatus'):
        zoom = resp.devStatus.zoom
        # maxZoom = resp.devStatus.maxZoom

        zoom_levels = [
            # archer_protocol_pb2.UNKNOWN_ZOOM_LEVEL,
            archer_protocol_pb2.ZOOM_X1,
            archer_protocol_pb2.ZOOM_X2,
            archer_protocol_pb2.ZOOM_X3,
            archer_protocol_pb2.ZOOM_X4,
        ]

        # if maxZoom == 6:
        #     zoom_levels.append(archer_protocol_pb2.ZOOM_X6)

        try:
            idx = zoom_levels.index(zoom)
        except IndexError:
            idx = len(zoom_levels)

        if idx >= len(zoom_levels) - 1:
            zoom_cur = zoom_levels[0]
        else:
            zoom_cur = zoom_levels[idx + 1]

        print("Zoom: ", zoom_cur)
        # Create a SetZoomLevel message
        set_zoom = archer_protocol_pb2.SetZoomLevel(zoomLevel=zoom_cur)

        # Create a Command message and set the SetZoomLevel message
        command = archer_protocol_pb2.Command()
        command.setZoom.CopyFrom(set_zoom)

        # Create a ClientPayload message and set the Command message
        client_payload = archer_protocol_pb2.ClientPayload()
        client_payload.command.CopyFrom(command)

        # Serialize the ClientPayload message to a binary string
        payload = client_payload.SerializeToString()
        await send(payload)


async def get_current_dev_status():
    # Create a GetHostDevStatus message
    get_status = archer_protocol_pb2.GetHostDevStatus()

    # Create a Command message and set the GetHostDevStatus message
    command = archer_protocol_pb2.Command()
    command.getHostDevStatus.CopyFrom(get_status)

    # Create a ClientPayload message and set the Command message
    client_payload = archer_protocol_pb2.ClientPayload()
    client_payload.command.CopyFrom(command)

    # Serialize the ClientPayload message to a binary string
    payload = client_payload.SerializeToString()
    status = await send(payload)
    return status



async def send_trigger_ffc_command():

    # Create a TriggerCmd message with the TRIGGER_FFC command
    trigger_cmd = archer_protocol_pb2.TriggerCmd(cmd=archer_protocol_pb2.TRIGGER_FFC)

    # Create a Command message and set the TriggerCmd message
    command = archer_protocol_pb2.Command()
    command.cmdTrigger.CopyFrom(trigger_cmd)

    # Create a ClientPayload message and set the Command message
    client_payload = archer_protocol_pb2.ClientPayload()
    client_payload.command.CopyFrom(command)
    # Serialize the ClientPayload message to a binary string
    payload = client_payload.SerializeToString()
    await send(payload)


async def send(payload):
    uri = WS
    async with websockets.connect(uri) as websocket:
        await websocket.send(payload)
        response = await websocket.recv()

        try:
            # Parse the response
            command_response = archer_protocol_pb2.HostPayload()
            command_response.ParseFromString(response)
            return command_response
        except Exception:
            return None
