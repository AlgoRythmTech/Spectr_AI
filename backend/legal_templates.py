"""
Legal Document Template Library for Indian Lawyers and CAs.
Provides 52 production-ready templates with proper Indian legal formatting,
statutory references, and bilingual conventions.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Template Categories
# ---------------------------------------------------------------------------
CATEGORIES = {
    "criminal": "Criminal Law",
    "civil": "Civil Law",
    "corporate": "Corporate Law",
    "contractual": "Contractual & Arbitration",
    "tax_gst": "Tax & GST",
    "property_family": "Property & Family",
    "consumer_misc": "Consumer & Miscellaneous",
}

# ---------------------------------------------------------------------------
# Template Registry  --  template_id -> metadata
# ---------------------------------------------------------------------------
TEMPLATE_REGISTRY: dict[str, dict] = {}


def _register(
    template_id: str,
    title: str,
    category: str,
    description: str,
    required_fields: list[str],
    optional_fields: list[str] | None = None,
    output_format: str = "text",
):
    """Register a template in the global registry."""
    TEMPLATE_REGISTRY[template_id] = {
        "template_id": template_id,
        "title": title,
        "category": category,
        "description": description,
        "required_fields": required_fields,
        "optional_fields": optional_fields or [],
        "output_format": output_format,
    }


# ===================================================================
# 1. CRIMINAL LAW TEMPLATES  (8)
# ===================================================================

# 1.1 Anticipatory Bail Application u/s 438 CrPC / 482 BNSS
_register(
    "bail_anticipatory",
    "Anticipatory Bail Application u/s 438 CrPC / 482 BNSS",
    "criminal",
    "Application for anticipatory bail with grounds, FIR details, and prayer clause.",
    required_fields=[
        "court_name", "case_number", "applicant_name", "applicant_father_name",
        "applicant_address", "applicant_age", "respondent_state",
        "fir_number", "fir_date", "police_station", "fir_sections",
        "brief_facts", "grounds", "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["co_accused", "investigating_officer", "district"],
)

TEMPLATE_BAIL_ANTICIPATORY = """
IN THE {court_name}

Criminal Miscellaneous Application No. {case_number}
(Under Section 438 of the Code of Criminal Procedure, 1973 /
Section 482 of the Bharatiya Nagarik Suraksha Sanhita, 2023)

IN THE MATTER OF:

{applicant_name}
S/o / D/o / W/o {applicant_father_name}
Aged about {applicant_age} years,
R/o {applicant_address}
                                                    ... APPLICANT

                        VERSUS

{respondent_state}
Through the Station House Officer,
P.S. {police_station}
                                                    ... RESPONDENT

APPLICATION FOR ANTICIPATORY BAIL

MOST RESPECTFULLY SHOWETH:

1. That the present application is being filed under Section 438 of the Code
   of Criminal Procedure, 1973 (corresponding to Section 482 of the Bharatiya
   Nagarik Suraksha Sanhita, 2023) for grant of anticipatory bail to the
   applicant in FIR No. {fir_number} dated {fir_date}, registered at Police
   Station {police_station} under Sections {fir_sections}.

2. BRIEF FACTS OF THE CASE:

{brief_facts}

3. GROUNDS FOR ANTICIPATORY BAIL:

{grounds}

4. That the applicant is a law-abiding citizen with deep roots in society
   and there is no likelihood of the applicant fleeing from justice or
   tampering with evidence.

5. That the applicant undertakes to cooperate with the investigation and
   shall make himself/herself available for interrogation as and when
   required by the Investigating Officer.

6. That the applicant has no previous criminal antecedents.

PRAYER:

In the light of the facts and circumstances stated above, it is most
respectfully prayed that this Hon'ble Court may graciously be pleased to:

(a) Grant anticipatory bail to the applicant in the event of his/her
    arrest in connection with FIR No. {fir_number} dated {fir_date}
    registered at P.S. {police_station};

(b) Pass any other order(s) as this Hon'ble Court may deem fit and proper
    in the interests of justice.

AND FOR THIS ACT OF KINDNESS, THE APPLICANT SHALL EVER PRAY.

Place: _______________
Date:  _______________

                                        (Signature of Applicant)
                                        {applicant_name}

THROUGH COUNSEL:

{advocate_name}
Advocate
Enrollment No. {advocate_enrollment}
"""

# 1.2 Regular Bail Application u/s 437 CrPC / 480 BNSS
_register(
    "bail_regular",
    "Regular Bail Application u/s 437 CrPC / 480 BNSS",
    "criminal",
    "Application for regular bail for accused in judicial custody.",
    required_fields=[
        "court_name", "case_number", "applicant_name", "applicant_father_name",
        "applicant_address", "applicant_age", "respondent_state",
        "fir_number", "fir_date", "police_station", "fir_sections",
        "date_of_arrest", "brief_facts", "grounds",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["jail_name", "co_accused_bail_status", "surety_details"],
)

TEMPLATE_BAIL_REGULAR = """
IN THE COURT OF {court_name}

Criminal Miscellaneous Application No. {case_number}
(Under Section 437 of the Code of Criminal Procedure, 1973 /
Section 480 of the Bharatiya Nagarik Suraksha Sanhita, 2023)

IN THE MATTER OF:

{applicant_name}
S/o / D/o / W/o {applicant_father_name}
Aged about {applicant_age} years,
R/o {applicant_address}
(Presently lodged in Judicial Custody)
                                                    ... APPLICANT / ACCUSED

                        VERSUS

{respondent_state}
Through SHO, P.S. {police_station}
                                                    ... RESPONDENT / STATE

APPLICATION FOR REGULAR BAIL

MOST RESPECTFULLY SHOWETH:

1. That the applicant/accused is in judicial custody since {date_of_arrest}
   in connection with FIR No. {fir_number} dated {fir_date} registered at
   P.S. {police_station} under Sections {fir_sections}.

2. BRIEF FACTS:

{brief_facts}

3. GROUNDS FOR BAIL:

{grounds}

4. That the investigation qua the applicant is complete and no further
   custodial interrogation is required. Continued incarceration of the
   applicant would serve no useful purpose.

5. That the applicant is ready and willing to furnish bail bonds / surety
   to the satisfaction of this Hon'ble Court and shall abide by such
   conditions as may be imposed.

6. That the applicant shall not tamper with evidence, influence witnesses,
   or leave the jurisdiction of this Hon'ble Court without prior permission.

PRAYER:

It is, therefore, most respectfully prayed that this Hon'ble Court may
graciously be pleased to:

(a) Release the applicant on regular bail in the aforesaid FIR/case on
    such terms and conditions as this Hon'ble Court deems fit;

(b) Pass any other order as this Hon'ble Court may deem just and proper.

