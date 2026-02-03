import React, { useState, useEffect, useCallback, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid'; // For generating temporary IDs
import './App.css'; // Import the CSS styles
import RefreshButton from './components/RefreshButton'; // NEW: Import the RefreshButton component
import TodoFormModal from './components/TodoFormModal'; // NEW: Import the TodoFormModal component

// --- Types ---
type Filter = 'all' | 'completed' | 'active';
type Priority = 'low' | 'medium' | 'high';
type Status = 'pending' | 'in-progress' | 'completed';
type ToastType = 'success' | 'error';

interface Todo {
  id: string;
  title: string;
  description: string;
  priority: Priority;
  status: Status;
  createdAt: string;
  updatedAt: string;
}

// NEW: Interface for data handled by the form modal
interface TodoFormData {
  title: string;
  description: string;
  priority: Priority;
}

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

// --- Mock API (Simulates network requests) ---
const mockApi = {
  // Simulate network delay
  delay: (ms: number) => new Promise(res => setTimeout(res, ms)),

  // Simulate potential network failures
  shouldFail: (probability = 0.15) => Math.random() < probability,

  async fetchTodos(): Promise<Todo[]> {
    await this.delay(500 + Math.random() * 500); // 0.5s to 1s delay
    if (this.shouldFail(0.1)) { // 10% chance to fail on fetch
      throw new Error('Failed to fetch todos. Please try again.');
    }
    const storedTodos = localStorage.getItem('todos');
    if (storedTodos) {
      return JSON.parse(storedTodos).sort((a: Todo, b: Todo) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
    }
    return [];
  },

  async addTodo(todo: Omit<Todo, 'id' | 'createdAt' | 'updatedAt'>): Promise<Todo> {
    await this.delay(700 + Math.random() * 800); // 0.7s to 1.5s delay
    if (this.shouldFail()) {
      throw new Error('Failed to add todo. Server error.');
    }
    const newTodo: Todo = {
      ...todo,
      id: uuidv4(),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    const todos = JSON.parse(localStorage.getItem('todos') || '[]');
    todos.push(newTodo);
    localStorage.setItem('todos', JSON.stringify(todos));
    return newTodo;
  },

  async updateTodo(id: string, updates: Partial<Todo>): Promise<Todo> {
    await this.delay(400 + Math.random() * 600); // 0.4s to 1s delay
    if (this.shouldFail()) {
      throw new Error(`Failed to update todo '${id}'. Network issues.`);
    }
    let todos = JSON.parse(localStorage.getItem('todos') || '[]');
    let updatedTodo: Todo | undefined;
    todos = todos.map((todo: Todo) => {
      if (todo.id === id) {
        updatedTodo = { ...todo, ...updates, updatedAt: new Date().toISOString() };
        return updatedTodo;
      }
      return todo;
    });
    if (!updatedTodo) {
      throw new Error(`Todo with ID '${id}' not found.`);
    }
    localStorage.setItem('todos', JSON.stringify(todos));
    return updatedTodo;
  },

  async deleteTodo(id: string): Promise<void> {
    await this.delay(300 + Math.random() * 700); // 0.3s to 1s delay
    if (this.shouldFail()) {
      throw new Error(`Failed to delete todo '${id}'. Please try again.`);
    }
    let todos = JSON.parse(localStorage.getItem('todos') || '[]');
    const initialLength = todos.length;
    todos = todos.filter((todo: Todo) => todo.id !== id);
    if (todos.length === initialLength) {
      throw new Error(`Todo with ID '${id}' not found for deletion.`);
    }
    localStorage.setItem('todos', JSON.stringify(todos));
  },
};

// --- Custom Hooks ---

// Hook for setting interval that intelligently handles changes
function useInterval(callback: () => void, delay: number | null) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    function tick() {
      savedCallback.current();
    }
    if (delay !== null) {
      const id = setInterval(tick, delay);
      return () => clearInterval(id);
    }
  }, [delay]);
}

// --- Components ---

