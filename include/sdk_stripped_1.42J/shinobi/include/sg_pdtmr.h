#ifndef _SG_PDTMR_H_
#define _SG_PDTMR_H_
#ifdef __cplusplus
extern "" {
#endif
#include <sg_xpt.h>
#define PDD_TMRERR_OK          0
#define PDD_TMRERR_BUSY       (-1)
#define PDD_TMRERR_NO_TIMER   (-2)
#define PDD_TMRERR_INVALID    (-3)
typedef struct {
	Uint16 year;
	Uint8 month;
	Uint8 day;
	Uint8 hour;
	Uint8 minute;
	Uint8 second;
	Uint8 dayofweek;
} PDS_TIME;
typedef (*PD_TIMERCALLBACK)(Sint32 stat, Uint32 param);
Sint32 pdTmrIsReady(Uint32 port);
Sint32 pdTmrSetTime(Uint32 port, const PDS_TIME* time,
							PD_TIMERCALLBACK func, Uint32 param);
Sint32 pdTmrGetTime(Uint32 port, PDS_TIME*,
							PD_TIMERCALLBACK func, Uint32 param);
Sint32 pdTmrAlarm(Uint32 port, Uint8* data);
#ifdef __cplusplus
}
#endif
#endif
