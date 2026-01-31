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
  commit_info?: {
    commit_hash?: string;
    commit_message?: string;
    timestamp?: string;
    status?: string;
    error?: string;
  };
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
  status: 'pending' | 'active' | 'completed' | 'approved' | 'rejected' | 'awaiting_commit_approval';
  agent: string;
  timestamp?: string;
}

interface TaskWorkflow {
  task_id: string;
  transcript: string;
  steps: WorkflowStep[];
  current_step: number;
  commit_info?: {
    commit_hash?: string;
    commit_message?: string;
    timestamp?: string;
    status?: string;
  };
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
  const [completedTasks, setCompletedTasks] = useState<{[key: string]: AgentResponse}>({});
  const [commitActions, setCommitActions] = useState<{[key: string]: boolean}>({});
  const [showCommitModal, setShowCommitModal] = useState(false);
  const [currentCommitTask, setCurrentCommitTask] = useState<{taskId: string, task: AgentResponse} | null>(null);
  
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
          
          // Handle completed tasks for commit approval
          if (response.status === 'completed' && response.task_id) {
            console.log('Received completed task:', response.task_id, 'with commit_info:', response.commit_info);
            setCompletedTasks(prev => ({
              ...prev,
              [response.task_id!]: response
            }));
            
            // Show commit approval popup for successful commits
            if (response.commit_info?.commit_hash) {
              setCurrentCommitTask({
                taskId: response.task_id,
                task: response
              });
              setShowCommitModal(true);
            }
          }
          
          // Handle commit approval/rollback notifications
          if (response.status === 'rolled_back' || response.status === 'approved') {
            // Remove from completed tasks
            if (response.task_id) {
              setCompletedTasks(prev => {
                const updated = { ...prev };
                delete updated[response.task_id!];
                return updated;
              });
              
              // Close modal if it's for this task
              if (currentCommitTask?.taskId === response.task_id) {
                setShowCommitModal(false);
                setCurrentCommitTask(null);
              }
            }
          }
          
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
            { id: 'commit', name: 'Git Commit', status: 'pending', agent: 'System' },
            { id: 'commit_approval', name: 'Commit Approval', status: 'pending', agent: 'User' }
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
            // Mark development and testing as completed, commit as completed, commit approval as awaiting
            updated.steps[0].status = 'completed'; // PM
            updated.steps[1].status = 'completed'; // Dev
            updated.steps[2].status = 'completed'; // Testing
            updated.steps[3].status = 'completed'; // Commit
            updated.steps[4].status = 'awaiting_commit_approval'; // Commit Approval
            updated.current_step = 4;
            
