import { setState } from "./stateSlice"
// import { setConfig } from "./configSlice"
import { setStream, clearStream } from "./streamSlice";

import { setAgentStatus,AgentState } from "./AgentStatusSlice";






let ws = null;

export const startWs = (data) =>async (dispatch) => {
  const api = `${process.env.REACT_APP_WEBSOCKET_API}/ws`
  if (ws && (ws.readyState === WebSocket.OPEN ||ws.readyState === WebSocket.CONNECTING)) {return;}

  ws = new WebSocket(api);

  ws.onopen = () => {
    console.log("WebSocket connected"); 
    dispatch(setAgentStatus(AgentState.IDLE))
    ws.send(JSON.stringify({event:AgentState.CONNECT}))
    ws.send(JSON.stringify(data))
  };

  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);


    if (data.event === "connection") {
        console.log("connect success",data)
    }
  
      if (data.event === "stream") {
        console.log("WS stream:", data);     
        dispatch(setAgentStatus(AgentState.RUNNING))
      dispatch(setStream(data.stream));
    }

    if (data.event === "state") {
      console.log("WS state messasge:", data);
        // dispatch(setAgentStatus(AgentState.RUNNING))
      dispatch(clearStream());
      dispatch(setState(data.data.state))
      dispatch({type:'removeMessages'})
    }
    if (data.event === "monitor") {
      console.log("WS monitior token messasge:", data);
        // dispatch(setAgentStatus(AgentState.RUNNING))
    }

    if (data.event === "status") {
        console.log("WS state messasge:", data);
        if(data.status===AgentState.IDLE)dispatch(setAgentStatus(AgentState.IDLE))
        if(data.status===AgentState.RUNNING)dispatch(setAgentStatus(AgentState.RUNNING))
        if(data.status===AgentState.INTERRUPT)dispatch(setAgentStatus(AgentState.INTERRUPT))
        if(data.status===AgentState.ERROR)dispatch(setAgentStatus(AgentState.ERROR))
    }

    if (data.event === "snapshot") {
      console.log("WS snap shot:", data);
      dispatch(setState(data.data.state))
    }
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
    // dispatch(setAgentStatus(AgentState.ERROR))
    dispatch(setAgentStatus(AgentState.IDLE))
 

  };

  ws.onclose = () => {
    console.log("WebSocket closed");
    ws = null;

    dispatch({
      type: "wsDisconnected"
    });
  };
};


export const sendWs = (state, config,option) => async (dispatch) => {
  try {

    if (!ws || ws.readyState !== WebSocket.OPEN) {
      dispatch(setAgentStatus(AgentState.ERROR))
      await dispatch(startWs({event:AgentState.RUNNING,state,config,option}));
      throw new Error("WebSocket is not open");
    }

    ws.send(JSON.stringify({event: AgentState.RUNNING,state,config,option}));

  } catch (error) {
    console.error("sendWs failed:", error);
    dispatch(setAgentStatus(AgentState.ERROR));
  }
};


export const cancelAgent = (config) => async(dispatch) => { //function return a function 
  if (!ws) {
    console.error("running task  cancel");
    dispatch(setAgentStatus(AgentState.IDLE))
    return;
  }

  if (ws.readyState !== WebSocket.OPEN) {
    console.error("WebSocket is not open");
    return;
  }

  ws.send(
    JSON.stringify({
      event: AgentState.STOP,
      config:config

    })
  );
  
 
};


export const resumeAgent = (resume, config,option) => async(dispatch) => {
 try{
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      dispatch(setAgentStatus(AgentState.ERROR))
      await dispatch(startWs({event:AgentState.RESUME,resume,config,option}));
      throw new Error("WebSocket is not open");
    }
  ws.send(
    JSON.stringify({
      event: AgentState.RESUME,
      resume:resume,
      config:config,
      option:option
    })
  );}
  catch (error) {
    console.error("sendWs failed:", error);
    dispatch(setAgentStatus(AgentState.ERROR));
  }

};