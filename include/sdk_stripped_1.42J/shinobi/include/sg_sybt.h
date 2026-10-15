#ifndef _SG_SYBT_H_
#define _SG_SYBT_H_
#include    <sg_xpt.h>
#include    <shinobi.h>
#define SYD_BT_OK                (1)
#define SYD_BT_NG                (0)
struct tag_SYS_BT_SYSTEMID{
    Sint32 nNo ;
    Sint32 nAll ;
    Sint8  szProduct[16];
} ;
typedef struct tag_SYS_BT_SYSTEMID SYS_BT_SYSTEMID ;
#ifdef __cplusplus
extern ""{
#endif
extern Void   syBtExit     ( Void );
extern Sint32 syBtCheckDisc( Void );
extern Sint32 syBtGetBootSystemID   ( SYS_BT_SYSTEMID* ) ;
extern Sint32 syBtGetCurrentSystemID( SYS_BT_SYSTEMID* ) ;
#ifdef __cplusplus
}
#endif
#endif