// Simple Spinner Component (moved here as it's used by App and potentially child components)
const Spinner: React.FC<{ size?: string; color?: string }> = ({ size = '1em', color = 'var(--button-text-primary)' }) => (
  <span className="spinner" style={{ width: size, height: size, borderColor: `rgba(255, 255, 255, 0.3) ${color} rgba(255, 255, 255, 0.3) ${color}` }} role="status" aria-label="Loading"></span>
);

// Toast Notification Component
const ToastNotification: React.FC<{ toast: Toast; onClose: (id: string) => void }> = ({ toast, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(() => onClose(toast.id), 5000); // Auto-close after 5 seconds
    return () => clearTimeout(timer);
  }, [toast.id, onClose]);

  return (
    <div className={`toast ${toast.type}`} role="alert">
      <p className="toast-message">{toast.message}</p>
      <button className="toast-close-btn" onClick={() => onClose(toast.id)} aria-label={`Close ${toast.type} notification`}>
        &times;
      </button>
    </div>
  );
};

// Toast Container Component
const ToastContainer: React.FC<{ toasts: Toast[]; removeToast: (id: string) => void }> = ({ toasts, removeToast }) => {
  return (
    <div className="toast-container" aria-live="polite" aria-atomic="true">
      {toasts.map((toast) => (
        <ToastNotification key={toast.id} toast={toast} onClose={removeToast} />
      ))}
    </div>
  );
};

// TodoCard Component (extracted for better modularity and individual busy states)
interface TodoCardProps {
  todo: Todo;
  isBusy: boolean; // Indicates if this specific todo is undergoing a CRUD operation
  toggleTodoStatus: (id: string, newStatus: Status) => Promise<void>;
  deleteTodo: (id: string) => Promise<void>;
  onEdit: (todo: Todo) => void; // NEW: Callback to trigger edit mode for this todo
}

