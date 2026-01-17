<script lang="ts">
    import '../app.css';
    import { page } from '$app/stores';
    import { theme } from '$lib/stores/theme';
    import { onMount } from 'svelte';

    let sidebarExpanded = false;
    let isMobile = false;
    let mobileMenuOpen = false;

    onMount(() => {
        theme.init();
        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    });

    function checkMobile() {
        isMobile = window.innerWidth < 768;
        if (!isMobile) mobileMenuOpen = false;
    }

    function toggleTheme() {
        theme.toggle();
    }

    function closeMobileMenu() {
        mobileMenuOpen = false;
    }

    $: currentPath = $page.url.pathname;
</script>

<div class="app-layout" class:sidebar-expanded={sidebarExpanded}>
    <!-- Sidebar -->
    <aside
        class="sidebar"
        class:expanded={sidebarExpanded}
        class:mobile-open={mobileMenuOpen}
        on:mouseenter={() => !isMobile && (sidebarExpanded = true)}
        on:mouseleave={() => !isMobile && (sidebarExpanded = false)}
        role="navigation"
    >
        <!-- Brand -->
        <div class="sidebar-brand">
            <a href="/" class="brand-link">
                <span class="brand-icon">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                        <path d="M2 17l10 5 10-5"/>
                        <path d="M2 12l10 5 10-5"/>
                    </svg>
                </span>
                <span class="brand-text">DSE Investor</span>
            </a>
        </div>

        <!-- Navigation -->
        <nav class="sidebar-nav">
            <a href="/" class="nav-item" class:active={currentPath === '/'} on:click={closeMobileMenu}>
                <span class="nav-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                        <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                        <line x1="12" y1="22.08" x2="12" y2="12"/>
                    </svg>
                </span>
                <span class="nav-label">Portfolio</span>
            </a>

            <a href="/stocks" class="nav-item" class:active={currentPath.startsWith('/stocks')} on:click={closeMobileMenu}>
                <span class="nav-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
                        <polyline points="16 7 22 7 22 13"/>
                    </svg>
                </span>
                <span class="nav-label">Stocks</span>
            </a>

            <a href="/calculator" class="nav-item" class:active={currentPath === '/calculator'} on:click={closeMobileMenu}>
                <span class="nav-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="4" y="2" width="16" height="20" rx="2"/>
                        <line x1="8" y1="6" x2="16" y2="6"/>
                        <line x1="8" y1="10" x2="16" y2="10"/>
                        <line x1="8" y1="14" x2="12" y2="14"/>
                        <line x1="8" y1="18" x2="12" y2="18"/>
                    </svg>
                </span>
                <span class="nav-label">Calculator</span>
            </a>

            <a href="/admin" class="nav-item" class:active={currentPath === '/admin'} on:click={closeMobileMenu}>
                <span class="nav-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                </span>
                <span class="nav-label">Data Entry</span>
            </a>
        </nav>

        <!-- Sidebar Footer -->
        <div class="sidebar-footer">
            <button
                class="theme-toggle"
                on:click={toggleTheme}
                aria-label="Toggle theme"
            >
                {#if $theme === 'light'}
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                    </svg>
                {:else}
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="5"/>
                        <line x1="12" y1="1" x2="12" y2="3"/>
                        <line x1="12" y1="21" x2="12" y2="23"/>
                        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                        <line x1="1" y1="12" x2="3" y2="12"/>
                        <line x1="21" y1="12" x2="23" y2="12"/>
                        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                    </svg>
                {/if}
                <span class="toggle-label">{$theme === 'light' ? 'Dark' : 'Light'} Mode</span>
            </button>

            <div class="sidebar-credit">
                <span class="credit-text">Rule #1 Investing</span>
            </div>
        </div>
    </aside>

    <!-- Mobile Overlay -->
    {#if mobileMenuOpen}
        <div class="mobile-overlay" on:click={closeMobileMenu} on:keydown={closeMobileMenu} role="button" tabindex="0" aria-label="Close menu"></div>
    {/if}

    <!-- Main Content -->
    <div class="main-wrapper">
        <!-- Top Header (Mobile) -->
        <header class="top-header">
            <button class="mobile-menu-btn" on:click={() => mobileMenuOpen = !mobileMenuOpen} aria-label="Toggle menu">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="3" y1="12" x2="21" y2="12"/>
                    <line x1="3" y1="6" x2="21" y2="6"/>
                    <line x1="3" y1="18" x2="21" y2="18"/>
                </svg>
            </button>

            <a href="/" class="mobile-brand">
                <span class="brand-icon-sm">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                        <path d="M2 17l10 5 10-5"/>
                        <path d="M2 12l10 5 10-5"/>
                    </svg>
                </span>
                DSE Investor
            </a>

            <button class="theme-toggle-mobile" on:click={toggleTheme} aria-label="Toggle theme">
                {#if $theme === 'light'}
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                    </svg>
                {:else}
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="5"/>
                        <line x1="12" y1="1" x2="12" y2="3"/>
                        <line x1="12" y1="21" x2="12" y2="23"/>
                        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                        <line x1="1" y1="12" x2="3" y2="12"/>
                        <line x1="21" y1="12" x2="23" y2="12"/>
                        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                    </svg>
                {/if}
            </button>
        </header>

        <main>
            <slot />
        </main>
    </div>
</div>

<style>
    .app-layout {
        display: flex;
        min-height: 100vh;
        background: var(--bg-primary);
    }

    /* =====================
       SIDEBAR
       ===================== */
    .sidebar {
        position: fixed;
        top: 0;
        left: 0;
        height: 100vh;
        width: var(--sidebar-collapsed);
        background: var(--bg-sidebar);
        border-right: 1px solid var(--sidebar-border);
        display: flex;
        flex-direction: column;
        z-index: 100;
        transition: width var(--duration-normal) var(--ease-out-expo);
        overflow: hidden;
    }

    .sidebar.expanded {
        width: var(--sidebar-expanded);
    }

    .sidebar-brand {
        padding: 1.25rem;
        border-bottom: 1px solid var(--sidebar-border);
    }

    .brand-link {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        text-decoration: none;
        color: var(--sidebar-text);
    }

    .brand-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
        background: var(--accent-primary);
        border-radius: var(--radius-md);
        color: white;
        flex-shrink: 0;
    }

    .brand-text {
        font-family: 'DM Serif Display', Georgia, serif;
        font-size: 1.125rem;
        white-space: nowrap;
        opacity: 0;
        transition: opacity var(--duration-fast) var(--ease-out-expo);
    }

    .sidebar.expanded .brand-text {
        opacity: 1;
    }

    /* Sidebar Navigation */
    .sidebar-nav {
        flex: 1;
        padding: 1rem 0.875rem;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .nav-item {
        display: flex;
        align-items: center;
        gap: 0.875rem;
        padding: 0.75rem;
        border-radius: var(--radius-md);
        color: var(--sidebar-text-muted);
        text-decoration: none;
        transition: all var(--duration-fast) var(--ease-out-expo);
        white-space: nowrap;
    }

    .nav-item:hover {
        background: var(--sidebar-hover);
        color: var(--sidebar-text);
    }

    .nav-item.active {
        background: var(--accent-primary);
        color: white;
    }

    .nav-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        flex-shrink: 0;
    }

    .nav-label {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.875rem;
        font-weight: 500;
        opacity: 0;
        transition: opacity var(--duration-fast) var(--ease-out-expo);
    }

    .sidebar.expanded .nav-label {
        opacity: 1;
    }

    /* Sidebar Footer */
    .sidebar-footer {
        padding: 1rem 0.875rem;
        border-top: 1px solid var(--sidebar-border);
    }

    .theme-toggle {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        width: 100%;
        padding: 0.75rem;
        background: var(--sidebar-hover);
        border: none;
        border-radius: var(--radius-md);
        color: var(--sidebar-text-muted);
        cursor: pointer;
        transition: all var(--duration-fast) var(--ease-out-expo);
    }

    .theme-toggle:hover {
        background: var(--accent-tertiary);
        color: var(--sidebar-text);
    }

    .toggle-label {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.8125rem;
        font-weight: 500;
        opacity: 0;
        white-space: nowrap;
        transition: opacity var(--duration-fast) var(--ease-out-expo);
    }

    .sidebar.expanded .toggle-label {
        opacity: 1;
    }

    .sidebar-credit {
        margin-top: 0.75rem;
        padding: 0 0.75rem;
    }

    .credit-text {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.6875rem;
        color: var(--text-muted);
        opacity: 0;
        white-space: nowrap;
        transition: opacity var(--duration-fast) var(--ease-out-expo);
    }

    .sidebar.expanded .credit-text {
        opacity: 1;
    }

    /* =====================
       MAIN CONTENT
       ===================== */
    .main-wrapper {
        flex: 1;
        margin-left: var(--sidebar-collapsed);
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        transition: margin-left var(--duration-normal) var(--ease-out-expo);
    }

    .top-header {
        display: none;
    }

    main {
        flex: 1;
        padding: 2rem;
        max-width: 1400px;
        margin: 0 auto;
        width: 100%;
    }

    /* =====================
       MOBILE STYLES
       ===================== */
    @media (max-width: 768px) {
        .sidebar {
            transform: translateX(-100%);
            width: var(--sidebar-expanded);
        }

        .sidebar.mobile-open {
            transform: translateX(0);
        }

        .sidebar .brand-text,
        .sidebar .nav-label,
        .sidebar .toggle-label,
        .sidebar .credit-text {
            opacity: 1;
        }

        .main-wrapper {
            margin-left: 0;
        }

        .top-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.25rem;
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-light);
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .mobile-menu-btn,
        .theme-toggle-mobile {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background: transparent;
            border: none;
            border-radius: var(--radius-md);
            color: var(--text-primary);
            cursor: pointer;
            transition: background var(--duration-fast) var(--ease-out-expo);
        }

        .mobile-menu-btn:hover,
        .theme-toggle-mobile:hover {
            background: var(--bg-secondary);
        }

        .mobile-brand {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: 'DM Serif Display', Georgia, serif;
            font-size: 1.125rem;
            color: var(--text-primary);
            text-decoration: none;
        }

        .brand-icon-sm {
            color: var(--accent-primary);
        }

        .mobile-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 90;
            animation: fadeIn var(--duration-fast) var(--ease-out-expo);
        }

        main {
            padding: 1.25rem;
        }
    }

    @media (max-width: 480px) {
        main {
            padding: 1rem;
        }
    }
</style>
