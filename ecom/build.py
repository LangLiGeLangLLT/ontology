"""E-commerce ontology schema built with rdflib + OWL-RL.

Design goal:
- Model the relationship between User, Platform, Product and OrderRecord.
- Do not include operational order payloads such as amounts, timestamps, IDs,
  or any large dynamic order data in the ontology itself.
- Keep a generic relation layer that can be populated by downstream systems.
"""

from __future__ import annotations

from pathlib import Path

import owlrl
from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, XSD

ECOM = Namespace("http://example.org/ecommerce#")
ROOT = Path(__file__).resolve().parent


def _label(graph: Graph, resource, text: str) -> None:
    graph.add((resource, RDFS.label, Literal(text, lang="zh")))


def add_class(graph: Graph, uri, label: str, parent=None) -> None:
    graph.add((uri, RDF.type, OWL.Class))
    if parent is not None:
        graph.add((uri, RDFS.subClassOf, parent))
    _label(graph, uri, label)


def add_object_property(graph: Graph, uri, label: str, domain, range_) -> None:
    graph.add((uri, RDF.type, OWL.ObjectProperty))
    graph.add((uri, RDFS.domain, domain))
    graph.add((uri, RDFS.range, range_))
    _label(graph, uri, label)


def add_data_property(graph: Graph, uri, label: str, domain, range_type) -> None:
    graph.add((uri, RDF.type, OWL.DatatypeProperty))
    graph.add((uri, RDFS.domain, domain))
    graph.add((uri, RDFS.range, range_type))
    _label(graph, uri, label)


