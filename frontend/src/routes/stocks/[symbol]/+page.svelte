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
</script>

<svelte:head>
    <title>{symbol} - DSE Value Investor</title>
</svelte:head>

<div class="stock-detail-page">
    <div class="page-header">
        <div>
            <h1>{symbol}</h1>
            {#if analysis?.recommendation}
                <span class="badge {getRecommendationClass(analysis.recommendation)}">
                    {analysis.recommendation.replace('_', ' ')}
                </span>
            {/if}
        </div>
        <div class="header-actions">
            <a href="/calculator?symbol={symbol}" class="btn btn-primary">
                Full Analysis
            </a>
            <button class="btn btn-secondary" on:click={loadStockData}>
                Refresh
            </button>
        </div>
    </div>

    {#if loading}
        <div class="loading">
            <div class="spinner"></div>
        </div>
    {:else if error}
        <div class="error">{error}</div>
    {:else}
        <!-- Price Card -->
        {#if priceData}
            <div class="card">
                <div class="card-header">
                    <h2>Current Price</h2>
                </div>
                <div class="price-grid">
                    <div class="price-item">
                        <span class="label">LTP</span>
                        <span class="value large">{formatCurrency(priceData.ltp)}</span>
                    </div>
                    <div class="price-item">
                        <span class="label">Change</span>
                        <span class="value {priceData.change && priceData.change >= 0 ? 'positive' : 'negative'}">
                            {priceData.change !== undefined ? (priceData.change >= 0 ? '+' : '') + priceData.change.toFixed(2) : '-'}
                            {#if priceData.change_pct !== undefined}
                                ({priceData.change_pct >= 0 ? '+' : ''}{priceData.change_pct.toFixed(2)}%)
                            {/if}
                        </span>
                    </div>
                    <div class="price-item">
                        <span class="label">High</span>
                        <span class="value">{formatCurrency(priceData.high)}</span>
                    </div>
                    <div class="price-item">
                        <span class="label">Low</span>
                        <span class="value">{formatCurrency(priceData.low)}</span>
                    </div>
                    <div class="price-item">
                        <span class="label">Volume</span>
                        <span class="value">{priceData.volume?.toLocaleString() || '-'}</span>
                    </div>
                </div>
            </div>
        {/if}

        <!-- Valuation Summary -->
        {#if analysis?.sticker_price}
            <div class="card mt-2">
                <div class="card-header">
                    <h2>Rule #1 Valuation</h2>
                    <span class="badge grade-{analysis.four_ms.overall_grade}">
                        Grade {analysis.four_ms.overall_grade}
                    </span>
                </div>
                <div class="valuation-grid">
                    <div class="val-item">
                        <span class="label">Sticker Price</span>
                        <span class="value accent">{formatCurrency(analysis.sticker_price.sticker_price)}</span>
                    </div>
                    <div class="val-item">
                        <span class="label">Margin of Safety</span>
                        <span class="value positive">{formatCurrency(analysis.sticker_price.margin_of_safety)}</span>
                    </div>
                    <div class="val-item">
                        <span class="label">Current Price</span>
                        <span class="value">{formatCurrency(analysis.current_price)}</span>
                    </div>
                    <div class="val-item">
                        <span class="label">Discount</span>
                        <span class="value {analysis.sticker_price.discount_to_sticker && analysis.sticker_price.discount_to_sticker > 0 ? 'positive' : 'negative'}">
                            {analysis.sticker_price.discount_to_sticker ? formatPercent(analysis.sticker_price.discount_to_sticker) : '-'}
                        </span>
                    </div>
                    <div class="val-item">
                        <span class="label">Big Five Score</span>
                        <span class="value">{analysis.big_five.score}/5 ({analysis.big_five.grade})</span>
                    </div>
                    <div class="val-item">
                        <span class="label">4Ms Score</span>
                        <span class="value">{analysis.four_ms.overall_score.toFixed(0)}/100</span>
                    </div>
                </div>
            </div>
        {/if}

        <!-- Financial History -->
        {#if fundamentals && fundamentals.data.length > 0}
            <div class="card mt-2">
                <div class="card-header">
                    <h2>Financial History</h2>
                    <span class="text-muted">{fundamentals.data.length} years of data</span>
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
                            {#each [...fundamentals.data].reverse() as record}
                                <tr>
                                    <td>{record.year}</td>
                                    <td class="text-right">{formatCurrency(record.eps)}</td>
                                    <td class="text-right">{record.revenue ? formatNumber(record.revenue / 1000000) + 'M' : '-'}</td>
                                    <td class="text-right">{record.total_equity ? formatNumber(record.total_equity / 1000000) + 'M' : '-'}</td>
                                    <td class="text-right">{record.roe ? formatPercent(record.roe) : '-'}</td>
                                    <td class="text-right">{record.debt_to_equity !== undefined ? record.debt_to_equity.toFixed(2) : '-'}</td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            </div>
        {/if}
    {/if}
</div>

<style>
    .stock-detail-page {
        max-width: 1000px;
        margin: 0 auto;
    }

    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1.5rem;
    }

    .page-header h1 {
        margin-bottom: 0.5rem;
    }

    .header-actions {
        display: flex;
        gap: 0.75rem;
    }

    .price-grid, .valuation-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1.5rem;
    }

    .price-item, .val-item {
        display: flex;
        flex-direction: column;
    }

    .label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }

    .value {
        font-size: 1.125rem;
        font-weight: 500;
    }

    .value.large {
        font-size: 1.5rem;
    }

    .value.accent {
        color: var(--accent-primary);
    }

    .table-container {
        overflow-x: auto;
    }
</style>
