#ifndef _SG_SYTMU_H_
#define _SG_SYTMU_H_
#ifdef __cplusplus
extern "" {
#endif
#define SYD_TMR_CLOCK_P4        (0)
#define SYD_TMR_CLOCK_P16       (1)
#define SYD_TMR_CLOCK_P64       (2)
#define SYD_TMR_CLOCK_P256      (3)
#define SYD_TMR_CLOCK_P1024     (4)
typedef Uint16 SY_TMR_CLOCK;
void syTmrInit(void);
Uint32 syTmrGetCount(void);
Uint32 syTmrDiffCount(Uint32, Uint32);
Uint32 syTmrCountToMicro(Uint32);
Uint32 syTmrMicroToCount(Uint32);
void syTmrGenStart(void);
void syTmrGenStop(void);
void syTmrGenSetInt(void(*)(void *), void *);
void syTmrGenCancelInt(void);
void syTmrGenSetClock(SY_TMR_CLOCK);
void syTmrGenSetCount(Uint32);
Uint32 syTmrGenGetCount(void);
Uint32 syTmrGenMicroToCount(Uint32, SY_TMR_CLOCK);
Uint32 syTmrGenCountToMicro(Uint32, SY_TMR_CLOCK);
Uint32 syTmrGenDiffCount(Uint32, Uint32);
#ifdef __cplusplus
	   }
#endif
#endif
