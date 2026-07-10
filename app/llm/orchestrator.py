from dataclasses import dataclass, field

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.llm.memory import get_session_history
from app.llm.prompts import SYSTEM_PROMPT
from app.llm.tools import build_tools


@dataclass
class AgentTurnResult:
    reply: str
    tool_calls: list[str] = field(default_factory=list)
    grounded_amounts: set[str] = field(default_factory=set)


def _build_agent_executor(session_id: str) -> AgentExecutor:
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.3,
    )
    tools = build_tools(session_id)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=settings.DEBUG, max_iterations=6)


def run_agent_turn(session_id: str, user_input: str) -> AgentTurnResult:
    """
    Run one turn of the support agent for a given session, using the tool-calling
    agent + persistent per-session chat history.
    """
    executor = _build_agent_executor(session_id)

    with_history = RunnableWithMessageHistory(
        executor,
        get_session_history=get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    result = with_history.invoke(
        {"input": user_input},
        config={"configurable": {"session_id": session_id}},
    )

    reply_text: str = result.get("output", "")
    tool_calls: list[str] = []
    grounded_amounts: set[str] = set()

    for step in result.get("intermediate_steps", []) or []:
        action, observation = step
        tool_calls.append(action.tool)
        if isinstance(observation, dict):
            for key in ("total", "refund_amount"):
                if key in observation and observation[key] is not None:
                    grounded_amounts.add(f"${observation[key]:.2f}")

    return AgentTurnResult(reply=reply_text, tool_calls=tool_calls, grounded_amounts=grounded_amounts)
