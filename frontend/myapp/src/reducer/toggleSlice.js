import { createSlice } from "@reduxjs/toolkit";

const toggleSlice = createSlice({
  name: "toggle",

  initialState: {
    toggle: true,
  },

  reducers: {
    pausetoggle: (state) => {
      state.toggle = false;
    },

    resumetoggle: (state) => {
      state.toggle = true;
    },
  },
});

export const { pausetoggle, resumetoggle } = toggleSlice.actions;

export default toggleSlice.reducer;