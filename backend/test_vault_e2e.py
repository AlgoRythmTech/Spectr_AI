"""
End-to-end test for Vault Box pipeline.
Tests: upload -> analyze -> verify response has sections with content.
"""
import requests
import json
import sys
import time
import os

BASE = "http://localhost:8000/api"
TOKEN = "Bearer dev_mock_token_7128"
HEADERS_JSON = {"Content-Type": "application/json", "Authorization": TOKEN}

# Create a small test PDF-like text file
TEST_CONTENT = """
LEASE AGREEMENT

This Lease Agreement ("Agreement") is entered into as of January 15, 2025, 
by and between:

LANDLORD: Rajesh Kumar Sharma, residing at 45 MG Road, New Delhi - 110001
TENANT: Priya Enterprises Pvt. Ltd., registered office at 12 Connaught Place, New Delhi

1. PREMISES: The Landlord hereby leases to the Tenant the commercial space 
   measuring approximately 2,500 sq. ft. located at Ground Floor, Tower B, 
   Cyber City, Gurugram, Haryana.

2. TERM: The lease term shall be for a period of 3 (three) years, commencing 
   from February 1, 2025 and ending on January 31, 2028.

3. RENT: The monthly rent shall be INR 1,50,000 (Rupees One Lakh Fifty Thousand only), 
   payable on or before the 5th day of each calendar month.

4. SECURITY DEPOSIT: The Tenant shall pay a security deposit of INR 9,00,000 
   (Rupees Nine Lakhs only) upon execution of this Agreement.

5. MAINTENANCE: Common Area Maintenance (CAM) charges of INR 15 per sq. ft. 
   per month shall be borne by the Tenant.

6. ESCALATION: The rent shall escalate by 10% at the end of each year of the lease term.

7. TERMINATION: Either party may terminate this Agreement by providing 3 months' 
   prior written notice. Early termination by the Tenant within the first year 
   shall result in forfeiture of the security deposit.

8. JURISDICTION: Any disputes arising out of this Agreement shall be subject 
   to the exclusive jurisdiction of courts in New Delhi.

Signed:
Rajesh Kumar Sharma (Landlord)
For Priya Enterprises Pvt. Ltd. (Tenant)
Date: January 15, 2025
"""

def test_vault():
    print("=" * 60)
    print("VAULT BOX END-TO-END TEST")
    print("=" * 60)
    
    # Step 1: Upload
    print("\n[STEP 1] Uploading test document...")
    files = {"file": ("test_lease_agreement.txt", TEST_CONTENT.encode(), "text/plain")}
    try:
        res = requests.post(f"{BASE}/vault/upload", files=files, headers={"Authorization": TOKEN}, timeout=30)
        print(f"  Upload Status: {res.status_code}")
        if res.status_code != 200:
            print(f"  ERROR: {res.text[:500]}")
            sys.exit(1)
        doc = res.json()
        doc_id = doc.get("doc_id")
        print(f"  doc_id: {doc_id}")
        print(f"  filename: {doc.get('filename')}")
        print(f"  doc_type: {doc.get('doc_type')}")
        print(f"  size: {doc.get('size')} bytes")
    except Exception as e:
        print(f"  FATAL UPLOAD ERROR: {e}")
        sys.exit(1)
    
    # Step 2: Analyze (this is the part that was failing)
    print("\n[STEP 2] Triggering Vault Analysis (general)...")
    print("  (This calls process_document_analysis -> map/reduce -> GPT-4o synthesis)")
    start = time.time()
    try:
        res = requests.post(f"{BASE}/vault/analyze", 
            json={
                "document_id": doc_id,
                "analysis_type": "general",
                "custom_prompt": "Provide a concise executive summary of this document in 3-5 key bullet points."
            },
            headers=HEADERS_JSON, timeout=180)
        elapsed = time.time() - start
        print(f"  Analyze Status: {res.status_code} (took {elapsed:.1f}s)")
        
        if res.status_code != 200:
            print(f"  ERROR BODY: {res.text[:1000]}")
            sys.exit(1)
        
        data = res.json()
        
        # Verify response structure
        print(f"\n[STEP 3] Verifying response structure...")
        response_text = data.get("response_text", "")
        sections = data.get("sections", [])
        analysis_type = data.get("analysis_type", "")
        doc_type = data.get("doc_type", "")
        
        print(f"  response_text length: {len(response_text)} chars")
        print(f"  sections count: {len(sections)}")
        print(f"  analysis_type: {analysis_type}")
        print(f"  doc_type: {doc_type}")
        
        if len(response_text) < 50:
            print(f"\n  *** FAILURE: response_text is too short! ***")
            print(f"  Content: '{response_text}'")
            sys.exit(1)
        
        if len(sections) == 0:
            print(f"\n  *** FAILURE: sections array is empty! ***")
            sys.exit(1)
        
        # Check sections have content
        for i, sec in enumerate(sections):
            title = sec.get("title", "NO TITLE")
            content = sec.get("content", "")
            print(f"  Section {i+1}: '{title}' ({len(content)} chars)")
        
        print(f"\n  First 300 chars of response_text:")
        print(f"  {response_text[:300]}")
        
        print(f"\n{'=' * 60}")
        print(f"*** ALL CHECKS PASSED — VAULT BOX IS WORKING ***")
        print(f"{'=' * 60}")
        
    except requests.exceptions.Timeout:
        print(f"  TIMEOUT after 180s — the backend is hanging!")
        sys.exit(1)
    except Exception as e:
        print(f"  FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_vault()
