/**
 * API Client for DSE Value Investor backend
 */

// Use environment variable in production, fallback to localhost for development
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ApiResponse<T> {
    data?: T;
    error?: string;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            return { error: errorData.detail || `HTTP ${response.status}` };
        }

        const data = await response.json();
        return { data };
    } catch (err) {
        return { error: err instanceof Error ? err.message : 'Network error' };
    }
}

// Portfolio API
export const portfolio = {
    get: () => request<PortfolioSummary>('/portfolio/'),
    add: (holding: HoldingCreate) => request<HoldingResponse>('/portfolio/', {
        method: 'POST',
        body: JSON.stringify(holding),
    }),
    update: (symbol: string, data: HoldingUpdate) => request<HoldingResponse>(`/portfolio/${symbol}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    }),
    delete: (symbol: string) => request<{message: string}>(`/portfolio/${symbol}`, {
        method: 'DELETE',
    }),
    seed: () => request<{message: string, added: string[]}>('/portfolio/seed', {
        method: 'POST',
    }),
};

// Stocks API
export const stocks = {
    getPrices: (limit?: number) => request<StockPrice[]>(`/stocks/prices${limit ? `?limit=${limit}` : ''}`),
    getPrice: (symbol: string) => request<StockPrice>(`/stocks/${symbol}`),
    getHistory: (symbol: string, startDate?: string, endDate?: string) => {
        const params = new URLSearchParams();
        if (startDate) params.set('start_date', startDate);
        if (endDate) params.set('end_date', endDate);
        const query = params.toString() ? `?${params.toString()}` : '';
        return request<{symbol: string, count: number, data: any[]}>(`/stocks/${symbol}/history${query}`);
    },
    getFundamentals: (symbol: string) => request<FundamentalsResponse>(`/stocks/${symbol}/fundamentals`),
    refreshFundamentals: (symbol: string) => request<{message: string, years_updated: number}>(`/stocks/${symbol}/refresh-fundamentals`, {
        method: 'POST',
    }),
};

// Calculator API
export const calculator = {
    stickerPrice: (data: StickerPriceRequest) => request<StickerPriceResponse>('/calculate/sticker-price', {
        method: 'POST',
        body: JSON.stringify(data),
    }),
    getStickerPrice: (symbol: string) => request<StickerPriceResponse>(`/calculate/sticker-price/${symbol}`),
    getBigFive: (symbol: string) => request<BigFiveResponse>(`/calculate/big-five/${symbol}`),
    getFourMs: (data: FourMsRequest) => request<FourMsResponse>('/calculate/four-ms', {
        method: 'POST',
        body: JSON.stringify(data),
    }),
    getFullAnalysis: (symbol: string) => request<FullAnalysisResponse>(`/calculate/analysis/${symbol}`),
};

// Types
export interface PortfolioSummary {
    total_invested: number;
    current_value: number;
    total_profit_loss: number;
    total_profit_loss_pct: number;
    holdings_count: number;
    holdings: HoldingResponse[];
}

export interface HoldingResponse {
    id: number;
    stock_symbol: string;
    shares: number;
    avg_cost: number;
    current_price?: number;
    current_value?: number;
    total_cost?: number;
    profit_loss?: number;
    profit_loss_pct?: number;
    notes?: string;
}

export interface HoldingCreate {
    stock_symbol: string;
    shares: number;
    avg_cost: number;
    notes?: string;
}

export interface HoldingUpdate {
    shares?: number;
    avg_cost?: number;
    notes?: string;
}

export interface StockPrice {
    symbol: string;
    ltp?: number;
    high?: number;
    low?: number;
    open?: number;
    close?: number;
    volume?: number;
    change?: number;
    change_pct?: number;
}

export interface FundamentalsResponse {
    symbol: string;
    source: string;
    company_data?: Record<string, any>;
    data: FinancialRecord[];
}

export interface FinancialRecord {
    year: number;
    revenue?: number;
    eps?: number;
    total_equity?: number;
    operating_cash_flow?: number;
    free_cash_flow?: number;
    roe?: number;
    debt_to_equity?: number;
}

export interface StickerPriceRequest {
    symbol?: string;
    current_eps?: number;
    eps_growth_rate?: number;
    historical_pe?: number;
    current_price?: number;
}

export interface StickerPriceResponse {
    symbol?: string;
    current_eps: number;
    eps_growth_rate: number;
    used_growth_rate: number;
    historical_pe: number;
    future_eps: number;
    future_pe: number;
    future_price: number;
    sticker_price: number;
    margin_of_safety: number;
    current_price?: number;
    discount_to_sticker?: number;
    discount_to_mos?: number;
    recommendation?: string;
}

export interface BigFiveResponse {
    symbol: string;
    score: number;
    total: number;
    passes: boolean;
    grade: string;
    revenue: GrowthMetric;
    eps: GrowthMetric;
    equity: GrowthMetric;
    operating_cf: GrowthMetric;
    free_cf: GrowthMetric;
}

export interface GrowthMetric {
    name: string;
    values: (number | null)[];
    years: number;
    cagr_pct: number;
    passes: boolean;
    status: string;
}

export interface FourMsRequest {
    symbol: string;
    meaning_score?: number;
    meaning_notes?: string;
    market_position?: string;
    insider_ownership?: number;
    capital_allocation?: string;
}

export interface FourMsResponse {
    meaning_score?: number;
    meaning_notes?: string;
    moat: MoatScore;
    management: ManagementScore;
    mos: MOSScore;
    overall_score: number;
    overall_grade: string;
    recommendation: string;
    summary: string[];
}

export interface MoatScore {
    roe_avg: number;
    roe_consistent: boolean;
    gross_margin_avg: number;
    gross_margin_stable: boolean;
    market_position?: string;
    score: number;
    grade: string;
    notes: string[];
}

export interface ManagementScore {
    roe_above_15: boolean;
    debt_to_equity?: number;
    debt_reasonable: boolean;
    insider_ownership?: number;
    capital_allocation?: string;
    score: number;
    grade: string;
    notes: string[];
}

export interface MOSScore {
    current_price: number;
    sticker_price: number;
    margin_of_safety: number;
    discount_pct: number;
    score: number;
    grade: string;
    recommendation: string;
    notes: string[];
}

export interface FullAnalysisResponse {
    symbol: string;
    current_price?: number;
    sticker_price?: StickerPriceResponse;
    big_five: BigFiveResponse;
    four_ms: FourMsResponse;
    data_years: number;
    recommendation: string;
}
