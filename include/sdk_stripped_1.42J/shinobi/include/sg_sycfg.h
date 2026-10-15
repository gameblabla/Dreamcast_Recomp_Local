#ifndef _SG_SYCFG_H_
#define _SG_SYCFG_H_
#include    <sg_xpt.h>
#include    <shinobi.h>
#define SYD_CFG_STEREO  (0x00)
#define SYD_CFG_MONO    (0x01)
#define SYD_CFG_OK      (0)
#define SYD_CFG_NG      (-1)
#define SYD_CFG_JAPAN    (0x30)
#define SYD_CFG_AMERICA  (0x31)
#define SYD_CFG_EUROPE   (0x32)
#define SYD_CFG_JAPANESE   (0x0)
#define SYD_CFG_ENGLISH    (0x1)
#define SYD_CFG_GERMAN     (0x2)
#define SYD_CFG_FRENCH     (0x3)
#define SYD_CFG_SPANISH    (0x4)
#define SYD_CFG_ITALIAN    (0x5)
#define SYD_CFG_D_JAPANESE (0x30)
#define SYD_CFG_D_ENGLISH  (0x31)
#define SYD_CFG_D_GERMAN   (0x32)
#define SYD_CFG_D_FRENCH   (0x33)
#define SYD_CFG_D_SPANISH  (0x34)
#define SYD_CFG_D_ITALIAN  (0x35)
#define SYD_CFG_NTSC     (0x30)
#define SYD_CFG_PAL      (0x31)
#define SYD_CFG_PAL_M    (0x32)
#define SYD_CFG_PAL_N    (0x33)
#define SYD_CFG_IID_SIZE (6)
#define SYD_CFG_IID_OK		(1)
#define SYD_CFG_IID_CHKERR	(2)
#define SYD_CFG_IID_NG  	(0)
#ifdef __cplusplus
extern ""{
#endif
Sint32 syCfgInit( Void* ) ;
Sint32 syCfgExit( Void  ) ;
Sint32 syCfgSetSoundMode( Sint32  ) ;
Sint32 syCfgGetSoundMode( Sint32* ) ;
Sint32 syCfgGetCountryCode  ( Sint32* ) ;
Sint32 syCfgGetLanguage     ( Sint32* ) ;
Sint32 syCfgGetDefaultLanguage( Sint32* ) ;
Sint32 syCfgGetBroadcastType( Sint32* ) ;
Sint32 syCfgGetIndividualID( Sint8* ) ;
#ifdef __cplusplus
}
#endif
#endif
