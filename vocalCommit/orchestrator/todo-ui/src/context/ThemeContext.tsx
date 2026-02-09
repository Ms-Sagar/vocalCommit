import React, { createContext, useEffect, ReactNode } from 'react';

// The Theme type is now fixed to 'light' as dark mode is removed.
export type Theme = 'light';

// The ThemeContextType now only includes the 'theme' as there is no toggle functionality.
export interface ThemeContextType {
  theme: Theme;
}

export const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  // The theme is now always 'light'.
  // We no longer need useState to manage theme state or read from localStorage on initial render
  // for selection logic, as it's a fixed value.
  const theme: Theme = 'light';

  useEffect(() => {
    const body = document.body;
    // Ensure the 'dark-theme' class is always removed, enforcing light mode styles.
    body.classList.remove('dark-theme');
    // Set the document's color-scheme property to 'light'.
    document.documentElement.style.setProperty('color-scheme', 'light');

    // Persist the 'light' theme to localStorage.
    // This ensures any previously stored 'dark' theme is overwritten and
    // future loads consistently apply 'light' mode.
    localStorage.setItem('theme', 'light');
  }, []); // The effect runs once on mount to set the fixed 'light' theme properties.

  // The context value now only provides the fixed 'light' theme.
  // The toggleTheme function has been removed as there is no dark mode to toggle to.
  const contextValue = {
    theme,
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
};