import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent, SidebarGroupLabel,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarHeader, SidebarFooter,
  useSidebar,
} from '@/components/ui/sidebar';
import { NavLink } from '@/components/NavLink';
import { useLocation } from 'react-router-dom';
import { LayoutDashboard, CheckSquare, ScrollText, Settings, Plug, Zap, ShieldCheck } from 'lucide-react';

const navItems = [
  { title: 'Dashboard', url: '/dashboard', icon: LayoutDashboard },
  { title: 'Approvals', url: '/approvals', icon: CheckSquare },
  { title: 'Integrations', url: '/integrations', icon: Plug },
  { title: 'Audit Trail', url: '/audit', icon: ScrollText },
  { title: 'Admin', url: '/admin', icon: Settings },
  { title: 'Demo Console', url: '/demo', icon: Zap },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === 'collapsed';
  const location = useLocation();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-2.5">
          <img src="/zappsec.png" alt="ZappSec" className="w-8 h-8 rounded-lg" />
          {!collapsed && (
            <div>
              <span className="text-sm font-bold text-sidebar-foreground">WarRoom</span>
              <span className="text-xs text-sidebar-primary ml-1">Agent</span>
            </div>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map(item => (
                <SidebarMenuItem key={item.url}>
                  <SidebarMenuButton asChild>
                    <NavLink to={item.url} className="hover:bg-sidebar-accent/50" activeClassName="bg-sidebar-accent text-sidebar-primary font-medium">
                      <item.icon className="mr-2 h-4 w-4" />
                      {!collapsed && <span>{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4">
        {!collapsed && (
          <div className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-sidebar-accent/30">
            <ShieldCheck className="w-3.5 h-3.5 text-severity-success" />
            <span className="text-xs text-sidebar-foreground">All systems secured</span>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
