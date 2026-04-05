import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import IncidentDetail from "./pages/IncidentDetail";
import Integrations from "./pages/Integrations";
import ApprovalCenter from "./pages/ApprovalCenter";
import AuditTrail from "./pages/AuditTrail";
import Admin from "./pages/Admin";
import DemoConsole from "./pages/DemoConsole";
import NotFound from "./pages/NotFound";
import RequireAuth from "./components/RequireAuth";

const queryClient = new QueryClient();

const Protected = ({ element }: { element: JSX.Element }) => (
  <RequireAuth>{element}</RequireAuth>
);

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<Protected element={<Dashboard />} />} />
        <Route path="/incidents/:id" element={<Protected element={<IncidentDetail />} />} />
        <Route path="/integrations" element={<Protected element={<Integrations />} />} />
        <Route path="/approvals" element={<Protected element={<ApprovalCenter />} />} />
        <Route path="/audit" element={<Protected element={<AuditTrail />} />} />
        <Route path="/admin" element={<Protected element={<Admin />} />} />
        <Route path="/demo" element={<Protected element={<DemoConsole />} />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;