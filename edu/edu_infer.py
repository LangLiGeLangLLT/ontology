from rdflib import Graph
import owlrl

# 加载上一节导出的教育本体
g = Graph()
g.parse("edu_ontology.ttl", format="turtle")

print("=== 推理前三元组数量：", len(g))

# OWL-RL推理，把推论直接加到图里
owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)

print("=== 推理后三元组数量：", len(g))

# SPARQL查询：找出所有Person（我们新增Person作为Teacher、Student的父类）
query = """
PREFIX edu: <http://example.org/edu-ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?inst WHERE {
    ?inst rdf:type edu:Person .
}
"""
print("\n=== OWL-RL推理查询结果 ===")
for row in g.query(query):
    print(row.inst)

# 保存推理后的完整图
g.serialize("edu_inferred.ttl", format="turtle")
print("\n推理结果保存到 edu_inferred.ttl")
