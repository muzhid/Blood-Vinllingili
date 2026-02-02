import { useState, useEffect, useMemo } from 'react'
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    flexRender,
} from '@tanstack/react-table'
import { ArrowUpDown } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"

export function RequestTable() {
    const [data, setData] = useState([])
    const [sorting, setSorting] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchRequests()
    }, [])

    const fetchRequests = async () => {
        try {
            const res = await fetch('/api/requests', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
            })
            const requests = await res.json()
            if (!res.ok) throw new Error("Failed to fetch requests")

            setData(requests)
        } catch (error) {
            console.error('Error fetching requests:', error)
        } finally {
            setLoading(false)
        }
    }

    const columns = useMemo(
        () => [
            {
                accessorKey: 'blood_type',
                header: ({ column }) => {
                    return (
                        <Button
                            variant="ghost"
                            className="p-0 hover:bg-transparent"
                            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                        >
                            Blood Type
                            <ArrowUpDown className="ml-2 h-4 w-4" />
                        </Button>
                    )
                },
                cell: ({ row }) => <span className="font-bold text-primary">{row.getValue('blood_type') || '-'}</span>,
            },
            {
                accessorKey: 'location',
                header: 'Location',
                cell: ({ row }) => row.getValue('location') || '-',
            },
            {
                accessorKey: 'urgency',
                header: 'Urgency',
                cell: ({ row }) => {
                    const urgency = row.getValue('urgency')
                    return (
                        <Badge variant={urgency === 'High' ? "destructive" : "secondary"}>
                            {urgency || 'Normal'}
                        </Badge>
                    )
                },
            },
            {
                accessorKey: 'requester.full_name', // Accessing nested data
                header: 'Requester',
                cell: ({ row }) => row.original.requester?.full_name || '-',
            },
            {
                accessorKey: 'requester.phone_number',
                header: 'Phone',
                cell: ({ row }) => row.original.requester?.phone_number || '-',
            },
            {
                accessorKey: 'donors_found',
                header: 'Donors',
                cell: ({ row }) => row.getValue('donors_found') || 0,
            },
            {
                accessorKey: 'is_active',
                header: 'Status',
                cell: ({ row }) => (
                    <Badge variant={row.getValue('is_active') ? "outline" : "secondary"}>
                        {row.getValue('is_active') ? 'Active' : 'Closed'}
                    </Badge>
                ),
            },
            {
                accessorKey: 'created_at',
                header: 'Time',
                cell: ({ row }) => new Date(row.getValue('created_at')).toLocaleString(),
            },
        ],
        []
    )

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        onSortingChange: setSorting,
        state: {
            sorting,
        },
    })

    if (loading) return <div className="text-muted-foreground animate-pulse">Loading requests...</div>

    return (
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
                                className="hover:bg-muted/50 transition-colors"
                            >
                                {row.getVisibleCells().map((cell) => (
                                    <TableCell key={cell.id}>
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
                                No requests found.
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </div>
    )
}
