import http from '@/lib/axios'
import type {
    McpServer,
    McpServerGridItem,
    McpServerCreatePayload,
    McpServerUpdatePayload,
    ToolInfo,
    ToolCallRequest,
    ToolCallResponse,
} from '@/types/mcpServer'

const mcpServerService = {
    async listServers(): Promise<McpServerGridItem[]> {
        return http.get('/system/mcp-server/servers')
    },

    async getServerById(id: number): Promise<McpServer> {
        return http.get(`/system/mcp-server/servers/${id}`)
    },

    async createServer(payload: McpServerCreatePayload): Promise<McpServer> {
        return http.post('/system/mcp-server/servers', payload)
    },

    async updateServer(payload: McpServerUpdatePayload): Promise<McpServer> {
        return http.put('/system/mcp-server/servers', payload)
    },

    async deleteServer(id: number): Promise<McpServer> {
        return http.delete(`/system/mcp-server/servers/${id}`)
    },

    async getServerTools(serverId: number): Promise<ToolInfo[]> {
        return http.get(`/system/mcp-server/servers/${serverId}/tools`)
    },

    async callTool(serverId: number, request: ToolCallRequest): Promise<ToolCallResponse> {
        return http.post(`/system/mcp-server/servers/${serverId}/tools/call`, request)
    },
}

export default mcpServerService
