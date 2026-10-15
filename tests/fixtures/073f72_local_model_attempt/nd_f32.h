#ifndef ND_F32_H
#define ND_F32_H
/* Bit-exact software IEEE-754 binary32 arithmetic, integer code only (no FPU needed, e.g. Saturn SH-2).
 *
 * The retail Dreamcast code computes parts of its rules (damage, RAND, rand_range) with SH-4 single precision
 * (FPSCR = round-to-nearest-even, no denormal flushing needed for the values involved). To stay bit-exact
 * without a floating point unit the portable core performs those expressions with these routines.
 * Values are carried as raw uint32_t bit patterns ("nd_f32"). Operations round to nearest, ties to even.
 * Inf/NaN are handled conservatively (propagated), the game never produces them.
 */
#include "nd_int.h"

typedef uint32_t nd_f32;

#define ND_F32_ZERO 0x00000000u
#define ND_F32_ONE  0x3F800000u

nd_f32  nd_f32_from_i32(int32_t v);              /* (float)v  */
int32_t nd_f32_trunc(nd_f32 x);                  /* (int)x, toward zero, saturating like SH-4 FTRC */
nd_f32  nd_f32_add(nd_f32 a, nd_f32 b);
nd_f32  nd_f32_sub(nd_f32 a, nd_f32 b);
nd_f32  nd_f32_mul(nd_f32 a, nd_f32 b);
nd_f32  nd_f32_div(nd_f32 a, nd_f32 b);
int     nd_f32_lt(nd_f32 a, nd_f32 b);           /* a < b (false if either is NaN) */
int     nd_f32_gt(nd_f32 a, nd_f32 b);
nd_f32  nd_f32_abs(nd_f32 x);                    /* FABS: clears the sign bit (exact) */
nd_f32  nd_f32_neg(nd_f32 x);                    /* FNEG: flips the sign bit (exact) */
nd_f32  nd_f32_sqrt(nd_f32 x);                   /* FSQRT: correctly rounded; sqrt(-x) for x < 0 yields QNAN */
nd_f32  nd_f32_fmac(nd_f32 a, nd_f32 b, nd_f32 c); /* FMAC FR0,FRm,FRn: c + a*b, product and sum each rounded (not fused; CONFIRMED by nd_randavg differential) */
#endif
