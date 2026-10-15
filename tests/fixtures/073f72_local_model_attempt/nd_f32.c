#include "nd_f32.h"

#define SIGN_BIT 0x80000000u
#define QNAN     0x7FC00000u
#define INF_BITS 0x7F800000u

static int is_nan(nd_f32 x) { return (x & 0x7FFFFFFFu) > INF_BITS; }
static int is_inf(nd_f32 x) { return (x & 0x7FFFFFFFu) == INF_BITS; }
static int is_zero(nd_f32 x) { return (x & 0x7FFFFFFFu) == 0u; }

/* Unpack to (exp, man) with man having bit 23 set for normals; denormals use exp = 1 and no hidden bit. */
static void unpack(nd_f32 x, int32_t *e, uint32_t *m)
{
    *e = (int32_t)((x >> 23) & 0xFFu);
    *m = x & 0x7FFFFFu;
    if (*e == 0) *e = 1; else *m |= 0x800000u;
}

/* Round and pack. `m` is a mantissa with `extra` guard bits below the 24-bit significand (m >> extra has bit 23 set for
 * a normalised value), `sticky` is non-zero if bits were discarded earlier, `e` the exponent for bit 23. */
static nd_f32 round_pack(uint32_t sign, int32_t e, uint64_t m, int extra, int sticky)
{
    uint64_t lsb_mask, half, rem, out;
    /* normalise so bit (23+extra) is set, unless the result is denormal */
    if (m == 0) return sign;
    while (m >= ((uint64_t)1 << (24 + extra))) { sticky |= (int)(m & 1u); m >>= 1; ++e; }
    while (m < ((uint64_t)1 << (23 + extra)) && e > 1) { m <<= 1; --e; }
    if (e < 1) {                                   /* denormal result: shift right into place */
        int sh = 1 - e;
        if (sh > 40) { sticky |= (m != 0); m = 0; }
        else { sticky |= (int)((m & (((uint64_t)1 << sh) - 1u)) != 0); m >>= sh; }
        e = 1;
    }
    lsb_mask = (uint64_t)1 << extra;
    half = lsb_mask >> 1;
    rem = m & (lsb_mask - 1u);
    out = m >> extra;
    if (rem > half || (rem == half && (sticky || (out & 1u)))) ++out;
    else if (rem == half && !sticky && !(out & 1u)) { /* tie to even: keep */ }
    if (out >= 0x1000000u) { out >>= 1; ++e; }     /* rounding carried into a new bit */
    if (e >= 255) return sign | INF_BITS;
    if (out < 0x800000u) e = 0;                    /* still denormal (or zero) */
    return sign | ((uint32_t)e << 23) | (uint32_t)(out & 0x7FFFFFu);
}

nd_f32 nd_f32_from_i32(int32_t v)
{
    uint32_t sign = 0, u;
    if (v == 0) return 0;
    if (v < 0) { sign = SIGN_BIT; u = (uint32_t)0 - (uint32_t)v; } else u = (uint32_t)v;
    return round_pack(sign, 150, (uint64_t)u << 8, 8, 0);   /* u = m * 2^(150-150-8) with 8 guard bits */
}

int32_t nd_f32_trunc(nd_f32 x)
{
    int32_t e = (int32_t)((x >> 23) & 0xFFu) - 127;
    uint32_t m = (x & 0x7FFFFFu) | 0x800000u;
    int neg = (x & SIGN_BIT) != 0;
    if (is_nan(x)) return (int32_t)0x80000000;
    if (e < 0) return 0;
    if (e >= 31) return neg ? (int32_t)0x80000000 : 0x7FFFFFFF;
    {
        uint32_t v = e >= 23 ? m << (e - 23) : m >> (23 - e);
        return neg ? -(int32_t)v : (int32_t)v;
    }
}

nd_f32 nd_f32_add(nd_f32 a, nd_f32 b)
{
    int32_t ea, eb, d;
    uint32_t ma, mb, sa = a & SIGN_BIT, sb = b & SIGN_BIT;
    uint64_t Ma, Mb, R;
    if (is_nan(a) || is_nan(b)) return QNAN;
    if (is_inf(a)) return (is_inf(b) && sa != sb) ? QNAN : a;
    if (is_inf(b)) return b;
    if (is_zero(a) && is_zero(b)) return (sa && sb) ? SIGN_BIT : 0u;
    if (is_zero(a)) return b;
    if (is_zero(b)) return a;
    unpack(a, &ea, &ma); unpack(b, &eb, &mb);
    if (ea < eb || (ea == eb && ma < mb)) {        /* make |a| >= |b| */
        uint32_t t; int32_t te;
        t = ma; ma = mb; mb = t; te = ea; ea = eb; eb = te; t = sa; sa = sb; sb = t;
    }
    d = ea - eb;
    Ma = (uint64_t)ma << 3; Mb = (uint64_t)mb << 3;       /* guard, round, sticky positions */
    if (d > 0) {                                           /* right shift with "jamming": lost bits OR into bit 0 */
        if (d > 40) Mb = (Mb != 0);
        else Mb = (Mb >> d) | ((Mb & (((uint64_t)1 << d) - 1u)) != 0);
    }
    if (sa == sb) R = Ma + Mb;
    else {
        R = Ma - Mb;
        if (R == 0) return 0u;                             /* x - x = +0 in round-to-nearest */
    }
    return round_pack(sa, ea, R, 3, 0);
}

