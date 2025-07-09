import requests
import sys

# Usage: python debug_hackclub_models.py [API_BASE_URL]
# Example: python debug_hackclub_models.py https://ai.hackclub.com

def try_endpoint(api_base, endpoint):
    url = api_base.rstrip('/') + endpoint
    print(f"\nTrying: {url}")
    try:
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        if resp.status_code == 200:
            # Try to parse as JSON, but if it fails, treat as plain text
            try:
                data = resp.json()
                if 'data' in data:
                    print(f"Found OpenAI format: {[m.get('id') for m in data['data']]}")
                if 'models' in data:
                    print(f"Found models list: {data['models']}")
                if 'model' in data:
                    print(f"Found single model: {data['model']}")
            except Exception:
                # Not JSON, treat as plain text (e.g., hackclub/ai returns just the model name)
                text = resp.text.strip()
                if text:
                    print(f"Plain text model name: {text}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_hackclub_models.py [API_BASE_URL]")
        sys.exit(1)
    api_base = sys.argv[1]
    for endpoint in ["/v1/models", "/models", "/model"]:
        try_endpoint(api_base, endpoint)

if __name__ == "__main__":
    main()
