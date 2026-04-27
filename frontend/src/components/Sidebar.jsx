import React from 'react';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';

const Sidebar = ({ isOpen, chats, currentSessionId, onCreateNew, onLoadChat, onDeleteChat }) => {
  return (
    <div className={`sidebar ${!isOpen ? 'collapsed' : ''}`}>
      <button className="new-chat-btn" onClick={onCreateNew}>
        <Plus size={20} />
        New Chat
      </button>
      
      <div className="chat-history">
        <div className="chat-history-title">Recent</div>
        {chats.map(chat => (
          <div 
            key={chat._id} 
            className={`history-item ${currentSessionId === chat._id ? 'active' : ''}`}
            onClick={() => onLoadChat(chat._id)}
          >
            <MessageSquare size={16} />
            <span>{chat.session_name}</span>
            <button className="delete-btn" onClick={(e) => onDeleteChat(chat._id, e)}>
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Sidebar;
