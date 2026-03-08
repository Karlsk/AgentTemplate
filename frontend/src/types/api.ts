export interface ApiResponse<T> {
    code: number
    data: T
    msg: string | null
}

export interface PageResult<T> {
    items: T[]
    total: number
}
