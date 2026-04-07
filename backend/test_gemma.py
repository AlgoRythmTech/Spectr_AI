import urllib.request, json, ssl, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY = 'AIzaSyAHA7_KBuo22yKA6NzrjsAZ0jZGkb_5XcM'

# Google AI Studio API for Gemma/Gemini
def test_google_model(model_name):
    # Depending on model type (Gemini vs Gemma), the endpoint may differ for chat, 
    # but generatesContent works for all modern ones.
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
            
            # Extract content
            try:
                reply = data['candidates'][0]['content']['parts'][0]['text'].strip()
            except (KeyError, IndexError):
                reply = "Response parse failed: " + str(data)
                
            print(f"[OK] {model_name} ({elapsed}s)")
            print(f"     REPLY: {reply}")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"[FAIL] {model_name}: HTTP {e.code}")
        print(f"     ERROR: {body.strip()}")
    except Exception as e:
        print(f"[FAIL] {model_name}: {type(e).__name__} - {e}")

# Get available models
print("Fetching available models from Google AI Studio...")
models_url = f'https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}'
req = urllib.request.Request(models_url)
try:
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        data = json.loads(r.read())
        gemma_models = [m['name'] for m in data.get('models', []) if 'gemma' in m['name'].lower()]
        print(f"Found {len(gemma_models)} Gemma models: {', '.join(gemma_models) if gemma_models else 'None'}")
        
        models_to_test = [m.split('/')[1] for m in gemma_models]
        if not models_to_test:
            models_to_test = ['gemma-2-27b-it', 'gemini-1.5-flash'] # fallbacks
            print("No Gemma models listed by default, trying fallbacks...")
            
        print("\nTesting models:")
        for m in models_to_test:
            test_google_model(m)
            time.sleep(1) # small delay
            
except Exception as e:
    print(f"Failed to fetch models: {e}")
    print("Testing hardcoded Gemma 2 27B model...")
    test_google_model('gemma-2-27b-it')
