from ecom.query import query_agent_recommendation_context
from ecom.build import build_ontology, infer

graph = build_ontology(include_demo_instances=True)
infer(graph)

ctx = query_agent_recommendation_context(graph, "http://example.org/ecommerce#User_A")

prompt = f"""
你是一个电商推荐 agent。

请基于以下本体知识进行推荐：
{ctx['context_for_agent']}

请使用以下 reasoning：
{ctx['reasoning']['summary']}
{ctx['reasoning']['decision_logic']}

请按以下 todo 执行：
{ctx['plan_todo']}
"""
