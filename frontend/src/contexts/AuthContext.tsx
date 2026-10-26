import { useQueryClient } from '@tanstack/react-query';
import { resetApiSession } from '@/lib/api';
import React, { useState } from 'react';
import { AuthContext } from './useAuth';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const clearSession = () => {
    resetApiSession();
    void queryClient.cancelQueries();
    queryClient.clear();
  };
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!localStorage.getItem('access_token'));

  const login = (access: string, refresh: string) => {
    clearSession();
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    setIsAuthenticated(true);
  };

  const logout = () => {
    clearSession();
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
