
let ws = null;


export const websocketStart = (url) => (dispatch) => {
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


export const sendMessage = (type, data) => (dispatch) => {
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

export const stopTask=()=>(dispatch)=>{  dispatch(sendMessage("stop", "cancel running task")); } 

export const stopWebsocket = () => (dispatch) => {
  if (!ws) {
    return;
  }

  ws.close();
  ws = null;

};