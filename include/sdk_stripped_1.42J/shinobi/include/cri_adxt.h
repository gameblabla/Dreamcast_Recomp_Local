#ifndef	_ADXT_H_INCLUDED
#define	_ADXT_H_INCLUDED
#define	ADXT_VER	""
#ifndef SJ_DEFINED
#define SJ_DEFINED
typedef void *SJ;
#endif
#ifndef ADXSTM_DEFINED
#define ADXSTM_DEFINED
typedef	void	*ADXSTM;
#endif
#ifndef ADXSJD_DEFINED
#define ADXSJD_DEFINED
typedef void	*ADXSJD;
#endif
#ifndef ADXRNA_DEFINED
#define ADXRNA_DEFINED
typedef void	*ADXRNA;
#endif
#ifndef TRUE
#define TRUE	1
#endif
#ifndef FALSE
#define FALSE	0
#endif
#define	ADXT_MAX_OBJ		(8)
#define	ADXT_MAX_DATASIZE	(0x40000000)
#define ADXT_IBUF_XLEN (36)
#define	ADXT_OBUF_SIZE	(0x2000)
#define	ADXT_OBUF_DIST	(0x2020)
#define	ADXT_MAX_SFREQ	(44100)
#define ADXT_PLY_MEM	(0)
#define ADXT_PLY_STM	(1)
#define ADXT_CALC_IBUFSIZE0(nch, sfreq)	(25000*(nch)*((sfreq)/1000)/44)
#define ADXT_CALC_IBUFSIZE(nch, nstm, sfreq)	\
	((ADXT_CALC_IBUFSIZE0(nch, sfreq)*((nstm)+1)+2048)/2048*2048+ADXT_IBUF_XLEN)
#define ADXT_CALC_OBUFSIZE(nch)	\
	( ADXT_OBUF_DIST*(nch)*sizeof(short))
#define ADXT_CALC_WORK(nch, stmflg, nstm, sfreq)	\
	(ADXT_CALC_IBUFSIZE(nch, nstm, sfreq)*(stmflg) + ADXT_CALC_OBUFSIZE(nch) + 32)
