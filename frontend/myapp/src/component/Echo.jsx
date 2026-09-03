
import { useRef, useState } from "react";
import { Upload, Button, Progress, message } from "antd";
import { UploadOutlined } from "@ant-design/icons";

function App() {
  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const remoteAudioRef = useRef(null);
  const [fileList, setFileList] = useState([]);
  const pcRef = useRef(null);
  const wsRef = useRef(null);
  const streamRef = useRef(null);

  const [connected, setConnected] = useState(false);
const [muted, setMuted] = useState(false);
const [micMuted, setMicMuted] = useState(false);
const [videoMuted, setVideoMuted] = useState(false);

const soundMute = () => {
  if (remoteAudioRef.current) {
    remoteAudioRef.current.muted = !remoteAudioRef.current.muted;
    setMuted(remoteAudioRef.current.muted);
  }
};
const toggleMic = () => {
  const micTrack = streamRef.current?.getAudioTracks()[0];

  if (micTrack) {
    micTrack.enabled = !micTrack.enabled;
    setMicMuted(!micTrack.enabled);
  }
};


const props = {
  name: "files",
  action: "http://localhost:9000/uploadfiles",

  fileList: fileList,

  progress: {
    strokeWidth: 30,
    showInfo: true,
    format: (percent) => `${percent.toFixed(0)}%`,
  },

  showUploadList: {
    showRemoveIcon: false,
  },

  onChange(info) {
    setFileList(info.fileList);

    const { status } = info.file;

    if (status === "uploading") {
      console.log(
        "Progress:",
        info.file.percent
      );
    }

    if (status === "done") {
      message.success(
        `${info.file.name} uploaded successfully`
      );
    }

    if (status === "error") {
      message.error(
        `${info.file.name} upload failed`
      );
    }
  },
};
const toggleVideo = () => {
  const videoTrack = streamRef.current?.getVideoTracks()[0];

  if (videoTrack) {
    videoTrack.enabled = !videoTrack.enabled;
    setVideoMuted(!videoTrack.enabled);
  }
};

  const start = async () => {
    // 1. Get camera + microphone
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true
    //   {
    //     echoCancellation: true,
    //     noiseSuppression: true,
    //     autoGainControl: true,
    //   },
    });

    streamRef.current = stream;
    localVideoRef.current.srcObject = stream;

    // 2. Create native RTCPeerConnection
    const pc = new RTCPeerConnection();

    pcRef.current = pc;

    // 3. Add local camera + microphone
    stream.getTracks().forEach((track) => {
      pc.addTrack(track, stream);
    });

    // 4. Receive echo stream from FastAPI
  pc.ontrack = (event) => {
  console.log("Remote track:", event.track.kind);
 const remoteStrea = event.streams[0];

  remoteVideoRef.current.srcObject = remoteStrea;

  if (event.track.kind === "audio") {
    const [remoteStream] = event.streams;

    if (remoteStream && remoteAudioRef.current) {
       remoteAudioRef.current.srcObject = remoteStream;
    }
  }
};

    // 5. ICE candidate
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        wsRef.current.send(
          JSON.stringify({
            type: "candidate",
            candidate: event.candidate,
          })
        );
      }
    };

    // 6. WebSocket signaling
    const ws = new WebSocket(
      "ws://localhost:9000/echo"
    );

    wsRef.current = ws;

    ws.onopen = async () => {
      console.log("Signaling connected");

      // 7. Create SDP offer
      const offer = await pc.createOffer();

      // 8. Set local SDP
      await pc.setLocalDescription(offer);

      // 9. Send offer to FastAPI
      ws.send(
        JSON.stringify({
          type: "offer",
          sdp: offer.sdp,
        })
      );
    };

    // 10. Receive signaling messages
    ws.onmessage = async (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "answer") {
        await pc.setRemoteDescription({
          type: "answer",
          sdp: data.sdp,
        });
      }

      if (data.type === "candidate") {
        await pc.addIceCandidate(
          data.candidate
        );
      }
    };

    pc.onconnectionstatechange = () => {
      console.log(
        "Connection:",
        pc.connectionState
      );

      if (pc.connectionState === "connected") {
        setConnected(true);
      }

      if (
        pc.connectionState === "failed" ||
        pc.connectionState === "closed"
      ) {
        setConnected(false);
      }
    };
  };

  const stop = () => {
    pcRef.current?.close();
    wsRef.current?.close();

    streamRef.current
      ?.getTracks()
      .forEach((track) => track.stop());

    localVideoRef.current.srcObject = null;
    // remoteVideoRef.current.srcObject = null;
    remoteAudioRef.current.srcObject = null;

    pcRef.current = null;
    wsRef.current = null;
    streamRef.current = null;

    setConnected(false);
  };

  return (
    <div>
      <h2>Native RTCPeerConnection Echo</h2>

      <button onClick={start} disabled={connected}>
        Start
      </button>

      <button onClick={stop}>
        Stop
      </button>

      <div
        style={{
          display: "flex",
          gap: 20,
          marginTop: 20,
        }}
      >
        <div>
          <h3>Local</h3>

          <video
            ref={localVideoRef}
            autoPlay
            muted
            playsInline
            width="400"
          />
        </div>

        <div>
          <h3>Echo / Remote</h3>
             <video
            ref={remoteVideoRef}
            autoPlay
            muted
            playsInline
            width="400"
          />
           <audio ref={remoteAudioRef} autoPlay></audio> 
          
        </div>
      </div>
        <button onClick={toggleMic} style={{fontSize:'50px'}}>{micMuted ? "🔇 Unmute Mic" : "🎤 Mute Mic"}</button>
        <button onClick={soundMute} style={{fontSize:'50px'}}>{muted ? "🔇 Unmute" : "🔊 Mute"}</button>
        <button onClick={toggleVideo} style={{fontSize:'50px'}}>{videoMuted ? "📷 Turn Camera On" : "📷 Turn Camera Off"}</button>
       
       <Upload
  {...props}
  showUploadList={false}
>
  <Button icon={<UploadOutlined />}>
    Upload File
  </Button>
</Upload>

{fileList.map((file) => (
  <div key={file.uid} style={{ width: 500 }}>
    <div>{file.name}</div>

    <Progress
      percent={
        file.status === "done"
          ? 100
          : Math.round(file.percent || 0)
      }
      status={
        file.status === "error"
          ? "exception"
          : undefined
      }
    />
  </div>
))}
    </div>
  );
}

export default App;