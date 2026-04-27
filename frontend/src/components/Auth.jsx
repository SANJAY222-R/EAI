import React, { useState } from 'react';

const Auth = ({ setToken }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const endpoint = isLogin ? '/api/login' : '/api/signup';
    
    try {
      const res = await fetch(`http://localhost:5000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        if (isLogin) {
          setToken(data.token);
        } else {
          setIsLogin(true);
          setError('Registration successful. Please log in.');
        }
      } else {
        setError(data.message || 'Authentication failed');
      }
    } catch (err) {
      setError('Network error. Is the backend running?');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <div className="auth-header">
          <h2><span className="logo-icon">🧠</span> MedAI</h2>
          <p className="auth-subtitle">
            {isLogin ? 'Welcome back to your intelligent health assistant' : 'Create an account to get started'}
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {error && <div className={`auth-message ${error.includes('successful') ? 'success' : 'error'}`}>{error}</div>}
          
          <div className="form-group">
            <label>Email Address</label>
            <input 
              type="email" 
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              required 
              placeholder="name@example.com"
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required 
              placeholder="••••••••"
            />
          </div>
          
          <button type="submit" className="auth-submit-btn">
            {isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <div className="auth-toggle-wrapper">
          <div className="auth-toggle-pill">
            <button 
              className={`toggle-btn ${isLogin ? 'active' : ''}`} 
              onClick={() => {setIsLogin(true); setError('');}}
              type="button"
            >
              Login
            </button>
            <button 
              className={`toggle-btn ${!isLogin ? 'active' : ''}`} 
              onClick={() => {setIsLogin(false); setError('');}}
              type="button"
            >
              Sign Up
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Auth;