def build_ontology(include_demo_instances: bool = False) -> Graph:
    """Create the ontology schema and optionally add a tiny example graph.

    The schema models only relationship semantics. The demo instances are generic
    and intentionally omit any real transaction quantities or dynamic order
    payloads.
    """
    graph = Graph()
    graph.bind("ecom", ECOM)
    graph.bind("owl", OWL)
    graph.bind("rdfs", RDFS)
    graph.bind("rdf", RDF)
    graph.bind("xsd", XSD)

    ontology = ECOM["OrderRelationshipOntology"]
    graph.add((ontology, RDF.type, OWL.Ontology))
    graph.add(
        (
            ontology,
            RDFS.comment,
            Literal(
                "描述用户、平台、产品和订单之间的关系层，不包含具体订单金额、时间、数量等动态业务数据。",
                lang="zh",
            ),
        )
    )
    _label(graph, ontology, "电商订单关系本体")

    add_class(graph, ECOM.User, "用户")
    add_class(graph, ECOM.Platform, "平台")
    add_class(graph, ECOM.Product, "产品")
    add_class(graph, ECOM.OrderRecord, "订单记录")

    add_object_property(
        graph, ECOM.hasPlatform, "用户在平台的账号/平台关联", ECOM.User, ECOM.Platform
    )
    add_object_property(
        graph, ECOM.platformOf, "平台的用户关联", ECOM.Platform, ECOM.User
    )
    add_object_property(
        graph, ECOM.hasOrder, "用户持有的订单记录", ECOM.User, ECOM.OrderRecord
    )
    add_object_property(
        graph, ECOM.buyerOf, "订单记录对应的购买者", ECOM.OrderRecord, ECOM.User
    )
    add_object_property(
        graph, ECOM.orderPlatform, "订单记录对应的平台", ECOM.OrderRecord, ECOM.Platform
    )
    add_object_property(
        graph,
        ECOM.platformOfOrder,
        "平台对应的订单记录",
        ECOM.Platform,
        ECOM.OrderRecord,
    )
    add_object_property(
        graph,
        ECOM.includesProduct,
        "订单记录包含的产品",
        ECOM.OrderRecord,
        ECOM.Product,
    )
    add_object_property(
        graph,
        ECOM.productInOrder,
        "产品出现在订单记录中",
        ECOM.Product,
        ECOM.OrderRecord,
    )
    add_object_property(
        graph, ECOM.soldOnPlatform, "产品在某平台销售", ECOM.Product, ECOM.Platform
    )
    add_object_property(
        graph, ECOM.platformSellsProduct, "平台销售的产品", ECOM.Platform, ECOM.Product
    )

    graph.add((ECOM.hasPlatform, OWL.inverseOf, ECOM.platformOf))
    graph.add((ECOM.hasOrder, OWL.inverseOf, ECOM.buyerOf))
    graph.add((ECOM.orderPlatform, OWL.inverseOf, ECOM.platformOfOrder))
    graph.add((ECOM.includesProduct, OWL.inverseOf, ECOM.productInOrder))
    graph.add((ECOM.soldOnPlatform, OWL.inverseOf, ECOM.platformSellsProduct))

    add_data_property(graph, ECOM.name, "名称", ECOM.User, XSD.string)
    add_data_property(graph, ECOM.platformName, "平台名称", ECOM.Platform, XSD.string)
    add_data_property(graph, ECOM.productName, "产品名称", ECOM.Product, XSD.string)

    if include_demo_instances:
        # These are abstract examples only; they intentionally avoid actual order
        # numbers, payment amounts, timestamps, or any real customer transaction data.
        user1 = ECOM["User_A"]
        user2 = ECOM["User_B"]
        platform1 = ECOM["Platform_Amazon"]
        platform2 = ECOM["Platform_Taobao"]
        platform3 = ECOM["Platform_JD"]
        product1 = ECOM["Product_Smartphone"]
        product2 = ECOM["Product_Shoes"]
        product3 = ECOM["Product_Laptop"]
        order1 = ECOM["OrderRecord_1"]
        order2 = ECOM["OrderRecord_2"]

        for resource in [
            user1,
            user2,
            platform1,
            platform2,
            platform3,
            product1,
            product2,
            product3,
            order1,
            order2,
        ]:
            graph.add((resource, RDF.type, OWL.NamedIndividual))

        graph.add((user1, RDF.type, ECOM.User))
        graph.add((user2, RDF.type, ECOM.User))
        graph.add((platform1, RDF.type, ECOM.Platform))
        graph.add((platform2, RDF.type, ECOM.Platform))
        graph.add((platform3, RDF.type, ECOM.Platform))
        graph.add((product1, RDF.type, ECOM.Product))
        graph.add((product2, RDF.type, ECOM.Product))
        graph.add((product3, RDF.type, ECOM.Product))
        graph.add((order1, RDF.type, ECOM.OrderRecord))
        graph.add((order2, RDF.type, ECOM.OrderRecord))

        graph.add((user1, ECOM.hasPlatform, platform1))
        graph.add((user1, ECOM.hasPlatform, platform2))
        graph.add((user2, ECOM.hasPlatform, platform3))

        graph.add((user1, ECOM.hasOrder, order1))
        graph.add((user2, ECOM.hasOrder, order2))

        graph.add((order1, ECOM.buyerOf, user1))
        graph.add((order2, ECOM.buyerOf, user2))

        graph.add((order1, ECOM.orderPlatform, platform1))
        graph.add((order2, ECOM.orderPlatform, platform2))

        graph.add((order1, ECOM.includesProduct, product1))
        graph.add((order2, ECOM.includesProduct, product2))

        graph.add((product1, ECOM.soldOnPlatform, platform1))
        graph.add((product2, ECOM.soldOnPlatform, platform2))
        graph.add((product3, ECOM.soldOnPlatform, platform3))

        graph.add((user1, ECOM.name, Literal("用户A", lang="zh")))
        graph.add((user2, ECOM.name, Literal("用户B", lang="zh")))
        graph.add((platform1, ECOM.platformName, Literal("Amazon", lang="en")))
        graph.add((platform2, ECOM.platformName, Literal("淘宝", lang="zh")))
        graph.add((platform3, ECOM.platformName, Literal("京东", lang="zh")))
        graph.add((product1, ECOM.productName, Literal("智能手机", lang="zh")))
        graph.add((product2, ECOM.productName, Literal("运动鞋", lang="zh")))
        graph.add((product3, ECOM.productName, Literal("笔记本电脑", lang="zh")))

    return graph


def infer(graph: Graph) -> Graph:
    """Materialize OWL-RL consequences in place."""
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)
    return graph


def main() -> None:
    graph = build_ontology(include_demo_instances=False)
    infer(graph)

    ttl_path = ROOT / "ecommerce_order_ontology.ttl"
    inferred_path = ROOT / "ecommerce_order_inferred.ttl"
    graph.serialize(destination=ttl_path, format="turtle")
    graph.serialize(destination=inferred_path, format="turtle")

    print(f"Ontology saved to: {ttl_path}")
    print(f"Inferred graph saved to: {inferred_path}")
    print(f"Triples count: {len(graph)}")


if __name__ == "__main__":
    main()
