import { LogOut, Users, Activity, Settings as SettingsIcon } from 'lucide-react'
import { Button } from "@/components/ui/button"

export function Sidebar({
    activeTab,
    setActiveTab,
    isCollapsed,
    mobile = false,
    setIsSidebarOpen,
    handleLogout
}) {
    return (
        <div className="flex flex-col h-full bg-sidebar text-sidebar-foreground transition-all duration-300">
            <div className={`h-16 flex items-center border-b border-sidebar-border bg-sidebar ${mobile || !isCollapsed ? 'px-6' : 'justify-center'}`}>
                {mobile || !isCollapsed ? (
                    <div className="text-xl font-bold tracking-tight truncate">Blood Donation</div>
                ) : (
                    <Activity className="w-6 h-6 text-primary" />
                )}
            </div>
            <nav className="flex-1 p-2 space-y-2">
                <Button
                    variant={activeTab === 'users' ? "secondary" : "ghost"}
                    className={`w-full justify-start ${!mobile && isCollapsed ? 'px-2 justify-center' : ''}`}
                    onClick={() => { setActiveTab('users'); if (mobile) setIsSidebarOpen(false); }}
                    title="User Management"
                >
                    <Users className={`w-5 h-5 ${mobile || !isCollapsed ? 'mr-2' : ''}`} />
                    {(mobile || !isCollapsed) && <span>User Management</span>}
                </Button>
                <Button
                    variant={activeTab === 'feed' ? "secondary" : "ghost"}
                    className={`w-full justify-start ${!mobile && isCollapsed ? 'px-2 justify-center' : ''}`}
                    onClick={() => { setActiveTab('feed'); if (mobile) setIsSidebarOpen(false); }}
                    title="Live Feed"
                >
                    <Activity className={`w-5 h-5 ${mobile || !isCollapsed ? 'mr-2' : ''}`} />
                    {(mobile || !isCollapsed) && <span>Live Feed</span>}
                </Button>
                <Button
                    variant={activeTab === 'settings' ? "secondary" : "ghost"}
                    className={`w-full justify-start ${!mobile && isCollapsed ? 'px-2 justify-center' : ''}`}
                    onClick={() => { setActiveTab('settings'); if (mobile) setIsSidebarOpen(false); }}
                    title="Settings"
                >
                    <SettingsIcon className={`w-5 h-5 ${mobile || !isCollapsed ? 'mr-2' : ''}`} />
                    {(mobile || !isCollapsed) && <span>Settings</span>}
                </Button>
            </nav>
            <div className="p-2 border-t border-sidebar-border">
                <Button
                    variant="ghost"
                    className={`w-full justify-start text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent ${!mobile && isCollapsed ? 'px-2 justify-center' : ''}`}
                    onClick={handleLogout}
                    title="Logout"
                >
                    <LogOut className={`w-5 h-5 ${mobile || !isCollapsed ? 'mr-2' : ''}`} />
                    {(mobile || !isCollapsed) && <span>Logout</span>}
                </Button>
            </div>
        </div>
    )
}
