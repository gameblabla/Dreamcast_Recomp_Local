#ifndef _SG_PDKBD_H_
#define _SG_PDKBD_H_
#ifdef __cplusplus
extern "" {
#endif
#include <sg_xpt.h>
#include <sg_pad.h>
#define PDD_KEY_CTRL_RGUI     (1 << 7)
#define PDD_KEY_CTRL_RALT     (1 << 6)
#define PDD_KEY_CTRL_RSHIFT   (1 << 5)
#define PDD_KEY_CTRL_RCTRL    (1 << 4)
#define PDD_KEY_CTRL_LGUI     (1 << 3)
#define PDD_KEY_CTRL_LALT     (1 << 2)
#define PDD_KEY_CTRL_LSHIFT   (1 << 1)
#define PDD_KEY_CTRL_LCTRL    (1 << 0)
#define PDD_LED_SHIFT         (1 << 7)
#define PDD_LED_POWER         (1 << 6)
#define PDD_LED_KANA          (1 << 5)
#define PDD_LED_SCRLOCK       (1 << 2)
#define PDD_LED_CAPLOCK       (1 << 1)
#define PDD_LED_NUMLOCK       (1 << 0)
typedef struct {
	Uint8 ctrl;
	Uint8 led;
	Uint8 key[6];
} PDS_KEYBOARD;
#if 0
typedef struct {
	Uint8 lang;
	Uint8 type;
	Uint8 reserved[2];
} PDS_KEYBOARDINFO;
typedef struct {
	Uint8 used;
	Uint8 rate;
	Uint8 delay;
	Uint8 rate_count;
	Uint8 delay_count;
	Uint8 repeat_flag;
	Uint8 predata;
	Uint8 old_data[8];
	Uint32 port;
	Uint32 putp;
	Uint32 getp;
	Uint8* buf;
	Uint32 bufsize;
} PDS_KBDSTRUCT;
typedef PDS_KBDSTRUCT* PD_KBD;
#endif
const PDS_KEYBOARD* pdKbdGetData(Uint32 port);
#if 0
const PDS_KEYBOARDINFO* pdKbdGetInfo(Uint32 port);
#endif
#if 0
void pdKbdInit(void);
void pdKbdSetState(PD_KBD hKbd, Uint8 rate, Uint8 delay);
void pdKbdGetState(PD_KBD hKbd, Uint8* rate, Uint8* delay);
Sint32 pdKbdIsHit(PD_KBD hKbd);
PD_KBD pdKbdCreate(Uint32 port);
void pdKbdDestroy(PD_KBD kbd);
char pdKbdGetc(PD_KBD hKbd);
void pdKbdExecServer(void);
void pdKbdExecServerOne(PD_KBD hKbd);
#endif
#ifdef __cplusplus
}
#endif
#endif
