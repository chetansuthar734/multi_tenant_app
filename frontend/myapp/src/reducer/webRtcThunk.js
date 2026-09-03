import { pauseTimer, resumeTimer, startTimer, stopTimer } from "./TimerThunk"
let ws =null
let pc =null
let stream = null

  
export const startWebsocket=()=>async(dispatch)=>{
    if (ws){console.log("already connecrt ws and pc");return}

     const api = process.env.REACT_APP_WEBSOCKET_API
     ws = new WebSocket(`${api}/voice/webrtc`)
     await new Promise((resolve, reject) => {
      ws.onopen = () => {console.log("🟢 WebSocket connected");resolve();};
      ws.onerror = (error) => {console.error("❌ WebSocket connection failed");reject(error);};
    });
    console.log("✅ startWebsocket() finished");   

  ws.onmessage=async(event)=>{
        const msg = JSON.parse(event.data)
        console.log("🟢",msg)
        if (msg.type==='answer')await pc.setRemoteDescription(msg)
        }
      
  ws.onclose = () => {console.log("🔴 WebSocket disconnected");
    dispatch(stopWebRTC())
    ws = null
      if (pc) {
      pc.close();
      pc = null;}
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());stream = null;
      }}
    }
    

    
    
export const startWebRTC=()=> async(dispatch)=>{
  if (!ws) {console.log("error WebSocket/PeerConnection");
    await dispatch(startWebsocket());}
  if (pc) {console.log("⚠️ WebRTC already running");return;}
      
  pc = new RTCPeerConnection({iceServers: [{urls: "stun:stun.l.google.com:19302"}]});
  // stream = await navigator.mediaDevices.getUserMedia({audio:true,video:false})
  stream = await navigator.mediaDevices.getUserMedia({  audio: {echoCancellation: true,noiseSuppression: true,autoGainControl: true},video: false});
  pc.addTransceiver("audio", {direction: "sendrecv"});  

  stream.getTracks().forEach(track=>pc.addTrack(track,stream)) 
  pc.ontrack = (event) => {
       const audio = new Audio();
       audio.autoplay = true;
       audio.srcObject = event.streams[0];
       audio.play();
       document.body.appendChild(audio);
      };
  pc.onicecandidate=(event)=>{ if (event.candidate)ws.send(JSON.stringify({type:"candidate",candidate:event.candidate}))}

  const offer= await pc.createOffer()
  await pc.setLocalDescription(offer)
  ws.send(JSON.stringify({type:'offer',sdp:offer.sdp}))
  dispatch(startTimer())
}


export  const stopWebRTC=()=>(dispatch)=>{
  dispatch(stopTimer())
  if(stream){
    stream.getTracks().forEach((track)=>track.stop());
    stream=null
  }
  if(pc){
    pc.close();
    ws.close()
    ws=null
    pc=null

  } 
  }

export  const pauseWebRTC=()=>(dispatch)=>{
  if(stream){
    stream.getTracks().forEach((track)=>{track.enabled=false});
    dispatch(pauseTimer())
  }}

export  const resumeWebRTC=()=>(dispatch)=>{
  if(stream){
    stream.getTracks().forEach((track)=>track.enabled=true);
    dispatch(resumeTimer())
   }
  }
