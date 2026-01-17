<script lang="ts">
    import { onMount } from 'svelte';
    import { stocks, type StockPrice } from '$lib/api/client';
    import { stocksData, stocksLoaded, stocksLoading, stocksError } from '$lib/stores/stocks';

    // Use store values
    let priceData: StockPrice[] = [];
    let loading = true;
    let error = '';
    let searchQuery = '';
    let limit = 200;
    let viewMode: 'table' | 'grid' = 'table';

    // Sorting
    type SortKey = 'symbol' | 'ltp' | 'change' | 'change_pct' | 'volume' | 'high' | 'low';
    let sortKey: SortKey = 'symbol';
    let sortDirection: 'asc' | 'desc' = 'asc';

    // Filtering
    type FilterType = 'all' | 'gainers' | 'losers' | 'unchanged';
    let activeFilter: FilterType = 'all';

    // Subscribe to stores
    stocksData.subscribe(v => priceData = v);
    stocksLoading.subscribe(v => loading = v);
    stocksError.subscribe(v => error = v);

    // Filter -> Search -> Sort pipeline
    $: filteredByType = priceData.filter(stock => {
        if (activeFilter === 'all') return true;
        if (activeFilter === 'gainers') return (stock.change ?? 0) > 0;
        if (activeFilter === 'losers') return (stock.change ?? 0) < 0;
        if (activeFilter === 'unchanged') return (stock.change ?? 0) === 0;
        return true;
    });

    $: searchedStocks = filteredByType.filter(stock =>
        stock.symbol?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    $: sortedStocks = [...searchedStocks].sort((a, b) => {
        let aVal: any = a[sortKey];
        let bVal: any = b[sortKey];

        // Handle nulls/undefined
        if (aVal === null || aVal === undefined) aVal = sortDirection === 'asc' ? Infinity : -Infinity;
        if (bVal === null || bVal === undefined) bVal = sortDirection === 'asc' ? Infinity : -Infinity;

        // String comparison for symbol
        if (sortKey === 'symbol') {
            return sortDirection === 'asc'
                ? String(aVal).localeCompare(String(bVal))
                : String(bVal).localeCompare(String(aVal));
        }

        // Numeric comparison for others
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });

    // Stats computed from filtered (not searched) data
    $: totalStocks = priceData.length;
    $: gainersCount = priceData.filter(s => (s.change ?? 0) > 0).length;
    $: losersCount = priceData.filter(s => (s.change ?? 0) < 0).length;
    $: unchangedCount = priceData.filter(s => (s.change ?? 0) === 0).length;

    onMount(async () => {
        // Only fetch if not already loaded
        let isLoaded = false;
        stocksLoaded.subscribe(v => isLoaded = v)();

        if (!isLoaded) {
            await loadPrices();
        }
    });

    async function loadPrices() {
        stocksLoading.set(true);
        stocksError.set('');

        const result = await stocks.getPrices(limit);

        if (result.error) {
            stocksError.set(result.error);
        } else if (result.data) {
            stocksData.set(result.data);
            stocksLoaded.set(true);
        }

        stocksLoading.set(false);
    }

    function handleSort(key: SortKey) {
        if (sortKey === key) {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            sortKey = key;
            sortDirection = key === 'symbol' ? 'asc' : 'desc'; // Default desc for numbers
        }
    }

    function setFilter(filter: FilterType) {
        activeFilter = filter;
    }

    function clearFilters() {
        activeFilter = 'all';
        searchQuery = '';
        sortKey = 'symbol';
        sortDirection = 'asc';
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
    <title>Stocks - Stokr</title>
</svelte:head>

<div class="stocks-page">
    <!-- Page Header -->
    <div class="page-header">
        <div class="header-content">
            <h1>Stocks</h1>
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
        <!-- Filter Tabs -->
        <div class="filter-bar animate-fadeIn">
            <div class="filter-tabs">
                <button
                    class="filter-tab"
                    class:active={activeFilter === 'all'}
                    on:click={() => setFilter('all')}
                >
                    All <span class="filter-count">{totalStocks}</span>
                </button>
                <button
                    class="filter-tab gainers"
                    class:active={activeFilter === 'gainers'}
                    on:click={() => setFilter('gainers')}
                >
                    Gainers <span class="filter-count positive">{gainersCount}</span>
                </button>
                <button
                    class="filter-tab losers"
                    class:active={activeFilter === 'losers'}
                    on:click={() => setFilter('losers')}
                >
                    Losers <span class="filter-count negative">{losersCount}</span>
                </button>
                <button
                    class="filter-tab"
                    class:active={activeFilter === 'unchanged'}
                    on:click={() => setFilter('unchanged')}
                >
                    Unchanged <span class="filter-count">{unchangedCount}</span>
                </button>
            </div>

            {#if activeFilter !== 'all' || searchQuery}
                <button class="clear-filters-btn" on:click={clearFilters}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                    Clear filters
                </button>
            {/if}

            <div class="filter-actions">
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
            </div>
        </div>

        <!-- Results count -->
        <div class="results-info mt-2">
            <span class="results-count">Showing {sortedStocks.length} of {totalStocks} stocks</span>
            {#if sortKey !== 'symbol' || sortDirection !== 'asc'}
                <span class="sort-indicator">
                    Sorted by {sortKey === 'change_pct' ? 'change %' : sortKey}
                    {sortDirection === 'asc' ? '↑' : '↓'}
                </span>
            {/if}
        </div>

        {#if viewMode === 'table'}
            <!-- Table View -->
            <div class="card stocks-card mt-3 animate-fadeIn stagger-2">
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>
                                    <button class="sort-header" on:click={() => handleSort('symbol')}>
                                        Symbol
                                        <span class="sort-icon" class:active={sortKey === 'symbol'}>
                                            {sortKey === 'symbol' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right">
                                    <button class="sort-header" on:click={() => handleSort('ltp')}>
                                        LTP
                                        <span class="sort-icon" class:active={sortKey === 'ltp'}>
                                            {sortKey === 'ltp' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right">
                                    <button class="sort-header" on:click={() => handleSort('change_pct')}>
                                        Change
                                        <span class="sort-icon" class:active={sortKey === 'change_pct'}>
                                            {sortKey === 'change_pct' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right">
                                    <button class="sort-header" on:click={() => handleSort('high')}>
                                        High
                                        <span class="sort-icon" class:active={sortKey === 'high'}>
                                            {sortKey === 'high' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right">
                                    <button class="sort-header" on:click={() => handleSort('low')}>
                                        Low
                                        <span class="sort-icon" class:active={sortKey === 'low'}>
                                            {sortKey === 'low' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right">
                                    <button class="sort-header" on:click={() => handleSort('volume')}>
                                        Volume
                                        <span class="sort-icon" class:active={sortKey === 'volume'}>
                                            {sortKey === 'volume' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each sortedStocks as stock, i}
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

                {#if sortedStocks.length === 0}
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
                {#each sortedStocks as stock, i}
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

            {#if sortedStocks.length === 0}
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

    /* Filter Bar */
    .filter-bar {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.75rem 1rem;
        background: var(--bg-card);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-card);
        border: 1px solid var(--border-light);
        flex-wrap: wrap;
    }

    .filter-tabs {
        display: flex;
        gap: 0.25rem;
        flex-wrap: wrap;
    }

    .filter-tab {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: transparent;
        border: none;
        border-radius: var(--radius-md);
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--text-secondary);
        cursor: pointer;
        transition: all var(--duration-fast) var(--ease-out-expo);
    }

    .filter-tab:hover {
        background: var(--bg-secondary);
        color: var(--text-primary);
    }

    .filter-tab.active {
        background: var(--accent-primary);
        color: white;
    }

    .filter-tab.active .filter-count {
        background: rgba(255, 255, 255, 0.2);
        color: white;
    }

    .filter-count {
        padding: 0.125rem 0.5rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-full);
        font-size: 0.6875rem;
        font-weight: 700;
    }

    .filter-count.positive {
        color: var(--success);
    }

    .filter-count.negative {
        color: var(--danger);
    }

    .clear-filters-btn {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.375rem 0.75rem;
        background: transparent;
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--text-muted);
        cursor: pointer;
        transition: all var(--duration-fast) var(--ease-out-expo);
    }

    .clear-filters-btn:hover {
        background: var(--danger);
        border-color: var(--danger);
        color: white;
    }

    .filter-actions {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-left: auto;
    }

    /* Results Info */
    .results-info {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.5rem 0;
    }

    .results-count {
        font-size: 0.8125rem;
        color: var(--text-muted);
    }

    .sort-indicator {
        font-size: 0.75rem;
        color: var(--accent-primary);
        font-weight: 500;
    }

    /* Sortable Headers */
    .sort-header {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        background: none;
        border: none;
        padding: 0;
        font: inherit;
        color: inherit;
        cursor: pointer;
        white-space: nowrap;
    }

    .sort-header:hover {
        color: var(--accent-primary);
    }

    .sort-icon {
        font-size: 0.75rem;
        opacity: 0.3;
        transition: opacity var(--duration-fast) var(--ease-out-expo);
    }

    .sort-icon.active {
        opacity: 1;
        color: var(--accent-primary);
    }

    .sort-header:hover .sort-icon {
        opacity: 0.7;
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

        .filter-bar {
            gap: 0.75rem;
        }

        .filter-tabs {
            width: 100%;
            justify-content: flex-start;
            overflow-x: auto;
            padding-bottom: 0.5rem;
        }

        .filter-tab {
            padding: 0.375rem 0.75rem;
            font-size: 0.75rem;
        }

        .filter-actions {
            width: 100%;
            justify-content: flex-end;
            margin-left: 0;
        }

        .results-info {
            flex-wrap: wrap;
            gap: 0.5rem;
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
        .filter-tab {
            padding: 0.25rem 0.5rem;
            font-size: 0.6875rem;
        }

        .filter-count {
            display: none;
        }

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
