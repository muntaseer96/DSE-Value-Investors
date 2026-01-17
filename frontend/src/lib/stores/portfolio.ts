import { writable } from 'svelte/store';
import type { PortfolioSummary } from '$lib/api/client';

// Portfolio data store - persists across page navigations
export const portfolioData = writable<PortfolioSummary | null>(null);
export const portfolioLoaded = writable<boolean>(false);
export const portfolioLoading = writable<boolean>(false);
export const portfolioError = writable<string>('');
