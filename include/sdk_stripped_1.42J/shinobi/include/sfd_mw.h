#ifndef	_SFD_MW_H_
#define	_SFD_MW_H_
#define	MWD_SFD_VER	""
#define	MWD_PLY_ERR_SFD_INIT	(-301)
#define	MWD_PLY_ERR_SFD_NOTYPE	(-302)
#define	MWD_PLY_ERR_SFD_ERRFN	(-303)
#define	MWD_PLY_ERR_SFD_FINISH	(-304)
#define	MWD_PLY_ERR_SFD_CREATE	(-305)
#define	MWD_PLY_ERR_SFD_DSTRY	(-306)
#define	MWD_PLY_ERR_SFD_START	(-307)
#define	MWD_PLY_ERR_SFD_STOP	(-308)
#define	MWD_PLY_ERR_SFD_GETTIME	(-309)
#define	MWD_PLY_ERR_SFD_PAUSE	(-310)
#define	MWD_PLY_ERR_SFD_STANDBY	(-311)
#define	MWD_PLY_FTYPE_NON		(0)
#define	MWD_PLY_FTYPE_SFD		(1)
#define	MWD_PLY_FTYPE_MPV		(2)
#define	MWD_DECTYP_NON			(0)
#define	MWD_DECTYP_SOFDEC		(1)
#define	MWD_LATENCY_2V			(2)
#define	MWD_LATENCY_3V			(3)
#define	MWD_GSCHN_MAX			(1)
#define MWD_PLY_DTYPE_AUTO	(0)
#define MWD_PLY_DTYPE_FULL	(1)
#if 0
#define MWD_DFL_BRIGHT		(0xea)
#define MWD_DFL_BRIGHT		(0xff)
#endif
#define MWD_DFL_BRIGHT		(0xe0)
#define MWD_DFL_BRIGHT_OFST	(6)
#define MWD_DFL_DLZ			(65536.0f)
#define	MWD_SFD_CALC_WORK_AUDIO_OUT(nch)	(0x2020*sizeof(short)*(nch)+32)
#define	MWD_SFD_CALC_WORK_AUDIO_OUT0	MWD_SFD_CALC_WORK_AUDIO_OUT(2)
#define	MWD_SFD_CALC_WORK_AUDIO_IN			(36*2048+32)
#define	MWD_SFD_SIZE_WORK_AUDIO(nch)	( \
				MWD_SFD_CALC_WORK_AUDIO_OUT0 + \
				MWD_SFD_CALC_WORK_AUDIO_IN \
			)
#define	MWD_SFD_CALC_WORK_RFB(wc, hc, wy, hy)	\
								SFD_RFB_BUF_SIZ((wc), (hc), (wy), (hy))
#define	MWD_SFD_CALC_WORK_RFB0 \
				MWD_SFD_CALC_WORK_RFB(	SFD_RFB_WIDTH_C, \
										SFD_RFB_HEIGHT_C, \
										SFD_RFB_WIDTH_Y, \
										SFD_RFB_HEIGHT_Y )
#define	MWD_SFD_CALC_WORK_TAB(wy, hy, nfrm)	\
								SFD_TA_BUF_SIZ((wy), (hy), (nfrm))
#define MWD_SFD_CALC_WORK_TAB0	\
				MWD_SFD_CALC_WORK_TAB(SFD_RFB_WIDTH_Y, SFD_RFB_HEIGHT_Y, 4)
#define	MWD_SFD_CALC_WORK(sx, sy, nch)	\
		MWD_SFD_CALC_WORK_AUDIO(2) +	\
#define	MWD_SFD_SIZE_WORK		(0x00300000)
#define	MWD_PLY_LATENCY(op, om, tp, tm, pt) ( \
			((op) < 0) ? MWD_LATENCY_2V : \
			((om) < 0) ? MWD_LATENCY_2V : \
			((tp) < 0) ? MWD_LATENCY_2V : \
			((tm) < 0) ? MWD_LATENCY_2V : \
			((pt) < 0) ? MWD_LATENCY_2V : MWD_LATENCY_3V)
typedef struct {
#if 0
	Sint32		ftype;
	Sint32		hnmax;
	Sint32		vsync_mhz;
	Sint32		disp_latency;
#endif
	Sint32		mode;
	Sint32		frame;
	Sint32		count;
	Sint32		latency;
	Sint32		rsv[4];
} MWS_PLY_INIT_SFD;
typedef struct {
	Sint32	ftype;
	Sint32	max_bps;
	Sint32	max_width;
	Sint32	max_height;
	Sint32	nfrm_pool_wk;
	Sint8	*work;
	Sint32	wksize;
	Sint32  dtype;
} MWS_PLY_CPRM_SFD;
void mwPlyPreInitSofdec(void);
void mwPlyInitSofdec(MWS_PLY_INIT_SFD *iprm);
void mwPlyFinishSofdec(void);
MWPLY mwPlyCreateSofdec(MWS_PLY_CPRM_SFD *cprm);
Sint32 mwPlyCalcWorkSofdec(
	Sint32 ftype, Sint32 max_bps, Sint32 max_sx, Sint32 max_sy, Sint32 nfb);
Sint32 mwPlyCalcWorkCprmSfd(MWS_PLY_CPRM_SFD *cprm);
void mwPlySetDispMode(Sint32 mode, Sint32 frame, Sint32 count, Sint32 latency);
void mwPlySetFastHalfpel(MWPLY mwply, Sint32 sw);
void mwPlySetAdjustY16(MWPLY mwply, Sint32 sw);
void mwPlySetAudioSw(MWPLY mwply, Sint32 sw);
void mwPlySetDispPos(MWPLY mwply, float lx, float ly);
void mwPlySetDispSize(MWPLY mwply, float sx, float sy);
void mwPlySetBright(MWPLY mwply, Sint32 val);
void mwPlySetBrightOfst(MWPLY mwply, Sint32 val);
Sint32 mwPlyGetBright(MWPLY mwply);
Sint32 mwPlyGetBrightOfst(MWPLY mwply);
float mwPlyGetDispZ(MWPLY mwply);
void mwPlySetDispZ(MWPLY mwply, float z);
void mwPlySetVideoSw(MWPLY ply, Sint32 sw);
Sint32 mwPlyGetVideoSw(MWPLY ply);
Sint32 mwPlyGetNumDropFrm(MWPLY ply);
#endif

