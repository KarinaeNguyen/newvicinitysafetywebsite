## Plan: POS Sales Receipt Workflow Upgrade

This plan redesigns POS Sales entry to match your receipt-style flow while keeping control strict and reliable: always approval-first, new receipt data model, customer profile creation/matching with review flags, and PDF export in a simpler but layout-consistent style. The implementation will separate receipt header/lines from legacy Sales rows, then only post into Sales after Level 2/3/4 approval. Customer matching will flag potential duplicates when at least two fields match (phone, email, address). This avoids duplicate customer records and prevents incorrect auto-merges.

**Steps**
1. Add new schema for receipt workflow in db/FinancialDatabase.sql:
   - CustomerProfiles (name, phone, email, address, normalized fields, status)
   - SalesReceipts (receipt header: customer reference, sale date, tax rate, subtotal, service total, total, status)
   - SalesReceiptLines (line details: line type Product/Service, item name, unit price, quantity, line total, optional product sku)
   - CustomerMatchFlags (potential duplicate reviews for Level 2/3/4)
2. Add startup schema guard methods in app/finance_ui.py near existing ensure-table methods so missing tables/columns are created safely at runtime.
3. Replace current inline Sales entry panel (under Entry navigation) with a receipt-style form in app/finance_ui.py (inline entry panel section):
   - Customer section: name, phone, email, address
   - Product lines grid: product name, unit price, item count, total
   - Service lines grid: service name, unit price, item count, total
   - Tax section: GTGT tax rate input and computed totals
4. Add customer matching engine in app/finance_ui.py:
   - Normalize phone/email/address
   - Find existing profiles
   - If at least two fields match, create review flag and keep receipt pending
   - If no acceptable match, create new customer profile
5. Implement PDF export action in POS form using a reusable PDF module under scripts or a new utility module in app:
   - Use receipt-like layout from your image (simplified but structurally similar)
   - Include customer block, product/service tables, GTGT, adjustments, total
   - Save generated file path in receipt record for traceability
6. Change Submit for Sales Approval behavior:
   - Submit stores SalesReceipts and SalesReceiptLines as pending
   - Approval queue in app/finance_ui.py (approval panel and apply_pending_entry sections) is extended to show and approve receipt entries
   - On approval, write final rows into Sales table and mark receipt approved
7. Add strict approval gating for this flow:
   - No direct Sales write from new receipt form
   - Only approved receipts create Sales records
   - Audit all approve/reject actions with user level and reason
8. Update POS docs and permission test guide:
   - docs/SYSTEM_README.md
   - docs/PERMISSION_TEST_GUIDE.md
   - Include customer-match flag workflow and approval-completion behavior

**Verification**
- Form validation: required customer fields, valid GTGT rate, line totals and grand total correctness.
- Matching validation: at least two-field match creates review flag and approval visibility.
- Approval validation: before approval, no new Sales rows; after approval, Sales rows are created correctly.
- PDF validation: exported receipt includes all sections and computed totals.
- Role validation: Level 2/3/4 can submit and approve according to configured permissions.

**Decisions**
- Approval mode: always pending first, then enter system after approval.
- Data model: new receipt header and line tables.
- Customer logic: create profile if new; flag potential duplicate when at least two fields match.
- PDF style: close to provided receipt structure, but simpler/rigid for reliability.
