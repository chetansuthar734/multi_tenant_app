

from langgraph.graph import StateGraph,START,END,add_messages
from dataclasses import dataclass
from langchain_core.prompts import ChatMessagePromptTemplate
from typing_extensions import Annotated,List,Dict,Optional,Union
from langchain_core.messages import BaseMessage,AIMessage,HumanMessage,SystemMessage,AIMessageChunk,RemoveMessage,ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool 
from langchain_community.tools import DuckDuckGoSearchRun
import requests
from typing_extensions import Literal
from langgraph.prebuilt import ToolNode
from langgraph.types import Command,interrupt
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError 
from langgraph.config import get_config, get_store, get_stream_writer
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
import httpx
import os
import time
from datetime import datetime
import asyncio
from uuid import uuid4
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
load_dotenv()



API = os.getenv("API")
DB_API=os.getenv("DB_ENV")
MODEL=os.getenv("MODEL")
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")


from langchain_openai import ChatOpenAI
search= DuckDuckGoSearchRun()
llm = ChatOpenAI(
    # model="Qwen3-8B-Q4_K_M.gguf", #slow 3t/s but good tool calls
    # model="Qwen2.5-3B-Instruct-Q4_K_M.gguf", #poor tool calls but fast 20token/sec
    # model="Qwen2.5-7B-Instruct-Q4_K_M.gguf", #5t/s slow but perfect in a1990 mac
    # model="Qwen2.5-Omni-7B-Q4_K_M.gguf", #5t/s slow but perfect in a1990 mac
    model="Qwen2.5-Omni-7B-Q4_K_M.gguf", #multimodel llm with mmproj a1990 mac
    base_url="http://127.0.0.1:8080/v1",
    api_key="not-needed",
    stream_chunk_timeout=0,
    )

# response = llm.invoke("Explain LangGraph in one sentence.")

# print(response.type)

model = ChatGoogleGenerativeAI(model=MODEL,google_api_key=GEMINI_API_KEY,)
# model = ChatGoogleGenerativeAI(model="gemini-3.5-flash",google_api_key="AQ.Ab8RN6LH_P4D3zEMeUsnoWUERSy4dKIA-jpBnzRqeY0o4BnF5w",)

@dataclass 
class State:
    # messages:List[Union[Dict,BaseMessage,str]]
    messages:Annotated[List[Union[BaseMessage,str,Dict]],add_messages]

@dataclass 
class InputState:
    messages:List[Union[Dict,BaseMessage,str]]


@tool
def datetime_tool():
    """for access current date and time"""
    return datetime.now().strftime("%d/%m/%Y, %H:%M:%S")

@tool
def web_search(query:str):
    """for access external information """
    res = search.invoke(query)
    return res

@tool
def rag_tool(query:str):
    """Retrive augment generate tool for user releted informamtion like name, education, skill"""
    return "chetan suthar"

    # print("config",config)
    # assistant=config['configurable'].get('assistant',None)
    # if not assistant:
    #     return "No Document provided."
    # docs=[]
    # if assistant:
    #     async with httpx.AsyncClient() as req:
    #         response = await req.get(f"API/?assistant={assistant}&query={query}")
    #         response.raise_for_status()
    #         docs = response.json()

    # return  "\n".join(str(content) for content in ['my name is chetan','i am electrical engineer'])
    # return  "\n".join(str(content) for content in docs)


async def tool_node(state:State,config:RunnableConfig):
    writer = get_stream_writer()
    user_input = interrupt('tool use approval: y/n',)
    print("user_input👦 ",user_input)
    if user_input.strip().lower() in {"n", "no"}:
        return {"messages":[ToolMessage("permission not allow",tool_call_id=str(state.messages[-1].id))]}

    # writer(AIMessageChunk("stream from tool"))
    mcp_server = config.get("configurable",{}).get('mcp_server',None)
    mcp_server=True
    tools=[]
    if mcp_server :
        """here get mcp tools"""
        try:
            client = MultiServerMCPClient( {"my_tools": {"transport": "http","url": "http://127.0.0.1:8000/mcp",}})
            tools = await client.get_tools()
            for tool in tools:
                print('⚙️', tool.name)
        except Exception as e:
            print("error",e)

    tools = [*tools,rag_tool,datetime_tool,web_search]
    res = await ToolNode(tools).ainvoke({"messages":state.messages})  #return dict {"messages":[list of ToolMessage]}
    print(res)
    return res


