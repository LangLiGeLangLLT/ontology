"""Build and reason over a customer-order ontology with sparse data.

The default mode deliberately creates no customer or order individuals.  The
schema still captures the direction of the relationship and lets HermiT
classify concepts from OWL restrictions.  ``--demo`` adds one synthetic
relationship only to demonstrate individual-level inverse-property inference.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from owlready2 import ObjectProperty, Ontology, Thing, get_ontology, sync_reasoner


ONTOLOGY_IRI = "http://example.org/ecommerce-sparse#"
OUTPUT_DIRECTORY = Path(__file__).resolve().parent


def build_ontology(include_demo_data: bool = False) -> Ontology:
    """Build the schema and, optionally, one non-production demo relation."""
    ontology = get_ontology(ONTOLOGY_IRI)

    with ontology:
        class Customer(Thing):
            pass

        class Order(Thing):
            pass

        class placesOrder(ObjectProperty):
            domain = [Customer]
            range = [Order]

        class hasCustomer(ObjectProperty):
            inverse_property = placesOrder
            domain = [Order]
            range = [Customer]

        class CustomerWithOrders(Customer):
            equivalent_to = [Customer & placesOrder.some(Order)]

        class OrderWithCustomer(Order):
            equivalent_to = [Order & hasCustomer.some(Customer)]

        if include_demo_data:
            customer = Customer("synthetic_customer")
            order = Order("synthetic_order")
            customer.placesOrder = [order]

    return ontology


def reason(ontology: Ontology) -> None:
    """Run HermiT and materialize inferred inverse-property values."""
    with ontology:
        sync_reasoner([ontology], infer_property_values=True, debug=0)


def save(ontology: Ontology, file_name: str) -> Path:
    """Save one RDF/XML artifact and return its path."""
    output_path = OUTPUT_DIRECTORY / file_name
    ontology.save(file=str(output_path), format="rdfxml")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="在实例数据稀缺时构建客户-订单本体并使用 HermiT 推理"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="加入一条合成关系，验证逆属性的个体级推理",
    )
    args = parser.parse_args()

    ontology = build_ontology(include_demo_data=args.demo)
    asserted_path = save(ontology, "customer_order_schema.owl")
    reason(ontology)

    print(f"实例数量：{len(list(ontology.individuals()))}")
    print("关系方向：Customer --placesOrder--> Order")
    print("逆关系：Order --hasCustomer--> Customer")
    print(
        "类级推理：CustomerWithOrders ≡ Customer 且至少有一个 Order，"
        "OrderWithCustomer ≡ Order 且至少有一个 Customer"
    )

    if args.demo:
        synthetic_order = ontology.synthetic_order
        customers = [item.name for item in synthetic_order.hasCustomer]
        print(f"synthetic_order 的推断客户：{', '.join(customers)}")

    inferred_path = save(ontology, "customer_order_inferred.owl")
    print(f"声明本体：{asserted_path}")
    print(f"HermiT 推理结果：{inferred_path}")


if __name__ == "__main__":
    main()