<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { calculator, type StickerPriceResponse, type BigFiveResponse, type FullAnalysisResponse } from '$lib/api/client';

    // Form inputs
    let symbol = '';
    let manualMode = false;
    let currentEps = 0;
    let epsGrowthRate = 0;
    let historicalPe = 15;
    let currentPrice = 0;

    // Results
    let stickerResult: StickerPriceResponse | null = null;
    let bigFiveResult: BigFiveResponse | null = null;
    let fullAnalysis: FullAnalysisResponse | null = null;
    let loading = false;
    let error = '';

    onMount(() => {
        // Check for symbol in URL
        const urlSymbol = $page.url.searchParams.get('symbol');
        if (urlSymbol) {
            symbol = urlSymbol;
            analyzeStock();
        }
    });

    async function analyzeStock() {
        if (!symbol && !manualMode) {
            error = 'Please enter a stock symbol';
            return;
        }

        loading = true;
        error = '';
        stickerResult = null;
        bigFiveResult = null;
        fullAnalysis = null;

        if (manualMode) {
            // Manual calculation
            const result = await calculator.stickerPrice({
                current_eps: currentEps,
                eps_growth_rate: epsGrowthRate,
                historical_pe: historicalPe,
                current_price: currentPrice || undefined,
            });

            if (result.error) {
                error = result.error;
            } else if (result.data) {
                stickerResult = result.data;
            }
        } else {
            // Full analysis by symbol
            const result = await calculator.getFullAnalysis(symbol.toUpperCase());

            if (result.error) {
                error = result.error;
            } else if (result.data) {
                fullAnalysis = result.data;
                stickerResult = result.data.sticker_price || null;
                bigFiveResult = result.data.big_five;
            }
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
            default: return '';
        }
    }

    function formatCurrency(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        return `৳${value.toLocaleString('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    function formatPercent(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        return `${value.toFixed(2)}%`;
    }
</script>

<svelte:head>
    <title>Calculator - DSE Value Investor</title>
</svelte:head>

<div class="calculator-page">
    <!-- Page Header -->
    <div class="page-header">
        <div class="header-content">
            <h1>Rule #1 Calculator</h1>
            <p class="header-subtitle">Calculate Sticker Price, Big Five Numbers, and 4Ms Analysis</p>
        </div>
    </div>

    <!-- Input Form Card -->
    <div class="card form-card animate-fadeIn">
        <div class="form-toggle">
            <button
                class="toggle-btn"
                class:active={!manualMode}
                on:click={() => manualMode = false}
            >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="M21 21l-4.35-4.35"/>
                </svg>
                By Symbol
            </button>
            <button
                class="toggle-btn"
                class:active={manualMode}
                on:click={() => manualMode = true}
            >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="4" y="2" width="16" height="20" rx="2"/>
                    <line x1="8" y1="6" x2="16" y2="6"/>
                    <line x1="8" y1="10" x2="16" y2="10"/>
                    <line x1="8" y1="14" x2="12" y2="14"/>
                </svg>
                Manual Input
            </button>
        </div>

        <form on:submit|preventDefault={analyzeStock} class="calculator-form">
            {#if !manualMode}
                <div class="form-group">
                    <label for="symbol">Stock Symbol</label>
                    <div class="input-wrapper">
                        <input
                            type="text"
                            id="symbol"
                            bind:value={symbol}
                            placeholder="e.g., BXPHARMA"
                            class="symbol-input"
                        />
                        <span class="input-hint">Enter a DSE stock symbol</span>
                    </div>
                </div>
            {:else}
                <div class="manual-inputs">
                    <div class="form-group">
                        <label for="eps">Current EPS (BDT)</label>
                        <input type="number" id="eps" bind:value={currentEps} step="0.01" placeholder="0.00" />
                    </div>
                    <div class="form-group">
                        <label for="growth">EPS Growth Rate (%)</label>
                        <input type="number" id="growth" bind:value={epsGrowthRate} step="0.1" placeholder="0.0" />
                    </div>
                    <div class="form-group">
                        <label for="pe">Historical PE Ratio</label>
                        <input type="number" id="pe" bind:value={historicalPe} step="0.1" placeholder="15.0" />
                    </div>
                    <div class="form-group">
                        <label for="price">Current Price (optional)</label>
                        <input type="number" id="price" bind:value={currentPrice} step="0.01" placeholder="For comparison" />
                    </div>
                </div>
            {/if}

            <button type="submit" class="btn btn-primary btn-lg" disabled={loading}>
                {#if loading}
                    <span class="spinner spinner-sm"></span>
                    Analyzing...
                {:else}
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
                        <polyline points="16 7 22 7 22 13"/>
                    </svg>
                    Calculate
                {/if}
            </button>
        </form>
    </div>

    {#if error}
        <div class="error mt-3 animate-fadeIn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{error}</span>
        </div>
    {/if}

    {#if stickerResult}
        <!-- Sticker Price Results -->
        <div class="card result-card mt-3 animate-fadeIn stagger-1">
            <div class="card-header">
                <h2>
                    Sticker Price Analysis
                    {#if stickerResult.symbol}
                        <span class="symbol-tag">{stickerResult.symbol}</span>
                    {/if}
                </h2>
                {#if stickerResult.recommendation}
                    <span class="badge {getRecommendationClass(stickerResult.recommendation)}">
                        {stickerResult.recommendation.replace('_', ' ')}
                    </span>
                {/if}
            </div>

            <!-- Price Comparison Cards -->
            <div class="price-comparison">
                <div class="price-box mos-box">
                    <div class="price-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        </svg>
                    </div>
                    <div class="price-label">Margin of Safety</div>
                    <div class="price-value">{formatCurrency(stickerResult.margin_of_safety)}</div>
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
                    <div class="price-value">{formatCurrency(stickerResult.sticker_price)}</div>
                    <div class="price-note">Intrinsic value</div>
                </div>
                {#if stickerResult.current_price}
                    <div class="price-box current-box">
                        <div class="price-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
                                <polyline points="16 7 22 7 22 13"/>
                            </svg>
                        </div>
                        <div class="price-label">Current Price</div>
                        <div class="price-value">{formatCurrency(stickerResult.current_price)}</div>
                        {#if stickerResult.discount_to_sticker}
                            <div class="price-note {stickerResult.discount_to_sticker > 0 ? 'positive' : 'negative'}">
                                {stickerResult.discount_to_sticker > 0 ? 'Undervalued' : 'Overvalued'} by {Math.abs(stickerResult.discount_to_sticker).toFixed(1)}%
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>

            <!-- Calculation Breakdown -->
            <div class="breakdown-section mt-3">
                <h3>Calculation Breakdown</h3>
                <div class="breakdown-grid">
                    <div class="breakdown-item">
                        <span class="breakdown-label">Current EPS</span>
                        <span class="breakdown-value">{formatCurrency(stickerResult.current_eps)}</span>
                    </div>
                    <div class="breakdown-item">
                        <span class="breakdown-label">Historical EPS Growth</span>
                        <span class="breakdown-value">{formatPercent(stickerResult.eps_growth_rate)}</span>
                    </div>
                    <div class="breakdown-item">
                        <span class="breakdown-label">Used Growth Rate</span>
                        <span class="breakdown-value highlight">{formatPercent(stickerResult.used_growth_rate)}</span>
                    </div>
                    <div class="breakdown-item">
                        <span class="breakdown-label">Historical PE</span>
                        <span class="breakdown-value">{stickerResult.historical_pe.toFixed(2)}</span>
                    </div>
                    <div class="breakdown-item">
                        <span class="breakdown-label">Projected EPS (10yr)</span>
                        <span class="breakdown-value">{formatCurrency(stickerResult.future_eps)}</span>
                    </div>
                    <div class="breakdown-item">
                        <span class="breakdown-label">Future Price (10yr)</span>
                        <span class="breakdown-value">{formatCurrency(stickerResult.future_price)}</span>
                    </div>
                </div>
            </div>
        </div>
    {/if}

    {#if bigFiveResult}
        <!-- Big Five Results -->
        <div class="card result-card mt-3 animate-fadeIn stagger-2">
            <div class="card-header">
                <h2>Big Five Numbers</h2>
                <div class="score-display">
                    <span class="score">{bigFiveResult.score}/{bigFiveResult.total}</span>
                    <span class="badge grade-{bigFiveResult.grade}">Grade {bigFiveResult.grade}</span>
                </div>
            </div>

            <div class="big-five-grid">
                {#each [bigFiveResult.revenue, bigFiveResult.eps, bigFiveResult.equity, bigFiveResult.operating_cf, bigFiveResult.free_cf] as metric}
                    <div class="metric-card {metric.passes ? 'passing' : 'failing'}">
                        <div class="metric-header">
                            <span class="metric-name">{metric.name}</span>
                            <span class="metric-status badge {metric.passes ? 'badge-success' : 'badge-danger'}">
                                {metric.status}
                            </span>
                        </div>
                        <div class="metric-cagr {metric.passes ? 'positive' : 'negative'}">
                            {metric.cagr_pct > 0 ? '+' : ''}{metric.cagr_pct.toFixed(1)}%
                        </div>
                        <div class="metric-note">
                            {metric.years} year{metric.years !== 1 ? 's' : ''} of data
                        </div>
                    </div>
                {/each}
            </div>

            <div class="summary-box mt-3 {bigFiveResult.passes ? 'success' : 'danger'}">
                {#if bigFiveResult.passes}
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                    <span>Passes Big Five test ({bigFiveResult.score}/5 metrics above 10%)</span>
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

    {#if fullAnalysis?.four_ms}
        <!-- 4Ms Summary -->
        <div class="card result-card mt-3 animate-fadeIn stagger-3">
            <div class="card-header">
                <h2>4Ms Analysis</h2>
                <div class="score-display">
                    <span class="score">{fullAnalysis.four_ms.overall_score.toFixed(0)}/100</span>
                    <span class="badge grade-{fullAnalysis.four_ms.overall_grade}">
                        Grade {fullAnalysis.four_ms.overall_grade}
                    </span>
                </div>
            </div>

            <div class="four-ms-grid">
                <div class="ms-card">
                    <div class="ms-header">
                        <h4>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                            </svg>
                            Moat
                        </h4>
                        <span class="badge grade-{fullAnalysis.four_ms.moat.grade}">
                            {fullAnalysis.four_ms.moat.score.toFixed(0)}
                        </span>
                    </div>
                    <ul class="ms-notes">
                        {#each fullAnalysis.four_ms.moat.notes as note}
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
                        <span class="badge grade-{fullAnalysis.four_ms.management.grade}">
                            {fullAnalysis.four_ms.management.score.toFixed(0)}
                        </span>
                    </div>
                    <ul class="ms-notes">
                        {#each fullAnalysis.four_ms.management.notes as note}
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
                        <span class="badge grade-{fullAnalysis.four_ms.mos.grade}">
                            {fullAnalysis.four_ms.mos.score.toFixed(0)}
                        </span>
                    </div>
                    <ul class="ms-notes">
                        {#each fullAnalysis.four_ms.mos.notes as note}
                            <li>{note}</li>
                        {/each}
                    </ul>
                </div>
            </div>

            <div class="recommendation-summary mt-3">
                <h3>Summary</h3>
                <ul class="summary-list">
                    {#each fullAnalysis.four_ms.summary as item}
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
</div>

<style>
    .calculator-page {
        max-width: 900px;
        margin: 0 auto;
    }

    /* Page Header */
    .page-header {
        margin-bottom: 1.5rem;
    }

    .header-content h1 {
        margin-bottom: 0.25rem;
    }

    .header-subtitle {
        color: var(--text-muted);
        font-size: 0.9375rem;
        margin: 0;
    }

    /* Form Card */
    .form-card {
        padding: 1.5rem;
    }

    .form-toggle {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
        background: var(--bg-secondary);
        padding: 0.25rem;
        border-radius: var(--radius-md);
    }

    .toggle-btn {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.75rem;
        background: transparent;
        border: none;
        color: var(--text-secondary);
        border-radius: var(--radius-sm);
        cursor: pointer;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.875rem;
        font-weight: 500;
        transition: all var(--duration-fast) var(--ease-out-expo);
    }

    .toggle-btn:hover {
        color: var(--text-primary);
    }

    .toggle-btn.active {
        background: var(--bg-card);
        color: var(--accent-primary);
        box-shadow: var(--shadow-sm);
    }

    .calculator-form {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
    }

    .input-wrapper {
        display: flex;
        flex-direction: column;
        gap: 0.375rem;
    }

    .symbol-input {
        font-size: 1.125rem;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    .input-hint {
        font-size: 0.75rem;
        color: var(--text-muted);
    }

    .manual-inputs {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
    }

    .symbol-tag {
        background: var(--bg-secondary);
        padding: 0.25rem 0.625rem;
        border-radius: var(--radius-sm);
        font-size: 0.8125rem;
        font-weight: 600;
        margin-left: 0.5rem;
        color: var(--accent-primary);
    }

    /* Result Cards */
    .result-card {
        overflow: hidden;
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
        position: relative;
    }

    .price-icon {
        margin-bottom: 0.75rem;
        opacity: 0.5;
    }

    .mos-box {
        background: rgba(5, 150, 105, 0.06);
        border-color: rgba(5, 150, 105, 0.2);
    }

    .mos-box .price-icon {
        color: var(--success);
    }

    .sticker-box {
        background: rgba(59, 130, 246, 0.06);
        border-color: rgba(59, 130, 246, 0.2);
    }

    .sticker-box .price-icon {
        color: var(--info);
    }

    .current-box {
        background: rgba(124, 58, 237, 0.06);
        border-color: rgba(124, 58, 237, 0.2);
    }

    .current-box .price-icon {
        color: #7c3aed;
    }

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

    /* Breakdown Section */
    .breakdown-section {
        padding-top: 1.5rem;
        border-top: 1px solid var(--border-light);
    }

    .breakdown-section h3 {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-secondary);
        margin-bottom: 1rem;
    }

    .breakdown-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
    }

    .breakdown-item {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .breakdown-label {
        font-size: 0.6875rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .breakdown-value {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    .breakdown-value.highlight {
        color: var(--accent-primary);
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
        transition: all var(--duration-fast) var(--ease-out-expo);
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
        content: "•";
        position: absolute;
        left: 0;
        color: var(--accent-primary);
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

    /* Error */
    .error {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    /* Responsive */
    @media (max-width: 640px) {
        .manual-inputs {
            grid-template-columns: 1fr;
        }

        .breakdown-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }
</style>
