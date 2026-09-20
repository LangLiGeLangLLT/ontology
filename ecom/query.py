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
    """Build a recommendation context and reasoning for an agent.

    The result is a dictionary that can be injected directly into the agent's
    prompt context. It includes both factual context and the reasoning behind the
    plan, plus a todo list the agent can consume during planning.
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

    platform_labels = [
        _get_label(graph, URIRef(platform)) for platform in platforms
    ]
    historical_labels = [item["product_label"] for item in historical_pairs]
    recommendation_labels = [item["product_label"] for item in recommendations]

    reasoning = {
        "summary": (
            f"用户 {user_label} 与 {', '.join(platform_labels) if platform_labels else '未发现平台关联'} 建立了平台关系，"
            f"并且历史订单中关联了 {', '.join(historical_labels) if historical_labels else '无历史产品记录'}。"
            f"因此可根据“用户->平台”和“订单->产品”的本体关系，为其在已关联平台上推荐未购买过的产品。"
        ),
        "facts": [
            {
                "type": "platform_link",
                "statement": f"{user_label} hasPlatform {', '.join(platform_labels) if platform_labels else 'None'}",
            },
            {
                "type": "purchase_history",
                "statement": (
                    f"{user_label} has historical order links to "
                    f"{', '.join(historical_labels) if historical_labels else 'no product'}"
                ),
            },
            {
                "type": "candidate_recommendation",
                "statement": (
                    f"Products available on the user's platforms but not yet in purchase history: "
                    f"{', '.join(recommendation_labels) if recommendation_labels else 'None'}"
                ),
            },
        ],
        "decision_logic": [
            "通过 hasPlatform 推断用户和平台之间的关联关系。",
            "通过 hasOrder -> orderPlatform -> includesProduct 推断用户的购买历史和产品关联。",
            "通过 soldOnPlatform 过滤出同一平台上已售卖但未被用户购买过的候选产品。",
            "将这些候选产品作为推荐对象，而不直接使用具体订单明细数据。",
        ],
        "ontology_evidence": {
            "relations_used": [
                "ecom:hasPlatform",
                "ecom:hasOrder",
                "ecom:orderPlatform",
                "ecom:includesProduct",
                "ecom:soldOnPlatform",
            ],
            "inference_rule": "根据用户平台关联和历史订单关系，发现同平台下未购买但可推荐的产品。",
        },
    }

    plan_todo = [
        {
            "step": 1,
            "title": "Identify user-platform linkage",
            "reason": "Confirm the user is associated with the relevant marketplace(s) before recommendation.",
        },
        {
            "step": 2,
            "title": "Inspect historical orders and products",
            "reason": "Use OrderRecord relationships to learn what the user has already purchased and avoid duplicates.",
        },
        {
            "step": 3,
            "title": "Find candidate products on the same platform",
            "reason": "Recommend products sold on the same platform but absent from the user's historical purchase graph.",
        },
        {
            "step": 4,
            "title": "Construct final recommendation response",
            "reason": "Format the ontology-derived evidence into a concise agent response with reasoning and suggested next actions.",
        },
    ]

    context_text = (
        f"User: {user_label}\n"
        f"Platforms: {', '.join(platform_labels) if platform_labels else 'No platform linkage'}\n"
        f"Historical products: {', '.join(historical_labels) if historical_labels else 'No historical product linkage'}\n"
        f"Recommended products: {', '.join(recommendation_labels) if recommendation_labels else 'No product recommendation available'}\n\n"
        f"Reasoning: {reasoning['summary']}"
    )

    return {
        "user": {"uri": str(user), "label": user_label},
        "platforms": [
            {"uri": platform, "label": _get_label(graph, URIRef(platform))}
            for platform in platforms
        ],
        "historical_products": historical_pairs,
        "recommendations": recommendations,
        "reasoning": reasoning,
        "plan_todo": plan_todo,
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

    print("\n=== Agent Reasoning ===")
    for item in context["reasoning"]["facts"]:
        print(f"- {item['type']}: {item['statement']}")

    print("\n=== Plan Todo ===")
    for item in context["plan_todo"]:
        print(f"{item['step']}. {item['title']} -> {item['reason']}")


if __name__ == "__main__":
    main()
