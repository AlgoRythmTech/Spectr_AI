/**
 * Production-safe logger.
 *
 * - `log` / `info` / `debug`: only print in development (noise in prod)
 * - `warn`: only print in development
 * - `error`: ALWAYS prints (real failures should always be visible)
 *
 * Usage:
 *   import { log, warn, error } from '@/lib/logger';
 *   log('[Auth] signed in', user);
 */
const IS_DEV = process.env.NODE_ENV === 'development';

export const log = IS_DEV ? console.log.bind(console) : () => {};
export const info = IS_DEV ? console.info.bind(console) : () => {};
export const debug = IS_DEV ? console.debug.bind(console) : () => {};
export const warn = IS_DEV ? console.warn.bind(console) : () => {};
// error always on — production error visibility matters
export const error = console.error.bind(console);

const logger = { log, info, debug, warn, error };
export default logger;
