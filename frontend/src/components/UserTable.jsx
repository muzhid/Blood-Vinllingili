import { useState, useEffect, useMemo } from 'react'
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    getFilteredRowModel,
    flexRender,
} from '@tanstack/react-table'
import { ArrowUpDown, Plus, Search, Calendar as CalendarIcon, Droplet, User, Phone, MapPin, CreditCard, MoreHorizontal } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Calendar } from "@/components/ui/calendar"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { format, addMonths, parseISO } from "date-fns"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { CustomDatePicker } from "@/components/ui/custom-date-picker"

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"

import { EditUserModal } from './EditUserModal'

export function UserTable() {
    const [data, setData] = useState([])
    const [sorting, setSorting] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedUser, setSelectedUser] = useState(null)
    const [isModalOpen, setIsModalOpen] = useState(false)

    // Donation State
    const [donationUser, setDonationUser] = useState(null)
    const [donationDate, setDonationDate] = useState(new Date())
    const [isDonationOpen, setIsDonationOpen] = useState(false)

    useEffect(() => {
        fetchUsers()
    }, [])

    const fetchUsers = async () => {
        try {
            const res = await fetch('/api/users', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
            })
            const users = await res.json()
            if (!res.ok) throw new Error("Failed to fetch users")

            setData(users)
        } catch (error) {
            console.error('Error fetching users:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleRowClick = (user) => {
        setSelectedUser(user)
        setIsModalOpen(true)
    }

    const handleUpdate = () => {
        fetchUsers() // Refresh data
    }

    const openDonationModal = (e, user) => {
        e.stopPropagation() // Prevent row click
        setDonationUser(user)
        setDonationDate(new Date())
        setIsDonationOpen(true)
    }

    const confirmDonation = async () => {
        if (!donationUser) return

        try {
            const formattedDate = format(donationDate, 'yyyy-MM-dd')
            const res = await fetch('/api/update_last_donation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({ user_id: donationUser.telegram_id, date: formattedDate })
            })
            const result = await res.json()

            if (result.status === 'ok') {
                toast.success(`Donation recorded for ${donationUser.full_name}`)
                fetchUsers() // Refresh list
                setIsDonationOpen(false)
            } else {
                toast.error(result.message || "Failed to update")
            }
        } catch (e) {
            toast.error("Connection error")
        }
    }

    // ... columns definition ...
    const columns = useMemo(
        () => [
            {
                accessorKey: 'full_name',
                header: 'Name',
            },
            {
                accessorKey: 'phone_number',
                header: 'Phone',
            },
            {
                accessorKey: 'blood_type',
                header: ({ column }) => {
                    return (
                        <Button
                            variant="ghost"
                            className="p-0 hover:bg-transparent"
                            onClick={(e) => {
                                e.stopPropagation() // Prevent row click
                                column.toggleSorting(column.getIsSorted() === 'asc')
                            }}
                        >
                            Group
                            <ArrowUpDown className="ml-2 h-4 w-4" />
                        </Button>
                    )
                },
                cell: ({ row }) => <span className="font-bold text-primary">{row.getValue('blood_type') || '-'}</span>,
                filterFn: 'equals',
            },
            {
                accessorKey: 'sex',
                header: 'Sex',
                cell: ({ row }) => row.getValue('sex') || '-',
            },
            {
                accessorKey: 'address',
                header: 'Address',
                cell: ({ row }) => row.getValue('address') || '-',
            },
            {
                accessorKey: 'id_card_number',
                header: 'ID Card',
                cell: ({ row }) => row.getValue('id_card_number') || '-',
            },
            {
                accessorKey: 'last_donation_date',
                header: 'Last Donation',
                cell: ({ row }) => {
                    const date = row.getValue('last_donation_date')
                    if (!date) return <span className="text-muted-foreground">-</span>
                    return <span>{format(new Date(date), 'dd-MM-yyyy')}</span>
                }
            },
            {
                id: 'next_eligible',
                header: 'Next Eligible',
                cell: ({ row }) => {
                    const dateStr = row.getValue('last_donation_date')
                    const bloodType = row.getValue('blood_type')

                    if (!bloodType) return <span className="text-orange-500 font-bold text-xs">Profile Incomplete</span>
                    if (!dateStr) return <span className="text-green-600 font-bold text-xs">Available Now</span>

                    const lastDate = new Date(dateStr)
                    const nextDate = addMonths(lastDate, 3)
                    const today = new Date()

                    const isEligible = today >= nextDate

                    return (
                        <div className="flex flex-col">
                            <span className={isEligible ? "text-green-600 font-bold" : "text-destructive"}>
                                {format(nextDate, 'dd-MM-yyyy')}
                            </span>
                            {isEligible && <span className="text-[10px] text-green-600 uppercase">Eligible</span>}
                        </div>
                    )
                }
            },
            {
                accessorKey: 'role',
                header: 'Role',
                cell: ({ row }) => (
                    <Badge variant={row.getValue('role') === 'admin' ? "default" : "secondary"}>
                        {row.getValue('role') || 'user'}
                    </Badge>
                ),
            },
            {
                accessorKey: 'status',
                header: 'Status',
                cell: ({ row }) => (
                    <Badge variant={row.getValue('status') === 'active' ? "outline" : "destructive"}>
                        {row.getValue('status') || 'active'}
                    </Badge>
                ),
            },
            {
                id: 'actions',
                cell: ({ row }) => {
                    const user = row.original

                    // Logic: Check Eligibility
                    let isEligible = true
                    let reason = ""

                    if (!user.blood_type) {
                        isEligible = false
                        reason = "No Blood Type"
                    } else if (user.last_donation_date) {
                        const lastDate = new Date(user.last_donation_date)
                        const nextDate = addMonths(lastDate, 3)
                        if (new Date() < nextDate) {
                            isEligible = false
                            reason = "Not Eligible"
                        }
                    }

                    if (!isEligible) {
                        return (
                            <Button
                                size="sm"
                                variant="ghost"
                                disabled
                                className="h-8 px-2 text-[10px] font-medium text-muted-foreground bg-muted/50 w-auto whitespace-nowrap"
                            >
                                {reason}
                            </Button>
                        )
                    }

                    return (
                        <Button
                            size="sm"
                            variant="outline"
                            className="h-8 w-8 p-0 border-red-200 hover:bg-red-50 hover:text-red-600"
                            onClick={(e) => openDonationModal(e, user)}
                            title="Mark as Donated"
                        >
                            <Droplet className="h-4 w-4 text-red-500 fill-red-500" />
                        </Button>
                    )
                }
            },
        ],
        []
    )

    const [columnFilters, setColumnFilters] = useState([])
    const [globalFilter, setGlobalFilter] = useState('')

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        onSortingChange: setSorting,
        onColumnFiltersChange: setColumnFilters,
        onGlobalFilterChange: setGlobalFilter,
        state: {
            sorting,
            columnFilters,
            globalFilter,
        },
    })

    if (loading) return <div className="text-muted-foreground animate-pulse">Loading users...</div>

    return (
        <div className="space-y-4">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4 bg-muted/50 p-4 rounded-xl border">
                <h2 className="text-lg font-semibold self-start md:self-center">All Users</h2>
                <div className="flex-1 w-full md:w-auto flex justify-center px-0 md:px-4">
                    <div className="relative w-full md:max-w-sm">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search by name or phone..."
                            value={globalFilter ?? ''}
                            onChange={(e) => setGlobalFilter(e.target.value)}
                            className="pl-8"
                        />
                    </div>
                </div>
                <div className="flex flex-col md:flex-row items-center gap-2 w-full md:w-auto">
                    <Button
                        onClick={() => {
                            setSelectedUser({})
                            setIsModalOpen(true)
                        }}
                        className="w-full md:w-auto"
                    >
                        <Plus className="mr-2 h-4 w-4" />
                        Add User
                    </Button>
                    {/* Shadcn currently lacks a Select component in my manual install list, using native for now but styled */}
                    <select
                        value={(table.getColumn('blood_type')?.getFilterValue() ?? '')}
                        onChange={(e) => table.getColumn('blood_type')?.setFilterValue(e.target.value)}
                        className="w-full md:w-auto bg-background border border-input text-foreground text-sm rounded-md focus:ring-ring focus:border-ring block p-2.5 outline-none h-10"
                    >
                        <option value="">All Blood Types</option>
                        {['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'].map((type) => (
                            <option key={type} value={type}>{type}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Desktop View: Table */}
            <div className="rounded-md border hidden md:block">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id}>
                                {headerGroup.headers.map((header) => (
                                    <TableHead key={header.id}>
                                        {header.isPlaceholder
                                            ? null
                                            : flexRender(
                                                header.column.columnDef.header,
                                                header.getContext()
                                            )}
                                    </TableHead>
                                ))}
                            </TableRow>
                        ))}
                    </TableHeader>
                    <TableBody>
                        {table.getRowModel().rows?.length ? (
                            table.getRowModel().rows.map((row) => (
                                <TableRow
                                    key={row.id}
                                    data-state={row.getIsSelected() && "selected"}
                                    onClick={() => handleRowClick(row.original)}
                                    className={`cursor-pointer ${row.original.status === 'banned' ? 'bg-destructive/10 hover:bg-destructive/20' : ''}`}
                                >
                                    {row.getVisibleCells().map((cell) => (
                                        <TableCell key={cell.id} className="py-2">
                                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell
                                    colSpan={columns.length}
                                    className="h-24 text-center"
                                >
                                    No results.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Mobile View: Cards */}
            <div className="grid grid-cols-1 gap-4 md:hidden">
                {table.getRowModel().rows?.length ? (
                    table.getRowModel().rows.map((row) => {
                        const user = row.original
                        return (
                            <Card key={row.id} className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => handleRowClick(user)}>
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <div className="flex flex-col">
                                        <CardTitle className="text-base font-bold">{user.full_name}</CardTitle>
                                        <CardDescription className="text-xs">{user.role || 'user'}</CardDescription>
                                    </div>
                                    <Badge variant="outline" className="text-lg font-bold px-2 py-1 bg-red-50 text-red-600 border-red-100">
                                        {user.blood_type || '?'}
                                    </Badge>
                                </CardHeader>
                                <CardContent className="grid gap-2 text-sm">
                                    <div className="flex items-center text-muted-foreground">
                                        <Phone className="mr-2 h-3 w-3" />
                                        {user.phone_number}
                                    </div>
                                    <div className="flex items-center text-muted-foreground">
                                        <CreditCard className="mr-2 h-3 w-3" />
                                        ID: {user.id_card_number || '-'}
                                    </div>
                                    {user.status === 'banned' && (
                                        <Badge variant="destructive" className="w-fit">Banned</Badge>
                                    )}
                                </CardContent>
                                <CardFooter className="pt-2 flex justify-between items-center border-t bg-muted/20">
                                    <div className="w-full">
                                        {user.blood_type && (new Date() > addMonths(new Date(user.last_donation_date || 0), 3)) ? (
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                className="w-full border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 hover:border-red-300 transition-colors"
                                                onClick={(e) => openDonationModal(e, user)}
                                            >
                                                <Droplet className="mr-2 h-4 w-4 fill-current" />
                                                Mark as Donated
                                            </Button>
                                        ) : (
                                            <Badge variant="outline" className="text-muted-foreground bg-muted font-normal w-full justify-center">
                                                {user.last_donation_date ? `Eligible: ${format(addMonths(new Date(user.last_donation_date), 3), 'dd-MMM')}` : 'Profile Incomplete'}
                                            </Badge>
                                        )}
                                    </div>
                                </CardFooter>
                            </Card>
                        )
                    })
                ) : (
                    <div className="text-center p-8 text-muted-foreground bg-muted/20 rounded-lg">
                        No results found.
                    </div>
                )}
            </div>

            {
                isModalOpen && (
                    <EditUserModal
                        user={selectedUser}
                        onClose={() => setIsModalOpen(false)}
                        onUpdate={handleUpdate}
                    />
                )
            }

            {/* Donation Confirmation Modal */}
            <Dialog open={isDonationOpen} onOpenChange={setIsDonationOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle>Confirm Donation</DialogTitle>
                        <DialogDescription>
                            Mark <b>{donationUser?.full_name}</b> as having donated blood.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="flex flex-col space-y-2">
                            <CustomDatePicker
                                selected={donationDate}
                                onSelect={setDonationDate}
                            />
                        </div>

                        <div className="rounded-md bg-muted p-3 text-sm">
                            <p className="font-medium">Next Eligible Date:</p>
                            <p className="text-green-600 font-bold text-lg">
                                {donationDate ? format(addMonths(donationDate, 3), 'PPP') : '-'}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">
                                (Calculated as +3 months from selected date)
                            </p>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsDonationOpen(false)}>Cancel</Button>
                        <Button onClick={confirmDonation} className="bg-red-600 hover:bg-red-700 text-white">
                            <Droplet className="mr-2 h-4 w-4" />
                            Confirm Donation
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div >
    )
}
