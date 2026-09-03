from langgraph.graph import START,END,StateGraph,add_messages
from langchain_core.messages import BaseMessage,SystemMessage,AIMessageChunk ,AIMessage,HumanMessage,RemoveMessage,ToolMessage
from dataclasses import dataclass ,field
from langchain_openai import ChatOpenAI
from langgraph.config import get_stream_writer,get_store,get_config
from langgraph.types import Command, Send,Interrupt,interrupt
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from typing_extensions import Annotated,List,Literal,Callable,Optional
from datetime import datetime
from langgraph.prebuilt import ToolNode
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

search= DuckDuckGoSearchRun()
@tool
def web_search(query:str):
    """for access external information """
    res = search.invoke(query)
    return res


@tool
def datetime_tool():
    """for access current date and time"""
    return datetime.now().strftime("Day %A, %d %B %Y, time %I:%M %p") 

tools =[datetime_tool,web_search]
llm = ChatOpenAI(model="Qwen2.5-3B-Instruct-Q4_K_M.gguf",api_key="not_need",base_url="http://localhost:8080")
llm_tools = llm.bind_tools(tools=tools)



@dataclass
class State:
    messages:Annotated[List[BaseMessage|str],add_messages] =field(default_factory=list)

tool_node = ToolNode(tools=tools)

def should_continue(state:State)->Literal["end","tool_node"]:
    if not state.messages:
        return "end"
    last_message =state.messages[-1]
    if isinstance(last_message,AIMessage) and last_message.tool_calls:
        return "tool_node"
    else:
        return "end"

async def node(state:State,config:RunnableConfig):
    writer =get_stream_writer()

    prompt =ChatPromptTemplate.from_messages([("system","""You are a friendly, natural, and helpful voice AI assistant.
Your goal is to have smooth, human-like conversations.
Voice conversation rules:
- Keep responses concise and easy to understand when spoken aloud.
- Use natural conversational language rather than formal or robotic wording.
- Avoid unnecessary lists, tables, markdown, and long explanations.
- Ask one question at a time.
- Do not repeat information unnecessarily.
- If the user interrupts or changes the topic, adapt immediately.
- If you don't understand something, politely ask for clarification.
- Use short sentences and natural pauses.
- Do not describe your internal reasoning.
- Be helpful, friendly, and confident.
- Match the user's tone and level of formality.

CRITICAL INSTRUCTION:
- Answer ONLY the latest user input.
- Tool call if require .
- Do not answer previous questions that were already addressed."""),MessagesPlaceholder("history",optional=True) ,MessagesPlaceholder("messages")])
    
    chain = prompt | llm_tools

    # store = context.store
    # writer = context.stream_writer
   


    thread_id = config.get("configurable",None).get("thread_id",None)
    user_id = config.get("configurable",None).get("user_id",None)
    print(" ❤️ thread_id and user_id:",thread_id,user_id)
    # if user_id:
    #     history = store.get("user_id")


    full_chunk=None
    async for chunk in chain.astream({"messages":state.messages}):
        if full_chunk is None:
            full_chunk = chunk
        else:
            full_chunk +=chunk
        writer(AIMessage(chunk.content))

    return {"messages":[AIMessage(content=full_chunk.content,tool_calls=full_chunk.tool_calls)]}

graph = (StateGraph(state_schema=State)
        .add_node("node",node)
        .add_node("tool_node",tool_node)
        .add_edge(START,"node")
        .add_conditional_edges("node",should_continue,{"tool_node":"tool_node","end":END})
        .add_edge("tool_node","node")
        )

    