def tool_calls_check_node(state:State)->Literal['tool_node',"__end__"]:
    if not state.messages:
        return END
    last_message = state.messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        print("⚙️ tool calls start")
        return 'tool_node'
    else:
        return END




async def  supervisor(state:State,config:RunnableConfig)->State:
    # user_input = interrupt('please enter name fisrt')
    # if user_input=="end":
        # return {}
        # return Command(goto=END)
    # print("❤️ userinput:",user_input)
    writer = get_stream_writer()
    mcp_server = config.get("configurable",{}).get('mcp_server',None)
    mcp_server = config.get("configurable",{}).get('assistant',None)
    mcp_server=True
    tools=[]
    if mcp_server :
        """here get mcp tools"""
        try:
            client = MultiServerMCPClient( {"my_tools": {"transport": "http","url": "http://127.0.0.1:8000/mcp",}})
            tools = await client.get_tools()
            for tool in tools:
                print('⚙️', tool.name)
        except Exception as e:
            print("error",e)

    tools = [*tools,rag_tool,datetime_tool,web_search]
    model_with_tools = llm.bind_tools(tools)
    
    # res =await model_with_tools.ainvoke([SystemMessage('always call rag tool for gather user information,then anser'),HumanMessage('what is my name')])
    # if res.tool_calls:
    #     res = await ToolNode(tools).ainvoke({"messages":[res]})
    #     print(res)

    system_prompt = 'your are helpul rag assistant .first call rag tool if user related informtion require.'
    prompt = ChatPromptTemplate.from_messages([SystemMessage(content=system_prompt),MessagesPlaceholder("messages")])

    chain = prompt | llm.bind_tools([rag_tool,datetime_tool,web_search])
    full_chunk=None
    try:
        async for chunk in chain.astream({"messages":state.messages}):
            # print(chunk.content)
            if type(chunk.content)==[]:
                continue
            if full_chunk== None:
                full_chunk=chunk
            else :
                full_chunk+=chunk
            writer(AIMessage(full_chunk.content))


        final_message = AIMessage(content=full_chunk.content,tool_calls=full_chunk.tool_calls,id=str(uuid4()))

    # except Exception as e:
    except ChatGoogleGenerativeAIError as e:
        print("❌ chat model error, so not add message to state",e)    
        if not state.messages:
            return END
        return Command(goto=END,update= {"messages": [AIMessage("1Sorry, I couldn't process that message.")]})   #so new message is not add to state because it not return state

    except asyncio.CancelledError:
        # await asyncio.sleep(5)
        print("🛑 receive notification in agent node, Agent task was cancelled")
        if full_chunk is None:
            return {"messages": []}
        return Command(goto=END)#stream chunk append to messages
        # return Command(goto=END,update={"messages":[AIMessage(content=full_chunk.content,id=str(uuid4()))]} )#stream chunk append to messages
    
    return {"messages":[final_message]}

# agent.py

print("🔥 AGENT MODULE LOADED", flush=True)

graph = (
    StateGraph(state_schema=State)
    .add_node("supervisor", supervisor)
    .set_entry_point("supervisor")
    .add_node("tool_node", tool_node)
    .add_conditional_edges("supervisor",tool_calls_check_node,{"tool_node":"tool_node",END:END})
    .add_edge( 'tool_node',"supervisor")
)



















    #     id =uuid4()
    #     text = ""   
    #     full_chunk= None 
    #     async for chunk in chain.astream({"history":[],"messages":state.messages}):
    #         content = chunk.content
    #         if full_chunk is None:
    #             full_chunk = chunk
    #         else:
    #             full_chunk = full_chunk + chunk

    #         if isinstance(content, str):
    #             text = content
    #         elif isinstance(content, list):
    #             text = "".join(part.get("text", "")for part in content if isinstance(part, dict))  
    #         if text:
    #             msg+=text
    #             print(full_chunk)
    #             writer(AIMessage(msg))

        # final_message = AIMessage(content=full_chunk.content,additional_kwargs=full_chunk.additional_kwargs,tool_calls=full_chunk.tool_calls,id=str(id) ) # for tool calls also
        # print("TEXT:", final_message.content)
        # print("TOOL CALLS:", final_message.tool_calls)
        # writer(AIMessage("stream ai messages:....... send  accumulated chunk"))