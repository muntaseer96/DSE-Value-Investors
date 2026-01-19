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
    getFourMs: (symbol: string) => request<FourMsResponse>(`/calculate/four-ms/${symbol}`),
    getFullAnalysis: (symbol: string) => request<FullAnalysisResponse>(`/calculate/analysis/${symbol}`),
    // Batch valuation endpoints
    getBatchValuations: () => request<BatchValuationsResponse>('/calculate/batch-valuations'),
    refreshValuations: () => request<RefreshValuationsResponse>('/calculate/refresh-valuations', {
        method: 'POST',
    }),
    getRefreshStatus: () => request<RefreshStatusResponse>('/calculate/refresh-valuations-status'),
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
    sector?: string;  // From sector mapping
    ltp?: number;
    high?: number;
    low?: number;
    open?: number;
    close?: number;
    volume?: number;
    change?: number;
    change_pct?: number;
    // Valuation data (from cached stocks table)
    sticker_price?: number;
    margin_of_safety?: number;
    discount_pct?: number;  // Negative = undervalued, Positive = overvalued
    four_m_score?: number;
    four_m_grade?: string;
    recommendation?: string;
    valuation_status?: 'CALCULABLE' | 'NOT_CALCULABLE' | 'UNKNOWN';
    valuation_note?: string;
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
    status: string;  // CALCULABLE or NOT_CALCULABLE
    note?: string;   // Explanation when not calculable
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

export interface FourMsResponse {
    meaning: MeaningScore;
    moat: MoatScore;
    management: ManagementScore;
    mos: MOSScore;
    overall_score: number;
    overall_grade: string;
    recommendation: string;
    summary: string[];
}

export interface MeaningScore {
    revenue_stability: number;
    earnings_consistency: number;
    net_income_stability: number;
    data_quality: number;
    sector?: string;
    sector_note?: string;
    score: number;
    grade: string;
    notes: string[];
}

export interface MoatScore {
    roe_avg: number;
    roe_consistent: boolean;
    gross_margin_avg: number;
    gross_margin_trend: string;
    operating_margin_avg: number;
    score: number;
    grade: string;
    notes: string[];
    score_breakdown: Record<string, number>;
}

export interface ManagementScore {
    roe_above_15: boolean;
    debt_to_equity?: number;
    debt_reasonable: boolean;
    fcf_to_ni_ratio?: number;
    score: number;
    grade: string;
    notes: string[];
    score_breakdown: Record<string, number>;
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

// Batch Valuation Types
export interface BatchValuationItem {
    symbol: string;
    sticker_price?: number;
    margin_of_safety?: number;
    four_m_score?: number;
    four_m_grade?: string;
    recommendation?: string;
    discount_to_sticker?: number;
    valuation_status: 'CALCULABLE' | 'NOT_CALCULABLE' | 'UNKNOWN';
    valuation_note?: string;
    last_valuation_update?: string;
}

export interface BatchValuationsResponse {
    count: number;
    calculable_count: number;
    not_calculable_count: number;
    last_refresh?: string;
    valuations: BatchValuationItem[];
}

export interface RefreshValuationsResponse {
    status: 'started' | 'already_running';
    message: string;
    total_stocks?: number;
    check_progress_at?: string;
    progress?: {
        current: number;
        total: number;
        current_symbol: string;
    };
}

export interface RefreshStatusResponse {
    running: boolean;
    current: number;
    total: number;
    current_symbol: string;
    success_count: number;
    failed_count: number;
    started_at?: string;
    completed_at?: string;
    progress_percent?: number;
}
