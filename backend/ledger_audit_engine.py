import pandas as pd
import io
import re
from datetime import datetime

class LedgerAuditEngine:
    def __init__(self, raw_csv: bytes):
        try:
            self.df = pd.read_csv(io.BytesIO(raw_csv))
        except Exception as e:
            # Try to detect if it's tab separated or semicolon separated if comma fails
            self.df = pd.read_csv(io.BytesIO(raw_csv), sep=None, engine='python')
        
        # Standardize columns to lowercase without spaces
        self.df.columns = [str(c).strip().lower().replace(" ", "_") for c in self.df.columns]

    def _find_column(self, keywords):
        """Helper to safely identify likely columns for Amount, Date, Narration"""
        for col in self.df.columns:
            if any(k in col for k in keywords):
                return col
        return None

    def execute_audit(self):
        amount_col = self._find_column(['amount', 'debit', 'value', 'withdrawal'])
        date_col = self._find_column(['date', 'txn_date', 'posting_date'])
        mode_col = self._find_column(['mode', 'instrument', 'type'])
        narration_col = self._find_column(['narration', 'particulars', 'description', 'remarks'])
        
        if not amount_col:
            return {"error": "Could not identify an Amount or Debit column. Please ensure standard headers."}
            
        # Coerce amount to numeric
        self.df[amount_col] = pd.to_numeric(self.df[amount_col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
        
        # Coerce date to datetime
        if date_col:
            self.df['parsed_date'] = pd.to_datetime(self.df[date_col], errors='coerce')

        violations_40a3 = []
        violations_269ss = []
        holiday_transactions = []
        high_value_suspicious = []

        total_rows = len(self.df)
        total_value = self.df[amount_col].sum()

        for idx, row in self.df.iterrows():
            amount = row[amount_col]
            if amount == 0:
                continue

            narration = str(row.get(narration_col, "")).lower()
            mode = str(row.get(mode_col, narration)).lower()
            
            is_cash = 'cash' in mode or 'cash' in narration
            is_loan = 'loan' in narration or 'advance' in narration or 'deposit' in narration

            date_val = str(row.get(date_col, 'Unknown'))

            # 1. Section 40A(3): Cash expenditure exceeding 10,000
            if is_cash and amount > 10000 and not is_loan:
                violations_40a3.append({
                    "row": idx + 2, # +2 for header and 0-index
                    "date": date_val,
                    "amount": amount,
                    "narration": narration[:50],
                    "risk": "Section 40A(3) Disallowance - Cash expenditure > 10,000"
                })

            # 2. Section 269SS/T: Cash Loans/Deposits exceeding 20,000
            if is_cash and is_loan and amount > 20000:
                violations_269ss.append({
                    "row": idx + 2,
                    "date": date_val,
                    "amount": amount,
                    "narration": narration[:50],
                    "risk": "Section 269SS/T Penalty - Cash Loan/Deposit > 20,000"
                })

            # 3. Sunday/Holiday Transactions Check (Red Flag for fake invoices/cash entries)
            if 'parsed_date' in self.df.columns and pd.notnull(row['parsed_date']):
                if row['parsed_date'].weekday() == 6:  # Sunday
                    holiday_transactions.append({
                        "row": idx + 2,
                        "date": date_val,
                        "amount": amount,
                        "narration": narration[:50],
                        "risk": "Suspicious Sunday Transaction"
                    })

        return {
            "summary": {
                "total_rows_scanned": total_rows,
                "total_value_processed": float(total_value),
                "section_40A3_flags": len(violations_40a3),
                "section_269SS_flags": len(violations_269ss),
                "holiday_flags": len(holiday_transactions)
            },
            "anomalies": {
                "40a3_violations": violations_40a3[:100],  # cap at 100 to prevent payload blast
                "269ss_violations": violations_269ss[:100],
                "holiday_transactions": holiday_transactions[:100]
            }
        }

async def audit_tally_ledger(file_bytes: bytes) -> dict:
    # Offload pandas processing to prevent event loop blocking
    import asyncio
    engine = LedgerAuditEngine(file_bytes)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, engine.execute_audit)
