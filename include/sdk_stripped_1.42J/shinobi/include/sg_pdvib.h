#ifndef _SG_PDVIB_H_
#define _SG_PDVIB_H_
#ifdef __cplusplus
extern "" {
#endif
#include <sg_xpt.h>
#define PDD_VIBERR_OK           0
#define PDD_VIBERR_BUSY        (-1)
#define PDD_VIBERR_NO_VIBRATOR (-2)
#define PDD_VIBERR_INVALID     (-3)
#define PDD_VIB_DIRECTION_NORMAL   0
#define PDD_VIB_DIRECTION_FLIP     1
#define PDD_VIB_DIRECTION_LEFT     2
#define PDD_VIB_DIRECTION_RIGHT    3
#define PDD_VIB_FLAG_CONTINUOUS  (1 << 0)
#define PDD_VIB_FLAG_EXHALATION  (1 << 3)
#define PDD_VIB_FLAG_CONVERGENCE (1 << 7)
#define PDD_VIB_POS_FRONT 0
#define PDD_VIB_POS_BACK  1
#define PDD_VIB_POS_LEFT  2
#define PDD_VIB_POS_RIGHT 3
#define PDD_VIB_AXIS_NONE 0
#define PDD_VIB_AXIS_X    1
#define PDD_VIB_AXIS_Y    2
#define PDD_VIB_AXIS_Z    3
#define PDD_VIBRET_OK     0
typedef struct {
	Uint8 unit;
	Uint8 flag;
	Sint8 power;
	Uint8 freq;
	Uint8 inc;
	Uint8 reserved[3];
} PDS_VIBPARAM;
typedef struct {
	Uint8 units;
	Uint8 se_units;
} PDS_VIBINFO;
typedef struct {
	Uint8 position;
	Uint8 axis;
	Uint8 pow_enable;
	Uint8 cont_enable;
	Uint8 dir_enable;
	Uint8 wave_enable;
	Uint8 min_freq;
	Uint8 max_freq;
} PDS_VIBUNITINFO;
typedef Sint32 (*PD_VIBCALLBACK)(Sint32 stat, Uint32 param);
typedef Sint32 (*PD_VIBENUMUNITCALLBACK)(Uint32 unit, Sint32 stat,
									PDS_VIBUNITINFO* info, Uint32 param);
Sint32 pdVibMxIsReady(Uint32 port);
Sint32 pdVibMxSetStopTime(Uint32 port, Uint32 time);
Sint32 pdVibMxStart(Uint32 port, const PDS_VIBPARAM* param);
Sint32 pdVibMxStop(Uint32 port);
Sint32 pdVibIsReady(Uint32 port);
Sint32 pdVibGetDirection(Uint32 port);
Sint32 pdVibSetStopTime(Uint32 port, Uint8* unit, Uint8* time, Uint32 num);
Sint32 pdVibStart(Uint32 port, const PDS_VIBPARAM* param, Uint32 numunits);
Sint32 pdVibSetWave(Uint32 port, Uint32 unit, const void* wave, Uint32 num);
Sint32 pdVibGetInfo(Uint32 port, PDS_VIBINFO* info);
Sint32 pdVibEnumerateUnit(Uint32 port, PD_VIBENUMUNITCALLBACK func,
																Uint32 param);
#ifdef __cplusplus
}
#endif
#endif
