import { createSlice } from "@reduxjs/toolkit";

const initialState = {};

const stateSlice = createSlice({
  name: "state",
  initialState,

  reducers: {
    setState: (state, action) => {
      // Object.assign(state, action.payload); // Object.assign() merges the new state into the old state. It does not remove old keys.
     return action.payload;
    }
  }
});



export const {setState} = stateSlice.actions;

export default stateSlice.reducer;