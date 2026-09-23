"""Document generator — creates deal documents from Peña's templates.
Covers: LOI, NDA, Offer Letter, Due Diligence Checklist, Term Sheet.
"""
from __future__ import annotations

from typing import Any


def generate_loi(buyer: str, seller: str, target_name: str, 
                 purchase_price: str = "TBD", earnest_money: str = "TBD",
                 closing_days: int = 60, notes: str = "") -> str:
    """Generate Letter of Intent template based on Peña's methodology."""
    return f"""LETTER OF INTENT

Date: [DATE]

TO: {seller}
RE: Acquisition of {target_name}

Dear {seller},

This Letter of Intent ("LOI") sets forth the principal terms upon which {buyer} ("Buyer") would acquire {target_name} ("Company") from {seller} ("Seller").

1. PURCHASE PRICE
   Total Purchase Price: {purchase_price}
   Form of Consideration: [Cash / Seller Financing / Equity Mix]

2. EARNEST MONEY DEPOSIT
   Upon execution of definitive agreement: {earnest_money}

3. CLOSING
   Anticipated closing: {closing_days} days from definitive agreement
   Closing location: [City, State]

4. DUE DILIGENCE
   Buyer shall have [30] days to complete due diligence
   Access to: financial records, tax returns, contracts, employee lists, customer data

5. EXCLUSIVITY
   Seller agrees to negotiate exclusively with Buyer for [60] days from LOI execution

6. EXPENSES
   Each party bears its own expenses

7. GOVERNING LAW
   [State] law

8. NON-BINDING
   This LOI is non-binding except for Sections 5, 6, and 8

ACCEPTED AND AGREED:

___________________________
{buyer}

___________________________
{seller}

Date: _______________
"""


def generate_nda(buyer: str, seller: str, target_name: str) -> str:
    """Generate Non-Disclosure Agreement."""
    return f"""MUTUAL NON-DISCLOSURE AGREEMENT

This Agreement is entered into as of [DATE] by and between:

{buyer} ("Disclosing Party")
AND
{seller} ("Receiving Party")

1. PURPOSE
   The parties wish to evaluate a potential transaction involving {target_name}.

2. CONFIDENTIAL INFORMATION
   Includes: financial data, customer lists, employee information, trade secrets,
   business plans, and any proprietary information disclosed.

3. OBLIGATIONS
   - Use Confidential Information solely for evaluating the Transaction
   - Not disclose to third parties without written consent
   - Protect with same care as own confidential information

4. TERM
   This Agreement shall remain in effect for [2] years from the date of last disclosure.

5. NO LICENSE
   No license or right is granted to either party.

6. GOVERNING LAW
   [State] law.

IN WITNESS WHEREOF, the parties have executed this Agreement.

___________________________
{buyer}

___________________________
{seller}

Date: _______________
"""


def generate_offer_letter(buyer: str, seller: str, target_name: str,
                          offer_price: str = "TBD", terms: str = "TBD") -> str:
    """Generate formal offer letter."""
    return f"""OFFER TO PURCHASE

Date: [DATE]

{seller}
[Address]

RE: Offer to Purchase {target_name}

Dear {seller},

{buyer} is pleased to submit this offer to purchase {target_name} on the following terms:

PURCHASE PRICE: {offer_price}

TERMS: {terms}

This offer is contingent upon:
1. Satisfactory completion of due diligence
2. Execution of definitive purchase agreement
3. Securing financing (if applicable)
4. No material adverse change in the business

This offer shall remain open for acceptance until [DATE + 14 days].

We look forward to your favorable response.

Sincerely,

{buyer}
"""


