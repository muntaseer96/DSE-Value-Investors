<script lang="ts">
    import { onMount } from 'svelte';
    import { usStocks, type USStockPrice, type USScrapeStatusResponse, type USFilterCountsResponse, type USStatsResponse } from '$lib/api/client';

    let priceData: USStockPrice[] = [];
    let loading = true;
    let error = '';
    let searchQuery = '';
    let viewMode: 'table' | 'grid' = 'table';

    // Scrape stats
    let scrapeStats: USStatsResponse | null = null;

    // Pagination
    let offset = 0;
    let limit = 100;
    let totalCount = 0;
    let totalValuationCount = 0;
    let hasMore = false;

    // Filter counts from database (not from loaded data)
    let filterCounts: USFilterCountsResponse = {
        total: 0,
        sp500: 0,
        gainers: 0,
        losers: 0,
        undervalued: 0,
        overvalued: 0,
        with_valuation: 0,
    };

    // Sorting
    type SortKey = 'symbol' | 'current_price' | 'change' | 'change_pct' | 'market_cap' | 'sticker_price' | 'margin_of_safety' | 'discount_pct' | 'four_m_score';
    let sortKey: SortKey = 'market_cap';
    let sortDirection: 'asc' | 'desc' = 'desc';

    // Filtering
    type FilterType = 'all' | 'sp500' | 'gainers' | 'losers' | 'undervalued' | 'overvalued';
    let activeFilter: FilterType = 'all';
    let selectedSector: string | null = null;
    let sectors: string[] = [];

    // Scrape state
    let scraping = false;
    let scrapeProgress: USScrapeStatusResponse | null = null;
    let scrapeError = '';

    // Search debounce
    let searchTimeout: ReturnType<typeof setTimeout> | null = null;
    let isSearching = false;

    // All filtering/sorting/search now happens server-side
    $: displayedStocks = priceData;

    // Debounced search - triggers server-side search
    function handleSearchInput(event: Event) {
        const value = (event.target as HTMLInputElement).value;
        searchQuery = value;

        // Clear existing timeout
        if (searchTimeout) clearTimeout(searchTimeout);

        // Debounce: wait 300ms after user stops typing
        searchTimeout = setTimeout(async () => {
            offset = 0; // Reset to first page on new search
            await loadPrices();
        }, 300);
    }

    // Stats from loaded data (for display purposes only)
    $: loadedStocksCount = priceData.length;

    onMount(async () => {
        await loadPrices();
        await loadSectors();
        await loadStats();
        await checkScrapeStatus();
    });

    async function loadStats() {
        const result = await usStocks.getStats();
        if (result.data) {
            scrapeStats = result.data;
        }
    }

    async function loadPrices() {
        loading = true;
        error = '';

        const options: any = { limit, offset, sortBy: sortKey, sortOrder: sortDirection };
        if (activeFilter === 'sp500') options.sp500Only = true;
        if (activeFilter === 'gainers') options.filterType = 'gainers';
        if (activeFilter === 'losers') options.filterType = 'losers';
        if (activeFilter === 'undervalued') options.filterType = 'undervalued';
        if (activeFilter === 'overvalued') options.filterType = 'overvalued';
        if (selectedSector) options.sector = selectedSector;
        if (searchQuery.trim()) options.search = searchQuery.trim();

        const result = await usStocks.getPrices(options);

        if (result.error) {
            error = result.error;
        } else if (result.data) {
            priceData = result.data;
            hasMore = result.data.length === limit;
        }

        // Get all filter counts in one request
        const filterCountsResult = await usStocks.getFilterCounts();
        if (filterCountsResult.data) {
            filterCounts = filterCountsResult.data;
            totalCount = filterCountsResult.data.total;
            totalValuationCount = filterCountsResult.data.with_valuation;
        } else {
            // Fallback to old count endpoint if filter-counts fails
            const countResult = await usStocks.getCount();
            if (countResult.data) {
                totalCount = countResult.data.total;
                // Use loaded data for filter counts as fallback
                filterCounts = {
                    total: countResult.data.total,
                    sp500: priceData.filter(s => s.is_sp500).length,
                    gainers: priceData.filter(s => (s.change ?? 0) > 0).length,
                    losers: priceData.filter(s => (s.change ?? 0) < 0).length,
                    undervalued: priceData.filter(s => s.valuation_status === 'CALCULABLE' && (s.discount_pct ?? 0) < 0).length,
                    overvalued: priceData.filter(s => s.valuation_status === 'CALCULABLE' && (s.discount_pct ?? 0) > 0).length,
                    with_valuation: priceData.filter(s => s.valuation_status === 'CALCULABLE').length,
                };
            }
            // Get valuation count
            const valCountResult = await usStocks.getCount(false, true);
            if (valCountResult.data) {
                totalValuationCount = valCountResult.data.total;
            }
        }

        loading = false;
    }

    async function loadSectors() {
        const result = await usStocks.getSectors();
        if (result.data) {
            sectors = result.data.sectors;
        }
    }

    async function checkScrapeStatus() {
        const result = await usStocks.getScrapeStatus();
        if (result.data) {
            scrapeProgress = result.data;
            if (result.data.running) {
                scraping = true;
                pollScrapeStatus();
            }
        }
    }

    function handleSort(key: SortKey) {
        if (sortKey === key) {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            sortKey = key;
            sortDirection = key === 'symbol' ? 'asc' : 'desc';
        }
        // Reset offset and reload with new sort
        offset = 0;
        loadPrices();
    }

    function setFilter(filter: FilterType) {
        activeFilter = filter;
        // Reset offset and reload with new filter
        offset = 0;
        loadPrices();
    }

    function clearFilters() {
        activeFilter = 'all';
        searchQuery = '';
        selectedSector = null;
        sortKey = 'market_cap';
        sortDirection = 'desc';
        offset = 0;
        loadPrices();
    }

    function formatPrice(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        return `$${value.toFixed(2)}`;
    }

    function formatMarketCap(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        if (value >= 1_000_000_000_000) return `$${(value / 1_000_000_000_000).toFixed(1)}T`;
        if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
        if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
        return `$${value.toLocaleString()}`;
    }

    function getChangeClass(value: number | undefined | null): string {
        if (value === undefined || value === null) return '';
        return value >= 0 ? 'positive' : 'negative';
    }

    function getChangeIcon(value: number | undefined | null): string {
        if (value === undefined || value === null || value === 0) return '';
        return value >= 0 ? '↑' : '↓';
    }

    function formatDiscount(value: number | undefined | null): string {
        if (value === undefined || value === null) return '-';
        const sign = value < 0 ? '' : '+';
        return `${sign}${value.toFixed(1)}%`;
    }

    function getDiscountClass(value: number | undefined | null): string {
        if (value === undefined || value === null) return '';
        return value < 0 ? 'positive' : 'negative';
    }

    function getDiscountIcon(value: number | undefined | null): string {
        if (value === undefined || value === null) return '';
        return value < 0 ? '↓' : '↑';
    }

    function formatScore(score: number | undefined | null, grade: string | undefined | null): string {
        if (score === undefined || score === null) return '-';
        return `${Math.round(score)} ${grade || ''}`;
    }

    function getGradeClass(grade: string | undefined | null): string {
        if (!grade) return '';
        if (grade === 'A' || grade === 'B') return 'positive';
        if (grade === 'D' || grade === 'F') return 'negative';
        return '';
    }

    function getValuationTooltip(stock: USStockPrice): string {
        if (stock.valuation_status === 'CALCULABLE') return '';
        return stock.valuation_note || (stock.valuation_status === 'NOT_CALCULABLE' ? 'Not calculable' : 'Pending data fetch');
    }

    function getRecommendationClass(rec: string | undefined | null): string {
        if (!rec) return 'rec-hold';
        switch (rec.toUpperCase()) {
            case 'STRONG_BUY': return 'rec-strong-buy';
            case 'BUY': return 'rec-buy';
            case 'HOLD': return 'rec-hold';
            case 'SELL': return 'rec-sell';
            case 'STRONG_SELL': return 'rec-strong-sell';
            default: return 'rec-hold';
        }
    }

    // Seed and Scrape
    async function seedStocks() {
        scraping = true;
        scrapeError = '';

        const seedResult = await usStocks.seed(false);
        if (seedResult.error) {
            scrapeError = seedResult.error;
            scraping = false;
            return;
        }

        // Start scraping after seed
        await triggerScrape();
    }

    async function triggerScrape() {
        scraping = true;
        scrapeError = '';

        const result = await usStocks.triggerScrape({ sp500Only: true });

        if (result.error) {
            scrapeError = result.error;
            scraping = false;
            return;
        }

        pollScrapeStatus();
    }

    async function pollScrapeStatus() {
        const result = await usStocks.getScrapeStatus();

        if (result.error) {
            scrapeError = result.error;
            scraping = false;
            return;
        }

        scrapeProgress = result.data || null;

        if (result.data?.running) {
            setTimeout(pollScrapeStatus, 2000);
        } else {
            scraping = false;
            await loadPrices();
        }
    }

    async function loadMore() {
        offset += limit;
        const options: any = { limit, offset, sortBy: sortKey, sortOrder: sortDirection };
        if (activeFilter === 'sp500') options.sp500Only = true;
        if (activeFilter === 'gainers') options.filterType = 'gainers';
        if (activeFilter === 'losers') options.filterType = 'losers';
        if (activeFilter === 'undervalued') options.filterType = 'undervalued';
        if (activeFilter === 'overvalued') options.filterType = 'overvalued';
        if (selectedSector) options.sector = selectedSector;

        const result = await usStocks.getPrices(options);
        if (result.data) {
            priceData = [...priceData, ...result.data];
            hasMore = result.data.length === limit;
        }
    }
