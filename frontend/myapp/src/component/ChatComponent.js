import "../App.css"
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";


function MyTextComponent({ children }) {
  return (
    <div className="my-text" >
      {children}
    </div>
  );
}

export function MarkdownRenderer({ content }) {
  return (
    <ReactMarkdown
      components={{
        code({ node, inline, className, children, ...props }) {
          const language = className?.replace("language-", "");

          if (!inline && language === "text") {
            return (
              <MyTextComponent>
                {String(children).replace(/\n$/, "")}
              </MyTextComponent>
            );
          }

          return (
  <pre style={{background: "black", width:'100%',color: "green",padding: "30px 40px",borderRadius: "10px",margin: "40px 0",overflowX: "auto",lineHeight: "1.5",fontFamily:"'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace",border: "1px solid #333",whiteSpace: "pre-wrap",wordBreak: "break-word",}}>
     <code className={className}{...props}>{children}</code>
    </pre>
);

        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}



function ChatMessage({ message, index }) {
  
   if(message?.content==="")return // remove AIMessage("",tool_calls={})
  const isAI = message.type === "ai";

          //remove ToolMessage()
  if ( message?.type==="tool") return 
    // (<div className="chatbox-tool"><div className="chat-tool"id={message.id}>ToolMessage: {message.content}</div></div>);

  return (
    <div
      className={isAI ? "chatbox-ai" : "chatbox-human"}>
      
      
  { Array.isArray(message?.content) ? (
        message.content.map((part, i) => {
        
          if (part.type === "image_url") {
            return (
              <div className={isAI ? "chatbox-ai" : "chatbox-human"} key={i}>
                <img
                 headers={{
    "ngrok-skip-browser-warning": "true" 
  }}
                  src={part.image_url.url}
                  alt="uploaded"
                  style={{ width: "300px" }}
                />
              </div>
            );
          }

          if (part.type === "text") {
            return (
              <div className={isAI ? "chat-ai" : "chat-human"} key={i} style={{textAlign:'left',boxSizing:'border-box',overflow:'hidden'}} >

              <h4 style={{color:'black',height:'20px'}}>content-type:{message?.name}</h4>
              <div  key={i} style={{textAlign:'left',height:'90%',fontSize:'15px',margin:'10px' ,overflowY:"scroll",boxSizing: "border-box",padding:'20px'}} >
               <ReactMarkdown >
                {part.text}
                </ReactMarkdown> 
              </div>
              </div>
            );
          }       
       
        if (part.type === "video_url") {
            return (
              <div className={isAI ? "chatbox-ai" : "chatbox-human"} key={i}>
                <video
                 headers={{
    "ngrok-skip-browser-warning": "true"
  }}
                  src={part.video_url.url}
                  controls
                  style={{
                    width: "400px",
                    maxWidth: "100%",
                    borderRadius: "10px",
                    display: "block",
                  }}
                />
              </div>
            );
          }

           if (part.type === "audio_url") {
            return (
              <div className={isAI ? "chatbox-ai" : "chatbox-human"} key={i}>
                <audio
                 headers={{
    "ngrok-skip-browser-warning": "true"
  }}
                  src={part.audio_url.url}
                  controls
                  style={{ maxWidth: "100%" }}
                />
              </div>
            );
          } 
       return null;
        })  
    
    )
     :
      
      
      (
        <div className={isAI ? "chat-ai" : "chat-human"}>
         {/* <ReactMarkdown remarkPlugins={[remarkGfm]}> 
             {message.content}
            </ReactMarkdown> */}
            <MarkdownRenderer content={message.content} />
        </div>
      )}


    </div>
  );
}

export default ChatMessage;