#define ADXT_MAX_CDBSCT		(75)
#define ADXT_MIN_CDBSCT		(65)
#define ADXT_PREP_RDSCT		(25)
#define	ADXT_STAT_STOP		(0)
#define ADXT_STAT_DECINFO	(1)
#define ADXT_STAT_PREP		(2)
#define ADXT_STAT_PLAYING	(3)
#define ADXT_STAT_DECEND	(4)
#define ADXT_STAT_PLAYEND	(5)
#define	ADXT_ERR_OK			(0)
#define ADXT_ERR_SHRTBUF	(-1)
#define ADXT_ERR_SNDBLK		(-2)
#define	ADXT_FLTMODE_CPU	(0)
#define	ADXT_FLTMODE_SCSP	(1)
#define	ADXT_PMODE_FNAME	(0)
#define	ADXT_PMODE_AFS		(1)
#define	ADXT_PMODE_MEM		(2)
#define	ADXT_PMODE_SJ		(3)
#define	ADXT_RMODE_NOACT	(0)
#define	ADXT_RMODE_STOP		(1)
#define	ADXT_RMODE_REPLAY	(2)
#define	ADXT_PAN_LEFT		(-15)
#define	ADXT_PAN_CENTER		(0)
#define	ADXT_PAN_RIGHT		(15)
#define	ADXT_PAN_AUTO		(-128)
#define	ADXT_CH_L			(0)
#define	ADXT_CH_R			(1)
#define	ADXT_MAX_NCH		(2)
#define ADXT_DEF_SVRFREQ	(60)
#define	ADXT_DEF_OUTVOL		(0)
#define	ADXT_MIN_BUFDATA	(64)
#define	ADXT_EWAIT_PLY		(5)
#define	ADXT_EWAIT_NOTPLY	(20)
#define	ADXT_MAX_IDX		(0xFFFF)
typedef	struct _adx_talk {
	char	used;
	char	stat;
	char	pmode;
	char	maxnch;
	ADXSJD	sjd;
	ADXSTM	stm;
	ADXRNA	rna;
	SJ		sjf;
	SJ		sji;
	SJ		sjo[ADXT_MAX_NCH];
	char	*ibuf;
	long	ibuflen;
	long	ibufxlen;
	short	*obuf;
	long	obufsize;
	long	obufdist;
	long	svrfreq;
	short	maxsct;
	short	minsct;
	short	outvol;
	short	outpan[ADXT_MAX_NCH];
	long	maxdecsmpl;
	long	lpcnt;
	long	lp_skiplen;
	long	trp;
	long	wpos;
	long	mofst;
	short	ercode;
	long	edecpos;
	short	edeccnt;
	short	eshrtcnt;
	char	lpflg;
	char	autorcvr;
	char	fltmode;
	char	execflag;
	char	pstwait_flag;
	char	pstready_flag;
	char	pause_flag;
} ADX_TALK;
typedef	ADX_TALK	*ADXT;
typedef struct _adxt_idx {
	unsigned short nidx;
	unsigned short top;
} ADXT_IDX;
#ifdef __cplusplus
extern "" {
#endif
void ADXT_Init(void);
void ADXT_ResetLibrary(void);
void ADXT_Finish(void);
ADXT ADXT_Create(long maxnch, void *work, long worksize);
void ADXT_Destroy(ADXT adxt);
void ADXT_StartAfs(ADXT adxt, long patid, long fid);
void ADXT_StartFname(ADXT adxt, char *fname);
void ADXT_StartSj(ADXT adxt, SJ sj);
void ADXT_StartMem(ADXT adxt, void *adxdat);
void ADXT_StartMem2(ADXT adxt, void *adxdat, long datlen);
void ADXT_StartMemIdx(ADXT adxt, void *acx, long no);
void ADXT_Stop(ADXT adxt);
long ADXT_GetStat(ADXT adxt);
void ADXT_GetTime(ADXT adxt, long *ncount, long *tscale);
long ADXT_GetTimeReal(ADXT adxt);
long ADXT_GetNumSmpl(ADXT adxt);
long ADXT_GetSfreq(ADXT adxt);
void ADXT_SetOutPan(ADXT adxt, long ch, long pan);
long ADXT_GetOutPan(ADXT adxt, long ch);
void ADXT_SetOutVol(ADXT adxt, long vol);
long ADXT_GetOutVol(ADXT adxt);
void ADXT_SetSvrFreq(ADXT adxt, long freq);
void ADXT_SetReloadSct(ADXT adxt, long minsct);
long ADXT_GetNumSctIbuf(ADXT adxt);
long ADXT_IsIbufSafety(ADXT adxt);
void ADXT_SetAutoRcvr(ADXT adxt, long rmode);
long ADXT_IsCompleted(ADXT adxt);
void ADXT_ExecHndl(ADXT adxt);
void ADXT_ExecServer(void);
long ADXT_GetErrCode(ADXT adxt);
void ADXT_ClearErrCode(ADXT adxt);
long ADXT_GetLpCnt(ADXT adxt);
void ADXT_SetLpFlg(ADXT adxt, long flg);
SJ ADXT_GetInputSj(ADXT adxt);
void ADXT_SetWaitPlayStart(ADXT adxt, long flg);
long ADXT_IsReadyPlayStart(ADXT adxt);
void ADXT_Pause(ADXT adxt, long sw);
void ADXT_SetFx(ADXT adxt, long fxch, long fxlvl);
void ADXT_GetFx(ADXT adxt, long *fxch, long *fxlvl);
void ADXT_SetFilter(ADXT adxt, long coff, long q);
void ADXT_GetFilter(ADXT adxt, long *coff, long *q);
void ADXT_SetTranspose(ADXT adxt, long transps, long detune);
void ADXT_GetTranspose(ADXT adxt, long *transps, long *detune);
void ADXT_EntryErrFunc(void (*func)(void *obj, char *msg), void *obj);
long ADXT_DiscardSmpl(ADXT adxt, long nsmpl);
#ifdef __cplusplus
}
#endif
#endif

