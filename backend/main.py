
from pydantic import BaseModel
from twilio.rest import Client
import os
from dotenv import load_dotenv
import requests
import asyncio
import base64
import httpx
from urllib.parse import urlencode
import json
from bson import ObjectId
from fastapi import FastAPI, WebSocket, WebSocketDisconnect,Request,UploadFile,File,HTTPException,Query,Header
from contextlib import asynccontextmanager
from fastapi.responses import Response, StreamingResponse,JSONResponse,RedirectResponse
# from langgraph.checkpoint.redis import RedisSaver
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse, Connect
from fastapi.encoders import jsonable_encoder
from pymongo import AsyncMongoClient
from gridfs import AsyncGridFSBucket,GridFS
from pydantic import BaseModel ,Field,ConfigDict
from typing_extensions import List ,Optional ,Dict
from langchain_core.messages import BaseMessage,HumanMessage,AIMessage
from aiortc import RTCPeerConnection, RTCSessionDescription,MediaStreamTrack
from langchain_google_genai import ChatGoogleGenerativeAI
from agent import graph
from conversation_agent import graph as conv_graph
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.store.mongodb import MongoDBStore
import webrtcvad
from uuid import uuid4
from enum import Enum
import time
import pymupdf4llm
from faster_whisper import WhisperModel
import pymupdf
from langgraph.types import Command
from groq import Groq,AsyncGroq
import wave
from piper import PiperVoice
from routers.voice_agent import router as voice_router



groq_client = AsyncGroq(api_key="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")

pcs = set()

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
# whisper_model=WhisperModel(
#     "large-v3",
#     device="cpu",
#     compute_type="int8",
#     cpu_threads=8,
#     num_workers=1,
#     )


load_dotenv()
API = os.getenv("API")
DB_API=os.getenv("DB_ENV")
MODEL=os.getenv("MODEL")
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
REACT_APP_URL=os.getenv("REACT_APP_URL")

TWILIO_CLIENT_ID = os.getenv("TWILIO_CLIENT_ID")
TWILIO_CLIENT_SECRET = os.getenv("TWILIO_CLIENT_SECRET")
TWILIO_REDIRECT_URI = f"{API}/twilio/callback"
# TWILIO_AUTHORIZE_URL = os.getenv("AUTHORIZATION_URL") 
TWILIO_AUTHORIZE_URL =f"https://oauth.twilio.com/v2/authorize?client_id={TWILIO_CLIENT_ID}&response_type=code&scope=offline_access&redirect_uri={TWILIO_REDIRECT_URI}&state=STATE"
TWILIO_TOKEN_URL = "https://oauth.twilio.com/v2/token"
model = ChatGoogleGenerativeAI(
    model=MODEL,
    # model="gemini-3.1-pro-preview",
    google_api_key=GEMINI_API_KEY, 
    )



mdb = AsyncMongoClient(DB_API)
db = mdb["upload_files"]
# GridFS
fs = AsyncGridFSBucket(db)
# fs = GridFS(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    voice = PiperVoice.load("en_US-lessac-medium.onnx")
    # voice = PiperVoice.load(model_path="hi_IN-priyamvada-medium.onnx",config_path="hi_IN-priyamvada-medium.onnx.json",)
    app.state.voice =voice
    client = MongoClient(DB_API)
    db =client["my_database"]
    store = MongoDBStore.from_conn_string(conn_string=DB_API, db_name="store")
    checkpointer = MongoDBSaver(db,ttl=10) #ttl in sec
    # ttl_config={'default_ttl':60 , #60 min
    #            "refresh_on_read":True
    #            }
    app.state.mongo_client = client
    app.state.store = store
    app.state.checkpointer = checkpointer

    app.state.agent = graph.compile(checkpointer=checkpointer,store=store)
    app.state.conv_agent = conv_graph.compile(checkpointer=checkpointer,store=store)
    # with RedisSaver.from_conn_string("redis://localhost:6379",ttl=ttl_config) as checkpointer :
    #     checkpointer.setup()
    #     app.state.agent = graph.compile(checkpointer=checkpointer,store=store)

    try:
        yield

    finally:
        client.close()

app = FastAPI(lifespan=lifespan)
app.include_router(voice_router)

class AgentStatus(str,Enum):
    IDLE="idle"
    RUNNING="running"
    INTERRUPT="interrupt"
    RESUME="resume"
    ERROR="error"
    CONNECT="connect"
    STOP='stop'


class User(BaseModel):
    username:str|None=None
    # state:Dict[str,Union[List,BaseMessage,str,int,bool,float]] =Field(default_factory=dict)
    state:Dict[str,object] =Field(default_factory=dict) #contain any python object

    config:Dict[str,object] =Field(default_factory=dict) #contain any python object

    websocket:WebSocket | None = None
    queue:asyncio.Queue|None = None
    task:asyncio.Task|None=None

    class Config: #for custom data type
        arbitrary_types_allowed=True

    def json_enc(self):
        return jsonable_encoder({
            "username": self.username,
            "state": self.state,
            "config": self.config,
        })



class Users(BaseModel):
    users:Dict[str,User]=Field(default_factory=dict)

    def add_user(self, username):
        if username in self.users:
            return self.users[username]
            # raise ValueError('already user exist')
        else:
            self.users[username] = User(username=username)
            return self.users[username]
    
    def get_user(self,username):
        if username  not in self.users:
            raise ValueError('user not exist')
        
        else:
            return self.users.get(username)
    
    def remove_user(self,username):
        if username  not in self.users:
            raise ValueError('user not exist')
        
        else:
            return self.users.pop(username)


users = Users()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#this is twilio trail number credential 
client = Client(
    # os.getenv("TWILIO_ACCOUNT_SID"),
    "AC37321fb530e4591b594bd633fbebbe2f",
    # os.getenv("TWILIO_AUTH_TOKEN")
    "d861be3c74d4d59173df728005727fef"
)

# account = client.api.accounts(
#    "AC37321fb530e4591b594bd633fbebbe2f"
# ).fetch()

# print(account.sid)
# print(account.status)


class Configurable(BaseModel):
    thread_id:str =Field(default_factory=lambda: str(uuid4()))
    # checkpoint_ns:str=Field(default_factory=lambda: str(""))
    #dont assign checkpoint_id it use it use by graph to save sate on point 
    recursion_limit:int=Field(default_factory=lambda:5)
    model_config = {"extra": "allow"}
    

class Config(BaseModel):
    configurable:Configurable
    model_config={"extra":"allow"}

class Option(BaseModel):
    stream_mode:List[str]=["custom", "values"]
    model_config={"extra":"allow"}

class AgentInput(BaseModel):
    state: dict[str,object] = Field(default_factory=dict)
    resume: str = Field(default_factory=str)
    config:Config
    option: Dict[str,object] = Field(default_factory=dict)
    # model_config={"extra":"allow"}



# cookies

