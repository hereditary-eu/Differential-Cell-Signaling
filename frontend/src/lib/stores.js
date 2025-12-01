import { writable } from "svelte/store"; //, derived
// import { scaleOrdinal, schemeTableau10 } from 'd3';

export const sender = writable('');
export const receiver = writable(''); 
export const reverseSig = writable(false);
export const celltypes = writable([]);
// export const colorScale = derived(
//     celltypes,
//     ($celltypes) => scaleOrdinal(schemeTableau10).domain($celltypes)
// );