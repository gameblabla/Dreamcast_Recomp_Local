#ifndef _PROTO_WS_H
#define _PROTO_WS_H
#ifndef SG_XPT_H
#ifndef _VTYPE_DEFINED_
#define _VTYPE_DEFINED_
typedef signed char Sint8;
typedef signed short Sint16;
typedef signed long Sint32;
typedef unsigned char Uint8;
typedef unsigned short Uint16;
typedef unsigned long Uint32;
typedef float Float;
typedef int Int;
#endif
typedef int Bool;
enum BooleanLogic {
	FALSE = 0,
	TRUE  = 1
};
#endif
#ifndef NULL
#define NULL ((void *)0)
#endif
#if 0
#define WSD_TRIAL_SIP
#endif
#define WSD_ERR_OK            (0)
#define WSD_ERR_FATAL         (-1)
#define WSD_BUF_WSBUF_MAX      (4)
#define WSD_STM_WSSTM_MAX      (16)
#define WSD_BUF_SFREQ_11KHZ    (0)
#define WSD_BUF_SFREQ_8KHZ     (1)
#define WSD_BUF_BPS_16BIT      (0)
#define WSD_BUF_BPS_8BIT       (1)
#ifndef WSD_TRIAL_SIP
#define WSD_BUF_GAIN_MAX        (16)
#define WSD_BUF_GAIN_MIN        (-15)
#else
#define WSD_BUF_GAIN_MAX        (8)
#define WSD_BUF_GAIN_MIN        (-7)
#endif
#define WSD_DEV_A1              (1)
#define WSD_DEV_A2              (2)
#define WSD_DEV_A3              (3)
#define WSD_DEV_A4              (4)
#define WSD_DEV_A5              (5)
#define WSD_DEV_B1              (7)
#define WSD_DEV_B2              (8)
#define WSD_DEV_B3              (9)
#define WSD_DEV_B4              (10)
#define WSD_DEV_B5              (11)
#define WSD_DEV_C1              (13)
#define WSD_DEV_C2              (14)
#define WSD_DEV_C3              (15)
#define WSD_DEV_C4              (16)
#define WSD_DEV_C5              (17)
#define WSD_DEV_D1              (19)
#define WSD_DEV_D2              (20)
#define WSD_DEV_D3              (21)
#define WSD_DEV_D4              (22)
#define WSD_DEV_D5              (23)
#define WSD_STAT_DISCNCT      (0)
#define WSD_STAT_STOP         (1)
#define WSD_STAT_REC          (2)
#define WSD_STAT_ERR          (3)
#define WSD_STAT_RETRY        (4)
#define WSD_STAT_RESTART      (5)
#define WSD_STM_SEEK_SET       (0)
#define WSD_STM_SEEK_CUR       (1)
#define WSD_STM_SEEK_END       (2)
typedef struct _WSS_POS {
    Uint32 high;
    Uint32 low;
} WSS_POS;
typedef struct _WSBUF_OBJ {
    Uint8 recStat;
    Uint8 use;
    Sint32 sfreq;
    Sint32 bps;
    Sint32 blksize;
    Sint32 nblk;
    Sint32 bufnsmpl;
    Sint32 gain;
    Sint32 seq;
    Sint32 lastSeq;
    Sint32 device;
    Sint32 command;
    Sint32 lastCom;
    Sint32 initSeq;
#if 1
	Sint32 lastNsmpl;
	Sint32 sbfov;
#endif
    WSS_POS wpos;
    Sint32 err;
    void *bufptr;
} WSBUF_OBJ, *WSBUF;
typedef struct _WSS_BUF_PRM {
    Sint32 sfreq;
    Sint32 bps;
    Sint32 blksize;
    Sint32 nblk;
    Sint32 gain;
    void *bufptr;
} WSS_BUF_PRM;
typedef struct _WSSTM_OBJ {
    Uint8 overFlag;
    Uint8 use;
    WSBUF wsb;
    WSS_POS rpos;
} WSSTM_OBJ, *WSSTM;
Sint32 wsInit( void );
void wsFinish( void );
WSBUF wsBufCreate( Sint32 pno, WSS_BUF_PRM para );
void wsBufDestroy( WSBUF wsbuf );
Sint32 wsBufStart( WSBUF wsbuf );
Sint32 wsBufStop( WSBUF wsbuf );
void wsBufExecServer( void);
Sint32 wsBufGetStat( WSBUF wsbuf );
Sint32 wsBufGetErr( WSBUF wsbuf );
Sint32 wsBufGetNumSmpl( WSBUF wsbuf );
WSS_POS wsBufGetWrPos( WSBUF wsbuf );
Sint32 wsBufGetSfreq( WSBUF wsbuf );
Sint32 wsBufGetBitPerSmpl( WSBUF wsbuf );
Sint32 wsBufGetAmpGain( WSBUF wsbuf );
Sint32 wsBufSetAmpGain( WSBUF wsbuf, Sint32 gain );
#if 1
Sint32 wsBufGetSBFOV( WSBUF wsbuf );
#endif
WSSTM wsStmCreate( WSBUF wsbuf );
void wsStmDestroy( WSSTM wsstm );
WSBUF wsStmGetWsbuf( WSSTM wsstm );
Sint32 wsStmGetNumSmpl(WSSTM wsstm );
WSS_POS wsStmSeekRdPos( WSSTM wsstm, WSS_POS pos, Sint32 mode );
WSS_POS wsStmGetRdPos( WSSTM wsstm );
WSS_POS wsStmAddRdPos( WSSTM wsstm, Sint32 nsmpl );
Bool wsStmIsOverFlow( WSSTM wsstm );
void wsStmClearOverflow( WSSTM wsstm );
Sint32 wsStmCopyPcm( WSSTM wsstm, void *buf, Sint32 bufsite );
WSS_POS wsPosAdd( WSS_POS pos, Sint32 num );
WSS_POS wsPosAddPos( WSS_POS posa, WSS_POS posb );
WSS_POS wsPosMinus( WSS_POS posa, WSS_POS posb );
Sint32 wsPosDif( WSS_POS posa, WSS_POS posb );
Sint32 wsPosMod( WSS_POS pos, Sint32 num );
WSS_POS wsPosMul2( WSS_POS pos );
Sint32 wsPosCmp( WSS_POS posa, WSS_POS posb );
#endif
