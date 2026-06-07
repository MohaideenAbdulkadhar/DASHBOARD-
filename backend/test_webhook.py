import requests

LOCAL_WEBHOOK_URL = "http://127.0.0.1:8000/api/v1/inbound/webhook"


def simulate_end_of_call(phone_number: str, mock_name: str):
    print(f"📡 Simulating Vapi End-of-Call Report event for {mock_name} ({phone_number})...")

    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "id": "vapi-live-call-xyz-12345",
                "status": "ended"
            },
            "customer": {
                "number": phone_number
            },
            "transcript": (
                f"AI Agent: Hello {mock_name}, I see you own property on OMR. Are you looking to sell?\n"
                f"Customer: Yeah, I might be open to an all-cash offer if the valuation handles taxes.\n"
                f"AI Agent: Perfect! I will have our acquisitions director ring you tomorrow morning.\n"
                f"Customer: Sounds good. Speak then. Bye."
            ),
            "analysis": {
                "summary": f"Lead verified. {mock_name} confirmed asset ownership and requested an all-cash offer review tomorrow morning."
            },
            "recordingUrl": "https://actions.vapi.ai/mock-recording.mp3"
        }
    }

    try:
        response = requests.post(LOCAL_WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            print("✨ Webhook wrapper accepted successfully!")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Server rejected payload: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection to local FastAPI server failed: {str(e)}")


if __name__ == "__main__":
    simulate_end_of_call("+15559871234", "Bruce Wayne")
