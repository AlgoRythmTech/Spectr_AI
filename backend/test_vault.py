
import asyncio
from ai_engine import process_document_analysis

async def run_test():
    doc_text = '''IN THE SUPREME COURT OF INDIA
CIVIL APPELLATE JURISDICTION
CIVIL APPEAL NO. 8766-67 OF 2019
Committee of Creditors of Essar Steel India Limited vs. Satish Kumar Gupta & Ors.
The issue is whether the CoC has supremacy over the distribution of funds to operational creditors under the IBC 2016.
Date: 15 November 2019.'''
    
    print('Starting Vault Test...')
    try:
        result = await process_document_analysis(document_text=doc_text, analysis_type='general')
        print('\n--- SUCCESS! Final Response ---')
        print(result['response_text'][:500] + '...')
        print('\n--- SECTIONS PARSED ---')
        print(result['sections'])
    except Exception as e:
        print(f'\n--- FAILURE ---: {e}')

asyncio.run(run_test())

