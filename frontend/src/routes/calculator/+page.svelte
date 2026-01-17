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

<div class="calculator-page">
    <h1>Rule #1 Calculator</h1>
    <p class="subtitle">Calculate Sticker Price, Big Five Numbers, and 4Ms Analysis</p>

    <!-- Input Form -->
    <div class="card mt-2">
        <div class="form-toggle">
            <button
                class="toggle-btn {!manualMode ? 'active' : ''}"
                on:click={() => manualMode = false}
            >
                By Symbol
            </button>
            <button
                class="toggle-btn {manualMode ? 'active' : ''}"
                on:click={() => manualMode = true}
            >
                Manual Input
            </button>
        </div>

        <form on:submit|preventDefault={analyzeStock} class="calculator-form">
            {#if !manualMode}
                <div class="form-group">
                    <label for="symbol">Stock Symbol</label>
                    <input
                        type="text"
                        id="symbol"
                        bind:value={symbol}
                        placeholder="e.g., BXPHARMA"
                        class="symbol-input"
                    />
                </div>
            {:else}
                <div class="grid grid-2">
                    <div class="form-group">
                        <label for="eps">Current EPS (BDT)</label>
                        <input type="number" id="eps" bind:value={currentEps} step="0.01" />
                    </div>
                    <div class="form-group">
                        <label for="growth">EPS Growth Rate (%)</label>
                        <input type="number" id="growth" bind:value={epsGrowthRate} step="0.1" />
                    </div>
                    <div class="form-group">
                        <label for="pe">Historical PE Ratio</label>
                        <input type="number" id="pe" bind:value={historicalPe} step="0.1" />
                    </div>
                    <div class="form-group">
                        <label for="price">Current Price (optional)</label>
                        <input type="number" id="price" bind:value={currentPrice} step="0.01" />
                    </div>
                </div>
            {/if}

            <button type="submit" class="btn btn-primary" disabled={loading}>
                {loading ? 'Analyzing...' : 'Calculate'}
            </button>
        </form>
    </div>

    {#if error}
        <div class="error mt-2">{error}</div>
    {/if}

    {#if loading}
        <div class="loading mt-2">
            <div class="spinner"></div>
        </div>
    {/if}

    {#if stickerResult}
        <!-- Sticker Price Results -->
        <div class="card mt-2">
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

            <div class="sticker-results">
                <!-- Price Comparison -->
                <div class="price-comparison">
                    <div class="price-box mos-box">
                        <div class="price-label">Margin of Safety</div>
                        <div class="price-value">{formatCurrency(stickerResult.margin_of_safety)}</div>
                        <div class="price-note">Buy below this price</div>
                    </div>
                    <div class="price-box sticker-box">
                        <div class="price-label">Sticker Price</div>
                        <div class="price-value">{formatCurrency(stickerResult.sticker_price)}</div>
                        <div class="price-note">Intrinsic value</div>
                    </div>
                    {#if stickerResult.current_price}
                        <div class="price-box current-box">
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
                <div class="calculation-breakdown mt-2">
                    <h3>Calculation Breakdown</h3>
                    <table class="breakdown-table">
                        <tr>
                            <td>Current EPS</td>
                            <td class="text-right">{formatCurrency(stickerResult.current_eps)}</td>
                        </tr>
                        <tr>
                            <td>Historical EPS Growth</td>
                            <td class="text-right">{formatPercent(stickerResult.eps_growth_rate)}</td>
                        </tr>
                        <tr>
                            <td>Used Growth Rate (capped at 15%)</td>
                            <td class="text-right">{formatPercent(stickerResult.used_growth_rate)}</td>
                        </tr>
                        <tr>
                            <td>Historical PE Ratio</td>
                            <td class="text-right">{stickerResult.historical_pe.toFixed(2)}</td>
                        </tr>
                        <tr class="separator">
                            <td colspan="2"></td>
                        </tr>
                        <tr>
                            <td>Projected EPS (10 years)</td>
                            <td class="text-right">{formatCurrency(stickerResult.future_eps)}</td>
                        </tr>
                        <tr>
                            <td>Applied PE Ratio</td>
                            <td class="text-right">{stickerResult.future_pe.toFixed(2)}</td>
                        </tr>
                        <tr>
                            <td>Future Price (10 years)</td>
                            <td class="text-right">{formatCurrency(stickerResult.future_price)}</td>
                        </tr>
                        <tr class="highlight">
                            <td>Sticker Price (discounted 15%/yr)</td>
                            <td class="text-right">{formatCurrency(stickerResult.sticker_price)}</td>
                        </tr>
                        <tr class="highlight">
                            <td>Margin of Safety (50% discount)</td>
                            <td class="text-right">{formatCurrency(stickerResult.margin_of_safety)}</td>
                        </tr>
                    </table>
                </div>
            </div>
        </div>
    {/if}

    {#if bigFiveResult}
        <!-- Big Five Results -->
        <div class="card mt-2">
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
                            <span class="metric-status {getStatusClass(metric.status)}">{metric.status}</span>
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

            <div class="big-five-summary mt-2">
                {#if bigFiveResult.passes}
                    <p class="positive">✓ Passes Big Five test ({bigFiveResult.score}/5 metrics above 10%)</p>
                {:else}
                    <p class="negative">✗ Does not pass Big Five test (need at least 3/5 above 10%)</p>
                {/if}
            </div>
        </div>
    {/if}

    {#if fullAnalysis?.four_ms}
        <!-- 4Ms Summary -->
        <div class="card mt-2">
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
                    <h4>Moat</h4>
                    <div class="ms-score badge grade-{fullAnalysis.four_ms.moat.grade}">
                        {fullAnalysis.four_ms.moat.score.toFixed(0)}
                    </div>
                    <ul class="ms-notes">
                        {#each fullAnalysis.four_ms.moat.notes as note}
                            <li>{note}</li>
                        {/each}
                    </ul>
                </div>

                <div class="ms-card">
                    <h4>Management</h4>
                    <div class="ms-score badge grade-{fullAnalysis.four_ms.management.grade}">
                        {fullAnalysis.four_ms.management.score.toFixed(0)}
                    </div>
                    <ul class="ms-notes">
                        {#each fullAnalysis.four_ms.management.notes as note}
                            <li>{note}</li>
                        {/each}
                    </ul>
                </div>

                <div class="ms-card">
                    <h4>Margin of Safety</h4>
                    <div class="ms-score badge grade-{fullAnalysis.four_ms.mos.grade}">
                        {fullAnalysis.four_ms.mos.score.toFixed(0)}
                    </div>
                    <ul class="ms-notes">
                        {#each fullAnalysis.four_ms.mos.notes as note}
                            <li>{note}</li>
                        {/each}
                    </ul>
                </div>
            </div>

            <div class="recommendation-summary mt-2">
                <h3>Summary</h3>
                <ul>
                    {#each fullAnalysis.four_ms.summary as item}
                        <li>{item}</li>
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

    .subtitle {
        color: var(--text-secondary);
        margin-top: -1rem;
        margin-bottom: 1.5rem;
    }

    .form-toggle {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
    }

    .toggle-btn {
        flex: 1;
        padding: 0.75rem;
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        color: var(--text-secondary);
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s;
    }

    .toggle-btn.active {
        background: var(--accent-primary);
        color: #000;
        border-color: var(--accent-primary);
    }

    .calculator-form {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .form-group {
        display: flex;
        flex-direction: column;
    }

    .symbol-input {
        font-size: 1.25rem;
        text-transform: uppercase;
    }

    .symbol-tag {
        background: var(--bg-tertiary);
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.875rem;
        margin-left: 0.5rem;
    }

    /* Price Comparison */
    .price-comparison {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }

    .price-box {
        text-align: center;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px solid;
    }

    .mos-box {
        background: rgba(34, 197, 94, 0.1);
        border-color: var(--success);
    }

    .sticker-box {
        background: rgba(59, 130, 246, 0.1);
        border-color: var(--info);
    }

    .current-box {
        background: rgba(124, 58, 237, 0.1);
        border-color: var(--accent-secondary);
    }

    .price-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: var(--text-secondary);
        margin-bottom: 0.5rem;
    }

    .price-value {
        font-size: 1.5rem;
        font-weight: 600;
    }

    .price-note {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-top: 0.5rem;
    }

    /* Breakdown Table */
    .breakdown-table {
        width: 100%;
        font-size: 0.875rem;
    }

    .breakdown-table td {
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--border-color);
    }

    .breakdown-table tr.separator td {
        border-bottom: 2px solid var(--border-color);
        padding: 0.25rem 0;
    }

    .breakdown-table tr.highlight td {
        font-weight: 600;
        color: var(--accent-primary);
    }

    /* Big Five Grid */
    .big-five-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
    }

    .metric-card {
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid var(--border-color);
        background: var(--bg-secondary);
    }

    .metric-card.passing {
        border-color: var(--success);
        background: rgba(34, 197, 94, 0.05);
    }

    .metric-card.failing {
        border-color: var(--danger);
        background: rgba(239, 68, 68, 0.05);
    }

    .metric-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }

    .metric-name {
        font-size: 0.75rem;
        color: var(--text-secondary);
    }

    .metric-status {
        font-size: 0.625rem;
        font-weight: 600;
    }

    .metric-cagr {
        font-size: 1.5rem;
        font-weight: 600;
    }

    .metric-note {
        font-size: 0.625rem;
        color: var(--text-muted);
        margin-top: 0.25rem;
    }

    .big-five-summary {
        padding: 1rem;
        background: var(--bg-secondary);
        border-radius: 6px;
    }

    /* 4Ms Grid */
    .four-ms-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
    }

    .ms-card {
        padding: 1rem;
        background: var(--bg-secondary);
        border-radius: 8px;
    }

    .ms-card h4 {
        margin-bottom: 0.5rem;
    }

    .ms-score {
        font-size: 1.25rem;
        padding: 0.25rem 0.75rem;
        margin-bottom: 0.75rem;
        display: inline-block;
    }

    .ms-notes {
        list-style: none;
        font-size: 0.75rem;
        color: var(--text-secondary);
    }

    .ms-notes li {
        margin-bottom: 0.25rem;
        padding-left: 1rem;
        position: relative;
    }

    .ms-notes li::before {
        content: "•";
        position: absolute;
        left: 0;
    }

    .recommendation-summary {
        padding: 1rem;
        background: var(--bg-secondary);
        border-radius: 6px;
    }

    .recommendation-summary ul {
        list-style: none;
        margin-top: 0.75rem;
    }

    .recommendation-summary li {
        padding: 0.25rem 0;
        padding-left: 1.5rem;
        position: relative;
    }

    .recommendation-summary li::before {
        content: "→";
        position: absolute;
        left: 0;
        color: var(--accent-primary);
    }

    .score-display {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .score {
        font-size: 1.25rem;
        font-weight: 600;
    }
</style>