# @app.get("/demo")
# def demo(request:Request):
#     cookies = request.cookies.get('oauth_state')
#     print(cookies)
#     response = JSONResponse({
#         "message": "OAuth state created",
#         "state": "state",
#     })

#     # Store state in browser cookie
#     response.set_cookie(
#         key="oauth_state",
#         value="state",
#         httponly=True,
#         secure=False,
#         samesite="lax",
#         max_age=600,





async def run_agent(websocket, message):
    agent_inp = AgentInput.model_validate(message)
    start = time.time()
    token=0
  
     # send client info. agent is running
    await websocket.send_json(jsonable_encoder({"event":"status","status":AgentStatus.RUNNING}))
    agent = websocket.app.state.agent

    print("❤️ input type",message['event'])
    print("❤️ state",agent_inp.state)
    print("❤️ resume",agent_inp.resume)
    print("❤️ config",agent_inp.config)
    print("❤️ option",agent_inp.option)
    s = agent.get_state(message['config']).values  #previous values 
    print('🟢 agent run and get_state ',s)

    full_stream_msg=AIMessage("")
    try:
        print("🚀 BEFORE INVOKE",message)

        if message['event']==AgentStatus.RESUME:
            agent_input = Command(resume=agent_inp.resume)
        elif message['event']==AgentStatus.RUNNING:
            agent_input= agent_inp.state

        async for type,chunk in agent.astream(input=agent_input,config=agent_inp.config.model_dump(),**agent_inp.option):
            print("❤️",chunk)
            if type == "values": #state op at every step
                print("🔵 values")
                await websocket.send_json(jsonable_encoder({"event":"state","data":{"state":chunk}}))

            if type == "custom": #stream chunk AIMessage()
                print("🟡 custom")
                token =len(chunk.content.split()) #. chunk is alreadsy accumulated . len(text.split()) → words.   len(text) → characters including spaces
                await websocket.send_json(jsonable_encoder({"event":"stream","stream":chunk}))
                await websocket.send_json(jsonable_encoder({"event":"monitor","monitor":{"time":int(time.time() - start),"token":token}}))
                print("chunk :",chunk)
                full_stream_msg=chunk

        print("✅ AFTER INVOKE ")
        print("full_stream_msg",full_stream_msg)


    except asyncio.CancelledError as e:
        # await asyncio.sleep(5)
        agent.update_state(message['config'],{"messages":[full_stream_msg]}) 
        statesnapshot = agent.get_state(message['config']).values  #previous values 
        print('agent run cancel ❌ and state final',full_stream_msg)
        await websocket.send_json(jsonable_encoder({"event":"state","data":{"state":statesnapshot}}))

    except Exception as e:
        statesnapshot2 = agent.get_state(message['config']).values  #previous values 
        agent.update_state(message['config'],statesnapshot2)
        print("❌ ERROR ",e)
        await websocket.send_json(jsonable_encoder({"event":"state","data":{"state":{"messages":e}}}))
        await websocket.send_json(jsonable_encoder({"event":"status","status":AgentStatus.ERROR }))

    finally:

        # send agent is idle
        statesnapshot2 = agent.get_state(message['config']).values  #previous values 
        interrupts = agent.get_state(message['config']).interrupts  #previous values  () or (Interrupt(value='enter your name', id='5f0063633894833a701040f1c2966727'),)
        if interrupts:
            await websocket.send_json(jsonable_encoder({"event":"status","status":AgentStatus.INTERRUPT,"value":interrupts}))
        else:
            # await websocket.send_json(jsonable_encoder({"event":"state","data":{"state":statesnapshot2}}))
            await websocket.send_json(jsonable_encoder({"event":"status","status":AgentStatus.IDLE }))

        # agent.update_state(message['config'],statesnapshot2)
        print("✅ Final run ",full_stream_msg)
        # print('agent finally run  and state final',statesnapshot2)







@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket,
                             #  token:str=Query(...)
                            ):
    await websocket.accept()
    agent_task = None

    #verify token
    # assistant = 

    while True:
        data = await websocket.receive()
        if data["type"] == "websocket.disconnect":
                print("😢  Client disconnected")
                break
        # Handle your data here
        if data["type"] == "websocket.receive":
            if "text" in data:
                #text/json handle here
                try:
                    message = json.loads(data["text"])
                    event = message.get('event',None)
                    print("event",event)

                    if isinstance(message,dict):

                        #send status ws successfully connect to client
                        if message['event']==AgentStatus.CONNECT:
                            await websocket.send_json(jsonable_encoder({"event":"connection","data":"success","status":'idle'}))
                            print("JSON data:", message)
           
                        elif message['event'] in ("running","resume"):
                            if agent_task and not agent_task.done():
                                print("❌new run arrive and reject")
                                continue                    
                            agent_task = asyncio.create_task(run_agent(websocket,message))
           
        
                        elif message['event']==AgentStatus.STOP:
                            agent = websocket.app.state.agent
                            state = agent.get_state(message['config']).values 
                            await websocket.send_json(jsonable_encoder({"event":"state","data":{"state":state}}))
                            await websocket.send_json(jsonable_encoder({"event":"status","status":'idle'}))
                            if agent_task and not agent_task.done():
                                agent_task.cancel()
                                try:
                                    await agent_task
                                    print("🛑 await ended Agent task cancelled")
                                except asyncio.CancelledError:
                                    print("🛑  Agent task cancelled")
                                agent_task = None
                           #stop running task and return msg
    
                        elif isinstance(message,dict):
                            print('plain string')


                except WebSocketDisconnect as e:
                    if agent_task and not agent_task.done():
                        agent_task.cancel()
                        try:
                            await agent_task
                        except asyncio.CancelledError:
                            pass
                        finally:
                            agent_task = None


            elif "bytes" in data:
                #voice/video stream live 
                #bytes handle here
                b  = data['bytes']
                print(b)
        
        # data = bytes([1, 2, 3, 4, 5])
        # await websocket.send_bytes(data)

        







