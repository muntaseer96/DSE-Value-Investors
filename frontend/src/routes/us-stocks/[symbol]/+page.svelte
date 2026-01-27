<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { usStocks, type USFullAnalysisResponse, type BigFiveResponse, type StickerPriceResponse } from '$lib/api/client';

    // Get symbol from URL
    $: symbol = $page.params.symbol?.toUpperCase() || '';

    // Results
    let analysis: USFullAnalysisResponse | null = null;
    let loading = true;
    let error = '';

    onMount(async () => {
        if (symbol) {
            await loadAnalysis();
        }
    });

    async function loadAnalysis() {
        loading = true;
        error = '';

        const result = await usStocks.getAnalysis(symbol);

        if (result.error) {
            error = result.error;
        } else if (result.data) {
            analysis = result.data;
        }

        loading = false;
    }

    function getRecommendationClass(rec: string | undefined): string {
        if (!rec) return '';
        switch (rec) {
            case 'STRONG_BUY': return 'badge-success';
            case 'BUY': return 'badge-info';
            case 'HOLD': return 'badge-warning';
            case 'SELL':
            case 'STRONG_SELL':
            case 'AVOID': return 'badge-danger';
            default: return '';
        }
    }

    function getStatusClass(status: string): string {
        switch (status) {
            case 'STRONG': return 'positive';
            case 'PASS': return 'positive';
            case 'WEAK': return 'neutral';
            case 'FAIL': return 'negative';
            case 'NEGATIVE': return 'negative';
            case 'INCONSISTENT': return 'warning';
            case 'NO_DATA': return 'muted';
            default: return '';
        }
    }

    function formatCagrDisplay(metric: any): string {
        if (metric.cagr_pct === null || metric.cagr_pct === undefined) {
            if (metric.status === 'NEGATIVE') return 'N/A';
            if (metric.status === 'INCONSISTENT') return '~?%';
            if (metric.status === 'NO_DATA') return '-';
            return '-';
        }
        return (metric.cagr_pct > 0 ? '+' : '') + metric.cagr_pct.toFixed(1) + '%';
    }

    function formatCurrency(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    function formatPercent(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        return `${value.toFixed(2)}%`;
    }
</script>

<svelte:head>
    <title>{symbol} Analysis - Stokr</title>
</svelte:head>

<div class="analysis-page">
    <!-- Page Header -->
    <div class="page-header">
        <div class="header-content">
            <div class="header-top">
                <a href="/us-stocks" class="back-link">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M19 12H5M12 19l-7-7 7-7"/>
                    </svg>
                    Back to US Stocks
                </a>
            </div>
            <h1>
                {symbol}
                {#if analysis?.is_sp500}
                    <span class="sp500-tag">S&P 500</span>
                {/if}
            </h1>
            {#if analysis?.name}
                <p class="header-subtitle">{analysis.name}</p>
            {/if}
            <div class="header-tags">
                {#if analysis?.sector}
                    <span class="sector-badge">{analysis.sector}</span>
                {/if}
                <a href="https://finance.yahoo.com/quote/{symbol}/" target="_blank" rel="noopener noreferrer" class="yahoo-link">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                        <polyline points="15 3 21 3 21 9"/>
                        <line x1="10" y1="14" x2="21" y2="3"/>
                    </svg>
                    Yahoo Finance
                </a>
            </div>
        </div>
        {#if analysis?.recommendation}
            <div class="header-badge">
                <span class="badge badge-lg {getRecommendationClass(analysis.recommendation)}">
                    {analysis.recommendation.replace('_', ' ')}
                </span>
            </div>
        {/if}
    </div>

    {#if loading}
        <div class="loading">
            <div class="spinner"></div>
            <p>Analyzing {symbol}...</p>
        </div>
    {:else if error}
        <div class="error-card animate-fadeIn">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <h3>Unable to Analyze</h3>
            <p>{error}</p>
            <a href="/us-stocks" class="btn btn-secondary">Back to US Stocks</a>
        </div>
    {:else if analysis}
        <!-- Sticker Price Results -->
        {#if analysis.sticker_price}
            <div class="card result-card animate-fadeIn stagger-1">
                <div class="card-header">
                    <h2>Sticker Price Analysis</h2>
                    {#if analysis.sticker_price.status === 'CALCULABLE'}
                        <span class="data-years">{analysis.data_years} years of data</span>
                    {/if}
                </div>

                {#if analysis.sticker_price.status === 'NOT_CALCULABLE'}
                    <div class="not-calculable-box">
                        <div class="not-calculable-icon">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"/>
                                <line x1="12" y1="8" x2="12" y2="12"/>
                                <line x1="12" y1="16" x2="12.01" y2="16"/>
                            </svg>
                        </div>
                        <div class="not-calculable-title">Cannot Calculate Sticker Price</div>
                        <div class="not-calculable-note">{analysis.sticker_price.note}</div>
                        <div class="not-calculable-advice">
                            Phil Town's sticker price formula requires positive, growing earnings.
                            This stock may still be investable but requires different analysis methods.
                        </div>
                    </div>
                {:else}
                    <div class="price-comparison">
                        <div class="price-box mos-box">
                            <div class="price-icon">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                                </svg>
                            </div>
                            <div class="price-label">Margin of Safety</div>
                            <div class="price-value">{formatCurrency(analysis.sticker_price.margin_of_safety)}</div>
                            <div class="price-note">Buy below this price</div>
                        </div>
                        <div class="price-box sticker-box">
                            <div class="price-icon">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"/>
                                    <line x1="12" y1="8" x2="12" y2="16"/>
                                    <line x1="8" y1="12" x2="16" y2="12"/>
                                </svg>
                            </div>
                            <div class="price-label">Sticker Price</div>
                            <div class="price-value">{formatCurrency(analysis.sticker_price.sticker_price)}</div>
                            <div class="price-note">Intrinsic value</div>
                        </div>
                        {#if analysis.current_price}
                            <div class="price-box current-box">
                                <div class="price-icon">
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
                                        <polyline points="16 7 22 7 22 13"/>
                                    </svg>
                                </div>
                                <div class="price-label">Current Price</div>
                                <div class="price-value">{formatCurrency(analysis.current_price)}</div>
                                {#if analysis.sticker_price.discount_to_sticker}
                                    <div class="price-note {analysis.sticker_price.discount_to_sticker > 0 ? 'positive' : 'negative'}">
                                        {analysis.sticker_price.discount_to_sticker > 0 ? 'Undervalued' : 'Overvalued'} by {Math.abs(analysis.sticker_price.discount_to_sticker).toFixed(1)}%
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        {/if}

        <!-- Big Five Results -->
        {#if analysis.big_five}
            <div class="card result-card mt-3 animate-fadeIn stagger-2">
                <div class="card-header">
                    <h2>Big Five Numbers</h2>
                    <div class="score-display">
                        <span class="score">{analysis.big_five.score}/{analysis.big_five.total}</span>
                        <span class="badge grade-{analysis.big_five.grade}">Grade {analysis.big_five.grade}</span>
                    </div>
                </div>

                <div class="big-five-grid">
                    {#each [analysis.big_five.revenue, analysis.big_five.eps, analysis.big_five.equity, analysis.big_five.operating_cf, analysis.big_five.free_cf] as metric}
                        <div class="metric-card {metric.passes ? 'passing' : 'failing'}">
                            <div class="metric-header">
                                <span class="metric-name">{metric.name}</span>
                                <span class="metric-status badge {metric.passes ? 'badge-success' : 'badge-danger'}">
                                    {metric.status}
                                </span>
                            </div>
                            <div class="metric-cagr {getStatusClass(metric.status)}">
                                {formatCagrDisplay(metric)}
                            </div>
                            <div class="metric-note">
                                {#if metric.note}
                                    {metric.note}
                                {:else if metric.name === 'Book Value' && (metric.status === 'INCONSISTENT' || metric.status === 'NEGATIVE')}
                                    Negative book value (likely from stock buybacks, not losses)
                                {:else}
                                    {metric.years} year{metric.years !== 1 ? 's' : ''} of data
                                {/if}
                            </div>
                        </div>
                    {/each}
                </div>

                <div class="summary-box mt-3 {analysis.big_five.passes ? 'success' : 'danger'}">
                    {#if analysis.big_five.passes}
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                            <polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                        <span>Passes Big Five test ({analysis.big_five.score}/5 metrics above 10%)</span>
                    {:else}
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"/>
                            <line x1="15" y1="9" x2="9" y2="15"/>
                            <line x1="9" y1="9" x2="15" y2="15"/>
                        </svg>
                        <span>Does not pass Big Five test (need at least 3/5 above 10%)</span>
                    {/if}
                </div>
            </div>
        {/if}

        <!-- 4Ms Summary -->
        {#if analysis.four_ms}
            <div class="card result-card mt-3 animate-fadeIn stagger-3">
                <div class="card-header">
                    <h2>4Ms Analysis</h2>
                    <div class="score-display">
                        <span class="score">{analysis.four_ms.overall_score.toFixed(0)}/100</span>
                        <span class="badge grade-{analysis.four_ms.overall_grade}">
                            Grade {analysis.four_ms.overall_grade}
                        </span>
                    </div>
                </div>

                {#if analysis.four_ms.big_five_warning}
                    <div class="warning-banner">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                            <line x1="12" y1="9" x2="12" y2="13"/>
                            <line x1="12" y1="17" x2="12.01" y2="17"/>
                        </svg>
                        <span>Big Five failed - Score penalized by {analysis.four_ms.big_five_penalty} points, recommendation capped at HOLD</span>
                    </div>
                {/if}

                <div class="four-ms-grid">
                    <!-- Meaning Card -->
                    {#if analysis.four_ms.meaning}
                        <div class="ms-card meaning-card">
                            <div class="ms-header">
                                <h4>
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <circle cx="12" cy="12" r="10"/>
                                        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                                        <line x1="12" y1="17" x2="12.01" y2="17"/>
                                    </svg>
                                    Meaning
                                </h4>
                                <span class="badge grade-{analysis.four_ms.meaning.grade}">
                                    {analysis.four_ms.meaning.score.toFixed(0)}
                                </span>
                            </div>
                            <div class="meaning-metrics">
                                <div class="metric-bar">
                                    <span class="metric-label">Revenue Stability</span>
                                    <div class="bar-container">
                                        <div class="bar-fill" style="width: {Math.min(100, analysis.four_ms.meaning.revenue_stability)}%"></div>
                                    </div>
                                    <span class="metric-value">{analysis.four_ms.meaning.revenue_stability.toFixed(0)}%</span>
                                </div>
                                <div class="metric-bar">
                                    <span class="metric-label">Earnings Consistency</span>
                                    <div class="bar-container">
                                        <div class="bar-fill" style="width: {Math.min(100, analysis.four_ms.meaning.earnings_consistency)}%"></div>
                                    </div>
                                    <span class="metric-value">{analysis.four_ms.meaning.earnings_consistency.toFixed(0)}%</span>
                                </div>
                                <div class="metric-bar">
                                    <span class="metric-label">Data Quality</span>
                                    <div class="bar-container">
                                        <div class="bar-fill" style="width: {Math.min(100, analysis.four_ms.meaning.data_quality)}%"></div>
                                    </div>
                                    <span class="metric-value">{analysis.four_ms.meaning.data_quality.toFixed(0)}%</span>
                                </div>
                            </div>
                        </div>
                    {/if}

                    <div class="ms-card">
                        <div class="ms-header">
                            <h4>
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                                </svg>
                                Moat
                            </h4>
                            <span class="badge grade-{analysis.four_ms.moat.grade}">
                                {analysis.four_ms.moat.score.toFixed(0)}
                            </span>
                        </div>
                        <ul class="ms-notes">
                            {#each analysis.four_ms.moat.notes as note}
                                <li>{note}</li>
                            {/each}
                        </ul>
                    </div>

                    <div class="ms-card">
                        <div class="ms-header">
                            <h4>
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                    <circle cx="9" cy="7" r="4"/>
                                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                                </svg>
                                Management
                            </h4>
                            <span class="badge grade-{analysis.four_ms.management.grade}">
                                {analysis.four_ms.management.score.toFixed(0)}
                            </span>
                        </div>
                        <ul class="ms-notes">
                            {#each analysis.four_ms.management.notes as note}
                                <li>{note}</li>
                            {/each}
                        </ul>
                    </div>

                    <div class="ms-card">
                        <div class="ms-header">
                            <h4>
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="12" y1="1" x2="12" y2="23"/>
                                    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                                </svg>
                                Margin of Safety
                            </h4>
                            <span class="badge grade-{analysis.four_ms.mos.grade}">
                                {analysis.four_ms.mos.score.toFixed(0)}
                            </span>
                        </div>
                        <ul class="ms-notes">
                            {#each analysis.four_ms.mos.notes as note}
                                <li>{note}</li>
                            {/each}
                        </ul>
                    </div>
                </div>

                <div class="recommendation-summary mt-3">
                    <h3>Summary</h3>
                    <ul class="summary-list">
                        {#each analysis.four_ms.summary as item}
                            <li>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="9 18 15 12 9 6"/>
                                </svg>
                                {item}
                            </li>
                        {/each}
                    </ul>
                </div>
            </div>
        {/if}
    {/if}
</div>

<style>
    .analysis-page {
        max-width: 900px;
        margin: 0 auto;
    }

    /* Page Header */
    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1.5rem;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .header-top {
        margin-bottom: 0.5rem;
    }

    .back-link {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--text-muted);
        text-decoration: none;
        font-size: 0.875rem;
        transition: color var(--duration-fast) ease;
    }

    .back-link:hover {
        color: var(--accent-primary);
    }

    .header-content h1 {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.25rem;
    }

    .sp500-tag {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: var(--radius-sm);
        font-size: 0.75rem;
        font-weight: 600;
    }

    .header-subtitle {
        color: var(--text-muted);
        font-size: 0.9375rem;
        margin: 0 0 0.5rem 0;
    }

    .header-tags {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-top: 0.5rem;
    }

    .sector-badge {
        display: inline-block;
        padding: 0.25rem 0.625rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-sm);
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-secondary);
    }

    .yahoo-link {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.25rem 0.625rem;
        background: rgba(103, 58, 183, 0.1);
        border-radius: var(--radius-sm);
        font-size: 0.75rem;
        font-weight: 600;
        color: #7c3aed;
        text-decoration: none;
        transition: all var(--duration-fast) ease;
    }

    .yahoo-link:hover {
        background: rgba(103, 58, 183, 0.2);
        color: #6d28d9;
    }

    .header-badge {
        padding-top: 2rem;
    }

    .badge-lg {
        font-size: 1rem;
        padding: 0.5rem 1rem;
    }

    /* Loading */
    .loading {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem;
        color: var(--text-muted);
    }

    .loading p {
        margin-top: 1rem;
    }

    /* Error Card */
    .error-card {
        text-align: center;
        padding: 3rem;
        background: var(--bg-card);
        border-radius: var(--radius-lg);
        border: 1px solid var(--border);
    }

    .error-card svg {
        color: var(--danger);
        margin-bottom: 1rem;
    }

    .error-card h3 {
        margin-bottom: 0.5rem;
    }

    .error-card p {
        color: var(--text-muted);
        margin-bottom: 1.5rem;
    }

    /* Result Cards */
    .result-card {
        overflow: hidden;
    }

    .data-years {
        font-size: 0.75rem;
        color: var(--text-muted);
        padding: 0.25rem 0.5rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-sm);
    }

    /* Warning Banner */
    .warning-banner {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: var(--radius-md);
        margin-bottom: 1rem;
        font-size: 0.875rem;
        color: var(--warning);
    }

    /* Not Calculable Box */
    .not-calculable-box {
        padding: 2rem;
        text-align: center;
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
        border: 1px solid var(--border-warning);
    }

    .not-calculable-icon {
        color: var(--text-warning);
        margin-bottom: 1rem;
    }

    .not-calculable-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }

    .not-calculable-note {
        color: var(--text-warning);
        font-weight: 500;
        margin-bottom: 1rem;
        padding: 0.75rem;
        background: rgba(var(--warning-rgb), 0.1);
        border-radius: var(--radius-sm);
    }

    .not-calculable-advice {
        font-size: 0.875rem;
        color: var(--text-secondary);
        font-style: italic;
        max-width: 500px;
        margin: 0 auto;
    }

    /* Price Comparison */
    .price-comparison {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
    }

    .price-box {
        text-align: center;
        padding: 1.5rem;
        border-radius: var(--radius-lg);
        border: 2px solid;
    }

    .price-icon {
        margin-bottom: 0.75rem;
        opacity: 0.5;
    }

    .mos-box {
        background: rgba(5, 150, 105, 0.06);
        border-color: rgba(5, 150, 105, 0.2);
    }

    .mos-box .price-icon { color: var(--success); }

    .sticker-box {
        background: rgba(59, 130, 246, 0.06);
        border-color: rgba(59, 130, 246, 0.2);
    }

    .sticker-box .price-icon { color: var(--info); }

    .current-box {
        background: rgba(124, 58, 237, 0.06);
        border-color: rgba(124, 58, 237, 0.2);
    }

    .current-box .price-icon { color: #7c3aed; }

    .price-label {
        font-size: 0.6875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        margin-bottom: 0.5rem;
    }

    .price-value {
        font-family: 'DM Serif Display', Georgia, serif;
        font-size: 1.5rem;
        color: var(--text-primary);
    }

    .price-note {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-top: 0.5rem;
    }

    /* Big Five Grid */
    .big-five-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 1rem;
    }

    .metric-card {
        padding: 1rem;
        border-radius: var(--radius-md);
        border: 1px solid var(--border);
        background: var(--bg-secondary);
    }

    .metric-card.passing {
        border-color: rgba(5, 150, 105, 0.3);
        background: rgba(5, 150, 105, 0.04);
    }

    .metric-card.failing {
        border-color: rgba(220, 38, 38, 0.3);
        background: rgba(220, 38, 38, 0.04);
    }

    .metric-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
    }

    .metric-name {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-secondary);
    }

    .metric-status {
        font-size: 0.625rem;
        padding: 0.125rem 0.375rem;
    }

    .metric-cagr {
        font-family: 'DM Serif Display', Georgia, serif;
        font-size: 1.5rem;
    }

    .metric-cagr.warning { color: var(--warning, #f59e0b); }
    .metric-cagr.muted { color: var(--text-muted); }

    .metric-note {
        font-size: 0.625rem;
        color: var(--text-muted);
        margin-top: 0.25rem;
    }

    /* Summary Box */
    .summary-box {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem;
        border-radius: var(--radius-md);
        font-size: 0.875rem;
        font-weight: 500;
    }

    .summary-box.success {
        background: rgba(5, 150, 105, 0.08);
        color: var(--success);
        border: 1px solid rgba(5, 150, 105, 0.2);
    }

    .summary-box.danger {
        background: rgba(220, 38, 38, 0.08);
        color: var(--danger);
        border: 1px solid rgba(220, 38, 38, 0.2);
    }

    /* 4Ms Grid */
    .four-ms-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1rem;
    }

    .ms-card {
        padding: 1.25rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
    }

    .ms-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .ms-header h4 {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 0;
        font-size: 0.9375rem;
    }

    .ms-header .badge {
        font-size: 0.875rem;
        padding: 0.25rem 0.625rem;
    }

    .ms-notes {
        list-style: none;
        font-size: 0.8125rem;
        color: var(--text-secondary);
    }

    .ms-notes li {
        margin-bottom: 0.5rem;
        padding-left: 1rem;
        position: relative;
    }

    .ms-notes li::before {
        content: "\2022";
        position: absolute;
        left: 0;
        color: var(--accent-primary);
    }

    /* Meaning Metrics */
    .meaning-metrics {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .metric-bar {
        display: grid;
        grid-template-columns: 120px 1fr 40px;
        align-items: center;
        gap: 0.5rem;
    }

    .metric-label {
        font-size: 0.6875rem;
        color: var(--text-muted);
        font-weight: 500;
    }

    .bar-container {
        height: 6px;
        background: var(--bg-tertiary, var(--bg-card));
        border-radius: 3px;
        overflow: hidden;
    }

    .bar-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary, var(--accent-primary)));
        border-radius: 3px;
    }

    .metric-value {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-align: right;
    }

    /* Recommendation Summary */
    .recommendation-summary {
        padding: 1.25rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
    }

    .recommendation-summary h3 {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.875rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }

    .summary-list {
        list-style: none;
    }

    .summary-list li {
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
        padding: 0.5rem 0;
        font-size: 0.875rem;
        color: var(--text-secondary);
    }

    .summary-list svg {
        flex-shrink: 0;
        color: var(--accent-primary);
        margin-top: 2px;
    }

    .score-display {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .score {
        font-family: 'DM Serif Display', Georgia, serif;
        font-size: 1.25rem;
    }

    /* Responsive */
    @media (max-width: 640px) {
        .page-header {
            flex-direction: column;
        }

        .header-badge {
            padding-top: 0;
        }

        .metric-bar {
            grid-template-columns: 1fr 60px;
        }

        .metric-label {
            grid-column: span 2;
            margin-bottom: -0.25rem;
        }
    }
</style>
