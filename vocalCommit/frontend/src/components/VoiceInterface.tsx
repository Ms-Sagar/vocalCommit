import React, { useState, useEffect, useRef } from 'react';

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
  task_id?: string;
  requires_approval?: boolean;
  next_agent?: string;
  plan_details?: any;
  code_files?: any;
  dependencies?: string[];
  modified_files?: string[];
  ui_changes?: string[];
  test_results?: {
    status: string;
    tests_run: string[];
    overall_assessment: string;
    syntax_validation?: any;
    build_test?: any;
    functional_validation?: any;
    recommendations?: string[];
  };
}

interface WorkflowStep {
  id: string;
  name: string;
  status: 'pending' | 'active' | 'completed' | 'approved' | 'rejected';
  agent: string;
  timestamp?: string;
}

interface TaskWorkflow {
  task_id: string;
  transcript: string;
  steps: WorkflowStep[];
  current_step: number;
}

const VoiceInterface: React.FC = () => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [messages, setMessages] = useState<AgentResponse[]>([]);
  const [activeWorkflows, setActiveWorkflows] = useState<TaskWorkflow[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [generatingFiles, setGeneratingFiles] = useState<{[key: string]: boolean}>({});
  const [filesGenerated, setFilesGenerated] = useState<{[key: string]: boolean}>({});
  
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Helper functions for display names
  const getStepDisplayName = (step: string): string => {
    const stepMap: { [key: string]: string } = {
      'pm_completed': 'PM Analysis Complete',
      'pm_analysis': 'PM Analysis',
      'dev_completed': 'Development Complete', 
      'dev_analysis': 'Development Analysis',
      'dev_implementation': 'Development Implementation',
      'security_completed': 'Security Review Complete',
      'security_analysis': 'Security Analysis',
      'devops_completed': 'DevOps Review Complete',
      'devops_analysis': 'DevOps Analysis',
      'code_review': 'Code Review',
      'testing': 'Testing Phase',
      'deployment': 'Deployment Phase'
    };
    
    return stepMap[step] || step.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getNextAgentDisplayName = (nextStep: string): string => {
    const agentMap: { [key: string]: string } = {
      'dev_agent': 'Development Agent',
      'pm_agent': 'Project Manager Agent',
      'security_agent': 'Security Agent',
      'devops_agent': 'DevOps Agent',
      'testing_agent': 'Testing Agent',
      'code_review_agent': 'Code Review Agent',
      'completion': 'Task Completion',
      'manual_review': 'Manual Review',
      'final_review': 'Final Review'
    };
    
    return agentMap[nextStep] || nextStep.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

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
          
          // Update workflow tracking
          updateWorkflowStatus(response);
          
          // Clear any processing states when task completes
          if (response.status === 'completed' || response.status === 'rejected') {
            // Task completed, no additional cleanup needed
          }
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

  // Removed fetchPendingApprovals since approvals are no longer needed

  const updateWorkflowStatus = (response: AgentResponse) => {
    if (!response.task_id) return;

    setActiveWorkflows(prev => {
      const existing = prev.find(w => w.task_id === response.task_id);
      
      if (!existing) {
        // Create new workflow with simplified steps (no dev approval)
        const newWorkflow: TaskWorkflow = {
          task_id: response.task_id!,
          transcript: response.transcript || 'Unknown task',
          current_step: 0,
          steps: [
            { id: 'pm_analysis', name: 'PM Analysis', status: 'completed', agent: 'PM Agent' },
            { id: 'dev_implementation', name: 'Development', status: 'active', agent: 'Dev Agent' },
            { id: 'testing', name: 'Testing & Validation', status: 'pending', agent: 'Testing Agent' },
            { id: 'completion', name: 'Completion', status: 'pending', agent: 'System' }
          ]
        };

        // Update based on response status
        if (response.status === 'processing') {
          newWorkflow.steps[0].status = 'completed';
          newWorkflow.steps[1].status = 'active';
          newWorkflow.current_step = 1;
        }

        return [...prev, newWorkflow];
      } else {
        // Update existing workflow
        return prev.map(workflow => {
          if (workflow.task_id !== response.task_id) return workflow;

          const updated = { ...workflow };
          
          if (response.status === 'processing') {
            // Dev Agent is processing
            updated.steps[0].status = 'completed';
            updated.steps[1].status = 'active';
            updated.current_step = 1;
          } else if (response.status === 'completed') {
            // Mark all steps as completed, including testing
            updated.steps.forEach((step, index) => {
              if (index <= updated.current_step + 1) {
                step.status = index === updated.current_step ? 'approved' : 'completed';
              }
            });
            
            // If we have test results, mark testing step as completed
            if (response.test_results) {
              const testingStepIndex = updated.steps.findIndex(s => s.id === 'testing');
              if (testingStepIndex !== -1) {
                updated.steps[testingStepIndex].status = 'completed';
              }
            }
            
            updated.steps[updated.steps.length - 1].status = 'completed';
            updated.current_step = updated.steps.length - 1;
          } else if (response.status === 'rejected') {
            updated.steps[updated.current_step].status = 'rejected';
          }

          return updated;
        });
      }
    });
  };

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

  // Removed approval handling since dev approval is no longer required

  const generateFilesForTask = async (taskId: string) => {
    // Prevent multiple clicks
    if (generatingFiles[taskId]) {
      return;
    }

    try {
      // Set generating state
      setGeneratingFiles(prev => ({
        ...prev,
        [taskId]: true
      }));

      // Show loading state
      setMessages(prev => [...prev, {
        status: 'info',
        agent: 'File Generator',
        response: `🔄 **Generating Files...**\n\nProcessing task ${taskId}...`,
        transcript: `Generate files for ${taskId}`
      }]);

      const response = await fetch(`http://localhost:8000/generate-files/${taskId}`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (result.status === 'success') {
        // Mark files as generated for this task
        setFilesGenerated(prev => ({
          ...prev,
          [taskId]: true
        }));
        
        setMessages(prev => [...prev, {
          status: 'success',
          agent: 'File Generator',
          response: `✅ **Files Generated Successfully!**\n\n${result.message}\n\n**Generated Files:**\n${result.generated_files.map((f: any) => `• ${f.filename} (${f.size} bytes)`).join('\n')}\n\n**Location:** ${result.generated_dir || 'todo-ui/src/generated'}`,
          transcript: `Generate files for ${taskId}`
        }]);
      } else {
        setMessages(prev => [...prev, {
          status: 'error',
          agent: 'File Generator',
          response: `❌ **File Generation Failed**\n\n${result.error || 'Unknown error occurred'}`,
          transcript: `Generate files for ${taskId}`
        }]);
      }
    } catch (error) {
      console.error('Generate files error:', error);
      setMessages(prev => [...prev, {
        status: 'error',
        agent: 'File Generator',
        response: `❌ **File Generation Error**\n\n${error instanceof Error ? error.message : String(error)}`,
        transcript: `Generate files for ${taskId}`
      }]);
    } finally {
      // Clear generating state
      setGeneratingFiles(prev => {
        const updated = { ...prev };
        delete updated[taskId];
        return updated;
      });
    }
  };

  // Removed workflow editing functions since approvals are no longer required

  return (
    <div className="voice-interface">
      <div className="header">
        <h1>🎤 VocalCommit Admin - Voice Orchestrated SDLC</h1>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {connectionStatus}
        </div>
      </div>

      {/* Active Workflows Section */}
      {activeWorkflows.length > 0 && (
        <div className="active-workflows">
          <h3>🔄 Active Workflows ({activeWorkflows.length})</h3>
          <div className="workflows-container">
            {activeWorkflows.map((workflow) => (
              <div key={workflow.task_id} className="workflow-card">
                <div className="workflow-header">
                  <h4>{workflow.transcript}</h4>
                  <span className="task-id">ID: {workflow.task_id}</span>
                </div>
                
                <div className="workflow-progress">
                  <div className="progress-steps">
                    {workflow.steps.map((step, index) => (
                      <div 
                        key={step.id} 
                        className={`progress-step ${step.status} ${index === workflow.current_step ? 'current' : ''}`}
                      >
                        <div className="step-indicator">
                          {step.status === 'completed' && '✅'}
                          {step.status === 'approved' && '✅'}
                          {step.status === 'active' && '🔄'}
                          {step.status === 'rejected' && '❌'}
                          {step.status === 'pending' && '⏳'}
                        </div>
                        <div className="step-info">
                          <div className="step-name">{step.name}</div>
                          <div className="step-agent">{step.agent}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${(workflow.current_step / (workflow.steps.length - 1)) * 100}%` }}
                    ></div>
                  </div>
                </div>

                {/* Workflow feedback removed since no approvals needed */}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pending Approvals Section - Removed since dev approval is no longer required */}

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
            messages
              .filter(message => 
                // Only show actual agent responses, not system status updates
                message.agent && 
                !message.response.includes('🔄 **Processing**') &&
                !message.response.includes('📁 Modified') &&
                !message.response.includes('🌐 View changes')
              )
              .map((message, index) => (
              <div key={index} className={`message ${message.requires_approval ? 'pending-approval' : ''}`}>
                <div className="message-header">
                  <span className="agent-name">{message.agent || 'Orchestrator'}</span>
                  <span className={`message-status ${message.status}`}>{message.status}</span>
                </div>
                <div className="message-content">
                  {/* Clean up the response to focus on agent communication */}
                  {message.response
                    .replace(/📁 \*\*Files to Modify\*\*:.*?\n\n/gs, '')
                    .replace(/🔄 \*\*Status\*\*:.*?\n/g, '')
                    .replace(/💡 \*\*Updates\*\*:.*?\n/g, '')
                    .replace(/✨ \*\*Task ID\*\*:.*$/g, '')
                    .replace(/💡 \*\*Task ID\*\*:.*$/g, '')
                    .trim()
                  }
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
          <div className="agent-card active">
            <h4>🎯 PM Agent</h4>
            <p>Task planning and project coordination</p>
            <span className="agent-status-badge">Active</span>
          </div>
          <div className="agent-card active">
            <h4>💻 Dev Agent</h4>
            <p>AI-powered code generation with multi-file coordination</p>
            <span className="agent-status-badge">Active</span>
          </div>
          <div className="agent-card active">
            <h4>🧪 Testing Agent</h4>
            <p>Automated testing, validation & quality assurance</p>
            <span className="agent-status-badge">Active</span>
          </div>
          <div className="agent-card disabled">
            <h4>🔒 Security Agent</h4>
            <p>Code vulnerability scanning</p>
            <span className="agent-status-badge">Disabled</span>
          </div>
          <div className="agent-card disabled">
            <h4>🚀 DevOps Agent</h4>
            <p>Deployment and operations</p>
            <span className="agent-status-badge">Disabled</span>
          </div>
        </div>
      </div>

      <div className="footer-links">
        <h3>System Links</h3>
        <div className="links-grid">
          <a href="http://localhost:5174" target="_blank" className="link-card">
            <h4>📋 Todo UI</h4>
            <p>View generated tasks and progress</p>
            <span>localhost:5174</span>
          </a>
          <a href="http://localhost:8000/health" target="_blank" className="link-card">
            <h4>🔧 API Health</h4>
            <p>Check orchestrator status</p>
            <span>localhost:8000/health</span>
          </a>
          <a href="http://localhost:8000/pending-approvals" target="_blank" className="link-card">
            <h4>⏳ Pending Approvals</h4>
            <p>View pending approvals JSON</p>
            <span>localhost:8000/pending-approvals</span>
          </a>
        </div>
      </div>

    </div>
  );
};

export default VoiceInterface;