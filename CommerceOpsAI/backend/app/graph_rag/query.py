"""Graph traversal and LLM summarization utilities for customer histories."""

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
import networkx as nx

from app.llm_client import summary_llm

# Edge and node attribute constants
_RELATION_RETURNED = "RETURNED"
_RELATION_PLACED = "PLACED"

_NODE_TYPE_ORDER = "Order"
_NODE_TYPE_TICKET = "Ticket"
_NODE_TYPE_PRODUCT = "Product"

_SYSTEM_PROMPT = (
    "Answer the question using ONLY the structured graph-traversal data "
    "provided. Do not speculate beyond what the data shows."
)


def find_return_pattern(
    graph: nx.MultiDiGraph,
    sku: str,
    min_returns: int = 2,
) -> dict[str, Any]:
    """Finds cross-order return patterns for a given SKU.

    Identifies which customers have returned the SKU multiple times and
    computes the total number of returns across all orders.

    Args:
        graph: Directed multigraph containing products, orders, and customers.
        sku: Unique stock keeping unit identifier for the target product.
        min_returns: Threshold count to flag customers with repeated returns.

    Returns:
        A dictionary containing the SKU, customers meeting the return threshold,
        and total return occurrences.
    """
    product_node = f"product:{sku}"
    if product_node not in graph:
        return {
            "sku": sku,
            "customers_with_returns": [],
            "total_returns": 0,
        }

    total_returns = 0
    customers_seen: defaultdict[str, int] = defaultdict(int)

    for u, v, data in graph.edges(data=True):
        if v == product_node and data.get("relation") == _RELATION_RETURNED:
            order_node = u
            total_returns += 1
            for cust, _, edge_data in graph.in_edges(order_node, data=True):
                if edge_data.get("relation") == _RELATION_PLACED:
                    customers_seen[cust] += 1

    flagged = [
        {"customer": cust, "return_count": count}
        for cust, count in customers_seen.items()
        if count >= min_returns
    ]

    return {
        "sku": sku,
        "customers_with_returns": flagged,
        "total_returns": total_returns,
    }


def customer_history(
    graph: nx.MultiDiGraph,
    customer_id: str,
    max_hops: int = 2,
) -> dict[str, Any]:
    """Retrieves order and support ticket history for a customer via graph traversal.

    Traverses local neighborhood entities to surface related orders, support
    tickets, and associated products.

    Args:
        graph: Directed multigraph containing customer interaction topology.
        customer_id: Unique customer identifier.
        max_hops: Neighborhood traversal radius centered on the customer.

    Returns:
        A dictionary containing the customer ID, matched orders, tickets, and
        all products involved in the subgraph.
    """
    customer_node = f"customer:{customer_id}"
    if customer_node not in graph:
        return {
            "customer_id": customer_id,
            "orders": [],
            "tickets": [],
            "products_involved": [],
        }

    neighborhood = nx.ego_graph(
        graph,
        customer_node,
        radius=max_hops,
        undirected=True,
    )
    orders: list[dict[str, Any]] = []
    tickets: list[dict[str, Any]] = []
    products: set[str] = set()

    for node, data in neighborhood.nodes(data=True):
        node_type = data.get("node_type")
        if node_type == _NODE_TYPE_ORDER:
            orders.append({"order": node, "status": data.get("status")})
        elif node_type == _NODE_TYPE_TICKET:
            tickets.append({
                "ticket": node,
                "category": data.get("category"),
                "status": data.get("status"),
            })
        elif node_type == _NODE_TYPE_PRODUCT:
            products.append(node)

    return {
        "customer_id": customer_id,
        "orders": orders,
        "tickets": tickets,
        "products_involved": sorted(products),
    }


def multi_hop_query(
    graph: nx.MultiDiGraph,
    question: str,
    seed_type: str,
    seed_id: str,
) -> dict[str, Any]:
    """Dispatches a graph traversal based on seed type and synthesizes an answer via LLM.

    Args:
        graph: The backing knowledge graph.
        question: User inquiry to answer.
        seed_type: Entity type to seed traversal ("product" or "customer").
        seed_id: Entity identifier for the seed.

    Returns:
        A dictionary containing the natural language answer and raw graph data.
    """
    dispatch_map = {
        "product": find_return_pattern,
        "customer": customer_history,
    }

    traversal_fn = dispatch_map.get(seed_type)
    raw: Mapping[str, Any] = traversal_fn(graph, seed_id) if traversal_fn else {}

    llm = summary_llm()
    resp = llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Question: {question}\n\nGraph traversal result: {raw}"
        ),
    ])

    return {"answer": resp.content, "raw_traversal": raw}