const TodoCard: React.FC<TodoCardProps> = ({ todo, isBusy, toggleTodoStatus, deleteTodo, onEdit }) => {
  // Modified to return CSS variable names instead of hardcoded hex codes
  const getPriorityColorVar = (priority: Priority) => {
    switch (priority) {
      case 'high': return 'var(--priority-high-bg)';
      case 'medium': return 'var(--priority-medium-bg)';
      case 'low': return 'var(--priority-low-bg)';
      default: return 'var(--priority-medium-bg)'; // Fallback to medium
    }
  };

  // Modified to return CSS variable names instead of hardcoded hex codes
  const getStatusColorVar = (status: Status) => {
    switch (status) {
      case 'completed': return 'var(--status-completed-bg)';
      case 'in-progress': return 'var(--status-in-progress-bg)';
      case 'pending': return 'var(--status-pending-bg)';
      default: return 'var(--status-pending-bg)'; // Fallback to pending
    }
  };

  return (
    <div className={`todo-card ${isBusy ? 'busy' : ''}`} aria-busy={isBusy ? 'true' : 'false'}>
      <div className="todo-header">
        <h3>{todo.title}</h3>
        <div className="todo-badges">
          {/* Apply CSS variable using inline style for background, text color is handled by CSS class */}
          <span className="status-badge" style={{ backgroundColor: getStatusColorVar(todo.status) }}>
            {todo.status}
          </span>
          {/* Apply CSS variable using inline style for background, text color is handled by CSS class */}
          <span className="priority-badge" style={{ backgroundColor: getPriorityColorVar(todo.priority) }}>
            {todo.priority}
          </span>
        </div>
      </div>
      <p className="todo-description">{todo.description}</p>
      {/* NEW: Added timestamps for enhanced display, contributing to a "cool" and informative look */}
      <div className="todo-timestamps">
        <span className="timestamp-created">Created: {new Date(todo.createdAt).toLocaleString()}</span>
        <span className="timestamp-updated">Updated: {new Date(todo.updatedAt).toLocaleString()}</span>
      </div>
      <div className="todo-actions">
        <div className="status-controls">
          <label htmlFor={`status-${todo.id}`}>Status:</label>
          <select
            id={`status-${todo.id}`}
            value={todo.status}
            onChange={(e) => toggleTodoStatus(todo.id, e.target.value as Status)}
            disabled={isBusy}
            aria-label={`Change status for todo "${todo.title}"`}
          >
            <option value="pending">Pending</option>
            <option value="in-progress">In Progress</option>
            <option value="completed">Completed</option>
          </select>
        </div>
        <div className="todo-action-buttons"> {/* Group buttons for better layout */}
          <button
            className="edit-btn"
            onClick={() => onEdit(todo)}
            disabled={isBusy}
            aria-label={`Edit todo "${todo.title}"`}
          >
            {isBusy ? (
              <Spinner size="1em" />
            ) : (
              // Pencil icon SVG
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="1.2em" height="1.2em" style={{ verticalAlign: 'middle' }} aria-hidden="true">
                <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
              </svg>
            )}
          </button>
          <button
            className="delete-btn"
            onClick={() => deleteTodo(todo.id)}
            disabled={isBusy}
            aria-label={`Delete todo "${todo.title}"`}
          >
            {isBusy ? (
              <Spinner size="1em" />
            ) : (
              // Trash icon SVG, replacing the 'Delete' text
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="1.2em" height="1.2em" style={{ verticalAlign: 'middle' }} aria-hidden="true">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};


// --- Main App Component ---
function App() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  
  // Replaced `isModalOpen` and `newTodoInput` with `isFormModalOpen` and `editingTodo`
  const [isFormModalOpen, setIsFormModalOpen] = useState(false); // Controls the TodoFormModal
  const [editingTodo, setEditingTodo] = useState<Todo | null>(null); // Null for add, Todo object for edit

  const [isLoadingTodos, setIsLoadingTodos] = useState(true); // For initial fetch and manual refresh
  const [isPolling, setIsPolling] = useState(false); // For background polling
  const [todoLoadingStates, setTodoLoadingStates] = useState<Record<string, boolean>>({}); // For individual todo CRUD operations
  const [isAddingTodo, setIsAddingTodo] = useState(false); // Specifically for tracking if an 'add' operation is ongoing
  const [globalError, setGlobalError] = useState<string | null>(null); // For persistent errors
  const [toasts, setToasts] = useState<Toast[]>([]); // For transient success/error messages

  // Tracks active optimistic CRUD operations to pause polling
  const activeCrudOperations = useRef(new Set<string>());

  // --- Toast Management ---
  const addToast = useCallback((message: string, type: ToastType) => {
    const id = uuidv4();
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  // --- CRUD Operation Wrapper for consistent loading/error handling ---
  const handleCrudOperation = useCallback(async (
    operationId: string, // Unique ID for the operation, e.g., todo.id or 'add_new'
    apiCall: () => Promise<any>,
    optimisticUpdate: () => void,
    onSuccess: (result: any) => void,
    onFailure: (error: Error) => void,
  ) => {
    activeCrudOperations.current.add(operationId); // Mark operation as active

    // Set individual todo busy state, or global adding state for new todos
    if (operationId.startsWith('optimistic-')) { // Convention for new todo adds
      setIsAddingTodo(true);
    } else {
      setTodoLoadingStates(prev => ({ ...prev, [operationId]: true }));
    }

    try {
      optimisticUpdate();
      const result = await apiCall();
      onSuccess(result);
    } catch (error: any) {
      console.error(`CRUD operation (${operationId}) failed:`, error);
      onFailure(error);
      addToast(error.message || 'An unexpected error occurred.', 'error');
    } finally {
      // Clear individual todo busy state, or global adding state
      if (operationId.startsWith('optimistic-')) {
        setIsAddingTodo(false);
      } else {
        setTodoLoadingStates(prev => ({ ...prev, [operationId]: false }));
      }
      activeCrudOperations.current.delete(operationId); // Mark operation as complete
      // Check if no active operations left to potentially resume polling
      if (activeCrudOperations.current.size === 0 && !isPolling) {
        // Optionally trigger a silent fetch here to ensure data consistency
        // or just rely on the next poll interval. For now, we rely on the next poll.
        console.log("All CRUD operations complete. Polling can resume.");
      }
    }
  }, [addToast, isPolling]);

  // --- Data Fetching ---
  const fetchTodos = useCallback(async (isInitialFetch = false) => {
    if (isInitialFetch) {
      setIsLoadingTodos(true);
      setGlobalError(null);
    } else {
      setIsPolling(true);
    }

    // Crucial: If there are active CRUD operations, we skip updating the main todos state
    // to prevent overwriting optimistic local changes.
    if (activeCrudOperations.current.size > 0 && !isInitialFetch) {
      console.warn("Skipping poll update due to active CRUD operations.");
      setIsPolling(false);
      return;
    }

    try {
      const fetchedTodos = await mockApi.fetchTodos();
      // Only update if no active CRUD operations are present at the moment of update
      // This is a double-check in case an operation started *during* the fetch
      if (activeCrudOperations.current.size === 0 || isInitialFetch) {
        setTodos(fetchedTodos);
        setGlobalError(null);
      } else {
        console.warn("CRUD operation started during fetch, skipping state update to prevent overwrite.");
      }
    } catch (error: any) {
      console.error('Failed to fetch todos:', error);
      if (isInitialFetch) {
        setGlobalError(error.message || 'Failed to load todos.');
      } else {
        addToast(error.message || 'Background refresh failed.', 'error');
      }
    } finally {
      if (isInitialFetch) {
        setIsLoadingTodos(false);
      } else {
        setIsPolling(false);
      }
    }
  }, [addToast]);

  useEffect(() => {
    fetchTodos(true); // Initial fetch on component mount
  }, [fetchTodos]);

  // Polling for todos every 10 seconds
  useInterval(
    () => {
      // Only poll if no CRUD operations are active
      if (activeCrudOperations.current.size === 0) {
        fetchTodos();
      } else {
        console.log("Polling paused: Active CRUD operations detected.");
      }
    },
    activeCrudOperations.current.size === 0 ? 10000 : null // Pause interval if active CRUD ops
  );

  // --- Todo Form Modal Management (Add/Edit) ---

  const handleFormModalClose = useCallback(() => {
    setIsFormModalOpen(false);
    setEditingTodo(null); // Clear editing state when modal closes
  }, []);

  const handleAddTodoClick = useCallback(() => {
    setEditingTodo(null); // Ensure add mode
    setIsFormModalOpen(true);
  }, []);

  const handleEditTodoStart = useCallback((todo: Todo) => {
    setEditingTodo(todo); // Set todo for editing
    setIsFormModalOpen(true);
  }, []);

  const handleUpdateTodo = useCallback(async (id: string, updates: Partial<Todo>) => {
    await handleCrudOperation(
      id, // Use todo ID for tracking the operation
      () => mockApi.updateTodo(id, updates),
      () => {
        // Optimistic update
        setTodos((prevTodos) =>
          prevTodos.map((todo) =>
            todo.id === id
              ? { ...todo, ...updates, updatedAt: new Date().toISOString() }
              : todo
          )
        );
      },
      () => {
        addToast('Todo updated successfully!', 'success');
        handleFormModalClose(); // Close modal on success
      },
      (error) => {
        // Revert is implicitly handled if the next poll refreshes or if needed,
        // the `handleCrudOperation`'s `onFailure` could revert the optimistic state.
        // For partial updates, it's often simpler to let the next server fetch reconcile.
        // However, if strict rollback is needed, the `originalTodo` would need to be passed
        // or retrieved again.
      }
    );
  }, [addToast, handleCrudOperation, handleFormModalClose]);


  const handleFormSubmit = useCallback(async (formData: TodoFormData) => {
    if (editingTodo) {
      // Edit mode
      const updatedFields: Partial<Todo> = {
        title: formData.title,
        description: formData.description,
        priority: formData.priority,
      };
      await handleUpdateTodo(editingTodo.id, updatedFields);
    } else {
      // Add mode
      if (!formData.title.trim()) {
        addToast('Title cannot be empty.', 'error');
        return;
      }

      const tempId = `optimistic-${uuidv4()}`; // Temporary ID for optimistic UI
      const optimisticTodo: Todo = { ...formData, id: tempId, status: 'pending', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() };

      await handleCrudOperation(
        tempId, // Use tempId for tracking the operation
        () => mockApi.addTodo({ ...formData, status: 'pending' }),
        () => {
          // Optimistic update
          setTodos((prevTodos) => [optimisticTodo, ...prevTodos]);
        },
        (newTodo) => {
          // On success, replace the optimistic todo with the real one
          setTodos((prevTodos) =>
            prevTodos.map((t) => (t.id === tempId ? newTodo : t))
          );
          addToast('Todo added successfully!', 'success');
          handleFormModalClose(); // Close modal on success
        },
        () => {
          // On failure, revert optimistic update
          setTodos((prevTodos) => prevTodos.filter((t) => t.id !== tempId));
        }
      );
    }
  }, [editingTodo, addToast, handleCrudOperation, handleUpdateTodo, handleFormModalClose]);

  // --- Todo Status Toggle and Delete Operations ---

  const toggleTodoStatus = useCallback(async (id: string, newStatus: Status) => {
    const originalTodo = todos.find((t) => t.id === id);
    if (!originalTodo) return;

    await handleCrudOperation(
      id, // Use todo ID for tracking the operation
      () => mockApi.updateTodo(id, { status: newStatus }),
      () => {
        // Optimistic update
        setTodos((prevTodos) =>
          prevTodos.map((todo) =>
            todo.id === id
              ? { ...todo, status: newStatus, updatedAt: new Date().toISOString() }
              : todo
          )
        );
      },
      () => {
        // On success, state is already updated optimistically, no further action needed
        // The poll will eventually reconcile if needed, but optimistic update is sufficient.
        addToast('Todo status updated!', 'success');
      },
      () => {
        // On failure, revert to original status
        setTodos((prevTodos) =>
          prevTodos.map((todo) =>
            todo.id === id && originalTodo
              ? { ...todo, status: originalTodo.status, updatedAt: originalTodo.updatedAt }
              : todo
          )
        );
      }
    );
  }, [todos, addToast, handleCrudOperation]);

  const deleteTodo = useCallback(async (id: string) => {
    const originalTodo = todos.find((t) => t.id === id);
    if (!originalTodo) return;

    await handleCrudOperation(
      id, // Use todo ID for tracking the operation
      () => mockApi.deleteTodo(id),
      () => {
        // Optimistic update
        setTodos((prevTodos) => prevTodos.filter((t) => t.id !== id));
      },
      () => {
        // On success, state is already updated optimistically
        addToast('Todo deleted successfully!', 'success');
      },
      () => {
        // On failure, re-add the todo
        setTodos((prevTodos) => {
          const newTodos = [originalTodo, ...prevTodos]; // Re-add to the start
          return newTodos.sort((a: Todo, b: Todo) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()); // Maintain order
        });
      }
    );
  }, [todos, addToast, handleCrudOperation]);

  // --- Filtering Logic ---
  const filteredTodos = todos.filter((todo) => {
    if (filter === 'all') return true;
    if (filter === 'active') return todo.status !== 'completed';
    if (filter === 'completed') return todo.status === 'completed';
    return true;
  });

  const completedCount = todos.filter((todo) => todo.status === 'completed').length;
  const activeCount = todos.filter((todo) => todo.status !== 'completed').length;

  const totalTodosCount = todos.length;

  // Determine if the form modal is currently saving (either adding or updating an existing todo)
  const isFormSaving = isAddingTodo || (editingTodo ? !!todoLoadingStates[editingTodo.id] : false);

  return (
    <div className="app">
      <ToastContainer toasts={toasts} removeToast={removeToast} />

      <header className="header">
        <div className="header-content">
          <h1>My Todo List</h1>
          <p>Stay organized and productive.</p>
        </div>
        <div className="header-actions">
          {isPolling && (
            <div className="polling-status" role="status" aria-label="Refreshing data">
              <Spinner size="1em" color="var(--text-color-secondary)" /> Refreshing...
            </div>
          )}
          <RefreshButton
            onClick={() => fetchTodos(true)}
            disabled={isLoadingTodos || activeCrudOperations.current.size > 0}
            isLoading={isLoadingTodos}
            ariaLabel={isLoadingTodos ? "Loading todos" : (activeCrudOperations.current.size > 0 ? "Operations pending, cannot refresh" : "Refresh todos")}
          />
        </div>
      </header>

      {globalError && (
        <div className="error-banner" role="alert">
          <p>{globalError}</p>
          <button onClick={() => setGlobalError(null)} aria-label="Dismiss error message">Dismiss</button>
        </div>
      )}

      <section className="stats">
        <div className="stat-card">
          <h3>{totalTodosCount}</h3>
          <p>Total Todos</p>
        </div>
        <div className="stat-card">
          <h3>{activeCount}</h3>
          <p>Active Todos</p>
        </div>
        <div className="stat-card">
          <h3>{completedCount}</h3>
          <p>Completed Todos</p>
        </div>
      </section>

      <section className="controls">
        <div className="filters" role="group" aria-label="Filter todos">
          <button
            onClick={() => setFilter('all')}
            className={filter === 'all' ? 'active' : ''}
            aria-pressed={filter === 'all'}
          >
            All
          </button>
          <button
            onClick={() => setFilter('active')}
            className={filter === 'active' ? 'active' : ''}
            aria-pressed={filter === 'active'}
          >
            Active
          </button>
          <button
            onClick={() => setFilter('completed')}
            className={filter === 'completed' ? 'active' : ''}
            aria-pressed={filter === 'completed'}
          >
            Completed
          </button>
        </div>
        <button
          className="add-todo-btn"
          onClick={handleAddTodoClick} // Use new handler
          disabled={isFormSaving} // Disable if any form operation is saving
          aria-label="Add new todo"
          style={{ backgroundColor: 'purple' }}
        >
          <span aria-hidden="true">+</span> Add New Todo
        </button>
      </section>

      <main className="todos-container">
        {isLoadingTodos ? (
          <div className="loading" role="status" aria-live="polite">
            <h3>Loading Todos...</h3>
            <p>Please wait while we fetch your tasks.</p>
          </div>
        ) : filteredTodos.length === 0 ? (
          <div className="no-todos" role="note" aria-live="polite">
            <h3>No Todos Found</h3>
            <p>It looks like you don't have any todos in the '{filter}' category. Why not add one?</p>
            {filter !== 'all' && (
              <button className="admin-link" onClick={() => setFilter('all')} aria-label="View all todos">
                View All Todos
              </button>
            )}
          </div>
        ) : (
          filteredTodos.map((todo) => (
            <TodoCard
              key={todo.id}
              todo={todo}
              isBusy={!!todoLoadingStates[todo.id]}
              toggleTodoStatus={toggleTodoStatus}
              deleteTodo={deleteTodo}
              onEdit={handleEditTodoStart} // Pass the edit handler
            />
          ))
        )}
      </main>

      {/* NEW: Use TodoFormModal component for both Add and Edit */}
      <TodoFormModal
        isOpen={isFormModalOpen}
        onClose={handleFormModalClose}
        initialData={editingTodo} // Pass the todo to edit, or null for add
        onSubmit={handleFormSubmit}
        isSaving={isFormSaving}
        Spinner={Spinner} // Pass the Spinner component
      />

      <footer className="footer">
        <p>&copy; {new Date().getFullYear()} Todo App. All rights reserved.</p>
        <p>
          Built with <a href="https://react.dev/" target="_blank" rel="noopener noreferrer">React</a> and lots of coffee.
        </p>
      </footer>
    </div>
  );
}

export default App;