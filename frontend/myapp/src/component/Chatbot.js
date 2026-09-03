
import "../App.css"
import { useDispatch, useSelector } from "react-redux";

import { sendWs,cancelAgent ,resumeAgent} from "../reducer/agentRunThunk";
import ChatMessage from "./ChatComponent";
import { AgentState } from "../reducer/AgentStatusSlice";
import ReactMarkdown from "react-markdown";
import { MarkdownRenderer } from "./ChatComponent";
import remarkGfm from "remark-gfm";
import toast from "react-hot-toast";




function ChatBot() {
  const dispatch = useDispatch();
  
  const messages = useSelector(state => state.messages.messages);
  const agentStatus = useSelector(state=>state.status)
const stream = useSelector((state) => state.stream);
  const files = useSelector(state => state.files.files);
    const state = useSelector((state) => state.state);
    // const message = useSelector((state) => state.state?.message);

    // const config = useSelector((state) => state.config);
    // console.log("state",state)
    // console.log("config",config)


 const url = process.env.REACT_APP_API



  const handleChange = async(e) => {
    e.preventDefault();
    const files_upload =Array.from(e.target.files)
    e.target.value = "";
    const formData = new FormData();
    
    files_upload.forEach((file) => {
        formData.append("files", file);
    });
    
    try {
        console.log('file is upload to server')
          const response = await fetch(`${url}/uploadfiles`, {
                method: "POST",
                body: formData,
              });
              
             if (!response.ok) {
              toast.error('❌ file upload fail',{position:'bottom-right',duration:3000})
              throw new Error(`Upload failed: ${response.status}`);
            }
              const data = await response.json();
              console.log('res',data);
              toast.success('file upload sucess',{position:'bottom-right',duration:3000})
              // setFiles((pre_files)=>[...pre_files,...data.files]);    
              dispatch({type: "addfile",payload: data.files});
              // dispatch({type: "addMessages",payload: data.user.state.messages} );
              dispatch({type: "addMessages",payload: data.messages} );
    } catch (error) {
      console.error("Upload failed:", error);
    }
  };
  



  const agentRunhandle =async(query)=>{
    let msg=[]
    console.log(messages) //file messages list
 
    // console.log(query)
    if(query){ msg=[{type:'human',content:query}]}

    const s={messages:[...messages,  ...msg]}
     const c={configurable:{thread_id:'chetan'}}
     const option={stream_mode:["values","custom"]}
   
    dispatch(sendWs(s,c,option)); 
    toast.success('send messages',{position:'bottom-right',duration:3000})
    }
 

  const agentResumehandle =async(query)=>{
    console.log("RESUME HANDLE TRIGGER")
    const r=query
     const c={configurable:{thread_id:'chetan'}}
     const option={stream_mode:["values","custom"]}
   
    dispatch(resumeAgent(r,c,option)); 
    toast.success('resume messages send',{position:'bottom-right',duration:3000})
    }
 

  // const cookies =async()=>{
  //    const response = await fetch(`http://localhost:8001/demo`, {
  //               method: "GET",
  //                credentials: "include",
  //             });

  //     const d = response.json()
  //     console.log(d)
  // }



const deleteFile = async(file)=>{
  // delete file op
   try { 
          const response = await fetch(`${url}/file/${file.file_id}`, {
                method: "DELETE",
              });
              
             if (!response.ok) {throw new Error(`Upload failed: ${response.status}`);}
              const data = await response.json();   
              toast.success('🗑️ file removed',{position:'bottom-right',duration:3000})    
              console.log('file delete res',data);
              dispatch({type: "removefile",payload:file.file_id});
              dispatch({type: "removeMessages",payload:file.file_id});
              
    } catch (error) {
      console.error("delete failed:", error); 
    }
}


    return ( 
    <div  className="page"> 
    
     {/* <div className="box-v" style={{flex:'1'}}> chat history <br/>state snapshot.  </div> */}
   



     <div className="box-v" style={{flex:'4'}} >

      {/* messages list render */}
    {(Array.isArray(state?.messages) ? state.messages : []).map((m, i) => ( <ChatMessage key={i}message={m}index={i}/>) )}
     {/* stream chunk render */}
    {stream?.value && ( <div className="chatbox-ai"><div className="chat-ai"><MarkdownRenderer content={stream?.value.content} /></div></div>)}
    {/* interrupt message display */}
    {(Array.isArray(state?.__interrupt__) ? state?.__interrupt__ : []).map((m, i) => ( <div className="chatbox-ai" key={i}> <div style={{border:'2px dotted white',padding:'30px'}}>🛑 interrupt:{m.value} </div></div>) )}

     </div> 


      <div className="inputbox">  

        {files.length!==0 && <div className="file-container"> {files.map((file,i)=>
            <div className="file-box" key={i}>
                <div style={{fontSize:'40px'}}>📄 </div>
               <div style={{width:'100px',height:'100%',textOverflow:'ellipsis',whiteSpace:'nowrap',overflowX:'hidden'}}>{file.filename}</div> 
                <div className="delete-file" onClick={()=>deleteFile(file)}>❌</div>
            </div>)}</div>}
    
    
    {/* <div className="inp-box2">   */}

  <form className="box-h" 
         onSubmit={async(e)=>{ 
      // setAgentState(AgentState.RUNNING)
      e.preventDefault();
      const query = e.target.content.value
      const form =e.currentTarget;
      // setFiles([]);  // Reset textarea height
      
      const textarea = form.querySelector(".inp-txt-area");

      if (query.trim()==="" &&  files.length === 0) return
        // console.log(e.target.content.value)
      e.target.reset(); 
      textarea.style.height = "auto";
      textarea.style.overflowY = "hidden";

      dispatch({type: "remove_all_files",payload: []});
      // agenthandle(formData.get("content"))
      if (agentStatus ===AgentState.INTERRUPT){ agentResumehandle(query);return}
      await dispatch(cancelAgent({configurable:{thread_id:'chetan'}}))
      agentRunhandle(query)
      
    
    }} >

      <label className="inp-file" ><input  type="file"  multiple onChange={(e)=>{handleChange(e)}} style={{display:'none'}} />➕</label>
    
     <textarea
  className="inp-txt-area"
  name="content"
  placeholder="Ask anything...."
  onKeyDown={(e)=>{if(e.key==='Enter'&& !e.shiftKey){e.preventDefault();e.target.form.requestSubmit()}}}
  onInput={(e) => {
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 300)}px`;
    e.target.style.overflowY =e.target.scrollHeight > 300 ? "auto" : "hidden";
  }}
/>
 <button type="mic" onClick={(e)=>{e.preventDefault(); e.stopPropagation();}} className="inp-file" style={{border:'none',fontSize:'20px'}} >🎤︎︎</button>

{agentStatus===AgentState.IDLE ? 
<button type="submit" className="btn" style={{backgroundColor:'rgb(103, 173, 94)',height:'50px'}} > send</button>
:
 <div style={{display:"flex",flexDirection:'row',gap:'5px'}}>
   {agentStatus===AgentState.INTERRUPT && <button  type="submit" onClick={(e)=>{ console.log("resume CLICKED") } } className="btn" style={{backgroundColor:'rgb(230,220,0)'}} > resume</button> }
  <button  onClick={(e)=>{e.preventDefault(); e.stopPropagation(); console.log("STOP CLICKED") ;  dispatch(cancelAgent({configurable:{thread_id:'chetan'}}))}} className="btn" style={{backgroundColor:'rgb(249, 85, 85)'}} > stop</button> 
  </div>
}
    </form>
        {/* </div>  */}
      </div>
        

  
  
  
  
  {/* <div className="box-v"  style={{flex:'1'}}>uploaded file</div> */}
      
    </div> );
}

export default ChatBot