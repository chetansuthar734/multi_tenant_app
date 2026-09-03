from fastapi import APIRouter,Request,WebSocket,WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
import numpy as np
import scipy.signal
from av import AudioFrame,AudioResampler
from langchain_core.messages import HumanMessage
import asyncio
from fractions import Fraction
from aiortc import MediaStreamError, MediaStreamTrack,RTCPeerConnection,RTCSessionDescription
from av import AudioFrame, AudioResampler
import numpy as np
import torch
import json
import io
from faster_whisper import WhisperModel
from silero_vad import VADIterator, load_silero_vad
from piper import PiperVoice
import asyncio
from fractions import Fraction
from aiortc import MediaStreamTrack
from av import AudioFrame
import numpy as np
import os



router = APIRouter(
    prefix="/voice",
    tags=["Chat"]
)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
pcs = set()
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
# voice = PiperVoice.load("en_US-lessac-medium.onnx")

#  process audio for cusotm vad
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




@router.websocket("/webrtc")
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

