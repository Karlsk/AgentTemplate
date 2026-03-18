import http from '@/lib/axios'
import type {
    DbConfig,
    DbConfigListItem,
    DbConfigCreatePayload,
    DbConfigUpdatePayload,
    DbConfigTestPayload,
    DbConfigTestResponse,
    NL2SQLInstance,
    NL2SQLInstanceListItem,
    NL2SQLInstanceCreatePayload,
    NL2SQLInstanceUpdatePayload,
    DiscoverTableItem,
    DiscoverTablesResponse,
    DeleteSchemaTableResponse,
    SchemaSyncResponse,
    SchemaTableInfo,
    TrainingData,
    TrainingDataListResponse,
    AddDDLPayload,
    AddQuestionSQLPayload,
    AddDocumentationPayload,
    NL2SQLSearchRequest,
    NL2SQLSearchResponse,
    UpdateSchemaTablePayload,
} from '@/types/nl2sql'

const nl2sqlService = {
    // ==================== DB Config ====================

    async listDbConfigs(keyword?: string): Promise<DbConfigListItem[]> {
        const params = keyword ? { keyword } : {}
        return http.get('/nl2sql/db-config', { params })
    },

    async getDbConfig(id: number): Promise<DbConfig> {
        return http.get(`/nl2sql/db-config/${id}`)
    },

    async createDbConfig(payload: DbConfigCreatePayload): Promise<DbConfig> {
        return http.post('/nl2sql/db-config', payload)
    },

    async updateDbConfig(payload: DbConfigUpdatePayload): Promise<DbConfig> {
        return http.put('/nl2sql/db-config', payload)
    },

    async deleteDbConfig(id: number): Promise<void> {
        return http.delete(`/nl2sql/db-config/${id}`)
    },

    async testDbConnection(payload: DbConfigTestPayload): Promise<DbConfigTestResponse> {
        return http.post('/nl2sql/db-config/test', payload)
    },

    async testDbConfigById(id: number): Promise<DbConfigTestResponse> {
        return http.post(`/nl2sql/db-config/${id}/test`)
    },

    // ==================== NL2SQL Instance ====================

    async listInstances(keyword?: string): Promise<NL2SQLInstanceListItem[]> {
        const params = keyword ? { keyword } : {}
        return http.get('/nl2sql/instance', { params })
    },

    async getInstance(id: number): Promise<NL2SQLInstance> {
        return http.get(`/nl2sql/instance/${id}`)
    },

    async createInstance(payload: NL2SQLInstanceCreatePayload): Promise<NL2SQLInstance> {
        return http.post('/nl2sql/instance', payload)
    },

    async updateInstance(payload: NL2SQLInstanceUpdatePayload): Promise<NL2SQLInstance> {
        return http.put('/nl2sql/instance', payload)
    },

    async deleteInstance(id: number): Promise<void> {
        return http.delete(`/nl2sql/instance/${id}`)
    },

    // ==================== Schema ====================

    async discoverTables(instanceId: number): Promise<DiscoverTablesResponse> {
        return http.get(`/nl2sql/instance/${instanceId}/discover-tables`)
    },

    async syncSchema(instanceId: number, tableNames?: string[]): Promise<SchemaSyncResponse> {
        const body = tableNames ? { table_names: tableNames } : undefined
        return http.post(`/nl2sql/instance/${instanceId}/sync-schema`, body)
    },

    async getSchemaTable(instanceId: number): Promise<SchemaTableInfo[]> {
        return http.get(`/nl2sql/instance/${instanceId}/schema`)
    },

    async discoverTablesByConfig(configId: number): Promise<DiscoverTableItem[]> {
        return http.get(`/nl2sql/db-config/${configId}/discover-tables`)
    },

    async updateSchemaTable(
        instanceId: number,
        tableName: string,
        payload: UpdateSchemaTablePayload
    ): Promise<SchemaTableInfo> {
        return http.put(`/nl2sql/instance/${instanceId}/schema-table/${tableName}`, payload)
    },

    async deleteSchemaTable(
        instanceId: number,
        tableName: string
    ): Promise<DeleteSchemaTableResponse> {
        return http.delete(`/nl2sql/instance/${instanceId}/schema-table/${tableName}`)
    },

    // ==================== Training Data ====================

    async addDDL(instanceId: number, payload: AddDDLPayload): Promise<TrainingData> {
        return http.post(`/nl2sql/instance/${instanceId}/ddl`, payload)
    },

    async addQuestionSQL(instanceId: number, payload: AddQuestionSQLPayload): Promise<TrainingData> {
        return http.post(`/nl2sql/instance/${instanceId}/sql`, payload)
    },

    async addDocumentation(instanceId: number, payload: AddDocumentationPayload): Promise<TrainingData> {
        return http.post(`/nl2sql/instance/${instanceId}/doc`, payload)
    },

    async deleteTrainingData(instanceId: number, trainingDataId: number): Promise<void> {
        return http.delete(`/nl2sql/instance/${instanceId}/training-data/${trainingDataId}`)
    },

    async listTrainingData(
        instanceId: number,
        dataType?: 'ddl' | 'sql' | 'doc',
        offset = 0,
        limit = 50
    ): Promise<TrainingDataListResponse> {
        const params: Record<string, unknown> = { offset, limit }
        if (dataType) params.data_type = dataType
        return http.get(`/nl2sql/instance/${instanceId}/training-data`, { params })
    },

    // ==================== Search ====================

    async search(request: NL2SQLSearchRequest): Promise<NL2SQLSearchResponse> {
        return http.post('/nl2sql/search', request)
    },
}

export default nl2sqlService
