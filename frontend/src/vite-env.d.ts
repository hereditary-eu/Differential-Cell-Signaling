/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_PUPPY_URL: string;
    readonly VITE_PUPPY_AUTH: string;
    readonly VITE_BACKEND_URL: string;
    readonly DB_URL: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}