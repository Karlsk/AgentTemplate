export enum Supplier {
    OpenAI = 1,
    Azure = 2,
    Google = 3,
}

export const SupplierLabels: Record<Supplier, string> = {
    [Supplier.OpenAI]: 'OpenAI',
    [Supplier.Azure]: 'Azure',
    [Supplier.Google]: 'Google',
}

export enum Protocol {
    OpenAISdk = 1,
    VllmSdk = 2,
}

export const ProtocolLabels: Record<Protocol, string> = {
    [Protocol.OpenAISdk]: 'OpenAI SDK',
    [Protocol.VllmSdk]: 'vLLM SDK',
}

export interface AiModelConfigItem {
    key: string
    val: unknown
    name: string
}

export interface AiModel {
    id: number
    name: string
    base_model: string
    supplier: Supplier
    protocol: Protocol
    api_key?: string
    api_domain: string
    default_model: boolean
    backup_model: boolean
    llm_type: string
    config?: string
    status: number
    created_at?: string
    updated_at?: string
}

export interface AiModelCreatePayload {
    name: string
    base_model: string
    supplier: number
    protocol: number
    api_domain: string
    api_key: string
    default_model: boolean
    backup_model: boolean
    llm_type: string
    config_list: AiModelConfigItem[]
}

export interface AiModelUpdatePayload extends AiModelCreatePayload {
    id: number
}
