#ifndef _SJ_H_INCLUDED
#define _SJ_H_INCLUDED
#define	SJ_VER	""
#ifdef _MSC_VER
#pragma comment(lib, "")
#endif
#define	SJ_LIN_FREE	(0)
#define	SJ_LIN_DATA	(1)
#define SJ_ERR_FATAL		(-1)
#define SJ_ERR_INTERNAL		(-2)
#define SJ_ERR_PRM			(-3)
#define SJ_VOID_PTR(adr)	((void *)(adr))
#define SJ_OFF_LSB(val, n)	((((unsigned long)(val)) >> (n)) << (n))
#define SJ_OFF_LSB1(val)	((((unsigned long)(val)) >> (1)) << (1))
#define SJ_OFF_LSB2(val)	((((unsigned long)(val)) >> (2)) << (2))
#define SJ_OFF_LSB3(val)	(((unsigned long)(val)) & (0xfffffff8))
#define SJ_OFF_LSB4(val)	(((unsigned long)(val)) & (0xfffffff0))
#define SJ_OFF_LSB5(val)	(((unsigned long)(val)) & (0xffffffe0))
#define SJ_OFF_LSB6(val)	(((unsigned long)(val)) & (0xffffffc0))
#define SJ_OFF_LSB7(val)	(((unsigned long)(val)) & (0xffffff80))
#define SJ_OFF_LSB8(val)	((((unsigned long)(val)) >> (8)) << (8))
#define SJ_OFF_LSB16(val)	((((unsigned long)(val)) >> (16)) << (16))
#define SJ_BACK_BND2(ptr)	SJ_VOID_PTR(SJ_OFF_LSB1(ptr))
#define SJ_BACK_BND4(ptr)	SJ_VOID_PTR(SJ_OFF_LSB2(ptr))
#define SJ_BACK_BND8(ptr)	SJ_VOID_PTR(SJ_OFF_LSB3(ptr))
#define SJ_BACK_BND16(ptr)	SJ_VOID_PTR(SJ_OFF_LSB4(ptr))
#define SJ_BACK_BND32(ptr)	SJ_VOID_PTR(SJ_OFF_LSB5(ptr))
#define SJ_FORE_BND2(ptr)	SJ_BACK_BND2( ((unsigned long)(ptr)) +  1)
#define SJ_FORE_BND4(ptr)	SJ_BACK_BND4( ((unsigned long)(ptr)) +  3)
#define SJ_FORE_BND8(ptr)	SJ_BACK_BND8( ((unsigned long)(ptr)) +  7)
#define SJ_FORE_BND16(ptr)	SJ_BACK_BND16(((unsigned long)(ptr)) + 15)
#define SJ_FORE_BND32(ptr)	SJ_BACK_BND32(((unsigned long)(ptr)) + 31)
#define SJ_SIZ_BND32(siz)	((siz) + 32)
#define	SJ_ADR_BND32(adr)	SJ_FORE_BND32(adr)
#define SJ_GET_ENDPOS(bgn, num)		((bgn) + (num) - 1)
#define SJ_INNER_NUM(bgn, end)		((end) - (bgn) + 1)
#define SJ_IS_INNER(x, bgn, end) ( ((x) >= (bgn)) && ((x) <= (end)) )
#ifndef UUID_DEFINED
#define UUID_DEFINED
typedef struct _UUID {
    unsigned long Data1;
    unsigned short Data2;
    unsigned short Data3;
    unsigned char Data4[8];
} UUID;
#define uuid_t UUID
#endif
#ifndef SJCK_DEFINED
#define SJCK_DEFINED
typedef struct {
	char *data;
	long len;
} SJCK;
#endif
typedef struct {
	struct _sj_vtbl *vtbl;
} SJ_OBJ;
#ifndef SJ_DEFINED
#define SJ_DEFINED
typedef SJ_OBJ *SJ;
#endif
typedef struct _sj_vtbl {
	void (*QueryInterface)();
	void (*AddRef)();
	void (*Release)();
	void (*Destroy)(SJ sj);
	UUID *(*GetUuid)(SJ sj);
	void (*Reset)(SJ sj);
	void (*GetChunk)(SJ sj, long id, long nbyte, SJCK *ck);
	void (*UngetChunk)(SJ sj, long id, SJCK *ck);
	void (*PutChunk)(SJ sj, long id, SJCK *ck);
	long (*GetNumData)(SJ sj, long id);
	long (*IsGetChunk)(SJ sj, long id, long nbyte, long *rbyte);
	void (*EntryErrFunc)(SJ sj,
					void (*func)(void *obj, long ecode), void *obj);
} SJ_IF;
typedef SJ_IF *SJIF;
#define SJ_Destroy(sj) \
		(*(sj)->vtbl->Destroy)(sj)
#define SJ_GetUuid(sj) \
		(*(sj)->vtbl->GetUuid)(sj)
#define SJ_Reset(sj) \
		(*(sj)->vtbl->Reset)(sj)
#define SJ_GetChunk(sj, id, nbyte, ck) \
		(*(sj)->vtbl->GetChunk)(sj, id, nbyte, ck)
#define SJ_UngetChunk(sj, id, ck) \
		(*(sj)->vtbl->UngetChunk)(sj, id, ck)
#define SJ_PutChunk(sj, id, ck) \
		(*(sj)->vtbl->PutChunk)(sj, id, ck)
#define SJ_GetNumData(sj, id) \
		(*(sj)->vtbl->GetNumData)(sj, id)
#define SJ_IsGetChunk(sj, id, nbyte, rbyte) \
			(*(sj)->vtbl->IsGetChunk)(sj, id, nbyte, rbyte)
#define SJ_EntryErrFunc(sj, id, f, o) \
		(*(sj)->vtbl->EntryErrFunc)(sj, id, f, o)
#ifdef		__cplusplus
extern	"" {
#endif
void SJ_SplitChunk(SJCK *ck, long nbyte, SJCK *ck1, SJCK *ck2);
void SJRBF_Init(void);
void SJRBF_Finish(void);
SJ SJRBF_Create(char *buf, long bsize, long xsize);
void SJMEM_Init(void);
SJ SJMEM_Create(char *data, long bsize);
#define	SJUNI_MODE_SEPA			(0)
#define	SJUNI_MODE_JOIN			(1)
#define	SJUNI_CALC_WORK(nck)	((nck)*16)
SJ SJUNI_Create(long mode, char *work, long wksize);
long SJUNI_GetNumChunk(SJ sj, long id);
long SJUNI_GetNumChainPool(SJ sj);
#if 0
void SJUNI_EntryGetFunc(SJ sj, long id, void (*f)(void *o, SJCK *ck), void *o);
void SJUNI_EntryPutFunc(SJ sj, long id, void (*f)(void *o, SJCK *ck), void *o);
void SJUNI_EntryUngetFunc(SJ sj, long id, void (*f)(void *o, SJCK *ck), void *o);
#endif
#ifdef		__cplusplus
}
#endif
#endif

