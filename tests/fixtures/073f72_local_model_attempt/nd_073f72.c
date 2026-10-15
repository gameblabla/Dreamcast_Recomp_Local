#include "nd_073f72.h"
#include "nd_f32.h"

#define ND_STRIDE 1584

static uint32_t rd32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int16_t rd16(const uint8_t *p)
{
    return (int16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

void nd_073f72(struct nd_073f72_host *h, uint8_t *table, int32_t index_a, int32_t index_b, int32_t flag)
{
    uint8_t *entry_a;
    uint8_t *entry_b;
    uint32_t delta;
    uint32_t f4, f5, f6;

    if (index_a == index_b || index_a < 0 || index_b < 0) {
        return;
    }

    delta = ND_F32_ZERO;

    if (flag == 1) {
        entry_a = table + (uint32_t)index_a * ND_STRIDE;
        entry_b = table + (uint32_t)index_b * ND_STRIDE;
        int16_t val_a = rd16(entry_a + 0x4c);
        int16_t val_b = rd16(entry_b + 0x4c);
        uint8_t byte_a = h->lookup(h->ctx, val_a);
        uint8_t byte_b = h->lookup(h->ctx, val_b);

        if (byte_a != byte_b) {
            delta = 0x47000000u;
        }
    }

    entry_b = table + (uint32_t)index_b * ND_STRIDE;
    f4 = rd32(entry_b + 12);
    f5 = rd32(entry_b + 16);
    f6 = rd32(entry_b + 20);

    f5 = nd_f32_add(f5, delta);

    h->fsave(h->ctx, index_a, f4, f5, f6);
}
