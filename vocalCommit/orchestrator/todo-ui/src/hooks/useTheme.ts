import { useContext } from 'react';
import { ThemeContext, ThemeContextType } from '../context/ThemeContext';

/**
 * Custom hook to access the current theme.
 * It ensures that the ThemeContext is used within a ThemeProvider.
 * With dark mode removed, the theme is always 'light'.
 *
 * @returns An object containing the current theme ('light').
 * @throws An error if `useTheme` is used outside of a `ThemeProvider`.
 */
export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);

  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }

  return context;
};