@app.post("/uploadfiles")
async def upload_files(files: list[UploadFile] = File(...),username:str=Query("guest")):
    uploaded_files = []
    messages = []
    user = users.add_user(username)
    user.state["messages"] = []
    # user = users.get_user(username)


    for file in files:
        file_bytes = await file.read()   #all read  ,FIle at  EOF
        grid_file =  fs.open_upload_stream(
            file.filename,
            metadata={"username": username,
                      "content_type": file.content_type,}
            )


        await grid_file.write(file_bytes)
        file_url = f"{API}/file/{str(grid_file._id)}"
        
        if file.content_type.startswith("image/"):
            msg=HumanMessage(content=[{"type":"image_url","image_url":{"url":file_url }}])
            messages.append(msg)

        if file.content_type.startswith("video/"):
            msg=HumanMessage(content=[{"type":"video_url","video_url":{"url":file_url}}])
            messages.append(msg)

        if file.content_type.startswith("audio/"):
            msg=HumanMessage(content=[{"type":"audio_url","audio_url":{"url":file_url}}])
            messages.append(msg)

        if file.content_type.startswith("application/pdf"):  #application/pdf
            doc = pymupdf.open(stream=file_bytes,filetype="pdf")
            text = pymupdf4llm.to_markdown(doc)         
            msg=HumanMessage(content=[{"type":"text","text":text}],name=file.content_type)
            messages.append(msg)

        # if file.content_type.endswith(("/json","/xml")):  #application/json , xml text/xml ,application/xml ,application/json
        #     text = file_bytes.decode("utf-8", errors="replace")       
        #     msg=HumanMessage(content=[{"type":"text","text":text}],name=file.content_type)
        #     messages.append(msg)

        # if file.content_type.startswith("text/"): #for plain text and html.  For TXT/HTML/CSV:
        #     text = file_bytes.decode("utf-8", errors="replace")
        #     msg=HumanMessage(content=[{"type":"text","text":text}],name=file.content_type)
        #     messages.append(msg)
        # if file.content_type in ("application/json","application/xml","text/xml","text/plain","text/html","text/css","text/csv","text/javascript","application/javascript",):
        if file.filename.lower().endswith((".txt",".html",".css",".js",".py",".json",".xml",".csv",)):
            text = file_bytes.decode("utf-8", errors="replace")
            msg=HumanMessage(content=[{"type":"text","text":text}],name=file.content_type)
            messages.append(msg)

        await grid_file.close()

        # user.state['messages'].append(msg)


        uploaded_files.append({
            "file_id": str(grid_file._id),
            "filename": file.filename,
            "content_type": file.content_type,
            "url":file_url
            })

    return {
        "files": uploaded_files,
        # 'user':user.json_enc(),
        "messages":jsonable_encoder(messages)

    }





@app.get("/file/{file_id}")
async def get_file(file_id: str):

    try:
        grid_file = await fs.open_download_stream(
            ObjectId(file_id)
        
        )
        data = await grid_file.read()

        return Response(
            content=data,
            media_type=grid_file.metadata["content_type"]
        )
    except Exception:
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

   


@app.delete("/file/{file_id}")
async def delete_file(file_id: str):

    try:
        await fs.delete(ObjectId(file_id))
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return {
        "message": "File deleted",
        "file_id": file_id
    }



































@app.get("/twilio/connect")
async def twilio_connect(
    authorization: str = Header(...)
):
    # 1. Validate your JWT
    token = authorization.replace("Bearer ", "")

    # user_id = verify_jwt(token)

    # 2. Generate unique OAuth state
    state = str(uuid4())

    # 3. Store state -> user_id
    # await db.oauth_state.insert_one({
    #     "state": state,
    #     "user_id": user_id
    # })
    params = {
        "client_id": TWILIO_CLIENT_ID,
        "response_type": "code",
        "scope": "offline_access",
        "redirect_uri": TWILIO_REDIRECT_URI,
        "state": state,
        }

    oauth_url = (
        f"{TWILIO_AUTHORIZE_URL}?{urlencode(params)}"
        )

    return {
        "url": oauth_url
    }





TWILIO_TOKEN_URL = "https://oauth.twilio.com/v2/token"

@app.get("/twilio/callback")
async def twilio_callback(request: Request):
    account_sid = request.query_params.get("AccountSid")
    print("AccountSid",account_sid)
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        raise HTTPException(400, "Missing authorization code")

    # TODO:
    # Verify state against the state you stored for this user

    async with httpx.AsyncClient() as client:

        response = await client.post(
            TWILIO_TOKEN_URL,
            data={
                "client_id": TWILIO_CLIENT_ID,
                "client_secret": TWILIO_CLIENT_SECRET,
                "grant_type": "authorization_code",
                # "grant_type": "client_credentials",
                "code": code,
                "redirect_uri": TWILIO_REDIRECT_URI,
            },
        )

    print(response.status_code)
    print(response.text)
    

    response.raise_for_status()

    token_data = response.json()

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")



    async with httpx.AsyncClient() as client:
        # url = "https://api.twilio.com/2010-04-01/Accounts.json"
        # url = "https://iam.twilio.com/v2/Organizations/Roles"
        url = "https://iam.twilio.com/scim/v2/Users"
        headers = { "Authorization": f"Bearer {access_token}"}
        response = await client.get(url, headers=headers)
        res = response.json()
        # response.raise_for_status()
        print(res)
        # return response.json()


    # Save these in your database
    # await save_twilio_tokens(user_id, access_token, refresh_token)

    # return {
    #     "message": "Twilio connected",
    #     "access_token": access_token,
    #     "expires_in": token_data.get("expires_in"),

    # }
    return RedirectResponse(
        url=f"{REACT_APP_URL}/assistant?twilio=connected",
        status_code=302)




from twilio.rest import Client




@app.get("/twilio/call")
async def make_call(request:Request):

    # auth_token = request.account_id 
    # auth_token =  request.auth_token
    account_sid ="AC37321fb530e4591b594bd633fbebbe2f"
    auth_token ="d861be3c74d4d59173df728005727fef"
    client = Client(account_sid, auth_token)

    # call = client.calls.create(
    message = client.messages.create(
    to="whatsapp:+917340550726",
    from_="whatsapp:+17372212163",
    content_sid="HXfe5ab5f00277942d4d4200328b4d403c",
    body="hello"
    )

    print(message.sid)

    # return {
    #     "call_sid": call.sid,
    #     "status": call.status,
    # }
    # call = client.calls.create(
    #     to="+917340550726",
    #     from_="+17372212163",
    #     url="https://webhooks.twilio.com/v1/Voice/Template/voice_speech_recognition"
    #     )

    # print(call.sid)
    # return call.sid


    # url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json"
    # url = f"https://iam.twilio.com/scim/v2/Users"

    # headers = {
    #     "Authorization": f"Bearer {access_token}"
    # }

    # data = {
    #     "To": "+17372212163",
    #     "From": "+917340550726",
    #     "Url": "https://c6f1-2409-40d4-241e-5e4b-6cd3-2e96-4c2d-af45.ngrok-free.app/voice"
    # }

    # async with httpx.AsyncClient() as client:
    #     response = await client.get(
    #         url,
    #         headers=headers,
    #         # data=data
    #     )
    #     print(response.status_code)
    #     print(response.text)

        # response.raise_for_status()

        # return response.json()


@app.post("/voice")
async def voice():
    return Response(
        content="""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Hello from your FastAPI server</Say>
</Response>""",
        media_type="application/xml"
    )



















# import webrtcvad
# import numpy as np
# vad = webrtcvad.Vad(3) #aggressiveness:0-3
# #pip install silero-vad torch torchaudio
# # Trigger when a person is actually talking, but don't trigger on fan noise, tapping, AC, keyboard, etc.
# import torch
# import numpy as np
# from silero_vad import load_silero_vad,VADIterator

# model = load_silero_vad()
# # vad= VADIterator(model,sampling_rate=16000)

# vad = VADIterator(
#     model,
#     sampling_rate=16000,
#     threshold=0.7,
#     min_silence_duration_ms=1000,
#     speech_pad_ms=100,
# )