def generate_term_sheet(buyer: str, seller: str, target_name: str,
                        valuation: str = "TBD", structure: str = "TBD") -> str:
    """Generate deal term sheet."""
    return f"""TERM SHEET — {target_name}

Date: [DATE]
Buyer: {buyer}
Seller: {seller}

1. VALUATION
   Enterprise Value: {valuation}
   Structure: {structure}

2. PAYMENT
   - Cash at Close: [%]
   - Seller Note: [%] over [X] years at [X]%
   - Equity Rollover: [%]

3. CONDITIONS PRECEDENT
   - Due diligence satisfaction
   - Financing commitment
   - No material adverse change
   - Key employee retention

4. CLOSING
   Target: [DATE]
   Location: [City, State]

5. EXCLUSIVITY
   [60]-day exclusivity period

6. EXPENSES
   Each party bears its own costs

This term sheet is non-binding except for Sections 5 and 6.

___________________________
{buyer}

___________________________
{seller}
"""


def generate_due_diligence_checklist(target_name: str) -> str:
    """Generate due diligence checklist based on Peña's investigation criteria."""
    return f"""DUE DILIGENCE CHECKLIST — {target_name}

[PEÑA METHOD: "Investigate Generalities, Then Specifics"]

I. CORPORATE RECORDS
   [ ] Articles of Incorporation
   [ ] Bylaws / Operating Agreement
   [ ] Minutes (last 3 years)
   [ ] Capitalization table
   [ ] List of all shareholders/members

II. FINANCIAL RECORDS
   [ ] Audited financials (3 years)
   [ ] Tax returns (3 years)
   [ ] Accounts receivable aging
   [ ] Accounts payable aging
   [ ] Revenue by customer (top 10)
   [ ] EBITDA adjustments
   [ ] Owner compensation analysis

III. OPERATIONS
   [ ] Customer list with contact info
   [ ] Employee roster + compensation
   [ ] Key contracts and commitments
   [ ] Insurance policies
   [ ] Equipment list and condition
   [ ] Facility leases

IV. LEGAL / COMPLIANCE
   [ ] Pending or threatened litigation
   [ ] Regulatory licenses and permits
   [ ] Environmental compliance
   [ ] HIPAA compliance (healthcare)
   [ ] State survey results
   [ ] Corporate integrity agreements

V. MARKET / COMPETITION
   [ ] Market share analysis
   [ ] Competitor landscape
   [ ] Referral source analysis
   [ ] Growth opportunities
   [ ] Threats and risks

VI. HUMAN CAPITAL
   [ ] Key person dependencies
   [ ] Employee satisfaction
   [ ] Turnover rates
   [ ] Non-compete agreements
   [ ] Benefit plans

NOTES:
- Red flags to investigate: _______________
- Key assumptions to verify: _______________
- Deal-breakers identified: _______________
"""


def generate_purchase_agreement_outline(buyer: str, seller: str, target_name: str) -> str:
    """Generate purchase agreement outline."""
    return f"""PURCHASE AGREEMENT OUTLINE — {target_name}

ARTICLE I — DEFINITIONS
ARTICLE II — PURCHASE AND SALE
   2.1 Purchase Price
   2.2 Payment Terms
   2.3 Adjustments
ARTICLE III — REPRESENTATIONS AND WARRANTIES OF SELLER
   3.1 Organization and Good Standing
   3.2 Financial Statements
   3.3 Title to Assets
   3.4 Litigation
   3.5 Compliance with Laws
   3.6 Employee Matters
   3.7 Tax Matters
ARTICLE IV — REPRESENTATIONS AND WARRANTIES OF BUYER
ARTICLE V — COVENANTS
   5.1 Conduct of Business Prior to Closing
   5.2 Access to Information
   5.3 Efforts to Consummate
ARTICLE VI — CONDITIONS TO CLOSING
   6.1 Conditions to Buyer's Obligations
   6.2 Conditions to Seller's Obligations
ARTICLE VII — INDEMNIFICATION
ARTICLE VIII — TERMINATION
ARTICLE IX — MISCELLANEOUS
   9.1 Governing Law
   9.2 Dispute Resolution
   9.3 Entire Agreement

SCHEDULES:
- Disclosure Schedule
- Financial Statements
- Material Contracts
- Employee List
- Customer List
"""
