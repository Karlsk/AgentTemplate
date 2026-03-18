// ==================== DB Config ====================

export interface DbConfig {
    id: number
    workspace_id: number
    name: string
    db_type: string
    host: string
    port: number
    database_name: string
    schema_name: string | null
    username: string
    extra_params: string | null
    status: number
    created_at: string
}

export interface DbConfigListItem {
    id: number
    name: string
    db_type: string
    host: string
    port: number
    database_name: string
    status: number
    created_at: string
}

export interface DbConfigCreatePayload {
    name: string
    db_type: string
    host: string
    port: number
    database_name: string
    schema_name?: string
    username: string
    password: string
    extra_params?: string
}

export interface DbConfigUpdatePayload {
    id: number
    name?: string
    db_type?: string
    host?: string
    port?: number
    database_name?: string
    schema_name?: string
    username?: string
    password?: string
    extra_params?: string
}

export interface DbConfigTestPayload {
    db_type: string
    host: string
    port: number
    database_name: string
    schema_name?: string
    username: string
    password: string
    extra_params?: string
}

export interface DbConfigTestResponse {
    success: boolean
    message: string
    latency_ms: number | null
}

// ==================== NL2SQL Instance ====================

export interface NL2SQLInstance {
    id: number
    workspace_id: number
    name: string
    description: string
    db_config_id: number
    embedding_model_id: number | null
    ddl_mode: string
    ddl_count: number
    sql_count: number
    doc_count: number
    status: number
    created_at: string
}

export interface NL2SQLInstanceListItem {
    id: number
    name: string
    description: string
    db_config_id: number
    ddl_mode: string
    ddl_count: number
    sql_count: number
    doc_count: number
    status: number
    created_at: string
}

export interface NL2SQLInstanceCreatePayload {
    name: string
    description?: string
    db_config_id: number
    embedding_model_id?: number
    ddl_mode?: string
    table_names?: string[]
}

export interface NL2SQLInstanceUpdatePayload {
    id: number
    name?: string
    description?: string
    embedding_model_id?: number
    ddl_mode?: string
}

export interface SchemaSyncResponse {
    instance_id: number
    tables_synced: number
    columns_synced: number
    ddl_generated: number
}

export interface SchemaSyncRequest {
    table_names?: string[]
}

export interface DiscoverTableItem {
    table_name: string
    table_comment: string | null
    synced: boolean
}

export interface DiscoverTablesResponse {
    instance_id: number
    tables: DiscoverTableItem[]
    total: number
}

// ==================== Schema ====================

export interface SchemaColumnInfo {
    column_name: string
    column_type: string | null
    column_comment: string | null
    is_primary_key: boolean
    is_nullable: boolean
}

export interface SchemaTableInfo {
    table_schema: string | null
    table_name: string
    table_comment: string | null
    columns: SchemaColumnInfo[]
}

export interface UpdateSchemaColumnItem {
    column_name: string
    column_comment?: string | null
}

export interface UpdateSchemaTablePayload {
    table_comment?: string | null
    columns: UpdateSchemaColumnItem[]
}

export interface DeleteSchemaTableResponse {
    table_name: string
    schema_rows_deleted: number
    training_data_deleted: number
    vectors_deleted: number
}

// ==================== Training Data ====================

export interface TrainingData {
    id: number
    instance_id: number
    data_type: 'ddl' | 'sql' | 'doc'
    content: string
    question: string | null
    sql_text: string | null
    table_name: string | null
    source: string
    status: number
    created_at: string
}

export interface TrainingDataListItem {
    id: number
    data_type: 'ddl' | 'sql' | 'doc'
    content: string
    question: string | null
    sql_text: string | null
    table_name: string | null
    source: string
    status: number
    created_at: string
}

export interface TrainingDataListResponse {
    items: TrainingDataListItem[]
    total: number
    offset: number
    limit: number
}

export interface AddDDLPayload {
    content: string
    table_name?: string
}

export interface AddQuestionSQLPayload {
    question: string
    sql_text: string
}

export interface AddDocumentationPayload {
    content: string
}

// ==================== Search ====================

export interface NL2SQLSearchRequest {
    instance_id: number
    question: string
    top_k_ddl?: number
    top_k_sql?: number
    top_k_doc?: number
}

export interface SimilarSQLResult {
    id: number
    question: string
    sql_text: string
    score: number
}

export interface RelatedDDLResult {
    id: number
    content: string
    table_name: string | null
    score: number
}

export interface RelatedDocResult {
    id: number
    content: string
    score: number
}

export interface NL2SQLSearchResponse {
    question: string
    similar_sqls: SimilarSQLResult[]
    related_ddls: RelatedDDLResult[]
    related_docs: RelatedDocResult[]
}

// ==================== Labels ====================

export const DbTypeLabels: Record<string, string> = {
    mysql: 'MySQL',
    postgresql: 'PostgreSQL',
    oracle: 'Oracle',
    sqlserver: 'SQL Server',
    clickhouse: 'ClickHouse',
    dameng: 'Dameng',
    doris: 'Doris',
    starrocks: 'StarRocks',
    kingbase: 'KingBase',
    redshift: 'Redshift',
    elasticsearch: 'Elasticsearch',
}

export const DbTypeOptions = [
    { label: 'MySQL', value: 'mysql' },
    { label: 'PostgreSQL', value: 'postgresql' },
    { label: 'Oracle', value: 'oracle' },
    { label: 'SQL Server', value: 'sqlserver' },
    { label: 'ClickHouse', value: 'clickhouse' },
    { label: 'Dameng', value: 'dameng' },
    { label: 'Doris', value: 'doris' },
    { label: 'StarRocks', value: 'starrocks' },
    { label: 'KingBase', value: 'kingbase' },
    { label: 'Redshift', value: 'redshift' },
    { label: 'Elasticsearch', value: 'elasticsearch' },
]

export const DbConfigStatusLabels: Record<number, string> = {
    0: 'Unverified',
    1: 'Connected',
    2: 'Failed',
}

export const InstanceStatusLabels: Record<number, string> = {
    0: 'Initializing',
    1: 'Ready',
    2: 'Syncing',
}

export const TrainingDataTypeLabels: Record<string, string> = {
    ddl: 'DDL / Schema',
    sql: 'Question-SQL Pair',
    doc: 'Documentation',
}

export const TrainingDataStatusLabels: Record<number, string> = {
    0: 'Pending',
    1: 'Embedded',
    2: 'Failed',
}

export const DdlModeLabels: Record<string, string> = {
    full: '全量 DDL',
    compact: '精简 DDL',
}

export const DdlModeOptions = [
    { label: '全量 DDL', value: 'full' },
    { label: '精简 DDL', value: 'compact' },
]
