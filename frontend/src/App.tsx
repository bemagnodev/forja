import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Queue } from "./pages/Queue";
import { Contests } from "./pages/Contests";
import { ContestDetail } from "./pages/ContestDetail";
import { Dashboard } from "./pages/Dashboard";
import { Teams } from "./pages/Teams";
import { Notes } from "./pages/Notes";
import { Settings } from "./pages/Settings";
import { Profile } from "./pages/Profile";
import { AILab } from "./pages/AILab";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ToastProvider } from "@/components/ui/toast";
import { AuthProvider } from "@/contexts/AuthContext";
import { Login } from "@/pages/Login";
import { SetPassword } from "@/pages/SetPassword";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppFrame } from "@/components/layouts/AppFrame";

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return <AppFrame sidebar={<Sidebar />}>{children}</AppFrame>;
}

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <TooltipProvider>
          <Router>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/set-password" element={<SetPassword />} />
              <Route path="/*" element={
                <ProtectedRoute>
                  <ProtectedLayout>
                    <Routes>
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/" element={<Queue />} />
                      <Route path="/contests" element={<Contests />} />
                      <Route path="/contests/:id" element={<ContestDetail />} />
                      <Route path="/ai-lab" element={<AILab />} />
                      <Route path="/teams" element={<Teams />} />
                      <Route path="/notes" element={<Notes />} />
                      <Route path="/settings" element={<Settings />} />
                      <Route path="/profile" element={<Profile />} />
                    </Routes>
                  </ProtectedLayout>
                </ProtectedRoute>
              } />
            </Routes>
          </Router>
        </TooltipProvider>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
