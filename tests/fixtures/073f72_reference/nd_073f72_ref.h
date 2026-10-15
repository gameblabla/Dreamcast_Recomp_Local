#ifndef ND_073F72_REF_H
#define ND_073F72_REF_H
#include <stdint.h>
struct nd_073f72_host {
    void *ctx;
    void (*tail)(void *ctx, uint32_t r4, uint32_t r5, uint32_t r6, uint32_t r7, uint32_t f4, uint32_t f5, uint32_t f6);
};
void nd_073f72_ref(const struct nd_073f72_host *h, const uint8_t *tab, const uint8_t *tab2, uint32_t tab2_addr,
                   int32_t a, int32_t b, int32_t flag, uint32_t r7);
#endif
