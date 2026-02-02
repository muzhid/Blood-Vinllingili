import { useState, useEffect, useMemo } from 'react'
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    getFilteredRowModel,
    flexRender,
} from '@tanstack/react-table'
import { ArrowUpDown, Plus, Search } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"

import { EditUserModal } from './EditUserModal'

export function UserTable() {
    const [data, setData] = useState([])
    const [sorting, setSorting] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedUser, setSelectedUser] = useState(null)
    const [isModalOpen, setIsModalOpen] = useState(false)

    useEffect(() => {
        fetchUsers()
    }, [])

    const fetchUsers = async () => {
        try {
            const res = await fetch('/api/users')
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
                cell: ({ row }) => row.getValue('last_donation_date') || '-',
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

            <div className="rounded-md border">
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

            {isModalOpen && (
                <EditUserModal
                    user={selectedUser}
                    onClose={() => setIsModalOpen(false)}
                    onUpdate={handleUpdate}
                />
            )}
        </div>
    )
}
