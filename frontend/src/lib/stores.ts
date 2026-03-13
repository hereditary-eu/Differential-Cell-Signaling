import { scaleOrdinal, schemeTableau10 } from "d3";
import { writable, derived } from "svelte/store"; 
import type { NeighborhoodData} from "./types";
export const sender = writable('');
export const receiver = writable(''); 
export const reverseSig = writable(false);
export const celltypes = writable([]);
export const colorScale = derived(celltypes, ($celltypes): d3.ScaleOrdinal<string, string, string> => {
    return scaleOrdinal<string, string, string>()  // Explicitly typed generic parameters including unknown type
        .domain($celltypes)
        .range(schemeTableau10)
        .unknown('#999999');  // Use a fallback color string instead of undefined
});
export const filtersApplied = writable(false);
export const selectedCaseStudy = writable('');
export const selectedComparison = writable('');
export const selectedNode = writable('');
export const neighborhoodData = writable(<NeighborhoodData | null>null);
export const aesLRMapping = writable<'reset' | 'viridis' | 'volcano'>('reset');
export const aesTFMapping = writable<'reset' | 'endShape'>('reset');