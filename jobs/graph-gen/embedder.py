import asyncio
import voyageai
from models import Node


def _node_text(node: Node) -> str:
    """Build the text to embed for a node — type + subtype + label + description."""
    parts = []
    if node.metadata.get("subtype"):
        parts.append(node.metadata["subtype"])
    else:
        parts.append(node.type)
    parts.append(node.label)
    if node.description:
        parts.append(node.description)
    return " ".join(parts)


def _embed_sync(nodes: list[Node], api_key: str) -> list[Node]:
    client = voyageai.Client(api_key=api_key)
    texts = [_node_text(n) for n in nodes]
    result = client.embed(texts, model="voyage-3-lite", input_type="document")
    for node, emb in zip(nodes, result.embeddings):
        node.embedding = emb
    return nodes


async def embed_nodes(nodes: list[Node], api_key: str) -> list[Node]:
    """Batch-embed all nodes and attach vectors in-place. Returns the same list."""
    print(f"Embedding {len(nodes)} nodes via Voyage AI...")
    nodes = await asyncio.to_thread(_embed_sync, nodes, api_key)
    print("Embeddings done.")
    return nodes
