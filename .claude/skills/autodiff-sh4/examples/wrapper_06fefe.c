/* Example wrapper: retail FUN_8c06fefe(r4=index, r5=byte) -> core nd_06fefe(buf, count, idx, val).
 * The port takes plain pointers/values; the wrapper turns retail addresses + registers into them. */
#include "autodiff.h"
#include "nd_06fefe.h"

void ad_wrapper(ad_regs *c)
{
    int32_t count = (int32_t)ad_rd32(0x8c0f0c2c);               /* a word the retail code loads: read it from the region */
    c->ret = (uint32_t)nd_06fefe(ad_mem(0x8c23e962), count,      /* table base address from the literal pool */
                                 (int32_t)c->r[4], (uint8_t)c->r[5]);
}
