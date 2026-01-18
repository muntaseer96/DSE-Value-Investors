<script lang="ts">
    import { slide } from 'svelte/transition';
    import { quintOut } from 'svelte/easing';

    export let stickerData: {
        current_eps: number;
        eps_growth_rate: number;
        used_growth_rate: number;
        historical_pe: number;
        future_eps: number;
        future_pe: number;
        future_price: number;
        sticker_price: number;
        margin_of_safety: number;
    } | null = null;

    export let fourMsData: {
        meaning?: { score: number; grade: string };
        moat: { score: number; grade: string };
        management: { score: number; grade: string };
        mos: { score: number; grade: string };
        overall_score: number;
        overall_grade: string;
    } | null = null;

    // Get meaning score (from data or default to 50)
    $: meaningScore = fourMsData?.meaning?.score ?? 50;

    let stickerExpanded = false;
    let gradeExpanded = false;

    function formatNum(n: number, decimals = 2): string {
        return n?.toLocaleString('en-BD', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }) ?? '-';
    }

    function formatPercent(n: number): string {
        return `${n?.toFixed(2) ?? '-'}%`;
    }

    // Phil Town weights for 4Ms
    const weights = {
        meaning: 20,
        moat: 30,
        management: 20,
        mos: 30
    };
</script>

