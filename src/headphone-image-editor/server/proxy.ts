import { lookup } from 'node:dns/promises';
import { isIP } from 'node:net';

const PROXY_TIMEOUT_MS = 10_000;
const PROXY_MAX_BYTES = 10 * 1024 * 1024;

export { PROXY_TIMEOUT_MS, PROXY_MAX_BYTES };

/**
 * Validate a user-supplied URL before it is fetched by the image proxy.
 *
 * This is the central sanitizer for the /api/proxy endpoint. It rejects any
 * URL that could be used for server-side request forgery (SSRF):
 *   - non-HTTP(S) schemes
 *   - empty or obviously-internal hostnames
 *   - private/reserved IP addresses (IPv4 and IPv6)
 *   - hostnames that resolve to private/reserved addresses
 *
 * On success, a fresh URL object is returned. The URL is reconstructed from
 * the parsed components so that credentials, unexpected ports, or other
 * parser artifacts are stripped.
 */
export async function validateProxyUrl(target: string): Promise<URL | null> {
  let parsed: URL;
  try {
    parsed = new URL(target);
  } catch {
    return null;
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return null;
  }

  const host = parsed.hostname.toLowerCase();
  if (!host || !isValidHostname(host)) {
    return null;
  }

  // Reject obviously internal/special hostnames synchronously.
  if (
    host === 'localhost' ||
    host.endsWith('.local') ||
    host.endsWith('.internal') ||
    host.endsWith('.localhost')
  ) {
    return null;
  }

  // Reject IP addresses that are private or otherwise special.
  if (isIP(host) && isPrivateAddress(host)) {
    return null;
  }

  // For hostnames, verify via DNS that every resolved address is public.
  if (!isIP(host) && !(await isPublicHost(host))) {
    return null;
  }

  // Reconstruct the URL from validated components, stripping any credentials.
  const base = `${parsed.protocol}//${parsed.host}`;
  const relative = `${parsed.pathname}${parsed.search}${parsed.hash}`;
  return new URL(relative, base);
}

/**
 * Resolve a hostname and ensure none of its addresses are private/reserved.
 */
async function isPublicHost(host: string): Promise<boolean> {
  try {
    const addrs = await lookup(host, { all: true, verbatim: true });
    if (addrs.length === 0) return false;
    return addrs.every((a) => !isPrivateAddress(a.address));
  } catch {
    return false;
  }
}

/**
 * Check that a hostname is syntactically valid for a public host.
 * Single-label names (e.g. "path" parsed from "http:///path") are rejected
 * because they cannot be public internet hostnames.
 */
function isValidHostname(host: string): boolean {
  // Each label must be alphanumeric plus hyphens, not start/end with hyphen,
  // and at most 63 characters. The whole name must contain at least one dot.
  const label = '[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?';
  const re = new RegExp(`^(${label}\\.)+${label}$`, 'i');
  return re.test(host);
}

/**
 * Determine whether an IP address belongs to a private, reserved, or
 * otherwise non-public range.
 */
export function isPrivateAddress(addr: string): boolean {
  const a = addr.toLowerCase();

  // IPv6 loopback / unspecified / link-local / site-local / unique local /
  // multicast.
  if (a === '::' || a === '::1') return true;
  if (a.startsWith('fe80:') || a.startsWith('fec0:')) return true;
  if (/^f[cd][0-9a-f]{2}:/.test(a)) return true;
  if (/^ff[0-9a-f]{2}:/.test(a)) return true;

  // IPv4-mapped IPv6 addresses.
  const v4mapped = /^::ffff:([0-9.]+)$/.exec(a);
  if (v4mapped) return isPrivateAddress(v4mapped[1]);

  // IPv4.
  const m = /^(\d+)\.(\d+)\.(\d+)\.(\d+)$/.exec(a);
  if (!m) {
    // Not a recognized IP literal; conservatively treat as non-public.
    return true;
  }
  const [o1, o2] = [Number(m[1]), Number(m[2])];
  if (o1 === 0) return true; // 0.0.0.0/8
  if (o1 === 10) return true; // RFC1918
  if (o1 === 127) return true; // loopback
  if (o1 === 169 && o2 === 254) return true; // link-local
  if (o1 === 172 && o2 >= 16 && o2 <= 31) return true; // RFC1918
  if (o1 === 192 && o2 === 168) return true; // RFC1918
  if (o1 === 100 && o2 >= 64 && o2 <= 127) return true; // CGNAT
  if (o1 >= 224) return true; // multicast + reserved + broadcast
  return false;
}
