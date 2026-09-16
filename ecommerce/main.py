"""Build and reason over an e-commerce ontology without order instances.

The default run creates only the schema (TBox). HermiT can still classify
business concepts from restrictions and equivalent-class axioms. Use
``--demo`` to add a tiny synthetic fixture for individual-level inference.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from owlready2 import (
	DataProperty,
	FunctionalProperty,
	ObjectProperty,
	Ontology,
	Thing,
	get_ontology,
	sync_reasoner,
)


ONTOLOGY_IRI = "http://example.org/ecommerce#"
ROOT = Path(__file__).resolve().parent.parent


def build_ontology(include_demo_data: bool = False) -> Ontology:
	"""Build the e-commerce TBox and optionally add a minimal fixture."""
	ontology = get_ontology(ONTOLOGY_IRI)

	with ontology:
		class Entity(Thing):
			pass

		class Customer(Entity):
			pass

		class Product(Entity):
			pass

		class Order(Entity):
			pass

		class OrderLine(Entity):
			pass

		class Payment(Entity):
			pass

		class OrderStatus(Entity):
			pass

		class Pending(OrderStatus):
			pass

		class Paid(OrderStatus):
			pass

		class Shipped(OrderStatus):
			pass

		class hasCustomer(ObjectProperty):
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
			range = [OrderStatus]

		class name(DataProperty):
			domain = [Entity]
			range = [str]

		class orderNumber(DataProperty, FunctionalProperty):
			domain = [Order]
			range = [str]

		class quantity(DataProperty):
			domain = [OrderLine]
			range = [int]

		class amount(DataProperty):
			domain = [Order, Payment]
			range = [float]

		class ValidOrder(Order):
			equivalent_to = [Order & hasCustomer.some(Customer) & hasLine.some(OrderLine)]

		class PaidOrder(Order):
			equivalent_to = [Order & hasPayment.some(Payment) & hasStatus.some(Paid)]

		class FulfillableOrder(Order):
			equivalent_to = [ValidOrder & hasLine.only(OrderLine)]

		if include_demo_data:
			customer = Customer("demo_customer")
			product = Product("demo_product")
			line = OrderLine("demo_line")
			payment = Payment("demo_payment")
			order = Order("demo_order")
			paid = Paid("demo_paid_status")

			order.hasCustomer = [customer]
			order.hasLine = [line]
			order.hasPayment = [payment]
			order.hasStatus = [paid]
			line.lineProduct = [product]
			order.orderNumber = "DEMO-001"
			line.quantity = [1]
			payment.amount = [99.0]

	return ontology


def reason(ontology: Ontology) -> None:
	"""Run HermiT and materialize inferred class/property assertions."""
	with ontology:
		sync_reasoner([ontology], infer_property_values=True, debug=0)


def save_ontology(ontology: Ontology, *, asserted: bool) -> Path:
	suffix = "schema" if asserted else "inferred"
	output_path = ROOT / f"ecommerce_owlready_{suffix}.owl"
	ontology.save(file=str(output_path), format="rdfxml")
	return output_path


def main() -> None:
	parser = argparse.ArgumentParser(description="构建并使用 HermiT 推理电商本体")
	parser.add_argument(
		"--demo",
		action="store_true",
		help="加入最小合成订单，验证个体级 ValidOrder/PaidOrder 推理",
	)
	args = parser.parse_args()

	ontology = build_ontology(include_demo_data=args.demo)
	individual_count = len(list(ontology.individuals()))
	asserted_path = save_ontology(ontology, asserted=True)
	reason(ontology)

	print(f"实例数量：{individual_count}")
	for class_name in ("ValidOrder", "PaidOrder", "FulfillableOrder"):
		inferred_class = ontology[class_name]
		parents = sorted(parent.name for parent in inferred_class.ancestors())
		print(f"{class_name} 的推理祖先类：{', '.join(parents)}")

	if args.demo:
		demo_order = ontology.demo_order
		types = sorted(item.name for item in demo_order.is_a)
		print(f"demo_order 的推断类型：{', '.join(types)}")

	inferred_path = save_ontology(ontology, asserted=False)
	print(f"声明本体：{asserted_path}")
	print(f"HermiT 推理结果：{inferred_path}")


if __name__ == "__main__":
	main()
