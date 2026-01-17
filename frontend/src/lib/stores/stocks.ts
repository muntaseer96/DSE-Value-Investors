import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import type { StockPrice } from '$lib/api/client';

// Session storage keys
const STORAGE_KEY = 'stocks_data';
const LOADED_KEY = 'stocks_loaded';

// Helper to get initial data from sessionStorage
function getStoredData(): StockPrice[] {
    if (!browser) return [];
    const stored = sessionStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
}

function getStoredLoaded(): boolean {
    if (!browser) return false;
    return sessionStorage.getItem(LOADED_KEY) === 'true';
}

// Stocks data store - persists across page navigations within session
export const stocksData = writable<StockPrice[]>(getStoredData());
export const stocksLoaded = writable<boolean>(getStoredLoaded());
export const stocksLoading = writable<boolean>(false);
export const stocksError = writable<string>('');

// Sync to sessionStorage when data changes
if (browser) {
    stocksData.subscribe(value => {
        if (value && value.length > 0) {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
        } else {
            sessionStorage.removeItem(STORAGE_KEY);
        }
    });

    stocksLoaded.subscribe(value => {
        sessionStorage.setItem(LOADED_KEY, value.toString());
    });
}
