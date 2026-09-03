import { tick, start,resume, stop } from "./countSlice"; 
import  { pausetoggle, resumetoggle } from "./toggleSlice"


let time = null;


export const startTimer = () => (dispatch) => {

  if (time) return;

  dispatch(start());

  time = setInterval(() => {
    dispatch(tick());
  }, 100);
};

export const pauseTimer = () => (dispatch) => {
  if (time !== null) {
    clearInterval(time);
    time = null;
  }
  dispatch(pausetoggle())
};

export const resumeTimer = () => (dispatch) => {
  if (time !== null) return;

  dispatch(resume());
  dispatch(resumetoggle())

  time = setInterval(() => {
    dispatch(tick());
  }, 100);
};


export const stopTimer = () => (dispatch) => {

  if (time) {
    clearInterval(time);
    time = null;
  }

  dispatch(stop());
};