# #process audio function 
# from aiortc import RTCPeerConnection,RTCSessionDescription
# import av
# import time 
# pcs = set()
# from aiortc import MediaStreamTrack
# from av import AudioFrame
# import asyncio


# # class TTSAudioTrack(MediaStreamTrack):
# #     kind = "audio"
# #     def __init__(self):
# #         super().__init__()
# #         self.queue = asyncio.Queue()
# #     async def recv(self):
# #         pcm16 = await self.queue.get()
# #         # pcm16 = mono, s16, 16 kHz
# #         samples = len(pcm16) // 2
# #         frame = AudioFrame(format="s16",layout="mono",samples=samples)
# #         frame.sample_rate = 16000
# #         frame.planes[0].update(pcm16)
# #         output_frames = tts_resampler.resample(frame)
# #         return output_frames

# #     async def put_audio(self, pcm16):
# #         print("📥 TTS queue:", len(pcm16))
# #         await self.queue.put(pcm16)
# from fractions import Fraction
# import asyncio

# from aiortc import MediaStreamTrack, MediaStreamError
# from av import AudioFrame
# import asyncio
# import av

# from fractions import Fraction
# from aiortc import MediaStreamTrack
# from av import AudioFrame

# import asyncio
# import av

# from fractions import Fraction
# from av import AudioFrame
# from aiortc import MediaStreamTrack
# import asyncio
# import av

# from fractions import Fraction
# from av import AudioFrame
# from aiortc import MediaStreamTrack


# class TTSAudioTrack(MediaStreamTrack):
#     kind = "audio"

#     SAMPLE_RATE = 48000

#     # EXACTLY 20 ms
#     SAMPLES = 960
#     BYTES = 1920

#     def __init__(self):
#         super().__init__()

#         self.queue = asyncio.Queue(maxsize=3)

#         self.stopped = True

#         self.timestamp = 0

#         self.resampler = av.AudioResampler(
#             format="s16",
#             layout="mono",
#             rate=48000,
#         )

#         self.buffer = bytearray()

#     # ---------------------------------------------------------
#     # Add 16 kHz PCM
#     # ---------------------------------------------------------

#     async def put_audio(self, pcm16):

#         if self.stopped:
#             return

#         # 20 ms @ 16 kHz
#         CHUNK = 640

#         for i in range(0, len(pcm16), CHUNK):

#             if self.stopped:
#                 return

#             chunk = pcm16[i:i + CHUNK]

#             if len(chunk) != CHUNK:
#                 continue

#             # Don't allow huge TTS buffering
#             try:
#                 self.queue.put_nowait(chunk)
#             except asyncio.QueueFull:
#                 return

#     # ---------------------------------------------------------
#     # START
#     # ---------------------------------------------------------

#     def resume_audio(self):

#         print("▶️ TTS START")

#         self.stopped = False

#     # ---------------------------------------------------------
#     # STOP
#     # ---------------------------------------------------------

#     def stop_audio(self):

#         print("🛑🛑🛑 BARGE-IN")

#         self.stopped = True

#         # Clear Python-side audio immediately
#         while True:
#             try:
#                 self.queue.get_nowait()
#             except asyncio.QueueEmpty:
#                 break

#         # Clear resampler output
#         self.buffer.clear()

#     # ---------------------------------------------------------
#     # SILENCE 20ms
#     # ---------------------------------------------------------

#     def make_silence(self):

#         frame = AudioFrame(
#             format="s16",
#             layout="mono",
#             samples=960,
#         )

#         frame.sample_rate = 48000

#         frame.planes[0].update(
#             b"\x00" * 1920
#         )

#         frame.pts = self.timestamp

#         frame.time_base = Fraction(1, 48000)

#         self.timestamp += 960

#         return frame

#     # ---------------------------------------------------------
#     # WebRTC asks for ONE frame
#     # ---------------------------------------------------------

#     async def recv(self):

#         # ----------------------------------------------
#         # If stopped -> immediately give silence
#         # ----------------------------------------------

#         if self.stopped:
#             return self.make_silence()

#         # ----------------------------------------------
#         # Fill 20ms output buffer
#         # ----------------------------------------------

#         while len(self.buffer) < self.BYTES:

#             if self.stopped:

#                 self.buffer.clear()

#                 return self.make_silence()

#             try:

#                 pcm16 = await asyncio.wait_for(
#                     self.queue.get(),
#                     timeout=0.02
#                 )


#             except asyncio.TimeoutError:

#                 if self.stopped:
#                     return self.make_silence()

#                 continue

#             # ------------------------------------------
#             # 16 kHz frame
#             # ------------------------------------------

#             frame = AudioFrame(
#                 format="s16",
#                 layout="mono",
#                 samples=320,
#             )

#             frame.sample_rate = 16000

#             frame.planes[0].update(pcm16)

#             # ------------------------------------------
#             # 16k -> 48k
#             # ------------------------------------------

#             frames = self.resampler.resample(frame)

#             for f in frames:

#                 self.buffer.extend(
#                     f.planes[0].to_bytes()
#                 )

#         # ----------------------------------------------
#         # EXACTLY 1920 bytes = 20ms @ 48kHz
#         # ----------------------------------------------

#         data = bytes(
#             self.buffer[:self.BYTES]
#         )

#         del self.buffer[:self.BYTES]

#         # ----------------------------------------------
#         # Create EXACTLY 960 samples
#         # ----------------------------------------------

#         frame = AudioFrame(
#             format="s16",
#             layout="mono",
#             samples=960,
#         )

#         frame.sample_rate = 48000

#         frame.planes[0].update(data)

#         frame.pts = self.timestamp

#         frame.time_base = Fraction(1, 48000)

#         self.timestamp += 960
#         print("❤️ send frame to client")

#         return frame

# stt_resampler = av.AudioResampler(
#     format="s16",
#     layout="mono",
#     rate=16000)

# tts_resampler = av.AudioResampler(
#     format="s16",
#     layout="mono",
#     rate=48000)

# async def send_audio(tts_track, full_audio):

#     try:

#         tts_track.resume_audio()

#         await tts_track.put_audio(full_audio)

#     except asyncio.CancelledError:

#         print("🛑 TTS send cancelled")

#         raise


# async def process_audio(track, tts_track):

#     audio_buffer = []
#     task =None
#     # VAD input buffer: float32
#     vad_buffer = np.empty(0, dtype=np.float32)

#     speech_active = False

#     try:

#         while True:

#             frame = await track.recv()

#             frames = stt_resampler.resample(frame)

#             for pcm_frame in frames:

#                 # Original 16-bit PCM
#                 pcm16 = pcm_frame.to_ndarray().tobytes()

#                 # Convert PCM -> float32 for Silero
#                 samples = (
#                     np.frombuffer(
#                         pcm16,
#                         dtype=np.int16
#                     ).astype(np.float32) / 32768.0
#                 )

