import { scaleOrdinal, schemeTableau10 } from "d3";
import { writable, derived } from "svelte/store"; 
export const sender = writable('');
export const receiver = writable(''); 
export const reverseSig = writable(false);
export const celltypes = writable([]);
// remember this is js file, cant use svelte 5 $derived synthax
export const colorScale = derived(celltypes, ($celltypes) => {
    return scaleOrdinal()
        .domain($celltypes)
        .range(schemeTableau10)
        .unknown(undefined);
});
