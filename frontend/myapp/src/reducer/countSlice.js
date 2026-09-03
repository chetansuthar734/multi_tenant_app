import { createSlice } from "@reduxjs/toolkit";



const countSlice = createSlice({
  name: "counter",

  initialState: {
    count: 0,
    running: false
  },

  reducers: {
    start: (state) => {
      state.running = true;
    },

    tick: (state) => {
      state.count += 1;
    },

    pause: (state) => {
      // state.running = false;
    },

    resume: (state) => {
       state.running = true;
    },
    stop: (state) => {
      state.count = 0;
      state.running = false;
    },

    reset: (state) => {
      state.count = 0;
      state.running = false;
    }
  }
});

export const {
  start,
  tick,
  pause,
  resume,
  stop,
  reset
} = countSlice.actions;

export default countSlice.reducer;