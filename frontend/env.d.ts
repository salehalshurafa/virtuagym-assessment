/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly MAILPIT_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
