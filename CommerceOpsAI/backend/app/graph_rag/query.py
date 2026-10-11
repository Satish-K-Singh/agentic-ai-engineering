import networkx as nx
from langchain_core.messages import HumanMessage, SystemMessage
from app.llm_client import summary_llm

def find_return_pattern(graph: nx.MultiDiGraph, sku: str, min_returns: int = 2) -> dict:
    """Cross-order return-pattern lookup: which customers have returned
    this SKU more than once, or how many total returns has it had."""
    product_node = f"product:{sku}"
    if product_node not in graph:
        return {"sku": sku, "customers_with_returns": [], "total_returns": 0}

    total_returns = 0
    customers_seen = {}
    for u, v, data in graph.edges(data=True):
        if v == product_node and data.get("relation") == "RETURNED":
            order_node = u
            total_returns += 1
            for cust, order, edge_data in graph.in_edges(order_node, data=True):
                if edge_data.get("relation") == "PLACED":
                    customers_seen[cust] = customers_seen.get(cust, 0) + 1

    flagged = [
        {"customer": cust, "return_count": count}
        for cust, count in customers_seen.items()
        if count >= min_returns
    ]
    return {"sku": sku, "customers_with_returns": flagged, "total_returns": total_returns}