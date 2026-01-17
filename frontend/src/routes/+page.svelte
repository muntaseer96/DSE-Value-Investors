<script lang="ts">
    import { onMount } from 'svelte';
    import { portfolio, type PortfolioSummary, type HoldingResponse } from '$lib/api/client';
    import { portfolioData, portfolioLoaded, portfolioLoading, portfolioError } from '$lib/stores/portfolio';

    // Use store values
    let data: PortfolioSummary | null = null;
    let loading = true;
    let error = '';

    // Subscribe to stores
    portfolioData.subscribe(v => data = v);
    portfolioLoading.subscribe(v => loading = v);
    portfolioError.subscribe(v => error = v);

    onMount(async () => {
        // Only fetch if not already loaded
        let isLoaded = false;
        portfolioLoaded.subscribe(v => isLoaded = v)();

        if (!isLoaded) {
            await loadPortfolio();
        }
    });

    async function loadPortfolio() {
        portfolioLoading.set(true);
        portfolioError.set('');

        const result = await portfolio.get();

        if (result.error) {
            portfolioError.set(result.error);
        } else if (result.data) {
            portfolioData.set(result.data);
            portfolioLoaded.set(true);
        }

        portfolioLoading.set(false);
    }

    function formatCurrency(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        return new Intl.NumberFormat('en-BD', {
            style: 'currency',
            currency: 'BDT',
            minimumFractionDigits: 2,
        }).format(value);
    }

    function formatPercent(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        const sign = value >= 0 ? '+' : '';
        return `${sign}${value.toFixed(2)}%`;
    }

    function getPnlClass(value: number | undefined | null): string {
        if (value === undefined || value === null) return 'neutral';
        return value >= 0 ? 'positive' : 'negative';
    }

    function getPnlIcon(value: number | undefined | null): string {
        if (value === undefined || value === null || value === 0) return '';
        return value >= 0 ? '↑' : '↓';
    }
</script>

<svelte:head>
    <title>Portfolio - DSE Value Investor</title>
</svelte:head>

