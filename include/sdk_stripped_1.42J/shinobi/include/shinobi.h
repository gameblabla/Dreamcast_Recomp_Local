#ifndef _SHINOBI_H_
#define _SHINOBI_H_
#include <machine.h>
#include <ninja.h>
#include <ninjapad.h>
#ifdef __cplusplus
extern "" {
#endif
#include <sg_pad.h>
#include <sg_gd.h>
#include <sg_sytmr.h>
#include <sg_syrtc.h>
#include <sg_maloc.h>
#include <sg_sycbl.h>
#include <sg_sycfg.h>
#include <sg_sybt.h>
#include <sg_btfnt.h>
#include <sg_lcd.h>
#include <sg_pdkbd.h>
#include <sg_pdvib.h>
#include <sg_pdtmr.h>
#include <sg_bup.h>
#include <sg_cache.h>
#include <sg_uf.h>
#include <wssip.h>
#include <sg_sysrt.h>
extern void sbInitSystem(Int mode, Int frame, Int count);
extern void sbExitSystem(void);
#ifdef __cplusplus
}
#endif
#endif
