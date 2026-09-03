
import "../App"
import { useNavigate ,useSearchParams} from "react-router-dom";
import toast from "react-hot-toast";
import { useEffect } from "react";

function Assistant() {
  const navigate = useNavigate()

  const [searchParams] = useSearchParams();

  useEffect(() => {

    const twilio = searchParams.get("twilio");

    if (twilio === "connected") {
      console.log("Twilio connected successfully");

      // Show notification
      toast.success("Twilio connected");
      // toast.error("invalid ")
      // toast.loading("wait......")
    }

  }, [searchParams]);


   const url = process.env.REACT_APP_API
  //  const token = localStorage.getItem("token")
   const token = "1234556"


   //  connect to twilio request
const connectTwilio = async () => {
  const res = await fetch(`${url}/twilio/connect`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();

  window.location.href = data.url;
};


//  connect to whatsapp bussiness request
//  connect to email request

   const api = process.env.REACT_APP_API
   console.log(api)
    return ( 
  <div  style={{display:'flex',flexDirection:'row',width:'100vw',height:'100vh',color:'black'}} >
        <div style={{flex:'1',display:'flex',flexDirection:'column',gap:'40px',backgroundColor:"black",height:'100vh',textAlign:'center'}}>
            <h2>Assistant</h2>
           <div className="btn" style={{backgroundColor:'rgba(250, 40, 40, 0.95)',borderRadius:'0px'}} onClick={()=>connectTwilio()}>Connect twilio call</div>
           <div className="btn" style={{backgroundColor:'rgb(34, 254, 67)',borderRadius:'0px'}}>Connect whatspp business account</div>
           <div className="btn" style={{backgroundColor:'rgb(8, 189, 255)',borderRadius:'0px'}}>Connect Email</div>
           <div className="btn" style={{backgroundColor:"#fff",borderRadius:'0px'}} onClick={()=>navigate("/chatbot")} >Chatbot Assistant</div>

        </div>
       

  <div className="assistant-card" style={{flex:'5',borderRadius:"0px",height:'100%' , overflowY:'scroll'}}>
    <p className="assistant-subtitle">
    <span> <h2 style={{display:"inline" ,fontSize:'50px',fontFamily:"ui-rounded"}}>Assistant Configuration</h2></span>
    </p>

    <form onSubmit={(e) => e.preventDefault()}>
      <div className="form-group">

        <div style={{width:'100%', display:'flex',alignItems:'center',justifyContent:'center',flexDirection:'column'}}  >
        <label style={{width:'200px',height:'200px',borderRadius:'50%',border:'2px solid black',cursor:'pointer',backgroundImage:"url(/l60Hf.png)",backgroundSize: "cover",backgroundPosition: "center",backgroundRepeat: "no-repeat",}}>
        <input
        type="file"
        style={{display:'none',}}
        placeholder="Enter assistant name"
        />
        </label>
        upload image
        </div>

        <label>Assistant Name</label>
        <input
          className="assistant-input"
          placeholder="Enter assistant name"
        />
      </div>

      <div className="form-group">
        <label>System Prompt</label>
        <textarea
          className="assistant-input assistant-textarea"
          placeholder="Enter system prompt..."
        />
      </div>

      <div className="form-group">
        <label>MCP Server</label>
        <input
          className="assistant-input"
          placeholder="Enter MCP server URL"
        />
      </div>
      <div className="form-group" style={{display:'flex',flexDirection:'row'}}>
        <span style={{color:'black' ,flex:'1'}}>Assistant Scheduling type :</span>
<select className="assistant-input" style={{flex:"6"}}>
  <option value="queue">Queue Scheduling</option>
  <option value="schedule_event">Schedule Event</option>
  <option value="any_schedule_event">Any Schedule Event</option>
</select>      
  </div>

      <div className="form-group">


     <label className="upload-box">
          <input
            type="file"
            accept=".pdf"
            style={{ display: "none" }}
          />

          <span className="upload-icon">📄</span>
          <span>Upload PDF</span>
          <small>PDF files only</small>
        </label>
      </div>

      <button
        className="update-btn"
        type="submit"
      >
        Update Assistant
      </button>
    </form>

</div>
    </div> 
   
    );
}

export default Assistant;