import { describe, expect, it, vi } from 'vitest';

import { isPrivateAddress, validateProxyUrl } from './proxy.ts';

vi.mock('node:dns/promises', () => ({
  lookup: vi.fn(),
}));

import { lookup } from 'node:dns/promises';

type MockLookupResult = { address: string; family: number }[];

const mockedLookup = vi.mocked(lookup) as unknown as {
  mockImplementationOnce(fn: () => Promise<MockLookupResult>): void;
};

describe('isPrivateAddress', () => {
  it('returns false for public IPv4 addresses', () => {
    expect(isPrivateAddress('1.1.1.1')).toBe(false);
    expect(isPrivateAddress('8.8.8.8')).toBe(false);
    expect(isPrivateAddress('203.0.113.1')).toBe(false);
  });

  it('returns true for RFC1918 IPv4 addresses', () => {
    expect(isPrivateAddress('10.0.0.1')).toBe(true);
    expect(isPrivateAddress('172.16.0.1')).toBe(true);
    expect(isPrivateAddress('192.168.1.1')).toBe(true);
  });

  it('returns true for loopback and link-local IPv4 addresses', () => {
    expect(isPrivateAddress('127.0.0.1')).toBe(true);
    expect(isPrivateAddress('169.254.1.1')).toBe(true);
  });

  it('returns true for special IPv4 ranges', () => {
    expect(isPrivateAddress('0.0.0.0')).toBe(true);
    expect(isPrivateAddress('100.64.0.1')).toBe(true);
    expect(isPrivateAddress('224.0.0.1')).toBe(true);
    expect(isPrivateAddress('255.255.255.255')).toBe(true);
  });

  it('returns true for special IPv6 addresses', () => {
    expect(isPrivateAddress('::')).toBe(true);
    expect(isPrivateAddress('::1')).toBe(true);
    expect(isPrivateAddress('fe80::1')).toBe(true);
    expect(isPrivateAddress('fec0::1')).toBe(true);
    expect(isPrivateAddress('fd00::1')).toBe(true);
    expect(isPrivateAddress('ff02::1')).toBe(true);
  });

  it('returns true for IPv4-mapped IPv6 addresses when the IPv4 part is private', () => {
    expect(isPrivateAddress('::ffff:192.168.1.1')).toBe(true);
    expect(isPrivateAddress('::ffff:127.0.0.1')).toBe(true);
  });

  it('returns false for IPv4-mapped IPv6 addresses when the IPv4 part is public', () => {
    expect(isPrivateAddress('::ffff:1.1.1.1')).toBe(false);
  });

  it('returns true for non-IP literals', () => {
    expect(isPrivateAddress('not-an-ip')).toBe(true);
  });
});

describe('validateProxyUrl', () => {
  it('rejects missing or non-HTTP(S) schemes', async () => {
    expect(await validateProxyUrl('')).toBeNull();
    expect(await validateProxyUrl('ftp://example.com/file.png')).toBeNull();
    expect(await validateProxyUrl('file:///etc/passwd')).toBeNull();
  });

  it('rejects empty or internal hostnames', async () => {
    expect(await validateProxyUrl('http:///path')).toBeNull();
    expect(await validateProxyUrl('http://localhost/image.png')).toBeNull();
    expect(await validateProxyUrl('http://foo.local/image.png')).toBeNull();
    expect(await validateProxyUrl('http://foo.internal/image.png')).toBeNull();
    expect(await validateProxyUrl('http://foo.localhost/image.png')).toBeNull();
  });

  it('rejects private IP addresses without performing DNS lookup', async () => {
    expect(await validateProxyUrl('http://127.0.0.1/image.png')).toBeNull();
    expect(await validateProxyUrl('http://192.168.1.1/image.png')).toBeNull();
    expect(await validateProxyUrl('http://10.0.0.1/image.png')).toBeNull();
    expect(mockedLookup).not.toHaveBeenCalled();
  });

  it('rejects hostnames that resolve to private addresses', async () => {
    mockedLookup.mockImplementationOnce(async () => [
      { address: '192.168.1.1', family: 4 },
    ]);
    expect(await validateProxyUrl('http://evil.example.com/image.png')).toBeNull();
    expect(mockedLookup).toHaveBeenCalledWith('evil.example.com', {
      all: true,
      verbatim: true,
    });
  });

  it('rejects hostnames that resolve to a mix of public and private addresses', async () => {
    mockedLookup.mockImplementationOnce(async () => [
      { address: '1.1.1.1', family: 4 },
      { address: '192.168.1.1', family: 4 },
    ]);
    expect(await validateProxyUrl('http://evil.example.com/image.png')).toBeNull();
  });

  it('accepts hostnames that resolve to public addresses', async () => {
    mockedLookup.mockImplementationOnce(async () => [
      { address: '93.184.216.34', family: 4 },
    ]);
    const result = await validateProxyUrl('http://example.com/image.png?foo=bar#baz');
    expect(result).not.toBeNull();
    expect(result!.href).toBe('http://example.com/image.png?foo=bar#baz');
  });

  it('strips userinfo from the URL', async () => {
    mockedLookup.mockImplementationOnce(async () => [
      { address: '93.184.216.34', family: 4 },
    ]);
    const result = await validateProxyUrl('http://user:pass@example.com/image.png');
    expect(result).not.toBeNull();
    expect(result!.href).toBe('http://example.com/image.png');
    expect(result!.username).toBe('');
    expect(result!.password).toBe('');
  });
});
