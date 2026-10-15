/* Reference port of a table-pair compare with a tail call (judge for tools/ tests; written from the asm, not from any earlier port). */
#include "nd_073f72_ref.h"
#include "nd_f32.h"

static uint32_t rd32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }
static int16_t rd16(const uint8_t *p) { return (int16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8)); }

void nd_073f72_ref(const struct nd_073f72_host *h, const uint8_t *tab, const uint8_t *tab2, uint32_t tab2_addr,
                   int32_t a, int32_t b, int32_t flag, uint32_t r7)
{
    uint32_t delta = 0;          /* 0.0f */
    uint32_t r5 = (uint32_t)b;   /* the caller's r5 unless the flag path overwrites it */
    const uint8_t *eb;

    if (a == b || a < 0 || b < 0)
        return;
    if (flag == 1) {
        int16_t va = rd16(tab + (uint32_t)a * 1584u + 0x4c);
        int8_t xa = (int8_t)tab2[(uint32_t)((int32_t)va * 0x68) + 9];
        int16_t vb = rd16(tab + (uint32_t)b * 1584u + 0x4c);
        int8_t xb = (int8_t)tab2[(uint32_t)((int32_t)vb * 0x68) + 9];
        if (xa != xb)
            delta = 0x47000000u;
        r5 = tab2_addr;
    }
    eb = tab + (uint32_t)b * 1584u;
    h->tail(h->ctx, (uint32_t)a, r5, (uint32_t)flag, r7, rd32(eb + 0xc), nd_f32_add(rd32(eb + 0x10), delta), rd32(eb + 0x14));
}
