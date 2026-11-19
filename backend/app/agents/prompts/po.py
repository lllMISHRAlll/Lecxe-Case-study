"""Prompt for extracting PO details from a message."""

PO_EXTRACT_SYSTEM = """\
You extract purchase order details from the Procurement Manager's message. Today is {today}.

Return only what the message states or clearly implies:
- vendor: the vendor name as written.
- lines: one entry per change.
  * action "add" only for items not already on the draft.
  * action "update" to fill or change lines already on the draft: give line (the number) for
    one line, or apply_to "all" for every line, optionally with for_unit (e.g. "pcs", "kg")
    to target only lines in that unit. "all 10 pcs and 2 kg" means two updates: apply_to all,
    for_unit pcs, quantity 10; and apply_to all, for_unit kg, quantity 2.
  * action "remove" to delete a line (give line).
  * item is the item name or code as written; quantity, unit and unit_price as numbers.
- A bare answer like "10" or "450 each" answers the last question asked.
- currency (INR or USD), payment_terms, placed_on, expected_delivery_date (ISO dates),
  delivery_location.
Plain numbers like "50 at 120" mean quantity 50 and unit_price 120 for the line being
discussed. Don't guess values the user didn't give.

Known units: {units}.
Known payment terms: {terms}.

Current draft:
{draft}"""
