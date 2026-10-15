/* autodiff.h: contract between tools/dc/autodiff.py and your WRAPPER file (game-independent).
 *
 * You write ONE function, ad_wrapper(), that calls your C port the way the retail SH-4 function was called:
 *   - c->r[4..7] and c->fr[4..11] hold the retail integer / float(bit pattern) arguments of this case;
 *   - ad_mem(addr) returns a host pointer to the retail address `addr`, inside a region declared in the spec
 *     (pass these pointers to your port instead of the real addresses; use ad_mem(addr)+offset freely);
 *   - every call the retail function makes to a stubbed callee must be reported with ad_call(), in the same
 *     order and with the same argument values (this is what catches dropped / wrong / reordered arguments);
 *   - set c->ret to what the retail function leaves in r0 (void functions: leave it 0 and set "check_ret": false).
 */
#ifndef AUTODIFF_H
#define AUTODIFF_H
#include <stdint.h>
#include <stddef.h>   /* NULL, size_t: wrappers and ports kept failing to compile without it */

typedef struct {
    uint32_t r[16];     /* r0..r15 at entry; only r4..r7 are meaningful arguments */
    uint32_t fr[16];    /* fr0..fr15 raw IEEE-754 bit patterns; fr4..fr11 are float arguments */
    uint32_t ret;       /* you set: value of r0 on return */
} ad_regs;

uint8_t *ad_mem(uint32_t addr);   /* abort()s if addr is outside every declared region */
uint32_t ad_rd32(uint32_t addr);  /* little-endian read of the declared-region image, same as the CPU would see */
/* Report a call to a stubbed callee. ints = r4.. (ni values), fl = fr4.. (nf bit patterns). Returns the
 * scripted r0 of that call (from the spec's "ret" list for that callee; 0 when none). */
uint32_t ad_call(uint32_t callee, const uint32_t *ints, int ni, const uint32_t *fl, int nf);

void ad_wrapper(ad_regs *c);      /* YOU implement this */

/* Retail memory accessors (little-endian, abort outside the declared regions). Width/sign follow the SH-4 loads:
 *   mov.b = ad_rd8s (signed)   extu.b = ad_rd8   mov.w = ad_rd16s (signed)   extu.w = ad_rd16   mov.l = ad_rd32 */
static inline uint8_t  ad_rd8(uint32_t a)   { return *ad_mem(a); }
static inline int8_t   ad_rd8s(uint32_t a)  { return (int8_t)*ad_mem(a); }
static inline uint16_t ad_rd16(uint32_t a)  { uint8_t *p = ad_mem(a); return (uint16_t)(p[0] | (p[1] << 8)); }
static inline int16_t  ad_rd16s(uint32_t a) { return (int16_t)ad_rd16(a); }
void ad_wlog(uint32_t a, int size, uint32_t v);   /* appends one store to the write trace (compared with the retail store sequence when the spec has "write_trace") */
static inline void ad_wr8(uint32_t a, uint32_t v)  { ad_wlog(a, 1, v); *ad_mem(a) = (uint8_t)v; }
static inline void ad_wr16(uint32_t a, uint32_t v) { ad_wlog(a, 2, v); uint8_t *p = ad_mem(a); p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static inline void ad_wr32(uint32_t a, uint32_t v) { ad_wlog(a, 4, v); uint8_t *p = ad_mem(a); p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }
#define AD_STACK_TOP 0x8cffff00u   /* r15 at entry (the emulator and the port driver agree); stack argument i (5th, 6th ... argument) is at AD_STACK_TOP + 4*i */
#endif
