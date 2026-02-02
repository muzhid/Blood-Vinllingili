import {
    useReactTable,
    getCoreRowModel,
    flexRender,
} from '@tanstack/react-table'
import { useMemo } from 'react'
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"

export function CommandTable() {
    const data = useMemo(() => [
        {
            command: '/start',
            description: 'Start the bot. Shows welcome menu for Seekers/Donors. Checks registration status.',
            example: '/start',
            context: 'Private Chat'
        },
        {
            command: '(Share Contact)',
            description: 'Register as a new donor. Button available in /start menu.',
            example: '📎 > Contact',
            context: 'Private Chat'
        },
        {
            command: 'Welcome Back!',
            description: 'Main Menu (Keyboard). Opens the Blood Request & Profile menu.',
            example: 'Button Click',
            context: 'Private Chat'
        },
        {
            command: '[Photo Upload]',
            description: 'Admin Feature: Upload a Maldives ID Card image to auto-register or update a user. Supports OCR.',
            example: '(Upload Image)',
            context: 'Admin Group'
        },
        {
            command: '/admin_access',
            description: 'Generate temporary credentials for Admin Dashboard login.',
            example: '/admin_access',
            context: 'Admin Group'
        },
        {
            command: '/reset_password',
            description: 'Reset the Admin Dashboard password.',
            example: '/reset_password',
            context: 'Admin Group'
        },
        {
            command: '/update',
            description: 'Open interactive Profile Dashboard.',
            example: '/update',
            context: 'Private Chat'
        },
        {
            command: '/donor',
            description: 'Resume profile completion or check stats.',
            example: '/donor',
            context: 'Private Chat'
        },
        {
            command: '/profile',
            description: 'View or Edit Profile details.',
            example: '/profile',
            context: 'Private Chat'
        }
    ], [])

    const columns = useMemo(
        () => [
            {
                accessorKey: 'command',
                header: 'Command',
                cell: ({ row }) => <code className="bg-muted px-2 py-1 rounded text-red-500 font-mono text-sm">{row.getValue('command')}</code>,
            },
            {
                accessorKey: 'description',
                header: 'Description',
            },
            {
                accessorKey: 'example',
                header: 'Example Usage',
                cell: ({ row }) => <span className="font-mono text-xs text-muted-foreground">{row.getValue('example')}</span>,
            },
            {
                accessorKey: 'context',
                header: 'Context',
                cell: ({ row }) => (
                    <Badge variant={row.getValue('context').includes('Group') ? "default" : "secondary"}>
                        {row.getValue('context')}
                    </Badge>
                )
            }
        ],
        []
    )

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
    })

    return (
        <Card>
            <CardHeader>
                <CardTitle>Bot Command Reference</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="rounded-md border overflow-x-auto">
                    <Table>
                        <TableHeader>
                                    ))}
                        </TableRow>
                            ))}
                    </TableHeader>
                    <TableBody>
                        {table.getRowModel().rows.map((row) => (
                            <TableRow key={row.id}>
                                {row.getVisibleCells().map((cell) => (
                                    <TableCell key={cell.id} className={`py-2 md:py-4 ${cell.column.id === 'description' ? 'whitespace-normal min-w-[300px]' : cell.column.id === 'example' ? 'whitespace-normal min-w-[150px]' : 'whitespace-nowrap'}`}>
                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                    </TableCell>
                                ))}
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </CardContent>
        </Card >
    )
}
