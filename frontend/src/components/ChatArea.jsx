import React, { useState, useRef, useEffect } from 'react';
import { Send, Menu, User, Bot } from 'lucide-react';

const ChatArea = ({ token, currentSessionId, setCurrentSessionId, messages, setMessages, toggleSidebar, onLogout, onChatsUpdated }) => {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const endOfMessagesRef = useRef(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    
    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('http://localhost:5000/predict', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ 
          symptoms: userMessage.content,
          session_id: currentSessionId
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          const aiMessage = {
            role: 'model',
            content: data.response,
            status: data.status,
            predictions: data.top_predictions,
            matched_keywords: data.matched_keywords
          };
          setMessages(prev => [...prev, aiMessage]);
          if (!currentSessionId && data.session_id) { 
            setCurrentSessionId(data.session_id);
            onChatsUpdated(); // Refresh sidebar to show new chat
          }
        } else {
          setMessages(prev => [...prev, { role: 'model', content: "An error occurred while processing symptoms." }]);
        }
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: 'model', content: "Network error communicating with the backend." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="main-content">
      <div className="header">
        <div className="header-left">
          <button className="toggle-sidebar-btn" onClick={toggleSidebar}>
            <Menu size={24} />
          </button>
          <div className="app-title">MedAI</div>
        </div>
        <button className="logout-btn" onClick={onLogout}>Logout</button>
      </div>

      <div className="chat-area">
        {messages.length === 0 ? (
          <div className="empty-state">
            <h1>Hello, I'm MedAI</h1>
            <p>How can I help you today?</p>
          </div>
        ) : (
          <div className="messages-container">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <div className={`avatar ${msg.role}`}>
                  {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                </div>
                <div className="message-content">
                  {msg.role === 'model' && msg.status && (
                    <div className={`ai-status status-${msg.status}`}>
                      {msg.status} Priority
                    </div>
                  )}
                  {msg.role === 'model' && msg.predictions && (
                    <div style={{ marginBottom: '1rem' }}>
                      {msg.predictions.map((p, i) => (
                        <span key={i} className="prediction-pill">
                          {p.disease} ({p.confidence.toFixed(1)}%)
                        </span>
                      ))}
                    </div>
                  )}
                  {msg.role === 'model' && msg.matched_keywords && msg.matched_keywords.length > 0 && (
                    <div style={{ marginBottom: '1rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      <strong>Detected Keywords:</strong> {msg.matched_keywords.join(", ")}
                    </div>
                  )}
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message model">
                <div className="avatar ai"><Bot size={20} /></div>
                <div className="message-content" style={{ backgroundColor: 'transparent' }}>
                  <div className="spinner"></div>
                </div>
              </div>
            )}
            <div ref={endOfMessagesRef} />
          </div>
        )}
      </div>

      <div className="input-area-wrapper">
        <div className="input-container">
          <textarea 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your symptoms..."
            rows={1}
          />
          <button 
            className="send-btn" 
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatArea;
