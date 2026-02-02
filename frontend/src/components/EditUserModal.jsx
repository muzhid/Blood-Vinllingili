import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabaseClient'
import { X, Trash2, Ban, CheckCircle, Save } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"

export function EditUserModal({ user, onClose, onUpdate }) {
    const [formData, setFormData] = useState({
        full_name: '',
        phone_number: '',
        blood_type: '',
        sex: '',
        address: '',
        id_card_number: '',
        telegram_id: '',
        role: 'user',
        status: 'active'
    })
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (user) {
            setFormData({
                full_name: user.full_name || '',
                phone_number: user.phone_number || '',
                blood_type: user.blood_type || '',
                sex: user.sex || '',
                address: user.address || '',
                id_card_number: user.id_card_number || '',
                telegram_id: user.telegram_id || '',
                role: user.role || 'user',
                status: user.status || 'active'
            })
        }
    }, [user])

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value })
    }

    const handleSelectChange = (name, value) => {
        setFormData({ ...formData, [name]: value })
    }

    const handleSave = async () => {
        setLoading(true)
        setError(null)
        try {
            // Determine Endpoint
            const isCreate = !user || !user.telegram_id
            const endpoint = isCreate ? '/api/create_user' : '/api/update_user'

            const payload = { ...formData }
            if (!isCreate) payload.telegram_id = user.telegram_id

            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify(payload)
            })

            const result = await res.json()
            if (result.status !== 'ok') throw new Error(result.detail || 'Operation failed')

            onUpdate()
            onClose()
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const handleToggleBlock = async () => {
        if (!window.confirm(`Are you sure you want to ${formData.status === 'banned' ? 'unban' : 'ban'} this user?`)) return

        setLoading(true)
        const newStatus = formData.status === 'banned' ? 'active' : 'banned'
        try {
            const { error } = await supabase
                .from('villingili_users')
                .update({ status: newStatus })
                .eq('telegram_id', user.telegram_id)

            if (error) throw error
            onUpdate() // Refresh list
            onClose()  // Close or keep open? standard is close (or update local state)
        } catch (err) {
            setError(err.message)
            setLoading(false)
        }
    }

    const handleDelete = async () => {
        if (!window.confirm("Are you sure? This will delete the user AND all their requests. This action cannot be undone.")) return

        setLoading(true)
        try {
            // 1. Delete all requests by this user (FK constraint fix)
            const { error: reqError } = await supabase
                .from('villingili_requests')
                .delete()
                .eq('requester_id', user.telegram_id)

            if (reqError) throw reqError

            // 2. Delete the user
            const { error } = await supabase
                .from('villingili_users')
                .delete()
                .eq('telegram_id', user.telegram_id)

            if (error) throw error
            onUpdate()
            onClose()
        } catch (err) {
            console.error(err)
            setError(err.message)
            setLoading(false)
        }
    }

    const handleDeactivate = async () => {
        const isPending = formData.status === 'pending'
        if (!window.confirm(isPending ? "Activate this user?" : "Mark this user as 'deactive' (pending)? They won't appear in donor lists.")) return
        setLoading(true)
        try {
            // Use Backend API
            const res = await fetch('/api/update_user', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    telegram_id: user.telegram_id,
                    status: isPending ? 'active' : 'pending'
                })
            })
            const result = await res.json()
            if (result.status !== 'ok') throw new Error(result.detail || 'Deactivation failed')

            onUpdate()
            onClose()
        } catch (err) {
            setError(err.message)
            setLoading(false)
        }
    }

    const isCreate = !user || !user.telegram_id

    return (
        <Dialog open={true} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[625px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{isCreate ? 'Add New User' : 'Edit User'}</DialogTitle>
                    <DialogDescription>
                        {isCreate ? "Add a new user manually to the system." : "Update user details or manage their access."}
                    </DialogDescription>
                </DialogHeader>

                {!isCreate && user.telegram_id && (
                    <div className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
                        ID: {user.telegram_id}
                        <a
                            href={`https://web.telegram.org/a/#${user.telegram_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-500 hover:underline"
                        >
                            (Open TG)
                        </a>
                    </div>
                )}

                {error && (
                    <div className="bg-destructive/15 text-destructive text-sm p-3 rounded-md">
                        {error}
                    </div>
                )}

                <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="full_name">Full Name</Label>
                            <Input
                                id="full_name"
                                name="full_name"
                                value={formData.full_name}
                                onChange={handleChange}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="telegram_id">Telegram ID</Label>
                            <Input
                                id="telegram_id"
                                name="telegram_id"
                                type="number"
                                value={formData.telegram_id}
                                onChange={handleChange}
                                disabled={!isCreate}
                                placeholder="Auto-generated if empty"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="phone_number">Phone Number</Label>
                            <Input
                                id="phone_number"
                                name="phone_number"
                                value={formData.phone_number}
                                onChange={handleChange}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="blood_type">Blood Type</Label>
                            <Select
                                value={formData.blood_type}
                                onValueChange={(val) => handleSelectChange('blood_type', val)}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'].map(t => (
                                        <SelectItem key={t} value={t}>{t}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="sex">Sex</Label>
                            <Select
                                value={formData.sex}
                                onValueChange={(val) => handleSelectChange('sex', val)}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select..." />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="Male">Male</SelectItem>
                                    <SelectItem value="Female">Female</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="id_card_number">ID Card Number</Label>
                            <Input
                                id="id_card_number"
                                name="id_card_number"
                                value={formData.id_card_number}
                                onChange={handleChange}
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="role">Role</Label>
                            <Select
                                value={formData.role}
                                onValueChange={(val) => handleSelectChange('role', val)}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select..." />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="user">User</SelectItem>
                                    <SelectItem value="admin">Admin</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="address">Address/Island</Label>
                            <Input
                                id="address"
                                name="address"
                                value={formData.address}
                                onChange={handleChange}
                            />
                        </div>
                    </div>
                </div>

                <DialogFooter className="flex-col sm:flex-row gap-2">
                    <div className="flex flex-1 justify-start gap-2">
                        {!isCreate && (
                            <>
                                <Button
                                    variant="outline" size="sm"
                                    onClick={handleToggleBlock}
                                    className={formData.status === 'banned' ? "text-green-600 hover:text-green-700" : "text-orange-600 hover:text-orange-700"}
                                >
                                    {formData.status === 'banned' ? <CheckCircle className="mr-2 h-4 w-4" /> : <Ban className="mr-2 h-4 w-4" />}
                                    {formData.status === 'banned' ? 'Unban' : 'Block'}
                                </Button>
                                <Button
                                    variant="outline" size="sm"
                                    onClick={handleDeactivate}
                                    className="text-gray-500"
                                >
                                    {formData.status === 'pending' ? <CheckCircle className="mr-2 h-4 w-4" /> : <Ban className="mr-2 h-4 w-4 rotate-90" />}
                                    {formData.status === 'pending' ? 'Activate' : 'Waitlist'}
                                </Button>
                                <Button
                                    variant="destructive" size="sm"
                                    onClick={handleDelete}
                                >
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    Delete
                                </Button>
                            </>
                        )}
                    </div>
                    <div className="flex gap-2">
                        <Button variant="secondary" onClick={onClose}>Cancel</Button>
                        <Button onClick={handleSave} disabled={loading} className="bg-red-600 hover:bg-red-500">
                            {loading ? 'Saving...' : 'Save Changes'}
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
