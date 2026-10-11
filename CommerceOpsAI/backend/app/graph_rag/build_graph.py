"""Module for building and persisting an e-commerce knowledge graph."""

import json
import logging
from typing import Any, Mapping, Optional

import networkx as nx

from app.config import settings
from app.db import get_conn

logger = logging.getLogger(__name__)


def build_knowledge_graph() -> nx.MultiDiGraph:
  """Constructs a directed multigraph representing e-commerce relationships.

  Queries the database for customers, products, orders, and tickets, and
  populates nodes and directed edges capturing entities and interactions.

  Returns:
      nx.MultiDiGraph: Populated multigraph containing customer, product,
      order, and support ticket relationships.
  """
  graph = nx.MultiDiGraph()

  with get_conn() as connection:
    customers = connection.execute("SELECT * FROM customers").fetchall()
    products = connection.execute("SELECT * FROM products").fetchall()
    orders = connection.execute("SELECT * FROM orders").fetchall()
    tickets = connection.execute("SELECT * FROM tickets").fetchall()

  for customer in customers:
    graph.add_node(
        f"customer:{customer['customer_id']}",
        node_type="Customer",
        name=customer["name"],
    )

  for product in products:
    graph.add_node(
        f"product:{product['sku']}",
        node_type="Product",
        name=product["name"],
        category=product["category"],
    )

  for order in orders:
    order_node = f"order:{order['order_id']}"
    graph.add_node(
        order_node,
        node_type="Order",
        status=order["status"],
        date=order["order_date"],
    )
    graph.add_edge(
        f"customer:{order['customer_id']}",
        order_node,
        relation="PLACED_ORDER",
    )
    graph.add_edge(
        order_node,
        f"product:{order['sku']}",
        relation="CONTAINS_PRODUCT",
    )

    if order["status"] == "returned":
      graph.add_edge(
          order_node,
          f"product:{order['sku']}",
          relation="RETURNED",
      )

  for ticket in tickets:
    ticket_node = f"ticket:{ticket['ticket_id']}"
    graph.add_node(
        ticket_node,
        node_type="Ticket",
        category=ticket["category"],
        status=ticket["status"],
    )
    graph.add_edge(
        f"customer:{ticket['customer_id']}",
        ticket_node,
        relation="FILED",
    )
    if ticket["order_id"]:
      graph.add_edge(ticket_node, f"order:{ticket['order_id']}", relation="ABOUT")

  return graph


def save_graph(
    graph: nx.MultiDiGraph,
    path: Optional[str] = None,
) -> None:
  """Serializes and saves the knowledge graph to a JSON file.

  Args:
      graph: The NetworkX multigraph to persist.
      path: Filepath where the JSON representation will be saved. Defaults
        to `settings.KNOWLEDGE_GRAPH_PATH` if None.
  """
  target_path = path or settings.KNOWLEDGE_GRAPH_PATH
  data: Mapping[str, Any] = nx.node_link_data(graph)

  with open(target_path, "w", encoding="utf-8") as file:
    json.dump(data, file, indent=4)


def load_knowledge_graph(path: Optional[str] = None) -> nx.MultiDiGraph:
  """Deserializes a knowledge graph from a JSON file.

  Args:
      path: Filepath to the serialized graph. Defaults to
        `settings.KNOWLEDGE_GRAPH_PATH` if None.

  Returns:
      nx.MultiDiGraph: The reconstructed NetworkX multigraph.
  """
  source_path = path or settings.KNOWLEDGE_GRAPH_PATH
  with open(source_path, "r", encoding="utf-8") as file:
    data = json.load(file)

  return nx.node_link_graph(
      data,
      edges="edges",
      multigraph=True,
      directed=True,
  )


def main() -> None:
  """Builds and serializes the knowledge graph."""
  logging.basicConfig(level=logging.INFO)
  logger.info("Building knowledge graph...")

  graph = build_knowledge_graph()
  save_graph(graph)

  logger.info(
      "Knowledge graph saved to %s",
      settings.KNOWLEDGE_GRAPH_PATH,
  )


    
 
  