from ecom.build import build_ontology, infer
from ecom.query import query_agent_recommendation_context

graph = build_ontology(include_demo_instances=True)
infer(graph)

ctx = query_agent_recommendation_context(graph, "http://example.org/ecommerce#User_A")

print(ctx["context_for_agent"])
print(ctx["recommendations"])

prompt = f"""
你是一个电商推荐助手。
请基于用户历史和平台关系做推荐。

{ctx['context_for_agent']}
"""
