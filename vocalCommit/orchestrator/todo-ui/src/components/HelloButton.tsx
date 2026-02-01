import React, { useState, useEffect, useRef } from 'react';
import './HelloButton.css'; // Import the CSS for styling this component

interface HelloButtonProps {
  // In a production application, you might want to add props here
  // For example, `label?: string` to customize the button text,
  // or `onHello?: () => void` for an external callback when "hello" is displayed.
  // For this specific request, a self-contained button with a fixed message is sufficient.
}

const HelloButton: React.FC<HelloButtonProps> = () => {
  // State to control the visibility of the "Hello!" message
  const [showHelloMessage, setShowHelloMessage] = useState<boolean>(false);

  // useRef to store the timeout ID. This allows us to clear the timeout
  // effectively without causing re-renders when the ID changes.
  const timeoutIdRef = useRef<number | null>(null);

  /**
   * Handles the button click event.
   * - Clears any existing timeout to reset the message display duration if clicked rapidly.
   * - Sets `showHelloMessage` to true to display "Hello!".
   * - Sets a new timeout to hide the message after a specified duration.
   */
  const handleButtonClick = () => {
    // If there's an active timeout, clear it first
    if (timeoutIdRef.current) {
      clearTimeout(timeoutIdRef.current);
      timeoutIdRef.current = null; // Reset the ref after clearing
    }

    // Show the "Hello!" message
    setShowHelloMessage(true);

    // Set a new timeout to hide the message after 2.5 seconds
    // Using window.setTimeout ensures we get the browser's timer ID type (number)
    timeoutIdRef.current = window.setTimeout(() => {
      setShowHelloMessage(false);
      timeoutIdRef.current = null; // Clear the ref once the timeout has executed
    }, 2500); // Message will be displayed for 2.5 seconds
  };

  /**
   * useEffect hook for cleanup.
   * This ensures that any pending timeout is cleared if the component unmounts
   * before the timeout has a chance to execute. This prevents memory leaks.
   */
  useEffect(() => {
    // The cleanup function runs when the component unmounts
    return () => {
      if (timeoutIdRef.current) {
        clearTimeout(timeoutIdRef.current);
      }
    };
  }, []); // Empty dependency array ensures this effect runs only on mount and unmount

  return (
    <div className="hello-button-wrapper"> {/* Wrapper for potential layout of button and message */}
      <button
        type="button" // Important for accessibility and to prevent accidental form submissions
        className="hello-button" // Applies styling from HelloButton.css
        onClick={handleButtonClick}
        aria-label="Press to say hello" // Provides a descriptive label for screen readers
        // aria-live="off" on the button itself is not necessary as the message has its own live region
      >
        Say Hello
      </button>
      {showHelloMessage && (
        <span
          className="hello-message" // Applies styling for the message
          role="status" // Indicates to screen readers that this element contains status information
          aria-live="polite" // Screen readers will politely announce changes to this element
        >
          Hello!
        </span>
      )}
    </div>
  );
};

export default HelloButton;