import requests
import sys

def send_requests(url, n):
    for i in range(n):
        try:
            response = requests.get(url)
            print(f"Request {i+1}: {response.status_code}")
        except Exception as e:
            print(f"Request {i+1}: Error -> {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python script.py <url> <numero_de_peticiones>")
        sys.exit(1)

    url = sys.argv[1]
    n = int(sys.argv[2])

    send_requests(url, n)