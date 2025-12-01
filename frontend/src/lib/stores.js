import { writable } from "svelte/store"; 
export const sender = writable('');
export const receiver = writable(''); 
export const reverseSig = writable(false);
export const celltypes = writable([]);