#                 # ------------------------------------------------
#                 # Keep ORIGINAL PCM for speech buffer
#                 # ------------------------------------------------

#                 if speech_active:
#                     audio_buffer.append(pcm16)

#                 # ------------------------------------------------
#                 # VAD buffer
#                 # ------------------------------------------------

#                 vad_buffer = np.concatenate(
#                     [vad_buffer, samples]
#                 )

#                 # Silero requires exactly 512 samples
#                 while len(vad_buffer) >= 512:

#                     chunk = vad_buffer[:512]

#                     vad_buffer = vad_buffer[512:]

#                     audio = torch.from_numpy(chunk)

#                     result = vad(audio)

#                     print("VAD result:", result)

#                     # --------------------------------------------
#                     # SPEECH START
#                     # --------------------------------------------

#                     if result and "start" in result:

#                         print("🗣️ SPEECH START")

#                         # 1. Stop audio track immediately
#                         tts_track.stop_audio()

#                         # 2. Cancel current TTS generation/task
#                         if task and not task.done():
#                             task.cancel()

#                             try:
#                                 await task
#                             except asyncio.CancelledError:
#                                 pass
                    
#                         task = None

#                         speech_active = True

#                         audio_buffer = [pcm16]

#                     # --------------------------------------------
#                     # SPEECH END
#                     # --------------------------------------------

#                     elif result and "end" in result:

#                         print("🔇 SPEECH END")

#                         if audio_buffer:

#                             complete_audio = b"".join(audio_buffer)

#                             audio_buffer = []

#                             speech_active = False

#                             # VERY IMPORTANT
#                             tts_track.resume_audio()

#                             task = asyncio.create_task(
#                                 send_audio(
#                                     tts_track,
#                                     complete_audio
#                                 )
#                             )
                    

#     except MediaStreamError:

#         print("🛑 Media stream ended")

#     except asyncio.CancelledError:

#         print("🛑 process_audio cancelled")

#         raise

#     except Exception as e:

#         print("❌ process_audio error:", repr(e))

# # async def process_audio(track, tts_track):
# #     audio_buffer = []
# #     vad_buffer = np.empty(0, dtype=np.float32)

# #     try:

# #         while True:

# #             frame = await track.recv()

# #             frames = stt_resampler.resample(frame)

# #             for pcm_frame in frames:

# #                 # s16 PCM
# #                 pcm16 = pcm_frame.to_ndarray().tobytes()

# #                 print("len pcm16:", len(pcm16))

# #                 # bytes -> int16 samples -> float32
# #                 samples = (
# #                     np.frombuffer(
# #                         pcm16,
# #                         dtype=np.int16
# #                     ).astype(np.float32) / 32768.0
# #                 )

# #                 print("samples:", len(samples))

# #                 # Add samples to buffer
# #                 vad_buffer = np.concatenate(
# #                     [vad_buffer, samples]
# #                 )

# #                 # Process EXACTLY 512 samples
# #                 while len(vad_buffer) >= 512:

# #                     chunk = vad_buffer[:512]

# #                     # Keep remaining samples
# #                     vad_buffer = vad_buffer[512:]

# #                     audio = torch.from_numpy(chunk)

# #                     # Silero
# #                     result = vad(audio) # return only start and end trigger
# #                     print("VAD result:", result)
# #                     



# #     except Exception as e:

# #         print("❌ process_audio error:", repr(e))
# # # Now closing the browser/WebRTC connection won't produce the ugly unhandled task exception.            








#                       # WEBRTC WEBSOCKET



# @app.websocket("/webrtc")
# async def echo_voice(ws:WebSocket):
#     await ws.accept()
#     pc = None
#     process_task=None
#     # pc = RTCPeerConnection()
#     # pcs.add(pc)
#     # tts_track = TTSAudioTrack()
#     # pc.addTrack(tts_track)

#     # @pc.on("track")
#     # def on_track(track):
#     #     print('track received',track.kind)
#     #     pc.addTrack(track) #echo media track
#     #     @track.on("ended")
#     #     async def on_ended():
#     #         print("Track ended:", track.kind)

#     # @pc.on("connectionstatechange")
#     # async def on_connectionstatechange():
#     #     print("Connection state:", pc.connectionState)
#     #     if pc.connectionState in ("failed", "closed", "disconnected"):
#     #         await pc.close()
#     #         pcs.discard(pc)
#     try:
#         while True:
#             data = await ws.receive()
#             if data["type"] == "websocket.disconnect":
#                 print("🛑 Client disconnected")
#                 break
#             # Handle your data here
#             if data["type"] == "websocket.receive":
#                 if "text" in data:                     #text/json handle here.    
#                     message = json.loads(data["text"])
#                     if message['type']=='offer':
#                         if pc is None or pc.connectionState == "closed":
#                             pc = RTCPeerConnection()
#                             pcs.add(pc)
#                             @pc.on("track")
#                             def on_track(track):
#                                 nonlocal process_task
#                                 print("🎤 Track received:", track.kind)                              
#                                 # pc.addTrack(track)
#                                 if track.kind=="audio":
#                                     tts_track = TTSAudioTrack()
#                                     pc.addTrack(tts_track)
#                                     process_task= asyncio.create_task(process_audio(track,tts_track))

#                             @pc.on("connectionstatechange")
#                             async def on_connectionstatechange():
#                                 nonlocal process_task
#                                 print("Connection state:", pc.connectionState)
#                                 if pc.connectionState in ("failed", "closed", "disconnected"):
#                                     await pc.close()
#                                     if process_task is not None:
#                                         if not process_task.done():
#                                             process_task.cancel()
#                                             process_task = None

#                         print("offer webrtc connection 🟢")
#                         offer = RTCSessionDescription(sdp=message['sdp'],type="offer")
#                         await pc.setRemoteDescription(offer)
#                         answer = await pc.createAnswer()
#                         await pc.setLocalDescription(answer)
#                         await ws.send_json({'type':'answer','sdp':pc.localDescription.sdp})
#     except WebSocketDisconnect:
#         print("🛑 WebSocket disconnected")

#     finally:
#         print("🧹 Cleaning up peer connection")
#         await pc.close()
#         pcs.discard(pc)
#         if process_task is not None:
#             process_task.cancel()
#             process_task = None
















# from aiortc import MediaStreamTrack,MediaStreamError,RTCPeerConnection ,RTCSessionDescription
# from av import AudioFrame,AudioResampler
# import asyncio
# import numpy as np
# import torch
# from silero_vad import load_silero_vad,VADIterator

# model = load_silero_vad()
# vad = VADIterator(
#     model,
#     sampling_rate=16000,
#     threshold=0.7,
#     min_silence_duration_ms=1000,
#     speech_pad_ms=100,
# )

# pcs = set()


# stt_resampler = AudioResampler(
#     format="s16",
#     layout="mono",
#     rate=16000)

# tts_resampler = AudioResampler(
#     format="s16",
#     layout="mono",
#     rate=48000)


