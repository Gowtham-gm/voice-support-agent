"""
Mock order data-access layer. Replace internals with real DB/API calls to your
order management service — the function signatures are what the LangChain tools
in app/llm/tools.py depend on, so keep them stable.
"""

_MOCK_ORDERS = {
    "ORD1001": {
        "order_id": "ORD1001",
        "status": "out_for_delivery",
        "eta_minutes": 12,
        "restaurant": "Spice Villa",
        "total": 24.50,
        "driver": "Rahul",
    },
    "ORD1002": {
        "order_id": "ORD1002",
        "status": "delivered",
        "eta_minutes": 0,
        "restaurant": "Burger Barn",
        "total": 15.75,
        "driver": "Ayesha",
    },
    "ORD1003": {
        "order_id": "ORD1003",
        "status": "preparing",
        "eta_minutes": 30,
        "restaurant": "Sushi Central",
        "total": 42.00,
        "driver": None,
    },
}


def get_order_status(order_id: str) -> dict:
    order = _MOCK_ORDERS.get(order_id.upper())
    if not order:
        return {"error": f"No order found with id {order_id}"}
    return order


def issue_refund(order_id: str, reason: str) -> dict:
    order = _MOCK_ORDERS.get(order_id.upper())
    if not order:
        return {"error": f"No order found with id {order_id}"}
    # In production: call payments service, verify eligibility, create refund record.
    refund_amount = round(order["total"] * 0.5, 2) if "late" in reason.lower() else order["total"]
    return {
        "order_id": order_id,
        "refund_amount": refund_amount,
        "status": "refund_initiated",
        "reason": reason,
    }


def get_menu(restaurant_name: str) -> dict:
    _MOCK_MENUS = {
        "spice villa": ["Butter Chicken - $12", "Paneer Tikka - $10", "Garlic Naan - $3"],
        "burger barn": ["Classic Burger - $8", "Cheese Fries - $5", "Milkshake - $4"],
        "sushi central": ["California Roll - $9", "Salmon Nigiri - $11", "Miso Soup - $4"],
    }
    items = _MOCK_MENUS.get(restaurant_name.lower())
    if not items:
        return {"error": f"No menu found for {restaurant_name}"}
    return {"restaurant": restaurant_name, "items": items}
