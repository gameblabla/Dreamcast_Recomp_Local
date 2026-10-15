#ifndef _SG_PAD_H_
#define _SG_PAD_H_
#ifdef __cplusplus
extern "" {
#endif
#include <sg_xpt.h>
#define PDD_PORT_A0    0
#define PDD_PORT_A1    1
#define PDD_PORT_A2    2
#define PDD_PORT_A3    3
#define PDD_PORT_A4    4
#define PDD_PORT_A5    5
#define PDD_PORT_B0    6
#define PDD_PORT_B1    7
#define PDD_PORT_B2    8
#define PDD_PORT_B3    9
#define PDD_PORT_B4   10
#define PDD_PORT_B5   11
#define PDD_PORT_C0   12
#define PDD_PORT_C1   13
#define PDD_PORT_C2   14
#define PDD_PORT_C3   15
#define PDD_PORT_C4   16
#define PDD_PORT_C5   17
#define PDD_PORT_D0   18
#define PDD_PORT_D1   19
#define PDD_PORT_D2   20
#define PDD_PORT_D3   21
#define PDD_PORT_D4   22
#define PDD_PORT_D5   23
#define PDD_DEV_SUPPORT_AY2   (1 << 21)
#define PDD_DEV_SUPPORT_AX2   (1 << 20)
#define PDD_DEV_SUPPORT_AY1   (1 << 19)
#define PDD_DEV_SUPPORT_AX1   (1 << 18)
#define PDD_DEV_SUPPORT_AL    (1 << 17)
#define PDD_DEV_SUPPORT_AR    (1 << 16)
#define PDD_DEV_SUPPORT_KRB   (1 << 15)
#define PDD_DEV_SUPPORT_KLB   (1 << 14)
#define PDD_DEV_SUPPORT_KDB   (1 << 13)
#define PDD_DEV_SUPPORT_KUB   (1 << 12)
#define PDD_DEV_SUPPORT_TD    (1 << 11)
#define PDD_DEV_SUPPORT_TX    (1 << 10)
#define PDD_DEV_SUPPORT_TY    (1 <<  9)
#define PDD_DEV_SUPPORT_TZ    (1 <<  8)
#define PDD_DEV_SUPPORT_KR    (1 <<  7)
#define PDD_DEV_SUPPORT_KL    (1 <<  6)
#define PDD_DEV_SUPPORT_KD    (1 <<  5)
#define PDD_DEV_SUPPORT_KU    (1 <<  4)
#define PDD_DEV_SUPPORT_ST    (1 <<  3)
#define PDD_DEV_SUPPORT_TA    (1 <<  2)
#define PDD_DEV_SUPPORT_TB    (1 <<  1)
#define PDD_DEV_SUPPORT_TC    (1 <<  0)
#define PDD_DGT_TL    (1 << 17)
#define PDD_DGT_TR    (1 << 16)
#define PDD_DGT_KRB   (1 << 15)
#define PDD_DGT_KLB   (1 << 14)
#define PDD_DGT_KDB   (1 << 13)
#define PDD_DGT_KUB   (1 << 12)
#define PDD_DGT_TD    (1 << 11)
#define PDD_DGT_TX    (1 << 10)
#define PDD_DGT_TY    (1 <<  9)
#define PDD_DGT_TZ    (1 <<  8)
#define PDD_DGT_KR    (1 <<  7)
#define PDD_DGT_KL    (1 <<  6)
#define PDD_DGT_KD    (1 <<  5)
#define PDD_DGT_KU    (1 <<  4)
#define PDD_DGT_ST    (1 <<  3)
#define PDD_DGT_TA    (1 <<  2)
#define PDD_DGT_TB    (1 <<  1)
#define PDD_DGT_TC    (1 <<  0)
#define PDD_ERR_OK       0x00000000
#define PDD_ERR_RETRY    0xff0000fc
#define PDD_ERR_GENERIC  0xff000000
#define PDD_PLOGIC_ACTIVE    0
#define PDD_PLOGIC_NEGATIVE  1
#define PDD_MODE_TYPE_A      1
#define PDD_MODE_TYPE_B      0
#define PDD_GUNMODE_OFF   0x00000000
#define PDD_GUNMODE_A     0x00000001
#define PDD_GUNMODE_B     0x00000002
#define PDD_GUNMODE_C     0x00000004
#define PDD_GUNMODE_D     0x00000008
#define PDD_GUNMODE_ALL   0x0000000f
#define PDM_WORK_SIZE(num) ((num) * 1024 * 2)
#define PDD_DEVTYPE_CONTROLLER   (1 << 0)
#define PDD_DEVTYPE_STORAGE      (1 << 1)
#define PDD_DEVTYPE_LCD          (1 << 2)
#define PDD_DEVTYPE_TIMER        (1 << 3)
#define PDD_DEVTYPE_SOUNDINPUT   (1 << 4)
#define PDD_DEVTYPE_KEYBOARD     (1 << 6)
#define PDD_DEVTYPE_LIGHTGUN     (1 << 7)
#define PDD_DEVTYPE_VIBRATION    (1 << 8)
#define PDD_DEVAREA_USA          (1 << 0)
#define PDD_DEVAREA_JAPAN        (1 << 1)
#define PDD_DEVAREA_ASIA         (1 << 2)
#define PDD_DEVAREA_EUROPE       (1 << 3)
#define PDD_DEVAREA_RESERVED1    (1 << 4)
#define PDD_DEVAREA_RESERVED2    (1 << 5)
#define PDD_DEVAREA_RESERVED3    (1 << 6)
#define PDD_DEVAREA_RESERVED4    (1 << 7)
#define PDD_CONDIR_TOPSIDE       0
#define PDD_CONDIR_BOTTOMSIDE    1
#define PDD_CONDIR_LEFTSIDE      2
#define PDD_CONDIR_RIGHTSIDE     3
typedef struct {
	Uint32 type;
	Uint32 reserved[3];
	Uint8 is_root;
	Uint8 area_code;
	Uint8 connector_dir[2];
	char product_name[32];
	char license[64];
	Uint16 stdby_pow;
	Uint16 max_pow;
} PDS_PERIPHERALINFO;
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
void pdInitPeripheral(Sint32 logic, void* recvbuf, void* sendbuf);
void pdInitPeripheralEx(Sint32 logic, Sint32* permap,
							void** recvbuf, void* sendbuf, Sint32 num);
void pdExitPeripheral(void);
void pdExecPeripheralServer(void);
void pdExecPeripheralServerUser(void);
const PDS_PERIPHERAL* pdGetPeripheral(Uint32 port);
Sint32 pdGetPeripheralError(Uint32 port);
const PDS_PERIPHERALINFO* pdGetPeripheralInfo(Uint32 port);
void pdSetMode(Sint32 mode);
Sint32 pdGetMode(void);
void pdSetOptimize(Uint32 count);
Uint32 pdGetOptimize(void);
void pdSetThreshold(Uint8 on, Uint8 off);
void pdGunEnter(Uint32 portbit);
void pdGunLeave(void);
Sint32 pdGunCheck(void);
void pdGunGetPosition(Sint32* x, Sint32* y);
Sint32 pdGunGetLatchedPort(void);
void pdGunSetFlashColor(Uint32 color);
Uint32 pdGunGetFlashColor(void);
void pdGunSetRapid(Uint32 port, Uint32 num);
void pdGunSetTrigger(Uint32 port);
void pdGunSetCallback(Sint32 (*func)(void));
#ifdef __cplusplus
}
#endif
#endif