# # class TTSAudioTrack(MediaStreamTrack):
# #     kind = "audio"
# #     def __init__(self):
# #         super().__init__()
# #         self.queue = asyncio.Queue()
# #     async def recv(self):
# #         pcm16 = await self.queue.get()
# #         frame = AudioFrame(format="s16",layout="mono",samples=len(pcm16)//2)
# #         frame.sample_rate = 16000
# #         frame.planes[0].update(pcm16)
# #         frame = tts_resampler.resample(frame)
# #         return frame[0]
        
# #     async def put_audio(self, pcm16):
# #         print("len(pcm16)",len(pcm16))
# #         await self.queue.put(pcm16)
# from fractions import Fraction

# class TTSAudioTrack(MediaStreamTrack):
#     kind = "audio"
#     def __init__(self):
#         super().__init__()
#         self.queue = asyncio.Queue()
#         self.timestamp = 0
#     async def recv(self):
#         # 640 bytes = 320 samples = 20 ms @ 16 kHz
#         pcm16 = await self.queue.get()
#         frame = AudioFrame(format="s16",layout="mono",samples=len(pcm16) // 2)
#         frame.sample_rate = 16000
#         frame.planes[0].update(pcm16)
#         output_frames = tts_resampler.resample(frame)
#         if not output_frames:
#             return await self.recv()
#         output = output_frames[0]
#         # 48 kHz RTP timestamp
#         output.pts = self.timestamp
#         output.time_base = Fraction(1, 48000)
#         self.timestamp += output.samples
#         print("📤 sending:",output.samples,output.sample_rate,output.pts)
#         return output

#     async def put_audio(self, pcm16):
#         CHUNK = 640  # 20 ms @ 16 kHz
#         for i in range(0, len(pcm16), CHUNK):
#             chunk = pcm16[i:i + CHUNK]
#             if len(chunk) != CHUNK:
#                 continue
#             print("📥 queue:", len(chunk))
#             await self.queue.put(chunk)


# async def process_audio(track,tts_track):
#     vad_buffer = np.empty(0, dtype=np.float32)
#     audio_buffer = []
#     speech_active = False
#     try:
#         while True:
#             frame = await track.recv() # sign int16 , mono ,sample rate 48khz from browser 
#             # print(type(frame)) # <class 'av.audio.frame.AudioFrame'>
#             frames  = stt_resampler.resample(frame)  #webrtc send class av.audio.frame.AudioFrame audio class and av.AudioResmpler use for resampling to 16khz s16 for stt model trascriptin speech
#             for pcm_frame in frames:
#                 # S16 PCM
#                 pcm16=pcm_frame.to_ndarray().tobytes()
#                 if speech_active:
#                     audio_buffer.append(pcm16) # for 960 sample place here
#                 # await tts_track.put_audio(pcm16)
#                 pcm32 = np.frombuffer(pcm16,dtype=np.int16).astype(np.float32) / 32768.0
#                 vad_buffer = np.concatenate([vad_buffer,pcm32])
#                 if len(vad_buffer)>=512:
#                     chunk = vad_buffer[:512]
#                     vad_buffer = vad_buffer[512:]
#                     audio = torch.from_numpy(chunk)

#                     result = vad(audio)
#                     print(result)
#                     if result:
#                         if "start" in result:
#                             print('speech start🟢')
#                             speech_active = True
#                             audio_buffer.append(pcm16)
#                         if "end" in result:
#                             print("stop speak 🛑 ")
#                             speech_active = False
#                             complete_audio = b"".join(audio_buffer) 
#                             await tts_track.put_audio(complete_audio)
#                             # run asyncio.createa_task() that stt -> llm - > tts
#                             audio_buffer = []
                   
#     except MediaStreamError as e:
#         print(e)



# import asyncio
# from fractions import Fraction
# from aiortc import MediaStreamError, MediaStreamTrack
# from av import AudioFrame, AudioResampler
# import numpy as np
# import torch
# from silero_vad import VADIterator, load_silero_vad

# model = load_silero_vad()
# vad = VADIterator(
#     model,
#     sampling_rate=16000,
#     threshold=0.7,
#     min_silence_duration_ms=1000,
#     speech_pad_ms=100,
# )

# stt_resampler = AudioResampler(format="s16", layout="mono", rate=16000)
# tts_resampler = AudioResampler(format="s16", layout="mono", rate=48000)


# class TTSAudioTrack(MediaStreamTrack):
#     kind = "audio"

#     def __init__(self):
#         super().__init__()
#         self.queue = asyncio.Queue()
#         self.timestamp = 0

#     async def recv(self):
#         pcm16 = await self.queue.get()
#         frame = AudioFrame(format="s16", layout="mono", samples=len(pcm16) // 2)
#         frame.sample_rate = 16000
#         frame.planes[0].update(pcm16)

#         output_frames = tts_resampler.resample(frame)
#         if not output_frames:
#             return await self.recv()

#         output = output_frames[0]
#         output.pts = self.timestamp
#         output.time_base = Fraction(1, 48000)
#         self.timestamp += output.samples

#         # Pace the output stream to match real-time duration (20ms for 960 samples @ 48kHz)
#         await asyncio.sleep(output.samples / 48000)

#         return output

#     async def put_audio(self, pcm16):
#         CHUNK = 640  # 20 ms @ 16 kHz (320 samples * 2 bytes)
#         for i in range(0, len(pcm16), CHUNK):
#             chunk = pcm16[i : i + CHUNK]
#             if len(chunk) == CHUNK:
#                 await self.queue.put(chunk)

#     async def clear_audio():
#         #clear queue for barge-in


# async def process_audio(track, tts_track):
#     vad_buffer = np.empty(0, dtype=np.float32)
#     raw_pcm_buffer = bytearray()
#     audio_buffer = []
#     speech_active = False

#     try:
#         while True:
#             frame = await track.recv()
#             frames = stt_resampler.resample(frame)

#             for pcm_frame in frames:
#                 pcm16 = pcm_frame.to_ndarray().tobytes()
#                 raw_pcm_buffer.extend(pcm16)

#                 # Convert to Float32 for Silero VAD
#                 pcm32 = (
#                     np.frombuffer(pcm16, dtype=np.int16).astype(np.float32)
#                     / 32768.0
#                 )
#                 vad_buffer = np.concatenate([vad_buffer, pcm32])

#                 # Process 512-sample windows for VAD (32ms at 16kHz)
#                 while len(vad_buffer) >= 512:
#                     chunk_float = vad_buffer[:512]
#                     vad_buffer = vad_buffer[512:]

#                     # Extract corresponding raw bytes (512 samples * 2 bytes = 1024 bytes)
#                     chunk_bytes = bytes(raw_pcm_buffer[:1024])
#                     del raw_pcm_buffer[:1024]

#                     # Append to active speech buffer
#                     if speech_active:
#                         audio_buffer.append(chunk_bytes)

#                     audio_tensor = torch.from_numpy(chunk_float)
#                     result = vad(audio_tensor)

