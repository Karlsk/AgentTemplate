export interface Token {
    access_token: string
    token_type: string
    expires_at: string
}

export interface UserInfo {
    id: number
    email: string
    oid: number
    status: number
}

export interface LoginRequest {
    email: string
    password: string
}

export interface LoginResponse {
    access_token: string
    token_type: string
    expires_at: string
}

export interface JwtPayload {
    sub: string
    exp: number
    iat: number
    jti: string
    user: UserInfo
}

export interface RegisterRequest {
    email: string
    password: string
    oid: number
    status?: number
    oid_list?: number[]
}

export interface SessionResponse {
    session_id: string
    name: string
    token: Token
}
