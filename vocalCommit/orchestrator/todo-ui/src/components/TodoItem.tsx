import React from 'react';

// --- Types (Ensures component self-sufficiency for type definitions) ---
type Priority = 'low' | 'medium' | 'high';
type Status = 'pending' | 'in-progress' | 'completed';

interface Todo {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  dueDate: string; // ISO string (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:mm:ss.sssZ')
  priority: Priority;
  status: Status;
  createdAt: string;
  updatedAt: string;
}

interface TodoItemProps {
  todo: Todo;
  onToggleComplete: (id: string) => void;
  onDelete: (id: string) => void;
  onEdit: (id: string) => void;
  onUpdateStatus: (id: string, newStatus: Status) => void;
  onUpdatePriority: (id: string, newPriority: Priority) => void;
}

const TodoItem: React.FC<TodoItemProps> = ({
  todo,
  onToggleComplete,
  onDelete,
  onEdit,
  onUpdateStatus,
  onUpdatePriority,
}) => {
  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onUpdateStatus(todo.id, e.target.value as Status);
  };

  const handlePriorityChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onUpdatePriority(todo.id, e.target.value as Priority);
  };

  /**
   * Returns a CSS class name based on the priority level.
   * Assumes corresponding styles are defined in App.css.
   * @param priority The priority of the todo item.
   * @returns CSS class string.
   */
  const getPriorityClass = (priority: Priority) => {
    switch (priority) {
      case 'high': return 'priority-high';
      case 'medium': return 'priority-medium';
      case 'low': return 'priority-low';
      default: return ''; // Fallback for unexpected priority
    }
  };

  /**
   * Returns a CSS class name based on the status level.
   * Assumes corresponding styles are defined in App.css.
   * @param status The status of the todo item.
   * @returns CSS class string.
   */
  const getStatusClass = (status: Status) => {
    switch (status) {
      case 'completed': return 'status-completed';
      case 'in-progress': return 'status-in-progress';
      case 'pending': return 'status-pending';
      default: return ''; // Fallback for unexpected status
    }
  };

  /**
   * Formats an ISO date string into a more readable format.
   * Handles potential invalid date strings gracefully.
   * @param dateString The date string to format.
   * @returns Formatted date string or 'N/A' if invalid.
   */
  const formatDate = (dateString: string) => {
    if (!dateString) {
      return 'No Due Date';
    }
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return 'Invalid Date'; // Handle date strings that Date object can't parse
      }
      return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      }).format(date);
    } catch (error) {
      console.error("Error formatting date:", error);
      return 'N/A'; // Fallback for any unexpected errors during formatting
    }
  };

  return (
    <div className={`todo-item ${todo.completed ? 'todo-item-completed' : ''}`} data-id={todo.id}>
      <div className="todo-item-main-details">
        <input
          type="checkbox"
          checked={todo.completed}
          onChange={() => onToggleComplete(todo.id)}
          aria-label={`Mark "${todo.title}" as ${todo.completed ? 'not completed' : 'completed'}`}
          className="todo-item-checkbox"
          id={`checkbox-${todo.id}`}
        />
        <label htmlFor={`checkbox-${todo.id}`} className="visually-hidden">
          Toggle completion for {todo.title}
        </label>
        <span
          className={`todo-item-title ${todo.completed ? 'text-strike-through' : ''}`}
          title={todo.description} // Show description on hover
        >
          {todo.title}
        </span>
      </div>

      <div className="todo-item-meta-details">
        {/* Priority Selector */}
        <div className="todo-item-detail-group">
          <label htmlFor={`priority-${todo.id}`} className="visually-hidden">Priority</label>
          <select
            id={`priority-${todo.id}`}
            value={todo.priority}
            onChange={handlePriorityChange}
            className={`todo-item-priority-select ${getPriorityClass(todo.priority)}`}
            aria-label={`Change priority for ${todo.title}`}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>

        {/* Status Selector */}
        <div className="todo-item-detail-group">
          <label htmlFor={`status-${todo.id}`} className="visually-hidden">Status</label>
          <select
            id={`status-${todo.id}`}
            value={todo.status}
            onChange={handleStatusChange}
            className={`todo-item-status-select ${getStatusClass(todo.status)}`}
            aria-label={`Change status for ${todo.title}`}
          >
            <option value="pending">Pending</option>
            <option value="in-progress">In Progress</option>
            <option value="completed">Completed</option>
          </select>
        </div>

        {/* Due Date Display */}
        <div className="todo-item-detail-group">
          <span className="todo-item-meta-label">Due:</span>
          <span className="todo-item-due-date">{formatDate(todo.dueDate)}</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="todo-item-actions">
        <button
          onClick={() => onEdit(todo.id)}
          className="todo-item-action-btn edit-btn"
          aria-label={`Edit ${todo.title}`}
        >
          Edit
        </button>
        <button
          onClick={() => onDelete(todo.id)}
          className="todo-item-action-btn delete-btn"
          aria-label={`Delete ${todo.title}`}
          style={{ backgroundColor: 'purple', color: 'white' }} // Changed delete button color to purple
        >
          Delete
        </button>
      </div>
    </div>
  );
};

export default TodoItem;