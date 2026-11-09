"""What the AI is told about the database: each table, its columns, and the business definitions.

Short and exact on purpose. Most wrong answers in text-to-SQL come from a definition the model had to guess
("revenue" with or without refunds? "last quarter" of which year?), so those are spelled out here once.
"""
from .generate import TODAY

TABLES = {
    "customers": {
        "about": "One row per customer: people who buy online or subscribe (retail) and cafés (wholesale).",
        "columns": {
            "customer_id": "integer, primary key",
            "name": "text: a person's name, or a café's name for wholesale",
            "customer_type": "text: 'retail' or 'wholesale'",
            "city": "text", "state": "text: two-letter code",
            "region": "text: 'Northeast', 'Southeast', 'Midwest', 'Southwest' or 'West'",
            "signup_date": "date the customer signed up",
            "acquisition_channel": "text: 'organic', 'paid_search', 'social', 'referral' or 'wholesale_sales'",
        },
    },
    "products": {
        "about": "One row per product: coffees and brewing equipment.",
        "columns": {
            "product_id": "integer, primary key",
            "name": "text, unique, e.g. 'Morning Blend', 'Ethiopia Yirgacheffe 1kg', 'Burr Grinder'",
            "category": "text: 'blend', 'single_origin', 'decaf' or 'equipment'",
            "roast": "text: 'light', 'medium' or 'dark'; null for equipment",
            "bag_size_g": "integer: 340 or 1000 grams; null for equipment",
            "price": "numeric: current list price in US dollars",
            "unit_cost": "numeric: what one unit costs Fernwood, in US dollars",
            "launched_on": "date",
        },
    },
    "orders": {
        "about": "One row per order.",
        "columns": {
            "order_id": "integer, primary key",
            "customer_id": "integer, references customers",
            "order_date": "date",
            "channel": "text: 'web', 'subscription' or 'wholesale'",
            "discount_code": "text: 'WELCOME10' (10% off a first web order), 'HOLIDAY20' (20% off), or null",
            "status": "text: 'completed' or 'refunded'",
            "shipping_fee": "numeric: shipping charged, in US dollars (not part of revenue)",
        },
    },
    "order_items": {
        "about": "One row per product line in an order.",
        "columns": {
            "order_item_id": "integer, primary key",
            "order_id": "integer, references orders",
            "product_id": "integer, references products",
            "quantity": "integer: units (bags or items)",
            "unit_price": "numeric: price actually paid per unit, after any discount",
            "line_total": "numeric: quantity * unit_price, in US dollars",
        },
    },
    "subscriptions": {
        "about": "One row per coffee subscription. Its deliveries appear as orders with channel 'subscription'.",
        "columns": {
            "subscription_id": "integer, primary key",
            "customer_id": "integer, references customers",
            "plan": "text: 'monthly_1_bag', 'monthly_2_bags' or 'biweekly_1_bag'",
            "monthly_price": "numeric: US dollars per month",
            "started_on": "date",
            "cancelled_on": "date, or null while the subscription is still active",
        },
    },
    "marketing_spend": {
        "about": "Marketing spend: ONE ROW PER MONTH PER CHANNEL. Sum spend per month first before joining it to "
                 "monthly revenue, or every month is repeated once per channel.",
        "columns": {
            "month": "date: the first day of the month",
            "channel": "text: 'paid_search', 'social', 'email' or 'events'",
            "spend": "numeric: US dollars",
        },
    },
}

DEFINITIONS = f"""\
- Today is {TODAY.isoformat()}. The data runs from 2024-11-01 to 2026-10-31.
- Revenue = sum(order_items.line_total) for orders with status = 'completed'. Refunded orders and shipping fees
  are never revenue. "Sales" means revenue unless the question says units or orders.
- Units sold = sum(order_items.quantity) for completed orders.
- Counting orders ("how many orders", "orders that used a code") always counts status = 'completed' only,
  unless the question is about refunds.
- Gross profit = revenue - sum(order_items.quantity * products.unit_cost), completed orders only.
- Average order value = revenue / number of completed orders.
- Quarters and years are calendar ones: Q1 = Jan-Mar. "Last quarter" = Q3 2026, "this year" = 2026,
  "last year" = 2025, "last month" = October 2026, "this month" has no data yet.
- An active subscription has cancelled_on null. Churned = cancelled_on is not null.
- A new customer in a period = signup_date falls in that period.
- Product family names match every size: "Morning Blend products" or "Ethiopia Yirgacheffe" means
  name LIKE 'Morning Blend%' (the 340 g bag and the 1kg bag).
- Money is in US dollars."""


def describe() -> str:
    """The schema as the AI reads it."""
    parts = []
    for name, t in TABLES.items():
        cols = "\n".join(f"    {c}: {d}" for c, d in t["columns"].items())
        parts.append(f"fernwood.{name}: {t['about']}\n{cols}")
    return "\n\n".join(parts) + "\n\nDefinitions:\n" + DEFINITIONS
