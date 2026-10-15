#ifndef _NINJAPAD_H_
#define _NINJAPAD_H_
#ifdef __cplusplus
extern "" {
#endif
#include <sg_pad.h>
#define NJD_PORT_A0   PDD_PORT_A0
#define NJD_PORT_A1   PDD_PORT_A1
#define NJD_PORT_A2   PDD_PORT_A2
#define NJD_PORT_A3   PDD_PORT_A3
#define NJD_PORT_A4   PDD_PORT_A4
#define NJD_PORT_A5   PDD_PORT_A5
#define NJD_PORT_B0   PDD_PORT_B0
#define NJD_PORT_B1   PDD_PORT_B1
#define NJD_PORT_B2   PDD_PORT_B2
#define NJD_PORT_B3   PDD_PORT_B3
#define NJD_PORT_B4   PDD_PORT_B4
#define NJD_PORT_B5   PDD_PORT_B5
#define NJD_PORT_C0   PDD_PORT_C0
#define NJD_PORT_C1   PDD_PORT_C1
#define NJD_PORT_C2   PDD_PORT_C2
#define NJD_PORT_C3   PDD_PORT_C3
#define NJD_PORT_C4   PDD_PORT_C4
#define NJD_PORT_C5   PDD_PORT_C5
#define NJD_PORT_D0   PDD_PORT_D0
#define NJD_PORT_D1   PDD_PORT_D1
#define NJD_PORT_D2   PDD_PORT_D2
#define NJD_PORT_D3   PDD_PORT_D3
#define NJD_PORT_D4   PDD_PORT_D4
#define NJD_PORT_D5   PDD_PORT_D5
#define NJD_DEV_SUPPORT_AY2 PDD_DEV_SUPPORT_AY2
#define NJD_DEV_SUPPORT_AX2 PDD_DEV_SUPPORT_AX2
#define NJD_DEV_SUPPORT_AY1 PDD_DEV_SUPPORT_AY1
#define NJD_DEV_SUPPORT_AX1 PDD_DEV_SUPPORT_AX1
#define NJD_DEV_SUPPORT_AL  PDD_DEV_SUPPORT_AL
#define NJD_DEV_SUPPORT_AR  PDD_DEV_SUPPORT_AR
#define NJD_DEV_SUPPORT_KRB PDD_DEV_SUPPORT_KRB
#define NJD_DEV_SUPPORT_KLB PDD_DEV_SUPPORT_KLB
#define NJD_DEV_SUPPORT_KDB PDD_DEV_SUPPORT_KDB
#define NJD_DEV_SUPPORT_KUB PDD_DEV_SUPPORT_KUB
#define NJD_DEV_SUPPORT_TD  PDD_DEV_SUPPORT_TD
#define NJD_DEV_SUPPORT_TX  PDD_DEV_SUPPORT_TX
#define NJD_DEV_SUPPORT_TY  PDD_DEV_SUPPORT_TY
#define NJD_DEV_SUPPORT_TZ  PDD_DEV_SUPPORT_TZ
#define NJD_DEV_SUPPORT_KR  PDD_DEV_SUPPORT_KR
#define NJD_DEV_SUPPORT_KL  PDD_DEV_SUPPORT_KL
#define NJD_DEV_SUPPORT_KD  PDD_DEV_SUPPORT_KD
#define NJD_DEV_SUPPORT_KU  PDD_DEV_SUPPORT_KU
#define NJD_DEV_SUPPORT_ST  PDD_DEV_SUPPORT_ST
#define NJD_DEV_SUPPORT_TA  PDD_DEV_SUPPORT_TA
#define NJD_DEV_SUPPORT_TB  PDD_DEV_SUPPORT_TB
#define NJD_DEV_SUPPORT_TC  PDD_DEV_SUPPORT_TC
#define NJD_DGT_TL    PDD_DGT_TL
#define NJD_DGT_TR    PDD_DGT_TR
#define NJD_DGT_KRB   PDD_DGT_KRB
#define NJD_DGT_KLB   PDD_DGT_KLB
#define NJD_DGT_KDB   PDD_DGT_KDB
#define NJD_DGT_KUB   PDD_DGT_KUB
#define NJD_DGT_TD    PDD_DGT_TD
#define NJD_DGT_TX    PDD_DGT_TX
#define NJD_DGT_TY    PDD_DGT_TY
#define NJD_DGT_TZ    PDD_DGT_TZ
#define NJD_DGT_KR    PDD_DGT_KR
#define NJD_DGT_KL    PDD_DGT_KL
#define NJD_DGT_KD    PDD_DGT_KD
#define NJD_DGT_KU    PDD_DGT_KU
#define NJD_DGT_ST    PDD_DGT_ST
#define NJD_DGT_TA    PDD_DGT_TA
#define NJD_DGT_TB    PDD_DGT_TB
#define NJD_DGT_TC    PDD_DGT_TC
typedef PDS_PERIPHERAL NJS_PERIPHERAL;
#if 0
typedef struct {
	Uint32 id;
	Uint32 support;
	Uint32 on;
	Uint32 off;
#ifdef USE_UNION
	union {
		Uint32 push;
#endif
		Uint32 press;
#ifdef USE_UNION
	};
#endif
#ifdef USE_UNION
	union {
		Uint32 pull;
#endif
		Uint32 release;
#ifdef USE_UNION
	};
#endif
	Uint16 r;
	Uint16 l;
	Sint16 x1;
	Sint16 y1;
	Sint16 x2;
	Sint16 y2;
	char* name;
	void* extend;
	Uint32 old;
	PDS_PERIPHERALINFO* info;
} PDS_PERIPHERAL;
#endif
#define NJD_USER_CONTINUE  0
#define NJD_USER_EXIT      (-1)
extern const NJS_PERIPHERAL* njGetPeripheral(Uint32 port);
extern void njPrintPeripheralInfo(Int loc, Uint32 port);
extern void njUserInit(void);
extern Sint32 njUserMain(void);
extern void njUserExit(void);
#ifdef __cplusplus
}
#endif
#endif
