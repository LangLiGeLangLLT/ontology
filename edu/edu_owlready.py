"""Build and infer an education ontology without requiring source instance data.

The default run creates only the ontology schema. Use ``--demo`` to add a
small, local fixture and demonstrate individual-level inference.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import owlrl
from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, XSD


EDU = Namespace("http://example.org/edu-ontology#")
ROOT = Path(__file__).resolve().parent.parent


def _label(graph: Graph, resource, text: str) -> None:
    graph.add((resource, RDFS.label, Literal(text, lang="zh")))


def build_ontology(include_demo_data: bool = False) -> Graph:
    """Create the education schema and optionally add a tiny demonstration fixture."""
    graph = Graph()
    graph.bind("edu", EDU)
    graph.bind("owl", OWL)
    graph.bind("rdfs", RDFS)
    graph.bind("xsd", XSD)

    ontology = EDU["Ontology"]
    graph.add((ontology, RDF.type, OWL.Ontology))
    _label(graph, ontology, "教育领域本体")
    graph.add(
        (
            ontology,
            RDFS.comment,
            Literal(
                "不依赖具体实例数据的教育领域概念模型；实例数据可在后续接入。",
                lang="zh",
            ),
        )
    )

    classes = {
        "Entity": "教育实体",
        "Person": "人员",
        "Learner": "学习者",
        "Student": "学生",
        "Teacher": "教师",
        "LearningResource": "学习资源",
        "Course": "课程",
        "Program": "培养方案",
        "Organization": "教育组织",
        "School": "学校",
    }
    for name, label in classes.items():
        resource = EDU[name]
        graph.add((resource, RDF.type, OWL.Class))
        graph.add((resource, RDFS.subClassOf, EDU.Entity))
        _label(graph, resource, label)

    subclass_pairs = {
        "Person": "Entity",
        "Learner": "Person",
        "Student": "Learner",
        "Teacher": "Person",
        "LearningResource": "Entity",
        "Course": "LearningResource",
        "Program": "LearningResource",
        "Organization": "Entity",
        "School": "Organization",
    }
    for child, parent in subclass_pairs.items():
        graph.add((EDU[child], RDFS.subClassOf, EDU[parent]))

    object_properties = {
        "hasTeacher": ("课程授课教师", "Course", "Teacher"),
        "hasStudent": ("课程学生", "Course", "Student"),
        "partOfProgram": ("所属培养方案", "Course", "Program"),
        "offeredBy": ("开设组织", "Course", "Organization"),
        "teaches": ("教授课程", "Teacher", "Course"),
        "enrolledIn": ("选修课程", "Student", "Course"),
        "hasPrerequisite": ("先修课程", "Course", "Course"),
    }
    for name, (label, domain, range_) in object_properties.items():
        prop = EDU[name]
        graph.add((prop, RDF.type, OWL.ObjectProperty))
        graph.add((prop, RDFS.domain, EDU[domain]))
        graph.add((prop, RDFS.range, EDU[range_]))
        _label(graph, prop, label)

    graph.add((EDU.teaches, OWL.inverseOf, EDU.hasTeacher))
    graph.add((EDU.enrolledIn, OWL.inverseOf, EDU.hasStudent))

    data_properties = {
        "name": ("名称", "Entity", XSD.string),
        "courseCode": ("课程代码", "Course", XSD.string),
        "credits": ("学分", "Course", XSD.decimal),
        "level": ("课程层次", "Course", XSD.string),
    }
    for name, (label, domain, range_) in data_properties.items():
        prop = EDU[name]
        graph.add((prop, RDF.type, OWL.DatatypeProperty))
        graph.add((prop, RDFS.domain, EDU[domain]))
        graph.add((prop, RDFS.range, range_))
        _label(graph, prop, label)

    if include_demo_data:
        course = EDU.DemoCourse
        teacher = EDU.DemoTeacher
        student = EDU.DemoStudent
        graph.add((course, RDF.type, EDU.Course))
        graph.add((teacher, RDF.type, EDU.Teacher))
        graph.add((student, RDF.type, EDU.Student))
        graph.add((course, EDU.name, Literal("人工智能导论", lang="zh")))
        graph.add((course, EDU.hasTeacher, teacher))
        graph.add((course, EDU.hasStudent, student))

    return graph


def infer(graph: Graph) -> Graph:
    """Materialize OWL-RL consequences in-place and return the graph."""
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)
    return graph


def main() -> None:
    parser = argparse.ArgumentParser(description="构建并推理教育领域本体")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="加入少量演示实例，验证课程关系的个体级推理",
    )
    args = parser.parse_args()

    graph = build_ontology(include_demo_data=args.demo)
    before = len(graph)
    infer(graph)
    suffix = "_demo" if args.demo else "_schema"
    ontology_path = ROOT / f"edu_ontology{suffix}.ttl"
    inferred_path = ROOT / f"edu_inferred{suffix}.ttl"
    graph.serialize(ontology_path, format="turtle")
    graph.serialize(inferred_path, format="turtle")

    inferred_types = sorted(
        str(row.class_name).split("#")[-1]
        for row in graph.query(
            """
            SELECT DISTINCT ?class_name WHERE {
                edu:Student rdfs:subClassOf+ ?class_name .
            }
            """,
            initNs={"edu": EDU, "rdfs": RDFS},
        )
    )
    print(f"推理前三元组：{before}")
    print(f"推理后三元组：{len(graph)}")
    print(f"Student 可推断为：{', '.join(inferred_types)}")
    print(f"本体模型：{ontology_path}")
    print(f"推理结果：{inferred_path}")


if __name__ == "__main__":
    main()