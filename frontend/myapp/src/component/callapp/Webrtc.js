
import "../../App"
import "odometer/themes/odometer-theme-minimal.css"
import Odometer from 'react-odometerjs'
// import { pauseTimer, resumeTimer, startTimer, stopTimer } from "../../reducer/TimerThunk";
import { useEffect, useRef } from "react";
import { useDispatch,useSelector } from "react-redux";
// import { pausetoggle,resumetoggle } from "../../reducer/toggleSlice";
import { stopWebRTC,startWebsocket,startWebRTC,pauseWebRTC,resumeWebRTC } from "../../reducer/webRtcThunk";


function VoiceWebrtc() {
  const dispatch = useDispatch();
  
  const count = useSelector(state=>state.counter.count)
  const recording = useSelector(state=>state.counter.running)
  //  const [recording,setRecording] = useState(false)
  // const timeRef = useRef(null)
  const toggle = useSelector(state=>state.toggle.toggle)
  const formatter = new Intl.NumberFormat('en',{minimumIntegerDigits:2})
  
  useEffect(()=>{dispatch(startWebsocket())},[])
  
    // const startCall=()=>{
    //     if(timeRef.current) return;
    //     // timeRef.current = setInterval(()=>{ setCount(c=>c+1)},100)
    //     dispatch(startTimer());
    //     // setRecording(true)
    // }

    // const endCall = ()=>{
    //     clearInterval(timeRef.current);
    //     timeRef.current=null;
    //     // setCount(0)
    //     dispatch(stopTimer());
    //     // setRecording(false)
    // }
    const sec =formatter.format( Math.floor(count%60))
    const min = Math.floor((count%3600)/60)
    const hr = Math.floor(count/3600)

    return (
  <div className="card">
    
    <div className="profile-photo"></div>
    <input  inputMode="numeric" pattern="[0-9]*" className="inp" maxLength={10}  style={{border:'none',fontSize:'20px',textAlign:"center"}} placeholder="enter number" autoComplete="off"/>
     

     <div>     
        <div style={{height:'30px',display:'flex',alignItems:'center', justifyContent:'flex-start',borderRadius:'10px'}} > Rec :
        <Odometer value={hr} format="(dd)" duration={500} style={{width:'20px'}} /> :
        <Odometer value={min} format="dd" duration={5000} style={{width:'20px'}}/> :
        <Odometer value={sec} format="dd" duration={1000} style={{width:'20px'}} /> 

    </div>


    <div style={{height:'20px',display:"flex", alignItems:'center'}} > 
       Token count: <Odometer value={count} format="(dd)" duration={50} /> 
    </div>
    <div style={{height:'20px',display:"flex", alignItems:'center'}} > 
      charges ₹0.002/token: ₹<Odometer  value={Math.floor(count/20)} format="(dd)" duration={2000} /> 
    </div>
    </div>



    <div style={{height:'150px',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center'}}>
    {!recording ? 
      <div className="btn" style={{backgroundColor:'#51ff62',color:"black"}} onClick={()=>{dispatch(startWebRTC()) }} >CALL </div> :
     <> {toggle?<div className="btn2"  style={{backgroundColor:'#f9a750'}} onClick={()=>{dispatch(pauseWebRTC())  }}> pause</div>:<div className="btn2"  style={{backgroundColor:'#ffec18'}} onClick={()=>{dispatch(resumeWebRTC())}}> Resume</div> }
      <div className="btn2"  style={{backgroundColor:'#f95050'}} onClick={()=>{dispatch(stopWebRTC());}}>END</div> 
      </> 
      }
    </div>
    </div>);
}


export  default VoiceWebrtc 