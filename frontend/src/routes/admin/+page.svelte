<script lang="ts">
    import { onMount } from 'svelte';
    import { portfolioData, portfolioLoaded, portfolioLoading as pLoading } from '$lib/stores/portfolio';

    const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    // Tab state
    let activeTab: 'portfolio' | 'financial' = 'portfolio';

    // Portfolio Management - use store
    let portfolioHoldings: any[] = [];
    let portfolioLoading = false;
    let portfolioError = '';
    let portfolioSuccess = '';

    // Subscribe to portfolio store
    portfolioData.subscribe(v => {
        if (v) portfolioHoldings = v.holdings || [];
    });
    pLoading.subscribe(v => portfolioLoading = v);

    // New holding form
    let newHolding = {
        stock_symbol: '',
        shares: 0,
        avg_cost: 0,
        notes: ''
    };

    // Financial Data Entry
    let financialSymbol = '';
    let financialYear = new Date().getFullYear();
    let financialData = {
        net_income: null as number | null,
        total_assets: null as number | null,
        total_debt: null as number | null,
        operating_cash_flow: null as number | null,
        capital_expenditure: null as number | null
    };
    let financialLoading = false;
    let financialError = '';
    let financialSuccess = '';
    let calculatedMetrics: any = null;

    onMount(async () => {
        let isLoaded = false;
        portfolioLoaded.subscribe(v => isLoaded = v)();

        if (!isLoaded) {
            await loadPortfolio();
        }
    });

    async function loadPortfolio() {
        portfolioLoading = true;
        portfolioError = '';
        try {
            const res = await fetch(`${API_BASE}/portfolio/`);
            if (res.ok) {
                const data = await res.json();
                portfolioHoldings = data.holdings || [];
                portfolioData.set(data);
                portfolioLoaded.set(true);
            } else {
                portfolioError = 'Failed to load portfolio';
            }
        } catch (e) {
            portfolioError = 'Error connecting to server';
        }
        portfolioLoading = false;
    }

    async function updateHolding(symbol: string, shares: number, avgCost: number) {
        portfolioSuccess = '';
        portfolioError = '';
        try {
            const res = await fetch(`${API_BASE}/portfolio/${symbol}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ shares, avg_cost: avgCost })
            });
            if (res.ok) {
                portfolioSuccess = `Updated ${symbol} successfully`;
                await loadPortfolio();
                setTimeout(() => portfolioSuccess = '', 3000);
            } else {
                portfolioError = `Failed to update ${symbol}`;
            }
        } catch (e) {
            portfolioError = 'Error updating holding';
        }
    }

    async function addHolding() {
        portfolioSuccess = '';
        portfolioError = '';
        if (!newHolding.stock_symbol || newHolding.shares <= 0) {
            portfolioError = 'Please enter symbol and shares';
            return;
        }
        try {
            const res = await fetch(`${API_BASE}/portfolio/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newHolding)
            });
            if (res.ok) {
                portfolioSuccess = `Added ${newHolding.stock_symbol.toUpperCase()} to portfolio`;
                newHolding = { stock_symbol: '', shares: 0, avg_cost: 0, notes: '' };
                await loadPortfolio();
                setTimeout(() => portfolioSuccess = '', 3000);
            } else {
                const err = await res.json();
                portfolioError = err.detail || 'Failed to add holding';
            }
        } catch (e) {
            portfolioError = 'Error adding holding';
        }
    }

    async function deleteHolding(symbol: string) {
        if (!confirm(`Delete ${symbol} from portfolio?`)) return;
        portfolioSuccess = '';
        portfolioError = '';
        try {
            const res = await fetch(`${API_BASE}/portfolio/${symbol}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                portfolioSuccess = `Deleted ${symbol} from portfolio`;
                await loadPortfolio();
                setTimeout(() => portfolioSuccess = '', 3000);
            } else {
                portfolioError = `Failed to delete ${symbol}`;
            }
        } catch (e) {
            portfolioError = 'Error deleting holding';
        }
    }

    async function submitFinancialData() {
        if (!financialSymbol) {
            financialError = 'Please enter a stock symbol';
            return;
        }

        financialLoading = true;
        financialError = '';
        financialSuccess = '';

        const dataToSend: any = {};
        for (const [key, value] of Object.entries(financialData)) {
            if (value !== null && value !== undefined && String(value) !== '') {
                dataToSend[key] = Number(value);
            }
        }

        try {
            const res = await fetch(
                `${API_BASE}/stocks/${financialSymbol.toUpperCase()}/financials/${financialYear}`,
                {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dataToSend)
                }
            );

            if (res.ok) {
                const result = await res.json();
                financialSuccess = result.message;
                calculatedMetrics = result.data;
            } else {
                const err = await res.json();
                financialError = err.detail || 'Failed to save data';
            }
        } catch (e) {
            financialError = 'Error connecting to server';
        }

        financialLoading = false;
    }

    async function recalculateMetrics() {
        if (!financialSymbol) {
            financialError = 'Please enter a stock symbol';
            return;
        }

        financialLoading = true;
        financialError = '';
        try {
            const res = await fetch(
                `${API_BASE}/stocks/${financialSymbol.toUpperCase()}/calculate-metrics`,
                { method: 'POST' }
            );
            if (res.ok) {
                const result = await res.json();
                financialSuccess = result.message;
            } else {
                financialError = 'Failed to recalculate';
            }
        } catch (e) {
            financialError = 'Error connecting to server';
        }
        financialLoading = false;
    }

    function formatCurrency(value: number | null | undefined): string {
        if (value === null || value === undefined) return '-';
        return `৳${value.toLocaleString('en-BD', { minimumFractionDigits: 2 })}`;
    }

    function clearMessages() {
        portfolioSuccess = '';
        portfolioError = '';
    }
</script>

<svelte:head>
    <title>Data Entry - DSE Value Investor</title>
</svelte:head>

<div class="admin-page">
    <!-- Page Header -->
    <div class="page-header animate-fadeIn">
        <div class="header-content">
            <h1>Data Entry</h1>
            <p class="header-subtitle">Manage your portfolio and enter financial data manually</p>
        </div>
    </div>

    <!-- Tab Navigation -->
    <div class="tab-nav animate-fadeIn stagger-1">
        <button
            class="tab-btn"
            class:active={activeTab === 'portfolio'}
            on:click={() => { activeTab = 'portfolio'; clearMessages(); }}
        >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                <line x1="12" y1="22.08" x2="12" y2="12"/>
            </svg>
            Portfolio Holdings
        </button>
        <button
            class="tab-btn"
            class:active={activeTab === 'financial'}
            on:click={() => { activeTab = 'financial'; clearMessages(); }}
        >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <path d="M3 9h18"/>
                <path d="M9 21V9"/>
            </svg>
            Financial Data
        </button>
    </div>

    {#if activeTab === 'portfolio'}
        <!-- Portfolio Management -->
        <div class="card animate-fadeIn stagger-2">
            <div class="card-header">
                <h2>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 0.5rem; vertical-align: -2px;">
                        <rect x="3" y="3" width="7" height="7"/>
                        <rect x="14" y="3" width="7" height="7"/>
                        <rect x="14" y="14" width="7" height="7"/>
                        <rect x="3" y="14" width="7" height="7"/>
                    </svg>
                    Current Holdings
                </h2>
                <button class="btn btn-secondary" on:click={loadPortfolio}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="23 4 23 10 17 10"/>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                    </svg>
                    Refresh
                </button>
            </div>

            {#if portfolioError}
                <div class="message error">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="8" x2="12" y2="12"/>
                        <line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                    <span>{portfolioError}</span>
                </div>
            {/if}

            {#if portfolioSuccess}
                <div class="message success">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                    <span>{portfolioSuccess}</span>
                </div>
            {/if}

            {#if portfolioLoading}
                <div class="loading"><div class="spinner"></div></div>
            {:else if portfolioHoldings.length === 0}
                <div class="empty-state">
                    <svg class="empty-state-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                    </svg>
                    <h3>No Holdings Yet</h3>
                    <p>Add your first holding using the form below.</p>
                </div>
            {:else}
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th class="text-right">Shares</th>
                                <th class="text-right">Avg Cost</th>
                                <th class="text-right">Total Cost</th>
                                <th>Notes</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each portfolioHoldings as holding, i}
                                <tr class="animate-fadeIn" style="animation-delay: {50 + i * 30}ms">
                                    <td>
                                        <a href="/stocks/{holding.stock_symbol}" class="stock-link">{holding.stock_symbol}</a>
                                    </td>
                                    <td class="text-right">
                                        <input
                                            type="number"
                                            value={holding.shares}
                                            class="inline-input"
                                            on:change={(e) => updateHolding(holding.stock_symbol, parseInt(e.currentTarget.value), holding.avg_cost)}
                                        />
                                    </td>
                                    <td class="text-right">
                                        <input
                                            type="number"
                                            step="0.01"
                                            value={holding.avg_cost}
                                            class="inline-input"
                                            on:change={(e) => updateHolding(holding.stock_symbol, holding.shares, parseFloat(e.currentTarget.value))}
                                        />
                                    </td>
                                    <td class="text-right tabular-nums text-muted">{formatCurrency(holding.total_cost)}</td>
                                    <td class="text-muted">{holding.notes || '-'}</td>
                                    <td>
                                        <button class="btn btn-danger btn-sm" on:click={() => deleteHolding(holding.stock_symbol)}>
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                                <polyline points="3 6 5 6 21 6"/>
                                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                                            </svg>
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            {/if}
        </div>

        <!-- Add New Holding -->
        <div class="card add-holding-card mt-3 animate-fadeIn stagger-3">
            <div class="card-header">
                <h2>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 0.5rem; vertical-align: -2px;">
                        <path d="M12 5v14M5 12h14"/>
                    </svg>
                    Add New Holding
                </h2>
            </div>

            <form on:submit|preventDefault={addHolding} class="add-form">
                <div class="form-grid">
                    <div class="form-group">
                        <label for="newSymbol">Stock Symbol *</label>
                        <input
                            type="text"
                            id="newSymbol"
                            placeholder="e.g., BXPHARMA"
                            bind:value={newHolding.stock_symbol}
                            class="symbol-input"
                            required
                        />
                    </div>
                    <div class="form-group">
                        <label for="newShares">Shares *</label>
                        <input
                            type="number"
                            id="newShares"
                            placeholder="Number of shares"
                            bind:value={newHolding.shares}
                            min="1"
                            required
                        />
                    </div>
                    <div class="form-group">
                        <label for="newCost">Avg Cost (BDT) *</label>
                        <input
                            type="number"
                            id="newCost"
                            step="0.01"
                            placeholder="Average price per share"
                            bind:value={newHolding.avg_cost}
                            min="0.01"
                            required
                        />
                    </div>
                    <div class="form-group">
                        <label for="newNotes">Notes (optional)</label>
                        <input
                            type="text"
                            id="newNotes"
                            placeholder="Any notes about this holding"
                            bind:value={newHolding.notes}
                        />
                    </div>
                </div>
                <button type="submit" class="btn btn-primary">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 5v14M5 12h14"/>
                    </svg>
                    Add to Portfolio
                </button>
            </form>
        </div>
    {:else}
        <!-- Financial Data Entry -->
        <div class="card animate-fadeIn stagger-2">
            <div class="card-header">
                <h2>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 0.5rem; vertical-align: -2px;">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                    Manual Financial Data Entry
                </h2>
            </div>

            <div class="info-box">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="16" x2="12" y2="12"/>
                    <line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
                <div>
                    <strong>How it works</strong>
                    <p>Enter data NOT available from auto-fetch. ROE, ROA, FCF, and D/E ratio will be calculated automatically.</p>
                </div>
            </div>

            {#if financialError}
                <div class="message error">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="8" x2="12" y2="12"/>
                        <line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                    <span>{financialError}</span>
                </div>
            {/if}

            {#if financialSuccess}
                <div class="message success">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                    <span>{financialSuccess}</span>
                </div>
            {/if}

            <form on:submit|preventDefault={submitFinancialData} class="financial-form">
                <div class="form-section">
                    <h3>Basic Information</h3>
                    <div class="form-grid cols-2">
                        <div class="form-group">
                            <label for="finSymbol">Stock Symbol *</label>
                            <input
                                type="text"
                                id="finSymbol"
                                placeholder="e.g., BXPHARMA"
                                bind:value={financialSymbol}
                                class="symbol-input"
                                required
                            />
                        </div>
                        <div class="form-group">
                            <label for="finYear">Year *</label>
                            <input
                                type="number"
                                id="finYear"
                                min="2000"
                                max="2030"
                                bind:value={financialYear}
                                required
                            />
                        </div>
                    </div>
                </div>

                <div class="form-section">
                    <h3>Financial Data (from Annual Report)</h3>
                    <div class="form-grid cols-3">
                        <div class="form-group">
                            <label for="netIncome">
                                Net Income (Cr)
                                <span class="label-hint">For ROE calculation</span>
                            </label>
                            <input type="number" id="netIncome" step="0.01" bind:value={financialData.net_income} placeholder="0.00" />
                        </div>
                        <div class="form-group">
                            <label for="totalAssets">
                                Total Assets (Cr)
                                <span class="label-hint">For ROA calculation</span>
                            </label>
                            <input type="number" id="totalAssets" step="0.01" bind:value={financialData.total_assets} placeholder="0.00" />
                        </div>
                        <div class="form-group">
                            <label for="totalDebt">
                                Total Debt (Cr)
                                <span class="label-hint">For D/E ratio</span>
                            </label>
                            <input type="number" id="totalDebt" step="0.01" bind:value={financialData.total_debt} placeholder="0.00" />
                        </div>
                    </div>
                </div>

                <div class="form-section">
                    <h3>Cash Flow Statement</h3>
                    <div class="form-grid cols-2">
                        <div class="form-group">
                            <label for="opCashFlow">
                                Operating Cash Flow (Cr)
                                <span class="label-hint">Cash from operations</span>
                            </label>
                            <input type="number" id="opCashFlow" step="0.01" bind:value={financialData.operating_cash_flow} placeholder="0.00" />
                        </div>
                        <div class="form-group">
                            <label for="capex">
                                Capital Expenditure (Cr)
                                <span class="label-hint">FCF will be calculated</span>
                            </label>
                            <input type="number" id="capex" step="0.01" bind:value={financialData.capital_expenditure} placeholder="0.00" />
                        </div>
                    </div>
                </div>

                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" on:click={recalculateMetrics} disabled={financialLoading}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="23 4 23 10 17 10"/>
                            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                        </svg>
                        Recalculate
                    </button>
                    <button type="submit" class="btn btn-primary btn-lg" disabled={financialLoading}>
                        {#if financialLoading}
                            <span class="spinner spinner-sm"></span>
                            Saving...
                        {:else}
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                                <polyline points="17 21 17 13 7 13 7 21"/>
                                <polyline points="7 3 7 8 15 8"/>
                            </svg>
                            Save Data
                        {/if}
                    </button>
                </div>
            </form>

            {#if calculatedMetrics}
                <div class="calculated-metrics mt-3">
                    <h3>Calculated Metrics for {financialSymbol.toUpperCase()} ({calculatedMetrics.year})</h3>
                    <div class="metrics-grid">
                        <div class="metric-item">
                            <span class="metric-label">ROE</span>
                            <span class="metric-value {calculatedMetrics.roe > 10 ? 'positive' : calculatedMetrics.roe < 0 ? 'negative' : ''}">{calculatedMetrics.roe?.toFixed(2) || '-'}%</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">ROA</span>
                            <span class="metric-value">{calculatedMetrics.roa?.toFixed(2) || '-'}%</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Debt/Equity</span>
                            <span class="metric-value">{calculatedMetrics.debt_to_equity?.toFixed(2) || '-'}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Net Margin</span>
                            <span class="metric-value">{calculatedMetrics.net_margin?.toFixed(2) || '-'}%</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Free Cash Flow</span>
                            <span class="metric-value">{calculatedMetrics.free_cash_flow?.toFixed(2) || '-'} Cr</span>
                        </div>
                    </div>
                </div>
            {/if}
        </div>
    {/if}
</div>

<style>
    .admin-page {
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

    /* Tab Navigation */
    .tab-nav {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
        background: var(--bg-secondary);
        padding: 0.375rem;
        border-radius: var(--radius-lg);
    }

    .tab-btn {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.875rem 1rem;
        background: transparent;
        border: none;
        border-radius: var(--radius-md);
        color: var(--text-secondary);
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.875rem;
        font-weight: 600;
        cursor: pointer;
        transition: all var(--duration-fast) var(--ease-out-expo);
    }

    .tab-btn:hover {
        color: var(--text-primary);
    }

    .tab-btn.active {
        background: var(--bg-card);
        color: var(--accent-primary);
        box-shadow: var(--shadow-sm);
    }

    /* Messages */
    .message {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem;
        border-radius: var(--radius-md);
        font-size: 0.875rem;
        font-weight: 500;
        margin-bottom: 1rem;
    }

    .message.success {
        background: rgba(5, 150, 105, 0.08);
        color: var(--success);
        border: 1px solid rgba(5, 150, 105, 0.2);
    }

    .message.error {
        background: rgba(220, 38, 38, 0.08);
        color: var(--danger);
        border: 1px solid rgba(220, 38, 38, 0.2);
    }

    /* Info Box */
    .info-box {
        display: flex;
        gap: 0.75rem;
        padding: 1rem;
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: var(--radius-md);
        margin-bottom: 1.5rem;
        color: var(--info);
    }

    .info-box svg {
        flex-shrink: 0;
        margin-top: 2px;
    }

    .info-box strong {
        display: block;
        margin-bottom: 0.25rem;
    }

    .info-box p {
        margin: 0;
        font-size: 0.8125rem;
        opacity: 0.9;
    }

    /* Table Styles */
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

    .inline-input {
        width: 100px;
        padding: 0.375rem 0.5rem;
        font-size: 0.8125rem;
        text-align: right;
    }

    /* Add Holding Card */
    .add-holding-card {
        border: 2px dashed var(--border);
    }

    .add-form {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .add-form .form-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
    }

    .add-form button {
        align-self: flex-start;
    }

    /* Form Styles */
    .form-section {
        margin-bottom: 1.5rem;
    }

    .form-section h3 {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.8125rem;
        font-weight: 700;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--border-light);
        margin-bottom: 1rem;
    }

    .form-grid {
        display: grid;
        gap: 1rem;
    }

    .form-grid.cols-2 {
        grid-template-columns: repeat(2, 1fr);
    }

    .form-grid.cols-3 {
        grid-template-columns: repeat(3, 1fr);
    }

    .form-group {
        display: flex;
        flex-direction: column;
        gap: 0.375rem;
    }

    .form-group label {
        display: flex;
        flex-direction: column;
        gap: 0.125rem;
    }

    .label-hint {
        font-size: 0.6875rem;
        font-weight: 400;
        color: var(--text-muted);
        text-transform: none;
        letter-spacing: 0;
    }

    .symbol-input {
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    .form-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border-light);
    }

    /* Calculated Metrics */
    .calculated-metrics {
        padding: 1.5rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
    }

    .calculated-metrics h3 {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.875rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }

    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 1rem;
    }

    .metric-item {
        text-align: center;
        padding: 1rem;
        background: var(--bg-card);
        border-radius: var(--radius-md);
    }

    .metric-label {
        display: block;
        font-size: 0.6875rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }

    .metric-value {
        display: block;
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--accent-primary);
    }

    /* Empty State */
    .empty-state {
        padding: 3rem 2rem;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .tab-nav {
            flex-direction: column;
        }

        .add-form .form-grid {
            grid-template-columns: 1fr;
        }

        .form-grid.cols-2,
        .form-grid.cols-3 {
            grid-template-columns: 1fr;
        }

        .form-actions {
            flex-direction: column;
        }

        .form-actions button {
            width: 100%;
        }

        .inline-input {
            width: 80px;
        }
    }
</style>
