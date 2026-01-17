<script lang="ts">
    import '../app.css';
</script>

<div class="app">
    <nav class="navbar">
        <div class="nav-brand">
            <a href="/">DSE Value Investor</a>
            <span class="tagline">Rule #1 Investing</span>
        </div>
        <div class="nav-links">
            <a href="/">Portfolio</a>
            <a href="/calculator">Calculator</a>
            <a href="/stocks">Stocks</a>
        </div>
    </nav>

    <main>
        <slot />
    </main>

    <footer>
        <p>Based on Phil Town's Rule #1 Investing methodology</p>
    </footer>
</div>

<style>
    .app {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
    }

    .navbar {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }

    .nav-brand {
        display: flex;
        flex-direction: column;
    }

    .nav-brand a {
        color: #4ecca3;
        font-size: 1.5rem;
        font-weight: bold;
        text-decoration: none;
    }

    .tagline {
        color: #888;
        font-size: 0.75rem;
        margin-top: 0.25rem;
    }

    .nav-links {
        display: flex;
        gap: 2rem;
    }

    .nav-links a {
        color: #e8e8e8;
        text-decoration: none;
        font-weight: 500;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        transition: all 0.2s;
    }

    .nav-links a:hover {
        background: rgba(78, 204, 163, 0.2);
        color: #4ecca3;
    }

    main {
        flex: 1;
        padding: 2rem;
        max-width: 1400px;
        margin: 0 auto;
        width: 100%;
    }

    footer {
        text-align: center;
        padding: 1rem;
        color: #666;
        background: #0f0f1a;
        font-size: 0.875rem;
    }
</style>
