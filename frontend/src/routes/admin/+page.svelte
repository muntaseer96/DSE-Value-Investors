<script lang="ts">
    import { onMount } from 'svelte';

    const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    // Portfolio Management
    let portfolioHoldings: any[] = [];
    let portfolioLoading = false;
    let portfolioError = '';
    let portfolioSuccess = '';

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
        revenue: null as number | null,
        net_income: null as number | null,
        eps: null as number | null,
        total_equity: null as number | null,
        total_assets: null as number | null,
        total_debt: null as number | null,
        operating_cash_flow: null as number | null,
        capital_expenditure: null as number | null,
        free_cash_flow: null as number | null
    };
    let financialLoading = false;
    let financialError = '';
    let financialSuccess = '';
    let calculatedMetrics: any = null;

    onMount(async () => {
        await loadPortfolio();
    });

    async function loadPortfolio() {
        portfolioLoading = true;
        portfolioError = '';
        try {
            const res = await fetch(`${API_BASE}/portfolio/`);
            if (res.ok) {
                const data = await res.json();
                portfolioHoldings = data.holdings || [];
            } else {
                portfolioError = 'Failed to load portfolio';
            }
        } catch (e) {
            portfolioError = 'Error connecting to server';
        }
        portfolioLoading = false;
    }

    async function updateHolding(symbol: string, shares: number, avgCost: number) {
        try {
            const res = await fetch(`${API_BASE}/portfolio/${symbol}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ shares, avg_cost: avgCost })
            });
            if (res.ok) {
                portfolioSuccess = `Updated ${symbol}`;
                await loadPortfolio();
            } else {
                portfolioError = `Failed to update ${symbol}`;
            }
        } catch (e) {
            portfolioError = 'Error updating holding';
        }
    }

    async function addHolding() {
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
                portfolioSuccess = `Added ${newHolding.stock_symbol}`;
                newHolding = { stock_symbol: '', shares: 0, avg_cost: 0, notes: '' };
                await loadPortfolio();
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
        try {
            const res = await fetch(`${API_BASE}/portfolio/${symbol}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                portfolioSuccess = `Deleted ${symbol}`;
                await loadPortfolio();
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

        // Filter out null values
        const dataToSend: any = {};
        for (const [key, value] of Object.entries(financialData)) {
            if (value !== null && value !== '') {
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
</script>

<div class="admin-page">
    <h1>Data Management</h1>
    <p class="subtitle">Manage your portfolio and enter financial data manually</p>

    <!-- Portfolio Management Section -->
    <section class="card">
        <div class="card-header">
            <h2>Portfolio Holdings</h2>
            <button class="btn btn-secondary" on:click={loadPortfolio}>
                Refresh
            </button>
        </div>

        {#if portfolioError}
            <div class="alert alert-error">{portfolioError}</div>
        {/if}
        {#if portfolioSuccess}
            <div class="alert alert-success">{portfolioSuccess}</div>
        {/if}

        {#if portfolioLoading}
            <div class="loading"><div class="spinner"></div></div>
        {:else}
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Shares</th>
                            <th>Avg Cost</th>
                            <th>Total Cost</th>
                            <th>Notes</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each portfolioHoldings as holding}
                            <tr>
                                <td><strong>{holding.stock_symbol}</strong></td>
                                <td>
                                    <input
                                        type="number"
                                        value={holding.shares}
                                        class="input-sm"
                                        on:change={(e) => updateHolding(holding.stock_symbol, parseInt(e.currentTarget.value), holding.avg_cost)}
                                    />
                                </td>
                                <td>
                                    <input
                                        type="number"
                                        step="0.01"
                                        value={holding.avg_cost}
                                        class="input-sm"
                                        on:change={(e) => updateHolding(holding.stock_symbol, holding.shares, parseFloat(e.currentTarget.value))}
                                    />
                                </td>
                                <td>{formatCurrency(holding.total_cost)}</td>
                                <td>{holding.notes || '-'}</td>
                                <td>
                                    <button class="btn btn-danger btn-sm" on:click={() => deleteHolding(holding.stock_symbol)}>
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>

            <!-- Add New Holding -->
            <div class="add-holding">
                <h3>Add New Holding</h3>
                <div class="form-row">
                    <input
                        type="text"
                        placeholder="Symbol (e.g., BXPHARMA)"
                        bind:value={newHolding.stock_symbol}
                    />
                    <input
                        type="number"
                        placeholder="Shares"
                        bind:value={newHolding.shares}
                    />
                    <input
                        type="number"
                        step="0.01"
                        placeholder="Avg Cost"
                        bind:value={newHolding.avg_cost}
                    />
                    <input
                        type="text"
                        placeholder="Notes (optional)"
                        bind:value={newHolding.notes}
                    />
                    <button class="btn btn-primary" on:click={addHolding}>
                        Add
                    </button>
                </div>
            </div>
        {/if}
    </section>

    <!-- Financial Data Entry Section -->
    <section class="card">
        <div class="card-header">
            <h2>Manual Financial Data Entry</h2>
        </div>

        <p class="help-text">
            Enter cash flow and other financial data not available from auto-fetch.
            ROE, ROA, FCF, and margins will be calculated automatically.
        </p>

        {#if financialError}
            <div class="alert alert-error">{financialError}</div>
        {/if}
        {#if financialSuccess}
            <div class="alert alert-success">{financialSuccess}</div>
        {/if}

        <div class="financial-form">
            <div class="form-group">
                <label>Stock Symbol</label>
                <input
                    type="text"
                    placeholder="e.g., BXPHARMA"
                    bind:value={financialSymbol}
                />
            </div>

            <div class="form-group">
                <label>Year</label>
                <input
                    type="number"
                    min="2000"
                    max="2030"
                    bind:value={financialYear}
                />
            </div>

            <hr />
            <h3>Income Statement</h3>

            <div class="form-row">
                <div class="form-group">
                    <label>Revenue (Cr)</label>
                    <input type="number" step="0.01" bind:value={financialData.revenue} placeholder="Total Revenue" />
                </div>
                <div class="form-group">
                    <label>Net Income (Cr)</label>
                    <input type="number" step="0.01" bind:value={financialData.net_income} placeholder="Net Profit" />
                </div>
                <div class="form-group">
                    <label>EPS</label>
                    <input type="number" step="0.01" bind:value={financialData.eps} placeholder="Earnings Per Share" />
                </div>
            </div>

            <hr />
            <h3>Balance Sheet</h3>

            <div class="form-row">
                <div class="form-group">
                    <label>Total Equity (Cr)</label>
                    <input type="number" step="0.01" bind:value={financialData.total_equity} placeholder="Book Value" />
                </div>
                <div class="form-group">
                    <label>Total Assets (Cr)</label>
                    <input type="number" step="0.01" bind:value={financialData.total_assets} placeholder="Total Assets" />
                </div>
                <div class="form-group">
                    <label>Total Debt (Cr)</label>
                    <input type="number" step="0.01" bind:value={financialData.total_debt} placeholder="Total Debt" />
                </div>
            </div>

            <hr />
            <h3>Cash Flow Statement</h3>

            <div class="form-row">
                <div class="form-group">
                    <label>Operating Cash Flow (Cr)</label>
                    <input type="number" step="0.01" bind:value={financialData.operating_cash_flow} placeholder="OCF" />
                </div>
                <div class="form-group">
                    <label>Capital Expenditure (Cr)</label>
                    <input type="number" step="0.01" bind:value={financialData.capital_expenditure} placeholder="CapEx" />
                </div>
                <div class="form-group">
                    <label>Free Cash Flow (Cr)</label>
                    <input type="number" step="0.01" bind:value={financialData.free_cash_flow} placeholder="FCF (auto-calc if OCF+CapEx)" />
                </div>
            </div>

            <div class="form-actions">
                <button class="btn btn-primary" on:click={submitFinancialData} disabled={financialLoading}>
                    {financialLoading ? 'Saving...' : 'Save Financial Data'}
                </button>
                <button class="btn btn-secondary" on:click={recalculateMetrics} disabled={financialLoading}>
                    Recalculate All Metrics
                </button>
            </div>
        </div>

        {#if calculatedMetrics}
            <div class="calculated-metrics">
                <h3>Calculated Metrics for {financialSymbol} ({calculatedMetrics.year})</h3>
                <div class="metrics-grid">
                    <div class="metric">
                        <span class="label">ROE</span>
                        <span class="value">{calculatedMetrics.roe?.toFixed(2) || '-'}%</span>
                    </div>
                    <div class="metric">
                        <span class="label">ROA</span>
                        <span class="value">{calculatedMetrics.roa?.toFixed(2) || '-'}%</span>
                    </div>
                    <div class="metric">
                        <span class="label">Debt/Equity</span>
                        <span class="value">{calculatedMetrics.debt_to_equity?.toFixed(2) || '-'}</span>
                    </div>
                    <div class="metric">
                        <span class="label">Net Margin</span>
                        <span class="value">{calculatedMetrics.net_margin?.toFixed(2) || '-'}%</span>
                    </div>
                    <div class="metric">
                        <span class="label">Free Cash Flow</span>
                        <span class="value">{calculatedMetrics.free_cash_flow?.toFixed(2) || '-'} Cr</span>
                    </div>
                </div>
            </div>
        {/if}
    </section>
</div>

<style>
    .admin-page {
        max-width: 1000px;
        margin: 0 auto;
    }

    .subtitle {
        color: var(--text-secondary);
        margin-bottom: 2rem;
    }

    section {
        margin-bottom: 2rem;
    }

    .help-text {
        color: var(--text-secondary);
        font-size: 0.875rem;
        margin-bottom: 1rem;
    }

    .alert {
        padding: 0.75rem 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
    }

    .alert-error {
        background: rgba(239, 68, 68, 0.1);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .alert-success {
        background: rgba(34, 197, 94, 0.1);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }

    .form-row {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 1rem;
    }

    .form-group {
        flex: 1;
        min-width: 150px;
    }

    .form-group label {
        display: block;
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-bottom: 0.25rem;
    }

    .form-group input {
        width: 100%;
    }

    .input-sm {
        width: 100px;
        padding: 0.25rem 0.5rem;
    }

    .btn-sm {
        padding: 0.25rem 0.5rem;
        font-size: 0.75rem;
    }

    .btn-danger {
        background: #ef4444;
        color: white;
    }

    .btn-danger:hover {
        background: #dc2626;
    }

    .add-holding {
        margin-top: 1.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid var(--border-color);
    }

    .add-holding h3 {
        margin-bottom: 1rem;
    }

    .add-holding .form-row {
        align-items: flex-end;
    }

    .add-holding input {
        flex: 1;
    }

    hr {
        border: none;
        border-top: 1px solid var(--border-color);
        margin: 1.5rem 0;
    }

    h3 {
        font-size: 1rem;
        margin-bottom: 1rem;
        color: var(--text-secondary);
    }

    .form-actions {
        display: flex;
        gap: 1rem;
        margin-top: 1.5rem;
    }

    .calculated-metrics {
        margin-top: 2rem;
        padding: 1rem;
        background: var(--bg-secondary);
        border-radius: 8px;
    }

    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }

    .metric {
        text-align: center;
        padding: 0.75rem;
        background: var(--bg-primary);
        border-radius: 4px;
    }

    .metric .label {
        display: block;
        font-size: 0.75rem;
        color: var(--text-secondary);
    }

    .metric .value {
        display: block;
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--accent-primary);
    }

    .table-container {
        overflow-x: auto;
    }

    @media (max-width: 768px) {
        .form-row {
            flex-direction: column;
        }

        .form-group {
            min-width: 100%;
        }
    }
</style>
