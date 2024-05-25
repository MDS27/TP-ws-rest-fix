from starlette.testclient import TestClient

from app import app

def main():
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(f"Not error!")

        data = websocket.receive_text()

        print(data)

if __name__ == "__main__":
    main()