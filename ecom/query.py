"""Query the e-commerce ontology with SPARQL.

This file provides both generic ontology queries and an agent-oriented query that
converts ontology facts into a compact context block suitable for prompt
injection into an LLM recommender.

The ontology intentionally stores relationship structure only. Any real order
payload (amount, timestamp, item counts, order ids) should stay in the business
system and be linked dynamically rather than embedded in the ontology graph.
"""

from __future__ import annotations

from typing import Any

from rdflib import URIRef
from rdflib.namespace import RDFS
from ecom.build import ECOM, build_ontology, infer


def _local_name(resource) -> str:
    value = str(resource)
    if "#" in value:
        return value.rsplit("#", 1)[1]
    return value.rstrip("/").rsplit("/", 1)[-1]


def _get_label(graph, resource) -> str:
    label_rows = graph.query(
        """
        SELECT ?label WHERE {
            <%s> rdfs:label ?label .
        }
        LIMIT 1
        """ % resource,
        initNs={"rdfs": RDFS},
    )
    for row in label_rows:
        if row.label:
            return str(row.label)
    return _local_name(resource)


def query_user_platform_relations(graph):
    return graph.query(
        """
        SELECT ?user ?platform WHERE {
            ?user a ecom:User ;
                  ecom:hasPlatform ?platform .
        }
        ORDER BY ?user
        """,
        initNs={"ecom": ECOM},
    )


def query_user_product_order_relations(graph):
    return graph.query(
        """
        SELECT ?user ?order ?platform ?product WHERE {
            ?user a ecom:User ;
                  ecom:hasOrder ?order .
            ?order ecom:orderPlatform ?platform ;
                   ecom:includesProduct ?product .
        }
        ORDER BY ?user ?order
        """,
        initNs={"ecom": ECOM},
    )


def query_inverse_relations(graph):
    return graph.query(
        """
        SELECT ?user ?order ?platform ?product WHERE {
            ?order a ecom:OrderRecord ;
                   ecom:buyerOf ?user ;
                   ecom:orderPlatform ?platform ;
                   ecom:includesProduct ?product .
        }
        ORDER BY ?user ?order
        """,
        initNs={"ecom": ECOM},
    )


def query_agent_recommendation_context(
    graph, user_identifier: str | URIRef
) -> dict[str, Any]:
    """Build a recommendation context from ontology facts for an agent.

    The result is a dictionary that can be injected directly into the agent's
    prompt context. It includes the user, their platforms, previously related
    products, and a recommendation list computed from the ontology.
    """
    user_uri = (
        URIRef(user_identifier) if isinstance(user_identifier, str) else user_identifier
    )

    user_query = graph.query(
        """
        SELECT ?user WHERE {
            ?user a ecom:User .
            FILTER(STR(?user) = STR(?targetUser))
        }
        """,
        initNs={"ecom": ECOM},
        initBindings={"targetUser": user_uri},
    )
    if not user_query:
        raise ValueError(f"User not found in ontology: {user_identifier}")

    user = next(iter(user_query))["user"]
    user_label = _get_label(graph, user)

    platforms = [
        str(row.platform)
        for row in graph.query(
            """
            SELECT DISTINCT ?platform WHERE {
                <%s> ecom:hasPlatform ?platform .
            }
            ORDER BY ?platform
            """ % user,
            initNs={"ecom": ECOM},
        )
    ]

    historical_pairs = [
        {
            "order": str(row.order),
            "platform": str(row.platform),
            "product": str(row.product),
            "product_label": _get_label(graph, row.product),
            "platform_label": _get_label(graph, row.platform),
        }
        for row in graph.query(
            """
            SELECT DISTINCT ?order ?platform ?product WHERE {
                <%s> ecom:hasOrder ?order .
                ?order ecom:orderPlatform ?platform ;
                       ecom:includesProduct ?product .
            }
            ORDER BY ?order
            """ % user,
            initNs={"ecom": ECOM},
        )
    ]
    purchased_products = {item["product"] for item in historical_pairs}

    recommendations = []
    for platform in platforms:
        for row in graph.query(
            """
            SELECT DISTINCT ?product WHERE {
                ?product a ecom:Product ;
                         ecom:soldOnPlatform <%s> .
            }
            ORDER BY ?product
            """ % platform,
            initNs={"ecom": ECOM},
        ):
            product_uri = str(row.product)
            if product_uri in purchased_products:
                continue
            recommendations.append(
                {
                    "product": product_uri,
                    "product_label": _get_label(graph, row.product),
                    "platform": platform,
                    "platform_label": _get_label(graph, URIRef(platform)),
                    "reason": "用户已关联该平台，且该产品在该平台上销售，但该用户尚未在本体中体现购买记录",
                }
            )

    context_text = (
        f"User: {user_label}\n"
        f"Platforms: {', '.join(_get_label(graph, URIRef(p)) for p in platforms) if platforms else 'No platform linkage'}\n"
        f"Historical products: {', '.join(item['product_label'] for item in historical_pairs) if historical_pairs else 'No historical product linkage'}\n"
        f"Recommended products: {', '.join(item['product_label'] for item in recommendations) if recommendations else 'No product recommendation available'}"
    )

    return {
        "user": {"uri": str(user), "label": user_label},
        "platforms": [
            {"uri": platform, "label": _get_label(graph, URIRef(platform))}
            for platform in platforms
        ],
        "historical_products": historical_pairs,
        "recommendations": recommendations,
        "context_for_agent": context_text,
    }


def main() -> None:
    graph = build_ontology(include_demo_instances=True)
    infer(graph)

    print("=== 用户-平台关系 ===")
    for row in query_user_platform_relations(graph):
        print(f"{row.user} -> {row.platform}")

    print("\n=== 用户-订单-平台-产品关系 ===")
    for row in query_user_product_order_relations(graph):
        print(f"{row.user} -> {row.order} -> {row.platform} -> {row.product}")

    print("\n=== 反向关系推理 ===")
    for row in query_inverse_relations(graph):
        print(
            f"{row.user} bought through {row.platform} and got {row.product} in {row.order}"
        )

    print("\n=== Agent 推荐上下文 ===")
    context = query_agent_recommendation_context(
        graph, "http://example.org/ecommerce#User_A"
    )
    print(context["context_for_agent"])


if __name__ == "__main__":
    main()
