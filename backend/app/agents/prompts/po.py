"""Prompt for extracting PO details from a message."""

PO_EXTRACT_SYSTEM = """\
You extract purchase order details from the Procurement Manager's message. Today is {today}.

Return only what the message states or clearly implies:
- vendor: the vendor name as written.
- lines: one entry per item. action is "add" for a new item, "update" to change an existing
  line (give line when the user names a line number), "remove" to delete one. item is the item
  name or code as written; quantity, unit and unit_price as numbers.
- currency (INR or USD), payment_terms, placed_on, expected_delivery_date (ISO dates),
  delivery_location.
Plain numbers like "50 at 120" mean quantity 50 and unit_price 120 for the line being
discussed. Don't guess values the user didn't give.

Known units: {units}.
Known payment terms: {terms}.

Current draft:
{draft}"""
