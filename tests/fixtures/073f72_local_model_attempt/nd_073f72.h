#ifndef ND_073F72_H
#define ND_073F72_H
#include <stdint.h>

/* Retail FUN_8c073f72 (asm 8c073f72..8c073ffe, 142 B, callers 13, class rules).
 *
 * CONFIRMED (asm): params r4=index_a, r5=index_b, r6=flag.
 * CONFIRMED (asm): if index_a==index_b or index_a<0 or index_b<0: return (no store).
 * CONFIRMED (asm): if flag==1: delta=0.0f; read s16 at table+index_a*1584+0x4c and
 *   table+index_b*1584+0x4c; use each as index into lookup table at 0x8c0e8538
 *   (entry stride 0x68, byte at offset 9); if bytes differ, delta=0x47000000.
 * CONFIRMED (asm): read three floats at table+index_b*1584+12, +16, +20.
 * CONFIRMED (asm): f5 += delta; call FUN_8c070498(index_a, f4, f5, f6).
 * HYPOTHESIS: purpose is to copy a position/orientation from index_b to index_a,
 *   with an optional offset when flag==1 and the two entities are in different states.
 */

struct nd_073f72_host {
    void *ctx;
    void (*fsave)(void *ctx, int32_t index, uint32_t f4, uint32_t f5, uint32_t f6);
    uint8_t (*lookup)(void *ctx, int16_t index);
};

void nd_073f72(struct nd_073f72_host *h, uint8_t *table, int32_t index_a, int32_t index_b, int32_t flag);

#endif
