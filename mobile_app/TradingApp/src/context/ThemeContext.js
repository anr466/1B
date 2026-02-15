/**
 * Theme Context - توفير Theme عبر Context API
 */

import React, { createContext, useContext } from 'react';
import { theme } from '../theme/theme';

const ThemeContext = createContext(theme);

export const ThemeProvider = ({ children }) => {
    return (
        <ThemeContext.Provider value={theme}>
            {children}
        </ThemeContext.Provider>
    );
};

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) {
        return theme; // Fallback to default theme
    }
    return context;
};

export default ThemeContext;
