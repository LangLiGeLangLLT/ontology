"""Query the e-commerce ontology with SPARQL.

The ontology intentionally stores relationship structure only. Any real order
payload (amount, timestamp, item counts, order ids) should stay in the business
system and be linked dynamically rather than embedded in the ontology graph.
"""

from __future__ import annotations

from rdflib import Namespace

from ecom.build import ECOM, build_ontology, infer


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


if __name__ == "__main__":
    main()
