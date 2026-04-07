
import requests, os
from dotenv import load_dotenv
load_dotenv()
key = os.environ.get('EMERGENT_LLM_KEY')
print(f'Testing Emergent API with key starting {key[:10]}...')

urls = [
    'https://api.emergent.sh/v1/chat/completions',
    'https://api.emergent.sh/v1/messages',
    'https://api.emergent.sh/chat/completions'
]

for url in urls:
    try:
        r = requests.post(url, headers={'Authorization': f'Bearer {key}'}, json={})
        print(f'{url} -> {r.status_code} {r.text[:50]}')
    except Exception as e:
        print(f'{url} -> ERROR {e}')

