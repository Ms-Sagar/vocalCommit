import React, { useState, useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

interface VoiceMessage {
  type: string;
  transcript: string;
  timestamp: string;
}

interface AgentResponse {
  status: string;
  agent?: string;
  response: string;
  command_type?: string;
  transcript?: string;
}

const VoiceInterface: React.FC = () => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [messages, setMessages] = useState<AgentResponse[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Initialize WebSocket connection
    const connectWebSocket = () => {
      const ws = new WebSocket('ws://localhost:8000/ws');
      
      ws.onopen = () => {
        setIsConnected(true);
        setConnectionStatus('Connected to VocalCommit Orchestrator');
        console.log('Connected to VocalCommit WebSocket');
      };
      
      ws.onmessage = (event) => {
        try {
          const response: AgentResponse = JSON.parse(event.data);
          setMessages(prev => [...prev, response]);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      ws.onclose = () => {
        setIsConnected(false);
        setConnectionStatus('Disconnected - Attempting to reconnect...');
        console.log('WebSocket connection closed');
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('Connection Error');
      };
      
      wsRef.current = ws;
    };

    connectWebSocket();

    // Initialize Speech Recognition
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';
      
      recognition.onstart = () => {
        setIsListening(true);
        setTranscript('Listening...');
      };
      
      recognition.onresult = (event) => {
        const result = event.results[0][0].transcript;
        setTranscript(result);
        
        // Send to VocalCommit orchestrator
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          const message: VoiceMessage = {
            type: 'voice_command',
            transcript: result,
            timestamp: new Date().toISOString()
          };
          
          wsRef.current.send(JSON.stringify(message));
        }
      };
      
      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        setTranscript(`Error: ${event.error}`);
      };
      
      recognition.onend = () => {
        setIsListening(false);
      };
      
      recognitionRef.current = recognition;
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const startListening = () => {
    if (recognitionRef.current && !isListening) {
      recognitionRef.current.start();
    }
  };

  const stopListening = () => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
    }
  };

  const sendTextCommand = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && transcript.trim()) {
      const message: VoiceMessage = {
        type: 'text_command',
        transcript: transcript.trim(),
        timestamp: new Date().toISOString()
      };
      
      wsRef.current.send(JSON.stringify(message));
      setTranscript('');
    }
  };

  return (
    <div className="voice-interface">
      <div className="header">
        <h1>🎤 VocalCommit - Voice Orchestrated SDLC</h1>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {connectionStatus}
        </div>
      </div>

      <div className="voice-controls">
        <div className="transcript-section">
          <h3>Voice Input</h3>
          <div className="transcript-display">
            {transcript || 'Click "Start Listening" to begin voice commands...'}
          </div>
          
          <div className="control-buttons">
            <button 
              onClick={startListening} 
              disabled={isListening || !isConnected}
              className={`voice-btn ${isListening ? 'listening' : ''}`}
            >
              {isListening ? '🎤 Listening...' : '🎤 Start Listening'}
            </button>
            
            <button 
              onClick={stopListening} 
              disabled={!isListening}
              className="voice-btn stop"
            >
              ⏹️ Stop
            </button>
          </div>
        </div>

        <div className="text-input-section">
          <h3>Text Input</h3>
          <div className="text-input-controls">
            <input
              type="text"
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Type your command here..."
              className="text-input"
              onKeyPress={(e) => e.key === 'Enter' && sendTextCommand()}
            />
            <button 
              onClick={sendTextCommand}
              disabled={!isConnected || !transcript.trim()}
              className="send-btn"
            >
              Send Command
            </button>
          </div>
        </div>
      </div>

      <div className="agent-responses">
        <h3>Agent Responses</h3>
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="no-messages">
              No messages yet. Try saying: "Create a user authentication system"
            </div>
          ) : (
            messages.map((message, index) => (
              <div key={index} className="message">
                <div className="message-header">
                  <span className="agent-name">{message.agent || 'Orchestrator'}</span>
                  <span className="message-status">{message.status}</span>
                </div>
                <div className="message-content">
                  {message.response}
                </div>
                {message.transcript && (
                  <div className="original-command">
                    Original: "{message.transcript}"
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      <div className="agent-status">
        <h3>Available Agents</h3>
        <div className="agents-grid">
          <div className="agent-card">
            <h4>🎯 PM Agent</h4>
            <p>Task planning and project coordination</p>
          </div>
          <div className="agent-card">
            <h4>💻 Dev Agent</h4>
            <p>AI-powered code generation</p>
          </div>
          <div className="agent-card">
            <h4>🔒 Security Agent</h4>
            <p>Code vulnerability scanning</p>
          </div>
          <div className="agent-card">
            <h4>🚀 DevOps Agent</h4>
            <p>Deployment and operations</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VoiceInterface;