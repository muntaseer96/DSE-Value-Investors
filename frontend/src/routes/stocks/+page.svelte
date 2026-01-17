<script lang="ts">
    import { onMount } from 'svelte';
    import { stocks, type StockPrice } from '$lib/api/client';

    let priceData: StockPrice[] = [];
    let loading = true;
    let error = '';
    let searchQuery = '';
    let limit = 50;

    $: filteredStocks = priceData.filter(stock =>
        stock.symbol?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    onMount(async () => {
        await loadPrices();
    });

    async function loadPrices() {
        loading = true;
        error = '';

        const result = await stocks.getPrices(limit);

        if (result.error) {
            error = result.error;
        } else if (result.data) {
            priceData = result.data;
        }

        loading = false;
    }

    function formatPrice(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        return `৳${value.toFixed(2)}`;
    }

    function formatVolume(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        if (value >= 1000000) return `${(value / 1000000).toFixed(2)}M`;
        if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
        return value.toString();
    }

    function getChangeClass(value: number | undefined | null): string {
        if (value === undefined || value === null) return '';
        return value >= 0 ? 'positive' : 'negative';
    }
</script>

<div class="stocks-page">
    <div class="page-header">
        <h1>DSE Stocks</h1>
        <div class="header-actions">
            <input
                type="text"
                placeholder="Search stocks..."
                bind:value={searchQuery}
                class="search-input"
            />
            <button class="btn btn-secondary" on:click={loadPrices}>
                Refresh
            </button>
        </div>
    </div>

    {#if loading}
        <div class="loading">
            <div class="spinner"></div>
        </div>
    {:else if error}
        <div class="error">
            <p><strong>Error:</strong> {error}</p>
            <p class="mt-1 text-muted">Make sure the backend server is running</p>
        </div>
    {:else}
        <div class="card">
            <div class="card-header">
                <h2>Live Prices ({filteredStocks.length})</h2>
                <div class="limit-selector">
                    <label>Show:</label>
                    <select bind:value={limit} on:change={loadPrices}>
                        <option value={30}>30</option>
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                        <option value={200}>200</option>
                    </select>
                </div>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th class="text-right">LTP</th>
                            <th class="text-right">Change</th>
                            <th class="text-right">High</th>
                            <th class="text-right">Low</th>
                            <th class="text-right">Volume</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each filteredStocks as stock}
                            <tr>
                                <td>
                                    <a href="/stocks/{stock.symbol}" class="stock-link">
                                        {stock.symbol}
                                    </a>
                                </td>
                                <td class="text-right font-medium">{formatPrice(stock.ltp)}</td>
                                <td class="text-right {getChangeClass(stock.change)}">
                                    {#if stock.change !== undefined && stock.change !== null}
                                        {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}
                                        {#if stock.change_pct !== undefined && stock.change_pct !== null}
                                            <span class="change-pct">
                                                ({stock.change_pct >= 0 ? '+' : ''}{stock.change_pct.toFixed(2)}%)
                                            </span>
                                        {/if}
                                    {:else}
                                        -
                                    {/if}
                                </td>
                                <td class="text-right">{formatPrice(stock.high)}</td>
                                <td class="text-right">{formatPrice(stock.low)}</td>
                                <td class="text-right">{formatVolume(stock.volume)}</td>
                                <td>
                                    <a href="/calculator?symbol={stock.symbol}" class="btn btn-primary btn-sm">
                                        Analyze
                                    </a>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>

            {#if filteredStocks.length === 0}
                <div class="empty-state">
                    <p>No stocks found matching "{searchQuery}"</p>
                </div>
            {/if}
        </div>
    {/if}
</div>

<style>
    .stocks-page {
        max-width: 1200px;
        margin: 0 auto;
    }

    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
        gap: 1rem;
    }

    .header-actions {
        display: flex;
        gap: 0.75rem;
        align-items: center;
    }

    .search-input {
        width: 250px;
    }

    .limit-selector {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .limit-selector select {
        width: auto;
        padding: 0.375rem 0.75rem;
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

    .font-medium {
        font-weight: 500;
    }

    .change-pct {
        font-size: 0.75rem;
        opacity: 0.8;
    }

    .btn-sm {
        padding: 0.25rem 0.5rem;
        font-size: 0.75rem;
    }

    .empty-state {
        text-align: center;
        padding: 2rem;
        color: var(--text-secondary);
    }

    @media (max-width: 768px) {
        .page-header {
            flex-direction: column;
            align-items: stretch;
        }

        .header-actions {
            flex-direction: column;
        }

        .search-input {
            width: 100%;
        }
    }
</style>
