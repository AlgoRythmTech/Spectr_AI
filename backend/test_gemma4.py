import urllib.request, json, ssl, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY = 'AIzaSyAHA7_KBuo22yKA6NzrjsAZ0jZGkb_5XcM'

def test_gemma_4(model_name):
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}'
    
    payload = json.dumps({
        "contents": [{
            "parts": [{"text": "Under Section 73 CGST Act, what is the exact time limit for issuing SCN for FY 2021-22? One sentence."}]
        }]
    }).encode('utf-8')
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            data = json.loads(r.read())
            elapsed = round(time.time() - start, 2)
            reply = data['candidates'][0]['content']['parts'][0]['text'].strip()
            print(f"[OK] {model_name} ({elapsed}s)")
            print(f"     REPLY: {reply}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"[FAIL] {model_name}: HTTP {e.code}")
        print(f"     ERROR: {json.loads(body).get('error', {}).get('message', body)}")
        return False
    except Exception as e:
        print(f"[FAIL] {model_name}: {type(e).__name__} - {e}")
        return False

print("Testing exact Gemma 4 models on Google AI Studio...")
success_1 = test_gemma_4('gemma-4-26b-a4b-it')
success_2 = test_gemma_4('gemma-4-31b-it')
