import React, { useState, useEffect } from 'react';
import Auth from './components/Auth';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import './index.css';

const App = () => {
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [sidebarChats, setSidebarChats] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [currentMessages, setCurrentMessages] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    if (token) {
      fetchChats();
    }
  }, [token]);

  const fetchChats = async () => {
    try {
      const res = await fetch('http://localhost:5000/api/chats', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSidebarChats(data);
      } else {
        if(res.status === 401) handleLogout();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setSidebarChats([]);
    setCurrentSessionId(null);
    setCurrentMessages([]);
  };

  const createNewChat = () => {
    setCurrentSessionId(null);
    setCurrentMessages([]);
  };

  const loadChat = async (id) => {
    try {
      const res = await fetch(`http://localhost:5000/api/chats/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentSessionId(id);
        setCurrentMessages(data.messages || []);
      } else if (res.status === 401) {
        handleLogout();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const deleteChat = async (id, e) => {
    e.stopPropagation();
    try {
      const res = await fetch(`http://localhost:5000/api/chats/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setSidebarChats(sidebarChats.filter(c => c._id !== id));
        if (currentSessionId === id) {
          setCurrentSessionId(null);
          setCurrentMessages([]);
        }
      } else if (res.status === 401) {
        handleLogout();
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (!token) {
    return <Auth setToken={(t) => {
      localStorage.setItem('token', t);
      setToken(t);
    }} />;
  }

  return (
    <div className="app-container">
      <Sidebar 
        isOpen={sidebarOpen}
        chats={sidebarChats}
        currentSessionId={currentSessionId}
        onCreateNew={createNewChat}
        onLoadChat={loadChat}
        onDeleteChat={deleteChat}
      />
      <ChatArea 
        token={token}
        currentSessionId={currentSessionId}
        setCurrentSessionId={setCurrentSessionId}
        messages={currentMessages}
        setMessages={setCurrentMessages}
        toggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onLogout={handleLogout}
        onChatsUpdated={fetchChats}
      />
    </div>
  );
};

export default App;
