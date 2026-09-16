"""Build and reason over an education ontology with Owlready2 and HermiT.

This example deliberately contains no named individuals.  The ontology is
still useful because its classes, properties, restrictions, and equivalence
axioms describe the domain and allow HermiT to infer class-level knowledge.
"""

from __future__ import annotations

from pathlib import Path

from owlready2 import (
	DataProperty,
	FunctionalProperty,
	Ontology,
	Thing,
	get_ontology,
	sync_reasoner,
)


ONTOLOGY_IRI = "http://example.org/education#"
ROOT = Path(__file__).resolve().parent.parent


def build_ontology() -> Ontology:
	"""Build only the schema (TBox); no education individuals are created."""
	ontology = get_ontology(ONTOLOGY_IRI)

	with ontology:
		class Entity(Thing):
			pass

		class Person(Entity):
			pass

		class Learner(Person):
			pass

		class Student(Learner):
			pass

		class Teacher(Person):
			pass

		class LearningResource(Entity):
			pass

		class Course(LearningResource):
			pass

		class Program(LearningResource):
			pass

		class Organization(Entity):
			pass

		class School(Organization):
			pass

		class hasTeacher(Course >> Teacher):
			inverse_property = None

		class teaches(Teacher >> Course):
			inverse_property = hasTeacher

		class hasStudent(Course >> Student):
			inverse_property = None

		class enrolledIn(Student >> Course):
			inverse_property = hasStudent

		class partOfProgram(Course >> Program):
			pass

		class offeredBy(Course >> Organization):
			pass

		class hasPrerequisite(Course >> Course):
			pass

		class name(DataProperty):
			domain = [Entity]
			range = [str]

		class courseCode(DataProperty, FunctionalProperty):
			domain = [Course]
			range = [str]

		class credits(DataProperty):
			domain = [Course]
			range = [float]

		class CourseWithTeacher(Course):
			equivalent_to = [Course & hasTeacher.some(Teacher)]

		class LearnerCourse(Course):
			equivalent_to = [Course & hasStudent.some(Student)]

		class ProgramCourse(Course):
			equivalent_to = [Course & partOfProgram.some(Program)]

	return ontology


def reason(ontology: Ontology) -> None:
	"""Run HermiT and materialize its inferred axioms in the ontology."""
	with ontology:
		sync_reasoner(
			[ontology],
			infer_property_values=True,
			debug=0,
		)


def save_ontology(ontology: Ontology, *, asserted: bool) -> Path:
	"""Save either the asserted schema or the schema after HermiT reasoning."""
	suffix = "schema" if asserted else "inferred"
	output_path = ROOT / f"edu_owlready_{suffix}.owl"
	ontology.save(file=str(output_path), format="rdfxml")
	return output_path


def main() -> None:
	ontology = build_ontology()
	individual_count = len(list(ontology.individuals()))
	declared_class_count = len(list(ontology.classes()))

	print(f"个体数量：{individual_count}（预期为 0）")
	print(f"声明的类数量：{declared_class_count}")
	asserted_path = save_ontology(ontology, asserted=True)
	reason(ontology)

	for class_name in ("CourseWithTeacher", "LearnerCourse", "ProgramCourse"):
		inferred_class = ontology[class_name]
		parents = sorted(parent.name for parent in inferred_class.ancestors())
		print(f"{class_name} 的推理祖先类：{', '.join(parents)}")

	inferred_path = save_ontology(ontology, asserted=False)
	print(f"推理后的 HermiT 本体：{inferred_path}")
	print(f"声明版本：{asserted_path}")


if __name__ == "__main__":
	main()
