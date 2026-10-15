#ifndef	_PLA_MW_H_
#define	_PLA_MW_H_
#define	MWD_PLY_ERR_WAV_INIT	(-301)
#define	MWD_PLY_ERR_WAV_NOTYPE	(-302)
#define	MWD_PLY_ERR_WAV_ERRFN	(-303)
#define	MWD_PLY_ERR_WAV_FINISH	(-304)
#define	MWD_PLY_ERR_WAV_CREATE	(-305)
#define	MWD_PLY_ERR_WAV_DSTRY	(-306)
#define	MWD_PLY_ERR_WAV_START	(-307)
#define	MWD_PLY_ERR_WAV_STOP	(-308)
#define	MWD_PLY_ERR_RNA_INIT	(-401)
#define	MWD_PLY_ERR_RNA_FINISH	(-402)
#define	MWD_PLY_ERR_RNA_CREATE	(-403)
#define	MWD_PLY_ERR_RNA_DSTRY	(-404)
#define	MWD_PLY_ERR_RNA_START	(-405)
#define	MWD_PLY_ERR_RNA_STOP	(-406)
#define	MWD_PLY_ERR_RNA_PRM		(-407)
#define	MWD_GSCHN_MAX			(1)
#define	MWD_PLY_SVR_VSYNC		(0)
#define	MWD_PLY_SVR_MAIN		(1)
#define	MWD_PLY_CALC_AWORK(n)	((2048*(n))+32)
#define	MWD_PLY_MIN_AWORK		(48)
#define	MWD_PLY_AT_EXEC_VSYNC	MWD_PLY_SVR_VSYNC
#define	MWD_PLY_MN_EXEC_VSYNC	MWD_PLY_SVR_MAIN
#define	MWD_PLY_ALLOC_SJBUF(n)	MWD_PLY_CALC_AWORK(n)
#define	MWD_PLY_ALLOC_LIMIT		MWD_PLY_MIN_AWORK
typedef struct {
	Uint8	*buf;
	Sint32	size;
	Sint32	*libwork;
} MWS_PLY_CPRM;
typedef	void	*DCAIF;
void	mwPlaInit(Sint32 mode, DCAIF iftbl);
void	mwPlaFinish(DCAIF iftbl);
MWPLY	mwPlaCreate(MWS_PLY_CPRM *cprm, DCAIF iftbl);
#endif

