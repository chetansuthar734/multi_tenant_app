import { Link, } from "react-router-dom";
import "../App.css"
import { useSelector } from "react-redux";
import { useState } from "react";


function NavBar() {
  const status = useSelector(state=>state.status)
  const [login,setLogin] = useState(false)
  return (
    <div className="nav">
      <Link className="nav-link" to="/">Dashboard</Link>
      <Link className="nav-link" to="/chatbot">multimodel ChatBot</Link>
      <Link className="nav-link" to="/call">Voice call WebRTC</Link>
      <Link className="nav-link" to="/assistant">Assistant</Link>
      <Link className="nav-link" to="/moniter">Monitering & Token</Link>
      <Link className="nav-link" to="/about">About</Link>
      <Link className="nav-link" to="/echo">video/audio echo</Link>
      {/* <Link className="nav-link" to="/subscription">Subscription</Link> */}  
      {login? <Link onClick={()=>setLogin(!login)} className="nav-link" to="/login">Logout</Link>:
      <Link onClick={()=>setLogin(!login)} className="nav-link" to="/register">Login/Register</Link>}
      <div className="center" style={{backgroundColor:"rgb(105, 129, 99)",width:'300px',height:'100%'} }>Status:{status}</div>
    </div>
  );
}

export default NavBar;