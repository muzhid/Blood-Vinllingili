import { useState, useEffect } from 'react'
import { Save, Eye, EyeOff } from 'lucide-react'
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { AdminTable } from "@/components/AdminTable"
import { CommandTable } from "@/components/CommandTable"

export function Settings() {
    const [settings, setSettings] = useState({
        TELEGRAM_BOT_TOKEN: '',
        TELEGRAM_CHANNEL_ID: '',
        ADMIN_GROUP_ID: '',
        SUPABASE_URL: '',
        SUPABASE_KEY: ''
    })
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [showToken, setShowToken] = useState(false)
    const [showKey, setShowKey] = useState(false)

    useEffect(() => {
        fetchSettings()
    }, [])

    const fetchSettings = async () => {
        try {
            const res = await fetch('/api/settings', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
            })
            const data = await res.json()
            setSettings({
                TELEGRAM_BOT_TOKEN: data.TELEGRAM_BOT_TOKEN || '',
                TELEGRAM_CHANNEL_ID: data.TELEGRAM_CHANNEL_ID || '',
                ADMIN_GROUP_ID: data.ADMIN_GROUP_ID || '',
                SUPABASE_URL: data.SUPABASE_URL || '',
                SUPABASE_KEY: data.SUPABASE_KEY || ''
            })
        } catch (error) {
            toast.error('Failed to fetch settings')
        } finally {
            setLoading(false)
        }
    }

    const handleChange = (e) => {
        setSettings({ ...settings, [e.target.name]: e.target.value })
    }

    const handleSave = async () => {
        setSaving(true)
        try {
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify(settings)
            })
            const result = await res.json()
            if (result.status === 'ok') {
                toast.success(result.message)
            } else {
                throw new Error(result.detail)
            }
        } catch (error) {
            toast.error(error.message || 'Failed to save settings')
        } finally {
            setSaving(false)
        }
    }

    if (loading) return <div className="text-muted-foreground p-8">Loading settings...</div>

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <h1 className="text-3xl font-bold tracking-tight">System Settings</h1>
                <Button onClick={handleSave} disabled={saving} className="w-full md:w-auto text-white">
                    {saving ? (
                        <>Saving...</>
                    ) : (
                        <>
                            <Save className="mr-2 h-4 w-4" /> Save Configuration
                        </>
                    )}
                </Button>
            </div>

            <div className="grid gap-6">
                {/* 1. Admin Users */}
                <AdminTable />

                {/* 2. Bot Command Reference */}
                <CommandTable />

                {/* 3. Telegram Configuration */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-primary flex items-center gap-2">
                            Telegram Configuration
                        </CardTitle>
                        <CardDescription>
                            These settings connect your system to the Telegram Bot.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="TELEGRAM_BOT_TOKEN">Bot Token</Label>
                            <div className="relative">
                                <Input
                                    id="TELEGRAM_BOT_TOKEN"
                                    name="TELEGRAM_BOT_TOKEN"
                                    type={showToken ? "text" : "password"}
                                    value={settings.TELEGRAM_BOT_TOKEN}
                                    onChange={handleChange}
                                    placeholder="123456:ABC-DEF..."
                                    className="pr-10"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowToken(!showToken)}
                                    className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                                >
                                    {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                            </div>
                            <p className="text-xs text-muted-foreground">From @BotFather (Confidential)</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="TELEGRAM_CHANNEL_ID">Community Channel ID</Label>
                                <Input
                                    id="TELEGRAM_CHANNEL_ID"
                                    name="TELEGRAM_CHANNEL_ID"
                                    value={settings.TELEGRAM_CHANNEL_ID}
                                    onChange={handleChange}
                                    placeholder="-100..."
                                />
                                <p className="text-xs text-muted-foreground">For public requests</p>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="ADMIN_GROUP_ID">Admin Group ID</Label>
                                <Input
                                    id="ADMIN_GROUP_ID"
                                    name="ADMIN_GROUP_ID"
                                    value={settings.ADMIN_GROUP_ID}
                                    onChange={handleChange}
                                    placeholder="-100..."
                                />
                                <p className="text-xs text-muted-foreground">For admin alerts</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* 4. Database Configuration */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-primary flex items-center gap-2">
                            Database Configuration
                        </CardTitle>
                        <CardDescription>
                            Database Connection (Supabase or Local).
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="SUPABASE_URL">Supabase URL / Local URL</Label>
                            <Input
                                id="SUPABASE_URL"
                                name="SUPABASE_URL"
                                value={settings.SUPABASE_URL}
                                onChange={handleChange}
                                placeholder="http://localhost:8000"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="SUPABASE_KEY">Supabase Key (Service Role)</Label>
                            <div className="relative">
                                <Input
                                    id="SUPABASE_KEY"
                                    name="SUPABASE_KEY"
                                    type={showKey ? "text" : "password"}
                                    value={settings.SUPABASE_KEY}
                                    onChange={handleChange}
                                    placeholder="..."
                                    className="pr-10"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowKey(!showKey)}
                                    className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                                >
                                    {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
