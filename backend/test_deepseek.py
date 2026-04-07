import urllib.request, json, ssl, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = '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'
QUESTION = "Under Section 73 CGST Act, what is the exact time limit for issuing SCN for FY 2021-22? Cite the sub-section and date."

MODELS = [
    ('Gemma 3 27B', 'google/gemma-3-27b-it:free'),
    ('Llama 3.3 70B', 'meta-llama/llama-3.3-70b-instruct:free'),
    ('Qwen3.6 Plus', 'qwen/qwen3.6-plus:free'),
    ('NVIDIA Nemotron 120B', 'nvidia/nemotron-3-super-120b-a12b:free'),
]

lines = ["=" * 70, "OPENROUTER FREE MODEL TEST", "=" * 70, ""]

for label, model_id in MODELS:
    payload = json.dumps({
        'model': model_id,
        'messages': [{'role': 'user', 'content': QUESTION}],
        'max_tokens': 300
    }).encode()
    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/chat/completions',
        data=payload,
        headers={
            'Authorization': f'Bearer {KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://associate.ai',
        }
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=40) as r:
            data = json.loads(r.read())
            elapsed = round(time.time() - start, 2)
            reply = data['choices'][0]['message'].get('content', '').strip()
            lines.append(f"[OK] {label} - {elapsed}s")
            lines.append(f"     REPLY: {reply}")
            lines.append("")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try: msg = json.loads(body).get('error', {}).get('message', '')
        except: msg = body[:150]
        lines.append(f"[FAIL] {label}: HTTP {e.code} - {msg[:150]}")
        lines.append("")
    except Exception as e:
        lines.append(f"[FAIL] {label}: {type(e).__name__}: {str(e)[:100]}")
        lines.append("")

lines += ["=" * 70, "DONE"]

with open('model_test_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("Results written to model_test_results.txt")
