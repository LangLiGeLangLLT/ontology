"""Concept-level TBox reasoning for a realistic e-commerce ontology.

This version intentionally contains no instance data. It shows how HermiT can
reason over business concepts such as repeat buyers, premium customers,
high-value orders, and risk flags using only class axioms, property
restrictions, inverse properties, and equivalence definitions.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from owlready2 import ObjectProperty, Ontology, Thing, get_ontology, sync_reasoner


ONTOLOGY_IRI = "http://example.org/ecommerce-business-tbox#"
OUTPUT_DIRECTORY = Path(__file__).resolve().parent


def build_ontology() -> Ontology:
    """Build a richer TBox that mirrors e-commerce business semantics."""
    ontology = get_ontology(ONTOLOGY_IRI)

    with ontology:
        class Entity(Thing):
            pass

        class Customer(Entity):
            pass

        class RetailCustomer(Customer):
            pass

        class BusinessCustomer(Customer):
            pass

        class Order(Entity):
            pass

        class PendingOrder(Order):
            pass

        class ValidOrder(Order):
            pass

        class PaidOrder(ValidOrder):
            pass

        class ShippedOrder(PaidOrder):
            pass

        class ReturnedOrder(Order):
            pass

        class HighValueOrder(Order):
            pass

        class BusinessOrder(Order):
            pass

        class Product(Entity):
            pass

        class OrderLine(Entity):
            pass

        class Payment(Entity):
            pass

        class Status(Entity):
            pass

        class Pending(Status):
            pass

        class Paid(Status):
            pass

        class Shipped(Status):
            pass

        class RiskFlag(Entity):
            pass

        class FrequentBuyer(Customer):
            pass

        class LoyalCustomer(Customer):
            pass

        class HighValueCustomer(Customer):
            pass

        class PreferredCustomer(Customer):
            pass

        class RiskCustomer(Customer):
            pass

        class placesOrder(ObjectProperty):
            domain = [Customer]
            range = [Order]

        class hasCustomer(ObjectProperty):
            inverse_property = placesOrder
            domain = [Order]
            range = [Customer]

        class hasLine(ObjectProperty):
            domain = [Order]
            range = [OrderLine]

        class lineProduct(ObjectProperty):
            domain = [OrderLine]
            range = [Product]

        class hasPayment(ObjectProperty):
            domain = [Order]
            range = [Payment]

        class hasStatus(ObjectProperty):
            domain = [Order]
            range = [Status]

        class hasRiskFlag(ObjectProperty):
            domain = [Customer]
            range = [RiskFlag]

        class CustomerWithOrders(Customer):
            equivalent_to = [Customer & placesOrder.some(Order)]

        class RepeatCustomer(Customer):
            equivalent_to = [Customer & placesOrder.min(2, Order)]

        class FrequentBuyerDefinition(FrequentBuyer):
            equivalent_to = [Customer & placesOrder.min(3, Order)]

        class LoyalCustomerDefinition(LoyalCustomer):
            equivalent_to = [
                RepeatCustomer & CustomerWithOrders & placesOrder.some(PaidOrder)
            ]

        class HighValueOrderDefinition(HighValueOrder):
            equivalent_to = [
                Order
                & hasLine.min(2, OrderLine)
                & hasPayment.some(Payment)
                & hasStatus.some(Paid)
            ]

        class HighValueCustomerDefinition(HighValueCustomer):
            equivalent_to = [
                Customer & placesOrder.some(HighValueOrderDefinition)
            ]

        class PreferredCustomerDefinition(PreferredCustomer):
            equivalent_to = [
                LoyalCustomerDefinition & HighValueCustomerDefinition
            ]

        class VIPCustomer(PreferredCustomer):
            equivalent_to = [
                PreferredCustomerDefinition
                & placesOrder.some(ShippedOrder)
                & placesOrder.some(HighValueOrderDefinition)
            ]

        class RiskCustomerDefinition(RiskCustomer):
            equivalent_to = [
                Customer
                & hasRiskFlag.some(RiskFlag)
                & placesOrder.some(ReturnedOrder)
            ]

        class BusinessOrderDefinition(BusinessOrder):
            equivalent_to = [
                Order
                & hasCustomer.some(BusinessCustomer)
                & hasLine.some(OrderLine)
            ]

        class BusinessCustomerDefinition(BusinessCustomer):
            equivalent_to = [
                BusinessCustomer & placesOrder.some(BusinessOrderDefinition)
            ]

        class ValidOrderDefinition(ValidOrder):
            equivalent_to = [
                Order
                & hasCustomer.some(Customer)
                & hasLine.some(OrderLine)
                & hasPayment.some(Payment)
            ]

        class PaidOrderDefinition(PaidOrder):
            equivalent_to = [Order & hasStatus.some(Paid)]

        class ShippedOrderDefinition(ShippedOrder):
            equivalent_to = [PaidOrderDefinition & hasStatus.some(Shipped)]

        class OrderWithCustomer(Order):
            equivalent_to = [Order & hasCustomer.some(Customer)]

        class PreferredButRiskyCustomer(Customer):
            equivalent_to = [PreferredCustomerDefinition & RiskCustomerDefinition]

    return ontology


def reason(ontology: Ontology) -> None:
    """Use HermiT to infer class relationships and subsumption."""
    with ontology:
        sync_reasoner([ontology], infer_property_values=True, debug=0)


def save(ontology: Ontology, file_name: str) -> Path:
    output_path = OUTPUT_DIRECTORY / file_name
    ontology.save(file=str(output_path), format="rdfxml")
    return output_path


def print_ancestors(label: str, concept: object) -> None:
    ancestors = sorted(parent.name for parent in concept.ancestors())
    print(f"{label}: {ancestors}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="电商业务概念性 TBox：不含实例数据，仅用于复杂语义推理"
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="输出更多关键概念的推理后祖先层次",
    )
    args = parser.parse_args()

    ontology = build_ontology()
    asserted_path = save(ontology, "customer_order_business_tbox.owl")
    reason(ontology)

    print("实例数量：0")
    print("关系方向：Customer --placesOrder--> Order")
    print("逆关系：Order --hasCustomer--> Customer")
    print("说明：此版本只演示真实业务概念的 TBox 推理，不包含客户、订单或商品实例数据")

    for label, concept in (
        ("RepeatCustomer", ontology.RepeatCustomer),
        ("LoyalCustomerDefinition", ontology.LoyalCustomerDefinition),
        ("HighValueOrderDefinition", ontology.HighValueOrderDefinition),
        ("HighValueCustomerDefinition", ontology.HighValueCustomerDefinition),
        ("PreferredCustomerDefinition", ontology.PreferredCustomerDefinition),
        ("VIPCustomer", ontology.VIPCustomer),
        ("RiskCustomerDefinition", ontology.RiskCustomerDefinition),
        ("PreferredButRiskyCustomer", ontology.PreferredButRiskyCustomer),
    ):
        print_ancestors(label, concept)

    if args.show_all:
        for label, concept in (
            ("CustomerWithOrders", ontology.CustomerWithOrders),
            ("OrderWithCustomer", ontology.OrderWithCustomer),
            ("ValidOrderDefinition", ontology.ValidOrderDefinition),
            ("ShippedOrderDefinition", ontology.ShippedOrderDefinition),
            ("BusinessOrderDefinition", ontology.BusinessOrderDefinition),
            ("BusinessCustomerDefinition", ontology.BusinessCustomerDefinition),
        ):
            print_ancestors(label, concept)

    inferred_path = save(ontology, "customer_order_business_tbox_inferred.owl")
    print(f"声明本体：{asserted_path}")
    print(f"HermiT 推理结果：{inferred_path}")


if __name__ == "__main__":
    main()
