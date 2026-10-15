#include "autodiff.h"
#include "nd_073f72_ref.h"

static void tail(void *ctx, uint32_t r4, uint32_t r5, uint32_t r6, uint32_t r7, uint32_t f4, uint32_t f5, uint32_t f6)
{
    uint32_t ints[4] = {r4, r5, r6, r7};
    uint32_t fl[3] = {f4, f5, f6};
    (void)ctx;
    ad_call(0x8c070498, ints, 1, fl, 3);   /* the tail callee reads only r4 and fr4-fr6 (its own asm); r5-r7 pass through unread */
}

void ad_wrapper(ad_regs *c)
{
    struct nd_073f72_host h = {0, tail};
    nd_073f72_ref(&h, ad_mem(0x8c23e914), ad_mem(0x8c0e8538), 0x8c0e8538u, (int32_t)c->r[4], (int32_t)c->r[5], (int32_t)c->r[6], c->r[7]);
}
