import { useEffect, useState } from 'react'
import { fetchWithAuth } from '@/lib/auth'
import { LogOut, Users, Activity, Settings as SettingsIcon, Menu, Lock, PanelLeft } from 'lucide-react'
import { Separator } from "@/components/ui/separator"
import { useNavigate } from 'react-router-dom'
import { UserTable } from '../components/UserTable'
import { RequestTable } from '../components/RequestTable'
import { CommandTable } from '../components/CommandTable'
import { AdminTable } from '../components/AdminTable'
import { Sidebar } from '../components/Sidebar'
import { Settings } from './Settings'

import { Button } from "@/components/ui/button"
import { ModeToggle } from "@/components/mode-toggle"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"

export default function Dashboard() {
    const [activeTab, setActiveTab] = useState('users')
    const [isSidebarOpen, setIsSidebarOpen] = useState(false)
    const [isCollapsed, setIsCollapsed] = useState(false)

    // Auth State
    const [user, setUser] = useState(null)
    const [isResetOpen, setIsResetOpen] = useState(false)
    const [newPass, setNewPass] = useState('')
    const [confirmPass, setConfirmPass] = useState('')

    useEffect(() => {
        const u = localStorage.getItem('admin_user')
        if (u) setUser(JSON.parse(u))
    }, [])

    const handleLogout = () => {
        localStorage.removeItem('admin_user')
        window.location.href = '/'
    }

    const handleResetPassword = async () => {
        if (newPass !== confirmPass) {
            toast.error("Passwords do not match.")
            return
        }
        if (newPass.length < 4) {
            toast.error("Minimum 4 characters required.")
            return
        }
        if (!/[!@#$%^&*(),.?":{}|<>]/.test(newPass)) {
            toast.error("Must include at least one special character.")
            return
        }

        try {
            const res = await fetchWithAuth('/api/update_password', {
                method: 'POST',
                body: JSON.stringify({ username: user.phone_number || user.username, new_password: newPass })
            })
            if (!res) return
            const data = await res.json()
            if (data.status === 'ok') {
                toast.success('Password updated successfully!')
                setIsResetOpen(false)
                setNewPass('')
                setConfirmPass('')
            } else {
                toast.error(data.message || 'Update failed')
            }
        } catch (e) {
            toast.error('Connection error')
        }
    }

    return (
        <div className="flex h-screen bg-background overflow-hidden text-foreground">
            {/* Desktop Sidebar */}
            <div className={`hidden md:block border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-all duration-300 ${isCollapsed ? 'w-16' : 'w-52'}`}>
                <Sidebar
                    activeTab={activeTab}
                    setActiveTab={setActiveTab}
                    isCollapsed={isCollapsed}
                    handleLogout={handleLogout}
                />
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col h-full relative overflow-hidden bg-background">
                {/* Header */}
                <header className="flex h-16 items-center border-b bg-background px-6 justify-between">
                    <div className="flex items-center gap-4">
                        {/* Mobile Sidebar Trigger */}
                        <div className="md:hidden">
                            <Sheet open={isSidebarOpen} onOpenChange={setIsSidebarOpen}>
                                <SheetTrigger asChild>
                                    <Button variant="ghost" size="icon" className="md:hidden">
                                        <Menu className="h-6 w-6" />
                                        <span className="sr-only">Toggle menu</span>
                                    </Button>
                                </SheetTrigger>
                                <SheetContent side="left" className="p-0 border-r-0 bg-sidebar text-sidebar-foreground w-56">
                                    <Sidebar
                                        activeTab={activeTab}
                                        setActiveTab={setActiveTab}
                                        isCollapsed={false}
                                        mobile={true}
                                        setIsSidebarOpen={setIsSidebarOpen}
                                        handleLogout={handleLogout}
                                    />
                                </SheetContent>
                            </Sheet>
                        </div>

                        {/* Desktop Sidebar Toggle */}
                        <Button
                            variant="ghost"
                            size="icon"
                            className="hidden md:flex text-muted-foreground"
                            onClick={() => setIsCollapsed(!isCollapsed)}
                        >
                            <PanelLeft className="h-5 w-5" />
                        </Button>
                        <h1 className="text-xl font-bold tracking-tight">
                            {activeTab === 'feed' ? 'Live Requests' : activeTab === 'users' ? 'User Management' : 'Settings'}
                        </h1>
                    </div>

                    <div className="flex items-center gap-4">
                        <ModeToggle />

                        {/* User Profile Dropdown */}
                        {user && (
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                                        <Avatar>
                                            <AvatarImage src="" />
                                            <AvatarFallback className="bg-primary text-primary-foreground font-bold">
                                                {user.username?.substring(0, 2).toUpperCase() || 'AD'}
                                            </AvatarFallback>
                                        </Avatar>
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent className="w-56" align="end" forceMount>
                                    <DropdownMenuLabel className="font-normal">
                                        <div className="flex flex-col space-y-1">
                                            <p className="text-sm font-medium leading-none">{user.username}</p>
                                            <p className="text-xs leading-none text-muted-foreground">
                                                {user.phone_number || 'Admin Access'}
                                            </p>
                                        </div>
                                    </DropdownMenuLabel>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem onClick={() => setIsResetOpen(true)}>
                                        <Lock className="mr-2 h-4 w-4" />
                                        <span>Reset Password</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive">
                                        <LogOut className="mr-2 h-4 w-4" />
                                        <span>Log out</span>
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        )}
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto p-4 md:p-8">
                    {activeTab === 'feed' && (
                        <div className="max-w-7xl mx-auto space-y-4">
                            <RequestTable />
                        </div>
                    )}

                    {activeTab === 'users' && (
                        <div className="max-w-7xl mx-auto space-y-4">
                            <UserTable />
                        </div>
                    )}

                    {activeTab === 'settings' && (
                        <div className="max-w-4xl mx-auto space-y-8 pb-10">
                            <Settings />
                        </div>
                    )}
                </main>
            </div>

            {/* Password Reset Dialog */}
            <Dialog open={isResetOpen} onOpenChange={setIsResetOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle>Reset Password</DialogTitle>
                        <DialogDescription>
                            Change your admin dashboard password.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="new-pass">New Password</Label>
                            <Input
                                id="new-pass"
                                type="password"
                                value={newPass}
                                onChange={(e) => setNewPass(e.target.value)}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="confirm-pass">Confirm New Password</Label>
                            <Input
                                id="confirm-pass"
                                type="password"
                                value={confirmPass}
                                onChange={(e) => setConfirmPass(e.target.value)}
                            />
                            <p className="text-[0.8rem] text-muted-foreground">Min 4 chars, 1 special character.</p>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsResetOpen(false)}>Cancel</Button>
                        <Button onClick={handleResetPassword}>Update Password</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}