<div class="calculation-breakdown">
    <!-- Sticker Price Calculation Steps -->
    {#if stickerData}
        <div class="breakdown-section">
            <button
                class="section-toggle"
                class:expanded={stickerExpanded}
                on:click={() => stickerExpanded = !stickerExpanded}
                aria-expanded={stickerExpanded}
            >
                <div class="toggle-left">
                    <div class="toggle-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18"/>
                        </svg>
                    </div>
                    <div class="toggle-text">
                        <span class="toggle-title">Sticker Price Formula</span>
                        <span class="toggle-subtitle">Phil Town's Rule #1 Methodology</span>
                    </div>
                </div>
                <div class="toggle-chevron">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6 9 12 15 18 9"/>
                    </svg>
                </div>
            </button>

            {#if stickerExpanded}
                <div class="steps-container" transition:slide={{ duration: 400, easing: quintOut }}>
                    <div class="steps-flow">
                        <!-- Step 1: Future EPS -->
                        <div class="calc-step" style="--delay: 0">
                            <div class="step-number">1</div>
                            <div class="step-content">
                                <div class="step-header">
                                    <span class="step-label">Project EPS Forward 10 Years</span>
                                </div>
                                <div class="formula-box">
                                    <div class="formula">
                                        <span class="formula-part">Future EPS</span>
                                        <span class="formula-equals">=</span>
                                        <span class="formula-part">Current EPS</span>
                                        <span class="formula-op">×</span>
                                        <span class="formula-part">(1 + Growth Rate)<sup>10</sup></span>
                                    </div>
                                    <div class="calculation">
                                        <span class="calc-value">৳{formatNum(stickerData.current_eps)}</span>
                                        <span class="calc-op">×</span>
                                        <span class="calc-value">(1 + {formatPercent(stickerData.used_growth_rate)})<sup>10</sup></span>
                                        <span class="calc-equals">=</span>
                                        <span class="calc-result">৳{formatNum(stickerData.future_eps)}</span>
                                    </div>
                                </div>
                                {#if stickerData.eps_growth_rate !== stickerData.used_growth_rate}
                                    <div class="step-note">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <circle cx="12" cy="12" r="10"/>
                                            <line x1="12" y1="16" x2="12" y2="12"/>
                                            <line x1="12" y1="8" x2="12.01" y2="8"/>
                                        </svg>
                                        Growth rate capped at 15% (was {formatPercent(stickerData.eps_growth_rate)})
                                    </div>
                                {/if}
                            </div>
                        </div>

                        <div class="step-connector"></div>

                        <!-- Step 2: Future PE -->
                        <div class="calc-step" style="--delay: 1">
                            <div class="step-number">2</div>
                            <div class="step-content">
                                <div class="step-header">
                                    <span class="step-label">Determine Future PE Ratio</span>
                                </div>
                                <div class="formula-box">
                                    <div class="formula">
                                        <span class="formula-part">Future PE</span>
                                        <span class="formula-equals">=</span>
                                        <span class="formula-func">min(</span>
                                        <span class="formula-part">Growth% × 2</span>
                                        <span class="formula-sep">,</span>
                                        <span class="formula-part">Historical PE</span>
                                        <span class="formula-func">)</span>
                                    </div>
                                    <div class="calculation">
                                        <span class="calc-func">min(</span>
                                        <span class="calc-value">{formatNum(stickerData.used_growth_rate * 2)}</span>
                                        <span class="calc-sep">,</span>
                                        <span class="calc-value">{formatNum(stickerData.historical_pe)}</span>
                                        <span class="calc-func">)</span>
                                        <span class="calc-equals">=</span>
                                        <span class="calc-result">{formatNum(stickerData.future_pe)}</span>
                                    </div>
                                </div>
                                <div class="step-note info">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                                    </svg>
                                    Conservative: use lower of growth-based PE or historical PE
                                </div>
                            </div>
                        </div>

                        <div class="step-connector"></div>

                        <!-- Step 3: Future Price -->
                        <div class="calc-step" style="--delay: 2">
                            <div class="step-number">3</div>
                            <div class="step-content">
                                <div class="step-header">
                                    <span class="step-label">Calculate Future Stock Price</span>
                                </div>
                                <div class="formula-box">
                                    <div class="formula">
                                        <span class="formula-part">Future Price</span>
                                        <span class="formula-equals">=</span>
                                        <span class="formula-part">Future EPS</span>
                                        <span class="formula-op">×</span>
                                        <span class="formula-part">Future PE</span>
                                    </div>
                                    <div class="calculation">
                                        <span class="calc-value">৳{formatNum(stickerData.future_eps)}</span>
                                        <span class="calc-op">×</span>
                                        <span class="calc-value">{formatNum(stickerData.future_pe)}</span>
                                        <span class="calc-equals">=</span>
                                        <span class="calc-result">৳{formatNum(stickerData.future_price)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="step-connector"></div>

                        <!-- Step 4: Sticker Price -->
                        <div class="calc-step" style="--delay: 3">
                            <div class="step-number">4</div>
                            <div class="step-content">
                                <div class="step-header">
                                    <span class="step-label">Discount to Present Value (Sticker Price)</span>
                                </div>
                                <div class="formula-box">
                                    <div class="formula">
                                        <span class="formula-part">Sticker Price</span>
                                        <span class="formula-equals">=</span>
                                        <span class="formula-part">Future Price</span>
                                        <span class="formula-op">÷</span>
                                        <span class="formula-part">1.15<sup>10</sup></span>
                                    </div>
                                    <div class="calculation">
                                        <span class="calc-value">৳{formatNum(stickerData.future_price)}</span>
                                        <span class="calc-op">÷</span>
                                        <span class="calc-value">4.046</span>
                                        <span class="calc-equals">=</span>
                                        <span class="calc-result highlight">৳{formatNum(stickerData.sticker_price)}</span>
                                    </div>
                                </div>
                                <div class="step-note info">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <circle cx="12" cy="12" r="10"/>
                                        <polyline points="12 6 12 12 16 14"/>
                                    </svg>
                                    Requires 15% annual return (Rule #1 minimum)
                                </div>
                            </div>
                        </div>

                        <div class="step-connector"></div>

                        <!-- Step 5: Margin of Safety -->
                        <div class="calc-step final" style="--delay: 4">
                            <div class="step-number">5</div>
                            <div class="step-content">
                                <div class="step-header">
                                    <span class="step-label">Apply 50% Margin of Safety</span>
                                </div>
                                <div class="formula-box">
                                    <div class="formula">
                                        <span class="formula-part">Buy Price</span>
                                        <span class="formula-equals">=</span>
                                        <span class="formula-part">Sticker Price</span>
                                        <span class="formula-op">×</span>
                                        <span class="formula-part">50%</span>
                                    </div>
                                    <div class="calculation">
                                        <span class="calc-value">৳{formatNum(stickerData.sticker_price)}</span>
                                        <span class="calc-op">×</span>
                                        <span class="calc-value">0.5</span>
                                        <span class="calc-equals">=</span>
                                        <span class="calc-result highlight success">৳{formatNum(stickerData.margin_of_safety)}</span>
                                    </div>
                                </div>
                                <div class="step-note success">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                                    </svg>
                                    Buy below this price for maximum safety
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            {/if}
        </div>
    {/if}

    <!-- Grade Calculation Breakdown -->
    {#if fourMsData}
        <div class="breakdown-section">
            <button
                class="section-toggle"
                class:expanded={gradeExpanded}
                on:click={() => gradeExpanded = !gradeExpanded}
                aria-expanded={gradeExpanded}
            >
                <div class="toggle-left">
                    <div class="toggle-icon grade">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                            <polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                    </div>
                    <div class="toggle-text">
                        <span class="toggle-title">Grade Calculation</span>
                        <span class="toggle-subtitle">4Ms Weighted Score Breakdown</span>
                    </div>
                </div>
                <div class="toggle-chevron">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6 9 12 15 18 9"/>
                    </svg>
                </div>
            </button>

            {#if gradeExpanded}
                <div class="grade-container" transition:slide={{ duration: 400, easing: quintOut }}>
                    <div class="grade-explanation">
                        <p>The overall score is a weighted average of the Four Ms. All scores are now <strong>100% objective</strong>, calculated from financial data: <strong>Meaning</strong> (20%) measures business predictability, <strong>Moat</strong> (30%) competitive advantage, <strong>Management</strong> (20%) capital allocation, and <strong>Margin of Safety</strong> (30%) price vs value.</p>
                    </div>

                    <div class="grade-formula">
                        <div class="grade-formula-header">
                            <span class="formula-label">Overall Score Formula</span>
                        </div>
                        <div class="grade-equation">
                            <span class="eq-part">(Meaning × 0.20)</span>
                            <span class="eq-op">+</span>
                            <span class="eq-part">(Moat × 0.30)</span>
                            <span class="eq-op">+</span>
                            <span class="eq-part">(Management × 0.20)</span>
                            <span class="eq-op">+</span>
                            <span class="eq-part">(MOS × 0.30)</span>
                        </div>
                    </div>

                    <div class="grade-components">
                        <div class="grade-component">
                            <div class="component-header">
                                <span class="component-name">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <circle cx="12" cy="12" r="10"/>
                                        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                                        <line x1="12" y1="17" x2="12.01" y2="17"/>
                                    </svg>
                                    Meaning
                                </span>
                                <span class="component-weight">20%</span>
                            </div>
                            <div class="component-score">
                                <div class="score-bar">
                                    <div
                                        class="score-fill"
                                        class:good={meaningScore >= 70}
                                        class:medium={meaningScore >= 50 && meaningScore < 70}
                                        class:low={meaningScore < 50}
                                        style="width: {meaningScore}%"
                                    ></div>
                                </div>
                                <span class="score-value">{meaningScore.toFixed(0)}</span>
                            </div>
                            <span class="component-note">Revenue stability, earnings consistency</span>
                            <div class="component-calc">
                                <span class="calc-mini">{meaningScore.toFixed(0)} × 0.20 = <strong>{(meaningScore * 0.20).toFixed(1)}</strong></span>
                            </div>
                        </div>

                        <div class="grade-component">
                            <div class="component-header">
                                <span class="component-name">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                                    </svg>
                                    Moat
                                </span>
                                <span class="component-weight">30%</span>
                            </div>
                            <div class="component-score">
                                <div class="score-bar">
                                    <div
                                        class="score-fill"
                                        class:good={fourMsData.moat.score >= 70}
                                        class:medium={fourMsData.moat.score >= 50 && fourMsData.moat.score < 70}
                                        class:low={fourMsData.moat.score < 50}
                                        style="width: {fourMsData.moat.score}%"
                                    ></div>
                                </div>
                                <span class="score-value">{fourMsData.moat.score.toFixed(0)}</span>
                            </div>
                            <span class="component-note">ROE consistency, gross margins</span>
                            <div class="component-calc">
                                <span class="calc-mini">{fourMsData.moat.score.toFixed(0)} × 0.30 = <strong>{(fourMsData.moat.score * 0.30).toFixed(1)}</strong></span>
                            </div>
                        </div>

                        <div class="grade-component">
                            <div class="component-header">
                                <span class="component-name">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                        <circle cx="9" cy="7" r="4"/>
                                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                                        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                                    </svg>
                                    Management
                                </span>
                                <span class="component-weight">20%</span>
                            </div>
                            <div class="component-score">
                                <div class="score-bar">
                                    <div
                                        class="score-fill"
                                        class:good={fourMsData.management.score >= 70}
                                        class:medium={fourMsData.management.score >= 50 && fourMsData.management.score < 70}
                                        class:low={fourMsData.management.score < 50}
                                        style="width: {fourMsData.management.score}%"
                                    ></div>
                                </div>
                                <span class="score-value">{fourMsData.management.score.toFixed(0)}</span>
                            </div>
                            <span class="component-note">Debt levels, capital allocation</span>
                            <div class="component-calc">
                                <span class="calc-mini">{fourMsData.management.score.toFixed(0)} × 0.20 = <strong>{(fourMsData.management.score * 0.20).toFixed(1)}</strong></span>
                            </div>
                        </div>

                        <div class="grade-component">
                            <div class="component-header">
                                <span class="component-name">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <line x1="12" y1="1" x2="12" y2="23"/>
                                        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                                    </svg>
                                    Margin of Safety
                                </span>
                                <span class="component-weight">30%</span>
                            </div>
                            <div class="component-score">
                                <div class="score-bar">
                                    <div
                                        class="score-fill"
                                        class:good={fourMsData.mos.score >= 70}
                                        class:medium={fourMsData.mos.score >= 50 && fourMsData.mos.score < 70}
                                        class:low={fourMsData.mos.score < 50}
                                        style="width: {fourMsData.mos.score}%"
                                    ></div>
                                </div>
                                <span class="score-value">{fourMsData.mos.score.toFixed(0)}</span>
                            </div>
                            <span class="component-note">Price vs intrinsic value</span>
                            <div class="component-calc">
                                <span class="calc-mini">{fourMsData.mos.score.toFixed(0)} × 0.30 = <strong>{(fourMsData.mos.score * 0.30).toFixed(1)}</strong></span>
                            </div>
                        </div>
                    </div>

                    <div class="grade-total">
                        <div class="total-calculation">
                            <span class="total-parts">
                                {(meaningScore * 0.20).toFixed(1)} + {(fourMsData.moat.score * 0.30).toFixed(1)} + {(fourMsData.management.score * 0.20).toFixed(1)} + {(fourMsData.mos.score * 0.30).toFixed(1)}
                            </span>
                            <span class="total-equals">=</span>
                            <span class="total-score">{fourMsData.overall_score.toFixed(0)}</span>
                        </div>
                        <div class="grade-scale">
                            <div class="scale-item" class:active={fourMsData.overall_grade === 'A'}>
                                <span class="scale-grade">A</span>
                                <span class="scale-range">85+</span>
                            </div>
                            <div class="scale-item" class:active={fourMsData.overall_grade === 'B'}>
                                <span class="scale-grade">B</span>
                                <span class="scale-range">70-84</span>
                            </div>
                            <div class="scale-item" class:active={fourMsData.overall_grade === 'C'}>
                                <span class="scale-grade">C</span>
                                <span class="scale-range">55-69</span>
                            </div>
                            <div class="scale-item" class:active={fourMsData.overall_grade === 'D'}>
                                <span class="scale-grade">D</span>
                                <span class="scale-range">40-54</span>
                            </div>
                            <div class="scale-item" class:active={fourMsData.overall_grade === 'F'}>
                                <span class="scale-grade">F</span>
                                <span class="scale-range">&lt;40</span>
                            </div>
                        </div>
                    </div>
                </div>
            {/if}
        </div>
    {/if}
</div>

<style>
    .calculation-breakdown {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        margin-top: 1.5rem;
    }

    .breakdown-section {
        background: var(--bg-card, #fff);
        border: 1px solid var(--border, #e5e7eb);
        border-radius: var(--radius-lg, 12px);
        overflow: hidden;
    }

    /* Toggle Button */
    .section-toggle {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 1.25rem;
        background: linear-gradient(135deg, var(--bg-secondary, #f9fafb) 0%, var(--bg-card, #fff) 100%);
        border: none;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .section-toggle:hover {
        background: linear-gradient(135deg, var(--bg-secondary, #f3f4f6) 0%, var(--bg-secondary, #f9fafb) 100%);
    }

    .toggle-left {
        display: flex;
        align-items: center;
        gap: 0.875rem;
    }

    .toggle-icon {
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, var(--accent-primary, #059669) 0%, #047857 100%);
        border-radius: 10px;
        color: white;
        box-shadow: 0 2px 8px rgba(5, 150, 105, 0.25);
    }

    .toggle-icon.grade {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.25);
    }

    .toggle-text {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 0.125rem;
    }

    .toggle-title {
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
        font-size: 0.9375rem;
        font-weight: 600;
        color: var(--text-primary, #111827);
    }

    .toggle-subtitle {
        font-size: 0.75rem;
        color: var(--text-muted, #6b7280);
    }

    .toggle-chevron {
        color: var(--text-muted, #9ca3af);
        transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    .section-toggle.expanded .toggle-chevron {
        transform: rotate(180deg);
    }

    /* Steps Container */
    .steps-container {
        padding: 1.5rem;
        background: linear-gradient(180deg, var(--bg-secondary, #f9fafb) 0%, var(--bg-card, #fff) 100%);
        border-top: 1px solid var(--border-light, #f3f4f6);
    }

    .steps-flow {
        display: flex;
        flex-direction: column;
        gap: 0;
    }

    /* Individual Step */
    .calc-step {
        display: flex;
        gap: 1rem;
        padding: 1rem 0;
        animation: stepFadeIn 0.4s ease-out forwards;
        animation-delay: calc(var(--delay, 0) * 0.08s);
        opacity: 0;
    }

    @keyframes stepFadeIn {
        from {
            opacity: 0;
            transform: translateX(-10px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    .step-number {
        flex-shrink: 0;
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, var(--accent-primary, #059669) 0%, #047857 100%);
        color: white;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.8125rem;
        font-weight: 600;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(5, 150, 105, 0.2);
    }

    .calc-step.final .step-number {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
    }

    .step-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .step-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .step-label {
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
        font-size: 0.8125rem;
        font-weight: 600;
        color: var(--text-secondary, #374151);
    }

    /* Formula Box */
    .formula-box {
        background: var(--bg-card, #fff);
        border: 1px solid var(--border, #e5e7eb);
        border-radius: 10px;
        padding: 0.875rem 1rem;
        display: flex;
        flex-direction: column;
        gap: 0.625rem;
    }

    .formula {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.375rem;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.8125rem;
        color: var(--text-muted, #6b7280);
    }

    .formula-part {
        color: var(--text-secondary, #4b5563);
    }

    .formula-equals {
        color: var(--accent-primary, #059669);
        font-weight: 600;
    }

    .formula-op {
        color: var(--text-muted, #9ca3af);
    }

    .formula-func {
        color: #8b5cf6;
    }

    .formula-sep {
        color: var(--text-muted, #9ca3af);
    }

    .calculation {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.375rem;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.875rem;
        padding-top: 0.5rem;
        border-top: 1px dashed var(--border-light, #e5e7eb);
    }

    .calc-value {
        color: var(--text-primary, #111827);
        font-weight: 500;
    }

    .calc-op, .calc-equals {
        color: var(--text-muted, #9ca3af);
    }

    .calc-func {
        color: #8b5cf6;
    }

    .calc-sep {
        color: var(--text-muted, #9ca3af);
    }

    .calc-result {
        color: var(--accent-primary, #059669);
        font-weight: 600;
        padding: 0.125rem 0.5rem;
        background: rgba(5, 150, 105, 0.08);
        border-radius: 4px;
    }

    .calc-result.highlight {
        background: rgba(5, 150, 105, 0.12);
    }

    .calc-result.highlight.success {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.1) 100%);
        box-shadow: 0 1px 3px rgba(5, 150, 105, 0.1);
    }

    /* Step Note */
    .step-note {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        font-size: 0.6875rem;
        color: var(--text-muted, #6b7280);
        padding: 0.375rem 0.625rem;
        background: var(--bg-secondary, #f9fafb);
        border-radius: 6px;
        width: fit-content;
    }

    .step-note.info {
        color: #3b82f6;
        background: rgba(59, 130, 246, 0.08);
    }

    .step-note.success {
        color: var(--success, #059669);
        background: rgba(5, 150, 105, 0.08);
    }

    /* Step Connector */
    .step-connector {
        width: 2px;
        height: 16px;
        background: linear-gradient(180deg, var(--accent-primary, #059669) 0%, rgba(5, 150, 105, 0.2) 100%);
        margin-left: 13px;
        border-radius: 1px;
    }

    /* Grade Container */
    .grade-container {
        padding: 1.5rem;
        background: linear-gradient(180deg, var(--bg-secondary, #f9fafb) 0%, var(--bg-card, #fff) 100%);
        border-top: 1px solid var(--border-light, #f3f4f6);
    }

    .grade-explanation {
        font-size: 0.8125rem;
        color: var(--text-secondary, #4b5563);
        line-height: 1.6;
        margin-bottom: 1.25rem;
        padding: 0.875rem 1rem;
        background: var(--bg-card, #fff);
        border-radius: 8px;
        border-left: 3px solid #6366f1;
    }

    .grade-explanation strong {
        color: var(--text-primary, #111827);
    }

    /* Grade Formula */
    .grade-formula {
        background: var(--bg-card, #fff);
        border: 1px solid var(--border, #e5e7eb);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1.25rem;
    }

    .grade-formula-header {
        margin-bottom: 0.75rem;
    }

    .formula-label {
        font-size: 0.6875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted, #6b7280);
    }

    .grade-equation {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.375rem;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.8125rem;
    }

    .eq-part {
        color: var(--text-primary, #111827);
        padding: 0.25rem 0.5rem;
        background: var(--bg-secondary, #f3f4f6);
        border-radius: 4px;
    }

    .eq-op {
        color: #6366f1;
        font-weight: 600;
    }

    /* Grade Components */
    .grade-components {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 1.25rem;
    }

    .grade-component {
        background: var(--bg-card, #fff);
        border: 1px solid var(--border, #e5e7eb);
        border-radius: 10px;
        padding: 1rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .component-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .component-name {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        font-size: 0.8125rem;
        font-weight: 600;
        color: var(--text-primary, #111827);
    }

    .component-name svg {
        color: var(--text-muted, #9ca3af);
    }

    .component-weight {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6875rem;
        font-weight: 600;
        color: #6366f1;
        padding: 0.125rem 0.375rem;
        background: rgba(99, 102, 241, 0.1);
        border-radius: 4px;
    }

    .component-score {
        display: flex;
        align-items: center;
        gap: 0.625rem;
    }

    .score-bar {
        flex: 1;
        height: 6px;
        background: var(--bg-secondary, #e5e7eb);
        border-radius: 3px;
        overflow: hidden;
    }

    .score-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    .score-fill.good {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
    }

    .score-fill.medium {
        background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);
    }

    .score-fill.low {
        background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
    }

    .score-fill.neutral {
        background: linear-gradient(90deg, #6b7280 0%, #4b5563 100%);
    }

    .score-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-primary, #111827);
        min-width: 28px;
        text-align: right;
    }

    .component-note {
        font-size: 0.6875rem;
        color: var(--text-muted, #9ca3af);
    }

    .component-calc {
        padding-top: 0.5rem;
        border-top: 1px dashed var(--border-light, #e5e7eb);
    }

    .calc-mini {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: var(--text-secondary, #6b7280);
    }

    .calc-mini strong {
        color: #6366f1;
    }

    /* Grade Total */
    .grade-total {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(79, 70, 229, 0.04) 100%);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 1.25rem;
    }

    .total-calculation {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
        font-family: 'JetBrains Mono', monospace;
    }

    .total-parts {
        font-size: 0.875rem;
        color: var(--text-secondary, #4b5563);
    }

    .total-equals {
        font-size: 1rem;
        color: #6366f1;
        font-weight: 600;
    }

    .total-score {
        font-size: 1.5rem;
        font-weight: 700;
        color: #6366f1;
        padding: 0.25rem 0.75rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15);
    }

    /* Grade Scale */
    .grade-scale {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
    }

    .scale-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.125rem;
        padding: 0.5rem 0.875rem;
        background: var(--bg-card, #fff);
        border: 1px solid var(--border, #e5e7eb);
        border-radius: 8px;
        opacity: 0.5;
        transition: all 0.2s ease;
    }

    .scale-item.active {
        opacity: 1;
        border-color: #6366f1;
        background: white;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15);
        transform: translateY(-2px);
    }

    .scale-grade {
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
        font-size: 1rem;
        font-weight: 700;
        color: var(--text-primary, #111827);
    }

    .scale-item.active .scale-grade {
        color: #6366f1;
    }

    .scale-range {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.625rem;
        color: var(--text-muted, #9ca3af);
    }

    /* Responsive */
    @media (max-width: 640px) {
        .toggle-left {
            gap: 0.625rem;
        }

        .toggle-icon {
            width: 36px;
            height: 36px;
        }

        .toggle-title {
            font-size: 0.875rem;
        }

        .formula, .calculation {
            font-size: 0.75rem;
        }

        .grade-components {
            grid-template-columns: 1fr;
        }

        .grade-scale {
            flex-wrap: wrap;
        }
    }
</style>
