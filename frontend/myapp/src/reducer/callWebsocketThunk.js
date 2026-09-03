let ws = null;

export const callwebsocketStart = (url) => (dispatch) => {
  if (ws) {
    console.log("WebSocket already connected");
    return;
  }

  ws = new WebSocket(url);

  ws.onopen = () => {
    console.log("WebSocket connected");
  };

  ws.onmessage = (event) => {
    console.log("WebSocket message:", event.data);
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
  };

  ws.onclose = () => {
    console.log("WebSocket closed");
    ws = null;
  };
};


export const sendAudio = (type, data) => (dispatch) => {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.log("WebSocket is not connected");
    return;
  }

  ws.send(
    JSON.stringify({
      type,
      data
    })
  );

  console.log("sent:", {
    type,
    data
  });
};

export const stopCall=()=>(dispatch)=>{  dispatch(sendAudio("stop", "cancel running task")); } 
export const pauseCall=()=>(dispatch)=>{  dispatch(sendAudio("stop", "cancel running task")); } 


export const stopCallWebsocket = () => (dispatch) => {
  if (!ws) {
    return;
  }

  ws.close();
  ws = null;

};