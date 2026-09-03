import { configureStore } from "@reduxjs/toolkit";
import countReducer from "./reducer/countSlice";
import { MessageReducer, FileReducer } from "./reducer/MessageReducer";
import stateReducer from "./reducer/stateSlice"
import configReducer from "./reducer/configSlice"
import toggleReducer from "./reducer/toggleSlice";
import streamReducer from "./reducer/streamSlice";
import AgentReducer from "./reducer/AgentStatusSlice"

const store = configureStore({
  reducer: {
    counter: countReducer,
    messages: MessageReducer,
    files: FileReducer,
    state:stateReducer,
    config:configReducer,
    toggle:toggleReducer,
    stream:streamReducer,
    status:AgentReducer,
  }
});

export default store;