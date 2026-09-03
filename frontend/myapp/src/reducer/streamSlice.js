import { createSlice } from "@reduxjs/toolkit";

const initialState = {value:{}};

const streamSlice = createSlice({
  name: "stream",
  initialState,

  reducers: {
    setStream: (state, action) => {
      state.value = action.payload; // accumulated message receive from server
    },

    clearStream: (state) => {
     state.value={}
    },
  },
});

export const { setStream, clearStream } = streamSlice.actions;

export default streamSlice.reducer;