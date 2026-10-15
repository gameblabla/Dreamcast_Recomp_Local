#ifndef _SG_SQ_H_
#define _SG_SQ_H_
#define  SYD_SQNUM_0  1
#define  SYD_SQNUM_1  2
#define  SYD_SQNUM_01 3
typedef Sint8 SY_SQNUM;
Void sySqInit(Void);
Void sySqFinish(Void);
#define sySqOpen(sqNum) \
  set_imask(15)
#define sySqClose(sqNum) \
  set_imask(0)
Void *sySqStart(Uint32 *size, Void *dstArray);
#endif
