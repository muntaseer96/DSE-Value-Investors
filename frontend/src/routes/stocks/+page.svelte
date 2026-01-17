<script lang="ts">
    import { onMount } from 'svelte';
    import { stocks, type StockPrice } from '$lib/api/client';

    let priceData: StockPrice[] = [];
    let loading = true;
    let error = '';
    let searchQuery = '';
    let limit = 50;
    let viewMode: 'table' | 'grid' = 'table';

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

    function getChangeIcon(value: number | undefined | null): string {
        if (value === undefined || value === null || value === 0) return '';
        return value >= 0 ? '↑' : '↓';
    }
</script>

<svelte:head>
    <title>Stocks - DSE Value Investor</title>
</svelte:head>

<div class="stocks-page">
    <!-- Page Header -->
    <div class="page-header">
        <div class="header-content">
            <h1>DSE Stocks</h1>
            <p class="header-subtitle">Live prices from Dhaka Stock Exchange</p>
        </div>
        <div class="header-actions">
            <div class="search-wrapper">
                <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="M21 21l-4.35-4.35"/>
                </svg>
                <input
                    type="text"
                    placeholder="Search stocks..."
                    bind:value={searchQuery}
                    class="search-input"
                />
            </div>
            <button class="btn btn-secondary" on:click={loadPrices}>
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
                <p><strong>Error loading stocks</strong></p>
                <p class="text-muted">Make sure the backend server is running</p>
            </div>
        </div>
    {:else}
        <!-- Stats Bar -->
        <div class="stats-bar animate-fadeIn">
            <div class="stat-item">
                <span class="stat-value">{filteredStocks.length}</span>
                <span class="stat-label">Stocks</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
                <span class="stat-value positive">
                    {filteredStocks.filter(s => s.change && s.change > 0).length}
                </span>
                <span class="stat-label">Gainers</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
                <span class="stat-value negative">
                    {filteredStocks.filter(s => s.change && s.change < 0).length}
                </span>
                <span class="stat-label">Losers</span>
            </div>
            <div class="stat-actions">
                <div class="view-toggle">
                    <button
                        class="toggle-btn"
                        class:active={viewMode === 'table'}
                        on:click={() => viewMode = 'table'}
                        aria-label="Table view"
                    >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="3" width="18" height="18" rx="2"/>
                            <path d="M3 9h18M9 21V9"/>
                        </svg>
                    </button>
                    <button
                        class="toggle-btn"
                        class:active={viewMode === 'grid'}
                        on:click={() => viewMode = 'grid'}
                        aria-label="Grid view"
                    >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="3" width="7" height="7"/>
                            <rect x="14" y="3" width="7" height="7"/>
                            <rect x="14" y="14" width="7" height="7"/>
                            <rect x="3" y="14" width="7" height="7"/>
                        </svg>
                    </button>
                </div>
                <div class="limit-selector">
                    <label for="limit-select">Show:</label>
                    <select id="limit-select" bind:value={limit} on:change={loadPrices}>
                        <option value={30}>30</option>
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                        <option value={200}>200</option>
                    </select>
                </div>
            </div>
        </div>

        {#if viewMode === 'table'}
            <!-- Table View -->
            <div class="card stocks-card mt-3 animate-fadeIn stagger-2">
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
                            {#each filteredStocks as stock, i}
                                <tr class="animate-fadeIn" style="animation-delay: {30 + i * 20}ms">
                                    <td>
                                        <a href="/stocks/{stock.symbol}" class="stock-cell">
                                            <span class="stock-symbol">{stock.symbol}</span>
                                        </a>
                                    </td>
                                    <td class="text-right tabular-nums font-semibold">
                                        {formatPrice(stock.ltp)}
                                    </td>
                                    <td class="text-right {getChangeClass(stock.change)}">
                                        <div class="change-cell">
                                            {#if stock.change !== undefined && stock.change !== null}
                                                <span class="change-icon">{getChangeIcon(stock.change)}</span>
                                                <span class="change-value tabular-nums">
                                                    {Math.abs(stock.change).toFixed(2)}
                                                </span>
                                                {#if stock.change_pct !== undefined && stock.change_pct !== null}
                                                    <span class="change-pct">
                                                        ({Math.abs(stock.change_pct).toFixed(2)}%)
                                                    </span>
                                                {/if}
                                            {:else}
                                                -
                                            {/if}
                                        </div>
                                    </td>
                                    <td class="text-right tabular-nums text-muted">{formatPrice(stock.high)}</td>
                                    <td class="text-right tabular-nums text-muted">{formatPrice(stock.low)}</td>
                                    <td class="text-right tabular-nums">{formatVolume(stock.volume)}</td>
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
                        <svg class="empty-state-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="11" cy="11" r="8"/>
                            <path d="M21 21l-4.35-4.35"/>
                        </svg>
                        <h3>No stocks found</h3>
                        <p>No stocks matching "{searchQuery}"</p>
                    </div>
                {/if}
            </div>
        {:else}
            <!-- Grid View -->
            <div class="stocks-grid mt-3 animate-fadeIn stagger-2">
                {#each filteredStocks as stock, i}
                    <a href="/stocks/{stock.symbol}" class="stock-card animate-fadeIn" style="animation-delay: {30 + i * 15}ms">
                        <div class="stock-card-header">
                            <span class="stock-card-symbol">{stock.symbol}</span>
                            <span class="stock-card-change {getChangeClass(stock.change)}">
                                {#if stock.change_pct !== undefined && stock.change_pct !== null}
                                    {getChangeIcon(stock.change)}
                                    {Math.abs(stock.change_pct).toFixed(2)}%
                                {:else}
                                    -
                                {/if}
                            </span>
                        </div>
                        <div class="stock-card-price">{formatPrice(stock.ltp)}</div>
                        <div class="stock-card-meta">
                            <span>Vol: {formatVolume(stock.volume)}</span>
                            <span>H: {formatPrice(stock.high)}</span>
                            <span>L: {formatPrice(stock.low)}</span>
                        </div>
                    </a>
                {/each}
            </div>

            {#if filteredStocks.length === 0}
                <div class="empty-state mt-3">
                    <svg class="empty-state-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="M21 21l-4.35-4.35"/>
                    </svg>
                    <h3>No stocks found</h3>
                    <p>No stocks matching "{searchQuery}"</p>
                </div>
            {/if}
        {/if}
    {/if}
</div>

<style>
    .stocks-page {
        max-width: 1200px;
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
        align-items: center;
        flex-wrap: wrap;
    }

    .search-wrapper {
        position: relative;
    }

    .search-icon {
        position: absolute;
        left: 0.875rem;
        top: 50%;
        transform: translateY(-50%);
        color: var(--text-muted);
        pointer-events: none;
    }

    .search-input {
        width: 280px;
        padding-left: 2.5rem;
    }

    /* Stats Bar */
    .stats-bar {
        display: flex;
        align-items: center;
        gap: 1.5rem;
        padding: 1rem 1.5rem;
        background: var(--bg-card);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-card);
        border: 1px solid var(--border-light);
    }

    .stat-item {
        display: flex;
        flex-direction: column;
        gap: 0.125rem;
    }

    .stat-value {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-primary);
    }

    .stat-label {
        font-size: 0.6875rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .stat-divider {
        width: 1px;
        height: 32px;
        background: var(--border);
    }

    .stat-actions {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-left: auto;
    }

    .view-toggle {
        display: flex;
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
        padding: 0.25rem;
    }

    .toggle-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 32px;
        background: transparent;
        border: none;
        border-radius: var(--radius-sm);
        color: var(--text-muted);
        cursor: pointer;
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

    .limit-selector {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .limit-selector label {
        margin: 0;
        font-size: 0.8125rem;
        color: var(--text-muted);
    }

    .limit-selector select {
        width: auto;
        padding: 0.5rem 2rem 0.5rem 0.75rem;
        font-size: 0.8125rem;
    }

    /* Stocks Card */
    .stocks-card {
        padding: 0;
    }

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

    .stock-cell {
        display: flex;
        align-items: center;
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

    .change-cell {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.25rem;
    }

    .change-icon {
        font-size: 0.75rem;
    }

    .change-pct {
        font-size: 0.75rem;
        opacity: 0.8;
    }

    /* Grid View */
    .stocks-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 1rem;
    }

    .stock-card {
        display: flex;
        flex-direction: column;
        padding: 1.25rem;
        background: var(--bg-card);
        border-radius: var(--radius-lg);
        border: 1px solid var(--border-light);
        text-decoration: none;
        transition: all var(--duration-fast) var(--ease-out-expo);
    }

    .stock-card:hover {
        border-color: var(--accent-primary);
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }

    .stock-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
    }

    .stock-card-symbol {
        font-weight: 700;
        font-size: 0.9375rem;
        color: var(--text-primary);
    }

    .stock-card-change {
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.125rem 0.5rem;
        border-radius: var(--radius-full);
    }

    .stock-card-change.positive {
        background: rgba(5, 150, 105, 0.12);
    }

    .stock-card-change.negative {
        background: rgba(220, 38, 38, 0.12);
    }

    .stock-card-price {
        font-family: 'DM Serif Display', Georgia, serif;
        font-size: 1.5rem;
        color: var(--text-primary);
        margin-bottom: 0.75rem;
    }

    .stock-card-meta {
        display: flex;
        gap: 0.75rem;
        font-size: 0.6875rem;
        color: var(--text-muted);
    }

    /* Error */
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
    @media (max-width: 768px) {
        .page-header {
            flex-direction: column;
            align-items: stretch;
        }

        .header-actions {
            flex-direction: column;
            align-items: stretch;
        }

        .search-input {
            width: 100%;
        }

        .stats-bar {
            flex-wrap: wrap;
            gap: 1rem;
        }

        .stat-divider {
            display: none;
        }

        .stat-actions {
            width: 100%;
            justify-content: space-between;
            margin-left: 0;
            padding-top: 1rem;
            border-top: 1px solid var(--border-light);
        }

        /* Hide high/low on mobile */
        th:nth-child(4),
        td:nth-child(4),
        th:nth-child(5),
        td:nth-child(5) {
            display: none;
        }

        .stocks-grid {
            grid-template-columns: 1fr 1fr;
        }
    }

    @media (max-width: 480px) {
        .stocks-grid {
            grid-template-columns: 1fr;
        }

        /* Hide volume on small mobile */
        th:nth-child(6),
        td:nth-child(6) {
            display: none;
        }
    }
</style>
