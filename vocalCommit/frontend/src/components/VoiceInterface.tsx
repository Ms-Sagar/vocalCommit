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

interface PendingApproval {
  task_id: string;
  step: string;
  transcript: string;
  next_step: string;
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

// Define API and WebSocket URLs from environment variables or defaults
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper to derive WS URL from API URL if WS_URL is not explicitly provided
const getWsUrl = () => {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  // Remove trailing slash if present
  const cleanBase = API_BASE_URL.replace(/\/$/, '');
  // Switch protocol: http -> ws, https -> wss
  const wsProtocol = cleanBase.startsWith('https') ? 'wss' : 'ws';
  const wsBase = cleanBase.replace(/^https?/, wsProtocol);
  return `${wsBase}/ws`;
};

const WS_URL = getWsUrl();

const VoiceInterface: React.FC = () => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [messages, setMessages] = useState<AgentResponse[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [activeWorkflows, setActiveWorkflows] = useState<TaskWorkflow[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [approvalFeedback, setApprovalFeedback] = useState<{ [key: string]: string }>({});
  const [processingApprovals, setProcessingApprovals] = useState<{ [key: string]: boolean }>({});
  const [generatingFiles, setGeneratingFiles] = useState<{ [key: string]: boolean }>({});
  const [filesGenerated, setFilesGenerated] = useState<{ [key: string]: boolean }>({});
  const [editingWorkflow, setEditingWorkflow] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    transcript: '',
    description: '',
    priority: 'medium',
    estimated_effort: '',
    breakdown: [] as string[]
  });

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
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        setIsConnected(true);
        setConnectionStatus('Connected to VocalCommit Orchestrator');
        console.log('Connected to VocalCommit WebSocket');
        fetchPendingApprovals();
      };

      ws.onmessage = (event) => {
        try {
          const response: AgentResponse = JSON.parse(event.data);
          setMessages(prev => [...prev, response]);

          // Update workflow tracking
          updateWorkflowStatus(response);

          // If this is a pending approval, refresh the approvals list
          if (response.requires_approval) {
            fetchPendingApprovals();
          }

          // Clear approval feedback after successful operations
          if (response.status === 'completed' || response.status === 'rejected') {
            setApprovalFeedback(prev => {
              const updated = { ...prev };
              delete updated[response.task_id || ''];
              return updated;
            });
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

  const fetchPendingApprovals = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/pending-approvals`);
      const data = await response.json();
      setPendingApprovals(data.pending_approvals || []);
    } catch (error) {
      console.error('Error fetching pending approvals:', error);
    }
  };

  const updateWorkflowStatus = (response: AgentResponse) => {
    if (!response.task_id) return;

    setActiveWorkflows(prev => {
      const existing = prev.find(w => w.task_id === response.task_id);

      if (!existing) {
        // Create new workflow with dynamic steps based on response
        const newWorkflow: TaskWorkflow = {
          task_id: response.task_id!,
          transcript: response.transcript || 'Unknown task',
          current_step: 0,
          steps: [
            { id: 'pm_analysis', name: 'PM Analysis', status: 'pending', agent: 'PM Agent' },
            { id: 'pm_approval', name: 'PM Approval', status: 'pending', agent: 'Manual Review' },
            { id: 'dev_implementation', name: 'Development', status: 'pending', agent: 'Dev Agent' },
            { id: 'testing', name: 'Testing & Validation', status: 'pending', agent: 'Testing Agent' },
            { id: 'completion', name: 'Completion', status: 'pending', agent: 'System' }
          ]
        };

        // Update based on response status
        if (response.status === 'pending_approval') {
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

          if (response.status === 'pending_approval') {
            // Handle different types of approvals
            if (response.agent === 'PM Agent') {
              updated.steps[0].status = 'completed';
              updated.steps[1].status = 'active';
              updated.current_step = 1;
            } else if (response.agent === 'Dev Agent') {
              updated.steps[2].status = 'completed';
              updated.steps[3].status = 'active';
              updated.current_step = 3;
            }
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
          } else if (response.status === 'approval_confirmed') {
            // Handle approval confirmation
            const currentStep = updated.current_step;
            if (currentStep < updated.steps.length - 1) {
              updated.steps[currentStep].status = 'approved';
              updated.steps[currentStep + 1].status = 'active';
              updated.current_step = currentStep + 1;
            }
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

  const handleApproval = async (taskId: string, action: 'approve' | 'reject') => {
    // Prevent multiple clicks
    if (processingApprovals[taskId]) {
      return;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Set processing state immediately
      setProcessingApprovals(prev => ({
        ...prev,
        [taskId]: true
      }));

      // Show immediate feedback
      setApprovalFeedback(prev => ({
        ...prev,
        [taskId]: action === 'approve' ? '🔄 Processing approval...' : '🔄 Processing rejection...'
      }));

      const message: VoiceMessage = {
        type: 'approval',
        transcript: `${action}_${taskId}`,
        timestamp: new Date().toISOString()
      };

      wsRef.current.send(JSON.stringify(message));

      // Update workflow status immediately for visual feedback
      setActiveWorkflows(prev => prev.map(workflow => {
        if (workflow.task_id !== taskId) return workflow;

        const updated = { ...workflow };
        if (action === 'approve') {
          // Find current step and advance it
          const currentStepIndex = updated.current_step;
          if (currentStepIndex < updated.steps.length - 1) {
            updated.steps[currentStepIndex].status = 'approved';
            updated.steps[currentStepIndex + 1].status = 'active';
            updated.current_step = currentStepIndex + 1;
          }
        } else {
          // Mark current step as rejected
          updated.steps[updated.current_step].status = 'rejected';
        }
        return updated;
      }));

      // Set a longer timeout for better user experience
      setTimeout(() => {
        // Update feedback based on action
        setApprovalFeedback(prev => ({
          ...prev,
          [taskId]: action === 'approve'
            ? '✅ Approved! Processing with next agent...'
            : '❌ Task rejected and suspended'
        }));

        // Refresh approvals to get updated state
        fetchPendingApprovals();

        // Clear processing and feedback after longer delay
        setTimeout(() => {
          setProcessingApprovals(prev => {
            const updated = { ...prev };
            delete updated[taskId];
            return updated;
          });

          setApprovalFeedback(prev => {
            const updated = { ...prev };
            delete updated[taskId];
            return updated;
          });
        }, 4000); // Increased to 4 seconds for better visibility
      }, 1500); // Increased initial delay
    }
  };

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

      const response = await fetch(`${API_BASE_URL}/generate-files/${taskId}`, {
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

  const startEditingWorkflow = async (taskId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`);
      const workflow = await response.json();

      if (workflow.plan) {
        setEditForm({
          transcript: workflow.title || '',
          description: workflow.plan.description || '',
          priority: workflow.plan.priority || 'medium',
          estimated_effort: workflow.plan.estimated_effort || '',
          breakdown: workflow.plan.breakdown || []
        });
        setEditingWorkflow(taskId);
      }
    } catch (error) {
      console.error('Error fetching workflow details:', error);
    }
  };

  const saveWorkflowEdit = async () => {
    if (!editingWorkflow) return;

    try {
      const response = await fetch(`${API_BASE_URL}/admin-workflows/${editingWorkflow}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          transcript: editForm.transcript,
          plan: {
            description: editForm.description,
            priority: editForm.priority,
            estimated_effort: editForm.estimated_effort,
            breakdown: editForm.breakdown
          }
        })
      });

      const result = await response.json();

      if (result.status === 'success') {
        setMessages(prev => [...prev, {
          status: 'success',
          agent: 'System',
          response: `✅ **Workflow Updated Successfully!**\n\nTask "${editForm.transcript}" has been updated with your changes.`,
          transcript: editForm.transcript
        }]);

        // Refresh pending approvals
        fetchPendingApprovals();

        // Close edit modal
        setEditingWorkflow(null);
      } else {
        alert(`Error updating workflow: ${result.error}`);
      }
    } catch (error) {
      alert(`Error updating workflow: ${error}`);
    }
  };

  const cancelWorkflowEdit = () => {
    setEditingWorkflow(null);
    setEditForm({
      transcript: '',
      description: '',
      priority: 'medium',
      estimated_effort: '',
      breakdown: []
    });
  };

  const addBreakdownStep = () => {
    setEditForm(prev => ({
      ...prev,
      breakdown: [...prev.breakdown, '']
    }));
  };

  const updateBreakdownStep = (index: number, value: string) => {
    setEditForm(prev => ({
      ...prev,
      breakdown: prev.breakdown.map((step, i) => i === index ? value : step)
    }));
  };

  const removeBreakdownStep = (index: number) => {
    setEditForm(prev => ({
      ...prev,
      breakdown: prev.breakdown.filter((_, i) => i !== index)
    }));
  };

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

                {approvalFeedback[workflow.task_id] && (
                  <div className="approval-feedback">
                    {approvalFeedback[workflow.task_id]}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pending Approvals Section */}
      {pendingApprovals.length > 0 && (
        <div className="pending-approvals">
          <h3>⏳ Pending Approvals ({pendingApprovals.length})</h3>
          <div className="approvals-container">
            {pendingApprovals.map((approval) => (
              <div key={approval.task_id} className={`approval-card ${approval.step}`}>
                <div className="approval-header">
                  <h4>Task: {approval.transcript}</h4>
                  <span className="task-id">ID: {approval.task_id}</span>
                  <span className={`approval-type ${approval.step}`}>
                    {getStepDisplayName(approval.step)}
                  </span>
                </div>
                <div className="approval-details">
                  <p><strong>Current Step:</strong> {getStepDisplayName(approval.step)}</p>
                  <p><strong>Next Agent:</strong> {getNextAgentDisplayName(approval.next_step)}</p>
                  <p><strong>Status:</strong> Waiting for manual approval to proceed</p>
                </div>
                <div className="approval-actions">
                  <button
                    className="edit-btn"
                    onClick={() => startEditingWorkflow(approval.task_id)}
                  >
                    ✏️ Edit
                  </button>
                  <button
                    className="approve-btn"
                    onClick={() => handleApproval(approval.task_id, 'approve')}
                    disabled={processingApprovals[approval.task_id] || !!approvalFeedback[approval.task_id]}
                  >
                    {processingApprovals[approval.task_id] ? '🔄 Processing...' : '✅ Approve'}
                  </button>
                  <button
                    className="reject-btn"
                    onClick={() => handleApproval(approval.task_id, 'reject')}
                    disabled={processingApprovals[approval.task_id] || !!approvalFeedback[approval.task_id]}
                  >
                    {processingApprovals[approval.task_id] ? '🔄 Processing...' : '❌ Reject'}
                  </button>
                </div>

                {approvalFeedback[approval.task_id] && (
                  <div className="approval-feedback">
                    {approvalFeedback[approval.task_id]}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

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
              <div key={index} className={`message ${message.requires_approval ? 'pending-approval' : ''}`}>
                <div className="message-header">
                  <span className="agent-name">{message.agent || 'Orchestrator'}</span>
                  <span className={`message-status ${message.status}`}>{message.status}</span>
                  {message.requires_approval && (
                    <span className="approval-required">⏳ Approval Required</span>
                  )}
                </div>
                <div className="message-content">
                  {message.response}
                </div>

                {/* Testing Results Display */}
                {message.test_results && (
                  <div className="testing-results">
                    <h4>🧪 Testing Results</h4>
                    <div className="test-summary">
                      <div className={`test-status ${message.test_results.status}`}>
                        Status: {message.test_results.status.toUpperCase()}
                      </div>
                      <div className="test-assessment">
                        {message.test_results.overall_assessment}
                      </div>
                    </div>

                    {message.test_results.tests_run && message.test_results.tests_run.length > 0 && (
                      <div className="tests-executed">
                        <strong>Tests Executed:</strong>
                        <div className="test-badges">
                          {message.test_results.tests_run.map((test, idx) => (
                            <span key={idx} className="test-badge">
                              {test === 'syntax_validation' && '📝 Syntax'}
                              {test === 'build_test' && '🔨 Build'}
                              {test === 'functional_validation' && '⚙️ Functional'}
                              {!['syntax_validation', 'build_test', 'functional_validation'].includes(test) && test}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Detailed Test Results */}
                    <div className="detailed-test-results">
                      {message.test_results.syntax_validation && (
                        <div className="test-detail">
                          <strong>📝 Syntax Validation:</strong>
                          <span className={`result-status ${message.test_results.syntax_validation.status}`}>
                            {message.test_results.syntax_validation.status}
                          </span>
                          {message.test_results.syntax_validation.files_tested && (
                            <div className="files-tested">
                              Tested: {message.test_results.syntax_validation.files_tested.join(', ')}
                            </div>
                          )}
                        </div>
                      )}

                      {message.test_results.build_test && (
                        <div className="test-detail">
                          <strong>🔨 Build Test:</strong>
                          <span className={`result-status ${message.test_results.build_test.status}`}>
                            {message.test_results.build_test.status}
                          </span>
                          {message.test_results.build_test.message && (
                            <div className="build-message">
                              {message.test_results.build_test.message}
                            </div>
                          )}
                        </div>
                      )}

                      {message.test_results.functional_validation && (
                        <div className="test-detail">
                          <strong>⚙️ Functional Validation:</strong>
                          <span className={`result-status ${message.test_results.functional_validation.status}`}>
                            {message.test_results.functional_validation.status}
                          </span>
                          {message.test_results.functional_validation.ai_powered && (
                            <span className="ai-badge">🤖 AI-Powered</span>
                          )}
                        </div>
                      )}
                    </div>

                    {message.test_results.recommendations && message.test_results.recommendations.length > 0 && (
                      <div className="test-recommendations">
                        <strong>💡 Recommendations:</strong>
                        <ul>
                          {message.test_results.recommendations.slice(0, 3).map((rec, idx) => (
                            <li key={idx}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Modified Files Display */}
                {message.modified_files && message.modified_files.length > 0 && (
                  <div className="modified-files">
                    <strong>📁 Modified Files ({message.modified_files.length}):</strong>
                    <div className="file-list">
                      {message.modified_files.map((file, idx) => (
                        <span key={idx} className="file-badge">{file}</span>
                      ))}
                    </div>
                  </div>
                )}
                {message.transcript && (
                  <div className="original-command">
                    Original: "{message.transcript}"
                  </div>
                )}
                {message.task_id && (
                  <div className="task-actions">
                    <div className="task-id-display">
                      Task ID: {message.task_id}
                    </div>
                    {message.status === 'completed' && !filesGenerated[message.task_id!] && (
                      <button
                        className="generate-files-btn"
                        onClick={() => generateFilesForTask(message.task_id!)}
                        disabled={generatingFiles[message.task_id!]}
                      >
                        {generatingFiles[message.task_id!] ? '🔄 Generating...' : '📁 Generate Files to Frontend'}
                      </button>
                    )}
                    {filesGenerated[message.task_id!] && (
                      <div className="files-generated-indicator">
                        ✅ Files Generated Successfully
                      </div>
                    )}
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

      {/* Edit Workflow Modal */}
      {editingWorkflow && (
        <div className="modal-overlay">
          <div className="modal edit-workflow-modal">
            <div className="modal-header">
              <h3>✏️ Edit Workflow</h3>
              <button
                className="close-btn"
                onClick={cancelWorkflowEdit}
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div className="form-group">
                <label>Task Description *</label>
                <input
                  type="text"
                  value={editForm.transcript}
                  onChange={(e) => setEditForm({ ...editForm, transcript: e.target.value })}
                  placeholder="Enter task description..."
                />
              </div>

              <div className="form-group">
                <label>Detailed Description</label>
                <textarea
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  placeholder="Enter detailed description..."
                  rows={3}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Priority</label>
                  <select
                    value={editForm.priority}
                    onChange={(e) => setEditForm({ ...editForm, priority: e.target.value })}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Estimated Effort</label>
                  <input
                    type="text"
                    value={editForm.estimated_effort}
                    onChange={(e) => setEditForm({ ...editForm, estimated_effort: e.target.value })}
                    placeholder="e.g., 2-4 hours, 1-2 days"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Implementation Steps</label>
                <div className="breakdown-list">
                  {editForm.breakdown.map((step, index) => (
                    <div key={index} className="breakdown-item">
                      <input
                        type="text"
                        value={step}
                        onChange={(e) => updateBreakdownStep(index, e.target.value)}
                        placeholder={`Step ${index + 1}...`}
                      />
                      <button
                        className="remove-step-btn"
                        onClick={() => removeBreakdownStep(index)}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  <button
                    className="add-step-btn"
                    onClick={addBreakdownStep}
                  >
                    ➕ Add Step
                  </button>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="cancel-btn"
                onClick={cancelWorkflowEdit}
              >
                Cancel
              </button>
              <button
                className="save-btn"
                onClick={saveWorkflowEdit}
                disabled={!editForm.transcript.trim()}
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VoiceInterface;