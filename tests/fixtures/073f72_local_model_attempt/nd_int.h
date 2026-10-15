#ifndef ND_INT_H
#define ND_INT_H
/* Nadesico portable core: fixed-width integer types only.
 *
 * Everything under core/ is the platform-independent game core shared by the PC and
 * Saturn ports. HARD RULES (enforced by tools/check_core_no_float.sh in `make check`):
 *   - no float / double / long double, no <math.h>, no floating literals
 *   - no heap allocation, no stdio/file I/O, no globals mutated behind the caller's back
 *   - C99, 32-bit-int safe (every intermediate fits int32_t; 64-bit is never required)
 * Platform backends (PC SDL3 renderer, Saturn VDP1/VDP2, audio, file access) implement the
 * NdHost callbacks declared in nd_vm.h and may use floating point internally.
 */
#include <stdint.h>
#include <stddef.h>

#define ND_ARRAY_LEN(a) (sizeof(a) / sizeof((a)[0]))
#define ND_STATIC_ASSERT(name, cond) typedef char nd_assert_##name[(cond) ? 1 : -1]

/* Sign-extend a 16-bit script word without implementation-defined conversions. */
static inline int32_t nd_s16(uint16_t v) { return (v & 0x8000u) ? (int32_t)v - 65536 : (int32_t)v; }
static inline uint16_t nd_u16(int32_t v) { return (uint16_t)((uint32_t)v & 0xFFFFu); }

/* Little-endian field access (the retail data is SH-4 little endian). */
static inline uint16_t nd_rd16(const uint8_t *p) { return (uint16_t)(p[0] | ((unsigned)p[1] << 8)); }
static inline uint32_t nd_rd32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

ND_STATIC_ASSERT(int_is_at_least_32, sizeof(int) >= 4);
#endif