#                     if result:
#                         if "start" in result:
#                             #when user speak than barge-in tts-track.clear_audio()
#                             print("speech start 🟢")
#                             speech_active = True
#                             # Ensure the starting window is included
#                             if chunk_bytes not in audio_buffer:
#                                 audio_buffer.append(chunk_bytes)

#                         if "end" in result:
#                             print("speech stop 🛑")
#                             speech_active = False
#                             complete_audio = b"".join(audio_buffer)
#                             await tts_track.put_audio(complete_audio)
#                             audio_buffer = []

    # except MediaStreamError as e:
    #     print("MediaStream error:", e)

import asyncio
from fractions import Fraction
from aiortc import MediaStreamError, MediaStreamTrack
from av import AudioFrame, AudioResampler
import numpy as np
import torch
from silero_vad import VADIterator, load_silero_vad

model = load_silero_vad()
vad = VADIterator(
    model,
    sampling_rate=16000,
    threshold=0.8,
    min_silence_duration_ms=1000,
    speech_pad_ms=500,
    
)

stt_resampler = AudioResampler(format="s16", layout="mono", rate=16000)
tts_resampler = AudioResampler(format="s16", layout="mono", rate=48000)


class TTSAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self):
        super().__init__()
        self.queue = asyncio.Queue()
        self.timestamp = 0

    async def recv(self):
        try:
            # Wait up to 20ms for audio; if empty, send silence to keep clock synced
            pcm16 = await asyncio.wait_for(self.queue.get(), timeout=0.02)
        except asyncio.TimeoutError:
            # 20ms of silence at 16kHz (320 samples * 2 bytes)
            pcm16 = b"\x00" * 640

        frame = AudioFrame(format="s16", layout="mono", samples=len(pcm16) // 2)
        frame.sample_rate = 16000
        frame.planes[0].update(pcm16)

        output_frames = tts_resampler.resample(frame)
        if not output_frames:
            return await self.recv()

        output = output_frames[0]
        output.pts = self.timestamp
        output.time_base = Fraction(1, 48000)
        self.timestamp += output.samples

        # Real-time pacing (20ms per 960 samples @ 48kHz)
        await asyncio.sleep(output.samples / 48000)

        return output

    async def put_audio(self, pcm16):
        CHUNK = 640  # 20 ms @ 16 kHz
        for i in range(0, len(pcm16), CHUNK):
            chunk = pcm16[i : i + CHUNK]
            if len(chunk) == CHUNK:
                await self.queue.put(chunk)

    def clear_audio(self):
        """Flushes queued TTS audio immediately for barge-in support."""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break

import asyncio
from fractions import Fraction
from aiortc import MediaStreamTrack
from av import AudioFrame


# class TTSAudioTrack(MediaStreamTrack):
#     kind = "audio"

#     def __init__(self):
#         super().__init__()
#         self.queue = asyncio.Queue()
#         self.timestamp = 0

#     async def recv(self):
#         try:
#             # Wait up to 20ms for a 48kHz AudioFrame
#             frame = await asyncio.wait_for(self.queue.get(), timeout=0.02)
#         except asyncio.TimeoutError:
#             # Generate 20ms silent frame at 48kHz mono (960 samples * 2 bytes = 1920 bytes)
#             frame = AudioFrame(format="s16", layout="mono", samples=960)
#             frame.sample_rate = 48000
#             frame.planes[0].update(b"\x00" * 1920)

#         # Set presentation timestamp for WebRTC clock sync
#         frame.pts = self.timestamp
#         frame.time_base = Fraction(1, 48000)
#         self.timestamp += frame.samples

#         return frame

#     async def put_audio(self, frame: AudioFrame):
#         """Chunk a large 48kHz AudioFrame into 20ms (960-sample) frames for queueing."""
#         # raw_pcm = frame.planes[0].to_bytes()
#         raw_pcm = bytes(frame.planes[0])

#         # 20ms chunk size @ 48kHz mono s16 = 960 samples * 2 bytes = 1920 bytes
#         CHUNK_SIZE = 1920
#         SAMPLES_PER_CHUNK = 960

#         for i in range(0, len(raw_pcm), CHUNK_SIZE):
#             chunk_bytes = raw_pcm[i : i + CHUNK_SIZE]

#             # If chunk is complete 20ms frame
#             if len(chunk_bytes) == CHUNK_SIZE:
#                 sub_frame = AudioFrame(
#                     format="s16", layout="mono", samples=SAMPLES_PER_CHUNK
#                 )
#                 sub_frame.sample_rate = 48000
#                 sub_frame.planes[0].update(chunk_bytes)
#                 await self.queue.put(sub_frame)

#     def clear_audio(self):
#         """Flushes queued audio frames immediately for barge-in support."""
#         while not self.queue.empty():
#             try:
#                 self.queue.get_nowait()
#             except asyncio.QueueEmpty:
#                 break

def process_piper_chunk(chunk, target_sr: int = 16000, source_sr: int = 22050) -> bytes:
    """Converts a Piper AudioChunk float32 array into 16kHz s16 PCM bytes."""
    float_samples = chunk.audio_float_array
    # 1. Resample from Piper's 22050 Hz to the track's 16000 Hz target
    if source_sr != target_sr:
        num_target_samples = int(len(float_samples) * target_sr / source_sr)
        float_samples = scipy.signal.resample(
            float_samples, num_target_samples
        )
    # 2. Clip values to avoid audio clipping distortion [-1.0, 1.0]
    float_samples = np.clip(float_samples, -1.0, 1.0)
    # 3. Scale float32 [-1.0, 1.0] to int16 range [-32768, 32767]
    int16_samples = (float_samples * 32767).astype(np.int16)
    # 4. Return raw PCM bytes
    return int16_samples.tobytes()

import numpy as np
import scipy.signal
from av import AudioFrame





# def pcm_to_wav_io(
#     pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1
# ) -> io.BytesIO:
#     """Wraps raw s16 PCM bytes into an in-memory WAV file for Groq API."""
#     wav_io = io.BytesIO()
#     # Crucial: Groq inspects the filename extension to detect format
#     wav_io.name = "audio.wav"

#     with wave.open(wav_io, "wb") as wav_file:
#         wav_file.setnchannels(channels)
#         wav_file.setsampwidth(2)  # 16-bit PCM (2 bytes/sample)
#         wav_file.setframerate(sample_rate)
#         wav_file.writeframes(pcm_bytes)

#     wav_io.seek(0)
#     return wav_io


# # --- Inside your agent async function ---
# async def transcribe_audio(complete_audio: bytes) -> str:
#     if not complete_audio:
#         return ""

#     # Convert PCM bytes -> in-memory WAV
#     wav_file = pcm_to_wav_io(complete_audio, sample_rate=16000)

#     # Async Groq API Call
#     transcription = await client.audio.transcriptions.create(
#         file=wav_file,
#         model="whisper-large-v3-turbo",
#         temperature=0,
#         response_format="verbose_json",
#         language="en",
#     )

#     # Output text string
#     print(transcription.text)
#     return transcription.text


# def process_piper_chunk(chunk, target_sr: int = 48000, source_sr: int = 22050) -> AudioFrame:
#     """Converts a Piper AudioChunk float32 array into a 48kHz s16 PyAV AudioFrame."""
#     float_samples = chunk.audio_float_array

#     # 1. Resample from Piper source_sr (22050) to target_sr (48000)
#     if source_sr != target_sr:
#         num_target_samples = int(len(float_samples) * target_sr / source_sr)
#         float_samples = scipy.signal.resample(float_samples, num_target_samples)

#     # 2. Clip values to prevent audio distortion [-1.0, 1.0]
#     float_samples = np.clip(float_samples, -1.0, 1.0)

#     # 3. Convert float32 -> int16
#     int16_samples = (float_samples * 32767).astype(np.int16)

#     # 4. Construct PyAV AudioFrame
#     frame = AudioFrame(
#         format="s16",
#         layout="mono",
#         samples=len(int16_samples)
#     )
#     frame.sample_rate = target_sr
    
#     # 5. Write PCM bytes directly into the PyAV memory plane
#     frame.planes[0].update(int16_samples.tobytes())

#     return frame

async def agent_run_webrtc(complete_audio,tts_track,websocket):
    agent = websocket.app.state.conv_agent
    voice = websocket.app.state.voice
    try:
        # await tts_track.put_audio(complete_audio)
        audio_int16 = np.frombuffer(complete_audio, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        audio_np = np.squeeze(audio_float32)

        segments, _ = whisper_model.transcribe(audio_np, beam_size=2, language="hi")

        # 3. Combine text segments
        transcription = " ".join([segment.text.strip() for segment in segments])
        # transcription =await transcribe_audio(complete_audio) 
        print("🟡 transciption",transcription)
        if websocket and transcription.strip():
            await websocket.send_json({"event": "transcription", "data": transcription})
        sentence =""
        async for types,chunk in agent.astream(input={"messages":[HumanMessage(content=transcription.strip())]},config={"configurable":{"thread_id":'55'}},stream_mode=['values','custom']):
            print(chunk)
            if types=="custom":
                sentence += chunk.content
                if  sentence.endswith((".", "?", "!")):
                    print("🌈 sentence complate",sentence)
                    for audio_chunk in voice.synthesize(sentence):
                        # print(type(audio_chunk))
                        # print(audio_chunk)
                        frame = process_piper_chunk(audio_chunk, target_sr=16000, source_sr=audio_chunk.sample_rate)
                        await tts_track.put_audio(frame)
                    sentence=""
                await websocket.send_json(jsonable_encoder({"event":'stream' ,"stream" :chunk}))
            if types=="values":
                await websocket.send_json(jsonable_encoder({"event":'state' ,"state" :chunk}))



        
    except asyncio.CancelledError as e:
        # tts_track.clear_audio()
        pass



async def process_audio(track, tts_track,websocket):
    vad_buffer = np.empty(0, dtype=np.float32)
    raw_pcm_buffer = bytearray()
    audio_buffer = []
    speech_active = False
    agent_task =None

    try:
        while True:
            frame = await track.recv()
            frames = stt_resampler.resample(frame)

            for pcm_frame in frames:
                pcm16 = pcm_frame.to_ndarray().tobytes()
                raw_pcm_buffer.extend(pcm16)

                pcm32 = (np.frombuffer(pcm16, dtype=np.int16).astype(np.float32)/ 32768.0)
                vad_buffer = np.concatenate([vad_buffer, pcm32])

                while len(vad_buffer) >= 512:
                    chunk_float = vad_buffer[:512]
                    vad_buffer = vad_buffer[512:]

                    chunk_bytes = bytes(raw_pcm_buffer[:1024])
                    del raw_pcm_buffer[:1024]

                    if speech_active:
                        audio_buffer.append(chunk_bytes)

                    audio_tensor = torch.from_numpy(chunk_float)
                    result = vad(audio_tensor)

                    if result:
                        if "start" in result:
                            print("speech start 🟢 (Barge-in triggered)")
                            tts_track.clear_audio()
                            if agent_task is not None and not agent_task.done():
                                agent_task.cancel()
                                try:
                                    await agent_task
                                except asyncio.CancelledError:
                                    pass
                            agent_task=None
                            speech_active = True
                            
                            # Interrupt current TTS playback immediately
                            if chunk_bytes not in audio_buffer:
                                audio_buffer.append(chunk_bytes)

                        if "end" in result:
                            print("speech stop 🛑")
                            speech_active = False
                            complete_audio = b"".join(audio_buffer)
                            # await tts_track.put_audio(complete_audio)
                            agent_task= asyncio.create_task(agent_run_webrtc(complete_audio,tts_track,websocket))
                            audio_buffer = []

    except MediaStreamError as e:
        print("MediaStream error:", e)
        if agent_task is not None:
            agent_task.cancel()
            try:
                await agent_task
            except asyncio.CancelledError:
                pass
            agent_task =None


# process audio for cusotm vad
# silence=1
# audio_buffer=[]
# start_buffer=False
# start_silence=None
# if vad(track):
#     start_buffer=True
#     start_silence = None
#     audio_buffer.append(track)
# else:
#     if start_buffer :
#         if start_silence is None:
#             start_silence=time.time()
#         audio_buffer.append(track)
#         if time.time()-start_silence >silence:
#             start_buffer=False
#             start_silence = None
#             asyncio.create_task(agent_run(audio_buffer))
#             audio_buffer=[]

@app.websocket("/webrtc")
async def webrtc(ws:WebSocket):
    await ws.accept()
    pc =None
    process_task=None
    try:
        while True:
            data = await ws.receive()
            if data['type']=="websocket.disconnect":
                print('ws disconnect')
                break
            if data['type']=="websocket.receive":
                # here text/json handle
                if "text" in data:
                    message = json.loads(data['text'])
                    print("message",message)
                    if message['type']=='offer':
                        if pc is None or pc.connectionState == "closed":
                            pc =RTCPeerConnection()
                            pcs.add(pc)
                            @pc.on("track")
                            def on_track(track):
                                # nonlocal process_task
                                nonlocal process_task
                                print("🎤 Track received:", track.kind)                              
                                # pc.addTrack(track) #echo audio track
                                if track.kind=="audio":
                                    tts_track = TTSAudioTrack()
                                    pc.addTrack(tts_track)
                                    process_task= asyncio.create_task(process_audio(track,tts_track,ws))

                            print("offer webrtc connection 🟢")
                            offer = RTCSessionDescription(sdp=message['sdp'],type="offer")
                            await pc.setRemoteDescription(offer)
                            answer = await pc.createAnswer()
                            await pc.setLocalDescription(answer)
                            await ws.send_json({'type':'answer','sdp':pc.localDescription.sdp})


    except WebSocketDisconnect as e:
        print("error",e)
        if process_task is not None:
            process_task.cancel()

