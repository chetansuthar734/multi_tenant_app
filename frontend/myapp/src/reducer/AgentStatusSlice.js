import { createSlice } from "@reduxjs/toolkit";

export const AgentState = Object.freeze({
  IDLE: "idle",
  RUNNING: "running",
  RESUME:"resume",
  ERROR: "error",
  INTERRUPT: "interrupt",
  CONNECT:'connect',
  STOP:'stop'
});

const agentStatusSlice = createSlice({
  name: "agentStatus",

  initialState: AgentState.IDLE,

  reducers: {
    setAgentStatus: (_, action) => action.payload,
  },
});

export const { setAgentStatus } = agentStatusSlice.actions;

export default agentStatusSlice.reducer;