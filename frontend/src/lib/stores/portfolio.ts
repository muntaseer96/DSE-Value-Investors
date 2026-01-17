import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import type { PortfolioSummary } from '$lib/api/client';

// Session storage keys
const STORAGE_KEY = 'portfolio_data';
const LOADED_KEY = 'portfolio_loaded';

// Helper to get initial data from sessionStorage
function getStoredData(): PortfolioSummary | null {
    if (!browser) return null;
    const stored = sessionStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
}

function getStoredLoaded(): boolean {
    if (!browser) return false;
    return sessionStorage.getItem(LOADED_KEY) === 'true';
}

// Portfolio data store - persists across page navigations and refreshes within session
export const portfolioData = writable<PortfolioSummary | null>(getStoredData());
export const portfolioLoaded = writable<boolean>(getStoredLoaded());
export const portfolioLoading = writable<boolean>(false);
export const portfolioError = writable<string>('');

// Sync to sessionStorage when data changes
if (browser) {
    portfolioData.subscribe(value => {
        if (value) {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
        } else {
            sessionStorage.removeItem(STORAGE_KEY);
        }
    });

    portfolioLoaded.subscribe(value => {
        sessionStorage.setItem(LOADED_KEY, value.toString());
    });
}