</script>

<svelte:head>
    <title>US Stocks - Stokr</title>
</svelte:head>

<div class="stocks-page">
    <!-- Page Header -->
    <div class="page-header">
        <div class="header-content">
            <h1>US Stocks</h1>
            <p class="header-subtitle">US market with Phil Town valuations</p>
        </div>
        <div class="header-actions">
            <div class="search-wrapper">
                <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="M21 21l-4.35-4.35"/>
                </svg>
                <input
                    type="text"
                    placeholder="Search US stocks..."
                    value={searchQuery}
                    on:input={handleSearchInput}
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
            {#if totalCount === 0}
                <button
                    class="btn btn-primary"
                    on:click={seedStocks}
                    disabled={scraping}
                >
                    {#if scraping}
                        <svg class="spinner-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="32"/>
                        </svg>
                        Setting up...
                    {:else}
                        Seed US Stocks
                    {/if}
                </button>
            {:else}
                <button
                    class="btn btn-primary"
                    on:click={() => triggerScrape()}
                    disabled={scraping}
                >
                    {#if scraping}
                        <svg class="spinner-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="32"/>
                        </svg>
                        {#if scrapeProgress}
                            {scrapeProgress.current}/{scrapeProgress.total}
                        {:else}
                            Starting...
                        {/if}
                    {:else}
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
                        </svg>
                        Fetch S&P 500
                    {/if}
                </button>
            {/if}
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
                <p><strong>Error loading US stocks</strong></p>
                <p class="text-muted">{error}</p>
            </div>
        </div>
    {:else if totalCount === 0}
        <div class="empty-state animate-fadeIn">
            <svg class="empty-state-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"/>
                <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
                <line x1="9" y1="9" x2="9.01" y2="9"/>
                <line x1="15" y1="9" x2="15.01" y2="9"/>
            </svg>
            <h2>No US Stocks Yet</h2>
            <p>Click "Seed US Stocks" to fetch all US stock symbols from Finnhub.</p>
            <p class="text-muted">This will populate 18,000+ stocks and mark S&P 500 components.</p>
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
                    All <span class="filter-count">{filterCounts.total.toLocaleString()}</span>
                </button>
                <button
                    class="filter-tab sp500"
                    class:active={activeFilter === 'sp500'}
                    on:click={() => setFilter('sp500')}
                >
                    S&P 500 <span class="filter-count">{filterCounts.sp500}</span>
                </button>
                <button
                    class="filter-tab gainers"
                    class:active={activeFilter === 'gainers'}
                    on:click={() => setFilter('gainers')}
                >
                    Gainers <span class="filter-count positive">{filterCounts.gainers}</span>
                </button>
                <button
                    class="filter-tab losers"
                    class:active={activeFilter === 'losers'}
                    on:click={() => setFilter('losers')}
                >
                    Losers <span class="filter-count negative">{filterCounts.losers}</span>
                </button>
                <span class="filter-divider"></span>
                <button
                    class="filter-tab undervalued"
                    class:active={activeFilter === 'undervalued'}
                    on:click={() => setFilter('undervalued')}
                >
                    Undervalued <span class="filter-count positive">{filterCounts.undervalued}</span>
                </button>
                <button
                    class="filter-tab overvalued"
                    class:active={activeFilter === 'overvalued'}
                    on:click={() => setFilter('overvalued')}
                >
                    Overvalued <span class="filter-count negative">{filterCounts.overvalued}</span>
                </button>
            </div>

            {#if sectors.length > 0}
                <select
                    bind:value={selectedSector}
                    on:change={loadPrices}
                    class="sector-select"
                >
                    <option value={null}>All Sectors</option>
                    {#each sectors as sector}
                        <option value={sector}>{sector}</option>
                    {/each}
                </select>
            {/if}

            {#if activeFilter !== 'all' || searchQuery || selectedSector}
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
            <span class="results-count">Showing {displayedStocks.length} of {totalCount.toLocaleString()} stocks</span>
            {#if sortKey !== 'market_cap' || sortDirection !== 'desc'}
                <span class="sort-indicator">
                    Sorted by {sortKey === 'change_pct' ? 'change %' : sortKey === 'discount_pct' ? 'discount' : sortKey === 'four_m_score' ? 'Phil score' : sortKey}
                    {sortDirection === 'asc' ? '↑' : '↓'}
                </span>
            {/if}
            <span class="valuation-indicator">
                {totalValuationCount} with valuations
            </span>
            {#if scrapeStats}
                <span class="attempted-indicator">{scrapeStats.stocks_attempted.toLocaleString()} attempted</span>
            {/if}
            {#if scraping && scrapeProgress}
                <span class="refresh-indicator">
                    Fetching: {scrapeProgress.current_symbol} ({scrapeProgress.progress_percent?.toFixed(0) || 0}%)
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
                                <th title="Stock symbol">
                                    <button class="sort-header" on:click={() => handleSort('symbol')}>
                                        Symbol
                                        <span class="sort-icon" class:active={sortKey === 'symbol'}>
                                            {sortKey === 'symbol' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right" title="Current stock price">
                                    <button class="sort-header" on:click={() => handleSort('current_price')}>
                                        Price
                                        <span class="sort-icon" class:active={sortKey === 'current_price'}>
                                            {sortKey === 'current_price' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right" title="Price change from yesterday">
                                    <button class="sort-header" on:click={() => handleSort('change_pct')}>
                                        Change
                                        <span class="sort-icon" class:active={sortKey === 'change_pct'}>
                                            {sortKey === 'change_pct' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right" title="Market capitalization">
                                    <button class="sort-header" on:click={() => handleSort('market_cap')}>
                                        Mkt Cap
                                        <span class="sort-icon" class:active={sortKey === 'market_cap'}>
                                            {sortKey === 'market_cap' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right valuation-col" title="Phil Town's intrinsic value">
                                    <button class="sort-header" on:click={() => handleSort('sticker_price')}>
                                        Sticker
                                        <span class="sort-icon" class:active={sortKey === 'sticker_price'}>
                                            {sortKey === 'sticker_price' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right valuation-col" title="Margin of Safety (50% of Sticker)">
                                    <button class="sort-header" on:click={() => handleSort('margin_of_safety')}>
                                        MOS
                                        <span class="sort-icon" class:active={sortKey === 'margin_of_safety'}>
                                            {sortKey === 'margin_of_safety' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right valuation-col" title="Price vs Sticker: Negative = undervalued">
                                    <button class="sort-header" on:click={() => handleSort('discount_pct')}>
                                        Discount
                                        <span class="sort-icon" class:active={sortKey === 'discount_pct'}>
                                            {sortKey === 'discount_pct' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th class="text-right valuation-col" title="4Ms Score: Meaning, Moat, Management, MOS">
                                    <button class="sort-header" on:click={() => handleSort('four_m_score')}>
                                        Phil Score
                                        <span class="sort-icon" class:active={sortKey === 'four_m_score'}>
                                            {sortKey === 'four_m_score' ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}
                                        </span>
                                    </button>
                                </th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each displayedStocks as stock, i}
                                <tr class="animate-fadeIn" style="animation-delay: {30 + i * 10}ms">
                                    <td>
                                        <div class="stock-cell">
                                            <span class="stock-symbol">{stock.symbol}</span>
                                            {#if stock.is_sp500}
                                                <span class="sp500-badge" title="S&P 500">500</span>
                                            {/if}
                                            {#if stock.name}
                                                <span class="stock-name" title={stock.name}>{stock.name.length > 20 ? stock.name.slice(0, 20) + '...' : stock.name}</span>
                                            {/if}
                                        </div>
                                    </td>
                                    <td class="text-right tabular-nums font-semibold">
                                        {formatPrice(stock.current_price)}
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
                                    <td class="text-right tabular-nums">{formatMarketCap(stock.market_cap)}</td>
                                    <td class="text-right tabular-nums valuation-col" title={getValuationTooltip(stock)}>
                                        {#if stock.valuation_status === 'CALCULABLE'}
                                            {formatPrice(stock.sticker_price)}
                                        {:else}
                                            <span class="text-muted na-value">-</span>
                                        {/if}
                                    </td>
                                    <td class="text-right tabular-nums valuation-col" title={getValuationTooltip(stock)}>
                                        {#if stock.valuation_status === 'CALCULABLE'}
                                            {formatPrice(stock.margin_of_safety)}
                                        {:else}
                                            <span class="text-muted na-value">-</span>
                                        {/if}
                                    </td>
                                    <td class="text-right valuation-col {getDiscountClass(stock.discount_pct)}" title={getValuationTooltip(stock)}>
                                        {#if stock.valuation_status === 'CALCULABLE' && stock.discount_pct !== null && stock.discount_pct !== undefined}
                                            <div class="discount-cell">
                                                <span class="discount-icon">{getDiscountIcon(stock.discount_pct)}</span>
                                                <span class="tabular-nums">{formatDiscount(stock.discount_pct)}</span>
                                            </div>
                                        {:else}
                                            <span class="text-muted na-value">-</span>
                                        {/if}
                                    </td>
                                    <td class="text-right valuation-col {getGradeClass(stock.four_m_grade)}" title={stock.big_five_warning ? 'Big Five failed - recommendation capped' : getValuationTooltip(stock)}>
                                        {#if stock.valuation_status === 'CALCULABLE' && stock.four_m_score !== null && stock.four_m_score !== undefined}
                                            <span class="phil-score-cell">
                                                {#if stock.big_five_warning}
                                                    <span class="big-five-warning" title="Big Five failed">!</span>
                                                {/if}
                                                <span class="phil-score tabular-nums">{formatScore(stock.four_m_score, stock.four_m_grade)}</span>
                                            </span>
                                        {:else}
                                            <span class="text-muted na-value">-</span>
                                        {/if}
                                    </td>
                                    <td>
                                        {#if stock.valuation_status === 'CALCULABLE'}
                                            <span class="status-badge {getRecommendationClass(stock.recommendation)}">{stock.recommendation?.replace('_', ' ') || 'HOLD'}</span>
                                        {:else if stock.valuation_status === 'NOT_CALCULABLE'}
                                            <span class="status-badge status-error" title={stock.valuation_note}>N/A</span>
                                        {:else}
                                            <span class="status-badge status-pending">Pending</span>
                                        {/if}
                                    </td>
                                    <td>
                                        <a href="/us-stocks/{stock.symbol}" class="btn btn-primary btn-sm">
                                            Analyze
                                        </a>
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>

                {#if displayedStocks.length === 0}
                    <div class="empty-state">
                        <svg class="empty-state-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="11" cy="11" r="8"/>
                            <path d="M21 21l-4.35-4.35"/>
                        </svg>
                        <h3>No stocks found</h3>
                        <p>No stocks matching your search criteria</p>
                    </div>
                {/if}

                {#if hasMore}
                    <div class="load-more">
                        <button class="btn btn-secondary" on:click={loadMore}>
                            Load More
                        </button>
                    </div>
                {/if}
            </div>
        {:else}
            <!-- Grid View -->
            <div class="stocks-grid mt-3 animate-fadeIn stagger-2">
                {#each displayedStocks as stock, i}
                    <div class="stock-card animate-fadeIn" style="animation-delay: {30 + i * 10}ms">
                        <div class="stock-card-header">
                            <div>
                                <span class="stock-card-symbol">{stock.symbol}</span>
                                {#if stock.is_sp500}
                                    <span class="sp500-badge small">500</span>
                                {/if}
                            </div>
                            <span class="stock-card-change {getChangeClass(stock.change)}">
                                {#if stock.change_pct !== undefined && stock.change_pct !== null}
                                    {getChangeIcon(stock.change)}
                                    {Math.abs(stock.change_pct).toFixed(2)}%
                                {:else}
                                    -
                                {/if}
                            </span>
                        </div>
                        {#if stock.name}
                            <div class="stock-card-name" title={stock.name}>
                                {stock.name.length > 25 ? stock.name.slice(0, 25) + '...' : stock.name}
                            </div>
                        {/if}
                        <div class="stock-card-price">{formatPrice(stock.current_price)}</div>
                        <div class="stock-card-meta">
                            <span>Cap: {formatMarketCap(stock.market_cap)}</span>
                            {#if stock.valuation_status === 'CALCULABLE'}
                                <span class="{getDiscountClass(stock.discount_pct)}">{formatDiscount(stock.discount_pct)}</span>
                            {/if}
                        </div>
                    </div>
                {/each}
            </div>

            {#if displayedStocks.length === 0}
                <div class="empty-state mt-3">
                    <svg class="empty-state-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="M21 21l-4.35-4.35"/>
                    </svg>
                    <h3>No stocks found</h3>
                    <p>No stocks matching your search criteria</p>
                </div>
            {/if}
        {/if}
    {/if}
</div>

<style>
    .stocks-page {
        max-width: 1600px;
        margin: 0 auto;
    }

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

    .attempted-indicator {
        font-size: 0.75rem;
        color: var(--text-muted);
        opacity: 0.6;
    }

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

    .filter-divider {
        width: 1px;
        height: 20px;
        background: var(--border);
        margin: 0 0.5rem;
    }

    .sector-select {
        padding: 0.5rem 1rem;
        border-radius: var(--radius-md);
        border: 1px solid var(--border);
        background: var(--bg-secondary);
        font-size: 0.8125rem;
        color: var(--text-primary);
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

    .results-info {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.5rem 0;
        flex-wrap: wrap;
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

    .valuation-indicator {
        font-size: 0.75rem;
        color: var(--accent-primary);
        padding: 0.25rem 0.5rem;
        background: rgba(99, 102, 241, 0.1);
        border-radius: var(--radius-sm);
    }

    .refresh-indicator {
        font-size: 0.75rem;
        color: var(--warning);
        padding: 0.25rem 0.5rem;
        background: rgba(245, 158, 11, 0.1);
        border-radius: var(--radius-sm);
        animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    .spinner-icon {
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

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
    }

    .sort-icon.active {
        opacity: 1;
        color: var(--accent-primary);
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

    .stocks-card {
        padding: 0;
    }

    .table-container {
        overflow-x: auto;
        max-height: calc(100vh - 300px);
        overflow-y: auto;
    }

    thead {
        position: sticky;
        top: 0;
        z-index: 10;
        background: var(--bg-card);
    }

    thead th {
        background: var(--bg-card);
        box-shadow: 0 1px 0 var(--border);
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
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .stock-symbol {
        font-weight: 600;
        color: var(--accent-primary);
    }

    .stock-name {
        font-size: 0.75rem;
        color: var(--text-muted);
    }

    .sp500-badge {
        display: inline-block;
        padding: 0.125rem 0.375rem;
        font-size: 0.625rem;
        font-weight: 700;
        color: #f59e0b;
        background: rgba(245, 158, 11, 0.15);
        border-radius: var(--radius-sm);
    }

    .sp500-badge.small {
        font-size: 0.5rem;
        padding: 0.0625rem 0.25rem;
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

    .valuation-col {
        white-space: nowrap;
    }

    .na-value {
        font-size: 0.75rem;
        cursor: help;
    }

    .discount-cell {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.25rem;
    }

    .discount-icon {
        font-size: 0.75rem;
    }

    .phil-score {
        font-weight: 600;
    }

    .phil-score-cell {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        justify-content: flex-end;
    }

    .big-five-warning {
        color: var(--warning);
        font-weight: 700;
        cursor: help;
    }

    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        font-size: 0.6875rem;
        font-weight: 600;
        border-radius: var(--radius-sm);
        text-transform: uppercase;
    }

    .status-ready {
        background: rgba(5, 150, 105, 0.12);
        color: var(--success);
    }

    .status-pending {
        background: rgba(245, 158, 11, 0.12);
        color: var(--warning);
    }

    .status-error {
        background: rgba(220, 38, 38, 0.12);
        color: var(--danger);
    }

    /* Recommendation badges */
    .rec-strong-buy {
        background: rgba(5, 150, 105, 0.2);
        color: #059669;
        font-weight: 700;
    }

    .rec-buy {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
    }

    .rec-hold {
        background: rgba(245, 158, 11, 0.12);
        color: var(--warning);
    }

    .rec-sell {
        background: rgba(249, 115, 22, 0.15);
        color: #f97316;
    }

    .rec-strong-sell {
        background: rgba(220, 38, 38, 0.2);
        color: #dc2626;
        font-weight: 700;
    }

    .load-more {
        display: flex;
        justify-content: center;
        padding: 1.5rem;
    }

    .stocks-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 1rem;
    }

    .stock-card {
        display: flex;
        flex-direction: column;
        padding: 1.25rem;
        background: var(--bg-card);
        border-radius: var(--radius-lg);
        border: 1px solid var(--border-light);
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
        margin-bottom: 0.5rem;
    }

    .stock-card-symbol {
        font-weight: 700;
        font-size: 0.9375rem;
        color: var(--text-primary);
    }

    .stock-card-name {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-bottom: 0.5rem;
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

    .empty-state {
        text-align: center;
        padding: 3rem 1.5rem;
    }

    .empty-state-icon {
        color: var(--text-muted);
        margin-bottom: 1rem;
    }

    .empty-state h2, .empty-state h3 {
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }

    .empty-state p {
        color: var(--text-muted);
        margin-bottom: 0.25rem;
    }

    .error {
        display: flex;
        align-items: flex-start;
        gap: 1rem;
        padding: 1.5rem;
        background: rgba(220, 38, 38, 0.1);
        border-radius: var(--radius-lg);
    }

    .error svg {
        flex-shrink: 0;
        color: var(--danger);
    }

    .positive {
        color: var(--success);
    }

    .negative {
        color: var(--danger);
    }

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
            overflow-x: auto;
        }

        .filter-tab {
            padding: 0.375rem 0.75rem;
            font-size: 0.75rem;
        }

        .filter-divider {
            display: none;
        }

        .stocks-grid {
            grid-template-columns: 1fr 1fr;
        }

        th:nth-child(4),
        td:nth-child(4),
        th:nth-child(6),
        td:nth-child(6) {
            display: none;
        }
    }

    @media (max-width: 480px) {
        .filter-count {
            display: none;
        }

        .stocks-grid {
            grid-template-columns: 1fr;
        }

        th:nth-child(5),
        td:nth-child(5),
        th:nth-child(7),
        td:nth-child(7),
        th:nth-child(8),
        td:nth-child(8) {
            display: none;
        }
    }
</style>
