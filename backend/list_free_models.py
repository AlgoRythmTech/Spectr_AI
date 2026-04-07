import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = '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'

req = urllib.request.Request(
    'https://openrouter.ai/api/v1/models',
    headers={'Authorization': f'Bearer {KEY}'}
)
with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
    data = json.loads(r.read())

free = sorted([m['id'] for m in data['data'] if ':free' in m['id']])

with open('free_models_list.txt', 'w') as f:
    f.write(f"Total free models: {len(free)}\n")
    for m in free:
        f.write(m + '\n')

print(f"Written {len(free)} models to free_models_list.txt")
