from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services import customer_service, order_service


class OrderStatusInput(BaseModel):
    order_id: str = Field(description="The order id, e.g. ORD1001")


class RefundInput(BaseModel):
    order_id: str = Field(description="The order id, e.g. ORD1001")
    reason: str = Field(description="Why the customer is requesting a refund")


class MenuInput(BaseModel):
    restaurant_name: str = Field(description="Name of the restaurant")


class EscalateInput(BaseModel):
    session_id: str = Field(description="Current support session id")
    summary: str = Field(description="Short summary of the customer's issue for the human agent")


def build_tools(session_id: str) -> list[StructuredTool]:
    """Build the LangChain tool set. session_id is closed over for escalation context."""

    def _order_status(order_id: str) -> dict:
        return order_service.get_order_status(order_id)

    def _issue_refund(order_id: str, reason: str) -> dict:
        return order_service.issue_refund(order_id, reason)

    def _menu_lookup(restaurant_name: str) -> dict:
        return order_service.get_menu(restaurant_name)

    def _escalate(session_id_arg: str, summary: str) -> dict:
        return customer_service.escalate_to_human(session_id_arg or session_id, summary)

    return [
        StructuredTool.from_function(
            func=_order_status,
            name="order_status",
            description="Look up the live status, ETA, restaurant and total for an order id.",
            args_schema=OrderStatusInput,
        ),
        StructuredTool.from_function(
            func=_issue_refund,
            name="issue_refund",
            description="Initiate a refund for an order given a reason. Returns the exact refund amount.",
            args_schema=RefundInput,
        ),
        StructuredTool.from_function(
            func=_menu_lookup,
            name="menu_lookup",
            description="Fetch the menu items and prices for a restaurant by name.",
            args_schema=MenuInput,
        ),
        StructuredTool.from_function(
            func=_escalate,
            name="escalate_to_human",
            description="Escalate the conversation to a human support agent, creating a ticket.",
            args_schema=EscalateInput,
        ),
    ]
