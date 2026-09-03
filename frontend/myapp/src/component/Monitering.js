import {
  LineChart,
  XAxis,
  YAxis,
  Line,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";
import "../App"

const data = [
  { name: "1", value: 1.2 },
  { name: "2", value: 1.8 },
  { name: "3", value: 1.5 },
  { name: "4", value: 2.1 },
  { name: "5", value: 2.8 },
  { name: "6", value: 2.4 },
  { name: "7", value: 3.1 },
  { name: "8", value: 2.7 },
  { name: "9", value: 3.5 },
  { name: "10", value: 3.2 },
  { name: "11", value: 4.0 },
  { name: "12", value: 3.7 },
  { name: "13", value: 4.5 },
  { name: "14", value: 4.2 },
  { name: "15", value: 5.0 },
];

function Moniter() {
const schedules = [
  {name:"ash123 skin chekup" ,from:'2:30' , to:'3:00'},
  {name:"ash123 skin chekup" ,from:'2:30' , to:'3:00'},
  {name:"ash123 skin chekup" ,from:'2:30' , to:'3:00'},
  {name:"ash123 skin chekup" ,from:'2:30' , to:'3:00'},
  {name:"ash123 skin chekup" ,from:'2:30' , to:'3:00'},
  {name:"ash123 skin chekup" ,from:'2:30' , to:'3:00'},
  {name:"ash123 skin chekup" ,from:'2:30' , to:'3:00'},
]
  
 const SchedulesComponent = ({schedules})=>{
  return(<div style={{ padding:'20px',width:'100%' ,height:'100%',boxSizing:"border-box"}}>
 {schedules.map((schedule,i)=><div style={{width:'100%',  margin: "10px 0",height:'50px',border:'2px solid black'}}>schedule name:{schedule.name} | from:{schedule.from} ⇔ to:{schedule.to}</div>)}
  </div>)
 }

  return (
    <div  style={{height:'100%',width:'100vw',display:'flex',flexDirection:'row'}}>
           


    <div   style={{flex:2,backgroundColor:"gray",height:'100%',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',textAlign:'center',padding:'20px'}}>
 <ResponsiveContainer width="100%" height={300}>
  <LineChart data={data}>
    <CartesianGrid strokeDasharray="3 3" />

    <XAxis dataKey="name" />
    <YAxis />
    <Tooltip />

    <Line
      type="monotone"
      dataKey="value"
      stroke="#61dafb"
      strokeWidth={3}
      dot={{
        r: 5,
        fill: "#61dafb",
        stroke: "#fff",
        strokeWidth: 2,
      }}
      activeDot={{
        r: 7,
        fill: "#fff",
        stroke: "#61dafb",
        strokeWidth: 3,
      }}
    />
  </LineChart>
</ResponsiveContainer>

    </div>


    <div  style={{flex:2,backgroundColor:"gray",height:'100%',display:'flex',flexDirection:'column',alignItems:'center',textAlign:'center',padding:'20px'}}>
    <h1>Assistant Schedule</h1>
    <div className="card" style={{alignItems:'center',width:'100%',height:'100%'}}>
    <SchedulesComponent schedules={schedules}/>
      
    </div>
      </div>


    </div>

  );
}

export default Moniter