AND FOR THIS ACT OF KINDNESS, THE APPLICANT SHALL EVER PRAY.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 1.3 Default Bail Application u/s 167(2) CrPC / 187 BNSS
_register(
    "bail_default",
    "Default Bail Application u/s 167(2) CrPC / 187 BNSS",
    "criminal",
    "Application for default bail when chargesheet not filed within statutory period.",
    required_fields=[
        "court_name", "case_number", "applicant_name", "applicant_father_name",
        "applicant_address", "applicant_age", "respondent_state",
        "fir_number", "fir_date", "police_station", "fir_sections",
        "date_of_arrest", "statutory_period", "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["remand_dates", "chargesheet_status"],
)

TEMPLATE_BAIL_DEFAULT = """
IN THE COURT OF {court_name}

Criminal Miscellaneous Application No. {case_number}
(Under Section 167(2) of the Code of Criminal Procedure, 1973 /
Section 187 of the Bharatiya Nagarik Suraksha Sanhita, 2023)

IN THE MATTER OF:

{applicant_name}
S/o / D/o / W/o {applicant_father_name}
Aged about {applicant_age} years,
R/o {applicant_address}
                                                    ... APPLICANT / ACCUSED

                        VERSUS

{respondent_state}
Through SHO, P.S. {police_station}
                                                    ... RESPONDENT / STATE

APPLICATION FOR DEFAULT BAIL

MOST RESPECTFULLY SHOWETH:

1. That the applicant/accused has been in judicial custody since
   {date_of_arrest} in connection with FIR No. {fir_number} dated
   {fir_date} registered at P.S. {police_station} under Sections
   {fir_sections}.

2. That as per the provisions of Section 167(2) of the Code of Criminal
   Procedure, 1973 (corresponding to Section 187 of the BNSS, 2023), the
   Investigating Agency is mandated to complete the investigation and file
   the chargesheet/police report within {statutory_period} days from the
   date of arrest of the accused.

3. That the statutory period of {statutory_period} days has expired on
   __________ and no chargesheet/police report has been filed before this
   Hon'ble Court as on the date of filing of this application.

4. That the right to default bail under Section 167(2) CrPC is an
   indefeasible right of the accused as held by the Hon'ble Supreme Court
   in Sayed Mohamed Ahmed Kazmi v. State (GNCTD), (2012) 12 SCC 1, and
   Rakesh Kumar Paul v. State of Assam, (2017) 15 SCC 67.

5. That the applicant is entitled to be released on bail as a matter of
   right, the statutory period having expired without the filing of a
   chargesheet.

PRAYER:

It is most respectfully prayed that this Hon'ble Court may graciously be
pleased to:

(a) Release the applicant on default bail under Section 167(2) CrPC /
    Section 187 BNSS in the aforesaid case on such terms and conditions
    as this Hon'ble Court may deem fit;

(b) Pass any other order as this Hon'ble Court may deem just and proper.

AND FOR THIS ACT OF KINDNESS, THE APPLICANT SHALL EVER PRAY.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 1.4 Quashing Petition u/s 482 CrPC
_register(
    "quashing_petition",
    "Quashing Petition u/s 482 CrPC / 528 BNSS",
    "criminal",
    "Petition for quashing FIR or criminal proceedings before High Court.",
    required_fields=[
        "high_court_name", "case_number", "petitioner_name", "petitioner_address",
        "respondent_state", "fir_number", "fir_date", "police_station",
        "fir_sections", "brief_facts", "grounds_for_quashing",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["lower_court_case_number", "impugned_order_date"],
)

TEMPLATE_QUASHING_PETITION = """
IN THE HON'BLE HIGH COURT OF {high_court_name}

Criminal Miscellaneous Petition No. {case_number}
(Under Section 482 of the Code of Criminal Procedure, 1973 /
Section 528 of the Bharatiya Nagarik Suraksha Sanhita, 2023)

IN THE MATTER OF:

{petitioner_name}
R/o {petitioner_address}
                                                    ... PETITIONER

                        VERSUS

{respondent_state}
                                                    ... RESPONDENT

PETITION FOR QUASHING OF FIR / CRIMINAL PROCEEDINGS

TO,
THE HON'BLE CHIEF JUSTICE AND HIS COMPANION JUDGES OF THE
HON'BLE HIGH COURT OF {high_court_name}.

THE HUMBLE PETITION OF THE PETITIONER ABOVE NAMED:

MOST RESPECTFULLY SHOWETH:

1. That the present petition is being preferred under Section 482 of the
   Code of Criminal Procedure, 1973, for quashing of FIR No. {fir_number}
   dated {fir_date} registered at P.S. {police_station} under Sections
   {fir_sections} and/or any consequent proceedings arising therefrom.

2. BRIEF FACTS:

{brief_facts}

3. GROUNDS FOR QUASHING:

{grounds_for_quashing}

4. That the continuation of the criminal proceedings against the
   petitioner would amount to an abuse of the process of law and would
   result in gross injustice to the petitioner. The ingredients of the
   alleged offence are not made out from the allegations in the FIR even
   if taken at face value (ref: State of Haryana v. Bhajan Lal, 1992
   Supp (1) SCC 335).

5. That no useful purpose would be served by continuing with the
   proceedings and the same deserve to be quashed in the exercise of
   inherent jurisdiction of this Hon'ble Court.

PRAYER:

It is most respectfully prayed that this Hon'ble Court may graciously be
pleased to:

(a) Quash FIR No. {fir_number} dated {fir_date} registered at P.S.
    {police_station} and all consequent proceedings;

(b) Stay the investigation / arrest of the petitioner during the
    pendency of this petition;

(c) Pass any other order as this Hon'ble Court may deem fit and proper.

AND FOR THIS ACT OF KINDNESS, THE PETITIONER SHALL EVER PRAY.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 1.5 Private Criminal Complaint u/s 200 CrPC
_register(
    "criminal_complaint",
    "Private Criminal Complaint u/s 200 CrPC / 223 BNSS",
    "criminal",
    "Private complaint to Magistrate for cognizable/non-cognizable offence.",
    required_fields=[
        "court_name", "complainant_name", "complainant_father_name",
        "complainant_address", "complainant_age",
        "accused_name", "accused_address", "offence_sections",
        "facts_of_complaint", "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["witnesses", "documents_list"],
)

TEMPLATE_CRIMINAL_COMPLAINT = """
IN THE COURT OF {court_name}

Complaint Case No. __________
(Under Section 200 of the Code of Criminal Procedure, 1973 /
Section 223 of the Bharatiya Nagarik Suraksha Sanhita, 2023)

{complainant_name}
S/o / D/o / W/o {complainant_father_name}
Aged about {complainant_age} years,
R/o {complainant_address}
                                                    ... COMPLAINANT

                        VERSUS

{accused_name}
R/o {accused_address}
                                                    ... ACCUSED

COMPLAINT UNDER SECTION 200 CrPC

MOST RESPECTFULLY SHOWETH:

1. That the complainant is a law-abiding citizen residing at the address
   mentioned above. The accused is known to the complainant and is
   residing at the address mentioned hereinabove.

2. FACTS OF THE COMPLAINT:

{facts_of_complaint}

3. That the acts of the accused constitute offences punishable under
   Sections {offence_sections} and the complainant is constrained to file
   the present complaint before this Hon'ble Court.

4. That the complainant has not filed any other complaint in respect of
   the same cause of action before any other court of competent
   jurisdiction.

5. That the cause of action for filing the present complaint arose on
   __________ at __________ within the territorial jurisdiction of this
   Hon'ble Court.

PRAYER:

It is most respectfully prayed that this Hon'ble Court may graciously be
pleased to:

(a) Take cognizance of the offence(s) under Sections {offence_sections};

(b) Summon the accused and try him/her for the said offence(s);

(c) Punish the accused in accordance with law;

(d) Pass any other order as this Hon'ble Court may deem fit and proper.

AND FOR THIS ACT OF KINDNESS, THE COMPLAINANT SHALL EVER PRAY.

VERIFICATION:

I, {complainant_name}, the complainant above named, do hereby verify that
the contents of the above complaint are true and correct to the best of my
knowledge and belief and nothing material has been concealed therefrom.

Verified at __________ on this __________ day of __________, 20__.

                                        (Signature of Complainant)
                                        {complainant_name}

THROUGH COUNSEL:
{advocate_name}
Advocate
Enrollment No. {advocate_enrollment}
"""

# 1.6 Criminal Revision Petition
_register(
    "criminal_revision",
    "Criminal Revision Petition u/s 397 CrPC / 442 BNSS",
    "criminal",
    "Revision petition against order of lower criminal court.",
    required_fields=[
        "court_name", "case_number", "petitioner_name", "petitioner_address",
        "respondent_name", "respondent_address",
        "lower_court_name", "lower_court_case_number", "impugned_order_date",
        "brief_facts", "grounds_for_revision",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["original_fir_number"],
)

TEMPLATE_CRIMINAL_REVISION = """
IN THE COURT OF {court_name}

Criminal Revision Petition No. {case_number}
(Under Section 397 read with Section 401 of the Code of Criminal
Procedure, 1973 / Section 442 of the BNSS, 2023)

{petitioner_name}
R/o {petitioner_address}
                                                    ... PETITIONER / REVISIONIST

                        VERSUS

{respondent_name}
R/o {respondent_address}
                                                    ... RESPONDENT

CRIMINAL REVISION PETITION

MOST RESPECTFULLY SHOWETH:

1. That the petitioner/revisionist is aggrieved by the order dated
   {impugned_order_date} passed by the Ld. {lower_court_name} in
   Case No. {lower_court_case_number} and is filing the present revision
   petition under Section 397 r/w 401 CrPC.

2. BRIEF FACTS:

{brief_facts}

3. GROUNDS FOR REVISION:

{grounds_for_revision}

4. That the impugned order is patently illegal, perverse, and contrary
   to law and settled judicial precedents. The Ld. Court below has
   exercised its jurisdiction with material irregularity.

PRAYER:

It is most respectfully prayed that this Hon'ble Court may graciously be
pleased to:

(a) Set aside the impugned order dated {impugned_order_date} passed by
    the Ld. {lower_court_name} in Case No. {lower_court_case_number};

(b) Stay the operation of the impugned order during the pendency of
    this revision petition;

(c) Pass any other order as this Hon'ble Court may deem fit and proper.

AND FOR THIS ACT OF KINDNESS, THE PETITIONER SHALL EVER PRAY.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 1.7 Parole / Furlough Application
_register(
    "parole_application",
    "Application for Parole / Furlough",
    "criminal",
    "Application for temporary release on parole or furlough.",
    required_fields=[
        "court_name", "applicant_name", "applicant_father_name",
        "applicant_address", "conviction_details", "sentence_details",
        "jail_name", "date_of_conviction",
        "grounds_for_parole", "parole_period_requested",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["previous_parole_details", "surety_name"],
)

TEMPLATE_PAROLE_APPLICATION = """
IN THE COURT OF {court_name}

Criminal Miscellaneous Application No. __________
(Application for Parole / Furlough)

IN THE MATTER OF:

{applicant_name}
S/o {applicant_father_name}
R/o {applicant_address}
(Presently confined in {jail_name})
                                                    ... APPLICANT / CONVICT

APPLICATION FOR PAROLE / FURLOUGH

MOST RESPECTFULLY SHOWETH:

1. That the applicant has been convicted in {conviction_details} and is
   presently serving a sentence of {sentence_details} since
   {date_of_conviction} and is lodged in {jail_name}.

2. GROUNDS FOR PAROLE:

{grounds_for_parole}

3. That the applicant seeks parole/furlough for a period of
   {parole_period_requested} days.

4. That the applicant undertakes to surrender before the jail authorities
   upon the expiry of the parole/furlough period and shall not indulge in
   any criminal activity during the period of parole/furlough.

5. That the applicant is ready and willing to furnish surety and comply
   with such conditions as this Hon'ble Court may impose.

PRAYER:

It is most respectfully prayed that this Hon'ble Court may graciously be
pleased to grant parole/furlough to the applicant for a period of
{parole_period_requested} days on such terms and conditions as this
Hon'ble Court may deem fit and proper.

AND FOR THIS ACT OF KINDNESS, THE APPLICANT SHALL EVER PRAY.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 1.8 Victim Compensation Application u/s 357A CrPC
_register(
    "victim_compensation",
    "Victim Compensation Application u/s 357A CrPC / 396 BNSS",
    "criminal",
    "Application for victim compensation under the Victim Compensation Scheme.",
    required_fields=[
        "court_name", "applicant_name", "applicant_address",
        "fir_number", "fir_date", "police_station", "offence_sections",
        "nature_of_injury_loss", "compensation_amount_claimed",
        "brief_facts", "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["medical_reports", "accused_status"],
)

TEMPLATE_VICTIM_COMPENSATION = """
IN THE COURT OF {court_name}
(Before the District Legal Services Authority / State Legal Services Authority)

Application No. __________
(Under Section 357A of the Code of Criminal Procedure, 1973 /
Section 396 of the Bharatiya Nagarik Suraksha Sanhita, 2023
read with the Victim Compensation Scheme)

{applicant_name}
R/o {applicant_address}
                                                    ... APPLICANT / VICTIM

APPLICATION FOR VICTIM COMPENSATION

MOST RESPECTFULLY SHOWETH:

1. That the applicant is the victim of an offence registered vide FIR No.
   {fir_number} dated {fir_date} at P.S. {police_station} under Sections
   {offence_sections}.

2. BRIEF FACTS:

{brief_facts}

3. NATURE OF INJURY / LOSS:

{nature_of_injury_loss}

4. That the applicant has suffered physical/mental/financial loss and is
   entitled to compensation under the Victim Compensation Scheme as
   notified by the State Government under Section 357A CrPC.

5. That the applicant claims compensation of Rs. {compensation_amount_claimed}/-.

PRAYER:

It is most respectfully prayed that the Hon'ble Authority may graciously
be pleased to grant compensation of Rs. {compensation_amount_claimed}/-
to the applicant under the Victim Compensation Scheme.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# ===================================================================
# 2. CIVIL LAW TEMPLATES  (8)
# ===================================================================

# 2.1 Money Recovery Suit
_register(
    "civil_suit_money",
    "Money Recovery Suit (Order VII CPC)",
    "civil",
    "Suit for recovery of money / debt with interest.",
    required_fields=[
        "court_name", "suit_number", "plaintiff_name", "plaintiff_address",
        "defendant_name", "defendant_address",
        "amount_claimed", "cause_of_action_facts", "interest_rate",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["court_fee_paid", "documents_relied_upon", "limitation_details"],
)

TEMPLATE_CIVIL_SUIT_MONEY = """
IN THE COURT OF {court_name}

Civil Suit No. {suit_number}

{plaintiff_name}
R/o {plaintiff_address}
                                                    ... PLAINTIFF

                        VERSUS

{defendant_name}
R/o {defendant_address}
                                                    ... DEFENDANT

SUIT FOR RECOVERY OF MONEY

The plaintiff above named most respectfully submits as follows:

1. That the plaintiff is a resident of the address mentioned above and
   files the present suit for recovery of Rs. {amount_claimed}/- against
   the defendant.

2. CAUSE OF ACTION:

{cause_of_action_facts}

3. That the defendant is liable to pay Rs. {amount_claimed}/- along with
   interest at the rate of {interest_rate}% per annum from the date the
   cause of action arose till the date of realisation.

4. VALUATION AND COURT FEES:
   The suit is valued at Rs. {amount_claimed}/- for the purpose of
   jurisdiction and court fees. Requisite court fees have been affixed.

5. JURISDICTION:
   This Hon'ble Court has territorial and pecuniary jurisdiction to try
   and decide the present suit as the cause of action has arisen within
   the jurisdiction of this Court.

6. LIMITATION:
   The suit is within the period of limitation prescribed under the
   Limitation Act, 1963.

7. That the plaintiff has not filed any other suit or proceeding in
   respect of the same cause of action in any Court.

PRAYER:

In the premises aforesaid, it is most respectfully prayed that this
Hon'ble Court may graciously be pleased to:

(a) Pass a decree in favour of the plaintiff and against the defendant
    for recovery of Rs. {amount_claimed}/- along with pendente lite and
    future interest at the rate of {interest_rate}% per annum;

(b) Award costs of the suit to the plaintiff;

(c) Pass any other order or relief as this Hon'ble Court may deem fit.

AND FOR THIS ACT OF KINDNESS, THE PLAINTIFF SHALL EVER PRAY.

VERIFICATION:

I, {plaintiff_name}, the plaintiff above named, do hereby verify that the
contents of the above plaint are true and correct to my knowledge and
belief. No part of it is false and nothing material has been concealed.

Verified at __________ on this __________ day of __________, 20__.

                                        (Signature of Plaintiff)

{advocate_name}
Advocate
Enrollment No. {advocate_enrollment}
"""

# 2.2 Specific Performance Suit
_register(
    "civil_suit_specific_performance",
    "Suit for Specific Performance u/s 10 Specific Relief Act",
    "civil",
    "Suit for specific performance of contract relating to immovable property.",
    required_fields=[
        "court_name", "suit_number", "plaintiff_name", "plaintiff_address",
        "defendant_name", "defendant_address",
        "agreement_date", "property_description", "sale_consideration",
        "amount_paid", "balance_amount", "facts_of_breach",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["possession_date", "earnest_money"],
)

TEMPLATE_CIVIL_SUIT_SPECIFIC_PERFORMANCE = """
IN THE COURT OF {court_name}

Civil Suit No. {suit_number}

{plaintiff_name}
R/o {plaintiff_address}
                                                    ... PLAINTIFF

                        VERSUS

{defendant_name}
R/o {defendant_address}
                                                    ... DEFENDANT

SUIT FOR SPECIFIC PERFORMANCE OF CONTRACT

The plaintiff above named most respectfully submits as follows:

1. That the plaintiff entered into an Agreement to Sell dated
   {agreement_date} with the defendant for purchase of the following
   immovable property:

   SCHEDULE OF PROPERTY:
   {property_description}

2. That the total sale consideration was fixed at Rs. {sale_consideration}/-
   out of which the plaintiff has already paid Rs. {amount_paid}/- to the
   defendant. The balance amount of Rs. {balance_amount}/- was to be paid
   at the time of execution of the Sale Deed.

3. FACTS OF BREACH:

{facts_of_breach}

4. That the plaintiff has always been ready and willing to perform his/her
   part of the contract and is still ready and willing to pay the balance
   consideration of Rs. {balance_amount}/-.

5. That the plaintiff is entitled to specific performance of the contract
   as per Section 10 of the Specific Relief Act, 1963, the property being
   unique and monetary compensation not being an adequate remedy.

PRAYER:

(a) Direct the defendant to execute and register the Sale Deed of the
    scheduled property in favour of the plaintiff upon receipt of the
    balance consideration of Rs. {balance_amount}/-;

(b) In the alternative, pass a decree for refund of Rs. {amount_paid}/-
    with interest at 18% p.a.;

(c) Costs of the suit;

(d) Any other relief as this Hon'ble Court may deem fit.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 2.3 Partition Suit
_register(
    "civil_suit_partition",
    "Partition Suit",
    "civil",
    "Suit for partition and separate possession of joint property.",
    required_fields=[
        "court_name", "suit_number", "plaintiff_name", "plaintiff_address",
        "defendant_names_addresses", "property_description",
        "relationship_details", "share_claimed",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["genealogy_table", "property_valuation"],
)

TEMPLATE_CIVIL_SUIT_PARTITION = """
IN THE COURT OF {court_name}

Civil Suit No. {suit_number}

{plaintiff_name}
R/o {plaintiff_address}
                                                    ... PLAINTIFF

                        VERSUS

{defendant_names_addresses}
                                                    ... DEFENDANT(S)

SUIT FOR PARTITION AND SEPARATE POSSESSION

The plaintiff above named most respectfully submits as follows:

1. That the plaintiff and the defendant(s) are related as follows:
   {relationship_details}

2. That the following properties are joint / co-parcenary properties:

   SCHEDULE OF PROPERTIES:
   {property_description}

3. That the plaintiff is entitled to a {share_claimed} share in the
   aforesaid joint properties by virtue of inheritance / co-parcenary
   rights.

4. That the plaintiff has requested the defendant(s) for amicable
   partition, but the defendant(s) have refused to partition the property
   and give the plaintiff his/her lawful share. The plaintiff is
   therefore constrained to file the present suit.

5. JURISDICTION:
   This Court has jurisdiction as the suit properties are situate within
   its territorial jurisdiction.

PRAYER:

(a) Decree partition of the suit properties and allot the plaintiff's
    {share_claimed} share by metes and bounds;

(b) In case partition by metes and bounds is not possible, direct sale
    of the property and distribution of sale proceeds proportionately;

(c) Appoint a Commissioner for effecting partition;

(d) Costs of the suit;

(e) Any other relief as this Hon'ble Court may deem fit.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 2.4 Injunction Suit
_register(
    "civil_suit_injunction",
    "Suit for Temporary & Permanent Injunction",
    "civil",
    "Suit seeking injunction to prevent illegal dispossession or interference.",
    required_fields=[
        "court_name", "suit_number", "plaintiff_name", "plaintiff_address",
        "defendant_name", "defendant_address",
        "property_description", "cause_of_action",
        "acts_to_be_restrained", "irreparable_injury",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["balance_of_convenience", "title_documents"],
)

TEMPLATE_CIVIL_SUIT_INJUNCTION = """
IN THE COURT OF {court_name}

Civil Suit No. {suit_number}

{plaintiff_name}
R/o {plaintiff_address}
                                                    ... PLAINTIFF

                        VERSUS

{defendant_name}
R/o {defendant_address}
                                                    ... DEFENDANT

SUIT FOR PERMANENT AND MANDATORY INJUNCTION

The plaintiff above named most respectfully submits as follows:

1. That the plaintiff is the lawful owner / tenant / possessor of the
   following property:

   SCHEDULE OF PROPERTY:
   {property_description}

2. CAUSE OF ACTION:

{cause_of_action}

3. That the defendant is threatening / attempting to:

{acts_to_be_restrained}

4. That if the defendant is not restrained, the plaintiff will suffer
   irreparable loss and injury:

{irreparable_injury}

5. That the balance of convenience lies in favour of the plaintiff and
   against the defendant. The three-fold test laid down in Dalpat Kumar
   v. Prahlad Singh, (1992) 1 SCC 719, is satisfied.

6. That the plaintiff has a prima facie case, the balance of convenience
   is in his/her favour, and the plaintiff shall suffer irreparable
   injury if the injunction is not granted.

PRAYER:

(a) Grant permanent injunction restraining the defendant, his agents,
    servants, and anyone claiming through him from {acts_to_be_restrained};

(b) Grant ad-interim / temporary injunction in terms of prayer (a) during
    the pendency of the suit;

(c) Costs of the suit;

(d) Any other relief as this Hon'ble Court may deem fit.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 2.5 Civil Appeal
_register(
    "civil_appeal",
    "First Appeal from Original Decree",
    "civil",
    "First appeal against decree of trial court under Section 96 CPC.",
    required_fields=[
        "court_name", "appeal_number", "appellant_name", "appellant_address",
        "respondent_name", "respondent_address",
        "lower_court_name", "lower_court_suit_number", "decree_date",
        "brief_facts", "grounds_of_appeal",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["decree_details", "relief_sought"],
)

TEMPLATE_CIVIL_APPEAL = """
IN THE {court_name}

First Appeal No. {appeal_number}
(Under Section 96 of the Code of Civil Procedure, 1908)

{appellant_name}
R/o {appellant_address}
                                                    ... APPELLANT
                                    (Plaintiff / Defendant in the Court below)

                        VERSUS

{respondent_name}
R/o {respondent_address}
                                                    ... RESPONDENT
                                    (Defendant / Plaintiff in the Court below)

MEMORANDUM OF APPEAL

The appellant above named most respectfully submits:

1. That the Ld. {lower_court_name} passed a decree dated {decree_date}
   in Suit No. {lower_court_suit_number}, a copy of which is annexed
   herewith.

2. BRIEF FACTS:

{brief_facts}

3. GROUNDS OF APPEAL:

{grounds_of_appeal}

4. That the decree passed by the Ld. Court below is contrary to law,
   facts, and evidence on record, and deserves to be set aside.

PRAYER:

(a) Set aside the decree dated {decree_date} passed by the Ld.
    {lower_court_name} in Suit No. {lower_court_suit_number};

(b) Stay the execution of the impugned decree during the pendency of
    this appeal;

(c) Costs;

(d) Any other relief as this Hon'ble Court may deem fit.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 2.6 Execution Petition
_register(
    "execution_petition",
    "Execution of Decree Petition u/s 36 CPC",
    "civil",
    "Petition for execution of decree under Order XXI CPC.",
    required_fields=[
        "court_name", "execution_number", "decree_holder_name", "decree_holder_address",
        "judgment_debtor_name", "judgment_debtor_address",
        "decree_court", "decree_suit_number", "decree_date",
        "decree_amount", "mode_of_execution",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["property_details_for_attachment", "partial_satisfaction"],
)

TEMPLATE_EXECUTION_PETITION = """
IN THE COURT OF {court_name}

Execution Petition No. {execution_number}
(Under Section 36 read with Order XXI of the Code of Civil Procedure, 1908)

{decree_holder_name}
R/o {decree_holder_address}
                                                    ... DECREE HOLDER

                        VERSUS

{judgment_debtor_name}
R/o {judgment_debtor_address}
                                                    ... JUDGMENT DEBTOR

EXECUTION PETITION

MOST RESPECTFULLY SHOWETH:

1. That the decree holder obtained a decree dated {decree_date} from the
   {decree_court} in Suit No. {decree_suit_number} against the judgment
   debtor for Rs. {decree_amount}/-.

2. That the judgment debtor has failed to comply with / satisfy the decree
   despite demand and passage of time.

3. That the decree holder seeks execution of the decree in the following
   mode: {mode_of_execution}

4. That this Court has jurisdiction to execute the decree.

PRAYER:

(a) Execute the decree dated {decree_date} in favour of the decree
    holder;

(b) Issue warrant of attachment / arrest / delivery of possession as the
    case may be;

(c) Costs of execution proceedings;

(d) Any other relief as this Hon'ble Court may deem fit.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 2.7 Interlocutory Application
_register(
    "interlocutory_application",
    "Interlocutory Application for Interim Relief",
    "civil",
    "IA for temporary injunction, stay, or other interim relief.",
    required_fields=[
        "court_name", "ia_number", "main_case_number",
        "applicant_name", "respondent_name",
        "provision_under_which_filed", "interim_relief_sought",
        "grounds", "urgency_reasons",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["main_suit_details"],
)

TEMPLATE_INTERLOCUTORY_APPLICATION = """
IN THE COURT OF {court_name}

I.A. No. {ia_number}
IN
{main_case_number}

{applicant_name}                                    ... APPLICANT
                        VERSUS
{respondent_name}                                   ... RESPONDENT

INTERLOCUTORY APPLICATION
(Under {provision_under_which_filed})

MOST RESPECTFULLY SHOWETH:

1. That the applicant has filed the above suit/petition and the present
   application is being filed for the following interim relief:

   {interim_relief_sought}

2. GROUNDS:

{grounds}

3. URGENCY:

{urgency_reasons}

4. That if the interim relief is not granted, the applicant shall suffer
   irreparable loss and injury and the very purpose of the main
   proceedings shall be frustrated.

PRAYER:

It is most respectfully prayed that this Hon'ble Court may graciously be
pleased to grant the following interim relief:

{interim_relief_sought}

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 2.8 Written Statement / Defence
_register(
    "written_statement",
    "Written Statement / Defence",
    "civil",
    "Written statement filed by defendant in response to plaint.",
    required_fields=[
        "court_name", "suit_number", "plaintiff_name",
        "defendant_name", "defendant_address",
        "preliminary_objections", "parawise_reply",
        "additional_pleas",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["counter_claim_details", "set_off_details"],
)

TEMPLATE_WRITTEN_STATEMENT = """
IN THE COURT OF {court_name}

Civil Suit No. {suit_number}

{plaintiff_name}                                    ... PLAINTIFF

                        VERSUS

{defendant_name}
R/o {defendant_address}
                                                    ... DEFENDANT

WRITTEN STATEMENT ON BEHALF OF THE DEFENDANT

The defendant above named most respectfully submits as follows:

I. PRELIMINARY OBJECTIONS:

{preliminary_objections}

II. PARA-WISE REPLY TO THE PLAINT:

{parawise_reply}

III. ADDITIONAL PLEAS:

{additional_pleas}

IV. That the suit of the plaintiff is frivolous, vexatious, and filed
    with malafide intentions and deserves to be dismissed with exemplary
    costs.

PRAYER:

It is most respectfully prayed that this Hon'ble Court may graciously be
pleased to dismiss the suit of the plaintiff with costs.

VERIFICATION:

I, {defendant_name}, the defendant above named, do hereby verify that the
contents of paras __________ are true to my knowledge and paras __________
are based on information received and believed to be true. No part of the
written statement is false and nothing material has been concealed.

Verified at __________ on this __________ day of __________, 20__.

                                        (Signature of Defendant)
                                        {defendant_name}

{advocate_name}
Advocate
Enrollment No. {advocate_enrollment}
"""

# ===================================================================
# 3. CORPORATE LAW TEMPLATES  (10)
# ===================================================================

# 3.1 Board Resolution (General)
_register(
    "board_resolution_general",
    "Board Resolution (General Format)",
    "corporate",
    "General board resolution with recitals, resolution, and voting record.",
    required_fields=[
        "company_name", "cin", "registered_office",
        "meeting_date", "meeting_time", "meeting_venue",
        "chairman_name", "directors_present", "quorum_statement",
        "resolution_subject", "resolution_text",
    ],
    optional_fields=["directors_absent", "invitees", "company_secretary_name"],
)

TEMPLATE_BOARD_RESOLUTION_GENERAL = """
{company_name}
CIN: {cin}
Registered Office: {registered_office}

CERTIFIED TRUE COPY OF THE RESOLUTION PASSED AT THE MEETING OF THE
BOARD OF DIRECTORS HELD ON {meeting_date}

DATE:    {meeting_date}
TIME:    {meeting_time}
VENUE:   {meeting_venue}

PRESENT:
{directors_present}

IN THE CHAIR:
{chairman_name}, Chairman of the Meeting

QUORUM:
{quorum_statement}

ITEM NO. ___: {resolution_subject}

The Chairman placed before the Board the proposal regarding
{resolution_subject}.

After detailed discussion, the following resolution was passed:

RESOLVED THAT:

{resolution_text}

RESOLVED FURTHER THAT the Board of Directors hereby authorise(s)
__________, Director / Company Secretary, to do all such acts, deeds, and
things as may be necessary, proper, or expedient to give effect to this
resolution.

The resolution was passed unanimously / by majority.

                                        For {company_name}

                                        ________________________
                                        {chairman_name}
                                        Chairman of the Meeting

                                        ________________________
                                        Company Secretary
"""

# 3.2 Board Resolution for Borrowing
_register(
    "board_resolution_borrowing",
    "Board Resolution for Borrowing u/s 179/180 Companies Act",
    "corporate",
    "Board resolution authorising borrowing with Section 179/180 compliance.",
    required_fields=[
        "company_name", "cin", "registered_office",
        "meeting_date", "chairman_name", "directors_present",
        "borrowing_amount", "lender_name", "purpose_of_borrowing",
        "security_offered", "paid_up_capital", "free_reserves",
    ],
    optional_fields=["interest_rate", "tenure", "company_secretary_name"],
)

TEMPLATE_BOARD_RESOLUTION_BORROWING = """
{company_name}
CIN: {cin}
Registered Office: {registered_office}

CERTIFIED TRUE COPY OF THE RESOLUTION PASSED AT THE MEETING OF THE
BOARD OF DIRECTORS HELD ON {meeting_date}

PRESENT: {directors_present}
IN THE CHAIR: {chairman_name}

ITEM: APPROVAL FOR BORROWING UNDER SECTION 179/180 OF THE COMPANIES
      ACT, 2013

The Chairman informed the Board that the Company requires funds amounting
to Rs. {borrowing_amount}/- for the purpose of {purpose_of_borrowing} and
proposed to borrow from {lender_name}.

The Board noted that the aggregate of paid-up share capital and free
reserves of the Company is Rs. {paid_up_capital}/- (paid-up capital) and
Rs. {free_reserves}/- (free reserves).

After detailed deliberations, the following resolution was passed:

RESOLVED THAT pursuant to Section 179(3)(d) and Section 180(1)(c) of the
Companies Act, 2013, and subject to such approvals as may be necessary,
consent of the Board be and is hereby accorded to borrow a sum of
Rs. {borrowing_amount}/- (Rupees __________ only) from {lender_name},
for the purpose of {purpose_of_borrowing}, on such terms and conditions
as the Managing Director / Director(s) may deem fit.

RESOLVED FURTHER THAT the following property/assets be offered as
security for the said borrowing: {security_offered}

RESOLVED FURTHER THAT __________, Director, be and is hereby authorised
to negotiate, finalise, execute, and deliver all loan documents, deeds,
agreements, and writings as may be necessary for the said borrowing.

The resolution was passed unanimously.

                                        For {company_name}

                                        ________________________
                                        {chairman_name}
                                        Chairman
"""

# 3.3 Board Resolution for Related Party Transaction u/s 188
_register(
    "board_resolution_rpt",
    "Board Resolution for Related Party Transaction u/s 188",
    "corporate",
    "Board resolution for related party transaction under Section 188 Companies Act.",
    required_fields=[
        "company_name", "cin", "meeting_date", "chairman_name",
        "directors_present", "related_party_name", "nature_of_relationship",
        "transaction_description", "transaction_value",
        "material_terms", "arms_length_justification",
    ],
    optional_fields=["interested_directors", "audit_committee_approval_date"],
)

TEMPLATE_BOARD_RESOLUTION_RPT = """
{company_name}
CIN: {cin}

CERTIFIED TRUE COPY OF THE RESOLUTION PASSED AT THE MEETING OF THE
BOARD OF DIRECTORS HELD ON {meeting_date}

PRESENT: {directors_present}
IN THE CHAIR: {chairman_name}

ITEM: APPROVAL OF RELATED PARTY TRANSACTION UNDER SECTION 188 OF THE
      COMPANIES ACT, 2013

The Chairman informed the Board about the proposed transaction with
{related_party_name}, who is a related party within the meaning of
Section 2(76) of the Companies Act, 2013, being {nature_of_relationship}.

Transaction Details:
- Nature of Transaction: {transaction_description}
- Value: Rs. {transaction_value}/-
- Material Terms: {material_terms}

The Board noted that the Audit Committee has granted its prior approval
for the said transaction.

RESOLVED THAT pursuant to Section 188 of the Companies Act, 2013, read
with Rule 15 of the Companies (Meetings of Board and its Powers) Rules,
2014, consent of the Board be and is hereby accorded for entering into
the following transaction with {related_party_name}:

Transaction: {transaction_description}
Value: Rs. {transaction_value}/-

The Board is satisfied that the transaction is at arm's length:
{arms_length_justification}

RESOLVED FURTHER THAT the interested Directors have abstained from voting
on this resolution.

                                        For {company_name}

                                        ________________________
                                        {chairman_name}
                                        Chairman
"""

# 3.4 Board Resolution for Director Appointment
_register(
    "board_resolution_director_appointment",
    "Board Resolution for Director Appointment",
    "corporate",
    "Resolution for appointment of additional / independent director.",
    required_fields=[
        "company_name", "cin", "meeting_date", "chairman_name",
        "directors_present", "new_director_name", "new_director_din",
        "new_director_address", "director_category",
        "appointment_date", "term_of_appointment",
    ],
    optional_fields=["remuneration", "committee_memberships"],
)

TEMPLATE_BOARD_RESOLUTION_DIRECTOR_APPOINTMENT = """
{company_name}
CIN: {cin}

CERTIFIED TRUE COPY OF THE RESOLUTION PASSED AT THE MEETING OF THE
BOARD OF DIRECTORS HELD ON {meeting_date}

PRESENT: {directors_present}
IN THE CHAIR: {chairman_name}

ITEM: APPOINTMENT OF {new_director_name} AS {director_category}

The Chairman placed before the Board the proposal for appointment of
{new_director_name} (DIN: {new_director_din}), residing at
{new_director_address}, as {director_category} of the Company.

The Board noted that the Company has received from {new_director_name}:
(i)   Consent in Form DIR-2 under Section 152(5);
(ii)  Declaration of non-disqualification under Section 164;
(iii) Intimation of DIN in Form DIR-8.

RESOLVED THAT pursuant to Sections 149, 152, 160, and other applicable
provisions of the Companies Act, 2013, {new_director_name}
(DIN: {new_director_din}) be and is hereby appointed as {director_category}
of the Company with effect from {appointment_date} for a term of
{term_of_appointment}, subject to the approval of the shareholders at the
ensuing General Meeting.

RESOLVED FURTHER THAT the Board of Directors be and is hereby authorised
to file the necessary e-Forms with the Registrar of Companies.

                                        For {company_name}

                                        ________________________
                                        {chairman_name}
                                        Chairman
"""

# 3.5 AGM Notice
_register(
    "agm_notice",
    "Annual General Meeting Notice",
    "corporate",
    "Notice of AGM with agenda, explanatory statement, and proxy form reference.",
    required_fields=[
        "company_name", "cin", "registered_office",
        "agm_date", "agm_time", "agm_venue",
        "financial_year", "agenda_items",
        "explanatory_statement", "board_order_signatory",
    ],
    optional_fields=["e_voting_details", "book_closure_dates", "cut_off_date"],
)

TEMPLATE_AGM_NOTICE = """
{company_name}
CIN: {cin}
Registered Office: {registered_office}

NOTICE OF THE ANNUAL GENERAL MEETING

NOTICE is hereby given that the ______ Annual General Meeting of the
members of {company_name} will be held on {agm_date} at {agm_time} at
{agm_venue} to transact the following business:

ORDINARY BUSINESS:

1. To receive, consider, and adopt the Audited Financial Statements of
   the Company for the financial year ended {financial_year}, together
   with the Reports of the Board of Directors and Auditors thereon.

2. To appoint a Director in place of __________, who retires by rotation
   and being eligible, offers himself/herself for re-appointment.

3. To appoint Statutory Auditors and fix their remuneration.

SPECIAL BUSINESS:

{agenda_items}

NOTES:

(i)   A member entitled to attend and vote at the AGM is entitled to
      appoint a proxy to attend and vote on his/her behalf. The proxy
      need not be a member of the Company. The proxy form, duly stamped
      and signed, must be deposited at the Registered Office not less
      than 48 hours before the commencement of the meeting.

(ii)  Members are requested to bring their copy of the Annual Report to
      the meeting.

(iii) The Register of Members and Share Transfer Books will remain
      closed from __________ to __________ (both days inclusive).

EXPLANATORY STATEMENT PURSUANT TO SECTION 102 OF THE COMPANIES ACT, 2013:

{explanatory_statement}

                                        By Order of the Board
                                        For {company_name}

                                        {board_order_signatory}
                                        Company Secretary / Director

Place: _______________
Date:  _______________
"""

# 3.6 EGM Notice
_register(
    "egm_notice",
    "Extraordinary General Meeting Notice",
    "corporate",
    "Notice of EGM for urgent business requiring shareholder approval.",
    required_fields=[
        "company_name", "cin", "registered_office",
        "egm_date", "egm_time", "egm_venue",
        "special_business_items", "explanatory_statement",
        "board_order_signatory",
    ],
    optional_fields=["requisition_details"],
)

TEMPLATE_EGM_NOTICE = """
{company_name}
CIN: {cin}
Registered Office: {registered_office}

NOTICE OF EXTRAORDINARY GENERAL MEETING

NOTICE is hereby given that an Extraordinary General Meeting of the
members of {company_name} will be held on {egm_date} at {egm_time} at
{egm_venue} to transact the following special business:

SPECIAL BUSINESS:

{special_business_items}

NOTES:

(i)   A member entitled to attend and vote is entitled to appoint a proxy.
      The proxy form must be deposited at the Registered Office not less
      than 48 hours before the meeting.

(ii)  The Explanatory Statement pursuant to Section 102 of the Companies
      Act, 2013 is annexed hereto.

EXPLANATORY STATEMENT PURSUANT TO SECTION 102:

{explanatory_statement}

None of the Directors or Key Managerial Personnel or their relatives,
except as mentioned in the Explanatory Statement, is concerned or
interested in the resolution(s).

                                        By Order of the Board
                                        For {company_name}

                                        {board_order_signatory}
                                        Company Secretary / Director

Place: _______________
Date:  _______________
"""

# 3.7 Ordinary Resolution
_register(
    "shareholder_resolution_ordinary",
    "Ordinary Resolution Format",
    "corporate",
    "Format for ordinary resolution passed at general meeting (simple majority).",
    required_fields=[
        "company_name", "meeting_type", "meeting_date",
        "resolution_number", "resolution_subject", "resolution_text",
    ],
    optional_fields=["votes_for", "votes_against", "abstentions"],
)

TEMPLATE_SHAREHOLDER_RESOLUTION_ORDINARY = """
{company_name}

ORDINARY RESOLUTION

Passed at the {meeting_type} held on {meeting_date}

Resolution No. {resolution_number}

Subject: {resolution_subject}

RESOLVED THAT {resolution_text}

The resolution was put to vote and was passed as an ORDINARY RESOLUTION
with the requisite simple majority.

                                        For {company_name}

                                        ________________________
                                        Chairman of the Meeting
"""

# 3.8 Special Resolution
_register(
    "shareholder_resolution_special",
    "Special Resolution Format",
    "corporate",
    "Format for special resolution requiring 75% majority.",
    required_fields=[
        "company_name", "meeting_type", "meeting_date",
        "resolution_number", "resolution_subject", "resolution_text",
        "statutory_provision",
    ],
    optional_fields=["votes_for", "votes_against", "e_voting_results"],
)

TEMPLATE_SHAREHOLDER_RESOLUTION_SPECIAL = """
{company_name}

SPECIAL RESOLUTION

Passed at the {meeting_type} held on {meeting_date}

Resolution No. {resolution_number}

Subject: {resolution_subject}

RESOLVED THAT pursuant to {statutory_provision} and subject to such
approvals, permissions, and sanctions as may be necessary:

{resolution_text}

RESOLVED FURTHER THAT the Board of Directors of the Company be and is
hereby authorised to do all such acts, deeds, matters, and things and to
execute all such documents, instruments, and writings as may be required
to give effect to this resolution.

The resolution was put to vote and was passed as a SPECIAL RESOLUTION
with the votes of not less than three times the votes cast against the
resolution.

                                        For {company_name}

                                        ________________________
                                        Chairman of the Meeting
"""

# 3.9 Board Meeting Minutes
_register(
    "minutes_board_meeting",
    "Minutes of Board Meeting",
    "corporate",
    "Minutes template for recording proceedings of board meeting.",
    required_fields=[
        "company_name", "cin", "meeting_number",
        "meeting_date", "meeting_time", "meeting_venue",
        "chairman_name", "directors_present", "directors_absent",
        "quorum_statement", "agenda_and_proceedings",
    ],
    optional_fields=["company_secretary_name", "invitees", "leave_of_absence"],
)

TEMPLATE_MINUTES_BOARD_MEETING = """
{company_name}
CIN: {cin}

MINUTES OF THE {meeting_number} MEETING OF THE BOARD OF DIRECTORS OF
{company_name} HELD ON {meeting_date} AT {meeting_time} AT {meeting_venue}

PRESENT:
{directors_present}

ABSENT WITH LEAVE:
{directors_absent}

IN THE CHAIR:
{chairman_name}

QUORUM:
{quorum_statement}

The Chairman called the meeting to order and welcomed the Directors.

Leave of absence was granted to the Directors who could not attend the
meeting.

The Chairman confirmed that the quorum was present and the meeting was
duly constituted.

The minutes of the previous Board Meeting held on __________ were read
and confirmed.

PROCEEDINGS:

{agenda_and_proceedings}

CLOSURE:

There being no other business, the meeting concluded with a vote of
thanks to the Chair at __________ hours.

                                        ________________________
                                        {chairman_name}
                                        Chairman

Signed and confirmed at the Board Meeting held on __________.
"""

# 3.10 AGM Minutes
_register(
    "minutes_agm",
    "Minutes of Annual General Meeting",
    "corporate",
    "Minutes template for recording proceedings of AGM.",
    required_fields=[
        "company_name", "cin", "agm_number",
        "meeting_date", "meeting_time", "meeting_venue",
        "chairman_name", "members_present_count",
        "quorum_statement", "resolutions_passed",
    ],
    optional_fields=["proxies_count", "scrutineer_name", "e_voting_results"],
)

TEMPLATE_MINUTES_AGM = """
{company_name}
CIN: {cin}

MINUTES OF THE {agm_number} ANNUAL GENERAL MEETING OF THE MEMBERS OF
{company_name} HELD ON {meeting_date} AT {meeting_time} AT {meeting_venue}

PRESENT:
Members present in person: {members_present_count}
(As per the attendance register maintained at the meeting)

IN THE CHAIR:
{chairman_name}, Chairman of the Board

QUORUM:
{quorum_statement}

The Chairman called the meeting to order and welcomed the members.

The Chairman confirmed the presence of quorum and declared the meeting
duly convened and constituted.

The Notice convening the meeting was taken as read with the consent of
the members.

The Chairman gave a brief overview of the Company's performance during
the financial year.

RESOLUTIONS PASSED:

{resolutions_passed}

CLOSURE:

There being no other business, the Chairman thanked the members for
their presence and declared the meeting closed at __________ hours.

                                        ________________________
                                        {chairman_name}
                                        Chairman

Signed and confirmed.
"""

# ===================================================================
# 4. CONTRACTUAL & ARBITRATION TEMPLATES  (8)
# ===================================================================

# 4.1 Arbitration Notice u/s 21
_register(
    "arbitration_notice",
    "Arbitration Notice u/s 21 Arbitration & Conciliation Act",
    "contractual",
    "Notice invoking arbitration clause under the Arbitration Act, 1996.",
    required_fields=[
        "sender_name", "sender_address", "recipient_name", "recipient_address",
        "agreement_date", "arbitration_clause_reference",
        "dispute_description", "relief_claimed",
        "proposed_arbitrator", "advocate_name",
    ],
    optional_fields=["seat_of_arbitration", "governing_law"],
)

TEMPLATE_ARBITRATION_NOTICE = """
ARBITRATION NOTICE
(Under Section 21 of the Arbitration and Conciliation Act, 1996)

Date: _______________

To,
{recipient_name}
{recipient_address}

From:
{sender_name}
{sender_address}

Subject: Notice of Arbitration under Section 21 of the Arbitration and
         Conciliation Act, 1996

Dear Sir/Madam,

Under instructions from my client, {sender_name}, I hereby give notice
that my client invokes the arbitration clause contained in Clause
{arbitration_clause_reference} of the Agreement dated {agreement_date}
entered into between {sender_name} and {recipient_name}.

1. DISPUTE:

{dispute_description}

2. RELIEF CLAIMED:

{relief_claimed}

3. APPOINTMENT OF ARBITRATOR:

   My client proposes the appointment of {proposed_arbitrator} as the
   sole Arbitrator / proposes __________ as its nominee Arbitrator
   and requests you to appoint your nominee Arbitrator within 30 days
   of receipt of this notice, failing which an application under
   Section 11 of the Act shall be filed before the Hon'ble Court.

4. You are called upon to respond to this notice within 30 days of its
   receipt and participate in the arbitration proceedings.

This notice is issued without prejudice to the rights of my client.

{advocate_name}
Advocate for {sender_name}
"""

# 4.2 Petition u/s 34 (Challenge to Arbitral Award)
_register(
    "arbitration_petition_34",
    "Petition u/s 34 Arbitration Act (Challenge to Award)",
    "contractual",
    "Petition to set aside arbitral award under Section 34.",
    required_fields=[
        "court_name", "petition_number", "petitioner_name", "petitioner_address",
        "respondent_name", "respondent_address",
        "award_date", "arbitrator_name", "award_summary",
        "grounds_for_challenge",
        "advocate_name", "advocate_enrollment",
    ],
    optional_fields=["arbitration_agreement_date", "seat_of_arbitration"],
)

TEMPLATE_ARBITRATION_PETITION_34 = """
IN THE {court_name}

Arbitration Petition No. {petition_number}
(Under Section 34 of the Arbitration and Conciliation Act, 1996)

{petitioner_name}
R/o {petitioner_address}
                                                    ... PETITIONER

                        VERSUS

{respondent_name}
R/o {respondent_address}
                                                    ... RESPONDENT

PETITION UNDER SECTION 34 OF THE ARBITRATION AND CONCILIATION ACT, 1996

MOST RESPECTFULLY SHOWETH:

1. That the dispute between the parties was referred to arbitration before
   {arbitrator_name}, who passed an Award dated {award_date}.

2. SUMMARY OF THE AWARD:

{award_summary}

3. That the said Award is liable to be set aside on the following grounds
   under Section 34(2) of the Arbitration Act:

{grounds_for_challenge}

4. That the petitioner received the Award on __________ and the present
   petition is filed within the prescribed limitation period of three
   months (extendable by 30 days) under Section 34(3).

PRAYER:

(a) Set aside the Arbitral Award dated {award_date};

(b) Stay the enforcement of the Award pending disposal of this petition;

(c) Costs;

(d) Any other relief as this Hon'ble Court may deem fit.

Place: _______________
Date:  _______________

                                        {advocate_name}
                                        Advocate
                                        Enrollment No. {advocate_enrollment}
"""

# 4.3 General Legal Notice
_register(
    "legal_notice_general",
    "General Legal Notice (15/30 days)",
    "contractual",
    "General purpose legal notice for breach of contract, demand, etc.",
    required_fields=[
        "sender_name", "sender_address", "recipient_name", "recipient_address",
        "subject_matter", "facts", "demand",
        "notice_period_days", "advocate_name", "advocate_address",
    ],
    optional_fields=["prior_correspondence_ref"],
)

TEMPLATE_LEGAL_NOTICE_GENERAL = """
LEGAL NOTICE

Date: _______________

REGD. A.D. / SPEED POST / COURIER

To,
{recipient_name}
{recipient_address}

Subject: Legal Notice on behalf of {sender_name}

Dear Sir/Madam,

Under instructions from and on behalf of my client, {sender_name},
R/o {sender_address}, I do hereby serve upon you the following Legal
Notice:

1. FACTS:

{facts}

2. SUBJECT MATTER:

{subject_matter}

3. DEMAND:

{demand}

4. You are hereby called upon to comply with the above demand within
   {notice_period_days} days of receipt of this notice, failing which my
   client shall be constrained to initiate appropriate legal proceedings
   against you, civil and/or criminal, at your risk, cost, and
   consequences, without any further notice.

5. A copy of this notice is retained in my office for record and further
   action.

This notice is issued without prejudice to the rights and remedies of
my client, all of which are expressly reserved.

{advocate_name}
Advocate
{advocate_address}
"""

# 4.4 Section 138 NI Act Demand Notice (Cheque Bounce)
_register(
    "legal_notice_cheque_bounce",
    "Section 138 NI Act Demand Notice (Cheque Bounce)",
    "contractual",
    "Statutory demand notice for dishonour of cheque under Section 138 NI Act.",
    required_fields=[
        "sender_name", "sender_address", "recipient_name", "recipient_address",
        "cheque_number", "cheque_date", "cheque_amount", "bank_name",
        "date_of_presentation", "date_of_dishonour", "dishonour_reason",
        "underlying_liability", "advocate_name", "advocate_address",
    ],
    optional_fields=["bank_memo_date"],
)

TEMPLATE_LEGAL_NOTICE_CHEQUE_BOUNCE = """
LEGAL NOTICE
(Under Section 138 read with Section 141 of the Negotiable Instruments
Act, 1881)

Date: _______________

REGD. A.D. / SPEED POST

To,
{recipient_name}
{recipient_address}

Subject: Demand Notice for dishonour of Cheque No. {cheque_number}
         dated {cheque_date} for Rs. {cheque_amount}/-

Dear Sir/Madam,

Under instructions from and on behalf of my client, {sender_name},
R/o {sender_address}, I do hereby serve upon you the following Legal
Notice under Section 138 of the Negotiable Instruments Act, 1881:

1. That you had issued Cheque No. {cheque_number} dated {cheque_date}
   drawn on {bank_name} for Rs. {cheque_amount}/- (Rupees __________
   only) in favour of my client towards discharge of your existing
   liability/debt, namely: {underlying_liability}.

2. That the said cheque was presented by my client for encashment on
   {date_of_presentation} but the same was returned dishonoured /
   unpaid by the drawee bank on {date_of_dishonour} with the remark:
   "{dishonour_reason}".

3. That the dishonour of the cheque constitutes an offence punishable
   under Section 138 of the Negotiable Instruments Act, 1881.

4. You are hereby called upon to make the payment of the cheque amount
   of Rs. {cheque_amount}/- within 15 DAYS from the date of receipt of
   this notice.

5. In the event of your failure to make the payment within the
   stipulated period of 15 days, my client shall be constrained to file
   a Criminal Complaint under Section 138 of the NI Act, 1881 before
   the competent Magistrate, at your risk, cost, and consequences.

This notice is issued without prejudice to the other rights and
remedies of my client under law.

A copy of this notice is retained in my office for record and use.

{advocate_name}
Advocate
{advocate_address}
"""

# 4.5 Mutual NDA
_register(
    "nda_mutual",
    "Mutual Non-Disclosure Agreement",
    "contractual",
    "Mutual NDA for protecting confidential information between parties.",
    required_fields=[
        "party_a_name", "party_a_address", "party_a_type",
        "party_b_name", "party_b_address", "party_b_type",
        "purpose_of_disclosure", "confidentiality_period_years",
        "governing_law_state", "jurisdiction_city",
    ],
    optional_fields=["exclusions", "permitted_disclosees"],
)

TEMPLATE_NDA_MUTUAL = """
MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement ("Agreement") is executed on this
__________ day of __________, 20__ at _______________.

BETWEEN:

{party_a_name}, a {party_a_type} having its registered office /
residing at {party_a_address} (hereinafter referred to as "Party A",
which expression shall, unless repugnant to the context, include its
successors and permitted assigns) of the FIRST PART;

AND

{party_b_name}, a {party_b_type} having its registered office /
residing at {party_b_address} (hereinafter referred to as "Party B",
which expression shall, unless repugnant to the context, include its
successors and permitted assigns) of the SECOND PART.

Party A and Party B are hereinafter individually referred to as "Party"
and collectively as "Parties."

WHEREAS the Parties wish to explore a business relationship concerning
{purpose_of_disclosure} ("Purpose") and in connection therewith, each
Party may disclose certain confidential and proprietary information to
the other.

NOW, THEREFORE, in consideration of the mutual covenants contained
herein and for other good and valuable consideration, the Parties agree
as follows:

1. DEFINITION OF CONFIDENTIAL INFORMATION
   "Confidential Information" means all information disclosed by either
   Party (the "Disclosing Party") to the other (the "Receiving Party"),
   whether orally, in writing, or by any other means, that is designated
   as confidential or that reasonably should be understood to be
   confidential given the nature of the information.

2. OBLIGATIONS
   The Receiving Party shall: (a) hold the Confidential Information in
   strict confidence; (b) not disclose it to any third party without
   prior written consent; (c) use it solely for the Purpose; (d) protect
   it with at least the same degree of care as its own confidential
   information, but no less than reasonable care.

3. EXCLUSIONS
   This Agreement does not apply to information that: (a) is or becomes
   publicly available without breach; (b) was known to the Receiving
   Party prior to disclosure; (c) is independently developed; (d) is
   lawfully received from a third party without restriction.

4. TERM
   This Agreement shall remain in effect for a period of
   {confidentiality_period_years} year(s) from the date of execution.

5. RETURN OF INFORMATION
   Upon termination or request, the Receiving Party shall return or
   destroy all Confidential Information and certify such destruction.

6. REMEDIES
   The Parties acknowledge that breach may cause irreparable harm and
   that the Disclosing Party shall be entitled to equitable relief
   including injunction in addition to other remedies.

7. GOVERNING LAW AND JURISDICTION
   This Agreement shall be governed by the laws of India and the State
   of {governing_law_state}. Courts at {jurisdiction_city} shall have
   exclusive jurisdiction.

8. GENERAL
   This Agreement constitutes the entire agreement. No amendment shall
   be effective unless in writing. Neither Party may assign this
   Agreement without prior written consent.

IN WITNESS WHEREOF, the Parties have executed this Agreement on the
date first written above.

For {party_a_name}                    For {party_b_name}

Signature: ______________             Signature: ______________
Name:                                 Name:
Designation:                          Designation:
Date:                                 Date:

WITNESSES:
1. ________________________
2. ________________________
"""

# 4.6 Professional Services Agreement
_register(
    "service_agreement",
    "Professional Services Agreement",
    "contractual",
    "Agreement for professional / consultancy services.",
    required_fields=[
        "client_name", "client_address",
        "service_provider_name", "service_provider_address",
        "scope_of_services", "service_fee", "payment_terms",
        "term_start_date", "term_end_date",
        "governing_law_state", "jurisdiction_city",
    ],
    optional_fields=["deliverables", "sla_terms", "termination_notice_period"],
)

TEMPLATE_SERVICE_AGREEMENT = """
PROFESSIONAL SERVICES AGREEMENT

This Professional Services Agreement ("Agreement") is executed on this
__________ day of __________, 20__ at _______________.

BETWEEN:

{client_name}, having its office at {client_address} (hereinafter
referred to as the "Client") of the FIRST PART;

AND

{service_provider_name}, having its office at {service_provider_address}
(hereinafter referred to as the "Service Provider") of the SECOND PART.

WHEREAS the Client desires to engage the Service Provider to provide
certain professional services, and the Service Provider agrees to
provide such services on the terms and conditions set forth herein.

NOW, THEREFORE, the Parties agree as follows:

1. SCOPE OF SERVICES
   {scope_of_services}

2. TERM
   This Agreement shall commence on {term_start_date} and shall
   continue until {term_end_date} unless terminated earlier.

3. FEES AND PAYMENT
   Service Fee: Rs. {service_fee}/-
   Payment Terms: {payment_terms}
   All payments are subject to applicable TDS under the Income Tax Act.

4. CONFIDENTIALITY
   Each Party shall maintain confidentiality of the other's proprietary
   information.

5. INTELLECTUAL PROPERTY
   All deliverables created under this Agreement shall vest in the
   Client upon full payment.

6. INDEMNIFICATION
   Each Party shall indemnify the other against losses arising from
   breach of this Agreement.

7. TERMINATION
   Either Party may terminate this Agreement by giving 30 days' prior
   written notice.

8. GOVERNING LAW
   This Agreement shall be governed by the laws of India and the State
   of {governing_law_state}. Courts at {jurisdiction_city} shall have
   exclusive jurisdiction.

IN WITNESS WHEREOF, the Parties have executed this Agreement.

For {client_name}                     For {service_provider_name}

Signature: ______________             Signature: ______________
Name:                                 Name:
Designation:                          Designation:
Date:                                 Date:

WITNESSES:
1. ________________________
2. ________________________
"""

# 4.7 General Power of Attorney
_register(
    "power_of_attorney_general",
    "General Power of Attorney",
    "contractual",
    "General Power of Attorney authorising broad powers.",
    required_fields=[
        "principal_name", "principal_father_name", "principal_address",
        "principal_age",
        "attorney_name", "attorney_father_name", "attorney_address",
        "attorney_age",
        "powers_granted",
    ],
    optional_fields=["revocation_clause", "validity_period"],
)

TEMPLATE_POWER_OF_ATTORNEY_GENERAL = """
GENERAL POWER OF ATTORNEY

(On Non-Judicial Stamp Paper of appropriate value)

KNOW ALL MEN BY THESE PRESENTS:

I, {principal_name}, S/o / D/o / W/o {principal_father_name}, aged about
{principal_age} years, residing at {principal_address} (hereinafter
referred to as the "Principal" / "Executant")

DO HEREBY NOMINATE, CONSTITUTE, AND APPOINT:

{attorney_name}, S/o / D/o / W/o {attorney_father_name}, aged about
{attorney_age} years, residing at {attorney_address} (hereinafter
referred to as my "Attorney" / "Power of Attorney Holder")

as my true and lawful Attorney, to act, do, execute, and perform all or
any of the following acts, deeds, and things on my behalf:

POWERS GRANTED:

{powers_granted}

GENERAL POWERS:

(a) To sign, execute, verify, submit, and present all applications,
    forms, returns, documents, deeds, agreements, and writings.

(b) To appear before any authority, court, tribunal, office, or person
    and represent me.

(c) To receive and make payments, issue and receive receipts.

(d) To engage advocates, chartered accountants, and other professionals.

(e) To do all such acts as may be necessary and incidental to the above.

AND I do hereby agree and declare that all acts, deeds, and things done
by my said Attorney shall be construed as acts, deeds, and things done
by me and shall be binding on me and my heirs, executors, and
administrators.

AND I hereby agree to ratify and confirm all that my Attorney shall
lawfully do or cause to be done by virtue of this Power of Attorney.

IN WITNESS WHEREOF, I have executed this General Power of Attorney on
this __________ day of __________, 20__ at __________.

EXECUTANT:

(Signature)
{principal_name}

WITNESSES:
1. Name: _____________ Signature: _____________
2. Name: _____________ Signature: _____________

ACCEPTANCE:

I, {attorney_name}, do hereby accept the above Power of Attorney.

(Signature)
{attorney_name}
"""

# 4.8 Special Power of Attorney
_register(
    "power_of_attorney_special",
    "Special Power of Attorney (Specific Transaction)",
    "contractual",
    "Special Power of Attorney for a specific transaction or purpose.",
    required_fields=[
        "principal_name", "principal_father_name", "principal_address",
        "principal_age",
        "attorney_name", "attorney_father_name", "attorney_address",
        "attorney_age",
        "specific_purpose", "property_or_subject_description",
    ],
    optional_fields=["validity_period", "consideration_details"],
)

TEMPLATE_POWER_OF_ATTORNEY_SPECIAL = """
SPECIAL POWER OF ATTORNEY

(On Non-Judicial Stamp Paper of appropriate value)

KNOW ALL MEN BY THESE PRESENTS:

I, {principal_name}, S/o / D/o / W/o {principal_father_name}, aged about
{principal_age} years, residing at {principal_address} (hereinafter
referred to as the "Principal" / "Executant")

DO HEREBY NOMINATE, CONSTITUTE, AND APPOINT:

{attorney_name}, S/o / D/o / W/o {attorney_father_name}, aged about
{attorney_age} years, residing at {attorney_address} (hereinafter
referred to as my "Attorney")

as my true and lawful Attorney SPECIFICALLY AND SOLELY for the purpose of:

{specific_purpose}

IN RESPECT OF:

{property_or_subject_description}

My said Attorney is authorised to:

(a) Negotiate, sign, execute, and register all documents in connection
    with the above specific purpose;

(b) Appear before the concerned authorities / Sub-Registrar / Courts;

(c) Make and receive payments related to the above purpose only;

(d) Do all such acts as are necessary and incidental solely for the
    above purpose.

This Special Power of Attorney is limited to the specific purpose
mentioned above and does not confer any general powers on the Attorney.

This Power of Attorney shall be irrevocable until the completion of the
above transaction / shall remain valid until __________.

IN WITNESS WHEREOF, I have executed this Special Power of Attorney on
this __________ day of __________, 20__ at __________.

EXECUTANT:
(Signature)
{principal_name}

WITNESSES:
1. Name: _____________ Signature: _____________
2. Name: _____________ Signature: _____________

ACCEPTED BY:
(Signature)
{attorney_name}
"""

# ===================================================================
# 5. TAX & GST TEMPLATES  (8)
# ===================================================================

# 5.1 Reply to GST SCN u/s 73 CGST
_register(
    "gst_notice_reply_73",
    "Reply to Show Cause Notice u/s 73 CGST Act",
    "tax_gst",
    "Reply to SCN under Section 73 CGST (non-fraud cases).",
    required_fields=[
        "authority_name", "authority_address",
        "noticee_name", "noticee_gstin", "noticee_address",
        "scn_reference_number", "scn_date", "financial_year",
        "tax_demand_amount", "grounds_of_reply",
    ],
    optional_fields=["documents_enclosed", "case_laws_relied"],
)

TEMPLATE_GST_NOTICE_REPLY_73 = """
To,
{authority_name}
{authority_address}

Subject: Reply to Show Cause Notice No. {scn_reference_number} dated
         {scn_date} issued under Section 73 of the CGST Act, 2017

GSTIN: {noticee_gstin}
Financial Year: {financial_year}

Respected Sir/Madam,

With reference to the above-mentioned Show Cause Notice, I/we,
{noticee_name}, GSTIN: {noticee_gstin}, having our place of business at
{noticee_address}, beg to submit the following reply:

1. That the SCN demands an amount of Rs. {tax_demand_amount}/- on
   account of alleged short payment / non-payment / erroneous refund /
   wrong availment of input tax credit for the financial year
   {financial_year}.

2. REPLY ON MERITS:

{grounds_of_reply}

3. That without prejudice to the above, the noticee submits that no
   penalty is leviable as there is no intent to evade tax and the
   proceedings have been rightly initiated under Section 73 (and not
   Section 74) of the CGST Act, 2017.

4. The noticee reserves the right to file additional submissions and
   produce additional evidence at the time of personal hearing.

It is therefore most respectfully prayed that the Hon'ble Authority may
drop the proceedings initiated vide the impugned SCN and pass an order
in favour of the noticee.

Place: _______________
Date:  _______________

                                        Yours faithfully,

                                        {noticee_name}
                                        GSTIN: {noticee_gstin}

                                        Through Authorised Representative
"""

# 5.2 Reply to GST SCN u/s 74 CGST (Fraud/Suppression)
_register(
    "gst_notice_reply_74",
    "Reply to SCN u/s 74 CGST Act (Fraud/Suppression)",
    "tax_gst",
    "Reply to SCN under Section 74 CGST (fraud, suppression, misstatement).",
    required_fields=[
        "authority_name", "authority_address",
        "noticee_name", "noticee_gstin", "noticee_address",
        "scn_reference_number", "scn_date", "financial_year",
        "tax_demand_amount", "penalty_demand",
        "grounds_of_reply", "no_fraud_justification",
    ],
    optional_fields=["documents_enclosed", "case_laws_relied"],
)

TEMPLATE_GST_NOTICE_REPLY_74 = """
To,
{authority_name}
{authority_address}

Subject: Reply to Show Cause Notice No. {scn_reference_number} dated
         {scn_date} issued under Section 74 of the CGST Act, 2017

GSTIN: {noticee_gstin}
Financial Year: {financial_year}

Respected Sir/Madam,

With reference to the above-mentioned Show Cause Notice, the noticee,
{noticee_name}, GSTIN: {noticee_gstin}, submits the following reply:

1. The SCN demands tax of Rs. {tax_demand_amount}/- with penalty of
   Rs. {penalty_demand}/- alleging fraud / wilful misstatement /
   suppression of facts under Section 74 of the CGST Act, 2017.

2. PRELIMINARY OBJECTIONS:

   The noticee vehemently denies any allegation of fraud, wilful
   misstatement, or suppression of facts. The invocation of Section 74
   is without basis:

{no_fraud_justification}

3. REPLY ON MERITS:

{grounds_of_reply}

4. That in the absence of fraud, wilful misstatement, or suppression,
   the extended period of limitation under Section 74 cannot be invoked
   and the SCN is time-barred. Reference: Section 73 applies, with its
   shorter limitation period.

5. Without prejudice, the penalty under Section 74 is unwarranted as
   the ingredients of Section 74 are not satisfied.

PRAYER:

It is prayed that the proceedings be dropped or, in the alternative,
be treated under Section 73 of the CGST Act.

Place: _______________
Date:  _______________

                                        {noticee_name}
                                        GSTIN: {noticee_gstin}
"""

# 5.3 GST First Appeal u/s 107
_register(
    "gst_appeal_first",
    "First Appeal to Appellate Authority u/s 107 CGST",
    "tax_gst",
    "First appeal against order of adjudicating authority under GST.",
    required_fields=[
        "appellate_authority", "appellant_name", "appellant_gstin",
        "appellant_address", "order_number", "order_date",
        "adjudicating_authority", "tax_amount", "penalty_amount",
        "grounds_of_appeal", "pre_deposit_details",
    ],
    optional_fields=["interest_amount", "case_laws_relied"],
)

TEMPLATE_GST_APPEAL_FIRST = """
BEFORE THE APPELLATE AUTHORITY
{appellate_authority}

Appeal No. __________
(Under Section 107 of the Central Goods and Services Tax Act, 2017)

IN THE MATTER OF:

{appellant_name}
GSTIN: {appellant_gstin}
Address: {appellant_address}
                                                    ... APPELLANT

APPEAL AGAINST ORDER NO. {order_number} DATED {order_date}
PASSED BY {adjudicating_authority}

1. The appellant is aggrieved by the order dated {order_date} bearing
   No. {order_number} passed by {adjudicating_authority} demanding
   tax of Rs. {tax_amount}/- and penalty of Rs. {penalty_amount}/-.

2. PRE-DEPOSIT:
   The appellant has made the mandatory pre-deposit as required under
   Section 107(6) of the CGST Act: {pre_deposit_details}

3. GROUNDS OF APPEAL:

{grounds_of_appeal}

4. That the impugned order is contrary to law, facts, and the provisions
   of the CGST Act, 2017 and Rules made thereunder.

PRAYER:

(a) Set aside the impugned order dated {order_date};

(b) Grant stay of the demand pending disposal of the appeal;

(c) Any other relief as the Appellate Authority may deem fit.

Place: _______________
Date:  _______________

                                        {appellant_name}
                                        GSTIN: {appellant_gstin}
"""

# 5.4 Reply to Notice u/s 148 IT Act (Reassessment)
_register(
    "it_notice_reply_148",
    "Reply to Notice u/s 148 Income Tax Act (Reassessment)",
    "tax_gst",
    "Reply/objection to reassessment notice under Section 148 IT Act.",
    required_fields=[
        "assessing_officer", "ao_address",
        "assessee_name", "assessee_pan", "assessee_address",
        "notice_date", "assessment_year",
        "objections_to_reopening",
    ],
    optional_fields=["original_return_date", "original_assessment_date", "case_laws_relied"],
)

TEMPLATE_IT_NOTICE_REPLY_148 = """
To,
{assessing_officer}
{ao_address}

Subject: Reply / Objections to Notice u/s 148 / 148A of the Income Tax
         Act, 1961 for A.Y. {assessment_year}

PAN: {assessee_pan}

Respected Sir/Madam,

This is with reference to the Notice dated {notice_date} issued under
Section 148 / 148A of the Income Tax Act, 1961 proposing to reopen the
assessment for A.Y. {assessment_year}.

1. The assessee, {assessee_name} (PAN: {assessee_pan}), R/o
   {assessee_address}, has duly filed the return of income for the
   relevant assessment year and the same has been processed / assessed.

2. OBJECTIONS TO REOPENING:

{objections_to_reopening}

3. That the conditions precedent for issuing notice under Section 148
   are not satisfied. The reopening is based on mere change of opinion,
   which is not permissible (CIT v. Kelvinator of India, (2010) 320 ITR
   561 (SC)).

4. The assessee requests that the objections be disposed of by a
   speaking order before proceeding further, as mandated by GKN
   Driveshafts (India) Ltd. v. ITO, (2003) 259 ITR 19 (SC).

5. The assessee reserves the right to file further submissions.

The assessee requests that the notice be withdrawn and the reassessment
proceedings be dropped.

Place: _______________
Date:  _______________

                                        {assessee_name}
                                        PAN: {assessee_pan}
"""

# 5.5 Reply to Scrutiny Notice u/s 143(2)
_register(
    "it_notice_reply_143_2",
    "Reply to Scrutiny Notice u/s 143(2) IT Act",
    "tax_gst",
    "Detailed reply to scrutiny assessment notice with supporting submissions.",
    required_fields=[
        "assessing_officer", "ao_address",
        "assessee_name", "assessee_pan", "assessee_address",
        "notice_date", "assessment_year",
        "queries_and_replies",
    ],
    optional_fields=["documents_submitted", "case_laws_relied"],
)

TEMPLATE_IT_NOTICE_REPLY_143_2 = """
To,
{assessing_officer}
{ao_address}

Subject: Submission in response to Notice u/s 143(2) of the Income Tax
         Act, 1961 for A.Y. {assessment_year}

PAN: {assessee_pan}

Respected Sir/Madam,

This is with reference to the Notice dated {notice_date} issued under
Section 143(2) of the Income Tax Act, 1961 for A.Y. {assessment_year}.

The assessee, {assessee_name} (PAN: {assessee_pan}), most respectfully
submits the following:

QUERY-WISE REPLIES:

{queries_and_replies}

The assessee submits that the return of income filed for A.Y.
{assessment_year} is correct and complete in all respects.

The assessee requests that the assessment be completed in accordance
with law and prays for a just and fair order.

Place: _______________
Date:  _______________

                                        Yours faithfully,

                                        {assessee_name}
                                        PAN: {assessee_pan}
"""

# 5.6 Appeal to CIT(A) u/s 246A
_register(
    "it_appeal_cit_a",
    "Appeal to CIT(Appeals) u/s 246A IT Act",
    "tax_gst",
    "First appeal against assessment order to Commissioner of Income Tax (Appeals).",
    required_fields=[
        "cit_a_address", "appellant_name", "appellant_pan",
        "appellant_address", "assessment_year",
        "order_number", "order_date", "assessing_officer",
        "total_income_assessed", "total_income_returned",
        "grounds_of_appeal",
    ],
    optional_fields=["demand_amount", "stay_application"],
)

TEMPLATE_IT_APPEAL_CIT_A = """
FORM NO. 35
APPEAL TO THE COMMISSIONER OF INCOME TAX (APPEALS)
(Under Section 246A of the Income Tax Act, 1961)

To,
The Commissioner of Income Tax (Appeals)
{cit_a_address}

1. Name of the Appellant: {appellant_name}
2. PAN: {appellant_pan}
3. Address: {appellant_address}
4. Assessment Year: {assessment_year}
5. Order appealed against: Order u/s __________ No. {order_number}
   dated {order_date} passed by {assessing_officer}
6. Total income as per return: Rs. {total_income_returned}/-
7. Total income as assessed: Rs. {total_income_assessed}/-

GROUNDS OF APPEAL:

{grounds_of_appeal}

PRAYER:

The appellant prays that the Hon'ble CIT(A) may be pleased to:

(a) Delete the additions / disallowances made by the Assessing Officer;

(b) Direct the Assessing Officer to accept the income as returned by
    the appellant;

(c) Grant stay of demand pending disposal of the appeal;

(d) Any other relief as may be deemed fit.

Place: _______________
Date:  _______________

                                        {appellant_name}
                                        PAN: {appellant_pan}

VERIFICATION:

I, {appellant_name}, do hereby declare that what is stated above is true
to the best of my knowledge and belief.

                                        (Signature of Appellant)
"""

# 5.7 Appeal to ITAT u/s 253
_register(
    "it_appeal_itat",
    "Appeal to ITAT u/s 253 IT Act",
    "tax_gst",
    "Second appeal to Income Tax Appellate Tribunal against CIT(A) order.",
    required_fields=[
        "itat_bench", "appellant_name", "appellant_pan",
        "appellant_address", "assessment_year",
        "cit_a_order_number", "cit_a_order_date",
        "grounds_of_appeal",
    ],
    optional_fields=["cross_objections", "stay_application", "additional_grounds"],
)

TEMPLATE_IT_APPEAL_ITAT = """
BEFORE THE HON'BLE INCOME TAX APPELLATE TRIBUNAL
{itat_bench}

ITA No. __________
Assessment Year: {assessment_year}

{appellant_name}
PAN: {appellant_pan}
Address: {appellant_address}
                                                    ... APPELLANT

                        VERSUS

Income Tax Officer / DCIT / ACIT / CIT
                                                    ... RESPONDENT

APPEAL UNDER SECTION 253 OF THE INCOME TAX ACT, 1961

AGAINST THE ORDER OF THE COMMISSIONER OF INCOME TAX (APPEALS)
ORDER NO. {cit_a_order_number} DATED {cit_a_order_date}

The appellant respectfully submits the following:

GROUNDS OF APPEAL:

{grounds_of_appeal}

GENERAL GROUND:

The appellant craves leave to add, alter, amend, or withdraw any of the
grounds of appeal at any time before or at the time of hearing.

PRAYER:

The appellant prays that the Hon'ble Tribunal may be pleased to:

(a) Allow the appeal;

(b) Delete the additions / disallowances sustained by the Ld. CIT(A);

(c) Any other relief as the Hon'ble Tribunal may deem fit.

Place: _______________
Date:  _______________

                                        {appellant_name}
                                        PAN: {appellant_pan}

VERIFICATION:

I, {appellant_name}, the appellant above named, do hereby verify that the
facts stated in the grounds of appeal and in the form of appeal are true
to the best of my knowledge and belief.

                                        (Signature of Appellant)
"""

# 5.8 Advance Ruling Application u/s 98 CGST
_register(
    "advance_ruling_application",
    "Application for Advance Ruling u/s 98 CGST Act",
    "tax_gst",
    "Application to Authority for Advance Ruling on GST classification/applicability.",
    required_fields=[
        "aar_authority", "applicant_name", "applicant_gstin",
        "applicant_address", "question_for_ruling",
        "relevant_facts", "applicant_interpretation",
        "statutory_provisions_involved",
    ],
    optional_fields=["supporting_case_laws", "fee_payment_details"],
)

TEMPLATE_ADVANCE_RULING_APPLICATION = """
FORM GST ARA-01
APPLICATION FOR ADVANCE RULING

BEFORE THE AUTHORITY FOR ADVANCE RULING
{aar_authority}

1. APPLICANT DETAILS:
   Name: {applicant_name}
   GSTIN: {applicant_gstin}
   Address: {applicant_address}

2. QUESTION(S) ON WHICH ADVANCE RULING IS SOUGHT:

{question_for_ruling}

3. STATEMENT OF RELEVANT FACTS:

{relevant_facts}

4. STATEMENT CONTAINING THE APPLICANT'S INTERPRETATION OF LAW:

{applicant_interpretation}

5. RELEVANT STATUTORY PROVISIONS:

{statutory_provisions_involved}

6. The applicant declares that the question raised in this application
   is not pending or decided in any proceedings under the CGST/SGST Act.

7. The prescribed fee of Rs. 5,000/- under CGST and Rs. 5,000/- under
   SGST has been paid.

PRAYER:

The applicant prays that the Authority may pass an appropriate ruling
on the question(s) raised above.

Place: _______________
Date:  _______________

                                        {applicant_name}
                                        GSTIN: {applicant_gstin}

VERIFICATION:

I hereby declare that the information given in this application is true
and correct to the best of my knowledge and belief.

                                        (Signature of Authorised Signatory)
"""

# ===================================================================
# 6. PROPERTY & FAMILY TEMPLATES  (6)
# ===================================================================

# 6.1 Sale Deed
_register(
    "sale_deed",
    "Sale Deed for Immovable Property",
    "property_family",
    "Sale deed for transfer of immovable property with schedule and covenants.",
    required_fields=[
        "seller_name", "seller_father_name", "seller_address", "seller_age",
        "buyer_name", "buyer_father_name", "buyer_address", "buyer_age",
        "sale_consideration", "property_description",
        "property_boundaries", "encumbrance_details",
    ],
    optional_fields=["stamp_duty_paid", "previous_title_chain", "possession_date"],
)

TEMPLATE_SALE_DEED = """
SALE DEED

(To be executed on Non-Judicial Stamp Paper of appropriate value as per
the State Stamp Act and registered under the Registration Act, 1908)

This Sale Deed is executed on this __________ day of __________, 20__
at __________.

BY:

{seller_name}, S/o / D/o / W/o {seller_father_name}, aged about
{seller_age} years, residing at {seller_address}, PAN __________,
Aadhaar __________ (hereinafter called the "SELLER" / "VENDOR" /
"TRANSFEROR", which expression shall include his/her heirs, executors,
administrators, legal representatives, and assigns) of the FIRST PART;

IN FAVOUR OF:

{buyer_name}, S/o / D/o / W/o {buyer_father_name}, aged about
{buyer_age} years, residing at {buyer_address}, PAN __________,
Aadhaar __________ (hereinafter called the "BUYER" / "PURCHASER" /
"TRANSFEREE", which expression shall include his/her heirs, executors,
administrators, legal representatives, and assigns) of the SECOND PART;

WHEREAS:

(a) The Seller is the absolute owner in possession and enjoyment of the
    immovable property more fully described in the Schedule hereunder.

(b) The Seller has agreed to sell and the Buyer has agreed to purchase
    the said property for a total sale consideration of
    Rs. {sale_consideration}/- (Rupees __________ only).

NOW THIS DEED WITNESSETH:

1. That in consideration of Rs. {sale_consideration}/- paid by the Buyer
   to the Seller (the receipt whereof the Seller doth hereby admit and
   acknowledge), the Seller doth hereby grant, convey, sell, transfer,
   and assign unto the Buyer, the property described in the Schedule
   below, together with all rights, easements, privileges, and
   appurtenances thereto.

2. That the Seller hereby declares and covenants:
   (a) The Seller has clear, absolute, and marketable title;
   (b) The property is free from all encumbrances, mortgages, charges,
       liens, and claims: {encumbrance_details};
   (c) The Seller shall indemnify the Buyer against any claims on the
       property;
   (d) The Seller has not entered into any agreement for sale or
       otherwise with any other person.

3. That the possession of the said property has been / shall be handed
   over to the Buyer on the date of execution / on __________.

SCHEDULE OF PROPERTY:

{property_description}

BOUNDARIES:
{property_boundaries}

IN WITNESS WHEREOF, the Seller has executed this Sale Deed on the day,
month, and year first above written.

SELLER:
(Signature)
{seller_name}

BUYER (ACCEPTING):
(Signature)
{buyer_name}

WITNESSES:
1. Name: _____________ Signature: _____________ Address: _____________
2. Name: _____________ Signature: _____________ Address: _____________
"""

# 6.2 Gift Deed
_register(
    "gift_deed",
    "Gift Deed (with IT implications note)",
    "property_family",
    "Gift deed for immovable/movable property with Section 56(2)(x) IT Act reference.",
    required_fields=[
        "donor_name", "donor_father_name", "donor_address", "donor_age",
        "donee_name", "donee_father_name", "donee_address", "donee_age",
        "relationship", "property_description", "estimated_value",
    ],
    optional_fields=["occasion_of_gift", "conditions_if_any"],
)

TEMPLATE_GIFT_DEED = """
GIFT DEED

(On Non-Judicial Stamp Paper of appropriate value)

This Gift Deed is made and executed on this __________ day of __________,
20__ at __________.

BY:

{donor_name}, S/o / D/o / W/o {donor_father_name}, aged about
{donor_age} years, residing at {donor_address} (hereinafter called the
"DONOR") of the FIRST PART;

IN FAVOUR OF:

{donee_name}, S/o / D/o / W/o {donee_father_name}, aged about
{donee_age} years, residing at {donee_address} (hereinafter called the
"DONEE") of the SECOND PART;

WHEREAS:

(a) The Donor is the absolute owner of the property described in the
    Schedule below.

(b) The Donor, out of natural love and affection for the Donee, who is
    the {relationship} of the Donor, desires to gift the said property
    to the Donee voluntarily, without any consideration.

NOW THIS DEED WITNESSETH:

1. That the Donor doth hereby gift, grant, transfer, and convey to the
   Donee, all the right, title, interest, and claim in and to the
   property described in the Schedule below, out of natural love and
   affection, without any monetary consideration.

2. That the estimated value of the gifted property is
   Rs. {estimated_value}/-.

3. That the Donee hereby accepts the gift.

4. That possession of the property is handed over to the Donee.

NOTE ON INCOME TAX IMPLICATIONS:
Under Section 56(2)(x) of the Income Tax Act, 1961, any property received
without consideration or for inadequate consideration may be taxable in
the hands of the recipient, EXCEPT where received from a "relative" as
defined under the Act. The Donor and Donee being {relationship}, this
gift falls within the exempted category (if applicable under the Act).

SCHEDULE OF PROPERTY:

{property_description}

IN WITNESS WHEREOF, the Donor and Donee have executed this Gift Deed.

DONOR:                                DONEE (ACCEPTING):
(Signature)                           (Signature)
{donor_name}                          {donee_name}

WITNESSES:
1. ________________________
2. ________________________
"""

# 6.3 Residential Lease Agreement (11 months)
_register(
    "lease_agreement_residential",
    "Residential Lease Agreement (11 Months)",
    "property_family",
    "Standard 11-month residential lease/rental agreement.",
    required_fields=[
        "landlord_name", "landlord_address",
        "tenant_name", "tenant_address",
        "property_description", "monthly_rent", "security_deposit",
        "lease_start_date", "lease_end_date",
        "city",
    ],
    optional_fields=["maintenance_charges", "rent_escalation_clause", "broker_name"],
)

TEMPLATE_LEASE_AGREEMENT_RESIDENTIAL = """
RESIDENTIAL LEASE / RENT AGREEMENT

(On Non-Judicial Stamp Paper of appropriate value)

This Lease Agreement is made and executed on this __________ day of
__________, 20__ at {city}.

BETWEEN:

{landlord_name}, residing at {landlord_address} (hereinafter referred
to as the "LESSOR" / "LANDLORD") of the FIRST PART;

AND

{tenant_name}, residing at {tenant_address} (hereinafter referred to
as the "LESSEE" / "TENANT") of the SECOND PART.

WHEREAS the Lessor is the owner of the premises described hereunder and
has agreed to let out the same to the Lessee on the following terms:

1. PREMISES:
   {property_description}

2. TERM:
   Period: 11 (Eleven) months commencing from {lease_start_date} to
   {lease_end_date}. This agreement does not create any tenancy rights
   under the applicable Rent Control Act.

3. RENT:
   Monthly Rent: Rs. {monthly_rent}/- (Rupees __________ only),
   payable on or before the 7th of each English calendar month.

4. SECURITY DEPOSIT:
   Rs. {security_deposit}/- (Rupees __________ only) paid by the
   Lessee to the Lessor. Refundable without interest upon termination,
   after deducting arrears and damages, if any.

5. LESSEE'S OBLIGATIONS:
   (a) Use the premises solely for residential purposes;
   (b) Not sublet or assign the premises;
   (c) Maintain the premises in good condition;
   (d) Pay electricity, water, and other utility bills;
   (e) Not make structural alterations without written consent;
   (f) Vacate upon expiry and return keys.

6. LESSOR'S OBLIGATIONS:
   (a) Ensure peaceful possession;
   (b) Carry out major structural repairs;
   (c) Refund security deposit as per Clause 4.

7. TERMINATION:
   Either party may terminate by giving one month's written notice.

8. JURISDICTION:
   Courts at {city} shall have exclusive jurisdiction.

SCHEDULE OF PROPERTY:
{property_description}

IN WITNESS WHEREOF, the parties have set their hands on the day, month,
and year first above written.

LESSOR:                               LESSEE:
(Signature)                           (Signature)
{landlord_name}                       {tenant_name}

WITNESSES:
1. ________________________
2. ________________________
"""

# 6.4 Commercial Lease Agreement
_register(
    "lease_agreement_commercial",
    "Commercial Lease Agreement",
    "property_family",
    "Lease agreement for commercial premises with CAM charges and fit-out provisions.",
    required_fields=[
        "landlord_name", "landlord_address",
        "tenant_name", "tenant_address", "tenant_business",
        "property_description", "carpet_area",
        "monthly_rent", "security_deposit", "cam_charges",
        "lease_start_date", "lease_term_years",
        "lock_in_period", "rent_escalation_percentage",
        "city",
    ],
    optional_fields=["fit_out_period", "parking_details", "signage_rights"],
)

TEMPLATE_LEASE_AGREEMENT_COMMERCIAL = """
COMMERCIAL LEASE AGREEMENT

(On Non-Judicial Stamp Paper of appropriate value)

This Lease Deed is executed on this __________ day of __________, 20__
at {city}.

BETWEEN:

{landlord_name}, having its office at {landlord_address} (hereinafter
referred to as the "LESSOR") of the FIRST PART;

AND

{tenant_name}, having its office at {tenant_address}, engaged in the
business of {tenant_business} (hereinafter referred to as the "LESSEE")
of the SECOND PART;

1. PREMISES:
   {property_description}
   Carpet Area: {carpet_area} sq. ft.

2. TERM:
   {lease_term_years} year(s) commencing from {lease_start_date}.
   Lock-in Period: {lock_in_period}

3. RENT:
   Monthly Rent: Rs. {monthly_rent}/-
   CAM Charges: Rs. {cam_charges}/- per month
   Annual Escalation: {rent_escalation_percentage}%

4. SECURITY DEPOSIT:
   Rs. {security_deposit}/- (interest-free, refundable).

5. PERMITTED USE:
   The premises shall be used solely for the Lessee's business of
   {tenant_business}.

6. MAINTENANCE:
   Day-to-day maintenance: Lessee.
   Structural and major repairs: Lessor.

7. TERMINATION:
   After lock-in, either party may terminate by giving 3 months' notice.
   During lock-in, the Lessee shall pay rent for the remaining lock-in
   period as liquidated damages.

8. TDS:
   The Lessee shall deduct TDS at applicable rates on rent payments as
   per the Income Tax Act, 1961 and provide TDS certificates.

9. REGISTRATION:
   This Deed shall be registered under the Registration Act, 1908.

10. JURISDICTION:
    Courts at {city} shall have exclusive jurisdiction.

IN WITNESS WHEREOF, the parties have executed this deed.

LESSOR:                               LESSEE:
(Signature)                           (Signature)
{landlord_name}                       {tenant_name}

WITNESSES:
1. ________________________
2. ________________________
"""

# 6.5 Simple Will / Testament
_register(
    "will_simple",
    "Simple Will / Testament",
    "property_family",
    "Simple will format with bequests, executor appointment, and attestation.",
    required_fields=[
        "testator_name", "testator_father_name", "testator_address",
        "testator_age", "testator_religion",
        "bequests", "executor_name", "executor_address",
    ],
    optional_fields=["residuary_clause", "guardian_for_minors", "revocation_clause"],
)

TEMPLATE_WILL_SIMPLE = """
LAST WILL AND TESTAMENT

I, {testator_name}, S/o / D/o / W/o {testator_father_name}, aged about
{testator_age} years, {testator_religion}, residing at
{testator_address}, being of sound and disposing mind, memory, and
understanding, and not acting under any coercion, undue influence, fraud,
or misrepresentation, do hereby revoke all my former Wills, Codicils, and
testamentary dispositions heretofore made by me and declare this to be my
Last Will and Testament.

I DECLARE AND DIRECT AS FOLLOWS:

1. FAMILY DETAILS:
   [Details of family members to be inserted]

2. BEQUESTS:

{bequests}

3. EXECUTOR:
   I appoint {executor_name}, residing at {executor_address}, as the
   Executor of this Will and authorise him/her to carry out the
   provisions of this Will, obtain Probate if necessary, and administer
   my estate.

4. RESIDUARY ESTATE:
   All my remaining properties, assets, and belongings not specifically
   dealt with herein shall devolve upon __________.

5. GENERAL DECLARATIONS:
   (a) This Will is made voluntarily and without any coercion.
   (b) I reserve the right to revoke, alter, or amend this Will.
   (c) This Will shall come into effect after my demise.

IN WITNESS WHEREOF, I, {testator_name}, have signed this Will on this
__________ day of __________, 20__ at __________ in the presence of the
following witnesses who have attested the same in my presence and in the
presence of each other.

TESTATOR:
(Signature)
{testator_name}

WITNESSES (attesting in the presence of the Testator and each other):
1. Name: _____________ Signature: _____________ Address: _____________
2. Name: _____________ Signature: _____________ Address: _____________
"""

# 6.6 Family Settlement Deed
_register(
    "family_settlement_deed",
    "Family Settlement / Partition Deed",
    "property_family",
    "Deed recording amicable partition/settlement among family members.",
    required_fields=[
        "family_members", "property_description",
        "settlement_terms", "shares_allocated",
    ],
    optional_fields=["mediator_name", "pending_litigation_details"],
)

TEMPLATE_FAMILY_SETTLEMENT_DEED = """
FAMILY SETTLEMENT DEED / MEMORANDUM OF FAMILY ARRANGEMENT

(On Non-Judicial Stamp Paper of appropriate value)

This Family Settlement Deed is executed on this __________ day of
__________, 20__ at __________.

BETWEEN THE FOLLOWING FAMILY MEMBERS:

{family_members}

(hereinafter collectively referred to as the "Parties" and individually
as a "Party")

WHEREAS:

(a) The Parties are members of the same family and are joint owners /
    co-owners / co-parceners of the properties described hereunder.

(b) Disputes / differences have arisen among the Parties regarding their
    respective shares and rights in the family properties.

(c) The Parties have, with mutual goodwill and for the sake of family
    harmony, decided to settle their differences amicably and partition
    the family properties as per the terms set out herein.

(d) This family settlement is bona fide and made for the purpose of
    putting an end to existing or apprehended disputes and claims.

NOW THIS DEED WITNESSETH:

1. PROPERTIES SUBJECT TO SETTLEMENT:

{property_description}

2. TERMS OF SETTLEMENT:

{settlement_terms}

3. SHARES ALLOCATED:

{shares_allocated}

4. GENERAL TERMS:
   (a) Each Party shall have absolute rights over the property allotted
       to him/her and shall be free to deal with it independently.
   (b) No Party shall raise any claim or objection regarding the
       properties allotted to other Parties.
   (c) Each Party shall bear the expenses (stamp duty, registration)
       for the property allotted to them.
   (d) This settlement is final, binding, and irrevocable.

5. NOTE: As per settled law (Kale v. Deputy Director of Consolidation,
   AIR 1976 SC 807), a family settlement does not amount to transfer
   and hence no stamp duty on conveyance is payable in most states.
   However, parties are advised to verify applicable state laws.

IN WITNESS WHEREOF, the Parties have executed this Deed.

PARTIES:

[Signatures of all family members]

WITNESSES:
1. ________________________
2. ________________________
"""

# ===================================================================
# 7. CONSUMER & MISCELLANEOUS TEMPLATES  (4)
# ===================================================================

# 7.1 Consumer Complaint
_register(
    "consumer_complaint",
    "Consumer Complaint (Consumer Protection Act 2019)",
    "consumer_misc",
    "Consumer complaint to District/State/National Consumer Commission.",
    required_fields=[
        "commission_name", "complainant_name", "complainant_address",
        "opposite_party_name", "opposite_party_address",
        "product_or_service", "purchase_date", "amount_paid",
        "deficiency_description", "relief_claimed",
        "advocate_name",
    ],
    optional_fields=["invoice_number", "complaint_to_op_date"],
)

TEMPLATE_CONSUMER_COMPLAINT = """
BEFORE THE {commission_name}

Consumer Complaint No. __________
(Under Section 35 of the Consumer Protection Act, 2019)

{complainant_name}
R/o {complainant_address}
                                                    ... COMPLAINANT

                        VERSUS

{opposite_party_name}
{opposite_party_address}
                                                    ... OPPOSITE PARTY

CONSUMER COMPLAINT

MOST RESPECTFULLY SHOWETH:

1. That the complainant is a "consumer" within the meaning of Section
   2(7) of the Consumer Protection Act, 2019, having availed the
   goods/services of the opposite party.

2. That the complainant purchased / availed: {product_or_service}
   on {purchase_date} for a consideration of Rs. {amount_paid}/-.

3. DEFICIENCY IN SERVICE / DEFECT IN GOODS:

{deficiency_description}

4. That the opposite party has been guilty of unfair trade practice /
   deficiency in service / defect in goods and is liable under the
   Consumer Protection Act, 2019.

5. That the complainant has approached the opposite party for redressal
   but the opposite party has failed to resolve the complaint.

6. JURISDICTION:
   This Commission has jurisdiction as the value of goods/services and
   compensation claimed falls within its pecuniary jurisdiction, and the
   opposite party resides / carries on business within its territorial
   jurisdiction.

PRAYER:

(a) Direct the opposite party to pay compensation of Rs. __________/-;

(b) {relief_claimed};

(c) Direct the opposite party to pay litigation costs;

(d) Any other relief as the Commission may deem fit.

VERIFICATION:

I, {complainant_name}, do hereby verify that the contents of the above
complaint are true and correct to the best of my knowledge and belief.

                                        (Signature of Complainant)
                                        {complainant_name}

{advocate_name}
Advocate for the Complainant
"""

# 7.2 RTI Application
_register(
    "rti_application",
    "RTI Application Format",
    "consumer_misc",
    "Application under the Right to Information Act, 2005.",
    required_fields=[
        "pio_designation", "pio_department", "pio_address",
        "applicant_name", "applicant_address",
        "information_sought",
    ],
    optional_fields=["fee_payment_mode", "bpl_status"],
)

TEMPLATE_RTI_APPLICATION = """
APPLICATION UNDER THE RIGHT TO INFORMATION ACT, 2005

To,
The Public Information Officer,
{pio_designation}
{pio_department}
{pio_address}

Subject: Application under Section 6(1) of the Right to Information
         Act, 2005

Sir/Madam,

I, {applicant_name}, residing at {applicant_address}, do hereby request
you to kindly provide the following information under the Right to
Information Act, 2005:

INFORMATION SOUGHT:

{information_sought}

I am enclosing the prescribed fee of Rs. 10/- by way of Court Fee Stamp /
Indian Postal Order / Cash / Demand Draft / Online Payment towards the
application fee.

I undertake to pay additional charges as may be communicated for providing
the information.

I state that the information sought does not relate to any third party and
is not information prohibited under Section 8 and 9 of the RTI Act, 2005.

Place: _______________
Date:  _______________

                                        Yours faithfully,

                                        {applicant_name}
                                        Address: {applicant_address}
                                        Phone: __________
                                        Email: __________
"""

# 7.3 General Affidavit
_register(
    "affidavit_general",
    "General Affidavit Format",
    "consumer_misc",
    "General purpose affidavit on stamp paper with verification and oath.",
    required_fields=[
        "deponent_name", "deponent_father_name", "deponent_address",
        "deponent_age", "affidavit_content",
    ],
    optional_fields=["purpose_of_affidavit", "notary_details"],
)

TEMPLATE_AFFIDAVIT_GENERAL = """
AFFIDAVIT

(On Non-Judicial Stamp Paper of Rs. 10/- or as applicable)

I, {deponent_name}, S/o / D/o / W/o {deponent_father_name}, aged about
{deponent_age} years, residing at {deponent_address}, do hereby
solemnly affirm and state on oath as under:

{affidavit_content}

VERIFICATION:

I, {deponent_name}, the deponent above named, do hereby verify that the
contents of the above affidavit are true and correct to the best of my
knowledge, belief, and information obtained. No part of it is false and
nothing material has been concealed therefrom.

Verified at __________ on this __________ day of __________, 20__.

                                        (Signature of Deponent)
                                        {deponent_name}

BEFORE ME:

Notary Public / Oath Commissioner / Magistrate

(Seal and Signature)
"""

# 7.4 Legal Undertaking
_register(
    "undertaking",
    "Legal Undertaking Format",
    "consumer_misc",
    "Formal legal undertaking / declaration format.",
    required_fields=[
        "person_name", "person_father_name", "person_address",
        "person_age", "undertaking_content", "consequence_of_breach",
    ],
    optional_fields=["addressed_to", "validity_period"],
)

TEMPLATE_UNDERTAKING = """
UNDERTAKING

(On Non-Judicial Stamp Paper of appropriate value, if required)

I, {person_name}, S/o / D/o / W/o {person_father_name}, aged about
{person_age} years, residing at {person_address}, do hereby solemnly
undertake and declare as follows:

{undertaking_content}

I understand and acknowledge that in the event of any breach of this
undertaking:

{consequence_of_breach}

I further declare that this undertaking is given voluntarily, without
any coercion, undue influence, or misrepresentation.

Place: _______________
Date:  _______________

                                        (Signature)
                                        {person_name}

WITNESSES:
1. Name: _____________ Signature: _____________
2. Name: _____________ Signature: _____________
"""


# ===================================================================
# TEMPLATE BODY MAPPING
# ===================================================================
TEMPLATE_BODIES: dict[str, str] = {
    # Criminal
    "bail_anticipatory": TEMPLATE_BAIL_ANTICIPATORY,
    "bail_regular": TEMPLATE_BAIL_REGULAR,
    "bail_default": TEMPLATE_BAIL_DEFAULT,
    "quashing_petition": TEMPLATE_QUASHING_PETITION,
    "criminal_complaint": TEMPLATE_CRIMINAL_COMPLAINT,
    "criminal_revision": TEMPLATE_CRIMINAL_REVISION,
    "parole_application": TEMPLATE_PAROLE_APPLICATION,
    "victim_compensation": TEMPLATE_VICTIM_COMPENSATION,
    # Civil
    "civil_suit_money": TEMPLATE_CIVIL_SUIT_MONEY,
    "civil_suit_specific_performance": TEMPLATE_CIVIL_SUIT_SPECIFIC_PERFORMANCE,
    "civil_suit_partition": TEMPLATE_CIVIL_SUIT_PARTITION,
    "civil_suit_injunction": TEMPLATE_CIVIL_SUIT_INJUNCTION,
    "civil_appeal": TEMPLATE_CIVIL_APPEAL,
    "execution_petition": TEMPLATE_EXECUTION_PETITION,
    "interlocutory_application": TEMPLATE_INTERLOCUTORY_APPLICATION,
    "written_statement": TEMPLATE_WRITTEN_STATEMENT,
    # Corporate
    "board_resolution_general": TEMPLATE_BOARD_RESOLUTION_GENERAL,
    "board_resolution_borrowing": TEMPLATE_BOARD_RESOLUTION_BORROWING,
    "board_resolution_rpt": TEMPLATE_BOARD_RESOLUTION_RPT,
    "board_resolution_director_appointment": TEMPLATE_BOARD_RESOLUTION_DIRECTOR_APPOINTMENT,
    "agm_notice": TEMPLATE_AGM_NOTICE,
    "egm_notice": TEMPLATE_EGM_NOTICE,
    "shareholder_resolution_ordinary": TEMPLATE_SHAREHOLDER_RESOLUTION_ORDINARY,
    "shareholder_resolution_special": TEMPLATE_SHAREHOLDER_RESOLUTION_SPECIAL,
    "minutes_board_meeting": TEMPLATE_MINUTES_BOARD_MEETING,
    "minutes_agm": TEMPLATE_MINUTES_AGM,
    # Contractual
    "arbitration_notice": TEMPLATE_ARBITRATION_NOTICE,
    "arbitration_petition_34": TEMPLATE_ARBITRATION_PETITION_34,
    "legal_notice_general": TEMPLATE_LEGAL_NOTICE_GENERAL,
    "legal_notice_cheque_bounce": TEMPLATE_LEGAL_NOTICE_CHEQUE_BOUNCE,
    "nda_mutual": TEMPLATE_NDA_MUTUAL,
    "service_agreement": TEMPLATE_SERVICE_AGREEMENT,
    "power_of_attorney_general": TEMPLATE_POWER_OF_ATTORNEY_GENERAL,
    "power_of_attorney_special": TEMPLATE_POWER_OF_ATTORNEY_SPECIAL,
    # Tax & GST
    "gst_notice_reply_73": TEMPLATE_GST_NOTICE_REPLY_73,
    "gst_notice_reply_74": TEMPLATE_GST_NOTICE_REPLY_74,
    "gst_appeal_first": TEMPLATE_GST_APPEAL_FIRST,
    "it_notice_reply_148": TEMPLATE_IT_NOTICE_REPLY_148,
    "it_notice_reply_143_2": TEMPLATE_IT_NOTICE_REPLY_143_2,
    "it_appeal_cit_a": TEMPLATE_IT_APPEAL_CIT_A,
    "it_appeal_itat": TEMPLATE_IT_APPEAL_ITAT,
    "advance_ruling_application": TEMPLATE_ADVANCE_RULING_APPLICATION,
    # Property & Family
    "sale_deed": TEMPLATE_SALE_DEED,
    "gift_deed": TEMPLATE_GIFT_DEED,
    "lease_agreement_residential": TEMPLATE_LEASE_AGREEMENT_RESIDENTIAL,
    "lease_agreement_commercial": TEMPLATE_LEASE_AGREEMENT_COMMERCIAL,
    "will_simple": TEMPLATE_WILL_SIMPLE,
    "family_settlement_deed": TEMPLATE_FAMILY_SETTLEMENT_DEED,
    # Consumer & Misc
    "consumer_complaint": TEMPLATE_CONSUMER_COMPLAINT,
    "rti_application": TEMPLATE_RTI_APPLICATION,
    "affidavit_general": TEMPLATE_AFFIDAVIT_GENERAL,
    "undertaking": TEMPLATE_UNDERTAKING,
}


# ===================================================================
# PUBLIC API FUNCTIONS
# ===================================================================

def render_template(template_id: str, data: dict) -> str:
    """
    Render a legal document template with the provided data.

    Args:
        template_id: The identifier of the template (e.g. 'bail_anticipatory').
        data: Dictionary mapping field names to their values.

    Returns:
        The rendered document as a string.

    Raises:
        ValueError: If template_id is unknown or required fields are missing.
    """
    if template_id not in TEMPLATE_REGISTRY:
        raise ValueError(
            f"Unknown template_id '{template_id}'. "
            f"Use list_templates() to see available templates."
        )

    meta = TEMPLATE_REGISTRY[template_id]
    body = TEMPLATE_BODIES.get(template_id)
    if body is None:
        raise ValueError(f"Template body not found for '{template_id}'.")

    # Validate required fields
    missing = [f for f in meta["required_fields"] if f not in data or not data[f]]
    if missing:
        raise ValueError(
            f"Missing required fields for template '{template_id}': {', '.join(missing)}"
        )

    # Fill optional fields with empty string if not provided
    for field in meta.get("optional_fields", []):
        data.setdefault(field, "")

    try:
        rendered = body.format(**data)
    except KeyError as exc:
        raise ValueError(f"Template field not provided: {exc}") from exc

    return rendered.strip()


def get_template_info(template_id: str) -> dict:
    """
    Return metadata for a template including required fields and description.

    Args:
        template_id: The identifier of the template.

    Returns:
        Dictionary with keys: template_id, title, category, description,
        required_fields, optional_fields, output_format.

    Raises:
        ValueError: If template_id is unknown.
    """
    if template_id not in TEMPLATE_REGISTRY:
        raise ValueError(
            f"Unknown template_id '{template_id}'. "
            f"Use list_templates() to see available templates."
        )
    return dict(TEMPLATE_REGISTRY[template_id])


def list_templates(category: str | None = None) -> list[dict]:
    """
    List all templates, optionally filtered by category.

    Args:
        category: Optional category key (e.g. 'criminal', 'civil', 'corporate',
                  'contractual', 'tax_gst', 'property_family', 'consumer_misc').
                  If None, returns all templates.

    Returns:
        List of dicts with template_id, title, category, and description.
    """
    results = []
    for tid, meta in TEMPLATE_REGISTRY.items():
        if category is None or meta["category"] == category:
            results.append({
                "template_id": tid,
                "title": meta["title"],
                "category": meta["category"],
                "category_label": CATEGORIES.get(meta["category"], meta["category"]),
                "description": meta["description"],
            })
    return results


def search_templates(query: str) -> list[dict]:
    """
    Search templates by keyword across title, description, and category.

    Args:
        query: Search string (case-insensitive).

    Returns:
        List of matching template summaries.
    """
    query_lower = query.lower()
    results = []
    for tid, meta in TEMPLATE_REGISTRY.items():
        searchable = " ".join([
            tid,
            meta["title"],
            meta["description"],
            meta["category"],
            CATEGORIES.get(meta["category"], ""),
        ]).lower()
        if query_lower in searchable:
            results.append({
                "template_id": tid,
                "title": meta["title"],
                "category": meta["category"],
                "category_label": CATEGORIES.get(meta["category"], meta["category"]),
                "description": meta["description"],
            })
    return results


def get_categories() -> dict[str, str]:
    """Return the mapping of category keys to display labels."""
    return dict(CATEGORIES)


def get_template_count() -> dict:
    """Return a summary count of templates per category and total."""
    counts: dict[str, int] = {}
    for meta in TEMPLATE_REGISTRY.values():
        cat = meta["category"]
        counts[cat] = counts.get(cat, 0) + 1
    return {
        "total": len(TEMPLATE_REGISTRY),
        "by_category": {
            CATEGORIES.get(k, k): v for k, v in counts.items()
        },
    }
