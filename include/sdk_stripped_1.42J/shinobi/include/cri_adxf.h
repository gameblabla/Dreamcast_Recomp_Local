#ifndef	_CRI_ADXF_H_INCLUDED
#define	_CRI_ADXF_H_INCLUDED
#define	ADXF_VER				""
#define	ADXF_PART_MAX			(256)
#define	ADXF_FILE_MAX			(65536)
#define	ADXF_OBJ_MAX			(16)
#define	ADXF_STAT_STOP			(1)
#define ADXF_STAT_READING		(2)
#define ADXF_STAT_READEND		(3)
#define ADXF_STAT_ERROR			(4)
#define	ADXF_SEEK_SET			(0)
#define ADXF_SEEK_CUR			(1)
#define ADXF_SEEK_END			(2)
#define	ADXF_ERR_OK				(0)
#define	ADXF_ERR_FATAL			(-1)
#define	ADXF_ERR_INTERNAL		(-2)
#define	ADXF_ERR_PRM			(-3)
#define	ADXF_ERR_AFS_FILE		(-4)
#define	ADXF_DEF_SCT_SIZE		(2048)
#define	ADXF_DEF_DMA_ALIGN		(32)
#define	ADXF_CMD_HSTRY_MAX		(256)
#define	ADXF_CMD_OPEN			(1)
#define	ADXF_CMD_OPEN_AFS		(2)
#define	ADXF_CMD_CLOSE			(3)
#define	ADXF_CMD_READ_NW32		(4)
#define	ADXF_CMD_STOP			(5)
#define	ADXF_CMD_SEEK			(6)
#define	ADXF_CMD_NUM_MAX		(16)
#define	ADXF_PTIF_CMN_SZ			(5*sizeof(long))
#define	ADXF_CALC_PTINFO_REAL_SIZE(n)	\
								(ADXF_PTIF_CMN_SZ+(((n)+1)*sizeof(short)))
#define	ADXF_CALC_PTINFO_SIZE(n)	\
					((ADXF_CALC_PTINFO_REAL_SIZE(n)+sizeof(short))/4*4)
#define	ADXF_CALC_ADD_PTINFO_SIZE(n)	\
					(ADXF_PTIF_CMN_SZ+((n)*(2*sizeof(short)+sizeof(long))))
#ifndef ADXSTM_DEFINED
#define ADXSTM_DEFINED
typedef void *ADXSTM;
#endif
#ifndef SJ_DEFINED
#define SJ_DEFINED
typedef void *SJ;
#endif
#ifndef ADXF_DEFINED
#define	ADXF_DEFINED
typedef	struct _adx_fs {
	char	used;
	char	stat;
	char	sjflag;
	char	rev;
	ADXSTM	stm;
	SJ		sj;
	long	fad;
	long	fnsct;
	long	fsize;
	long	skpos;
	long	rdstpos;
	long	rqsct;
	long	rdsct;
	char	*buf;
	long	bsize;
} ADX_FS;
typedef	ADX_FS	*ADXF;
#endif
#ifndef ADXF_PTINFO_DEFINED
#define ADXF_PTINFO_DEFINED
typedef struct _adxf_ptinfo {
	struct _adxf_ptinfo	*next;
	long				size;
	long				fad;
	long				nfile;
	unsigned short		nentry;
	char				type;
	char				rev;
	long				top;
} ADXF_PTINFO;
#endif
#ifndef ADXF_ADD_DEFINED
#define ADXF_ADD_DEFINED
typedef struct _adxf_add_info {
	unsigned short	flid;
	unsigned short	fnsct;
	long			ofst;
} ADXF_ADD_INFO;
#endif
#ifndef ADXF_CMD_HSTRY_DEFINED
#define ADXF_CMD_HSTRY_DEFINED
typedef struct _adxf_cmd_hstry {
	unsigned char	cmdid;
	unsigned char	fg;
	unsigned short	ncall;
	long	prm[3];
} ADXF_CMD_HSTRY;
#endif
#ifdef __cplusplus
extern "" {
#endif
void ADXF_Init(void);
void ADXF_Finish(void);
long ADXF_LoadPartition(long ptid, char *fname, void *ptinfo, long nfile);
long ADXF_AddPartition(long ptid, char *fname, void *ptinfo, long nfile);
long ADXF_GetPtinfoSize(long ptid);
ADXF ADXF_Open(char *fname, void *atr);
ADXF ADXF_OpenAfs(long ptid, long flid);
void ADXF_Close(ADXF adxf);
long ADXF_ReadSj32(ADXF adxf, long nsct, SJ sj);
long ADXF_ReadNw32(ADXF adxf, long nsct, void *buf);
long ADXF_Stop(ADXF adxf);
void ADXF_ExecServer(void);
long ADXF_Seek(ADXF adxf, long pos, long type);
long ADXF_Tell(ADXF adxf);
long ADXF_GetFsizeSct(ADXF adxf);
long ADXF_GetFsizeByte(ADXF adxf);
long ADXF_GetNumReqSct(ADXF adxf, long *seekpos);
long ADXF_GetNumReadSct(ADXF adxf);
long ADXF_GetStat(ADXF adxf);
long ADXF_GetFileRange(long ptid, long flid, long *fad, long *fnsct);
#ifdef __cplusplus
}
#endif
#endif

