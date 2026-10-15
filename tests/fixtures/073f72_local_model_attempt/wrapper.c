#include "autodiff.h"
#include "nd_073f72.h"

static void cb_fsave(void *ctx, int32_t index, uint32_t f4, uint32_t f5, uint32_t f6)
{
    uint32_t ints[1] = {(uint32_t)index};
    uint32_t floats[3] = {f4, f5, f6};
    ad_call(0x8c070498, ints, 1, floats, 3);
}

static uint8_t cb_lookup(void *ctx, int16_t index)
{
    uint8_t *base = ad_mem(0x8c0e8538);
    uint32_t off = (uint32_t)index * 0x68u + 9;
    if (off >= 65536) {
        return 0;
    }
    return base[off];
}

void ad_wrapper(ad_regs *c)
{
    struct nd_073f72_host h;
    h.ctx = 0;
    h.fsave = cb_fsave;
    h.lookup = cb_lookup;

    uint8_t *table = ad_mem(0x8c23e914);

    nd_073f72(&h, table, (int32_t)c->r[4], (int32_t)c->r[5], (int32_t)c->r[6]);
}