nd_f32 nd_f32_sub(nd_f32 a, nd_f32 b) { return nd_f32_add(a, b ^ SIGN_BIT); }

nd_f32 nd_f32_mul(nd_f32 a, nd_f32 b)
{
    int32_t ea, eb;
    uint32_t ma, mb, s = (a ^ b) & SIGN_BIT;
    uint64_t p;
    if (is_nan(a) || is_nan(b)) return QNAN;
    if (is_inf(a) || is_inf(b)) return (is_zero(a) || is_zero(b)) ? QNAN : (s | INF_BITS);
    if (is_zero(a) || is_zero(b)) return s;
    unpack(a, &ea, &ma); unpack(b, &eb, &mb);
    while (ma < 0x800000u) { ma <<= 1; --ea; }
    while (mb < 0x800000u) { mb <<= 1; --eb; }
    p = (uint64_t)ma * mb;                                  /* 47..48 bits, value = p * 2^-46 * 2^(ea+eb-254) */
    return round_pack(s, ea + eb - 127, p, 23, 0);
}

nd_f32 nd_f32_div(nd_f32 a, nd_f32 b)
{
    int32_t ea, eb;
    uint32_t ma, mb, s = (a ^ b) & SIGN_BIT;
    uint64_t num, q, r;
    if (is_nan(a) || is_nan(b)) return QNAN;
    if (is_inf(a)) return is_inf(b) ? QNAN : (s | INF_BITS);
    if (is_inf(b)) return s;
    if (is_zero(b)) return is_zero(a) ? QNAN : (s | INF_BITS);
    if (is_zero(a)) return s;
    unpack(a, &ea, &ma); unpack(b, &eb, &mb);
    while (ma < 0x800000u) { ma <<= 1; --ea; }
    while (mb < 0x800000u) { mb <<= 1; --eb; }
    num = (uint64_t)ma << 26;                               /* quotient has 26..27 significant bits */
    q = num / mb; r = num % mb;
    /* q has 2 or 3 guard bits below the 24-bit significand; fold the remainder into a sticky bit */
    return round_pack(s, ea - eb + 127, q, 3, r != 0u);
}

static int ordered_key(nd_f32 x, int64_t *k)
{
    if (is_nan(x)) return 0;
    *k = (x & SIGN_BIT) ? -(int64_t)(x & 0x7FFFFFFFu) : (int64_t)x;
    return 1;
}
int nd_f32_lt(nd_f32 a, nd_f32 b) { int64_t x, y; return ordered_key(a, &x) && ordered_key(b, &y) && x < y; }
int nd_f32_gt(nd_f32 a, nd_f32 b) { return nd_f32_lt(b, a); }

nd_f32 nd_f32_fmac(nd_f32 a, nd_f32 b, nd_f32 c) { return nd_f32_add(c, nd_f32_mul(a, b)); }

nd_f32 nd_f32_abs(nd_f32 x) { return x & 0x7FFFFFFFu; }
nd_f32 nd_f32_neg(nd_f32 x) { return x ^ SIGN_BIT; }

/* floor(sqrt(n)) by the restoring bit method */
static uint64_t isqrt64(uint64_t n)
{
    uint64_t r = 0, bit = (uint64_t)1 << 62;
    while (bit > n) bit >>= 2;
    while (bit) {
        if (n >= r + bit) { n -= r + bit; r = (r >> 1) + bit; }
        else r >>= 1;
        bit >>= 2;
    }
    return r;
}

nd_f32 nd_f32_sqrt(nd_f32 x)
{
    int32_t e;
    uint32_t m;
    uint64_t n, r;
    if (is_nan(x)) return QNAN;
    if (is_zero(x)) return x;                               /* sqrt(+-0) = +-0 */
    if (x & SIGN_BIT) return QNAN;
    if (is_inf(x)) return x;
    unpack(x, &e, &m);                                      /* value = m * 2^(e-150) */
    while (m < 0x800000u) { m <<= 1; --e; }                 /* denormal: normalise so r has enough bits */
    if ((e - 150) & 1) { m <<= 1; --e; }                    /* make the binary exponent even */
    n = (uint64_t)m << 28;                                  /* sqrt(n) = sqrt(m) * 2^14: 26..27 significant bits */
    r = isqrt64(n);
    /* value = r * 2^(E/2 - 14) with E = e - 150 now even; round_pack takes e' with
     * value = m' * 2^(e' - 127 - 23 - extra), extra = 3, so e' = E/2 + 139 */
    return round_pack(0, (e - 150) / 2 + 139, r, 3, r * r != n);
}
