<script lang="ts">
    import { onMount } from 'svelte';
    import { portfolio, type PortfolioSummary, type HoldingResponse } from '$lib/api/client';

    let data: PortfolioSummary | null = null;
    let loading = true;
    let error = '';

    onMount(async () => {
        await loadPortfolio();
    });

    async function loadPortfolio() {
        loading = true;
        error = '';

        const result = await portfolio.get();

        if (result.error) {
            error = result.error;
        } else if (result.data) {
            data = result.data;
        }

        loading = false;
    }

    async function seedPortfolio() {
        const result = await portfolio.seed();
        if (result.data) {
            await loadPortfolio();
        }
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
</script>

<div class="portfolio-page">
    <div class="page-header">
        <h1>My Portfolio</h1>
        <div class="header-actions">
            <button class="btn btn-secondary" on:click={loadPortfolio}>
                Refresh
            </button>
            {#if !data || data.holdings_count === 0}
                <button class="btn btn-primary" on:click={seedPortfolio}>
                    Load My Stocks
                </button>
            {/if}
        </div>
    </div>

    {#if loading}
        <div class="loading">
            <div class="spinner"></div>
        </div>
    {:else if error}
        <div class="error">
            <p><strong>Error:</strong> {error}</p>
            <p class="mt-1 text-muted">Make sure the backend server is running on port 8000</p>
        </div>
    {:else if data}
        <!-- Summary Cards -->
        <div class="grid grid-4 summary-cards">
            <div class="card summary-card">
                <div class="summary-label">Total Invested</div>
                <div class="summary-value">{formatCurrency(data.total_invested)}</div>
            </div>
            <div class="card summary-card">
                <div class="summary-label">Current Value</div>
                <div class="summary-value">{formatCurrency(data.current_value)}</div>
            </div>
            <div class="card summary-card">
                <div class="summary-label">Total P&L</div>
                <div class="summary-value {getPnlClass(data.total_profit_loss)}">
                    {formatCurrency(data.total_profit_loss)}
                </div>
            </div>
            <div class="card summary-card">
                <div class="summary-label">Return</div>
                <div class="summary-value {getPnlClass(data.total_profit_loss_pct)}">
                    {formatPercent(data.total_profit_loss_pct)}
                </div>
            </div>
        </div>

        <!-- Holdings Table -->
        <div class="card mt-2">
            <div class="card-header">
                <h2>Holdings ({data.holdings_count})</h2>
            </div>

            {#if data.holdings.length === 0}
                <div class="empty-state">
                    <p>No holdings yet. Click "Load My Stocks" to add your portfolio.</p>
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
                                <th class="text-right">Value</th>
                                <th class="text-right">P&L</th>
                                <th class="text-right">Return</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each data.holdings as holding}
                                <tr>
                                    <td>
                                        <a href="/stocks/{holding.stock_symbol}" class="stock-link">
                                            {holding.stock_symbol}
                                        </a>
                                    </td>
                                    <td class="text-right">{holding.shares}</td>
                                    <td class="text-right">{formatCurrency(holding.avg_cost)}</td>
                                    <td class="text-right">
                                        {holding.current_price ? formatCurrency(holding.current_price) : '-'}
                                    </td>
                                    <td class="text-right">
                                        {holding.current_value ? formatCurrency(holding.current_value) : '-'}
                                    </td>
                                    <td class="text-right {getPnlClass(holding.profit_loss)}">
                                        {holding.profit_loss !== undefined ? formatCurrency(holding.profit_loss) : '-'}
                                    </td>
                                    <td class="text-right {getPnlClass(holding.profit_loss_pct)}">
                                        {holding.profit_loss_pct !== undefined ? formatPercent(holding.profit_loss_pct) : '-'}
                                    </td>
                                    <td>
                                        <a href="/calculator?symbol={holding.stock_symbol}" class="btn btn-secondary btn-sm">
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

    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
    }

    .header-actions {
        display: flex;
        gap: 0.75rem;
    }

    .summary-cards {
        margin-bottom: 1.5rem;
    }

    .summary-card {
        text-align: center;
        padding: 1.25rem;
    }

    .summary-label {
        color: var(--text-secondary);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    .summary-value {
        font-size: 1.5rem;
        font-weight: 600;
    }

    .table-container {
        overflow-x: auto;
    }

    .stock-link {
        color: var(--accent-primary);
        text-decoration: none;
        font-weight: 500;
    }

    .stock-link:hover {
        text-decoration: underline;
    }

    .btn-sm {
        padding: 0.25rem 0.5rem;
        font-size: 0.75rem;
    }

    .empty-state {
        text-align: center;
        padding: 3rem;
        color: var(--text-secondary);
    }

    @media (max-width: 768px) {
        .page-header {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
        }

        .summary-cards {
            grid-template-columns: repeat(2, 1fr);
        }
    }
</style>
