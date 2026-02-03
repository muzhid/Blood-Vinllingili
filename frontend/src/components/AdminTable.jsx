import { useEffect, useState } from 'react'
import { fetchWithAuth } from '@/lib/auth'
import { Plus, Trash2, Key } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"

export function AdminTable() {
    const [admins, setAdmins] = useState([])
    const [loading, setLoading] = useState(true)
    const [showAddModal, setShowAddModal] = useState(false)
    const [newUsername, setNewUsername] = useState('')
    const [newPhone, setNewPhone] = useState('')

    // Reset Password State
    const [resetTarget, setResetTarget] = useState(null)
    const [adminNewPass, setAdminNewPass] = useState('')
    const [adminConfirmPass, setAdminConfirmPass] = useState('')

    const handleAdminReset = async () => {
        if (!adminNewPass || adminNewPass !== adminConfirmPass) {
            toast.error("Passwords do not match or are empty.")
            return
        }
        if (adminNewPass.length < 4) {
            toast.error("Password must be at least 4 characters.")
            return
        }

        try {
            const res = await fetchWithAuth('/api/update_password', {
                method: 'POST',
                body: JSON.stringify({
                    username: resetTarget.phone_number || resetTarget.username, // Use Phone as ID
                    new_password: adminNewPass
                })
            })
            if (!res) return
            const data = await res.json()
            if (data.status === 'ok') {
                setResetTarget(null)
                setAdminNewPass('')
                setAdminConfirmPass('')
                toast.success("Password updated successfully!")
                fetchAdmins()
            } else {
                toast.error(data.message || 'Update failed')
            }
        } catch (e) {
            toast.error('Connection error')
        }
    }


    const handleDeleteAdmin = async (admin) => {
        if (!window.confirm(`Are you sure you want to delete admin ${admin.username}?`)) return

        try {
            const res = await fetchWithAuth('/api/delete_admin', {
                method: 'POST',
                body: JSON.stringify({ telegram_id: admin.telegram_id, username: admin.username })
            })
            if (!res) return
            const data = await res.json()
            if (data.status === 'ok') {
                toast.success("Admin deleted successfully")
                fetchAdmins()
            } else {
                toast.error("Delete Failed: " + data.detail)
            }
        } catch (e) {
            toast.error("Delete Error")
        }
    }

    const handleCreateAdmin = async () => {
        if (!newUsername || !newPhone) {
            toast.error("Username and Phone are required")
            return
        }

        try {
            const res = await fetchWithAuth('/api/create_admin', {
                method: 'POST',
                body: JSON.stringify({ username: newUsername, phone_number: newPhone })
            })
            if (!res) return
            const data = await res.json()
            if (data.status === 'ok') {
                setShowAddModal(false)
                setNewUsername('')
                setNewPhone('')
                toast.success("Admin created successfully")
                fetchAdmins()
            } else {
                toast.error(data.message || 'Creation failed')
            }
        } catch (e) {
            toast.error('Connection error')
        }
    }

    useEffect(() => {
        fetchAdmins()
    }, [])

    const fetchAdmins = async () => {
        try {
            const res = await fetchWithAuth('/api/get_admins')
            if (!res) return

            const data = await res.json()
            if (Array.isArray(data)) {
                setAdmins(data)
            } else {
                console.error("API Error or Invalid Format:", data)
                setAdmins([])
            }
        } catch (error) {
            console.error("Error fetching admins:", error)
        }
        setLoading(false)
    }

    if (loading) return <div className="text-muted-foreground animate-pulse">Loading Admins...</div>

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle>Admin Users</CardTitle>
                <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
                    <DialogTrigger asChild>
                        <Button className="bg-red-600 hover:bg-red-500">
                            <Plus className="mr-2 h-4 w-4" /> Add Admin
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Add New Admin</DialogTitle>
                            <DialogDescription>
                                Create a new admin user. Default password is <b>Password1</b>.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                            <div className="grid gap-2">
                                <Label htmlFor="username">Username</Label>
                                <Input
                                    id="username"
                                    placeholder="Username"
                                    value={newUsername}
                                    onChange={(e) => setNewUsername(e.target.value)}
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="phone">Phone Number</Label>
                                <Input
                                    id="phone"
                                    placeholder="Phone Number"
                                    value={newPhone}
                                    onChange={(e) => setNewPhone(e.target.value)}
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setShowAddModal(false)}>Cancel</Button>
                            <Button onClick={handleCreateAdmin} className="bg-red-600 hover:bg-red-500">Create</Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </CardHeader>
            <CardContent>
                {/* Desktop View */}
                <div className="hidden md:block rounded-md border overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-[200px]">Name</TableHead>
                                <TableHead>Phone</TableHead>
                                <TableHead>Password</TableHead>
                                <TableHead>Created At</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {admins.map((admin, index) => (
                                <TableRow key={index}>
                                    <TableCell className="font-medium py-1 md:py-4">{admin.username}</TableCell>
                                    <TableCell className="py-1 md:py-4">{admin.phone_number || '-'}</TableCell>
                                    <TableCell className="py-1 md:py-4">
                                        <code className="text-xs bg-muted px-2 py-1 rounded">••••••••</code>
                                    </TableCell>
                                    <TableCell className="py-1 md:py-4">{new Date(admin.created_at).toLocaleDateString('en-GB').replace(/\//g, '-')}</TableCell>
                                    <TableCell className="text-right py-1 md:py-4">
                                        <div className="flex justify-end gap-2">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-8 w-8 p-0"
                                                onClick={() => setResetTarget(admin)}
                                            >
                                                <Key className="h-4 w-4 text-blue-500" />
                                                <span className="sr-only">Reset Password</span>
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-8 w-8 p-0"
                                                onClick={() => handleDeleteAdmin(admin)}
                                            >
                                                <Trash2 className="h-4 w-4 text-red-500" />
                                                <span className="sr-only">Delete</span>
                                            </Button>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ))}
                            {admins.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan="5" className="h-24 text-center text-muted-foreground">No admins found.</TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </div>

                {/* Mobile View */}
                <div className="grid grid-cols-1 gap-4 md:hidden">
                    {admins.map((admin, index) => (
                        <Card key={index} className="bg-muted/10">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-base font-bold flex justify-between items-center">
                                    {admin.username}
                                    <span className="text-xs font-normal text-muted-foreground">
                                        {new Date(admin.created_at).toLocaleDateString('en-GB')}
                                    </span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="pb-2 text-sm">
                                <div className="flex flex-col gap-1">
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Phone:</span>
                                        <span>{admin.phone_number || '-'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Password:</span>
                                        <code className="text-xs bg-muted px-2 py-0.5 rounded">••••••••</code>
                                    </div>
                                </div>
                            </CardContent>
                            <CardFooter className="flex justify-end gap-2 pt-2 border-t bg-muted/20">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-8 text-xs border-blue-200 text-blue-600 hover:bg-blue-50"
                                    onClick={() => setResetTarget(admin)}
                                >
                                    <Key className="mr-2 h-3 w-3" />
                                    Reset Pass
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-8 text-xs border-red-200 text-red-600 hover:bg-red-50"
                                    onClick={() => handleDeleteAdmin(admin)}
                                >
                                    <Trash2 className="mr-2 h-3 w-3" />
                                    Delete
                                </Button>
                            </CardFooter>
                        </Card>
                    ))}
                    {admins.length === 0 && (
                        <div className="text-center p-8 text-muted-foreground bg-muted/20 rounded-lg">
                            No admins found.
                        </div>
                    )}
                </div>
            </CardContent>

            {/* Reset Password Dialog (Controlled by resetTarget state) */}
            <Dialog open={!!resetTarget} onOpenChange={(open) => !open && setResetTarget(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Reset Password for {resetTarget?.username}</DialogTitle>
                        <DialogDescription>
                            Enter a new password for this admin.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label>New Password</Label>
                            <Input
                                type="password"
                                placeholder="New Password"
                                value={adminNewPass}
                                onChange={(e) => setAdminNewPass(e.target.value)}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label>Confirm Password</Label>
                            <Input
                                type="password"
                                placeholder="Confirm Password"
                                value={adminConfirmPass}
                                onChange={(e) => setAdminConfirmPass(e.target.value)}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setResetTarget(null)}>Cancel</Button>
                        <Button onClick={handleAdminReset} className="bg-blue-600 hover:bg-blue-500">Update Password</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    )
}
