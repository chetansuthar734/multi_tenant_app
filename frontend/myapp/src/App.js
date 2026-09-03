import './App.css';
import { Route,Routes } from 'react-router-dom';

import { Toaster } from 'react-hot-toast';


import ChatBot from "./component/Chatbot"
import VoiceWebrtc from "./component/callapp/Webrtc"
import {DashBoard } from './component/DashBoard';
import AboutPage from './component/About';
import Login from './component/Login';
import Register from './component/Register';
import Subscription from './component/Subscription';
// import ProtectedRoute from './component/ProtectedRoute';
import NavBar from './component/NavBar';
import Moniter from './component/Monitering';
import Assistant from './component/Assistant';
import Echo from './component/Echo';


function App() {
  

  

  return (
    <div className="App">
      <header className="App-header">
     <NavBar />
      <Toaster  position='top-right'/>
    <Routes >
        <Route path="/" element={<DashBoard />} />
        <Route path="/chatbot" element={<ChatBot />} />
        <Route path="/call" element={<VoiceWebrtc />}/>
        <Route path="/login" element={<Login />}/>
        <Route path="/register" element={<Register />}/>
        <Route path="/about" element={<AboutPage />}/>
        <Route path="/moniter" element={<Moniter />}/>
        <Route path="/assistant" element={<Assistant />}/>
        <Route path="/subscription" element={<Subscription />}/>
        <Route path="/echo" element={<Echo />}/>
      </Routes>

    </header>
    </div>
  );
}

export default App;