<div class="portfolio-page">
    <!-- Page Header -->
    <div class="page-header">
        <div class="header-content">
            <h1>My Portfolio</h1>
            <p class="header-subtitle">Track your DSE investments with Rule #1 methodology</p>
        </div>
        <div class="header-actions">
            <button class="btn btn-secondary" on:click={loadPortfolio}>
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
                <p><strong>Connection Error</strong></p>
                <p class="text-muted">Make sure the backend server is running on port 8000</p>
            </div>
        </div>
    {:else if data}
        <!-- Hero Summary Card -->
        <div class="portfolio-hero animate-fadeIn">
            <div class="hero-accent"></div>
            <div class="hero-content">
                <div class="hero-main">
                    <span class="hero-label">Total Portfolio Value</span>
                    <h2 class="hero-value">{formatCurrency(data.current_value)}</h2>
                    <div class="hero-pnl {getPnlClass(data.total_profit_loss)}">
                        <span class="pnl-icon">{getPnlIcon(data.total_profit_loss)}</span>
                        <span class="pnl-amount">{formatCurrency(data.total_profit_loss)}</span>
                        <span class="pnl-badge {getPnlClass(data.total_profit_loss_pct)}">
                            {formatPercent(data.total_profit_loss_pct)}
                        </span>
                    </div>
                </div>
                <div class="hero-metrics">
                    <div class="hero-metric">
                        <span class="metric-label">Invested</span>
                        <span class="metric-value">{formatCurrency(data.total_invested)}</span>
                    </div>
                    <div class="hero-metric">
                        <span class="metric-label">Holdings</span>
                        <span class="metric-value">{data.holdings_count}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Holdings Table Card -->
        <div class="card holdings-card mt-3 animate-fadeIn stagger-2">
            <div class="card-header">
                <h2>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 0.5rem; vertical-align: -2px;">
                        <rect x="3" y="3" width="7" height="7"/>
                        <rect x="14" y="3" width="7" height="7"/>
                        <rect x="14" y="14" width="7" height="7"/>
                        <rect x="3" y="14" width="7" height="7"/>
                    </svg>
                    Holdings
                </h2>
                <span class="badge badge-neutral">{data.holdings_count} stocks</span>
            </div>

            {#if data.holdings.length === 0}
                <div class="empty-state">
                    <svg class="empty-state-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <rect x="3" y="3" width="18" height="18" rx="2"/>
                        <path d="M3 9h18"/>
                        <path d="M9 21V9"/>
                    </svg>
                    <h3>No holdings yet</h3>
                    <p>Add holdings via the Data Entry page to start tracking your portfolio.</p>
                </div>
            {:else}
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Stock</th>
                                <th class="text-right">Shares</th>
                                <th class="text-right">Avg Cost</th>
                                <th class="text-right">Current</th>
                                <th class="text-right">Total Cost</th>
                                <th class="text-right">Value</th>
                                <th class="text-right">P&L</th>
                                <th class="text-right">Return</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each data.holdings as holding, i}
                                <tr class="animate-fadeIn" style="animation-delay: {50 + i * 30}ms">
                                    <td>
                                        <a href="/stocks/{holding.stock_symbol}" class="stock-cell">
                                            <span class="stock-symbol">{holding.stock_symbol}</span>
                                        </a>
                                    </td>
                                    <td class="text-right tabular-nums">
                                        {holding.shares.toLocaleString()}
                                    </td>
                                    <td class="text-right tabular-nums">
                                        {formatCurrency(holding.avg_cost)}
                                    </td>
                                    <td class="text-right tabular-nums">
                                        {holding.current_price ? formatCurrency(holding.current_price) : '-'}
                                    </td>
                                    <td class="text-right tabular-nums">
                                        {formatCurrency(holding.shares * holding.avg_cost)}
                                    </td>
                                    <td class="text-right tabular-nums font-medium">
                                        {holding.current_value ? formatCurrency(holding.current_value) : '-'}
                                    </td>
                                    <td class="text-right tabular-nums {getPnlClass(holding.profit_loss)}">
                                        <span class="pnl-cell">
                                            {holding.profit_loss !== undefined ? formatCurrency(holding.profit_loss) : '-'}
                                        </span>
                                    </td>
                                    <td class="text-right">
                                        {#if holding.profit_loss_pct !== undefined}
                                            <span class="return-badge {getPnlClass(holding.profit_loss_pct)}">
                                                {formatPercent(holding.profit_loss_pct)}
                                            </span>
                                        {:else}
                                            -
                                        {/if}
                                    </td>
                                    <td>
                                        <a href="/calculator?symbol={holding.stock_symbol}" class="btn btn-sm btn-secondary">
                                            Analyze
                                        </a>
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            {/if}
        </div>
    {/if}
</div>

<style>
    .portfolio-page {
        max-width: 1200px;
        margin: 0 auto;
    }

    /* Page Header */
    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 2rem;
        gap: 1rem;
    }

    .header-content h1 {
        margin-bottom: 0.25rem;
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

    /* Hero Card */
    .portfolio-hero {
        position: relative;
        background: var(--bg-card);
        border-radius: var(--radius-xl);
        padding: 2rem;
        box-shadow: var(--shadow-lg);
        overflow: hidden;
        border: 1px solid var(--border-light);
    }

    .hero-accent {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
    }

    .hero-content {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 2rem;
    }

    .hero-main {
        flex: 1;
    }

    .hero-label {
        display: block;
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    .hero-value {
        font-family: 'DM Serif Display', Georgia, serif;
        font-size: 2.75rem;
        font-weight: 400;
        color: var(--text-primary);
        margin: 0 0 0.75rem;
        line-height: 1.1;
    }

    .hero-pnl {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .pnl-icon {
        font-size: 1rem;
        font-weight: 600;
    }

    .pnl-amount {
        font-size: 1.125rem;
        font-weight: 600;
    }

    .pnl-badge {
        display: inline-flex;
        padding: 0.25rem 0.625rem;
        border-radius: var(--radius-full);
        font-size: 0.75rem;
        font-weight: 700;
    }

    .pnl-badge.positive {
        background: rgba(5, 150, 105, 0.12);
    }

    .pnl-badge.negative {
        background: rgba(220, 38, 38, 0.12);
    }

    .hero-metrics {
        display: flex;
        gap: 2.5rem;
    }

    .hero-metric {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .metric-label {
        font-size: 0.6875rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .metric-value {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    /* Holdings Card */
    .holdings-card {
        padding: 0;
    }

    .holdings-card .card-header {
        padding: 1.25rem 1.5rem;
        margin-bottom: 0;
    }

    .holdings-card .card-header h2 {
        display: flex;
        align-items: center;
    }

    /* Table Styles */
    .table-container {
        overflow-x: auto;
    }

    table {
        margin: 0;
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

    .stock-cell {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        text-decoration: none;
    }

    .stock-symbol {
        font-weight: 600;
        color: var(--accent-primary);
        transition: color var(--duration-fast) var(--ease-out-expo);
    }

    .stock-cell:hover .stock-symbol {
        color: var(--accent-hover);
    }

    .pnl-cell {
        font-weight: 500;
    }

    .return-badge {
        display: inline-flex;
        padding: 0.25rem 0.5rem;
        border-radius: var(--radius-sm);
        font-size: 0.75rem;
        font-weight: 600;
    }

    .return-badge.positive {
        background: rgba(5, 150, 105, 0.12);
    }

    .return-badge.negative {
        background: rgba(220, 38, 38, 0.12);
    }

    /* Empty State */
    .empty-state {
        padding: 4rem 2rem;
    }

    /* Error state */
    .error {
        display: flex;
        align-items: flex-start;
        gap: 1rem;
    }

    .error svg {
        flex-shrink: 0;
        margin-top: 2px;
    }

    /* Responsive */
    @media (max-width: 1024px) {
        .hero-content {
            flex-direction: column;
            gap: 1.5rem;
        }

        .hero-metrics {
            width: 100%;
            border-top: 1px solid var(--border-light);
            padding-top: 1.5rem;
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

        .portfolio-hero {
            padding: 1.5rem;
        }

        .hero-value {
            font-size: 2rem;
        }

        .hero-metrics {
            gap: 1.5rem;
        }

        /* Hide less important columns on mobile: Avg Cost (3), Total Cost (5) */
        th:nth-child(3),
        td:nth-child(3),
        th:nth-child(5),
        td:nth-child(5) {
            display: none;
        }
    }

    @media (max-width: 480px) {
        /* Also hide P&L (7) on very small screens */
        th:nth-child(7),
        td:nth-child(7) {
            display: none;
        }
    }
</style>
