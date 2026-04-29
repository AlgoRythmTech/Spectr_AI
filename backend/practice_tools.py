"""
Practice Tools Engine — High-value tools for real CA/Lawyer pain points.
1. IPC → BNS Section Mapper (and CrPC → BNSS, Evidence → BSA)
2. TDS Section Auto-Classifier
3. Notice Validity Auto-Checker
4. Deadline Penalty Calculator
5. Tally XML/JSON Ledger Importer
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# =====================================================================
# 1. OLD → NEW CRIMINAL LAW SECTION MAPPER
# IPC (1860) → BNS (2023), CrPC (1973) → BNSS (2023), IEA (1872) → BSA (2023)
# Effective date: July 1, 2024
# =====================================================================

IPC_TO_BNS = {
    # Offences Against the State
    "120B": {"bns": "61", "title": "Criminal Conspiracy"},
    "121": {"bns": "147", "title": "Waging war against India"},
    "124A": {"bns": "152", "title": "Sedition → Acts endangering sovereignty"},
    # Offences Against Public Tranquility
    "141": {"bns": "189", "title": "Unlawful assembly"},
    "143": {"bns": "191", "title": "Punishment for unlawful assembly"},
    "144": {"bns": "192", "title": "Joining unlawful assembly armed with deadly weapon"},
    "147": {"bns": "189", "title": "Rioting"},
    "148": {"bns": "190", "title": "Rioting armed with deadly weapon"},
    "153A": {"bns": "196", "title": "Promoting enmity between groups"},
    # Offences Relating to Documents
    "170": {"bns": "204", "title": "Personating a public servant"},
    "171": {"bns": "205", "title": "Wearing garb of a public servant"},
    # Offences Against Human Body
    "299": {"bns": "105", "title": "Culpable homicide"},
    "300": {"bns": "101", "title": "Murder"},
    "302": {"bns": "103", "title": "Punishment for murder"},
    "304": {"bns": "105", "title": "Culpable homicide not amounting to murder"},
    "304A": {"bns": "106", "title": "Death by negligence"},
    "304B": {"bns": "80", "title": "Dowry death"},
    "306": {"bns": "108", "title": "Abetment of suicide"},
    "307": {"bns": "109", "title": "Attempt to murder"},
    "308": {"bns": "110", "title": "Attempt to commit culpable homicide"},
    "319": {"bns": "114", "title": "Hurt"},
    "320": {"bns": "114", "title": "Grievous hurt"},
    "323": {"bns": "115(2)", "title": "Voluntarily causing hurt"},
    "324": {"bns": "118", "title": "Voluntarily causing hurt by dangerous weapons"},
    "325": {"bns": "117", "title": "Voluntarily causing grievous hurt"},
    "326": {"bns": "118", "title": "Grievous hurt by dangerous weapons"},
    "354": {"bns": "74", "title": "Assault on woman with intent to outrage modesty"},
    "354A": {"bns": "75", "title": "Sexual harassment"},
    "354B": {"bns": "76", "title": "Assault with intent to disrobe woman"},
    "354C": {"bns": "77", "title": "Voyeurism"},
    "354D": {"bns": "78", "title": "Stalking"},
    "359": {"bns": "135", "title": "Kidnapping"},
    "363": {"bns": "137", "title": "Punishment for kidnapping"},
    "366": {"bns": "139", "title": "Kidnapping woman to compel marriage"},
    "375": {"bns": "63", "title": "Rape"},
    "376": {"bns": "64", "title": "Punishment for rape"},
    "376A": {"bns": "66", "title": "Intercourse by person in authority"},
    "376D": {"bns": "70", "title": "Gang rape"},
    # Offences Against Property
    "378": {"bns": "303", "title": "Theft"},
    "379": {"bns": "303(2)", "title": "Punishment for theft"},
    "380": {"bns": "305(a)", "title": "Theft in dwelling house"},
    "383": {"bns": "308", "title": "Extortion"},
    "384": {"bns": "308", "title": "Punishment for extortion"},
    "390": {"bns": "309", "title": "Robbery"},
    "392": {"bns": "309(2)", "title": "Punishment for robbery"},
    "395": {"bns": "310(2)", "title": "Dacoity"},
    "397": {"bns": "310(3)", "title": "Robbery or dacoity with attempt to cause death"},
    "403": {"bns": "314", "title": "Dishonest misappropriation"},
    "405": {"bns": "316", "title": "Criminal breach of trust"},
    "406": {"bns": "316(2)", "title": "Punishment for criminal breach of trust"},
    "409": {"bns": "316(5)", "title": "CBT by public servant / banker / agent"},
    "415": {"bns": "318", "title": "Cheating"},
    "417": {"bns": "318(2)", "title": "Punishment for cheating"},
    "418": {"bns": "318(4)", "title": "Cheating with knowledge of wrongful loss"},
    "419": {"bns": "319", "title": "Cheating by personation"},
    "420": {"bns": "318", "title": "Cheating and dishonestly inducing delivery of property"},
    "421": {"bns": "320", "title": "Dishonest/fraudulent removal of property"},
    "425": {"bns": "324", "title": "Mischief"},
    "426": {"bns": "324(2)", "title": "Punishment for mischief"},
    "427": {"bns": "324(3)", "title": "Mischief causing damage above fifty rupees"},
    "441": {"bns": "329", "title": "Criminal trespass"},
    "447": {"bns": "329(2)", "title": "Punishment for criminal trespass"},
    "448": {"bns": "330", "title": "House-trespass"},
    "452": {"bns": "331", "title": "House-trespass with preparation for hurt"},
    "453": {"bns": "332", "title": "Lurking house-trespass or house-breaking by night"},
    "457": {"bns": "333", "title": "Lurking house-trespass at night with preparation for hurt"},
    # Forgery & Counterfeiting
    "463": {"bns": "336", "title": "Forgery"},
    "464": {"bns": "336(3)", "title": "Making false document"},
    "465": {"bns": "336(2)", "title": "Punishment for forgery"},
    "467": {"bns": "338", "title": "Forgery of valuable security"},
    "468": {"bns": "339", "title": "Forgery for purpose of cheating"},
    "471": {"bns": "340", "title": "Using as genuine a forged document"},
    # Criminal Intimidation
    "503": {"bns": "351", "title": "Criminal intimidation"},
    "504": {"bns": "352", "title": "Intentional insult to provoke breach of peace"},
    "506": {"bns": "351(2)", "title": "Punishment for criminal intimidation"},
    "509": {"bns": "79", "title": "Word/gesture intended to insult modesty of woman"},
    # Defamation
    "499": {"bns": "356", "title": "Defamation"},
    "500": {"bns": "356(2)", "title": "Punishment for defamation"},
    # Attempt
    "511": {"bns": "62", "title": "Attempt to commit offences"},
    # Common
    "34": {"bns": "3(5)", "title": "Common intention"},
    "107": {"bns": "45", "title": "Abetment"},
    "109": {"bns": "48", "title": "Punishment for abetment"},
    "114": {"bns": "52", "title": "Abettor present when offence is committed"},
    "149": {"bns": "190(2)", "title": "Every member of unlawful assembly guilty of offence"},
    "191": {"bns": "229", "title": "Giving false evidence"},
    "193": {"bns": "229(2)", "title": "Punishment for false evidence"},
    "199": {"bns": "233", "title": "False statement made in declaration"},
    "200": {"bns": "234", "title": "Using false evidence"},
    "201": {"bns": "238", "title": "Causing disappearance of evidence"},
    "204": {"bns": "241", "title": "Destruction of document to prevent production"},
    "211": {"bns": "248", "title": "False charge of offence made with intent to injure"},
    "212": {"bns": "249", "title": "Harbouring offender"},
    "228": {"bns": "223", "title": "Intentional insult to court"},
}

CRPC_TO_BNSS = {
    "41": {"bnss": "35", "title": "When police may arrest without warrant"},
    "41A": {"bnss": "35", "title": "Notice of appearance before police officer"},
    "57": {"bnss": "58", "title": "Person arrested not to be detained more than 24 hours"},
    "125": {"bnss": "144", "title": "Maintenance of wives, children and parents"},
    "144": {"bnss": "163", "title": "Power to issue order in urgent cases of nuisance"},
    "154": {"bnss": "173", "title": "Information in cognizable cases (FIR)"},
    "155": {"bnss": "174", "title": "Information in non-cognizable cases"},
    "156": {"bnss": "175", "title": "Police officer's power to investigate cognizable case"},
    "161": {"bnss": "180", "title": "Examination of witnesses by police"},
    "164": {"bnss": "183", "title": "Recording of confessions and statements"},
    "167": {"bnss": "187", "title": "Procedure when investigation not completed in 24 hours"},
    "173": {"bnss": "193", "title": "Report of police officer on completion of investigation (Chargesheet)"},
    "190": {"bnss": "210", "title": "Cognizance of offences by Magistrate"},
    "197": {"bnss": "218", "title": "Prosecution of Judges and public servants"},
    "200": {"bnss": "223", "title": "Examination of complainant"},
    "204": {"bnss": "227", "title": "Dismissal of complaint"},
    "225": {"bnss": "251", "title": "Trial of summons cases by Magistrate"},
    "227": {"bnss": "250", "title": "Discharge (Sessions trial)"},
    "228": {"bnss": "251", "title": "Framing of charge (Sessions trial)"},
    "239": {"bnss": "262", "title": "When accused shall be discharged (warrant case)"},
    "245": {"bnss": "268", "title": "When accused shall be acquitted (summons)"},
    "250": {"bnss": "273", "title": "Compensation on accusation without reasonable cause"},
    "260": {"bnss": "283", "title": "Summary trial by Magistrate"},
    "313": {"bnss": "337", "title": "Examination of accused"},
    "354": {"bnss": "392", "title": "Language of judgments"},
    "374": {"bnss": "399", "title": "Appeals from convictions"},
    "378": {"bnss": "403", "title": "Appeal by State Government against acquittal"},
    "397": {"bnss": "426", "title": "Calling for records to exercise revisional jurisdiction"},
    "401": {"bnss": "430", "title": "High Court's powers of revision"},
    "436": {"bnss": "478", "title": "Bail in non-bailable offences"},
    "437": {"bnss": "480", "title": "Bail — when bail may be taken"},
    "438": {"bnss": "482", "title": "Anticipatory bail"},
    "439": {"bnss": "483", "title": "Special powers of High Court/Sessions Court regarding bail"},
    "468": {"bnss": "512", "title": "Bar to taking cognizance after lapse of limitation"},
    "482": {"bnss": "528", "title": "Inherent powers of High Court"},
}

IEA_TO_BSA = {
    "3": {"bsa": "2", "title": "Interpretation clause"},
    "17": {"bsa": "15", "title": "Admission"},
    "21": {"bsa": "19", "title": "Proof of admissions against persons making them"},
    "24": {"bsa": "22", "title": "Confession caused by inducement, threat or promise"},
    "25": {"bsa": "23", "title": "Confession to police officer not to be proved"},
    "26": {"bsa": "24", "title": "Confession by accused while in custody of police"},
    "27": {"bsa": "25", "title": "How much of information received from accused may be proved"},
    "32": {"bsa": "26", "title": "Cases in which statement of relevant fact by person who is dead or cannot be found, etc., is relevant (Dying declaration)"},
    "45": {"bsa": "39", "title": "Opinions of experts"},
    "47": {"bsa": "41", "title": "Opinion as to handwriting"},
    "56": {"bsa": "50", "title": "Fact judicially noticeable need not be proved"},
    "57": {"bsa": "51", "title": "Facts of which Court must take judicial notice"},
    "59": {"bsa": "53", "title": "Proof of facts by oral evidence"},
    "60": {"bsa": "54", "title": "Oral evidence must be direct"},
    "61": {"bsa": "55", "title": "Proof of contents of documents"},
    "63": {"bsa": "57", "title": "Primary evidence"},
    "65": {"bsa": "59", "title": "Secondary evidence"},
    "65B": {"bsa": "63", "title": "Admissibility of electronic records"},
    "73": {"bsa": "67", "title": "Comparison of signature, writing or seal"},
    "76": {"bsa": "70", "title": "Certified copies of public documents"},
    "101": {"bsa": "104", "title": "Burden of proof"},
    "102": {"bsa": "105", "title": "On whom burden of proof lies"},
    "103": {"bsa": "106", "title": "Burden of proof as to particular fact"},
    "106": {"bsa": "108", "title": "Burden of proving fact especially within knowledge"},
    "113A": {"bsa": "118", "title": "Presumption as to abetment of suicide by married woman"},
    "113B": {"bsa": "119", "title": "Presumption as to dowry death"},
    "114": {"bsa": "120", "title": "Court may presume existence of certain facts"},
    "132": {"bsa": "137", "title": "Witness not excused from answering on ground that answer will criminate"},
    "137": {"bsa": "142", "title": "Examination-in-chief, cross-examination, re-examination"},
    "138": {"bsa": "143", "title": "Order of examinations and direction of re-examination"},
    "145": {"bsa": "148", "title": "Cross-examination as to previous statements in writing"},
    "154": {"bsa": "155", "title": "Question by party to his own witness (Hostile witness)"},
    "155": {"bsa": "156", "title": "Impeaching credit of witness"},
}


def map_section(old_section: str, direction: str = "old_to_new") -> dict:
    """
    Map old criminal law sections to new (or vice versa).
    direction: 'old_to_new' (IPC→BNS) or 'new_to_old' (BNS→IPC)
    """
    old_section = str(old_section).strip().upper()

    if direction == "old_to_new":
        # Try IPC → BNS
        if old_section in IPC_TO_BNS:
            m = IPC_TO_BNS[old_section]
            return {
                "found": True,
                "old_act": "Indian Penal Code, 1860",
                "old_section": f"Section {old_section} IPC",
                "new_act": "Bharatiya Nyaya Sanhita, 2023",
                "new_section": f"Section {m['bns']} BNS",
                "title": m["title"],
                "effective_from": "2024-07-01",
                "note": "BNS applies to offences committed on or after July 1, 2024. For prior offences, IPC applies."
            }
        # Try CrPC → BNSS
        if old_section in CRPC_TO_BNSS:
            m = CRPC_TO_BNSS[old_section]
            return {
                "found": True,
                "old_act": "Code of Criminal Procedure, 1973",
                "old_section": f"Section {old_section} CrPC",
                "new_act": "Bharatiya Nagarik Suraksha Sanhita, 2023",
                "new_section": f"Section {m['bnss']} BNSS",
                "title": m["title"],
                "effective_from": "2024-07-01",
            }
        # Try IEA → BSA
        if old_section in IEA_TO_BSA:
            m = IEA_TO_BSA[old_section]
            return {
                "found": True,
                "old_act": "Indian Evidence Act, 1872",
                "old_section": f"Section {old_section} IEA",
                "new_act": "Bharatiya Sakshya Adhiniyam, 2023",
                "new_section": f"Section {m['bsa']} BSA",
                "title": m["title"],
                "effective_from": "2024-07-01",
            }
        # Check if it's a number without suffix
        clean = re.sub(r'[^0-9A-Z]', '', old_section)
        if clean != old_section:
            return map_section(clean, direction)

        return {"found": False, "error": f"Section {old_section} not found in IPC/CrPC/IEA mapping database. It may be from a different act."}

    elif direction == "new_to_old":
        # Reverse lookup: BNS → IPC
        for ipc_sec, data in IPC_TO_BNS.items():
            if data["bns"].upper() == old_section:
                return {
                    "found": True,
                    "new_act": "Bharatiya Nyaya Sanhita, 2023",
                    "new_section": f"Section {old_section} BNS",
                    "old_act": "Indian Penal Code, 1860",
                    "old_section": f"Section {ipc_sec} IPC",
                    "title": data["title"],
                }
        # Reverse: BNSS → CrPC
        for crpc_sec, data in CRPC_TO_BNSS.items():
            if data["bnss"].upper() == old_section:
                return {
                    "found": True,
                    "new_act": "Bharatiya Nagarik Suraksha Sanhita, 2023",
                    "new_section": f"Section {old_section} BNSS",
                    "old_act": "Code of Criminal Procedure, 1973",
                    "old_section": f"Section {crpc_sec} CrPC",
                    "title": data["title"],
                }
        # Reverse: BSA → IEA
        for iea_sec, data in IEA_TO_BSA.items():
            if data["bsa"].upper() == old_section:
                return {
                    "found": True,
                    "new_act": "Bharatiya Sakshya Adhiniyam, 2023",
                    "new_section": f"Section {old_section} BSA",
                    "old_act": "Indian Evidence Act, 1872",
                    "old_section": f"Section {iea_sec} IEA",
                    "title": data["title"],
                }
        return {"found": False, "error": f"Section {old_section} not found in BNS/BNSS/BSA reverse mapping."}

    return {"found": False, "error": "Invalid direction. Use 'old_to_new' or 'new_to_old'."}


def batch_map_sections(sections: list, direction: str = "old_to_new") -> list:
    """Map multiple sections at once. Returns list of mapping results."""
    return [map_section(s, direction) for s in sections]


# =====================================================================
# 2. TDS SECTION AUTO-CLASSIFIER
# Given a payment description, classify the correct TDS section
# =====================================================================

TDS_SECTIONS = {
    "194C": {
        "title": "Payment to Contractors",
        "threshold_single": 30000,
        "threshold_aggregate": 100000,
        "rate_individual": 1.0,
        "rate_others": 2.0,
        "keywords": ["contractor", "sub-contractor", "works contract", "job work", "labour",
                      "manufacturing", "supply of labour", "contract", "catering",
                      "transport", "freight", "hauling", "carriage"],
        "section_text": "Any payment to a resident contractor/sub-contractor for carrying out any work (including supply of labour).",
    },
    "194J": {
        "title": "Fees for Professional/Technical Services",
        "threshold": 30000,
        "rate_professional": 10.0,
        "rate_technical": 2.0,
        "rate_royalty": 2.0,
        "keywords": ["professional", "consultant", "advocate", "lawyer", "architect",
                      "interior designer", "chartered accountant", "CA", "company secretary",
                      "CS", "cost accountant", "CMA", "doctor", "engineer", "medical",
                      "technical services", "royalty", "non-compete fee", "managerial services"],
        "section_text": "Fees for professional services, technical services, royalty, or non-compete fees to residents.",
    },
    "194H": {
        "title": "Commission or Brokerage",
        "threshold": 15000,
        "rate": 5.0,
        "keywords": ["commission", "brokerage", "broker", "agent", "distributor margin",
                      "channel partner", "referral fee", "finder's fee", "marketing incentive"],
        "section_text": "Commission or brokerage payable to a resident (except insurance commission under 194D).",
    },
    "194I": {
        "title": "Rent",
        "threshold": 240000,
        "rate_plant_machinery": 2.0,
        "rate_land_building": 10.0,
        "keywords": ["rent", "lease", "hire", "warehouse", "godown", "office rent",
                      "factory rent", "equipment hire", "vehicle lease", "plant rent"],
        "section_text": "Rent payable to a resident for land, building, plant, machinery, equipment, furniture, or fittings.",
    },
    "194A": {
        "title": "Interest (other than on securities)",
        "threshold_bank": 40000,
        "threshold_senior": 50000,
        "threshold_others": 5000,
        "rate": 10.0,
        "keywords": ["interest", "interest on deposit", "FD interest", "loan interest",
                      "interest on advance", "interest on debentures"],
        "section_text": "Interest other than interest on securities, paid to a resident.",
    },
    "194T": {
        "title": "Payments to Partners of Firm",
        "threshold": 20000,
        "rate": 10.0,
        "effective_from": "2025-04-01",
        "keywords": ["partner salary", "partner remuneration", "partner interest",
                      "partner bonus", "partner commission", "partner payment",
                      "payment to partner"],
        "section_text": "NEW (w.e.f. 01-04-2025): TDS on salary, remuneration, commission, bonus, or interest paid by a firm to its partners.",
    },
    "194B": {
        "title": "Winnings from Lottery/Crossword Puzzle",
        "threshold": 10000,
        "rate": 30.0,
        "keywords": ["lottery", "crossword", "puzzle", "game show", "winnings",
                      "horse race", "card game", "gambling"],
        "section_text": "Winnings from lotteries, crossword puzzles, card games, and other games of any sort.",
    },
    "194D": {
        "title": "Insurance Commission",
        "threshold": 15000,
        "rate": 5.0,
        "keywords": ["insurance commission", "insurance agent", "LIC agent",
                      "insurance brokerage"],
        "section_text": "Insurance commission to a resident agent.",
    },
    "194DA": {
        "title": "Payment in respect of Life Insurance Policy",
        "threshold": 100000,
        "rate": 5.0,
        "keywords": ["life insurance", "insurance maturity", "insurance proceeds",
                      "endowment", "ULIP surrender"],
        "section_text": "Payment under a life insurance policy (including bonus) to a resident.",
    },
    "194E": {
        "title": "Payment to Non-Resident Sportsman/Entertainer",
        "threshold": 0,
        "rate": 20.0,
        "keywords": ["non-resident sportsman", "non-resident entertainer", "NRI athlete",
                      "foreign player", "performance fee NRI"],
        "section_text": "Payment to non-resident sportsman or sports association / entertainer.",
    },
    "194G": {
        "title": "Commission on Sale of Lottery Tickets",
        "threshold": 15000,
        "rate": 5.0,
        "keywords": ["lottery ticket commission", "lottery distributor"],
        "section_text": "Commission or remuneration on sale of lottery tickets.",
    },
    "194IA": {
        "title": "Payment on Transfer of Immovable Property",
        "threshold": 5000000,
        "rate": 1.0,
        "keywords": ["property purchase", "immovable property", "land purchase",
                      "flat purchase", "house purchase", "real estate transfer"],
        "section_text": "Payment for transfer of immovable property (other than agricultural land) where consideration > Rs 50 lakh.",
    },
    "194IB": {
        "title": "Rent by Individual/HUF",
        "threshold": 50000,
        "rate": 5.0,
        "keywords": ["individual rent", "HUF rent", "tenant TDS"],
        "section_text": "Rent paid by individual/HUF not liable to tax audit, where monthly rent > Rs 50,000.",
    },
    "194N": {
        "title": "Cash Withdrawal",
        "threshold": 10000000,
        "rate_non_filer": 5.0,
        "rate_filer": 2.0,
        "keywords": ["cash withdrawal", "bank withdrawal", "ATM withdrawal"],
        "section_text": "Cash withdrawal from bank/post office exceeding Rs 1 crore (Rs 20 lakh for non-filers).",
    },
    "194O": {
        "title": "E-commerce Operator TDS",
        "threshold": 500000,
        "rate": 1.0,
        "keywords": ["e-commerce", "online marketplace", "amazon seller", "flipkart seller",
                      "online platform payment"],
        "section_text": "Payment by e-commerce operator to e-commerce participant for sale of goods/services through its platform.",
    },
    "194Q": {
        "title": "Purchase of Goods",
        "threshold": 5000000,
        "rate": 0.1,
        "keywords": ["purchase of goods", "goods purchase", "buy goods", "procurement"],
        "section_text": "Purchase of goods from a resident seller where aggregate > Rs 50 lakh in a year (applicable to buyers with turnover > Rs 10 crore).",
    },
    "194R": {
        "title": "Benefits/Perquisites (Business)",
        "threshold": 20000,
        "rate": 10.0,
        "keywords": ["perquisite", "benefit", "gift", "incentive trip",
                      "sponsored travel", "free goods", "trade discount in kind"],
        "section_text": "Any benefit or perquisite arising from business/profession provided to a resident.",
    },
    "194S": {
        "title": "Payment on Transfer of Virtual Digital Asset",
        "threshold": 10000,
        "rate": 1.0,
        "keywords": ["crypto", "virtual digital asset", "VDA", "bitcoin", "cryptocurrency",
                      "NFT", "digital currency"],
        "section_text": "Payment for transfer of virtual digital assets.",
    },
    "195": {
        "title": "Payment to Non-Residents",
        "threshold": 0,
        "rate": 20.0,
        "keywords": ["NRI payment", "non-resident", "foreign payment", "overseas payment",
                      "payment to foreigner", "section 195", "DTAA"],
        "section_text": "Any sum chargeable to tax payable to a non-resident (rate depends on nature of income and applicable DTAA).",
    },
}


def classify_tds_section(payment_description: str, amount: float = 0,
                         payee_type: str = "company", is_non_filer: bool = False) -> dict:
    """
    Given a payment description, classify the applicable TDS section.
    Returns section, rate, threshold, and compliance notes.
    """
    desc_lower = payment_description.lower()

    matches = []
    for section, data in TDS_SECTIONS.items():
        score = 0
        for kw in data["keywords"]:
            if kw.lower() in desc_lower:
                score += len(kw)  # Longer keyword matches = higher confidence
        if score > 0:
            matches.append((section, data, score))

    matches.sort(key=lambda x: x[2], reverse=True)

    if not matches:
        return {
            "classified": False,
            "error": "Could not classify payment. Provide more description (e.g., 'rent for office', 'professional fees to CA', 'contractor payment').",
            "suggestion": "Common TDS sections: 194C (contractors), 194J (professionals), 194H (commission), 194I (rent), 194T (partner payments).",
        }

    best_section, best_data, confidence = matches[0]

    # Calculate applicable rate
    rate = best_data.get("rate", 0)
    if best_section == "194C":
        rate = best_data["rate_individual"] if payee_type in ("individual", "huf") else best_data["rate_others"]
    elif best_section == "194I":
        if any(kw in desc_lower for kw in ["plant", "machinery", "equipment", "vehicle"]):
            rate = best_data["rate_plant_machinery"]
        else:
            rate = best_data["rate_land_building"]
    elif best_section == "194J":
        if any(kw in desc_lower for kw in ["technical", "royalty", "non-compete"]):
            rate = best_data["rate_technical"]
        else:
            rate = best_data["rate_professional"]

    # Check 206AB (non-filer higher rate)
    sec_206ab_rate = max(rate * 2, 5.0) if is_non_filer else None

    # Determine threshold
    threshold = best_data.get("threshold", best_data.get("threshold_single", best_data.get("threshold_others", 0)))

    tds_amount = amount * rate / 100 if amount > 0 else None

    result = {
        "classified": True,
        "section": best_section,
        "title": best_data["title"],
        "rate_percent": rate,
        "threshold": threshold,
        "section_text": best_data["section_text"],
        "tds_amount": round(tds_amount, 2) if tds_amount else None,
        "payee_type": payee_type,
        "payment_description": payment_description,
    }

    if sec_206ab_rate:
        result["section_206ab_warning"] = f"Payee is a non-filer under Section 206AB. Higher rate applies: {sec_206ab_rate}% instead of {rate}%."
        result["rate_206ab"] = sec_206ab_rate
        if amount > 0:
            result["tds_amount_206ab"] = round(amount * sec_206ab_rate / 100, 2)

    if best_data.get("effective_from"):
        result["effective_from"] = best_data["effective_from"]
        result["note"] = f"This section is effective from {best_data['effective_from']}. Not applicable for earlier periods."

    if len(matches) > 1:
        result["alternatives"] = [
            {"section": m[0], "title": m[1]["title"], "confidence": "lower"}
            for m in matches[1:3]
        ]

    return result


# =====================================================================
# 3. NOTICE VALIDITY AUTO-CHECKER
# Check if a tax notice is valid based on limitation, DIN, jurisdiction
# =====================================================================

def check_notice_validity(notice_type: str, notice_date: str,
                          assessment_year: str = "", financial_year: str = "",
                          has_din: bool = True, is_fraud_alleged: bool = False) -> dict:
    """
    Automatically check if a tax/GST notice is valid.
    Returns validity status with specific legal grounds for challenge.
    """
    challenges = []
    valid = True

    try:
        n_date = datetime.strptime(notice_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "notice_date must be YYYY-MM-DD format"}

    today = datetime.now()
    notice_type_lower = notice_type.lower().strip()

    # === DIN CHECK (CBDT Circular 19/2019 dated 14.08.2019) ===
    if not has_din and n_date >= datetime(2019, 10, 1):
        challenges.append({
            "ground": "No DIN (Document Identification Number)",
            "legal_basis": "CBDT Circular No. 19/2019 dated 14.08.2019",
            "effect": "Notice is INVALID. All communications from the IT Department issued on or after 01-10-2019 must bear a DIN. Non-compliance renders the notice non-est in law.",
            "case_law": "Ashok Kumar Agarwal v. UOI (2021) — Allahabad HC held DIN-less notices are bad in law.",
            "severity": "CRITICAL — challenge immediately"
        })
        valid = False

    # === LIMITATION CHECKS ===
    if notice_type_lower in ["143(2)", "scrutiny", "scrutiny notice", "limited scrutiny"]:
        # Section 143(2): Must be served within 3 months from end of FY in which return was filed
        # For belated/revised returns, the deadline shifts accordingly
        if assessment_year:
            try:
                ay_start = int(assessment_year.split("-")[0])
                # General rule: notice must be served by Sep 30 of the AY
                # Post-amendment: within 3 months from end of FY of return filing
                deadline = datetime(ay_start, 9, 30)
                if n_date > deadline:
                    challenges.append({
                        "ground": "Limitation expired under Section 143(2)",
                        "legal_basis": f"Section 143(2) IT Act — notice must be served within prescribed time for AY {assessment_year}",
                        "effect": "Notice is TIME-BARRED. Assessment order passed pursuant to a time-barred notice is void ab initio.",
                        "severity": "CRITICAL"
                    })
                    valid = False
            except (ValueError, IndexError):
                pass

    elif notice_type_lower in ["148", "148a", "reassessment", "reopening"]:
        # Section 148/148A: Different limitation periods post Finance Act 2021
        if assessment_year:
            try:
                ay_start = int(assessment_year.split("-")[0])
                ay_end_date = datetime(ay_start + 1, 3, 31)
                years_elapsed = (n_date - ay_end_date).days / 365.25

                if not is_fraud_alleged and years_elapsed > 3:
                    challenges.append({
                        "ground": "Limitation expired — non-fraud reassessment beyond 3 years",
                        "legal_basis": "Section 149(1)(a) IT Act — notice under Section 148 cannot be issued after 3 years from end of AY unless income escaping > Rs 50 lakh",
                        "effect": "Reassessment notice is TIME-BARRED for non-fraud cases where escaped income < Rs 50 lakh.",
                        "severity": "CRITICAL"
                    })
                    valid = False
                elif years_elapsed > 10:
                    challenges.append({
                        "ground": "Absolute outer limit of 10 years exceeded",
                        "legal_basis": "Section 149(1)(b) IT Act — no notice under 148 after 10 years from end of AY",
                        "effect": "Notice is ABSOLUTELY time-barred. No exception applies.",
                        "severity": "CRITICAL"
                    })
                    valid = False

                # Check if 148A procedure was followed (mandatory post 01-04-2021)
                if n_date >= datetime(2021, 4, 1):
                    challenges.append({
                        "ground": "Verify Section 148A compliance",
                        "legal_basis": "Section 148A IT Act (w.e.f. 01-04-2021) — AO must conduct inquiry and provide opportunity before issuing 148 notice",
                        "effect": "If Section 148A procedure (inquiry + show cause + order) was not followed, the 148 notice is void. Check if you received a 148A(b) show cause BEFORE the 148 notice.",
                        "severity": "HIGH — verify procedural compliance"
                    })
            except (ValueError, IndexError):
                pass

    elif notice_type_lower in ["73", "section 73", "gst 73", "gst demand"]:
        # GST Section 73: 3-year limitation (non-fraud)
        if financial_year:
            try:
                fy_parts = financial_year.split("-")
                fy_end_year = int(fy_parts[0]) + 1 if len(fy_parts[0]) == 4 else int("20" + fy_parts[1])
                # Due date of annual return for the FY
                annual_return_due = datetime(fy_end_year, 12, 31)  # GSTR-9 due date
                limitation_deadline = annual_return_due.replace(year=annual_return_due.year + 3)

                if n_date > limitation_deadline:
                    challenges.append({
                        "ground": f"Section 73 limitation expired for FY {financial_year}",
                        "legal_basis": "Section 73(10) CGST Act — order must be issued within 3 years from due date of annual return",
                        "effect": "Demand notice is TIME-BARRED under Section 73. The entire demand falls.",
                        "severity": "CRITICAL"
                    })
                    valid = False
            except (ValueError, IndexError):
                pass

    elif notice_type_lower in ["74", "section 74", "gst 74", "gst fraud"]:
        # GST Section 74: 5-year limitation (fraud/suppression)
        if financial_year:
            try:
                fy_parts = financial_year.split("-")
                fy_end_year = int(fy_parts[0]) + 1 if len(fy_parts[0]) == 4 else int("20" + fy_parts[1])
                annual_return_due = datetime(fy_end_year, 12, 31)
                limitation_deadline = annual_return_due.replace(year=annual_return_due.year + 5)

                if n_date > limitation_deadline:
                    challenges.append({
                        "ground": f"Section 74 limitation expired for FY {financial_year}",
                        "legal_basis": "Section 74(10) CGST Act — order must be issued within 5 years from due date of annual return",
                        "effect": "Even under the extended fraud/suppression limitation, the demand is TIME-BARRED.",
                        "severity": "CRITICAL"
                    })
                    valid = False

                # Always challenge Section 74 invocation
                challenges.append({
                    "ground": "Challenge invocation of Section 74 (fraud/suppression allegation)",
                    "legal_basis": "Section 74 CGST Act requires the Department to PROVE fraud, wilful misstatement, or suppression of facts. The burden of proof is on the Department.",
                    "effect": "If the Department cannot prove mens rea, the SCN must be converted to Section 73 (which may already be time-barred). This is the FIRST line of defense.",
                    "case_law": "Continental Foundation Jt. Venture v. CCE (2007) 216 ELT 177 (SC) — suppression must be wilful, not inadvertent omission.",
                    "severity": "HIGH — mandatory challenge"
                })
            except (ValueError, IndexError):
                pass

    # === NATURAL JUSTICE CHECK ===
    challenges.append({
        "ground": "Verify adequate opportunity of hearing",
        "legal_basis": "Article 14 Constitution + principles of natural justice (audi alteram partem)",
        "effect": "If personal hearing was not granted or the time given to respond was unreasonably short, the order can be challenged on natural justice grounds.",
        "severity": "MEDIUM — check facts"
    })

    return {
        "notice_type": notice_type,
        "notice_date": notice_date,
        "assessment_year": assessment_year or "not specified",
        "financial_year": financial_year or "not specified",
        "overall_validity": "LIKELY INVALID — challengeable" if not valid else "PRIMA FACIE VALID — check procedural aspects",
        "challenges_found": len([c for c in challenges if c["severity"].startswith("CRITICAL")]),
        "challenge_grounds": challenges,
        "recommended_action": (
            "IMMEDIATE: File a detailed reply challenging the validity of the notice on the grounds identified above. "
            "Do NOT comply with the demand until the validity challenge is resolved. "
            "If limitation has expired, file a writ petition under Article 226 before the jurisdictional High Court."
        ) if not valid else (
            "The notice appears procedurally valid. Focus your defense on the MERITS of the demand. "
            "Verify DIN compliance, personal hearing opportunity, and proper service of notice."
        ),
    }


# =====================================================================
# 4. DEADLINE PENALTY CALCULATOR
# Given a missed deadline, calculate exact penalties
# =====================================================================

def calculate_deadline_penalty(deadline_type: str, due_date: str,
                                actual_date: str = "", tax_amount: float = 0) -> dict:
    """
    Calculate exact penalty for missing a compliance deadline.
    Returns penalty amount, interest, and total exposure.
    """
    try:
        due = datetime.strptime(due_date, "%Y-%m-%d")
        actual = datetime.strptime(actual_date, "%Y-%m-%d") if actual_date else datetime.now()
    except ValueError:
        return {"error": "Dates must be YYYY-MM-DD format"}

    days_late = max((actual - due).days, 0)
    if days_late == 0:
        return {"penalty": 0, "interest": 0, "total": 0, "status": "ON TIME", "message": "Filed on or before due date."}

    months_late = max(days_late // 30, 1)

    dl = deadline_type.lower().strip()

    result = {
        "deadline_type": deadline_type,
        "due_date": due_date,
        "actual_date": actual_date or datetime.now().strftime("%Y-%m-%d"),
        "days_late": days_late,
    }

    if dl in ["gstr-1", "gstr1"]:
        late_fee = min(days_late * 50, 10000)  # Rs 25 CGST + Rs 25 SGST per day, max Rs 5000+5000
        if tax_amount == 0:  # Nil return
            late_fee = min(days_late * 20, 1000)  # Rs 10+10 per day for nil
        result.update({
            "penalty_type": "Late fee under Section 47 CGST Act",
            "late_fee": late_fee,
            "interest": 0,
            "total_exposure": late_fee,
            "legal_basis": "Section 47(1) CGST Act — Rs 25 per day each under CGST and SGST (Rs 10 each for nil returns), capped at Rs 5,000 each.",
        })

    elif dl in ["gstr-3b", "gstr3b"]:
        late_fee = min(days_late * 50, 10000)
        if tax_amount == 0:
            late_fee = min(days_late * 20, 1000)
        interest = tax_amount * 0.18 * days_late / 365 if tax_amount > 0 else 0
        result.update({
            "penalty_type": "Late fee + Interest under CGST Act",
            "late_fee": round(late_fee, 2),
            "interest_rate": "18% p.a. under Section 50(1) CGST Act",
            "interest": round(interest, 2),
            "total_exposure": round(late_fee + interest, 2),
            "legal_basis": "Section 47 (late fee) + Section 50(1) (interest at 18% on net tax liability) CGST Act.",
        })

    elif dl in ["itr", "income tax return", "itr filing"]:
        # Section 234F late fee
        late_fee = 5000
        if tax_amount and tax_amount < 500000:
            late_fee = 1000

        # Section 234A interest (on unpaid tax)
        interest_234a = tax_amount * 0.01 * months_late if tax_amount > 0 else 0

        result.update({
            "penalty_type": "Late filing fee + Interest",
            "late_fee_234f": late_fee,
            "interest_234a": round(interest_234a, 2),
            "total_exposure": round(late_fee + interest_234a, 2),
            "legal_basis": (
                "Section 234F IT Act — Rs 5,000 late fee (Rs 1,000 if total income < Rs 5 lakh). "
                "Section 234A — interest at 1% per month on unpaid tax from due date to filing date."
            ),
        })

    elif dl in ["tds return", "24q", "26q", "27q", "tds"]:
        # Section 234E: Rs 200/day
        late_fee_234e = min(days_late * 200, tax_amount) if tax_amount > 0 else days_late * 200
        # Section 271H: Rs 10,000 to Rs 1,00,000 (if > 1 year late)
        penalty_271h = 0
        if days_late > 365:
            penalty_271h = 10000  # Minimum; max is Rs 1,00,000

        result.update({
            "penalty_type": "TDS Late Filing Penalties",
            "late_fee_234e": round(late_fee_234e, 2),
            "penalty_271h": penalty_271h,
            "total_exposure": round(late_fee_234e + penalty_271h, 2),
            "legal_basis": (
                "Section 234E IT Act — Rs 200 per day until filing (capped at TDS amount). "
                "Section 271H — Rs 10,000 to Rs 1,00,000 penalty if return not filed within 1 year of due date."
            ),
        })

    elif dl in ["tds deposit", "tds payment", "tds challan"]:
        # Section 201(1A): 1.5% per month from deduction date to deposit date
        interest = tax_amount * 0.015 * months_late if tax_amount > 0 else 0
        result.update({
            "penalty_type": "Interest on late TDS deposit",
            "interest_rate": "1.5% per month under Section 201(1A)",
            "interest": round(interest, 2),
            "total_exposure": round(interest, 2),
            "legal_basis": "Section 201(1A) IT Act — interest at 1.5% per month (or part thereof) from date of deduction to date of actual deposit.",
        })

    elif dl in ["gstr-9", "gstr9", "annual return"]:
        late_fee = min(days_late * 200, 5000)  # Rs 100 CGST + Rs 100 SGST, max Rs 5000 per act
        # Cap at 0.04% of turnover (if turnover available)
        result.update({
            "penalty_type": "Late fee for annual return",
            "late_fee": late_fee,
            "total_exposure": late_fee,
            "legal_basis": "Section 47(2) CGST Act — Rs 100 per day each under CGST and SGST, subject to cap of 0.04% of turnover in the state/UT.",
        })

    elif dl in ["roc filing", "annual filing", "mca filing", "aoc-4", "mgt-7"]:
        # Companies Act: Rs 100/day with no upper cap
        additional_fee = days_late * 100
        result.update({
            "penalty_type": "Additional fee for delayed ROC filing",
            "additional_fee": additional_fee,
            "total_exposure": additional_fee,
            "legal_basis": "Companies (Registration Offices and Fees) Rules, 2014 — additional fee of Rs 100 per day of delay. No upper cap. Continued default > 3 years may lead to director disqualification under Section 164(2).",
            "warning": "If delay exceeds 270 days, directors may face disqualification under Section 164(2)(a) of the Companies Act, 2013." if days_late > 270 else None,
        })

    else:
        return {
            "error": f"Unknown deadline type: {deadline_type}",
            "available_types": ["GSTR-1", "GSTR-3B", "GSTR-9", "ITR", "TDS Return", "TDS Deposit", "ROC Filing"],
        }

    result["status"] = "OVERDUE"
    return result


# =====================================================================
# 5. TALLY LEDGER IMPORTER
# Parse Tally XML exports and extract structured financial data
# =====================================================================

def parse_tally_xml(xml_content: str) -> dict:
    """
    Parse Tally Prime/ERP 9 XML export and extract structured ledger data.
    Supports: Day Book, Ledger Vouchers, Trial Balance XML exports.
    """
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        return {"error": f"Invalid XML: {str(e)}"}

    ledgers = []
    vouchers = []

    # Parse TALLYMESSAGE > VOUCHER structure (Day Book export)
    for voucher_elem in root.iter("VOUCHER"):
        v = {
            "date": voucher_elem.get("DATE", voucher_elem.findtext("DATE", "")),
            "voucher_type": voucher_elem.findtext("VOUCHERTYPENAME", ""),
            "voucher_number": voucher_elem.findtext("VOUCHERNUMBER", ""),
            "narration": voucher_elem.findtext("NARRATION", ""),
            "entries": [],
        }

        for ledger_entry in voucher_elem.iter("ALLLEDGERENTRIES"):
            entry = {
                "ledger_name": ledger_entry.findtext("LEDGERNAME", ""),
                "amount": float(ledger_entry.findtext("AMOUNT", "0").replace(",", "") or 0),
                "is_debit": False,
            }
            entry["is_debit"] = entry["amount"] < 0  # Tally uses negative for debits
            entry["amount"] = abs(entry["amount"])
            v["entries"].append(entry)

        # Also check LEDGERENTRIES (alternate structure)
        for ledger_entry in voucher_elem.iter("LEDGERENTRIES.LIST"):
            entry = {
                "ledger_name": ledger_entry.findtext("LEDGERNAME", ""),
                "amount": float(ledger_entry.findtext("AMOUNT", "0").replace(",", "") or 0),
                "is_debit": False,
            }
            entry["is_debit"] = entry["amount"] < 0
            entry["amount"] = abs(entry["amount"])
            v["entries"].append(entry)

        if v["entries"]:
            vouchers.append(v)

    # Parse LEDGER master data
    for ledger_elem in root.iter("LEDGER"):
        l = {
            "name": ledger_elem.get("NAME", ledger_elem.findtext("NAME", "")),
            "parent_group": ledger_elem.findtext("PARENT", ""),
            "opening_balance": float(ledger_elem.findtext("OPENINGBALANCE", "0").replace(",", "") or 0),
            "closing_balance": float(ledger_elem.findtext("CLOSINGBALANCE", "0").replace(",", "") or 0),
            "gstin": ledger_elem.findtext("GSTREGISTRATIONNUMBER", ledger_elem.findtext("PARTYGSTIN", "")),
        }
        ledgers.append(l)

    # Extract summary statistics
    total_debit = sum(e["amount"] for v in vouchers for e in v["entries"] if e["is_debit"])
    total_credit = sum(e["amount"] for v in vouchers for e in v["entries"] if not e["is_debit"])

    # Auto-detect cash payments > Rs 10,000 (Section 40A(3) violation)
    cash_violations = []
    for v in vouchers:
        if v["voucher_type"].lower() in ["payment", "cash payment"]:
            for e in v["entries"]:
                if e["amount"] > 10000 and "cash" in e["ledger_name"].lower():
                    cash_violations.append({
                        "date": v["date"],
                        "amount": e["amount"],
                        "ledger": e["ledger_name"],
                        "narration": v["narration"],
                        "violation": "Section 40A(3) IT Act — cash payment > Rs 10,000 in a single day to a single person. Expenditure will be disallowed.",
                    })

    # Auto-detect cash receipts > Rs 2 lakh (Section 269ST violation)
    cash_receipt_violations = []
    for v in vouchers:
        if v["voucher_type"].lower() in ["receipt", "cash receipt"]:
            for e in v["entries"]:
                if e["amount"] > 200000 and "cash" in e["ledger_name"].lower():
                    cash_receipt_violations.append({
                        "date": v["date"],
                        "amount": e["amount"],
                        "ledger": e["ledger_name"],
                        "violation": "Section 269ST IT Act — cash receipt > Rs 2 lakh. Penalty under Section 271DA equal to the amount received.",
                    })

    return {
        "parsed_vouchers": len(vouchers),
        "parsed_ledgers": len(ledgers),
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "vouchers": vouchers[:500],  # Cap for memory safety
        "ledgers": ledgers[:200],
        "auto_detected_violations": {
            "section_40a3_cash_payments": cash_violations,
            "section_269st_cash_receipts": cash_receipt_violations,
        },
        "violation_count": len(cash_violations) + len(cash_receipt_violations),
        "summary": (
            f"Parsed {len(vouchers)} vouchers and {len(ledgers)} ledgers. "
            f"Total debits: Rs {total_debit:,.0f}, Total credits: Rs {total_credit:,.0f}. "
            f"Auto-detected {len(cash_violations)} Section 40A(3) violations and "
            f"{len(cash_receipt_violations)} Section 269ST violations."
        ),
    }


# =====================================================================
# 6. ZOHO BOOKS IMPORTER
# Parse Zoho Books CSV/XLSX exports and extract structured financial data
# =====================================================================

def parse_zoho_export(file_bytes: bytes, filename: str) -> dict:
    """
    Parse Zoho Books CSV/XLSX export and extract structured ledger data.
    Supports: Journal Report, General Ledger, Day Book, Trial Balance,
    Purchase Register, Sales Register exports from Zoho Books.
    Auto-detects S.40A(3) and S.269ST violations same as Tally.
    """
    import pandas as pd
    import io

    try:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8", on_bad_lines="skip")
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            return {"error": f"Unsupported file type: .{ext}. Upload a CSV or XLSX export from Zoho Books."}
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}

    if df.empty:
        return {"error": "File is empty or could not be parsed."}

    cols_lower = {c: c.lower().strip() for c in df.columns}
    df.rename(columns={c: cols_lower[c] for c in df.columns}, inplace=True)

    # --- Auto-detect Zoho column names ---
    DATE_COLS = ["date", "transaction date", "journal date", "invoice date", "created date"]
    TYPE_COLS = ["transaction type", "type", "voucher type", "entry type"]
    PARTY_COLS = ["contact name", "vendor name", "customer name", "party name", "name", "account name"]
    AMOUNT_COLS = ["amount", "total", "grand total", "debit", "net amount", "invoice amount"]
    DEBIT_COLS = ["debit", "debit amount", "dr"]
    CREDIT_COLS = ["credit", "credit amount", "cr"]
    REF_COLS = ["reference number", "reference#", "journal number", "invoice number", "invoice#", "bill number", "bill#"]
    NARRATION_COLS = ["notes", "description", "narration", "memo", "remarks"]
    GSTIN_COLS = ["gstin", "gst number", "gstin/uin", "gst identification number"]
    PAYMENT_MODE_COLS = ["payment mode", "payment method", "mode of payment"]

    def _find(candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    date_col = _find(DATE_COLS)
    type_col = _find(TYPE_COLS)
    party_col = _find(PARTY_COLS)
    amount_col = _find(AMOUNT_COLS)
    debit_col = _find(DEBIT_COLS)
    credit_col = _find(CREDIT_COLS)
    ref_col = _find(REF_COLS)
    narration_col = _find(NARRATION_COLS)
    gstin_col = _find(GSTIN_COLS)
    payment_mode_col = _find(PAYMENT_MODE_COLS)

    # Build transactions
    transactions = []
    total_debit = 0.0
    total_credit = 0.0

    for _, row in df.iterrows():
        txn = {}
        txn["date"] = str(row.get(date_col, "")) if date_col else ""
        txn["voucher_type"] = str(row.get(type_col, "")) if type_col else ""
        txn["party"] = str(row.get(party_col, "")) if party_col else ""
        txn["reference"] = str(row.get(ref_col, "")) if ref_col else ""
        txn["narration"] = str(row.get(narration_col, "")) if narration_col else ""
        txn["gstin"] = str(row.get(gstin_col, "")) if gstin_col else ""
        txn["payment_mode"] = str(row.get(payment_mode_col, "")) if payment_mode_col else ""

        # Amount handling: prefer debit/credit columns, fallback to amount
        if debit_col and credit_col:
            dr = _safe_float(row.get(debit_col, 0))
            cr = _safe_float(row.get(credit_col, 0))
            txn["amount"] = dr if dr > 0 else cr
            txn["is_debit"] = dr > 0
            total_debit += dr
            total_credit += cr
        elif amount_col:
            amt = _safe_float(row.get(amount_col, 0))
            txn["amount"] = abs(amt)
            txn["is_debit"] = amt < 0
            if amt < 0:
                total_debit += abs(amt)
            else:
                total_credit += amt
        else:
            txn["amount"] = 0
            txn["is_debit"] = False

        if txn["amount"] > 0 or txn["party"]:
            transactions.append(txn)

    # Auto-detect S.40A(3) cash payment violations (>Rs 10,000)
    cash_violations = []
    for t in transactions:
        is_cash = (
            "cash" in t.get("payment_mode", "").lower()
            or "cash" in t.get("party", "").lower()
            or "cash" in t.get("voucher_type", "").lower()
        )
        is_payment = t.get("is_debit", False) or "payment" in t.get("voucher_type", "").lower()
        if is_cash and is_payment and t["amount"] > 10000:
            cash_violations.append({
                "date": t["date"],
                "amount": t["amount"],
                "party": t["party"],
                "section": "S.40A(3)",
                "violation": "Section 40A(3) IT Act — cash payment > Rs 10,000. Expenditure will be disallowed.",
            })

    # Auto-detect S.269ST cash receipt violations (>Rs 2 lakh)
    cash_receipt_violations = []
    for t in transactions:
        is_cash = (
            "cash" in t.get("payment_mode", "").lower()
            or "cash" in t.get("party", "").lower()
        )
        is_receipt = not t.get("is_debit", False) or "receipt" in t.get("voucher_type", "").lower()
        if is_cash and is_receipt and t["amount"] > 200000:
            cash_receipt_violations.append({
                "date": t["date"],
                "amount": t["amount"],
                "party": t["party"],
                "section": "S.269ST",
                "violation": "Section 269ST IT Act — cash receipt > Rs 2 lakh. Penalty u/s 271DA equal to the amount.",
            })

    # Build violation_details for frontend (unified format with Tally)
    violation_details = []
    for v in cash_violations:
        violation_details.append(v)
    for v in cash_receipt_violations:
        violation_details.append(v)

    return {
        "source": "zoho_books",
        "total_vouchers": len(transactions),
        "total_amount": round(total_debit + total_credit, 2),
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "violations_40a3": len(cash_violations),
        "violations_269st": len(cash_receipt_violations),
        "violation_details": violation_details,
        "transactions": [
            {"date": t["date"], "voucher_type": t["voucher_type"], "party": t["party"], "amount": t["amount"]}
            for t in transactions[:500]
        ],
        "columns_detected": {
            "date": date_col, "type": type_col, "party": party_col,
            "amount": amount_col, "debit": debit_col, "credit": credit_col,
            "gstin": gstin_col, "payment_mode": payment_mode_col,
        },
        "summary": (
            f"Parsed {len(transactions)} transactions from Zoho Books export. "
            f"Total debits: Rs {total_debit:,.0f}, Total credits: Rs {total_credit:,.0f}. "
            f"Auto-detected {len(cash_violations)} Section 40A(3) violations and "
            f"{len(cash_receipt_violations)} Section 269ST violations."
        ),
    }


def _safe_float(val) -> float:
    """Safely convert a value to float, handling Indian number formats."""
    if val is None or (isinstance(val, float) and str(val) == 'nan'):
        return 0.0
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0
