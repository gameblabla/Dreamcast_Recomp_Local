#ifndef _SG_LCD_H_
#define _SG_LCD_H_
#ifdef __cplusplus
extern "" {
#endif
#include <sg_xpt.h>
#define PDD_LCDERR_OK          0
#define PDD_LCDERR_BUSY       (-1)
#define PDD_LCDERR_NO_LCD     (-2)
#define PDD_LCD_DIRECTION_NORMAL   0
#define PDD_LCD_DIRECTION_FLIP     1
#define PDD_LCD_DIRECTION_LEFT     2
#define PDD_LCD_DIRECTION_RIGHT    3
#define PDD_LCD_FLAG_NOFLIP        0
#define PDD_LCD_FLAG_HFLIP         1
#define PDD_LCD_FLAG_VFLIP         2
#define PDD_LCD_FLAG_HVFLIP        3
void pdLcdInit(void);
void pdLcdExit(void);
Sint32 pdLcdGetDirection(Uint32 port);
Sint32 pdVmsLcdWrite(Uint32 port, void* data, Uint32 flag);
Sint32 pdVmsLcdWrite1(Uint32 port, void* data);
Sint32 pdVmsLcdIsReady(Uint32 port);
#ifdef __cplusplus
}
#endif
#endif
