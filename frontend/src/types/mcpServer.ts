export enum McpTransport {
    StreamableHttp = 'streamable_http',
    SSE = 'sse',
    Stdio = 'stdio',
    Gateway = 'gateway',
}

export const McpTransportLabels: Record<McpTransport, string> = {
    [McpTransport.StreamableHttp]: 'Streamable HTTP',
    [McpTransport.SSE]: 'SSE',
    [McpTransport.Stdio]: 'Stdio',
    [McpTransport.Gateway]: 'Gateway',
}

export interface McpServer {
    id: number
    name: string
    url: string
    transport: string
    config?: Record<string, unknown> | null
    created_at?: string
}

export interface McpServerGridItem {
    id: number
    name: string
    url: string
    transport: string
    created_at?: string
}

export interface McpServerCreatePayload {
    name: string
    url: string
    transport: string
    config?: Record<string, unknown> | null
}

export interface McpServerUpdatePayload {
    id: number
    name?: string
    url?: string
    transport?: string
    config?: Record<string, unknown> | null
}

export interface ToolInfo {
    name: string
    description: string
    args_schema?: Record<string, unknown> | null
}

export interface ToolCallRequest {
    tool_name: string
    arguments: Record<string, unknown>
}

export interface ToolCallResponse {
    ok: boolean
    result?: unknown
    error?: string
    elapsed_ms?: number
}
