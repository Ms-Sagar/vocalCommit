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
  github_pushed?: boolean;
  github_commit_info?: {
    commit_hash?: string;
    commit_message?: string;
    timestamp?: string;
    pushed_at?: string;
  };
  github_push_error?: string;
  type?: string; // For WebSocket message types like 'github_pushed', 'commit_dropped', 'task_failed'
  commit_hash?: string; // For WebSocket notifications
  reverted_commit?: string; // For drop commit responses
  changed_files?: string[]; // For drop commit responses
  github_rollback_pushed?: boolean; // For rollback with GitHub push
  github_rollback_info?: {
    commit_hash?: string;
    pushed_at?: string;
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
  // Error handling fields
  errors?: any;
  error_type?: string; // 'quota_exceeded', 'invalid_key', 'general_error'
  is_quota_exceeded?: boolean;
  is_invalid_key?: boolean;
  action_required?: string; // 'update_api_key', etc.
  // Production mode fields
  pending_github_push?: boolean;
  github_ready?: boolean;
  gemini_analysis?: {
    risk_assessment?: string;
    confidence?: number;
    [key: string]: any;
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
  const [activeWorkflows, setActiveWorkflows] = useState<TaskWorkflow[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  // const [generatingFiles, setGeneratingFiles] = useState<{ [key: string]: boolean }>({});
  // const [filesGenerated, setFilesGenerated] = useState<{ [key: string]: boolean }>({});
  const [completedTasks, setCompletedTasks] = useState<{ [key: string]: AgentResponse }>({});
  const [commitActions, setCommitActions] = useState<{ [key: string]: boolean }>({});
  const [showCommitModal, setShowCommitModal] = useState(false);
  const [currentCommitTask, setCurrentCommitTask] = useState<{ taskId: string, task: AgentResponse } | null>(null);
  const [isDroppingCommit, setIsDroppingCommit] = useState(false);
  const [lastGithubPush, setLastGithubPush] = useState<{ taskId: string, commitHash: string, timestamp: string } | null>(null);
  
  // API Key Management State
  const [apiKeyStatus, setApiKeyStatus] = useState<{
    status: string;
    configured: boolean;
    masked_key?: string;
    message: string;
    quota_info?: any;
    error_details?: string;
  } | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [newApiKey, setNewApiKey] = useState('');
  const [isUpdatingApiKey, setIsUpdatingApiKey] = useState(false);
  const [apiKeyValidation, setApiKeyValidation] = useState<{
    isValid: boolean;
    message: string;
  } | null>(null);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // API Key Validation Function
  const validateApiKey = (key: string): { isValid: boolean; message: string } => {
    if (!key.trim()) {
      return { isValid: false, message: '' }; // Empty is okay, just disable button
    }

    // Check minimum length
    if (key.length < 20) {
      return { 
        isValid: false, 
        message: '❌ API key is too short. Minimum 20 characters required.' 
      };
    }

    // Check for common mistakes
    if (key.includes(' ')) {
      return { 
        isValid: false, 
        message: '❌ API key contains spaces. Please remove any spaces.' 
      };
    }

    // All checks passed
    return { 
      isValid: true, 
      message: '✅ API key format looks valid' 
    };
  };

  // Handle API key input change with validation
  const handleApiKeyChange = (value: string) => {
    setNewApiKey(value);
    
    // Validate on change
    if (value.trim()) {
      const validation = validateApiKey(value);
      setApiKeyValidation(validation);
    } else {
      setApiKeyValidation(null);
    }
  };

  // API Key Management Functions (defined early so they can be used in useEffect)
  const fetchApiKeyStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api-key-status`);
      if (response.ok) {
        const data = await response.json();
        setApiKeyStatus(data);
      }
    } catch (error) {
      console.error('Error fetching API key status:', error);
    }
  };

  const updateApiKey = async () => {
    if (!newApiKey.trim() || isUpdatingApiKey) return;

    // Validate before submitting
    const validation = validateApiKey(newApiKey);
    if (!validation.isValid) {
      setApiKeyValidation(validation);
      return;
    }

    try {
      setIsUpdatingApiKey(true);

      const response = await fetch(`${API_BASE_URL}/update-api-key`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ api_key: newApiKey.trim() })
      });

      const result = await response.json();

      if (result.status === 'success' || result.status === 'warning') {
        const isTemporary = result.temporary === true;
        const isProduction = result.production_mode === true;
        
        let responseMessage = `✅ **API Key Updated**\n\n${result.message}\n\n🔑 **New Key**: ${result.masked_key}`;
        
        if (isProduction && isTemporary) {
          responseMessage += '\n\n⚠️ **Production Mode**: This change is temporary. To make it permanent:\n1. Go to your Render dashboard\n2. Navigate to your service settings\n3. Update the GEMINI_API_KEY environment variable\n4. Restart the service';
        }
        
        setMessages(prev => [...prev, {
          status: result.status === 'warning' ? 'info' : 'success',
          agent: 'System',
          response: responseMessage,
          transcript: 'Update Gemini API key'
        }]);

        // Refresh API key status immediately
        await fetchApiKeyStatus();

        // Close modal and clear input
        setShowApiKeyModal(false);
        setNewApiKey('');
        setApiKeyValidation(null);
      } else {
        setMessages(prev => [...prev, {
          status: 'error',
          agent: 'System',
          response: `❌ **API Key Update Failed**\n\n${result.message}`,
          transcript: 'Update Gemini API key'
        }]);
      }
    } catch (error) {
      console.error('Error updating API key:', error);
      setMessages(prev => [...prev, {
        status: 'error',
        agent: 'System',
        response: `❌ **API Key Update Error**\n\n${error instanceof Error ? error.message : String(error)}`,
        transcript: 'Update Gemini API key'
      }]);
    } finally {
      setIsUpdatingApiKey(false);
    }
  };

  // Helper functions for display names
  // const getStepDisplayName = (step: string): string => {
  //   const stepMap: { [key: string]: string } = {
  //     'pm_completed': 'PM Analysis Complete',
  //     'pm_analysis': 'PM Analysis',
  //     'dev_completed': 'Development Complete',
  //     'dev_analysis': 'Development Analysis',
  //     'dev_implementation': 'Development Implementation',
  //     'security_completed': 'Security Review Complete',
  //     'security_analysis': 'Security Analysis',
  //     'devops_completed': 'DevOps Review Complete',
  //     'devops_analysis': 'DevOps Analysis',
  //     'code_review': 'Code Review',
  //     'testing': 'Testing Phase',
  //     'deployment': 'Deployment Phase'
  //   };

  //   return stepMap[step] || step.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  // };

  // const getNextAgentDisplayName = (nextStep: string): string => {
  //   const agentMap: { [key: string]: string } = {
  //     'dev_agent': 'Development Agent',
  //     'pm_agent': 'Project Manager Agent',
  //     'security_agent': 'Security Agent',
  //     'devops_agent': 'DevOps Agent',
  //     'testing_agent': 'Testing Agent',
  //     'code_review_agent': 'Code Review Agent',
  //     'completion': 'Task Completion',
  //     'manual_review': 'Manual Review',
  //     'final_review': 'Final Review'
  //   };

  //   return agentMap[nextStep] || nextStep.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  // };

  // Fetch API key status on mount and periodically
  useEffect(() => {
    fetchApiKeyStatus();
    const interval = setInterval(fetchApiKeyStatus, 60000); // Check every minute
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Initialize WebSocket connection
    const connectWebSocket = () => {
      const ws = new WebSocket(WS_URL);

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

          // Handle task failures (especially quota exceeded)
          if (response.type === 'task_failed' || response.status === 'failed') {
            console.log('Task failed:', response.task_id, 'Error type:', response.error_type);
            
            // If quota exceeded or invalid key, automatically refresh API key status
            if (response.is_quota_exceeded || response.is_invalid_key) {
              fetchApiKeyStatus();
              
              // Show a prominent notification
              if (response.is_quota_exceeded) {
                // Automatically open API key modal after a short delay
                setTimeout(() => {
                  setShowApiKeyModal(true);
                }, 2000);
              }
            }
          }

          // Handle completed tasks for commit approval
          if (response.status === 'completed' && response.task_id) {
            console.log('Received completed task:', response.task_id, 'with commit_info:', response.commit_info);
            setCompletedTasks(prev => ({
              ...prev,
              [response.task_id!]: response
            }));

            // Check if task was auto-pushed to GitHub
            if (response.github_pushed && response.github_commit_info?.commit_hash) {
              setLastGithubPush({
                taskId: response.task_id,
                commitHash: response.github_commit_info.commit_hash,
                timestamp: response.github_commit_info.timestamp || new Date().toISOString()
              });
            }

            // Show commit approval popup for tasks pending GitHub push (production mode)
            // OR for tasks with local commits that haven't been pushed yet
            if ((response.pending_github_push && response.github_ready) || 
                (response.commit_info?.commit_hash && !response.github_pushed)) {
              setCurrentCommitTask({
                taskId: response.task_id,
                task: response
              });
              setShowCommitModal(true);
            }
          }

          // Handle GitHub push notifications
          if (response.type === 'github_pushed' && response.task_id) {
            setLastGithubPush({
              taskId: response.task_id,
              commitHash: response.commit_hash || 'unknown',
              timestamp: new Date().toISOString()
            });
          }

          // Handle commit drop notifications
          if (response.type === 'commit_dropped' || response.type === 'commit_reverted') {
            setLastGithubPush(null); // Clear the last push info
          }

          // Handle commit approval/rollback notifications
          if (response.status === 'rolled_back' || response.status === 'approved' || response.type === 'commit_approved') {
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
            
            // Handle GitHub push status for approved commits
            if ((response.status === 'approved' || response.type === 'commit_approved') && response.github_pushed && response.github_commit_info) {
              setLastGithubPush({
                taskId: response.task_id || '',
                commitHash: response.github_commit_info.commit_hash || '',
                timestamp: response.github_commit_info.timestamp || new Date().toISOString()
              });
            }
          }

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
        
        // Voice recognition only populates the input field
        // User must click submit button to send the command
        // This prevents duplicate requests from voice + text
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
      // Send command to backend (works for both voice-populated and manually-typed text)
      const message: VoiceMessage = {
        type: 'text_command',
        transcript: transcript.trim(),
        timestamp: new Date().toISOString()
      };

      wsRef.current.send(JSON.stringify(message));
      setTranscript('');
    }
  };

  // Removed handleApproval since dev approval is no longer required

  // const generateFilesForTask = async (taskId: string) => {
  //   // Prevent multiple clicks
  //   if (generatingFiles[taskId]) {
  //     return;
  //   }

  //   try {
  //     // Set generating state
  //     setGeneratingFiles(prev => ({
  //       ...prev,
  //       [taskId]: true
  //     }));

  //     // Show loading state
  //     setMessages(prev => [...prev, {
  //       status: 'info',
  //       agent: 'File Generator',
  //       response: `🔄 **Generating Files...**\n\nProcessing task ${taskId}...`,
  //       transcript: `Generate files for ${taskId}`
  //     }]);

  //     const response = await fetch(`${API_BASE_URL}/generate-files/${taskId}`, {
  //       method: 'POST'
  //     });

  //     if (!response.ok) {
  //       throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  //     }

  //     const result = await response.json();

  //     if (result.status === 'success') {
  //       // Mark files as generated for this task
  //       setFilesGenerated(prev => ({
  //         ...prev,
  //         [taskId]: true
  //       }));

  //       setMessages(prev => [...prev, {
  //         status: 'success',
  //         agent: 'File Generator',
  //         response: `✅ **Files Generated Successfully!**\n\n${result.message}\n\n**Generated Files:**\n${result.generated_files.map((f: any) => `• ${f.filename} (${f.size} bytes)`).join('\n')}\n\n**Location:** ${result.generated_dir || 'todo-ui/src/generated'}`,
  //         transcript: `Generate files for ${taskId}`
  //       }]);
  //     } else {
  //       setMessages(prev => [...prev, {
  //         status: 'error',
  //         agent: 'File Generator',
  //         response: `❌ **File Generation Failed**\n\n${result.error || 'Unknown error occurred'}`,
  //         transcript: `Generate files for ${taskId}`
  //       }]);
  //     }
  //   } catch (error) {
  //     console.error('Generate files error:', error);
  //     setMessages(prev => [...prev, {
  //       status: 'error',
  //       agent: 'File Generator',
  //       response: `❌ **File Generation Error**\n\n${error instanceof Error ? error.message : String(error)}`,
  //       transcript: `Generate files for ${taskId}`
  //     }]);
  //   } finally {
  //     // Clear generating state
  //     setGeneratingFiles(prev => {
  //       const updated = { ...prev };
  //       delete updated[taskId];
  //       return updated;
  //     });
  //   }
  // };

  // Removed startEditingWorkflow and saveWorkflowEdit since approvals are no longer required

  const approveCommit = async (taskId: string) => {
    if (commitActions[taskId]) return;

    try {
      setCommitActions(prev => ({ ...prev, [taskId]: true }));
      console.log(`[Approval] Starting approval for task: ${taskId}`);

      // Use the new approve-github-push endpoint that just pushes existing commit
      const response = await fetch(`${API_BASE_URL}/approve-github-push/${taskId}`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      console.log(`[Approval] Backend response:`, result);

      if (result.status === 'success') {
        // Build detailed success message with GitHub status
        let successMessage = `✅ **Pushed to GitHub**\n\nTask "${completedTasks[taskId]?.transcript}" has been pushed to production.\n\n🔗 **Commit**: ${result.commit_hash}\n\n🚀 **Status**: Live in TODO-UI repository`;

        setMessages(prev => [...prev, {
          status: 'success',
          agent: 'Git System',
          response: successMessage,
          transcript: `Push commit for ${taskId}`
        }]);

        // Remove from completed tasks and close modal immediately
        console.log(`[Approval] Removing task ${taskId} from completed tasks`);
        setCompletedTasks(prev => {
          const updated = { ...prev };
          delete updated[taskId];
          return updated;
        });

        // Close modal immediately
        if (currentCommitTask?.taskId === taskId) {
          console.log(`[Approval] Closing commit modal for task ${taskId}`);
          setShowCommitModal(false);
          setCurrentCommitTask(null);
        }

        // Update GitHub push status if successful
        if (result.github_pushed && result.github_commit_info) {
          setLastGithubPush({
            taskId: taskId,
            commitHash: result.github_commit_info.commit_hash,
            timestamp: result.github_commit_info.timestamp || new Date().toISOString()
          });
        }
      } else {
        console.error(`[Approval] Approval failed:`, result.error);
        
        setMessages(prev => [...prev, {
          status: 'error',
          agent: 'Git System',
          response: `❌ **Approval Failed**\n\n${result.error || 'Unknown error occurred'}`,
          transcript: `Approve commit for ${taskId}`
        }]);
      }
    } catch (error) {
      console.error('[Approval] Approve commit error:', error);
      
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

      const response = await fetch(`${API_BASE_URL}/rollback-commit/${taskId}?hard_rollback=${hardRollback}`, {
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

  const dropLatestCommit = async () => {
    if (isDroppingCommit) return;

    try {
      setIsDroppingCommit(true);

      const response = await fetch(`${API_BASE_URL}/drop-latest-commit`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.status === 'success') {
        setMessages(prev => [...prev, {
          status: 'success',
          agent: 'GitHub System',
          response: `🗑️ **Latest Commit Dropped**\n\nSuccessfully reverted commit ${result.reverted_commit} from TODO-UI production.\n\n**Original Task**: ${result.commit_message}\n\n**Files Affected**: ${result.changed_files?.length || 0} files\n\n✅ **Status**: Changes have been undone in production repository`,
          transcript: 'Drop latest commit from TODO-UI'
        }]);

        // Clear the last GitHub push info
        setLastGithubPush(null);
      } else {
        setMessages(prev => [...prev, {
          status: 'error',
          agent: 'GitHub System',
          response: `❌ **Drop Commit Failed**\n\n${result.error || 'Unknown error occurred'}\n\nThe latest commit could not be dropped from the TODO-UI repository.`,
          transcript: 'Drop latest commit from TODO-UI'
        }]);
      }
    } catch (error) {
      console.error('Drop commit error:', error);
      setMessages(prev => [...prev, {
        status: 'error',
        agent: 'GitHub System',
        response: `❌ **Drop Commit Error**\n\n${error instanceof Error ? error.message : String(error)}\n\nFailed to communicate with the orchestrator.`,
        transcript: 'Drop latest commit from TODO-UI'
      }]);
    } finally {
      setIsDroppingCommit(false);
    }
  };

  return (
    <div className="voice-interface">
      <div className="header">
        <h1>🎤 VocalCommit Admin - Voice Orchestrated SDLC</h1>
        <div className="header-status">
          <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            {connectionStatus}
          </div>
          {apiKeyStatus && (
            <div 
              className={`api-key-status ${apiKeyStatus.status}`}
              onClick={() => setShowApiKeyModal(true)}
              title={`Click to manage API key${apiKeyStatus.masked_key ? `\nCurrent: ${apiKeyStatus.masked_key}` : ''}${apiKeyStatus.quota_info ? `\nQuota: ${apiKeyStatus.quota_info.remaining_requests}/${apiKeyStatus.quota_info.max_requests_per_minute} requests remaining${apiKeyStatus.quota_info.reset_in_seconds > 0 ? `\nReset in: ${Math.ceil(apiKeyStatus.quota_info.reset_in_seconds)}s` : ''}` : ''}`}
            >
              <div className="status-content">
                <div className="status-main">
                  {apiKeyStatus.status === 'active' && '🔑 API Key: Active'}
                  {apiKeyStatus.status === 'quota_exceeded' && '⚠️ API Quota Exceeded'}
                  {apiKeyStatus.status === 'invalid' && '❌ API Key Invalid'}
                  {apiKeyStatus.status === 'missing' && '❌ API Key Missing'}
                  {apiKeyStatus.status === 'error' && '⚠️ API Key Error'}
                </div>
                {apiKeyStatus.masked_key && (
                  <div className="status-details">
                    <span className="masked-key-display">{apiKeyStatus.masked_key}</span>
                    {apiKeyStatus.quota_info && (
                      <>
                        <span className="quota-separator">•</span>
                        <span className="quota-display">
                          {apiKeyStatus.quota_info.remaining_requests}/{apiKeyStatus.quota_info.max_requests_per_minute} requests
                        </span>
                        {apiKeyStatus.quota_info.reset_in_seconds > 0 && apiKeyStatus.status === 'quota_exceeded' && (
                          <>
                            <span className="quota-separator">•</span>
                            <span className="quota-display">
                              Reset in {Math.ceil(apiKeyStatus.quota_info.reset_in_seconds)}s
                            </span>
                          </>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* API Key Management Modal */}
      {showApiKeyModal && (
        <div className="modal-overlay">
          <div className="modal api-key-modal">
            <div className="modal-header">
              <h3>🔑 Gemini API Key Management</h3>
              <button onClick={() => { setShowApiKeyModal(false); setNewApiKey(''); }} className="close-btn">
                ×
              </button>
            </div>

            <div className="modal-content">
              <div className="api-key-status-details">
                <div className={`status-badge ${apiKeyStatus?.status}`}>
                  Status: {apiKeyStatus?.status?.toUpperCase()}
                </div>
                <p className="status-message">{apiKeyStatus?.message}</p>
                
                {apiKeyStatus?.masked_key && (
                  <div className="current-key">
                    <strong>Current Key:</strong> <code>{apiKeyStatus.masked_key}</code>
                  </div>
                )}

                {apiKeyStatus?.quota_info && (
                  <div className="quota-info">
                    <h4>Quota Information:</h4>
                    <div className="quota-details">
                      <div>Remaining Requests: {apiKeyStatus.quota_info.remaining_requests}/{apiKeyStatus.quota_info.max_requests_per_minute} per minute</div>
                      {apiKeyStatus.quota_info.reset_in_seconds > 0 && (
                        <div>Reset in: {Math.ceil(apiKeyStatus.quota_info.reset_in_seconds)}s</div>
                      )}
                    </div>
                  </div>
                )}

                {apiKeyStatus?.error_details && (
                  <div className="error-details">
                    <strong>Error Details:</strong>
                    <pre>{apiKeyStatus.error_details}</pre>
                  </div>
                )}
              </div>

              <div className="api-key-update-section">
                <h4>Update API Key</h4>
                <p className="help-text">
                  Get your API key from <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer">Google AI Studio</a>
                </p>
                <input
                  type="password"
                  value={newApiKey}
                  onChange={(e) => handleApiKeyChange(e.target.value)}
                  placeholder="Enter new Gemini API key (minimum 20 characters)..."
                  className={`api-key-input ${apiKeyValidation ? (apiKeyValidation.isValid ? 'valid' : 'invalid') : ''}`}
                  onKeyPress={(e) => e.key === 'Enter' && apiKeyValidation?.isValid && updateApiKey()}
                />
                {apiKeyValidation && (
                  <div className={`validation-message ${apiKeyValidation.isValid ? 'valid' : 'invalid'}`}>
                    {apiKeyValidation.message}
                  </div>
                )}
              </div>
            </div>

            <div className="modal-footer">
              <button
                onClick={() => { 
                  setShowApiKeyModal(false); 
                  setNewApiKey(''); 
                  setApiKeyValidation(null);
                }}
                className="cancel-btn modal-btn"
              >
                Cancel
              </button>
              <button
                onClick={updateApiKey}
                disabled={!newApiKey.trim() || isUpdatingApiKey || !apiKeyValidation?.isValid}
                className="approve-btn modal-btn primary"
              >
                {isUpdatingApiKey ? '⏳ Updating...' : '✅ Update API Key'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* GitHub Push Status Section */}      {/* GitHub Push Status Section */}
      {lastGithubPush && (
        <div className="github-push-status">
          <h3>🚀 Latest Push to TODO-UI Production</h3>
          <div className="push-status-card">
            <div className="push-info">
              <div className="push-commit">
                <strong>🔗 Commit:</strong> <code>{lastGithubPush.commitHash}</code>
              </div>
              <div className="push-timestamp">
                <strong>📅 Pushed:</strong> {new Date(lastGithubPush.timestamp).toLocaleString()}
              </div>
              <div className="push-task">
                <strong>📝 Task ID:</strong> {lastGithubPush.taskId}
              </div>
            </div>
            <div className="push-actions">
              <button
                onClick={dropLatestCommit}
                disabled={isDroppingCommit}
                className="drop-commit-btn"
                title="Drop the latest commit from TODO-UI production repository"
              >
                {isDroppingCommit ? '⏳ Dropping...' : '🗑️ Drop Latest Commit'}
              </button>
            </div>
          </div>
          <div className="push-warning">
            <small>
              ⚠️ <strong>Warning:</strong> Dropping a commit will revert the latest changes in the TODO-UI production repository. 
              This action creates a revert commit and cannot be undone.
            </small>
          </div>
        </div>
      )}

      {/* API Error Banner (Quota Exceeded / Invalid Key) */}
      {apiKeyStatus && (apiKeyStatus.status === 'quota_exceeded' || apiKeyStatus.status === 'invalid') && (
        <div className={`api-error-banner ${apiKeyStatus.status}`}>
          <div className="error-banner-content">
            <div className="error-icon">
              {apiKeyStatus.status === 'quota_exceeded' ? '⚠️' : '❌'}
            </div>
            <div className="error-details">
              <h3>
                {apiKeyStatus.status === 'quota_exceeded' ? 'API Quota Exceeded' : 'Invalid API Key'}
              </h3>
              <p>{apiKeyStatus.message}</p>
              {apiKeyStatus.status === 'quota_exceeded' && apiKeyStatus.error_details && (
                <p className="error-hint">{apiKeyStatus.error_details}</p>
              )}
            </div>
            <div className="error-actions">
              <button
                onClick={() => setShowApiKeyModal(true)}
                className="update-key-btn"
              >
                🔑 Update API Key
              </button>
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noopener noreferrer"
                className="get-key-link"
              >
                Get New Key →
              </a>
            </div>
          </div>
        </div>
      )}

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
                  {/* Production mode: Show GitHub push pending status */}
                  {task.pending_github_push && task.github_ready && (
                    <div className="github-pending-info">
                      <div className="github-status">
                        🚀 Ready to push to TODO-UI production
                      </div>
                      {task.gemini_analysis && (
                        <div className="ai-summary">
                          🤖 AI Risk: <span className={`risk-${task.gemini_analysis.risk_assessment}`}>
                            {task.gemini_analysis.risk_assessment?.toUpperCase()}
                          </span> ({((task.gemini_analysis.confidence || 0) * 100).toFixed(0)}% confidence)
                        </div>
                      )}
                    </div>
                  )}

                  {/* Legacy mode: Show local commit info */}
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
                  {task.pending_github_push && task.github_ready ? (
                    /* Production mode: Only show Approve button */
                    <button
                      onClick={() => approveCommit(taskId)}
                      disabled={commitActions[taskId]}
                      className="approve-btn primary-action"
                    >
                      {commitActions[taskId] ? '⏳ Pushing to GitHub...' : '✅ Approve & Push to GitHub'}
                    </button>
                  ) : (
                    /* Legacy mode: Show all rollback options */
                    <>
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
                    </>
                  )}
                </div>

                {!task.pending_github_push && (
                  <div className="rollback-info">
                    <small>
                      <strong>Soft Rollback:</strong> Keeps changes as unstaged files<br />
                      <strong>Hard Rollback:</strong> Completely discards all changes
                    </small>
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
                            <pre>{JSON.stringify(message.test_results.syntax_validation, null, 2)}</pre>
                          </div>
                        )}

                        {message.test_results.build_test && (
                          <div className="test-detail">
                            <strong>🔨 Build Test:</strong>
                            <pre>{JSON.stringify(message.test_results.build_test, null, 2)}</pre>
                          </div>
                        )}

                        {message.test_results.functional_validation && (
                          <div className="test-detail">
                            <strong>⚙️ Functional Validation:</strong>
                            <pre>{JSON.stringify(message.test_results.functional_validation, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
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

            <div className="modal-content">
              <div className="commit-task-info">
                <h4>{currentCommitTask.task.transcript}</h4>
                <div className="task-id">Task ID: {currentCommitTask.taskId}</div>
              </div>

              <div className="commit-details-modal">
                {/* Production mode: Show pending GitHub push info */}
                {currentCommitTask.task.pending_github_push && currentCommitTask.task.github_ready ? (
                  <>
                    <div className="github-push-pending">
                      <strong>🚀 Ready to Push to GitHub</strong>
                      <p>Changes are ready to be pushed to the TODO-UI production repository.</p>
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

                    {currentCommitTask.task.gemini_analysis && (
                      <div className="ai-analysis-modal">
                        <strong>🤖 AI Analysis:</strong>
                        <div className="ai-details">
                          <div>Risk: <span className={`risk-${currentCommitTask.task.gemini_analysis.risk_assessment}`}>
                            {currentCommitTask.task.gemini_analysis.risk_assessment?.toUpperCase()}
                          </span></div>
                          <div>Confidence: {((currentCommitTask.task.gemini_analysis.confidence || 0) * 100).toFixed(0)}%</div>
                        </div>
                      </div>
                    )}

                    <div className="commit-message-preview">
                      <strong>💬 What was done:</strong>
                      <p>{currentCommitTask.task.transcript}</p>
                    </div>
                  </>
                ) : currentCommitTask.task.commit_info?.commit_hash ? (
                  /* Legacy mode: Show local commit info */
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
                  {currentCommitTask.task.pending_github_push ? (
                    <>
                      <div className="action-explanation">
                        <strong>✅ Approve & Push:</strong> Push changes to TODO-UI production repository on GitHub
                      </div>
                      <div className="action-explanation">
                        <strong>❌ Cancel:</strong> Discard changes and don't push to GitHub
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="action-explanation">
                        <strong>✅ Approve:</strong> Keep the changes permanently (no rollback possible)
                      </div>
                      <div className="action-explanation">
                        <strong>🔄 Soft Rollback:</strong> Undo the commit but keep changes as unstaged files
                      </div>
                      <div className="action-explanation">
                        <strong>🗑️ Hard Rollback:</strong> Only discard the specific files that were changed (safer)
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            <div className="modal-footer">
              {currentCommitTask.task.pending_github_push && currentCommitTask.task.github_ready ? (
                /* Production mode: Only show Approve and Cancel */
                <>
                  <button
                    onClick={() => { setShowCommitModal(false); setCurrentCommitTask(null); }}
                    className="cancel-btn modal-btn"
                  >
                    ❌ Cancel
                  </button>

                  <button
                    onClick={() => approveCommit(currentCommitTask.taskId)}
                    disabled={commitActions[currentCommitTask.taskId]}
                    className="approve-btn modal-btn primary"
                  >
                    {commitActions[currentCommitTask.taskId] ? '⏳ Pushing to GitHub...' : '✅ Approve & Push to GitHub'}
                  </button>
                </>
              ) : currentCommitTask.task.commit_info?.commit_hash ? (
                /* Legacy mode: Show all rollback options */
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