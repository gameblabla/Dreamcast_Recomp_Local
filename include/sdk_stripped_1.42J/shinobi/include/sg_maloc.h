#ifndef _SG_MALOC_H_
#define _SG_MALOC_H_
#ifdef __cplusplus
extern "" {
#endif
Void syMallocInit(Void *heap, Uint32 size);
Void syMallocFinish(Void);
#define syMalloc(__nbytes__) malloc(__nbytes__)
#define syFree(__ap__) free(__ap__)
Void syMallocStat(Uint32 *wholeFreeSize, Uint32 *biggestFreeBlockSize);
#ifdef __cplusplus
	   }
#endif
#endif
