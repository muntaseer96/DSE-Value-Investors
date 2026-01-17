<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { stocks, calculator, type StockPrice, type FundamentalsResponse, type FullAnalysisResponse } from '$lib/api/client';

    $: symbol = $page.params.symbol?.toUpperCase() || '';

    let priceData: StockPrice | null = null;
    let fundamentals: FundamentalsResponse | null = null;
    let analysis: FullAnalysisResponse | null = null;
    let loading = true;
    let error = '';

    onMount(async () => {
        await loadStockData();
    });

    async function loadStockData() {
        loading = true;
        error = '';

        // Load price
        const priceResult = await stocks.getPrice(symbol);
        if (priceResult.data) {
            priceData = priceResult.data;
        }

        // Load fundamentals
        const fundResult = await stocks.getFundamentals(symbol);
        if (fundResult.data) {
            fundamentals = fundResult.data;
        }

        // Load analysis
        const analysisResult = await calculator.getFullAnalysis(symbol);
        if (analysisResult.data) {
            analysis = analysisResult.data;
        } else if (analysisResult.error) {
            // Analysis might fail if not enough data
            console.log('Analysis not available:', analysisResult.error);
        }

        loading = false;
    }

    function formatCurrency(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        return `৳${value.toLocaleString('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    function formatNumber(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        return value.toLocaleString('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function formatPercent(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        return `${value.toFixed(2)}%`;
    }

    function getRecommendationClass(rec: string | undefined): string {
        if (!rec) return '';
        switch (rec) {
            case 'STRONG_BUY': return 'badge-success';
            case 'BUY': return 'badge-info';
            case 'HOLD': return 'badge-warning';
            case 'SELL':
            case 'AVOID': return 'badge-danger';
            default: return '';
        }
    }

    function getChangeClass(value: number | undefined | null): string {
        if (value === undefined || value === null || value === 0) return '';
        return value >= 0 ? 'positive' : 'negative';
    }

    function getChangeIcon(value: number | undefined | null): string {
        if (value === undefined || value === null || value === 0) return '';
        return value >= 0 ? '↑' : '↓';
    }
</script>

<svelte:head>
    <title>{symbol} - Stokr</title>
</svelte:head>

<div class="stock-detail-page">
    <!-- Page Header -->
    <div class="page-header animate-fadeIn">
        <div class="header-content">
            <div class="symbol-header">
                <h1>{symbol}</h1>
                {#if analysis?.recommendation}
                    <span class="badge {getRecommendationClass(analysis.recommendation)}">
                        {analysis.recommendation.replace('_', ' ')}
                    </span>
                {/if}
            </div>
            <p class="header-subtitle">Detailed stock analysis and fundamentals</p>
        </div>
        <div class="header-actions">
            <a href="/calculator?symbol={symbol}" class="btn btn-primary">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
                    <polyline points="16 7 22 7 22 13"/>
                </svg>
                Full Analysis
            </a>
            <button class="btn btn-secondary" on:click={loadStockData}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 4 23 10 17 10"/>
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                </svg>
                Refresh
            </button>
        </div>
    </div>

    {#if loading}
        <div class="loading">
            <div class="spinner"></div>
        </div>
    {:else if error}
        <div class="error animate-fadeIn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <div>
                <p><strong>Error loading data</strong></p>
                <p class="text-muted">{error}</p>
            </div>
        </div>
    {:else}
        <!-- Price Hero Card -->
        {#if priceData}
            <div class="price-hero animate-fadeIn">
                <div class="price-hero-main">
                    <span class="price-label">Last Traded Price</span>
                    <div class="price-value-row">
                        <span class="price-value">{formatCurrency(priceData.ltp)}</span>
                        <span class="price-change {getChangeClass(priceData.change)}">
                            <span class="change-icon">{getChangeIcon(priceData.change)}</span>
                            {priceData.change !== undefined ? Math.abs(priceData.change).toFixed(2) : '-'}
                            {#if priceData.change_pct !== undefined}
                                <span class="change-pct">({Math.abs(priceData.change_pct).toFixed(2)}%)</span>
                            {/if}
                        </span>
                    </div>
                </div>
                <div class="price-hero-stats">
                    <div class="stat">
                        <span class="stat-label">High</span>
                        <span class="stat-value">{formatCurrency(priceData.high)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Low</span>
                        <span class="stat-value">{formatCurrency(priceData.low)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Volume</span>
                        <span class="stat-value">{priceData.volume?.toLocaleString() || '-'}</span>
                    </div>
                </div>
            </div>
        {/if}

        <div class="content-grid mt-3">
            <!-- Valuation Summary -->
            {#if analysis?.sticker_price}
                <div class="card valuation-card animate-fadeIn stagger-1">
                    <div class="card-header">
                        <h2>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 0.5rem; vertical-align: -2px;">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                            </svg>
                            Rule #1 Valuation
                        </h2>
                        <span class="badge grade-{analysis.four_ms.overall_grade}">
                            Grade {analysis.four_ms.overall_grade}
                        </span>
                    </div>

                    <div class="valuation-grid">
                        <div class="val-item highlight">
                            <span class="val-label">Sticker Price</span>
                            <span class="val-value accent">{formatCurrency(analysis.sticker_price.sticker_price)}</span>
                        </div>
                        <div class="val-item highlight">
                            <span class="val-label">Margin of Safety</span>
                            <span class="val-value positive">{formatCurrency(analysis.sticker_price.margin_of_safety)}</span>
                        </div>
                        <div class="val-item">
                            <span class="val-label">Current Price</span>
                            <span class="val-value">{formatCurrency(analysis.current_price)}</span>
                        </div>
                        <div class="val-item">
                            <span class="val-label">Discount</span>
                            <span class="val-value {getChangeClass(analysis.sticker_price.discount_to_sticker)}">
                                {analysis.sticker_price.discount_to_sticker ? formatPercent(analysis.sticker_price.discount_to_sticker) : '-'}
                            </span>
                        </div>
                    </div>

                    <div class="scores-row mt-3">
                        <div class="score-item">
                            <span class="score-value">{analysis.big_five.score}/5</span>
                            <span class="score-label">Big Five Score</span>
                            <span class="score-grade badge grade-{analysis.big_five.grade}">{analysis.big_five.grade}</span>
                        </div>
                        <div class="score-item">
                            <span class="score-value">{analysis.four_ms.overall_score.toFixed(0)}/100</span>
                            <span class="score-label">4Ms Score</span>
                            <span class="score-grade badge grade-{analysis.four_ms.overall_grade}">{analysis.four_ms.overall_grade}</span>
                        </div>
                    </div>
                </div>
            {:else}
                <div class="card animate-fadeIn stagger-1">
                    <div class="empty-state">
                        <svg class="empty-state-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        </svg>
                        <h3>Valuation Not Available</h3>
                        <p>Not enough historical data to perform Rule #1 analysis.</p>
                    </div>
                </div>
            {/if}

            <!-- Quick Stats -->
            {#if analysis}
                <div class="card quick-stats-card animate-fadeIn stagger-2">
                    <div class="card-header">
                        <h2>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 0.5rem; vertical-align: -2px;">
                                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                            </svg>
                            Quick Stats
                        </h2>
                    </div>
                    <div class="quick-stats-grid">
                        <div class="quick-stat">
                            <span class="qs-label">EPS Growth</span>
                            <span class="qs-value {getChangeClass(analysis.sticker_price?.eps_growth_rate)}">{analysis.sticker_price?.eps_growth_rate ? formatPercent(analysis.sticker_price.eps_growth_rate) : '-'}</span>
                        </div>
                        <div class="quick-stat">
                            <span class="qs-label">Current EPS</span>
                            <span class="qs-value">{analysis.sticker_price?.current_eps ? formatCurrency(analysis.sticker_price.current_eps) : '-'}</span>
                        </div>
                        <div class="quick-stat">
                            <span class="qs-label">PE Ratio</span>
                            <span class="qs-value">{analysis.sticker_price?.historical_pe.toFixed(2) || '-'}</span>
                        </div>
                        <div class="quick-stat">
                            <span class="qs-label">10yr Future Price</span>
                            <span class="qs-value">{analysis.sticker_price?.future_price ? formatCurrency(analysis.sticker_price.future_price) : '-'}</span>
                        </div>
                    </div>
                </div>
            {/if}
        </div>

        <!-- Financial History -->
        {#if fundamentals && fundamentals.data.length > 0}
            <div class="card mt-3 animate-fadeIn stagger-3">
                <div class="card-header">
                    <h2>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 0.5rem; vertical-align: -2px;">
                            <rect x="3" y="3" width="18" height="18" rx="2"/>
                            <path d="M3 9h18"/>
                            <path d="M9 21V9"/>
                        </svg>
                        Financial History
                    </h2>
                    <span class="badge badge-neutral">{fundamentals.data.length} years</span>
                </div>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Year</th>
                                <th class="text-right">EPS</th>
                                <th class="text-right">Revenue</th>
                                <th class="text-right">Equity</th>
                                <th class="text-right">ROE</th>
                                <th class="text-right">D/E</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each [...fundamentals.data].reverse() as record, i}
                                <tr class="animate-fadeIn" style="animation-delay: {50 + i * 30}ms">
                                    <td class="font-semibold">{record.year}</td>
                                    <td class="text-right tabular-nums">{formatCurrency(record.eps)}</td>
                                    <td class="text-right tabular-nums text-muted">{record.revenue ? formatNumber(record.revenue / 1000000) + 'M' : '-'}</td>
                                    <td class="text-right tabular-nums text-muted">{record.total_equity ? formatNumber(record.total_equity / 1000000) + 'M' : '-'}</td>
                                    <td class="text-right tabular-nums {getChangeClass(record.roe)}">{record.roe ? formatPercent(record.roe) : '-'}</td>
                                    <td class="text-right tabular-nums">{record.debt_to_equity !== undefined && record.debt_to_equity !== null ? record.debt_to_equity.toFixed(2) : '-'}</td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            </div>
        {:else}
            <div class="card mt-3 animate-fadeIn stagger-3">
                <div class="empty-state">
                    <svg class="empty-state-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <rect x="3" y="3" width="18" height="18" rx="2"/>
                        <path d="M3 9h18"/>
                        <path d="M9 21V9"/>
                    </svg>
                    <h3>No Financial Data</h3>
                    <p>Historical financial data is not available for this stock.</p>
                </div>
            </div>
        {/if}
    {/if}
</div>

<style>
    .stock-detail-page {
        max-width: 1100px;
        margin: 0 auto;
    }

    /* Page Header */
    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1.5rem;
        gap: 1rem;
    }

    .symbol-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.25rem;
    }

    .symbol-header h1 {
        margin: 0;
    }

    .header-subtitle {
        color: var(--text-muted);
        font-size: 0.9375rem;
        margin: 0;
    }

    .header-actions {
        display: flex;
        gap: 0.75rem;
        flex-shrink: 0;
    }

    /* Price Hero */
    .price-hero {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.75rem 2rem;
        background: var(--bg-card);
        border-radius: var(--radius-xl);
        box-shadow: var(--shadow-lg);
        border: 1px solid var(--border-light);
    }

    .price-label {
        display: block;
        font-size: 0.6875rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    .price-value-row {
        display: flex;
        align-items: baseline;
        gap: 1rem;
    }

    .price-value {
        font-family: 'DM Serif Display', Georgia, serif;
        font-size: 2.5rem;
        color: var(--text-primary);
    }

    .price-change {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        font-size: 1.125rem;
        font-weight: 600;
    }

    .change-icon {
        font-size: 0.875rem;
    }

    .change-pct {
        opacity: 0.8;
    }

    .price-hero-stats {
        display: flex;
        gap: 2.5rem;
    }

    .stat {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
    }

    .stat-label {
        font-size: 0.6875rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .stat-value {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    /* Content Grid */
    .content-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
    }

    /* Valuation Card */
    .valuation-card {
        grid-column: 1;
    }

    .valuation-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1.25rem;
    }

    .val-item {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .val-item.highlight {
        padding: 1rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
    }

    .val-label {
        font-size: 0.6875rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .val-value {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    .val-value.accent {
        color: var(--accent-primary);
    }

    .scores-row {
        display: flex;
        gap: 1rem;
        padding-top: 1.25rem;
        border-top: 1px solid var(--border-light);
    }

    .score-item {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.25rem;
        padding: 1rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
    }

    .score-value {
        font-family: 'DM Serif Display', Georgia, serif;
        font-size: 1.5rem;
    }

    .score-label {
        font-size: 0.6875rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
    }

    .score-grade {
        margin-top: 0.25rem;
    }

    /* Quick Stats */
    .quick-stats-card {
        grid-column: 2;
    }

    .quick-stats-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
    }

    .quick-stat {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        padding: 1rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
    }

    .qs-label {
        font-size: 0.6875rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .qs-value {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    /* Table */
    .table-container {
        overflow-x: auto;
    }

    th:first-child,
    td:first-child {
        padding-left: 1.5rem;
    }

    th:last-child,
    td:last-child {
        padding-right: 1.5rem;
    }

    .tabular-nums {
        font-variant-numeric: tabular-nums;
    }

    /* Empty State */
    .empty-state {
        padding: 3rem 2rem;
    }

    /* Responsive */
    @media (max-width: 900px) {
        .content-grid {
            grid-template-columns: 1fr;
        }

        .valuation-card,
        .quick-stats-card {
            grid-column: auto;
        }
    }

    @media (max-width: 768px) {
        .page-header {
            flex-direction: column;
            align-items: stretch;
        }

        .header-actions {
            justify-content: flex-start;
        }

        .price-hero {
            flex-direction: column;
            align-items: flex-start;
            gap: 1.5rem;
            padding: 1.5rem;
        }

        .price-value {
            font-size: 2rem;
        }

        .price-hero-stats {
            width: 100%;
            justify-content: space-between;
            padding-top: 1rem;
            border-top: 1px solid var(--border-light);
        }

        .stat {
            align-items: flex-start;
        }

        .valuation-grid {
            grid-template-columns: 1fr;
        }

        .scores-row {
            flex-direction: column;
        }

        .quick-stats-grid {
            grid-template-columns: 1fr;
        }

        /* Hide some columns on mobile */
        th:nth-child(3),
        td:nth-child(3),
        th:nth-child(4),
        td:nth-child(4) {
            display: none;
        }
    }
</style>
