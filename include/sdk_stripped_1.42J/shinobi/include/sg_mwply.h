#ifndef _SG_MWPLY_H_
#define _SG_MWPLY_H_
#define		MWD_PLY_VER		""
#include <sg_xpt.h>
#define	MWD_PLY_LID	{ \
	0xa99e5b80, 0x09f9, 0x11d2, \
	0xa5, 0xa0, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00 \
}
#define	MWD_PLY_PRI_VBLNK		(0x70)
#define	MWD_PLY_MAX_OBJ		(32)
#define	MWD_PLY_ERR_OK			(0)
#define	MWD_PLY_ERR_NG			(-1)
#define	MWD_PLY_ERR_FATAL		(-2)
#define	MWD_PLY_ERR_INTERNAL	(-3)
#define	MWD_PLY_ERR_PRM			(-4)
#define	MWD_PLY_ERR_NOHN		(-11)
#define	MWD_PLY_ERR_NULHN		(-12)
#define	MWD_PLY_ERR_GSC_INIT	(-101)
#define	MWD_PLY_ERR_GSC_OPFN	(-102)
#define	MWD_PLY_ERR_GSC_START	(-103)
#define	MWD_PLY_ERR_GSC_OPENAGAIN	(-104)
#define	MWD_PLY_ERR_SJ_FATAL	(-201)
#define MWD_CH_L				(0)
#define MWD_CH_R				(1)
#define	MWD_PAN_LEFT			(-15)
#define	MWD_PAN_CENTER			(0)
#define	MWD_PAN_RIGHT			(15)
#define	MWD_PAN_AUTO			(-128)
typedef	enum _mwe_ply_stat {
	MWE_PLY_STAT_STOP		= (0),
	MWE_PLY_STAT_PREP		= (1),
	MWE_PLY_STAT_PLAYING	= (2),
	MWE_PLY_STAT_PLAYEND	= (3),
	MWE_PLY_STAT_ERROR		= (4)
} MWE_PLY_STAT;
#define	MWD_PLY_TIME2SEC(ncount, tscale)	((ncount) / (tscale))
#define	MWD_PLY_TIME2MSEC(ncount, tscale)	((1000 * (ncount)) / (tscale))
#ifndef MWPLY_DEFINED
#define MWPLY_DEFINED
typedef struct {
	struct _mwply_if *vtbl;
} MW_PLY_OBJ;
typedef MW_PLY_OBJ *MWPLY;
#endif
typedef void (*MW_PLY_ERRFN)(void *obj, char *ecode);
typedef struct _mwply_if {
	void (*QueryInterface)();
	void (*AddRef)();
	void (*Release)();
	void (*VsyncHndl)(MWPLY ply);
	void (*ExecSvrHndl)(MWPLY ply);
	void (*Destroy)(MWPLY ply);
	void (*StartFname)(MWPLY ply, Sint8 *fname);
	void (*Stop)(MWPLY ply);
	MWE_PLY_STAT (*GetStat)(MWPLY ply);
	void (*GetTime)(MWPLY ply, Sint32 *ncount, Sint32 *tscale);
	void (*Pause)(MWPLY ply, Sint32 sw);
	void (*SetOutVol)(MWPLY ply, Sint32 vol);
	Sint32 (*GetOutVol)(MWPLY ply);
	void (*SetOutPan)(MWPLY ply, Sint32 chno, Sint32 pan);
	Sint32 (*GetOutPan)(MWPLY ply, Sint32 chno);
} MWD_IF;
#define mwPlyVsyncHndl(ply)			(*(ply)->vtbl->VsyncHndl)((ply))
#define mwPlyExecSvrHndl(ply)		(*(ply)->vtbl->ExecSvrHndl)((ply))
#define mwPlyDestroy(ply)			(*(ply)->vtbl->Destroy)((ply))
#define mwPlyStartFname(ply, fname)	(*(ply)->vtbl->StartFname)((ply), (fname))
#define mwPlyStop(ply)				(*(ply)->vtbl->Stop)((ply))
#define mwPlyGetStat(ply)			(*(ply)->vtbl->GetStat)((ply))
#define mwPlyGetTime(ply, ncount, tscale)	\
							(*(ply)->vtbl->GetTime)((ply), (ncount), (tscale))
#define	mwPlyPause(ply, sw)			(*(ply)->vtbl->Pause)((ply), (sw))
#define mwPlySetOutVol(ply, vol)	(*(ply)->vtbl->SetOutVol)((ply), (vol))
#define mwPlyGetOutVol(ply)			(*(ply)->vtbl->GetOutVol)((ply))
#define mwPlySetOutPan(ply, c, p)	(*(ply)->vtbl->SetOutPan)((ply), (c), (p))
#define mwPlyGetOutPan(ply, c)     (*(ply)->vtbl->GetOutPan)((ply), (c))
void mwPlyStartFrame(void);
void mwPlyEntryErrFunc(MW_PLY_ERRFN errfn, void *obj);
void mwPlyExecServer(void);
#endif

