import React from 'react';
import './RefreshButton.css';

/**
 * Props for the RefreshButton component.
 */
interface RefreshButtonProps {
  /**
   * Function to call when the refresh button is clicked.
   */
  onClick: () => void;
  /**
   * Indicates whether a refresh operation is currently in progress.
   * If true, the button will show a loading animation and be disabled.
   */
  isLoading: boolean;
  /**
   * Optional. The Date object representing the last time content was refreshed.
   * Used for accessibility labels and tooltips.
   */
  lastRefreshTime?: Date;
}

/**
 * A reusable Refresh Button component that displays an icon,
 * handles loading states with an animation, and provides accessibility features.
 *
 * @param {RefreshButtonProps} props - The props for the RefreshButton component.
 * @returns {JSX.Element} The rendered RefreshButton component.
 */
const RefreshButton: React.FC<RefreshButtonProps> = ({ onClick, isLoading, lastRefreshTime }) => {
  // Format the last refresh time for display in aria-label and title.
  const formattedLastRefreshTime = lastRefreshTime
    ? lastRefreshTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : 'never';

  // Construct an accessibility label that changes based on the loading state.
  const ariaLabel = isLoading
    ? 'Refreshing content...'
    : `Refresh content. Last refreshed at ${formattedLastRefreshTime}.`;

  return (
    <button
      type="button"
      className={`refresh-button ${isLoading ? 'loading' : ''}`}
      onClick={onClick}
      disabled={isLoading} // Disable the button when loading to prevent multiple clicks
      aria-label={ariaLabel} // Provides an accessible label for screen readers
      title={ariaLabel} // Provides a tooltip for mouse users
    >
      {/* SVG Icon for the refresh action */}
      <svg
        className="refresh-icon"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true" // Hide from screen readers as button already has aria-label
      >
        <path d="M23 4v6h-6"></path>
        <path d="M1 20v-6h6"></path>
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
      </svg>
    </button>
  );
};

export default RefreshButton;