import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

if __package__ in (None, ""):
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START, MessagesState
from langchain.messages import AIMessage, SystemMessage, HumanMessage

from ecom.build import build_ontology, infer
from ecom.query import query_agent_recommendation_context

load_dotenv()

model = ChatOpenAI(
    model=os.getenv("LLM_MODEL_ID"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
    temperature=0,
)


class State(MessagesState):
    plan: str = ""
    review_note: str = ""
    revision_count: int = 0
    task_list: list[dict] = []
    max_replans: int = 3
    replan_status: str = "pending"
    execution_results: list[dict] = []
    product_recommendation: str = ""
    execution_replan_reason: str = ""


def _resolve_user_identifier(messages):
    text = "\n".join(
        getattr(m, "content", "") for m in messages if hasattr(m, "content")
    )
    lowered = text.lower()
    if "user_b" in lowered or "user b" in lowered:
        return "http://example.org/ecommerce#User_B"
    if "user_a" in lowered or "user a" in lowered:
        return "http://example.org/ecommerce#User_A"
    return "http://example.org/ecommerce#User_A"


def _build_agent_recommendation_context(messages):
    graph = build_ontology(include_demo_instances=True)
    infer(graph)
    user_identifier = _resolve_user_identifier(messages)
    recommendation_context = query_agent_recommendation_context(graph, user_identifier)
    return json.dumps(
        {
            "user": recommendation_context["user"],
            "platforms": recommendation_context["platforms"],
            "historical_products": recommendation_context["historical_products"],
            "recommendations": recommendation_context["recommendations"],
            "reasoning": recommendation_context["reasoning"],
            "plan_todo": recommendation_context["plan_todo"],
            "context_for_agent": recommendation_context["context_for_agent"],
        },
        ensure_ascii=False,
        indent=2,
    )


def build_platform_subagents():
    return [
        {
            "name": "Platform_Amazon",
            "description": "Execute Amazon-specific workflow tasks such as catalog review, listing setup, pricing strategy, and fulfillment coordination.",
            "system_prompt": (
                "You are the Amazon execution specialist. Complete the assigned tasks for the Amazon channel, "
                "focus on practical commerce operations, and return a concise platform-specific execution summary."
            ),
        },
        {
            "name": "Platform_Taobao",
            "description": "Execute Taobao-specific workflow tasks such as storefront setup, content optimization, and customer engagement tasks.",
            "system_prompt": (
                "You are the Taobao execution specialist. Complete the assigned tasks for the Taobao channel, "
                "focus on local commerce execution, and return a concise platform-specific summary."
            ),
        },
        {
            "name": "Platform_JD",
            "description": "Execute JD-specific workflow tasks such as channel operations, inventory handling, and conversion optimization.",
            "system_prompt": (
                "You are the JD execution specialist. Complete the assigned tasks for the JD channel, "
                "focus on operational execution and order flow, and return a concise platform-specific summary."
            ),
        },
    ]


def build_product_agent():
    return {
        "name": "Product_Agent",
        "description": "Recommend related products after platform execution is complete. This agent runs serially and is separate from platform_parallel_batch execution.",
        "system_prompt": (
            "You are the product recommendation specialist. After platform execution has concluded, "
            "recommend the most relevant related products based on the user context, ontology evidence, and the platform outcomes. "
            "Keep the recommendation list concise and clearly explain why the products fit. "
            "This is a serial recommendation step and must not be grouped with platform_parallel_batch tasks."
        ),
    }


def _invoke_model(system_prompt: str, user_prompt: str):
    return model.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )


