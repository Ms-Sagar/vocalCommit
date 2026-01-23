import React, { useState, useEffect } from 'react'
import './App.css'

interface TodoItem {
  id: string
  title: string
  description: string
  status: 'pending' | 'in-progress' | 'completed'
  priority: 'low' | 'medium' | 'high'
  createdAt: string
  updatedAt: string
  files?: string[]
  dependencies?: string[]
  code_files?: { [key: string]: string }
  implementation_notes?: string[]
}

function App() {
  const [todos, setTodos] = useState<TodoItem[]>([])
  const [filter, setFilter] = useState<'all' | 'pending' | 'in-progress' | 'completed'>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [generatingFiles, setGeneratingFiles] = useState<string | null>(null)
  const [showAddTodo, setShowAddTodo] = useState(false)
  const [newTodo, setNewTodo] = useState({
    title: '',
    description: '',
    priority: 'medium' as 'low' | 'medium' | 'high'
  })

  // Fetch manual todos only (not admin workflows)
  useEffect(() => {
    fetchTodos()
    // Set up polling to refresh data every 10 seconds
    const interval = setInterval(fetchTodos, 10000)
    return () => clearInterval(interval)
  }, [])

  const fetchTodos = async () => {
    try {
      const response = await fetch('http://localhost:8000/tasks')
      if (!response.ok) {
        throw new Error('Failed to fetch todos')
      }
      const data = await response.json()
      setTodos(data.tasks || [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch todos')
      console.error('Error fetching todos:', err)
    } finally {
      setLoading(false)
    }
  }

  const addTodo = async () => {
    if (!newTodo.title.trim()) return

    try {
      const response = await fetch('http://localhost:8000/todos', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: newTodo.title,
          description: newTodo.description,
          priority: newTodo.priority,
          status: 'pending'
        })
      })

      if (response.ok) {
        setNewTodo({ title: '', description: '', priority: 'medium' })
        setShowAddTodo(false)
        fetchTodos() // Refresh the list
      } else {
        alert('Failed to add todo')
      }
    } catch (err) {
      alert('Error adding todo')
    }
  }

  const updateTodoStatus = async (todoId: string, newStatus: 'pending' | 'in-progress' | 'completed') => {
    try {
      const response = await fetch(`http://localhost:8000/todos/${todoId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: newStatus })
      })

      if (response.ok) {
        fetchTodos() // Refresh the list
      } else {
        alert('Failed to update todo status')
      }
    } catch (err) {
      alert('Error updating todo status')
    }
  }

  const deleteTodo = async (todoId: string) => {
    if (!confirm('Are you sure you want to delete this todo?')) return

    try {
      const response = await fetch(`http://localhost:8000/todos/${todoId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        fetchTodos() // Refresh the list
      } else {
        alert('Failed to delete todo')
      }
    } catch (err) {
      alert('Error deleting todo')
    }
  }

  const generateFiles = async (taskId: string) => {
    setGeneratingFiles(taskId)
    try {
      const response = await fetch(`http://localhost:8000/generate-files/${taskId}`, {
        method: 'POST'
      })
      const result = await response.json()
      
      if (result.status === 'success') {
        alert(`✅ Files generated successfully!\n\n${result.message}\n\nGenerated ${result.generated_files.length} files`)
      } else {
        alert(`❌ Error: ${result.error}`)
      }
    } catch (err) {
      alert(`❌ Error generating files: ${err}`)
    } finally {
      setGeneratingFiles(null)
    }
  }

  const filteredTodos = todos.filter(todo => 
    filter === 'all' ? true : todo.status === filter
  )

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#28a745'
      case 'in-progress': return '#ffc107'
      case 'pending': return '#6c757d'
      default: return '#6c757d'
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#dc3545'
      case 'medium': return '#fd7e14'
      case 'low': return '#20c997'
      default: return '#6c757d'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <div className="app">
      <header className="header">
        <h1>🎯 VocalCommit Todo</h1>
        <p>Manual todos separate from admin voice commands</p>
        <button onClick={fetchTasks} className="refresh-btn" disabled={loading}>
          {loading ? '🔄 Loading...' : '🔄 Refresh'}
        </button>
      </header>

      {error && (
        <div className="error-banner">
          <p>❌ {error}</p>
          <button onClick={fetchTasks}>Retry</button>
        </div>
      )}

      <div className="stats">
        <div className="stat-card">
          <h3>{todos.filter(t => t.status === 'completed').length}</h3>
          <p>Completed</p>
        </div>
        <div className="stat-card">
          <h3>{todos.filter(t => t.status === 'in-progress').length}</h3>
          <p>In Progress</p>
        </div>
        <div className="stat-card">
          <h3>{todos.filter(t => t.status === 'pending').length}</h3>
          <p>Pending</p>
        </div>
        <div className="stat-card">
          <h3>{todos.length}</h3>
          <p>Total Tasks</p>
        </div>
      </div>

      <div className="controls">
        <div className="filters">
          <button 
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All Tasks
          </button>
          <button 
            className={filter === 'pending' ? 'active' : ''}
            onClick={() => setFilter('pending')}
          >
            Pending
          </button>
          <button 
            className={filter === 'in-progress' ? 'active' : ''}
            onClick={() => setFilter('in-progress')}
          >
            In Progress
          </button>
          <button 
            className={filter === 'completed' ? 'active' : ''}
            onClick={() => setFilter('completed')}
          >
            Completed
          </button>
        </div>
        
        <button 
          className="add-todo-btn"
          onClick={() => setShowAddTodo(true)}
        >
          ➕ Add Manual Todo
        </button>
      </div>

      {/* Add Todo Modal */}
      {showAddTodo && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>➕ Add Manual Todo</h3>
              <button 
                className="close-btn"
                onClick={() => setShowAddTodo(false)}
              >
                ✕
              </button>
            </div>
            
            <div className="modal-body">
              <div className="form-group">
                <label>Title *</label>
                <input
                  type="text"
                  value={newTodo.title}
                  onChange={(e) => setNewTodo({...newTodo, title: e.target.value})}
                  placeholder="Enter todo title..."
                />
              </div>
              
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={newTodo.description}
                  onChange={(e) => setNewTodo({...newTodo, description: e.target.value})}
                  placeholder="Enter todo description..."
                  rows={3}
                />
              </div>
              
              <div className="form-group">
                <label>Priority</label>
                <select
                  value={newTodo.priority}
                  onChange={(e) => setNewTodo({...newTodo, priority: e.target.value as 'low' | 'medium' | 'high'})}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
            </div>
            
            <div className="modal-footer">
              <button 
                className="cancel-btn"
                onClick={() => setShowAddTodo(false)}
              >
                Cancel
              </button>
              <button 
                className="add-btn"
                onClick={addTodo}
                disabled={!newTodo.title.trim()}
              >
                Add Todo
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="filters">
        <button 
          className={filter === 'all' ? 'active' : ''}
          onClick={() => setFilter('all')}
        >
          All Tasks
        </button>
        <button 
          className={filter === 'pending' ? 'active' : ''}
          onClick={() => setFilter('pending')}
        >
          Pending
        </button>
        <button 
          className={filter === 'in-progress' ? 'active' : ''}
          onClick={() => setFilter('in-progress')}
        >
          In Progress
        </button>
        <button 
          className={filter === 'completed' ? 'active' : ''}
          onClick={() => setFilter('completed')}
        >
          Completed
        </button>
      </div>

      <div className="todos-container">
        {loading && todos.length === 0 ? (
          <div className="loading">
            <h3>🔄 Loading todos...</h3>
            <p>Manual todos are separate from admin voice commands</p>
          </div>
        ) : filteredTodos.length === 0 ? (
          <div className="no-todos">
            <h3>No manual todos found</h3>
            <p>Click "Add Manual Todo" to create your first todo</p>
            <p>Voice commands from admin create separate workflows</p>
            <a href="http://localhost:5173" target="_blank" className="admin-link">
              🎤 Open Admin Interface for Voice Commands
            </a>
          </div>
        ) : (
          filteredTodos.map(todo => (
            <div key={todo.id} className="todo-card">
              <div className="todo-header">
                <h3>{todo.title}</h3>
                <div className="todo-badges">
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(todo.status) }}
                  >
                    {todo.status.replace('-', ' ')}
                  </span>
                  <span 
                    className="priority-badge"
                    style={{ backgroundColor: getPriorityColor(todo.priority) }}
                  >
                    {todo.priority}
                  </span>
                </div>
              </div>
              
              <p className="todo-description">{todo.description}</p>
              
              <div className="todo-actions">
                <div className="status-controls">
                  <label>Status:</label>
                  <select
                    value={todo.status}
                    onChange={(e) => updateTodoStatus(todo.id, e.target.value as 'pending' | 'in-progress' | 'completed')}
                  >
                    <option value="pending">Pending</option>
                    <option value="in-progress">In Progress</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
                
                <button 
                  className="delete-btn"
                  onClick={() => deleteTodo(todo.id)}
                >
                  🗑️ Delete
                </button>
              </div>
              
              {todo.files && todo.files.length > 0 && (
                <div className="todo-files">
                  <h4>📁 Generated Files:</h4>
                  <div className="file-list">
                    {todo.files.map(file => (
                      <span key={file} className="file-tag">{file}</span>
                    ))}
                  </div>
                </div>
              )}
              
              {todo.dependencies && todo.dependencies.length > 0 && (
                <div className="todo-dependencies">
                  <h4>📦 Dependencies:</h4>
                  <div className="dependency-list">
                    {todo.dependencies.map(dep => (
                      <span key={dep} className="dependency-tag">{dep}</span>
                    ))}
                  </div>
                </div>
              )}

              {todo.implementation_notes && todo.implementation_notes.length > 0 && (
                <div className="todo-notes">
                  <h4>📝 Implementation Notes:</h4>
                  <ul>
                    {todo.implementation_notes.map((note, index) => (
                      <li key={index}>{note}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div className="todo-actions">
                {todo.status === 'completed' && todo.code_files && (
                  <button 
                    className="generate-files-btn"
                    onClick={() => generateFiles(todo.id)}
                    disabled={generatingFiles === todo.id}
                  >
                    {generatingFiles === todo.id ? '⏳ Generating...' : '📁 Generate Files'}
                  </button>
                )}
              </div>
              
              <div className="todo-footer">
                <small>Created: {formatDate(todo.createdAt)}</small>
                <small>Updated: {formatDate(todo.updatedAt)}</small>
                <small>ID: {todo.id}</small>
              </div>
            </div>
          ))
        )}
      </div>

      <footer className="footer">
        <p>
          🎤 Admin Interface: <a href="http://localhost:5173" target="_blank">localhost:5173</a>
        </p>
        <p>
          📊 API Health: <a href="http://localhost:8000/health" target="_blank">localhost:8000/health</a>
        </p>
        <p>
          🔄 Auto-refresh: Every 5 seconds
        </p>
      </footer>
    </div>
  )
}

export default App