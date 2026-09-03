import { createSlice } from "@reduxjs/toolkit";

const initialState = {};

const configSlice = createSlice({
  name: "config",
  initialState,

  reducers: {
    setConfig: (state, action) => {
      Object.assign(state, action.payload);
    }
  }
});

export const {setConfig} = configSlice.actions;

export default configSlice.reducer;