def _format_platform_results(results):
    payload = []
    for item in results:
        platform_name = item.get("platform", "unknown")
        content = item.get("result", "")
        payload.append(
            {
                "platform": platform_name,
                "status": "completed",
                "summary": content,
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _should_replan_from_subagent_results(results):
    failure_markers = [
        "fail",
        "failed",
        "no listing",
        "not found",
        "tbd",
        "partial",
        "pending",
        "needs review",
        "re-run candidate discovery",
        "requires runtime call",
        "no ontology linkage",
    ]
    combined = "\n".join(str(item.get("result", "")) for item in results).lower()
    triggers = [marker for marker in failure_markers if marker in combined]
    if triggers:
        return (
            "Subagent execution indicates incomplete or failed data; replan required to adjust the task list. "
            f"Detected markers: {', '.join(triggers[:5])}"
        )
    return ""


def _extract_task_items(plan_text: str):
    items = []
    for line in str(plan_text).splitlines():
        stripped = line.strip()
        if stripped.startswith("- [") or stripped.startswith("* ["):
            rest = stripped.split("]", 1)[1].strip()
            if rest:
                items.append(rest)
    if not items:
        return [
            {
                "id": "task-1",
                "title": str(plan_text).strip(),
                "priority": "P1",
                "subagent": "Platform_Amazon",
                "parallel_group": "platform_parallel_batch",
                "description": str(plan_text).strip(),
            }
        ]

    task_list = []
    for index, item in enumerate(items, start=1):
        title = item
        subagent = "Planner"
        parallel_group = None
        lower = item.lower()

        subagent_match = re.search(
            r"(Platform_Amazon|Platform_Taobao|Platform_JD|Product_Agent)",
            item,
            re.IGNORECASE,
        )
        if subagent_match:
            subagent = subagent_match.group(0)

        if re.search(r"parallel_group\s*[:=]\s*['\"]?platform_parallel_batch['\"]?", item, re.IGNORECASE):
            parallel_group = "platform_parallel_batch"
        elif "parallel_group: platform_parallel_batch" in lower or "parallel_group='platform_parallel_batch'" in lower:
            parallel_group = "platform_parallel_batch"

        if subagent == "Product_Agent":
            parallel_group = None

        task_list.append(
            {
                "id": f"task-{index}",
                "title": title,
                "priority": "P1",
                "subagent": subagent,
                "parallel_group": parallel_group,
                "description": title,
            }
        )
    return task_list


def _execute_platform_task(platform_name: str, plan_text: str):
    print(f"\n=== [Subagent Debug] Invoking {platform_name} ===")
    print(f"[Subagent Debug] start: {platform_name} with plan length={len(plan_text)}")
    prompt = (
        f"Platform: {platform_name}\n\n"
        "You are the execution specialist for this channel. "
        "Execute the approved e-commerce plan for this platform, identify the concrete work items, "
        "and return a short platform-specific execution summary with clear action items.\n\n"
        f"Approved plan:\n{plan_text}"
    )
    response = _invoke_model(
        system_prompt=(
            f"You are the {platform_name} execution specialist. "
            "Focus only on this platform's operational tasks. "
            "Return concise, practical output with clear next steps."
        ),
        user_prompt=prompt,
    )
    result_text = str(response.content or "").strip()
    print(
        f"[Subagent Debug] finish: {platform_name} -> result length={len(result_text)}"
    )
    print(
        f"[Subagent Debug] evidence: {platform_name} returned execution summary for plan"
    )
    return {"platform": platform_name, "result": result_text}


def create_ecom_agent():
    graph_builder = StateGraph(State)

    def plan_and_schedule(state: State):
        user_messages = state.get("messages", [])
        previous_plan = state.get("plan", "")
        current_revision = state.get("revision_count", 0)
        max_replans = state.get("max_replans", 3)

        if current_revision >= max_replans:
            print(
                f"[Flow guard] replan cap reached before planning: {current_revision}/{max_replans}; freezing plan and stopping retries"
            )
            return {
                "messages": [AIMessage(content=f"Plan accepted after revision cap:\n{previous_plan}")],
                "plan": previous_plan,
                "replan_status": f"limit_reached ({current_revision}/{max_replans})",
            }

        revision_count = current_revision + 1
        recommendation_context = _build_agent_recommendation_context(user_messages)

        print(
            f"\n--- [Planner] Replan #{revision_count} / {state.get('max_replans', 3)} ---"
        )
        print("Planner input context loaded from ontology recommendation context.")
        result = _invoke_model(
            system_prompt=(
                "You are a planning agent for an e-commerce workflow. "
                "Generate a concise task list for the user request. "
                "Return a task list as markdown bullet points, and every task must clearly indicate which platform subagent executes it. "
                "The valid subagent names are exactly: Platform_Amazon, Platform_Taobao, Platform_JD, Product_Agent. "
                "Product_Agent is a serial recommendation stage and must never be included in platform_parallel_batch. "
                "Use this exact pattern in each task title: '[P0] [Platform_Taobao] Validate product availability'. "
                "If several tasks are independent and run together, assign the same parallel_group='platform_parallel_batch' in the task metadata. "
                "If a previous plan exists, improve it instead of repeating it. "
                "Prefer a clear structure: summary, tasks, priority_order, recommended_platforms, next_steps."
            ),
            user_prompt=(
                "Generate a task list and prioritize it. "
                "Use the ontology recommendation context below to ground the todo list and recommendation logic.\n\n"
                "Important: every task must say which subagent executes it.\n"
                "Platform tasks must use Platform_Amazon, Platform_Taobao, or Platform_JD.\n"
                "Recommendation tasks for related products must use Product_Agent and should be serial, not part of platform_parallel_batch.\n"
                "Format example: '- [P0] [Platform_Taobao] Validate Product_Shoes availability on Taobao'\n"
                "For parallel tasks, use the same parallel_group label: platform_parallel_batch.\n\n"
                f"Existing plan (if any):\n{previous_plan}\n\n{recommendation_context}"
            ),
        )
        plan_text = str(result.content or "").strip()
        task_items = _extract_task_items(plan_text)
        task_summary = {
            "revision": revision_count,
            "summary": "Recommendation plan generated from ontology context.",
            "tasks": task_items,
            "priority_order": ["P0", "P1", "P2"],
            "recommended_platforms": [
                "Platform_Amazon",
                "Platform_Taobao",
                "Platform_JD",
            ],
            "replan_limit": state.get("max_replans", 3),
            "replan_status": f"{revision_count}/{state.get('max_replans', 3)}",
        }
        print(
            f"[Planner result]\n{json.dumps(task_summary, ensure_ascii=False, indent=2)}\n"
        )
        return {
            "messages": [AIMessage(content=f"Plan v{revision_count}:\n{plan_text}")],
            "plan": plan_text,
            "task_list": task_items,
            "revision_count": revision_count,
            "replan_status": f"{revision_count}/{state.get('max_replans', 3)}",
        }

    def review_plan(state: State):
        plan_text = state.get("plan", "")
        max_replans = state.get("max_replans", 3)
        print(
            f"\n--- [Reviewer] Reviewing plan (replan {state.get('revision_count', 0)}/{max_replans}) ---"
        )
        result = _invoke_model(
            system_prompt=(
                "You are the reviewer for an e-commerce execution plan. "
                "Decide whether the plan is sufficient. "
                "If it is not sufficient, return 'REVISE: <reason>' with concrete improvement suggestions. "
                "If it is sufficient, return 'ACCEPTED'."
            ),
            user_prompt=(
                "Review the following plan.\n\n"
                f"Plan:\n{plan_text}\n\n"
                "Return either 'ACCEPTED' or 'REVISE: <reason and improvement suggestions>'"
            ),
        )
        review_text = str(result.content or "").strip()
        print(f"[Reviewer result]\n{review_text}\n")
        if review_text.startswith("ACCEPTED"):
            return {
                "messages": [AIMessage(content=f"Final approved plan:\n{plan_text}")],
                "review_note": "Plan accepted without changes.",
                "replan_status": f"accepted ({state.get('revision_count', 0)}/{state.get('max_replans', 3)})",
            }

        max_replans = state.get("max_replans", 3)
        if state.get("revision_count", 0) >= max_replans:
            return {
                "messages": [
                    AIMessage(content=f"Plan accepted after revision cap:\n{plan_text}")
                ],
                "review_note": review_text,
                "replan_status": f"limit_reached ({state.get('revision_count', 0)}/{max_replans})",
            }

        return {
            "messages": [
                AIMessage(
                    content=(
                        "Planner should revise the plan. "
                        f"Review note: {review_text or 'Needs improvement.'}"
                    )
                )
            ],
            "review_note": review_text,
            "replan_status": f"needs_revision ({state.get('revision_count', 0)}/{max_replans})",
        }

    def execute_platforms(state: State):
        plan_text = state.get("plan", "")
        tasks = [
            ("Platform_Amazon", plan_text),
            ("Platform_Taobao", plan_text),
            ("Platform_JD", plan_text),
        ]
        print(f"\n--- [Execution] Dispatching to Amazon / Taobao / JD ---")
        results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(_execute_platform_task, platform_name, plan_text)
                for platform_name, plan_text in tasks
            ]
            for future in as_completed(futures):
                results.append(future.result())
        execution_summary = _format_platform_results(results)
        replan_reason = _should_replan_from_subagent_results(results)
        print(f"[Execution result]\n{execution_summary}\n")
        if replan_reason:
            print(f"[Subagent Replan Trigger] {replan_reason}\n")
        return {
            "messages": [AIMessage(content=f"Execution summary:\n{execution_summary}")],
            "execution_results": results,
            "execution_replan_reason": replan_reason,
        }

    def recommend_related_products(state: State):
        plan_text = state.get("plan", "")
        execution_results = state.get("execution_results", [])
        final_execution = _format_platform_results(execution_results)
        print(f"\n=== [Subagent Debug] Invoking Product_Agent ===")
        print("[Subagent Debug] start: Product_Agent serial recommendation")
        result = _invoke_model(
            system_prompt=(
                "You are the Product_Agent. Your job is to recommend related products serially after the platform execution phase. "
                "Do not mix this with the platform_parallel_batch execution. "
                "Use the platform results and ontology context to suggest 2-5 related products with clear rationale."
            ),
            user_prompt=(
                "Recommend related products for the user based on the plan and platform execution outcomes. "
                "This is a serial recommendation step separate from platform parallel execution.\n\n"
                f"Final plan:\n{plan_text}\n\n"
                f"Platform execution results:\n{final_execution}"
            ),
        )
        product_content = str(result.content or "").strip()
        print(
            f"[Subagent Debug] finish: Product_Agent -> result length={len(product_content)}"
        )
        print(
            "[Subagent Debug] evidence: Product_Agent produced a serial related-product recommendation"
        )
        print(f"[Product_Agent result]\n{product_content}\n")
        return {
            "messages": [
                AIMessage(content=f"Product recommendation summary:\n{product_content}")
            ],
            "product_recommendation": product_content,
        }

    def joiner(state: State):
        user_messages = state.get("messages", [])
        user_question = "\n".join(
            str(getattr(m, "content", ""))
            for m in user_messages
            if getattr(m, "type", "") == "human"
        )
        if not user_question:
            raise ValueError("User question is missing from the message history.")
        plan_text = state.get("plan", "")
        review_note = state.get("review_note", "")
        execution_results = state.get("execution_results", [])
        product_recommendation = state.get("product_recommendation", "")
        final_execution = _format_platform_results(execution_results)
        print(f"\n--- [Synthesizer] Finalizing result ---")
        result = _invoke_model(
            system_prompt=(
                "You are the final synthesis agent. Your final answer must first directly answer the user's shopping question. "
                "Do not start with technical process notes. Start by giving a product recommendation in plain language, then add a compact summary. "
                "Use the platform outputs and product recommendation to support the recommendation."
            ),
            user_prompt=(
                "Answer the user's question directly first.\n\n"
                "User question: "
                f"{user_question}\n\n"
                "Then provide a short summary including: 1) the recommended product, 2) why it fits the user, 3) the platform and evidence, 4) optional related products, 5) execution notes if relevant.\n\n"
                f"Final plan:\n{plan_text}\n\n"
                f"Review improvements:\n{review_note}\n\n"
                f"Execution output:\n{final_execution}\n\n"
                f"Serial product recommendation:\n{product_recommendation}"
            ),
        )
        final_content = str(result.content or "").strip()
        print(f"[Synthesizer result]\n{final_content}\n")
        return {"messages": [AIMessage(content=final_content)]}

    graph_builder.add_node("plan_and_schedule", plan_and_schedule)
    graph_builder.add_node("review_plan", review_plan)
    graph_builder.add_node("execute_platforms", execute_platforms)
    graph_builder.add_node("recommend_related_products", recommend_related_products)
    graph_builder.add_node("join", joiner)

    def should_continue(state):
        messages = state["messages"]
        last_message = messages[-1]
        last_text = str(getattr(last_message, "content", "")).upper()
        current_revision = state.get("revision_count", 0)
        max_replans = state.get("max_replans", 3)
        print(
            f"[Flow guard] revision={current_revision}; max_replans={max_replans}; replan_status={state.get('replan_status', 'pending')}"
        )

        if "REVISE" in last_text:
            if current_revision < max_replans:
                return "plan_and_schedule"
            print(
                f"[Flow guard] revision cap reached: stopping replan loop at {current_revision}/{max_replans}"
            )
            return END

        if (
            "FINAL APPROVED PLAN" in last_text
            or "PLAN ACCEPTED AFTER REVISION CAP" in last_text
        ):
            return "execute_platforms"
        if "EXECUTION SUMMARY" in last_text:
            execution_reason = state.get("execution_replan_reason", "")
            if execution_reason:
                if current_revision < max_replans:
                    print(f"[Flow guard] subagent-triggered replan: {execution_reason}")
                    return "plan_and_schedule"
                print(
                    f"[Flow guard] max replan reached; ignoring execution-triggered replan: {execution_reason}"
                )
                return "recommend_related_products"
            return "recommend_related_products"
        if "PRODUCT RECOMMENDATION SUMMARY" in last_text:
            return "join"
        return END

    graph_builder.add_edge(START, "plan_and_schedule")
    graph_builder.add_edge("plan_and_schedule", "review_plan")
    graph_builder.add_conditional_edges(
        "review_plan",
        should_continue,
        ["plan_and_schedule", "execute_platforms", END],
    )
    graph_builder.add_conditional_edges(
        "execute_platforms",
        should_continue,
        ["plan_and_schedule", "recommend_related_products", END],
    )
    graph_builder.add_edge("recommend_related_products", "join")
    graph_builder.add_edge("join", END)

    return graph_builder.compile()


def _print_debug_flow(label, messages):
    print(f"\n===== {label} =====")
    for index, message in enumerate(messages, start=1):
        content = getattr(message, "content", "")
        if not content:
            continue
        print(f"[{index}] {type(message).__name__}:\n{content}\n")


if __name__ == "__main__":
    agent = create_ecom_agent()
    response = agent.invoke(
        {
            "messages": [
                HumanMessage(content="I'm want to shopping, what do you recommend?")
            ]
        }
    )
    _print_debug_flow("Agent execution trace", response["messages"])