            // Store commit info
            if (response.commit_info) {
              updated.commit_info = response.commit_info;
            }
          } else if (response.status === 'approved') {
            // Commit approved - mark final step as approved
            updated.steps[4].status = 'approved';
          } else if (response.status === 'rolled_back') {
            // Commit rolled back - mark final step as rejected
            updated.steps[4].status = 'rejected';
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

  const approveCommit = async (taskId: string) => {
    if (commitActions[taskId]) return;

    try {
      setCommitActions(prev => ({ ...prev, [taskId]: true }));

      const response = await fetch(`http://localhost:8000/approve-commit/${taskId}`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.status === 'success') {
        setMessages(prev => [...prev, {
          status: 'success',
          agent: 'Git System',
          response: `✅ **Commit Approved**\n\nTask "${completedTasks[taskId]?.transcript}" has been approved.\n\n🔗 **Commit**: ${result.commit_hash}\n\n🔒 **Status**: Changes are now final (rollback no longer available)`,
          transcript: `Approve commit for ${taskId}`
        }]);

        // Remove from completed tasks and close modal
        setCompletedTasks(prev => {
          const updated = { ...prev };
          delete updated[taskId];
          return updated;
        });
        
        if (currentCommitTask?.taskId === taskId) {
          setShowCommitModal(false);
          setCurrentCommitTask(null);
        }
      } else {
        setMessages(prev => [...prev, {
          status: 'error',
          agent: 'Git System',
          response: `❌ **Approval Failed**\n\n${result.error || 'Unknown error occurred'}`,
          transcript: `Approve commit for ${taskId}`
        }]);
      }
    } catch (error) {
      console.error('Approve commit error:', error);
      setMessages(prev => [...prev, {
        status: 'error',
        agent: 'Git System',
        response: `❌ **Approval Error**\n\n${error instanceof Error ? error.message : String(error)}`,
        transcript: `Approve commit for ${taskId}`
      }]);
    } finally {
      setCommitActions(prev => {
        const updated = { ...prev };
        delete updated[taskId];
        return updated;
      });
    }
  };

  const rollbackCommit = async (taskId: string, hardRollback: boolean = false) => {
    if (commitActions[taskId]) return;

    try {
      setCommitActions(prev => ({ ...prev, [taskId]: true }));

      const response = await fetch(`http://localhost:8000/rollback-commit/${taskId}?hard_rollback=${hardRollback}`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.status === 'success') {
        setMessages(prev => [...prev, {
          status: 'success',
          agent: 'Git System',
          response: `🔄 **Commit Rolled Back**\n\nTask "${completedTasks[taskId]?.transcript}" has been rolled back.\n\n🔗 **Commit**: ${result.rolled_back_commit}\n\n${hardRollback ? '🗑️ **Hard Rollback**: Only affected files discarded (safer)' : '📝 **Soft Rollback**: Changes are now unstaged'}`,
          transcript: `Rollback commit for ${taskId}`
        }]);

        // Remove from completed tasks and close modal
        setCompletedTasks(prev => {
          const updated = { ...prev };
          delete updated[taskId];
          return updated;
        });
        
        if (currentCommitTask?.taskId === taskId) {
          setShowCommitModal(false);
          setCurrentCommitTask(null);
        }
      } else {
        setMessages(prev => [...prev, {
          status: 'error',
          agent: 'Git System',
          response: `❌ **Rollback Failed**\n\n${result.error || 'Unknown error occurred'}`,
          transcript: `Rollback commit for ${taskId}`
        }]);
      }
    } catch (error) {
      console.error('Rollback commit error:', error);
      setMessages(prev => [...prev, {
        status: 'error',
        agent: 'Git System',
        response: `❌ **Rollback Error**\n\n${error instanceof Error ? error.message : String(error)}`,
        transcript: `Rollback commit for ${taskId}`
      }]);
    } finally {
      setCommitActions(prev => {
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
                          {step.status === 'awaiting_commit_approval' && '⏳'}
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

      {/* Commit Approval Section */}
      {Object.keys(completedTasks).length > 0 && (
        <div className="commit-approvals">
          <h3>🔗 Commit Approvals ({Object.keys(completedTasks).length})</h3>
          <div className="approvals-container">
            {Object.entries(completedTasks).map(([taskId, task]) => (
              <div key={taskId} className="approval-card">
                <div className="approval-header">
                  <h4>{task.transcript}</h4>
                  <span className="task-id">ID: {taskId}</span>
                </div>
                
                <div className="commit-info">
                  {task.commit_info?.commit_hash && (
                    <div className="commit-details">
                      <div className="commit-hash">
                        🔗 Commit: <code>{task.commit_info.commit_hash}</code>
                      </div>
                      <div className="commit-timestamp">
                        📅 {task.commit_info.timestamp}
                      </div>
                    </div>
                  )}
                  
                  {task.modified_files && task.modified_files.length > 0 && (
                    <div className="modified-files">
                      <strong>📁 Modified Files ({task.modified_files.length}):</strong>
                      <ul>
                        {task.modified_files.slice(0, 5).map((file, index) => (
                          <li key={index}>{file}</li>
                        ))}
                        {task.modified_files.length > 5 && (
                          <li>... and {task.modified_files.length - 5} more</li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="approval-actions">
                  <button
                    onClick={() => approveCommit(taskId)}
                    disabled={commitActions[taskId]}
                    className="approve-btn"
                  >
                    {commitActions[taskId] ? '⏳ Approving...' : '✅ Approve Commit'}
                  </button>
                  
                  <button
                    onClick={() => rollbackCommit(taskId, false)}
                    disabled={commitActions[taskId]}
                    className="rollback-soft-btn"
                  >
                    {commitActions[taskId] ? '⏳ Rolling back...' : '🔄 Soft Rollback'}
                  </button>
                  
                  <button
                    onClick={() => rollbackCommit(taskId, true)}
                    disabled={commitActions[taskId]}
                    className="rollback-hard-btn"
                  >
                    {commitActions[taskId] ? '⏳ Rolling back...' : '🗑️ Hard Rollback'}
                  </button>
                </div>

                <div className="rollback-info">
                  <small>
                    <strong>Soft Rollback:</strong> Keeps changes as unstaged files<br/>
                    <strong>Hard Rollback:</strong> Completely discards all changes
                  </small>
                </div>
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

      {/* Commit Approval Modal */}
      {showCommitModal && currentCommitTask && (
        <div className="modal-overlay">
          <div className="modal commit-approval-modal">
            <div className="modal-header">
              <h3>🔗 Commit Approval Required</h3>
              <button onClick={() => { setShowCommitModal(false); setCurrentCommitTask(null); }} className="close-btn">
                ×
              </button>
            </div>
            
            <div className="modal-body">
              <div className="commit-task-info">
                <h4>{currentCommitTask.task.transcript}</h4>
                <div className="task-id">Task ID: {currentCommitTask.taskId}</div>
              </div>
              
              <div className="commit-details-modal">
                {currentCommitTask.task.commit_info?.commit_hash ? (
                  <>
                    <div className="commit-hash-display">
                      <strong>🔗 Commit Hash:</strong>
                      <code>{currentCommitTask.task.commit_info.commit_hash}</code>
                    </div>
                    
                    <div className="commit-timestamp-display">
                      <strong>📅 Timestamp:</strong>
                      {currentCommitTask.task.commit_info.timestamp}
                    </div>
                    
                    {currentCommitTask.task.modified_files && currentCommitTask.task.modified_files.length > 0 && (
                      <div className="modified-files-modal">
                        <strong>📁 Modified Files ({currentCommitTask.task.modified_files.length}):</strong>
                        <div className="file-list-modal">
                          {currentCommitTask.task.modified_files.map((file, index) => (
                            <div key={index} className="file-item">{file}</div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div className="commit-message-preview">
                      <strong>💬 What was done:</strong>
                      <p>{currentCommitTask.task.transcript}</p>
                    </div>
                  </>
                ) : (
                  <div className="commit-error-modal">
                    ⚠️ Commit information not available
                  </div>
                )}
              </div>
              
              <div className="rollback-explanation">
                <h4>Choose your action:</h4>
                <div className="action-explanations">
                  <div className="action-explanation">
                    <strong>✅ Approve:</strong> Keep the changes permanently (no rollback possible)
                  </div>
                  <div className="action-explanation">
                    <strong>🔄 Soft Rollback:</strong> Undo the commit but keep changes as unstaged files
                  </div>
                  <div className="action-explanation">
                    <strong>🗑️ Hard Rollback:</strong> Only discard the specific files that were changed (safer)
                  </div>
                </div>
              </div>
            </div>
            
            <div className="modal-footer">
              {currentCommitTask.task.commit_info?.commit_hash ? (
                <>
                  <button
                    onClick={() => rollbackCommit(currentCommitTask.taskId, true)}
                    disabled={commitActions[currentCommitTask.taskId]}
                    className="rollback-hard-btn modal-btn"
                  >
                    {commitActions[currentCommitTask.taskId] ? '⏳ Processing...' : '🗑️ Hard Rollback'}
                  </button>
                  
                  <button
                    onClick={() => rollbackCommit(currentCommitTask.taskId, false)}
                    disabled={commitActions[currentCommitTask.taskId]}
                    className="rollback-soft-btn modal-btn"
                  >
                    {commitActions[currentCommitTask.taskId] ? '⏳ Processing...' : '🔄 Soft Rollback'}
                  </button>
                  
                  <button
                    onClick={() => approveCommit(currentCommitTask.taskId)}
                    disabled={commitActions[currentCommitTask.taskId]}
                    className="approve-btn modal-btn primary"
                  >
                    {commitActions[currentCommitTask.taskId] ? '⏳ Processing...' : '✅ Approve Commit'}
                  </button>
                </>
              ) : (
                <button onClick={() => { setShowCommitModal(false); setCurrentCommitTask(null); }} className="cancel-btn modal-btn">
                  Close
                </button>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default VoiceInterface;