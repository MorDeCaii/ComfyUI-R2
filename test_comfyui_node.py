import requests
import json
import sys
import time
import websocket
import os

# additional Python packages required to run this script:
# websocket-client==1.8.0

def on_message(ws, message):
    print("Received message:", message)
    try:
        data = json.loads(message)
        # Look for outputs in the message
        outputs = None
        if "data" in data and "outputs" in data["data"]:
            outputs = data["data"]["outputs"]
        elif "outputs" in data:
            outputs = data["outputs"]
        if outputs:
            # Find the STRING output (from S3SaveNode)
            for node_id, node_outputs in outputs.items():
                for output in node_outputs:
                    if "STRING" in output:
                        print("S3SaveNode output STRING:", output["STRING"])
                        ws.close()
                        return
        # Optionally, close on execution_end
        if data.get("type") == "execution_end":
            print("Execution ended, but no output found.")
            ws.close()
    except Exception as e:
        print("Error parsing message as JSON:", e)

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed")

def on_open(ws):
    print("WebSocket connection opened, waiting for output...")

if len(sys.argv) != 4:
    print("Usage: python test_comfyui_node.py <workflow.json> <bearer_token> <comfyui_url>")
    sys.exit(1)

workflow_path = sys.argv[1]
bearer_token = sys.argv[2]
comfyui_url = sys.argv[3]
if comfyui_url.endswith("/"):
    comfyui_url = comfyui_url[:-1]

# Read workflow.json
with open(workflow_path, "r") as f:
    workflow = json.load(f)

# Wrap workflow in a 'prompt' key if not already wrapped
if "prompt" not in workflow:
    payload = {"prompt": workflow}
else:
    payload = workflow

# Submit workflow to /prompt
url = f"{comfyui_url}/prompt"
headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json"
}
response = requests.post(url, headers=headers, json=payload)
if response.status_code != 200:
    print("Failed to submit prompt:", response.text)
    sys.exit(1)

resp_json = response.json()
prompt_id = resp_json.get("prompt_id")
if not prompt_id:
    print("No prompt_id in response:", resp_json)
    sys.exit(1)

print("Submitted prompt, prompt_id:", prompt_id)

# Connect to /ws and listen for output
ws_url = comfyui_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
ws = websocket.WebSocketApp(
    ws_url,
    header=[f"Authorization: Bearer {bearer_token}"],
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

globals()['prompt_id'] = prompt_id
ws.run_forever()
