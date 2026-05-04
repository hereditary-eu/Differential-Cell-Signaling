import { scaleOrdinal, schemeTableau10 } from "d3";
import { writable, derived } from "svelte/store"; 
import type { NeighborhoodData} from "./types";
export const sender = writable('');
export const receiver = writable(''); 
export const reverseSig = writable(false);
export const celltypes = writable([]);
export const colorScale = derived(celltypes, ($celltypes): d3.ScaleOrdinal<string, string, string> => {
    return scaleOrdinal<string, string, string>() 
        .domain($celltypes)
        .range(schemeTableau10)
        .unknown('#999999');  // Use a fallback color string instead of undefined
});
// ["rgb(32,142,183)", "rgb(242,87,156)", "rgb(54,229,21)", 
// "rgb(207,96,243)", "rgb(159,216,65)", "rgb(46,48,231)", 
// "rgb(114,142,36)", "rgb(134,9,103)", "rgb(139,232,173)", 
// "rgb(137,28,26)", "rgb(92,214,244)", "rgb(93,62,71)", 
// "rgb(194,203,161)", "rgb(30,67,141)", "rgb(237,170,131)", 
// "rgb(21,81,38)", "rgb(250,27,252)", "rgb(28,152,32)", 
// "rgb(250,175,227)", "rgb(241,212,56)", "rgb(103,120,245)", 
// "rgb(254,143,6)", "rgb(182,197,245)", "rgb(253,43,49)", 
// "rgb(141,124,166)", "rgb(134,102,9)"]
export const filtersApplied = writable(false);
export const filteringQueryStr = writable('');
export const selectedCaseStudy = writable('');
export const selectedComparison = writable('');
export const selectedNode = writable('');
export const selectedNodeName = writable('');
export const neighborhoodData = writable(<NeighborhoodData | null>null);
export const aesSettings = writable({
    LR: <'reset' | 'viridis' | 'volcano'>('reset'),
    TF: <'reset' | 'endShape'>('reset'),
    CT: <boolean>(true),
    groupNodes: <boolean>(false)
})
export const highlightedNode = writable<string | null>(null);
export const highlightedCycle = writable<{
  nodeIds: Set<string>;
  edgePairs: Set<string>; // "sourceId->targetId" for fast lookup
} | null>(null);